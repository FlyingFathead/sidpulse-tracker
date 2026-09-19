"""Channel automation controls and one undoable edit per slider gesture."""
import time
from sidpulse.playback.automation_parameters import PARAMETERS


class PulseRecordingActions:
    @property
    def recording_info(self):
        return PARAMETERS[self.automation_parameter]

    @property
    def inline_recording_visible(self):
        return self.page == 'instrument' and self.instrument_tab == 'automation'

    def open_automation_recording(self):
        self.finish_instrument_drag()
        self.release_audition()
        self.automation_state.pop('slider_keys',None)
        self.automation_state.pop('keyboard_touch',None)
        if self.automation_display == 1:
            self.dialog = {'kind': 'automation_recording', 'title': 'Record automation', 'focus': 4}
        else:
            self.dialog = None
            if self.page != 'instrument':self.change_page('instrument')
            self.instrument_tab = 'automation'
            self.instrument_focus = 'automation'

    def automation_event(self, event):
        from sidpulse.ui.automation_input import handle_event
        return handle_event(self, event)

    def close_automation_recording(self):
        self.finish_instrument_drag()
        self.automation_state.pop('slider_keys',None)
        self.automation_state.pop('keyboard_touch',None)
        if self.dialog and self.dialog.get('kind') == 'automation_recording':
            self.dialog = None
        elif self.inline_recording_visible:
            self.instrument_tab = 'general'
            self.instrument_focus = 'list'

    def toggle_pulse_recording(self):
        if self.pulse_record_armed:
            self.disarm_pulse_recording()
            return
        self.finish_instrument_drag()
        if self.pulse_take:
            self.editor.status = 'Finishing the current automation take.'
            return
        self.pulse_record_armed = not self.pulse_record_armed
        self.editor.status = f'{self.recording_info[1]} armed on CH {self.pulse_record_voice+1}: drag or use slider arrow keys while playing.'

    def disarm_pulse_recording(self):
        self.pulse_record_armed = False
        self.finish_instrument_drag()
        if self.pulse_take and not self.pulse_take['pending']:
            self.finish_pulse_drag()
        self.editor.status = (f'CH {self.pulse_record_voice+1} automation disarmed.'
                              + (' Finishing the current take.' if self.pulse_take else ''))

    def set_recording_channel(self, voice):
        if voice in range(3) and not self.pulse_take:
            self.pulse_record_voice = voice
            self.editor.status = f'Automation destination: CH {voice+1} {self.recording_info[1]}'

    def set_recording_parameter(self, field):
        if field in PARAMETERS and not self.pulse_take:
            self.automation_values[self.automation_parameter] = self.pulse_record_value
            self.automation_parameter = field
            self.pulse_record_value = self.automation_values[field]

    def begin_pulse_drag(self, data, pos):
        value = self.pulse_slider_value(data, pos)
        self.pulse_record_value = value
        if not self.pulse_record_armed or not self.audio.ready or self.audio.playback.status != 'playing':
            self.instrument_drag = {**data, 'automation_preview': True}
        else:self.begin_pulse_value(value, data)

    def begin_pulse_value(self, value, data):
        if not self.pulse_record_armed:
            self.editor.status = 'Arm the destination channel before recording.'
            return
        if not self.audio.ready or self.audio.playback.status != 'playing':
            self.editor.status = 'Recording needs playback. Use F5 or F6, then adjust the slider.'
            return
        self.pulse_record_serial += 1
        value = max(0, min(self.recording_info[2], value))
        self.pulse_take = {'token': self.pulse_record_serial, 'value': value, 'field': self.automation_parameter,
                           'voice': self.pulse_record_voice, 'pending': False, 'cancel': False}
        self.pulse_record_value = self.pulse_take['value']
        self.instrument_drag = {**data, 'recording': True}
        self.audio.send('pulse_record_start', self.pulse_take['token'], self.pulse_take['voice'], self.pulse_take['value'], self.automation_parameter)
        self.editor.status = f"Recording {self.recording_info[1]} on CH {self.pulse_take['voice'] + 1}; release to keep, Esc to cancel."

    @staticmethod
    def pulse_slider_value(data, pos):
        rect = data['rect']
        maximum = data.get('maximum', 4095)
        return max(0, min(maximum, round((pos[0] - rect.x) * maximum / max(1, rect.width - 1))))

    def update_pulse_drag(self, pos):
        if self.instrument_drag.get('keyboard'):return
        self.update_pulse_value(self.pulse_slider_value(self.instrument_drag, pos))

    def update_pulse_value(self, value):
        if self.pulse_take and not self.pulse_take['pending']:
            if value != self.pulse_take['value']:
                self.pulse_take['value'] = value
                self.pulse_record_value = value
                self.audio.send('pulse_record_value', self.pulse_take['token'], value)

    def adjust_recording_value(self, delta):
        value = max(0, min(self.recording_info[2], self.pulse_record_value + delta))
        self.pulse_record_value = value
        if self.pulse_record_armed and self.audio.ready and self.audio.playback.status == 'playing':
            if not self.pulse_take:
                self.begin_pulse_value(value, {'keyboard': True, 'kind': 'keyboard', 'field': self.automation_parameter})
            else:
                self.update_pulse_value(value)

    def finish_pulse_drag(self, cancel=False):
        self.instrument_drag = None
        if self.pulse_take and not self.pulse_take['pending']:
            self.pulse_take.update(pending=True, cancel=cancel, deadline=time.monotonic() + 3)
            self.audio.send('pulse_record_end', self.pulse_take['token'], cancel)

    def sync_pulse_recording(self):
        take = self.pulse_take
        if take is None:
            return
        snapshot = self.audio.pulse_capture
        if snapshot is not None and snapshot.token == take['token']:
            take['snapshot'] = snapshot
        else:
            snapshot = take.get('snapshot')
        failed = bool(self.audio.error) or (take['pending'] and time.monotonic() > take['deadline'])
        if not failed and not (snapshot and snapshot.done):
            return
        self.pulse_take = None
        if self.instrument_drag and self.instrument_drag.get('recording'):
            self.instrument_drag = None
        if failed:
            self.audio.send('panic')
        cancelled = take['cancel'] or (snapshot and snapshot.cancelled)
        if snapshot and not cancelled:
            ed = self.editor
            pattern = ed.song.patterns.get(snapshot.pattern)
            field = snapshot.field
            updates = [(("patterns", snapshot.pattern, "rows", row, snapshot.voice, field), value)
                       for row, value in snapshot.rows if pattern and row < len(pattern.rows)]
            ed.edit(f'Record {PARAMETERS[field][1]} on CH {snapshot.voice + 1} ({len(updates)} rows)', updates)
            if not updates:
                ed.status = snapshot.reason or 'No automation rows recorded.'
            elif snapshot.reason == 'Pattern pass complete':
                ed.status += ' | Pattern pass complete; release and drag again for another pass.'
        if cancelled:
            self.editor.status = 'Automation recording cancelled; pattern and instrument unchanged.'
        if failed:
            self.editor.status = 'Automation recording interrupted; recovered acknowledged rows. Check audio status.'
        # Also restores the worker snapshot after cancel/no-op takes.
        self.audio.send('update_song', self.editor.song)
        self.last_audio_revision = self.editor.history.revision
        deferred, self.pulse_deferred_events = self.pulse_deferred_events, []
        for event in deferred:
            self.handle(event)
