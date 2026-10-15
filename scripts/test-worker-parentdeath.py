"""Real orphan-worker test. Imports AI runtime, sends no photo data."""
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parent_code='''import subprocess,sys,json
from pathlib import Path
from local_ai.isolation import command,worker_environment
from local_ai.protocol import read_frame
root=Path.cwd();cache=root/'.runtime/app-sandbox-prototype/cache'
p=subprocess.Popen(command(cache,script=root/'local_ai/worker.py'),env=worker_environment(cache),cwd=cache,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
print(p.pid,flush=True)
print(json.dumps(read_frame(p.stdout)),flush=True)
sys.stdin.readline()
'''
parent=subprocess.Popen([sys.executable,'-u','-c',parent_code],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
pid=int(parent.stdout.readline())
try:
    ready=json.loads(parent.stdout.readline());assert ready['kind']=='ready',ready
    parent.stdin.write('exit\n');parent.stdin.flush();parent.wait(timeout=5)
    for _ in range(30):
        try:os.kill(pid,0)
        except ProcessLookupError:print('Worker exited after parent termination; no photos were sent.');break
        time.sleep(.1)
    else:raise AssertionError('Orphan worker did not exit')
finally:
    if parent.poll() is None:parent.terminate();parent.wait(timeout=5)
    try:os.kill(pid,15)
    except ProcessLookupError:pass
