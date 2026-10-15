"""Offline inference worker: JSON pipe input/output; no listener or shell API."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_ai.protocol import read_frame,write_frame
output=sys.stdout.buffer
sys.stdout=sys.stderr # model diagnostics never enter the structured output pipe
if os.environ.get('YOURFITTINGROOM_WORKER')!='1':raise RuntimeError('Use the local supervisor to start the worker.')
if os.name=='nt':
    from local_ai.windows_native import assert_worker_token
    assert_worker_token(os.environ.get('YOURFITTINGROOM_APP_SID',''))
else:
    import resource
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024*1024,64*1024*1024))
    resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
    resource.setrlimit(resource.RLIMIT_NPROC,(0,0))
import threading,time
parent=os.getppid()
if parent==1:raise RuntimeError('The local supervisor must remain running.')
def parent_watch():
    while True:
        time.sleep(.5)
        if os.getppid()!=parent:os._exit(0) # Stop even if the broker crashes during a model call.
threading.Thread(target=parent_watch,daemon=True).start()
from local_ai import inference
write_frame(output,{'kind':'ready','device':inference.DEVICE_LABEL})
while True:
    try:message=read_frame(sys.stdin.buffer)
    except EOFError:break
    try:
        if message.get('operation')=='analyze':
            write_frame(output,{'kind':'result','analysis':inference.analyze_image(message['image'])})
        elif message.get('operation')=='generate':
            result=inference.generate(message['payload'],lambda stage:write_frame(output,{'kind':'stage','stage':stage}))
            write_frame(output,{'kind':'result','image':result});result=None
        else:raise ValueError('Unsupported worker operation.')
    except Exception as error:
        clear=str(error) if isinstance(error,ValueError) and str(error).startswith('A clear person could not be detected.') else 'Local processing failed. Check the selected images; no sample was substituted.'
        if isinstance(error,(MemoryError,getattr(inference.torch,'OutOfMemoryError',MemoryError))):
            clear='Local processing ran out of memory. Close other memory-heavy apps or test a device with more available memory. No sample or cloud fallback was used.'
        elif os.name=='nt' and not isinstance(error,ValueError):
            clear='Local processing failed on the selected Windows backend. Run Test Windows.cmd and check device memory; no sample or cloud fallback was used.'
        write_frame(output,{'kind':'error','error':clear})
    finally:message=None
