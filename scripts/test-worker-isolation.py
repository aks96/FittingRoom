"""Verify real OS denials using disposable fixtures, never personal files."""
import json,subprocess,tempfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from local_ai.isolation import command,worker_environment
cache=ROOT/'.runtime/app-sandbox-prototype/cache';cache.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='yfr-denied-',dir=ROOT/'.runtime') as denied:
    secret=Path(denied)/'fixture.txt';secret.write_text('disposable isolation fixture')
    code='''import json,socket,subprocess,resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_NPROC,(0,0))
result={}
try:Path(SECRET).read_text();result['unrelated_read_denied']=False
except PermissionError:result['unrelated_read_denied']=True
try:Path(SECRET).write_text('bad');result['unrelated_write_denied']=False
except PermissionError:result['unrelated_write_denied']=True
try:
 s=socket.socket();s.settimeout(1);s.connect(('192.0.2.1',9));result['internet_denied']=False
except PermissionError:result['internet_denied']=True
except OSError:result['internet_denied']=False
try:subprocess.run(['/bin/sh','-c','true'],check=True);result['shell_denied']=False
except PermissionError:result['shell_denied']=True
except OSError:result['shell_denied']=True
Path(CACHE).joinpath('allowed.txt').write_text('own temporary cache')
result['own_cache_allowed']=True
print(json.dumps(result))
'''.replace('SECRET',repr(str(secret.resolve()))).replace('CACHE',repr(str(cache.resolve())))
    result=subprocess.run(command(cache,code=code),env=worker_environment(cache),cwd=cache,capture_output=True,text=True,timeout=15)
    if result.returncode:print(result.stderr);sys.exit(result.returncode)
    report=json.loads(result.stdout);print(json.dumps(report));assert all(report.values()),report
