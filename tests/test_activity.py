"""Real trigger/state telemetry with a register-recorder SID; no SDL required."""
from copy import deepcopy
from dataclasses import replace
import pytest
from sidpulse.audio.activity import ActivitySnapshot,InstrumentActivity
from sidpulse.ui.activity import ActivityLights
from sidpulse.playback.voices import VoicePrograms,Audition
from sidpulse.playback.sequencer import Sequencer
from sidpulse.export.psid import RecordingSID
from sidpulse.sid.backend_residfp import set_filter
from sidpulse.song.model import Song,Pattern,Cell,Instrument,OFF,CUT


def rig():
    sid=RecordingSID();set_filter(sid,Song().filter)
    activity=InstrumentActivity();programs=VoicePrograms(sid,activity)
    return sid,activity,programs


def snap(sid,activity,programs,**kw):return activity.snapshot(programs,sid.registers,**kw)


@pytest.mark.parametrize('voice',range(3))
def test_actual_slot_not_selected_cursor_or_instrument_object(voice):
    sid,a,p=rig();p.row(voice,Cell(48,13),Instrument(),13)
    result=snap(sid,a,p)
    assert result.active==(13,) and result.triggers==((13,1),)
    assert p.voices[voice].instrument_id==13
    # Same cloned instrument/name does not make another bank row active.
    p.row((voice+1)%3,Cell(52,17),Instrument(),17)
    assert snap(sid,a,p).active==(13,17)


def test_instrument_only_and_portamento_rows_do_not_forge_triggers():
    sid,a,p=rig();inst=Instrument()
    p.row(0,Cell(48,1),inst,1);p.tick(0);before=dict(a.counts)
    p.row(0,Cell(instrument=2),replace(inst,name='New memory'),2);p.tick(0)
    assert p.voices[0].instrument_id==1 and a.counts==before
    p.row(0,Cell(60,2,'G',3),inst,2);p.tick(1)
    assert p.voices[0].instrument_id==1 and a.counts==before


def test_delayed_note_identity_and_gate_are_published_only_when_it_fires():
    sid,a,p=rig();p.row(0,Cell(48,7,'S',0xD2),Instrument(),7)
    p.tick(0);p.tick(1);assert snap(sid,a,p).triggers==()
    p.tick(2);assert snap(sid,a,p).active==(7,) and snap(sid,a,p).triggers==((7,1),)


@pytest.mark.parametrize('mode',[OFF,CUT])
def test_release_cut_remove_gated_activity_but_keep_brief_trigger_history(mode):
    sid,a,p=rig();p.row(0,Cell(48,7),Instrument(),7);p.tick(0)
    p.row(0,Cell(mode),Instrument(),7)
    s=snap(sid,a,p);assert not s.active and s.triggers==((7,1),)


def test_retrigger_flashes_again_without_new_instrument():
    sid,a,p=rig();p.row(0,Cell(48,5,'Q',2),Instrument(),5)
    p.tick(0);p.tick(1);p.tick(2)
    assert snap(sid,a,p).triggers==((5,2),) and p.voices[0].instrument_id==5


def test_two_fast_instruments_survive_one_gui_poll():
    sid,a,p=rig();p.trigger(0,48,Instrument(),6);p.trigger(0,52,Instrument(),11)
    s=snap(sid,a,p);assert s.active==(11,) and len(s.triggers)==2
    assert ActivityLights().levels(s,now=1)=={6:1.,11:1.}


def test_same_instrument_on_two_voices_is_aggregated_without_false_extinction():
    sid,a,p=rig()
    for v in (0,1):p.trigger(v,48,Instrument(),8)
    p.release(0,True)
    assert snap(sid,a,p).active==(8,)
    assert not snap(sid,a,p,muted=(False,True,False)).active


def test_muted_and_master_volume_zero_do_not_show_bright_dots():
    sid,a,p=rig();p.trigger(0,48,Instrument(),2)
    lights=ActivityLights();s=snap(sid,a,p,muted=(True,False,False))
    assert lights.levels(s,now=1)=={}
    # Unmuting a held voice is steady activity, not another note trigger.
    s=snap(sid,a,p);assert lights.levels(s,now=1.1)=={2:.55}
    sid.write(24,0);assert not snap(sid,a,p).enabled
    assert lights.levels(snap(sid,a,p),now=1.2)=={}


def test_missing_or_invalid_ids_do_not_light_unrelated_slots():
    sid,a,p=rig()
    for value in (None,0,-1,100,True,'1'):
        p.trigger(0,48,Instrument(),value)
        assert not snap(sid,a,p).triggers and not snap(sid,a,p).active
    assert a.serial==0


def test_no_future_lookahead_notes_and_loop_counts_still_increment():
    sid=RecordingSID();a=InstrumentActivity();song=Song(speed=2,tempo=125)
    song.patterns={0:Pattern(rows=[[Cell(48,1),Cell(),Cell()]])};song.orders=[0]
    seq=Sequencer(sid,a);seq.start(song)
    seq._boundary();assert a.serial==1  # lookahead crosses the upcoming loop
    seq.frames=int(seq.next_tick);seq._boundary();assert a.serial==1
    seq.frames=int(seq.next_tick);seq._boundary();assert a.serial==2
    assert seq.loops==1


def test_observer_does_not_change_any_register_write():
    song=Song(speed=3);song.orders=[0]
    song.patterns={0:Pattern(rows=[
        [Cell(48,1,'S',0xD1),Cell(24,2),Cell(60,3)],
        [Cell(52,2,'G',3),Cell(effect='Q',parameter=1),Cell(OFF)],
        [Cell(55,3),Cell(CUT),Cell(64,1)]])}
    traces=[]
    for observer in (None,InstrumentActivity()):
        sid=RecordingSID();seq=Sequencer(sid,observer);seq.start(deepcopy(song),loop=False)
        while seq.status=='playing':
            seq._boundary();seq.frames=int(seq.next_tick)
        traces.append(sid.events)
    assert traces[0]==traces[1]


def test_audition_id_and_generation_reset_are_independent_of_playback():
    sid,a,p=rig();audition=Audition(sid,activity=a)
    audition.trigger(1,60,Instrument(),12)
    assert snap(sid,a,audition).active==(12,)
    a.reset();assert a.generation==1 and not a.counts


def test_snapshot_is_immutable_and_storage_is_bounded():
    sid,a,p=rig()
    for _ in range(2):
        for v in range(3):
            for number in range(1,100):a.note_on(v,number)
    assert len(a.counts)==297
    s=snap(sid,a,p)
    a.reset();assert len(s.triggers)==99 and len(a.counts)==0
    with pytest.raises(AttributeError):s.enabled=False


def test_held_state_and_150ms_flash_decay():
    lights=ActivityLights();s=ActivitySnapshot(0,True,(3,),((3,1),),(3,))
    assert lights.levels(s,now=0)=={3:1.}
    assert lights.levels(s,now=1)=={3:.55}
    off=replace(s,active=())
    assert lights.levels(off,now=1.1)=={}
    s=replace(s,triggers=((3,2),))
    assert lights.levels(s,now=2)=={3:1.}
    off=replace(s,active=())
    assert lights.levels(off,now=2.075)[3]==pytest.approx(.5)
    assert lights.levels(off,now=2.16)=={}


def test_pause_panic_and_reset_cannot_leave_stale_indicators():
    lights=ActivityLights();s=ActivitySnapshot(1,True,(3,),((3,1),),(3,))
    lights.levels(s,now=0)
    assert lights.levels(replace(s,enabled=False),now=.02)=={}
    assert lights.levels(s,now=.04)=={3:.55}
    assert lights.levels(ActivitySnapshot(2,False),now=.05)=={}
    assert lights.levels(ActivitySnapshot(3,True,(7,),((7,2),),(7,)),now=.1)=={7:1.}
