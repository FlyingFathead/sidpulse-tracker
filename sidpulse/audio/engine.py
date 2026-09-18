"""A bounded SDL PCM queue fed by an isolated native-emulation worker.

A sample-clocked sequencer and audition share one native SID register
interface. An SDL callback transports finished PCM; it never synthesizes the SID.
"""
from copy import deepcopy
from array import array
import math
from queue import Empty, SimpleQueue
from threading import Event, Thread
from sidpulse.preferences import DEFAULT_BUFFER
from sidpulse.audio.activity import InstrumentActivity, ActivitySnapshot

from sidpulse.playback.voices import Audition
from sidpulse.sid.backend_residfp import ReSIDfpBackend, note_on, note_off, set_filter


class VoiceAllocator:
    def __init__(self):
        self.held = {}  # token -> (voice, age)
        self.age = 0

    def acquire(self, token, preferred=None):
        if token in self.held:
            return self.held[token][0]
        used = {v for v, _ in self.held.values()}
        if preferred is not None and preferred not in range(3):
            raise ValueError("SID voice must be 0, 1 or 2")
        free = preferred if preferred is not None else next((v for v in range(3) if v not in used), None)
        if preferred is not None:
            for held, (voice, _) in list(self.held.items()):
                if voice == preferred:
                    del self.held[held]
        if free is None:
            oldest = min(self.held, key=lambda k: self.held[k][1])
            free, _ = self.held.pop(oldest)
        self.age += 1
        self.held[token] = (free, self.age)
        return free

    def release(self, token):
        value = self.held.pop(token, None)
        return None if value is None else value[0]


class AudioEngine:
    def __init__(self, song, enabled=True, buffer_frames=DEFAULT_BUFFER, output_device=None):
        from sidpulse.playback.sequencer import PlaybackState
        from sidpulse.preferences import BUFFERS
        if buffer_frames not in BUFFERS:
            raise ValueError("Unsupported audio buffer size")
        self.commands = SimpleQueue()
        self.stop_event = Event()
        self.thread = None
        self.error = None
        self.active = ()
        self.activity = ActivitySnapshot()
        self.levels = (0, 0, 0)
        self.underruns = self.late_wakes = self.over_budget = 0
        self.missing_frames = self.late_callbacks = self.callback_count = 0
        self.max_callback_interval = 0.0
        self.render_load = self.peak_render_load = 0.0
        self.peak = self.rms = 0.0
        self.waveform = (0.0,) * 64
        self.voice_waveforms = ((0.0,) * 128,) * 3
        self.ready = False
        self.muted = (False, False, False)
        self.description = "Audio disabled"
        self.buffer_frames = buffer_frames
        self.output_device = output_device
        self.output_devices = ()
        self.output_notice = self.output_list_error = ''
        self.output_result = self.test_result = None
        self.test_active = False
        self.request_serial = 0
        self.playback = PlaybackState()
        self.startup = deepcopy(song)
        if enabled:
            from sidpulse.audio.process import bridge
            self.thread = Thread(target=bridge, args=(self,), name="sidpulse-audio-control", daemon=True)
            self.thread.start()

    def send(self, name, *values):
        if self.thread and not self.stop_event.is_set():
            self.commands.put((name, deepcopy(values)))

    def request(self, name, *values):
        self.request_serial += 1
        self.send(name, self.request_serial, *values)
        return self.request_serial

    def configure(self, song):
        self.send("configure", song.sid_model, song.filter, song.clock)

    def close(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)

    def measure(self, pcm):
        samples = array("h", pcm)
        if samples:
            mean = sum(samples) / len(samples)
            centered = [(s - mean) / 32768 for s in samples]
            self.peak = min(1., max(abs(s) for s in centered))
            self.rms = min(1., math.sqrt(sum(s * s for s in centered) / len(centered)))
            self.waveform = tuple(centered[::max(1, len(samples) // 64)])

    def _run(self):
        import time
        from sidpulse.audio.routing import AudioOutput
        from sidpulse.audio.output import OutputConditioner
        from sidpulse.playback.sequencer import Sequencer
        from sidpulse.preferences import BUFFERS
        channel = output = None
        try:
            sid = ReSIDfpBackend(self.startup.sid_model, clock=self.startup.clock)
            set_filter(sid, self.startup.filter)
            # Settle power-up DC before opening the output. This is host startup,
            # not tracker time; first note still starts at sequencer frame zero.
            sid.render(48000)
            activity = InstrumentActivity()
            sequencer = Sequencer(sid, activity)
            audition = Audition(sid, self.startup.tempo, activity)
            conditioner = OutputConditioner()
            output = AudioOutput(self.buffer_frames, self.output_device)
            channel = output.channel
            def publish_output():
                self.output_device = output.device_name
                self.output_devices = output.devices
                self.output_notice = output.notice
                self.output_list_error = output.list_error
                self.buffer_frames = output.channel.frames
                self.test_active = output.testing
                for field, counter in (('underruns', 'gaps'), ('missing_frames', 'missing_frames'),
                                       ('callback_count', 'callback_count'), ('late_callbacks', 'late_callbacks'),
                                       ('max_callback_interval', 'max_callback_interval')):
                    setattr(self, field, getattr(output.channel, counter, 0))
                self.description = f"reSIDfp / 48 kHz / {self.buffer_frames} samples"
            publish_output()
            allocator = VoiceAllocator()
            audition_sources = {}
            audition_filter = deepcopy(self.startup.filter)
            self.ready = True
            last_wake = time.perf_counter()
            while not self.stop_event.is_set():
                now = time.perf_counter()
                if now - last_wake > self.buffer_frames / 48000:
                    self.late_wakes += 1
                last_wake = now
                for _ in range(256):
                    try:
                        name, values = self.commands.get_nowait()
                    except Empty:
                        break
                    if output.testing and name in ('on', 'play', 'pause', 'panic', 'configure', 'buffer', 'output'):
                        output.stop_test()
                        channel = output.channel
                        publish_output()
                        last_wake = time.perf_counter()
                    if name == 'refresh_outputs':
                        output.refresh()
                        publish_output()
                    elif name in ('output', 'test_output'):
                        request, frames, device = values
                        error = ''
                        try:
                            if name == 'output':
                                previous_channel = output.channel
                                output.switch(frames, device)
                                if output.channel is not previous_channel:
                                    conditioner.gain = 0.0  # retain the existing reopen fade-in
                            else:
                                output.start_test(frames, device)
                        except Exception as exc:
                            if output.channel.device is None:
                                raise  # even the default failed; report unavailable audio
                            error = str(exc)
                        channel = output.channel
                        publish_output()
                        result = (request, not bool(error), error)
                        if name == 'output':
                            self.output_result = result
                        else:
                            self.test_result = result
                        last_wake = time.perf_counter()
                    elif name == 'stop_test':
                        output.stop_test()
                        channel = output.channel
                        publish_output()
                        last_wake = time.perf_counter()
                    elif name == "on" and sequencer.status == "stopped":
                        token, note, instrument, *preferred = values
                        if not allocator.held:set_filter(sid,audition_filter)
                        voice = allocator.acquire(token, preferred[0] if preferred else None)
                        number = preferred[1] if len(preferred)>1 else None
                        audition.trigger(voice, note, instrument, number)
                        audition_sources[voice] = number
                        conditioner.target = 1.0
                    elif name == "scopes":
                        sid.enable_scopes(bool(values[0]))
                        if not values[0]:
                            self.voice_waveforms = ((0.0,) * 128,) * 3
                    elif name == "monitor":
                        self.muted = tuple(values[0])
                        sid.set_muted(self.muted)
                    elif name == "off":
                        voice = allocator.release(values[0])
                        if voice is not None:
                            audition.release(voice)
                    elif name == "release_audition":
                        for voice, _ in allocator.held.values():
                            audition.release(voice)
                        allocator.held.clear()
                    elif name == "play":
                        activity.reset()
                        audition_sources.clear()
                        song, mode, order, row, pattern = values
                        audition_filter = deepcopy(song.filter)
                        channel.stop()
                        allocator.held.clear()
                        sid.set_model(song.sid_model)
                        sid.set_clock(song.clock)
                        sid.reset()
                        set_filter(sid, song.filter)
                        sid.set_muted(self.muted)
                        sid.render(48000)
                        conditioner = OutputConditioner()
                        conditioner.target = 1.0
                        audition = Audition(sid, audition.tempo, activity)
                        audition.tempo = song.tempo
                        sequencer.start(song, mode, order, row, pattern)
                        last_wake = time.perf_counter()
                    elif name == "pause":
                        sequencer.pause()
                        if sequencer.status == "paused":
                            channel.pause()
                        else:
                            channel.unpause()
                    elif name == "update_song":
                        sequencer.update_song(values[0])
                        audition_filter = deepcopy(values[0].filter)
                        audition.tempo = values[0].tempo
                        if sequencer.status=="stopped":
                            for voice,_ in allocator.held.values():
                                number=audition_sources.get(voice)
                                inst=values[0].instruments.get(number)
                                if inst is not None:
                                    audition.voices[voice].instrument=deepcopy(inst)
                                    audition.write(voice*7+5,inst.attack<<4|inst.decay)
                                    audition.write(voice*7+6,inst.sustain<<4|inst.release)
                    elif name == "panic":
                        activity.reset()
                        audition_sources.clear()
                        sequencer.stop()
                        audition = Audition(sid, audition.tempo, activity)
                        allocator.held.clear()
                        channel.unpause()
                        conditioner.target = 0.0
                    elif name == "buffer" and values[0] in BUFFERS:
                        # Reopen without resetting musical state; keep pause state.
                        try:
                            output.switch(values[0], output.device_name)
                        except Exception as exc:
                            if output.channel.device is None:
                                raise
                            output.notice = f'Audio setting unchanged: {exc}'
                        channel = output.channel
                        publish_output()
                        conditioner.gain = 0.0
                        last_wake = time.perf_counter()
                    elif name == "reset_stats":
                        channel.reset_stats()
                        self.underruns = self.late_wakes = self.over_budget = 0
                        self.missing_frames = self.late_callbacks = self.callback_count = 0
                        self.max_callback_interval = 0.0
                        self.render_load = self.peak_render_load = 0.0
                    elif name == "configure":
                        model, filter_state, clock = values
                        audition_filter = deepcopy(filter_state)
                        if sid.model != model or sid.clock_name != clock:
                            activity.reset()
                            audition_sources.clear()
                            sequencer.stop()
                            allocator.held.clear()
                            channel.stop()
                            sid.set_model(model)
                            sid.set_clock(clock)
                            audition = Audition(sid, audition.tempo, activity)
                            set_filter(sid, filter_state)
                            sid.render(48000)
                            conditioner = OutputConditioner()
                        set_filter(sid, filter_state)
                        sid.set_muted(self.muted)
                if output.testing:
                    output.pump_test()
                    channel = output.channel
                    publish_output()
                    last_wake = time.perf_counter()
                    self.stop_event.wait(.001)
                    continue
                if channel.callback_error is not None:
                    raise RuntimeError('Audio callback failed') from channel.callback_error
                self.playback = sequencer.state
                self.activity = activity.snapshot(
                    sequencer.programs if sequencer.status != "stopped" else audition,
                    sid.registers, self.muted,
                    enabled=sequencer.status != "paused" and conditioner.target > 0)
                self.active = tuple(v for v in range(3) if sid.registers[v * 7 + 4] & 1
                                    and sid.registers[v * 7 + 4] & 0xF0)
                self.levels = tuple(int(v in self.active) for v in range(3))
                if sequencer.status != "paused":
                    channel.expect_audio = sequencer.status == "playing" or bool(allocator.held)
                    self.underruns = channel.gaps
                    self.missing_frames = getattr(channel, 'missing_frames', 0)
                    self.late_callbacks = getattr(channel, 'late_callbacks', 0)
                    self.callback_count = getattr(channel, 'callback_count', 0)
                    self.max_callback_interval = getattr(channel, 'max_callback_interval', 0.0)
                    if channel.needs_block():
                        began = time.perf_counter()
                        was_playing = sequencer.status == "playing"
                        pcm = sequencer.render(self.buffer_frames) if was_playing else audition.render(self.buffer_frames)
                        if was_playing and sequencer.status == "stopped":
                            conditioner.target = 0.0
                        pcm = conditioner.process(pcm)
                        self.measure(pcm)
                        if sid.voice_scopes is not None:
                            self.voice_waveforms = sid.voice_scopes.snapshot()
                        ratio = (time.perf_counter() - began) / (self.buffer_frames / 48000)
                        self.render_load = .9 * self.render_load + .1 * ratio
                        self.peak_render_load = max(self.peak_render_load, ratio)
                        self.over_budget += int(ratio > 1.0)
                        channel.write(pcm)
                        self.playback = sequencer.state
                        self.activity = activity.snapshot(
                            sequencer.programs if sequencer.status != "stopped" else audition,
                            sid.registers, self.muted,
                            enabled=sequencer.status != "paused" and conditioner.target > 0)
                        continue  # prime both queue slots before waiting
                self.stop_event.wait(.001)
        except Exception as exc:
            from sidpulse.diagnostics import record_exception
            record_exception('Audio worker failed', exc)
            self.error = f"{type(exc).__name__}: {exc}"
            self.description = "Audio unavailable; editing remains available"
        finally:
            self.activity = ActivitySnapshot()
            self.ready = False
            self.test_active = False
            if output is not None:
                try: output.close()
                except Exception as exc:
                    from sidpulse.diagnostics import record_exception
                    record_exception('Audio device close failed', exc)
                    self.error = f'{type(exc).__name__}: {exc}'
