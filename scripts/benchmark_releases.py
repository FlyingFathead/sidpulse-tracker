"""Matched SIDpulse release benchmark. Runs trials serially, never edits projects."""
import argparse
from dataclasses import replace
import hashlib
import importlib.metadata
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time


def stats(values):
    a=sorted(values)
    return {'mean':statistics.mean(a),'median':statistics.median(a),
            'p95':a[math.ceil(.95*len(a))-1],'maximum':a[-1],'n':len(a)}


def init(repo,cpus):
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
    sys.path.insert(0,str(Path(repo).resolve()))
    if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,set(cpus))


def audio(task):
    from sidpulse.project.format import load
    from sidpulse.sid.backend_residfp import ReSIDfpBackend
    from sidpulse.playback.sequencer import Sequencer
    from sidpulse.audio.activity import InstrumentActivity
    from sidpulse.audio.engine import AudioEngine
    from sidpulse.audio.output import OutputConditioner
    song=load(task['song'])[0]
    sid=ReSIDfpBackend(song.sid_model,clock=song.clock,voice_scopes=task['scopes'])
    sid.render(48000)
    activity=InstrumentActivity()
    try:
        from sidpulse.audio.monitor import InstrumentMonitor
        monitor=InstrumentMonitor(sid)
        seq=Sequencer(sid,activity,monitor.note_on)
    except ModuleNotFoundError:
        seq=Sequencer(sid,activity)
    seq.start(song)
    conditioner=OutputConditioner();conditioner.target=1
    meter=AudioEngine(song,enabled=False)
    frames=task['frames'];blocks=math.ceil(task['seconds']*48000/frames)
    stages={key:[] for key in ('sid','conditioning','meter_scopes_activity','total')}
    def block():
        t0=time.perf_counter_ns();pcm=seq.render(frames)
        t1=time.perf_counter_ns();pcm=conditioner.process(pcm)
        t2=time.perf_counter_ns();meter.measure(pcm)
        if task['scopes']:sid.voice_scopes.snapshot()
        activity.snapshot(seq.programs,sid.registers,getattr(sid,'muted',(False,)*3))
        t3=time.perf_counter_ns()
        return (t1-t0,t2-t1,t3-t2,t3-t0)
    for _ in range(16):block()
    cpu=time.process_time_ns();wall=time.perf_counter_ns()
    for _ in range(blocks):
        for key,value in zip(stages,block()):stages[key].append(value/1e6)
    cpu=(time.process_time_ns()-cpu)/1e9;wall=(time.perf_counter_ns()-wall)/1e9
    duration=blocks*frames/48000;budget=frames/48
    return {'cpu_seconds':cpu,'wall_seconds':wall,'audio_seconds':duration,
            'cpu_ms_per_block':cpu*1000/blocks,'core_percent':100*cpu/duration,
            'block_budget_ms':budget,'over_budget_blocks':sum(t>budget for t in stages['total']),
            'stages_ms':{k:stats(v) for k,v in stages.items()},
            'last_pattern':seq.pattern,'last_row':seq.row}


def gui(task):
    import pygame as pg
    from sidpulse.project.format import load
    from sidpulse.app import App
    from sidpulse.audio.activity import ActivitySnapshot
    song=load(task['song'])[0]
    app=App(song,audio=False,size=tuple(task['size']))
    try:
        app.change_page(task['page']);app.channel_visualizers=task.get('scopes',True)
        if not task.get('bank_buttons',True):
            if hasattr(app,'instrument_monitor_buttons'):
                app.instrument_monitor_buttons=False
            else:
                # Ablation for releases before this setting existed.
                app.renderer.bank_monitor_buttons=lambda *args: None
        if task.get('recording'):
            app.open_automation_recording();app.set_recording_channel(1);app.toggle_pulse_recording()
            if task.get('recording_parameter'):app.set_recording_parameter(task['recording_parameter'])
        app.audio.ready=True;app.audio.active=(0,1,2)
        app.audio.activity=ActivitySnapshot(1,True,(2,23,24),((2,1),(23,2),(24,3)),(2,23,24))
        app.audio.voice_waveforms=tuple(tuple(math.sin((i+v)*math.pi/16)*.65 for i in range(128)) for v in range(3))
        app.audio.waveform=tuple(math.sin(i*math.pi/8)*.5 for i in range(64))
        state=replace(app.audio.playback,status='playing',pattern=app.editor.pattern_id,
                      notes=(50,26,57),instruments=(23,2,24))
        def frame(index):
            row=(index//4)%len(app.editor.pattern.rows)
            if task.get('scrolling'):
                number=1+(index//2)%99
                if task['page']=='instrument':
                    app.instrument_slot=number
                    if number in app.editor.song.instruments:app.editor.instrument=number
                else:app.sample_index=number
            app.editor.row=row;app.audio.playback=replace(state,row=row,frames=index*800)
            app.renderer.render(app);pg.display.flip()
        for i in range(32):frame(i)
        wall=[];cpu=time.process_time_ns()
        for i in range(task['iterations']):
            t=time.perf_counter_ns();frame(i);wall.append((time.perf_counter_ns()-t)/1e6)
        cpu=(time.process_time_ns()-cpu)/1e6
        return {'cpu_ms_per_frame':cpu/task['iterations'],'frame_work_ms':stats(wall),
                'core_percent_at_60fps':cpu/task['iterations']*6,
                'over_16_67ms_frames':sum(t>1000/60 for t in wall)}
    finally:app.close()


def proc_cpu(pid):
    data=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()
    return (int(data[11])+int(data[12]))/os.sysconf('SC_CLK_TCK')


def live(task):
    import pygame as pg
    from sidpulse.project.format import load
    from sidpulse.app import App
    song=load(task['song'])[0]
    app=App(song,audio=True,size=tuple(task['size']),audio_buffer=task['frames'])
    try:
        engine=app.audio
        deadline=time.monotonic()+10
        while not engine.ready and not engine.error and time.monotonic()<deadline:time.sleep(.005)
        if not engine.ready:raise RuntimeError(engine.error or 'Audio startup timeout')
        app.change_page(task['page']);app.channel_visualizers=task['scopes']
        engine.send('play',song,'song',0,0,None);engine.send('scopes',task['scopes'])
        app.scopes_visible=task['page']=='info' and task['scopes']
        if task.get('recording'):
            app.open_automation_recording();app.set_recording_channel(1);app.toggle_pulse_recording()
            if task.get('recording_parameter'):app.set_recording_parameter(task['recording_parameter'])
        frame_index=0
        clock=pg.time.Clock()
        def frame():
            nonlocal frame_index
            for event in pg.event.get():app.handle(event)
            app.sync_audio();app.renderer.render(app);pg.display.flip()
            if task.get('recording'):
                rect,data=next((r,v) for r,a,v in app.renderer.hits if a=='automation_slider')
                fraction=.2+.6*(1-abs((frame_index%120)/60-1));frame_index+=1
                pos=(int(rect.left+rect.width*fraction),rect.centery)
                if app.pulse_take is None:app.begin_pulse_drag(data,pos)
                elif not app.pulse_take['pending']:app.update_pulse_drag(pos)
        warm=time.monotonic()+1
        while time.monotonic()<warm:frame();clock.tick(60)
        engine.send('reset_stats')
        warm=time.monotonic()+.15
        while time.monotonic()<warm:frame();clock.tick(60)
        child=next(p for p in mp.active_children() if p.name=='sidpulse-audio')
        a0=proc_cpu(child.pid);u0=time.process_time();start=time.perf_counter()
        times=[];loads=[]
        while time.perf_counter()-start<task['seconds']:
            t=time.perf_counter();frame();times.append((time.perf_counter()-t)*1000)
            loads.append(engine.render_load*100);clock.tick(60)
        elapsed=time.perf_counter()-start
        result={'elapsed_seconds':elapsed,'ui_main_core_percent':(time.process_time()-u0)/elapsed*100,
            'audio_process_core_percent':(proc_cpu(child.pid)-a0)/elapsed*100,
            'ui_frame_work_ms':stats(times),'reported_render_budget_percent':stats(loads),
            'achieved_ui_fps':len(times)/elapsed,'gaps':engine.underruns,
            'missing_frames':engine.missing_frames,'late_callbacks':engine.late_callbacks,
            'over_budget_blocks':engine.over_budget,'maximum_callback_ms':engine.max_callback_interval*1000,
            'callback_count':engine.callback_count,'error':engine.error}
        if task.get('recording'):
            result['committed_takes']=len(app.editor.history.undo_stack)
            result['in_progress_rows']=len(engine.pulse_capture.rows) if engine.pulse_capture else 0
        if result['error']:raise RuntimeError(result['error'])
        return result
    finally:app.close()


def worker(task):
    init(task['repo'],task['cpus'])
    with tempfile.TemporaryDirectory(prefix='sidpulse-benchmark-') as config:
        os.environ['SIDPULSE_CONFIG_HOME']=config
        result={'audio':audio,'gui':gui,'live':live}[task['kind']](task)
    from sidpulse import __version__
    return {'version':__version__,**result}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker')
    parser.add_argument('--baseline');parser.add_argument('--candidate');parser.add_argument('--input')
    parser.add_argument('--out');parser.add_argument('--repetitions',type=int,default=5)
    parser.add_argument('--phases',default='audio,gui,live')
    args=parser.parse_args()
    if args.worker:
        task=json.loads(Path(args.worker).read_text());print(json.dumps(worker(task)));return
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    source=Path(args.input).resolve();original=source.read_bytes();document=json.loads(original)
    count={key:0 for key in ('attack','decay','sustain','release','pulse_width')}
    for pattern in document['song']['patterns'].values():
        for row in pattern['rows']:
            for cell in row:
                for key in count:
                    if cell.get(key) is not None:count[key]+=1
                    cell.pop(key,None)
    document['format_version']=6
    common=out/'v5-without-row-automation.sidpulse';common.write_text(json.dumps(document,indent=2)+'\n')
    inputs=out/'v5-original.sidpulse';inputs.write_bytes(original)
    env={'python':platform.python_version(),'pygame':importlib.metadata.version('pygame-ce'),
         'pyresidfp':importlib.metadata.version('pyresidfp'),'platform':platform.system()+' '+platform.machine(),
         'affinity_available':sorted(os.sched_getaffinity(0)),'drivers':'SDL dummy audio/video',
         'input_sha256':hashlib.sha256(original).hexdigest(),'removed_row_commands':count,
         'common_input_sha256':hashlib.sha256(common.read_bytes()).hexdigest()}
    (out/'environment.json').write_text(json.dumps(env,indent=2)+'\n')
    cpus=env['affinity_available'];versions=[('baseline',args.baseline),('candidate',args.candidate)]
    first=Path(args.baseline).resolve()/'examples/first-light.sidpulse'
    def launch(label,repo,case,repetition):
        task={'repo':str(Path(repo).resolve()),'repetition':repetition,'label':label,'cpus':cpus[:2] if case['kind']=='live' else cpus[:1],**case}
        taskfile=out/'task.json';taskfile.write_text(json.dumps(task))
        run=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(taskfile)],capture_output=True,text=True)
        if run.returncode:raise RuntimeError(run.stderr+'\n'+run.stdout)
        result=json.loads(run.stdout.strip().splitlines()[-1]);record={k:v for k,v in task.items() if k not in ('repo','song')}
        record['song']=Path(task['song']).name;record.update(result)
        with (out/'results.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
        metric=result.get('cpu_ms_per_block',result.get('cpu_ms_per_frame',result.get('audio_process_core_percent')))
        print(f"{task['kind']} {label} {case['case']} rep {repetition}: {metric:.3f}",flush=True)
    phases=args.phases.split(',')
    for repetition in range(args.repetitions):
        order=versions if repetition%2==0 else versions[::-1]
        if 'audio' in phases:
            for scopes in (False,True):
                for frames in (2048,512):
                    case={'kind':'audio','case':f'v5-common-{frames}-scopes-{int(scopes)}','song':str(common),'seconds':10,'frames':frames,'scopes':scopes}
                    for label,repo in order:launch(label,repo,case,repetition)
                case={'kind':'audio','case':f'first-light-2048-scopes-{int(scopes)}','song':str(first),'seconds':10,'frames':2048,'scopes':scopes}
                for label,repo in order:launch(label,repo,case,repetition)
                case={'kind':'audio','case':f'v5-automation-2048-scopes-{int(scopes)}','song':str(inputs),'seconds':10,'frames':2048,'scopes':scopes}
                launch('candidate',args.candidate,case,repetition)
        if 'gui' in phases:
            for size in ((960,1080),(1280,900)):
                for page in ('pattern','instrument','info'):
                    case={'kind':'gui','case':f'{page}-{size[0]}x{size[1]}','song':str(common),'size':size,'page':page,'scopes':True,'iterations':200}
                    for label,repo in order:launch(label,repo,case,repetition)
                case={'kind':'gui','case':f'info-scopes-off-{size[0]}x{size[1]}','song':str(common),'size':size,'page':'info','scopes':False,'iterations':200}
                launch('candidate',args.candidate,case,repetition)
        if 'buttons' in phases:
            for page in ('instrument', 'samples'):
                for enabled in ((True, False) if repetition % 2 == 0 else (False, True)):
                    case={'kind':'gui','case':f'bank-buttons-{page}-{int(enabled)}','song':str(inputs),
                          'size':(960,1080),'page':page,'scopes':True,'bank_buttons':enabled,'iterations':400}
                    for label,repo in order:launch(label,repo,case,repetition)
        if 'recording' in phases:
            case={'kind':'gui','case':'recording-view-960x1080','song':str(inputs),'size':(960,1080),
                  'page':'instrument','scopes':False,'recording':True,'iterations':200}
            launch('candidate',args.candidate,case,repetition)
        if 'scrolling' in phases:
            for page in ('instrument','samples'):
                case={'kind':'gui','case':f'scrolling-{page}-960x1080','song':str(inputs),'size':(960,1080),
                      'page':page,'scopes':False,'scrolling':True,'iterations':400}
                for label,repo in order:launch(label,repo,case,repetition)
        if 'live512' in phases:
            case={'kind':'live','case':'v5-common-info-512','song':str(common),
                  'size':(960,1080),'page':'info','scopes':True,'frames':512,'seconds':15}
            for label,repo in order:launch(label,repo,case,repetition)
    if 'live' in phases:
        for page,frames in (('pattern',2048),('info',2048),('info',512)):
            case={'kind':'live','case':f'v5-common-{page}-{frames}','song':str(common),'size':(960,1080),'page':page,'scopes':page=='info','frames':frames,'seconds':15}
            for label,repo in versions:launch(label,repo,case,0)
        for scopes in (True,False):
            case={'kind':'live','case':f'v5-automation-info-scopes-{int(scopes)}','song':str(inputs),'size':(960,1080),'page':'info','scopes':scopes,'frames':2048,'seconds':15}
            launch('candidate',args.candidate,case,0)
    if 'recording' in phases:
        case={'kind':'live','case':'v5-recording-pw-channel-2','song':str(inputs),'size':(960,1080),
              'page':'instrument','scopes':False,'recording':True,'frames':2048,'seconds':15}
        launch('candidate',args.candidate,case,0)
    assert source.read_bytes()==original
    (out/'task.json').unlink(missing_ok=True)
    print('All requested phases completed; original input unchanged.',flush=True)


if __name__=='__main__':main()
