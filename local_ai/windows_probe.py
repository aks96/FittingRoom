"""Runs INSIDE the Windows sandbox. Uses disposable sentinels, never user files."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from local_ai.protocol import read_frame,write_frame
from local_ai.windows_native import assert_worker_token
COMPUTE_INFO={}

def denied(operation,codes=(5,10013)):
    try:operation()
    except OSError as error:return getattr(error,'winerror',None) in codes
    return False

def probe(request):
    assert_worker_token(os.environ['YOURFITTINGROOM_APP_SID'])
    checks={'appContainerToken':True,'outsideReadDenied':denied(lambda:Path(request['outside']).read_bytes()),
            'outsideWriteDenied':denied(lambda:Path(request['outside']).write_bytes(b'blocked')),
            'codeWriteDenied':denied(lambda:Path(__file__).open('ab'))}
    scratch=Path(os.environ['TEMP'])/'probe.tmp';scratch.write_bytes(b'local sandbox probe')
    checks['cacheWritable']=scratch.read_bytes()==b'local sandbox probe';scratch.unlink()
    def connect():
        with socket.socket() as client:
            client.settimeout(3);client.connect(('127.0.0.1',request['port']))
    checks['loopbackDenied']=denied(connect)
    def internet():
        with socket.socket() as client:
            client.settimeout(3);client.connect(('192.0.2.1',9)) # Reserved documentation address; sends no image data.
    checks['internetDenied']=denied(internet)
    def child():
        result=subprocess.Popen([sys.executable,'-I','-S','-c','pass'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        result.kill();result.communicate(timeout=5)
    checks['childProcessDenied']=denied(child,codes=(5,367)) # Access denied / ERROR_CHILD_PROCESS_BLOCKED.
    if request.get('models'):
        model=Path(request['models']);checks['modelReadAllowed']=bool(model.open('rb').read(1))
        checks['modelWriteDenied']=denied(lambda:model.open('ab'))
    if request.get('device'):
        import torch
        from local_ai.compute import probe_compute
        result,info=probe_compute(torch,request['device'],int(os.environ.get('YOURFITTINGROOM_DEVICE_INDEX','0')))
        checks.update(result);COMPUTE_INFO.update(info)
    return checks

if __name__=='__main__':
    request=read_frame(sys.stdin.buffer);mode=request.get('mode','probe')
    if mode=='probe':write_frame(sys.stdout.buffer,{'checks':probe(request),'hardware':COMPUTE_INFO})
    elif mode=='sleep':
        assert_worker_token(os.environ['YOURFITTINGROOM_APP_SID'])
        write_frame(sys.stdout.buffer,{'waiting':True});time.sleep(300)
    elif mode=='crash':os._exit(23)
    elif mode=='memory':
        assert_worker_token(os.environ['YOURFITTINGROOM_APP_SID'])
        chunks=[]
        try:
            while True:chunks.append(bytearray(8*1024*1024))
        except MemoryError:write_frame(sys.stdout.buffer,{'memoryDenied':True})
    else:raise ValueError('Unknown test mode.')
