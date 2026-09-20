"""Sample bank edits and background host audio jobs, using the shared browser."""
from copy import deepcopy
from pathlib import Path
import tempfile


class MediaActions:
    @staticmethod
    def _cleanup_media_folder(state):
        if state.get('folder'):
            try:
                state['folder'].cleanup()
            except OSError:
                # A terminating encoder may briefly hold its staging file on
                # Windows. Never crash the UI or touch the existing destination.
                import logging
                logging.getLogger('sidpulse.export.audio').warning('Temporary audio cleanup deferred', exc_info=True)

    def begin_audio_export(self):
        self.browse('wav')

    def import_sample_browser(self, instrument=None):
        if instrument is not None:
            if not self.allow_instrument_edit(instrument):return
            inst = self.editor.song.instruments[instrument]
            slot = inst.sample_slot or next((n for n in range(1, 100)
                    if str(n) not in self.editor.song.samples and n not in self.editor.song.samples), None)
            if slot is None:
                self.editor.status = 'Sample bank is full. Select a slot to replace in F3.'
                return
            self.sample_index = slot
        self.browse('sample', result={'slot': self.sample_index, 'instrument': instrument})

    def _start_media_job(self, source, options, *, folder=None, target=None, assignment=None):
        from sidpulse.export.analysis_job import AnalysisJob
        from sidpulse.export.audio import media_worker
        job = AnalysisJob(source, options, 'sid', worker=media_worker)
        state = dict(job=job, folder=folder, target=target, assignment=assignment,
                     kind='media_job', title=(options['operation'].title() + ' PCM sample') if assignment else 'Export audio',
                     phase='Preparing...', detail='', cancelled=False,
                     return_page=self.browser.return_page if self.page == 'files' else self.page)
        if options['operation']=='synthesize':state['title']='Create SID wavetable'
        if options['operation']=='synthesize_all':state['title']='Synthesize all PCM instruments'
        self.media_jobs.append(state)
        self.dialog = state
        job.start()
        self.sync_file_text_input()

    def start_audio_export(self, target, kind, loops):
        from sidpulse.audio.media import ffmpeg_path
        if kind == 'mp3':
            ffmpeg_path()  # fail before rendering if the optional encoder is absent
        self.release_audition()
        folder = tempfile.TemporaryDirectory(prefix='.sidpulse-audio-', dir=target.parent)
        try:
            self._start_media_job(self.editor.song,
                                  dict(operation='export', kind=kind, loops=loops,
                                       staged=str(Path(folder.name) / ('render.' + kind))),
                                  folder=folder, target=target)
        except Exception:
            folder.cleanup()
            raise

    def start_sample_import(self, target):
        assignment = self.browser.export_result or {'slot': self.sample_index, 'instrument': None}
        slot = assignment['slot']
        def begin():
            self._start_media_job(str(target), {'operation': 'import', 'auto_squeeze': self.sample_auto_squeeze,
                                  'normalize_before': self.sample_normalize_before,
                                  'normalize_after': self.sample_normalize_after},
                                  assignment=assignment)
        if str(slot) in self.editor.song.samples or slot in self.editor.song.samples:
            self.dialog = dict(title='Replace sample?', message=f'Replace sample {slot:02d}? '
                               'Assigned instruments will use the new sample. This can be undone.',
                               yes=begin, on_cancel=self._resume_file_browser)
        else:
            begin()

    def selected_sample(self):
        return self.editor.song.samples.get(str(self.sample_index), self.editor.song.samples.get(self.sample_index))

    def toggle_sample_auto_squeeze(self):
        from sidpulse.preferences import save_preferences
        enabled = not self.sample_auto_squeeze
        save_preferences({'sample_auto_squeeze_on_import': enabled})
        self.sample_auto_squeeze = enabled
        self.editor.status = ('Auto-squeeze on import: 4,000 Hz / 4-bit; original kept for Restore.' if enabled else
                              'Auto-squeeze on import off: keep imported sample quality.')

    def sample_range(self, field):
        sample = self.selected_sample()
        if not sample:
            return
        slot = self.sample_index
        def accept(text):
            text = text.strip().lower()
            value = round(float(text[:-2]) * sample['sample_rate'] / 1000) if text.endswith('ms') else int(text)
            self.set_sample_range(slot, field, value)
        self.text_dialog('Sample ' + field + ' frame', str(sample.get(field, 0 if field == 'start' else sample['frames'])),
                         accept, f'Frame index, or milliseconds with ms suffix. {sample["sample_rate"]:,} Hz. End is exclusive.')

    def toggle_sample_normalization(self, when):
        from sidpulse.preferences import save_preferences
        field = 'sample_normalize_' + when
        enabled = not getattr(self, field)
        save_preferences({field: enabled})
        setattr(self, field, enabled)
        self.editor.status = f'Normalize {when} squeezing: {"on" if enabled else "off"}. Applies to future squeezes/imports.'

    def normalize_sample(self):
        from sidpulse.audio.media import sample_data
        try:
            sample = self.selected_sample()
            sample_data(sample)
        except ValueError as exc:
            self.notice('Select a sample', str(exc)); return
        slot = self.sample_index
        def begin():
            self.release_audition()
            self._start_media_job(sample, {'operation': 'normalize'},
                                  assignment={'slot': slot, 'instrument': None, 'operation': 'Normalize'})
        self.dialog = dict(title='Normalize audio?', message='Normalize the marked range to peak level? '
                           'Rate, bit depth and markers stay the same. Constant data is left alone. '
                           'This can be undone; the original remains restorable.', yes=begin)

    def set_sample_range(self, slot, field, value):
        from sidpulse.audio.media import sample_bounds
        bank = dict(self.editor.song.samples)
        key = str(slot) if str(slot) in bank else slot
        sample = dict(bank[key])
        sample[field] = value
        sample_bounds(sample)
        bank[key] = sample
        self.release_audition()
        self.editor.edit('Set sample ' + field, [(('samples',), bank)])

    def sample_drag_event(self, event):
        import pygame as pg
        drag = self.sample_drag
        if drag is None:
            return False
        if event.type in (pg.MOUSEMOTION, pg.MOUSEBUTTONUP):
            value = round((event.pos[0] - drag['rect'].left) * drag['frames'] / max(1, drag['rect'].width - 1))
            lo, hi = (0, drag['end'] - 1) if drag['field'] == 'start' else (drag['start'] + 1, drag['frames'])
            drag[drag['field']] = max(lo, min(hi, value))
        finish = event.type in (pg.KEYDOWN, pg.WINDOWFOCUSLOST, pg.VIDEORESIZE, pg.QUIT) or (
                    event.type == pg.MOUSEBUTTONUP and event.button == 1)
        if finish:
            self.sample_drag = None
            if not (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                self.set_sample_range(drag['slot'], drag['field'], drag[drag['field']])
            return event.type in (pg.KEYDOWN, pg.MOUSEBUTTONUP)
        return event.type == pg.MOUSEMOTION

    def begin_sample_drag(self, data, pos):
        from sidpulse.audio.media import sample_bounds
        sample = self.selected_sample()
        start, end = sample_bounds(sample)
        self.sample_drag = dict(data, slot=self.sample_index, start=start, end=end, frames=sample['frames'])
        import pygame as pg
        self.sample_drag_event(pg.event.Event(pg.MOUSEMOTION, pos=pos))

    def open_sample_squeeze(self):
        from sidpulse.audio.media import sample_data
        try:
            sample_data(self.selected_sample())
        except ValueError as exc:
            self.notice('Select a sample', str(exc)); return
        self.dialog = dict(kind='sample_squeeze', title='Squeeze PCM sample', rate=4000, bits=4, focus=0,
                           normalize_before=self.sample_normalize_before, normalize_after=self.sample_normalize_after)

    def apply_sample_squeeze(self):
        d = self.dialog
        self._start_media_job(self.selected_sample(),
                              dict(operation='squeeze', rate=d['rate'], bits=d['bits'],
                                   normalize_before=d['normalize_before'], normalize_after=d['normalize_after']),
                              assignment={'slot': self.sample_index, 'instrument': None, 'operation': 'Squeeze'})

    def restore_sample(self):
        sample = self.selected_sample()
        if not sample or 'original' not in sample:
            self.editor.status = 'This sample is already the original.'; return
        self.accept_sample(deepcopy(sample['original']), {'slot': self.sample_index, 'instrument': None})
        self.page = 'samples'

    def cancel_media_job(self):
        state = self.dialog
        state['cancelled'] = True
        state['job'].cancel()
        self.dialog = state.get('return_dialog')
        self.editor.status = 'Audio operation cancelled. Existing files and project unchanged.'
        self.sync_file_text_input()

    def poll_media_jobs(self):
        reachable, visited = set(), set()
        view = self.dialog
        while isinstance(view, dict) and id(view) not in visited:
            visited.add(id(view))
            if view.get('kind') == 'media_job':
                reachable.add(id(view))
            view = view.get('return_dialog')
        for state in list(self.media_jobs):
            if id(state) not in reachable or not self.running:
                state['cancelled'] = True
                state['job'].cancel()
            update = state['job'].poll()
            state.update(phase=update.phase, detail=update.detail)
            if not update.done:
                continue
            self.media_jobs.remove(state)
            try:
                if state['cancelled'] or update.cancelled:
                    continue
                if self.dialog is not state:
                    # A notice may temporarily cover the operation. Apply its
                    # result only after that modal has returned to this one.
                    self.media_jobs.append(state)
                    continue
                self.dialog = state.get('return_dialog')
                if update.error:
                    raise ValueError(update.error)
                if state['assignment']:
                    if state['assignment'].get('batch_synthesis'):
                        from sidpulse.ui.batch_synthesis import show_result
                        show_result(self, update.result, state['assignment'], update.source)
                    elif state['assignment'].get('synthesis'):
                        from sidpulse.ui.sample_synthesis import show_result
                        show_result(self, update.result, state['assignment'])
                    else:
                        self.accept_sample(update.result, state['assignment'])
                        self.page = state['return_page']
                else:
                    from sidpulse.export.audio import publish_audio
                    path = publish_audio(update.result['path'], state['target'])
                    self.page = self.browser.return_page
                    self.editor.status = f'Exported {path.name}: {update.result["seconds"]:.2f}s / {update.result["loops"]} extra loops'
                    self.notice('Audio exported', self.editor.status + '. Full song, including PCM; preview mutes/solos are not exported.')
                self.browser.export_result = None
            except (OSError, ValueError) as exc:
                self.notice('Audio operation failed', str(exc), return_dialog=state.get('return_dialog'))
            finally:
                if state not in self.media_jobs:
                    self._cleanup_media_folder(state)
                self.sync_file_text_input()

    def close_media_jobs(self):
        for state in self.media_jobs:
            if state['job'].close():
                self._cleanup_media_folder(state)
        self.media_jobs.clear()

    def accept_sample(self, sample, assignment):
        from sidpulse.project.format import validate
        slot = assignment['slot']
        bank = dict(self.editor.song.samples)
        bank.pop(slot, None)
        bank[str(slot)] = sample
        probe = deepcopy(self.editor.song)
        probe.samples = bank
        validate(probe)  # enforce project limits before mutating the undo history
        updates = [(('samples',), bank)]
        number = assignment.get('instrument')
        if number in self.editor.song.instruments:
            if not self.allow_instrument_edit(number):raise ValueError(self.editor.status)
            updates += [(('instruments', number, 'sample_slot'), slot),
                        (('instruments', number, 'sample_override'), True)]
        operation = assignment.get('operation', 'Import')
        self.editor.edit(f'{operation} sample {slot:02d}', updates)
        self.sample_index = slot
        self.page = self.browser.return_page
        self.editor.status = f'{operation} complete: sample {slot:02d}, {sample["name"]}.'

    def assign_sample(self):
        slot = self.sample_index
        from sidpulse.audio.media import sample_data
        try:
            sample_data(self.editor.song.samples.get(str(slot), self.editor.song.samples.get(slot)))
        except ValueError as exc:
            self.notice('Select a PCM sample', str(exc))
            return
        def accept(text):
            from sidpulse.song.model import Instrument
            number = int(text)
            if not 1 <= number <= 99:
                raise ValueError('Instrument number must be 01..99 (decimal).')
            if not self.allow_instrument_edit(number):raise ValueError(self.editor.status)
            bank = dict(self.editor.song.instruments)
            inst = deepcopy(bank.get(number, Instrument(name=f'Sample {slot:02d}')))
            inst.sample_slot, inst.sample_override = slot, True
            bank[number] = inst
            self.release_audition()
            self.editor.edit(f'Assign sample {slot:02d} to instrument {number:02d}', [(('instruments',), bank)])
            self.editor.instrument = self.instrument_slot = number
            self.change_page('instrument')
            self.instrument_tab = 'sample'
        self.text_dialog('Assign sample to instrument', f'{self.editor.instrument:02d}', accept,
                         '01..99 decimal. Existing SID settings are preserved; an empty instrument slot is created.')

    def sample_setting(self, field):
        slot = self.sample_index
        sample = self.editor.song.samples.get(str(slot), self.editor.song.samples.get(slot))
        if not sample:
            self.import_sample_browser()
            return
        def accept(text):
            value = int(text)
            if not 0 <= value <= 95:
                raise ValueError('Root note must be 0..95: C-4 = 48.')
            bank = deepcopy(self.editor.song.samples)
            key = str(slot) if str(slot) in bank else slot
            bank[key][field] = value
            self.editor.edit('Set sample root note', [(('samples',), bank)])
        self.text_dialog('Sample root note', str(sample.get(field, 48)), accept,
                         'Tracker note 0..95. C-4 = 48 plays at the original pitch and speed.')

    def delete_sample(self):
        slot = self.sample_index
        if str(slot) not in self.editor.song.samples and slot not in self.editor.song.samples:
            return
        def remove():
            bank = dict(self.editor.song.samples)
            bank.pop(str(slot), None); bank.pop(slot, None)
            self.release_audition()
            self.editor.edit(f'Delete sample {slot:02d}', [(('samples',), bank)])
        self.dialog = dict(title='Delete sample?', message=f'Delete sample {slot:02d}? '
                           'Instruments assigned to it stay assigned and become silent until you replace the sample. Undo restores it.', yes=remove)

    def preview_sample(self, token='sample-preview', note=None):
        sample = self.editor.song.samples.get(str(self.sample_index), self.editor.song.samples.get(self.sample_index))
        if not sample:
            self.editor.status = 'Empty sample slot. Import a sample first.'
            return
        if self.audio.playback.status != 'stopped':
            self.editor.status = 'F8 stops the song for sample audition.'
            return
        from sidpulse.audio.media import sample_data
        try:
            sample_data(sample)
            self.audio.send('sample_on', token, sample.get('root_note', 48) if note is None else note, sample)
        except ValueError as exc:
            self.notice('Sample unavailable', str(exc))

    def pcm_instrument_setting(self, field):
        if not self.allow_instrument_edit():return
        number = self.editor.instrument
        inst = self.editor.song.instruments[number]
        if field == 'sample_override':
            self.release_audition()
            self.editor.edit('Toggle PCM override', [(('instruments', number, field), not inst.sample_override)])
            self.choose_instrument_tab('sample' if inst.sample_override else 'general')
            return
        def accept(text):
            value = int(text)
            limit = 99 if field == 'sample_slot' else 100
            if not 0 <= value <= limit:
                raise ValueError(f'Use 0..{limit} decimal.')
            self.release_audition()
            self.editor.edit('Set ' + field.replace('_', ' '), [(('instruments', number, field), value)])
        self.text_dialog(field.replace('_', ' ').title(), str(getattr(inst, field)), accept,
                         'Slot 00 = unassigned; slots and gain are decimal. Gain is 0..100%.')

    def media_action(self, action, value=None):
        if action == 'export_audio': self.begin_audio_export()
        elif action == 'import_sample': self.import_sample_browser()
        elif action == 'import_instrument_sample': self.import_sample_browser(self.editor.instrument)
        elif action == 'open_instrument_sample':
            self.sample_index = max(1,self.editor.song.instruments[self.editor.instrument].sample_slot)
            self.change_page('samples')
        elif action == 'assign_sample': self.assign_sample()
        elif action == 'delete_sample': self.delete_sample()
        elif action == 'preview_sample': self.preview_sample()
        elif action == 'sample_root': self.sample_setting('root_note')
        elif action == 'sample_range': self.sample_range(value)
        elif action == 'sample_squeeze': self.open_sample_squeeze()
        elif action == 'sample_restore': self.restore_sample()
        elif action == 'sample_auto_squeeze': self.toggle_sample_auto_squeeze()
        elif action == 'sample_normalize': self.normalize_sample()
        elif action == 'sample_volume':
            from sidpulse.ui.sample_volume import open_dialog
            open_dialog(self)
        elif action == 'sample_synthesis':
            from sidpulse.ui.sample_synthesis import begin
            begin(self)
        elif action == 'sample_normalization': self.toggle_sample_normalization(value)
        elif action == 'pcm_setting': self.pcm_instrument_setting(value)
        elif action == 'sample_slot_move': self.sample_index = max(1, min(99, self.sample_index + value))
        else: return False
        return True


def handle_job_event(app, event):
    import pygame as pg
    if event.type == pg.KEYDOWN and event.key in (pg.K_ESCAPE, pg.K_RETURN):
        app.cancel_media_job()
    elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
        for rect, action, _ in app.renderer.hits:
            if action == 'cancel_media' and rect.collidepoint(event.pos):
                app.cancel_media_job()
                break


def draw_job(r, app):
    from . import renderer as c
    from .instrument_graphs import button
    r.hits = []
    w = min(72, r.cols - 4); x = (r.cols - w) / 2; y = max(1, (r.lines - 10) / 2)
    r.panel(x, y, w, 10, app.dialog['title'])
    r.text(x + 2, y + 2, app.dialog['phase'], c.YELLOW, w - 4)
    r.text(x + 2, y + 4, app.dialog['detail'], c.TEXT, w - 4)
    button(r, x + 2, y + 7, 20, 'Cancel (Esc)', 'cancel_media')
