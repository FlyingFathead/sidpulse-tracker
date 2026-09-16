"""Song-loop UI flag/transport semantics, without pygame or a native SID."""
from copy import deepcopy
import pytest
from sidpulse.commands.editor import Editor
from sidpulse.song.model import Song,Pattern,Cell
from sidpulse.project.format import save,load
from sidpulse.export.psid import RecordingSID,compile_song
from sidpulse.playback.sequencer import Sequencer


def song(loop):
    s=Song(speed=2,tempo=125,export_config={'loop':loop,'released':'Loop test'})
    s.patterns={0:Pattern(rows=[[Cell(48,1),Cell(),Cell()]]),1:Pattern(rows=[[Cell(50,1),Cell(),Cell()]])}
    s.orders=[0,1];return s


def step(seq,n):
    for _ in range(n):seq._boundary();seq.frames=int(seq.next_tick)


@pytest.mark.parametrize('flag',[True,False])
def test_setter_only_changes_saved_loop_flag_and_undo_redo(tmp_path,flag):
    ed=Editor(song(flag));before=deepcopy(ed.song)
    ed.set_song_loop();after=deepcopy(before);after.export_config['loop']=not flag
    assert ed.song==after and ed.dirty
    assert load(save(tmp_path/'loop.sidpulse',ed.song))[0]==after
    ed.history.undo(ed.song);assert ed.song==before
    ed.history.redo(ed.song);assert ed.song==after
    rev=ed.history.revision;ed.set_song_loop(not flag);assert ed.history.revision==rev


def test_missing_key_is_default_on_but_is_not_silently_persisted():
    s=song(True);s.export_config.pop('loop');ed=Editor(s)
    ed.set_song_loop(True);assert 'loop' not in s.export_config and not ed.dirty
    ed.set_song_loop();assert s.export_config['loop'] is False
    ed.history.undo(s);assert 'loop' not in s.export_config


@pytest.mark.parametrize('old,new',[(True,False),(False,True)])
@pytest.mark.parametrize('clock',['PAL','NTSC'])
def test_live_last_row_toggle_uses_new_value(old,new,clock):
    s=song(old);s.clock=clock;seq=Sequencer(RecordingSID(clock));seq.start(s)
    step(seq,3);assert seq.order==1 and seq.tick==0
    edited=deepcopy(s);edited.export_config['loop']=new;seq.update_song(edited);step(seq,2)
    assert seq.status==('playing' if new else 'stopped') and seq.loops==int(new)
    if new:assert seq.order==0 and seq.song.export_config['loop'] is True


@pytest.mark.parametrize('flag',[True,False])
def test_pattern_loop_independent_and_one_pass_override(flag):
    seq=Sequencer(RecordingSID());seq.start(song(flag),mode='pattern',order=1)
    step(seq,7);assert seq.status=='playing' and seq.pattern==1 and seq.loops==3
    seq=Sequencer(RecordingSID());seq.start(song(flag),loop=False)
    step(seq,5);assert seq.status=='stopped'
    assert compile_song(song(flag)).seconds==pytest.approx(.08)
