"""Offline Windows validation entry point. No personal images, downloads or API.

Use --compute to add a real GPU/CPU probe after setup. Full image-quality testing
is a separate deliberate UI step; a small compute probe cannot certify try-on.
"""
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_ai import windows_native as native
from local_ai.windows_worker import WindowsRuntime,read_reply,stop,require_windows
from local_ai.protocol import write_frame
from local_ai.windows_profiles import PROFILES

def crash_parent():
    """Disposable broker; the real broker and its pairing state are untouched."""
    runtime=WindowsRuntime();worker=runtime.spawn('local_ai.windows_probe')
    write_frame(worker.stdin,{'mode':'sleep'});assert read_reply(worker,30).get('waiting') is True
    print(json.dumps({'pid':worker.pid}),flush=True)
    sys.stdin.readline();os._exit(0) # Deliberately skip cleanup to exercise kill-on-close.

def parent_death_test():
    parent=subprocess.Popen([sys.executable,'-I',str(Path(__file__)),'--crash-parent'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,cwd=ROOT)
    handle=None
    try:
        import queue,threading
        messages=queue.Queue(maxsize=1)
        threading.Thread(target=lambda:messages.put(parent.stdout.readline()),daemon=True).start()
        try:line=messages.get(timeout=60)
        except queue.Empty:raise RuntimeError('Disposable Windows broker startup timed out.')
        if not line:raise RuntimeError('Disposable Windows broker could not start.')
        pid=json.loads(line)['pid'];a=native.api()
        handle=a.OpenProcess(0x100000|0x1000,False,pid);native.checked(handle,'observe disposable worker exit')
        # Hold the process handle before parent exits, avoiding a recycled PID check.
        parent.stdin.write('crash\n');parent.stdin.flush();parent.wait(timeout=5)
        return a.WaitForSingleObject(handle,5000)==0
    finally:
        if parent.poll() is None:parent.kill();parent.wait(timeout=5)
        for stream in (parent.stdin,parent.stdout):stream.close()
        if handle:native.api().CloseHandle(handle)

def validate(compute=None):
    require_windows(compute)
    report={'status':'running','platform':'Windows','windowsVersion':platform.version(),'architecture':platform.machine(),
            'python':platform.python_version(),'compute':compute or 'not tested','checks':{},
            'generationTested':False,'imageQualityTested':False,'releaseApproved':False}
    source=hashlib.sha256()
    from local_ai.windows_worker import SNAPSHOT_FILES
    for name in sorted(set(SNAPSHOT_FILES)|{'windows_worker.py','windows_validate.py','windows_start.py','windows_profiles.py','rocm_bootstrap.py','supervisor.py'}):
        source.update(name.encode());source.update((ROOT/'local_ai'/name).read_bytes())
    source.update((ROOT/'security/garment-catalog.json').read_bytes());source.update((ROOT/'security/windows-compute.json').read_bytes());report['workerSourceSha256']=source.hexdigest()
    folder=ROOT/'.runtime/windows-validation';folder.mkdir(parents=True,exist_ok=True)
    output=folder/'report.json';started=time.monotonic();runtime=None
    try:
        try:
            from local_ai.windows_hardware import inventory
            report['displayAdapters']=inventory()
        except (RuntimeError,ValueError,OSError,subprocess.SubprocessError):report['displayAdapters']='unavailable'
        report['stage']='isolation-and-compute';runtime=WindowsRuntime();report['checks'].update(runtime.probe(compute));report['hardware']=runtime.hardware
        report['stage']='cancellation'
        process=runtime.spawn('local_ai.windows_probe');write_frame(process.stdin,{'mode':'sleep'})
        assert read_reply(process,30).get('waiting') is True
        stop(process);report['checks']['cancellationStopsWorker']=process.returncode is not None
        report['stage']='worker-crash';process=runtime.spawn('local_ai.windows_probe');write_frame(process.stdin,{'mode':'crash'})
        report['checks']['crashObserved']=process.wait(timeout=10)==23;process.close()
        # A bounded allocation in a dedicated 256 MB job exercises the OS cap.
        # It cannot allocate an entire machine's RAM before the cap takes effect.
        report['stage']='memory-limit';process=runtime.spawn('local_ai.windows_probe',memory_bytes=256*1024**2)
        write_frame(process.stdin,{'mode':'memory'})
        report['checks']['memoryLimitEnforced']=read_reply(process,30).get('memoryDenied') is True
        process.wait(timeout=5);process.close()
        runtime.close();runtime=None
        report['checks']['cacheRemoved']=not (ROOT/'.runtime/windows-worker/cache').exists()
        report['stage']='broker-death';report['checks']['brokerDeathStopsWorker']=parent_death_test()
        # Recover app-owned cache/profile/ACL remnants of the deliberate crash.
        report['stage']='crash-cleanup';runtime=WindowsRuntime();runtime.close();runtime=None
        report['checks']['crashCleanupRecovered']=not (ROOT/'.runtime/windows-worker/cache').exists()
        if not all(report['checks'].values()):raise RuntimeError('One or more Windows validation checks failed.')
        report['status']='passed';report['stage']='complete'
    except (OSError,RuntimeError,ValueError,AssertionError,subprocess.SubprocessError) as error:
        report['status']='failed';report['failureType']=type(error).__name__
        # Keep arbitrary exception text (which can contain private paths) out of
        # the report. The console gives a short local-only diagnostic instead.
        print('Windows validation failed:',error,file=sys.stderr)
    finally:
        if runtime:
            try:runtime.close()
            except (OSError,RuntimeError) as error:
                report['status']='failed';report['checks']['cleanupConfirmed']=False
                print('Windows cleanup requires attention:',error,file=sys.stderr)
        report['elapsedSeconds']=round(time.monotonic()-started,2)
        output.write_text(json.dumps(report,indent=2)+'\n')
        print('Local report: .runtime/windows-validation/report.json',flush=True)
        print('No personal images were used. Windows generation and visual quality still require testing.',flush=True)
    return 0 if report['status']=='passed' else 1

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--compute',choices=list(PROFILES));parser.add_argument('--crash-parent',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.crash_parent:crash_parent();return 0
    return validate(args.compute)

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,RuntimeError) as error:print(error,file=sys.stderr);sys.exit(1)
