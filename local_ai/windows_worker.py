"""Private Windows worker runtime. Experimental until tested on real Windows.

Only the approved code/runtime/source/weights receive read access. One disposable
cache receives write access. No network capabilities are granted. Every AI worker
launch must pass real OS-denial and compute probes, not a cached test-pass flag.
"""
import hashlib
import os
import platform
import queue
import shutil
import socket
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from local_ai import windows_native as native
from local_ai.protocol import read_frame,write_frame
from local_ai.windows_profiles import PROFILES,AMD_TARGETS

ROOT=Path(__file__).resolve().parents[1]
MEMORY_BYTES=12*1024**3
SNAPSHOT_FILES=('worker.py','protocol.py','inference.py','garment_details.py','garment_catalog.py','compute.py','windows_native.py','windows_probe.py')

def require_windows(profile=None):
    if os.name!='nt' or platform.machine().lower() not in ('amd64','x86_64') or sys.maxsize<=2**32:
        raise RuntimeError('The Windows worker requires 64-bit Windows on x64. It cannot be validated on a Mac.')
    if sys.version_info[:2]!=(3,12):raise RuntimeError('The experimental Windows runtime requires Python 3.12.')
    build=sys.getwindowsversion().build
    if build<19041:raise RuntimeError('Windows 10 version 2004 or newer on x64 is required for internal testing.')
    if profile in ('xpu','rocm') and build<22000:raise RuntimeError('AMD/Intel GPU testing requires Windows 11. On Windows 10, explicitly select CPU testing instead.')

def read_reply(process,timeout=60):
    messages=queue.Queue(maxsize=1)
    def reader():
        try:messages.put(read_frame(process.stdout))
        except (OSError,EOFError,ValueError) as error:messages.put(error)
    threading.Thread(target=reader,daemon=True).start()
    try:result=messages.get(timeout=timeout)
    except queue.Empty:raise RuntimeError('Windows worker validation timed out.')
    if isinstance(result,Exception):
        detail=bytes(getattr(process,'probe_log',b'')).decode('utf-8',errors='replace').strip()
        raise RuntimeError('Windows worker validation stopped before reporting success.'+(' Local probe diagnostic: '+detail if detail else '')) from result
    return result

def stop(process):
    if process.poll() is None:process.terminate()
    process.wait(timeout=5);process.close()

class WindowsRuntime:
    def __init__(self,root=ROOT):
        require_windows(os.environ.get('YOURFITTINGROOM_DEVICE'));self.root=Path(root).resolve();self.base=self.root/'.runtime/windows-worker'
        self.code=self.base/'code';self.cache=self.base/'cache';self.grants=[];self.sid=None;self.lock_handle=None;self.children=[];self.closed=False;self.hardware={};self.profile_created=False
        self.name='YourFittingRoom.Worker.'+hashlib.sha256(str(self.root).casefold().encode()).hexdigest()[:24]
        a=native.api()
        try:
            for path in (self.root/'.runtime',self.base,self.code,self.cache):
                if path.exists() and path.lstat().st_file_attributes & 0x400:
                    raise RuntimeError('Windows worker storage must not be a link or junction.')
            self.base.mkdir(parents=True,exist_ok=True)
            self.lock_handle=a.CreateFileW(str(self.base/'runtime.lock'),0xC0000000,0,None,4,0x80,None)
            if self.lock_handle in (None,native.H(-1).value):
                self.lock_handle=None
                raise RuntimeError('The Windows runtime is locked or unavailable. Stop any other companion before testing.')
            self.lock_owned=True
            # A prior crash may leave this app's profile. Stable identity avoids new
            # identities/ACL entries on each restart; no loopback exemptions are set.
            self.sid=native.H();status=a.CreateAppContainerProfile(self.name,'yourFittingRoom inference','Offline local inference',None,0,native.C.byref(self.sid))
            if status==-2147024713:status=a.DeriveAppContainerSidFromAppContainerName(self.name,native.C.byref(self.sid)) # ERROR_ALREADY_EXISTS
            if status<0:raise OSError(status,'Unable to create the restricted Windows worker identity.')
            self.profile_created=True
            self.sid_text=native.sid_string(self.sid)
            # The Windows venv python.exe is a redirector that creates a child.
            # Launch the real base interpreter directly, keeping child creation blocked.
            self.executable=Path(sys.base_prefix)/'python.exe'
            if not self.executable.is_file():raise RuntimeError('The approved base Python executable is missing.')
            if self.code.exists():shutil.rmtree(self.code)
            if self.cache.exists():shutil.rmtree(self.cache)
            (self.code/'local_ai').mkdir(parents=True);(self.code/'security').mkdir();self.cache.mkdir()
            for name in SNAPSHOT_FILES:shutil.copyfile(self.root/'local_ai'/name,self.code/'local_ai'/name)
            shutil.copyfile(self.root/'security/garment-catalog.json',self.code/'security/garment-catalog.json')
            native.label_disposable_cache_low(self.cache)
            # Never grant access to the project root, home folder or selected-photo paths.
            roots=[self.code,Path(sys.base_prefix).resolve(),Path(sys.prefix).resolve()]
            roots.extend(p for p in (self.root/'.runtime/fashn-src/src',self.root/'.runtime/weights') if p.is_dir())
            for path in dict.fromkeys(roots):
                if path in (self.root,self.root.parent,Path.home().resolve()) or not path.is_dir():raise RuntimeError('Unsafe Windows runtime directory. Use the project virtual environment.')
                # Reject links in supplied code/models; inherited ACL grants must not
                # accidentally traverse junctions into unrelated directories.
                for ancestor in (path,*path.parents):
                    if ancestor.lstat().st_file_attributes & 0x400:raise RuntimeError('Approved Windows worker roots must not traverse junctions.')
                    if ancestor==self.root:break
                for entry in path.rglob('*'):
                    if entry.lstat().st_file_attributes & 0x400:raise RuntimeError('Reparse points are not allowed in approved Windows worker directories.')
                self.grants.append(path);native.change_acl(path,self.sid,None);native.change_acl(path,self.sid,0x1200A9)
            self.grants.append(self.cache);native.change_acl(self.cache,self.sid,None);native.change_acl(self.cache,self.sid,0x1301BF)
        except BaseException:
            self.close();raise

    def environment(self,device):
        if device not in PROFILES:raise RuntimeError('Windows compute must be NVIDIA CUDA, AMD ROCm, Intel XPU or explicit CPU testing.')
        require_windows(device)
        buffer=native.C.create_unicode_buffer(32768);length=native.api().GetWindowsDirectoryW(buffer,len(buffer))
        if not 0<length<len(buffer):raise RuntimeError('Unable to locate the trusted Windows system runtime.')
        windows=Path(buffer.value)
        result={'SystemRoot':str(windows),'WINDIR':str(windows),'PATH':str(windows/'System32'),
                'TEMP':str(self.cache),'TMP':str(self.cache),'HOME':str(self.cache),'USERPROFILE':str(self.cache),
                'APPDATA':str(self.cache),'LOCALAPPDATA':str(self.cache),'HF_HOME':str(self.cache/'hf'),
                'MPLCONFIGDIR':str(self.cache/'mpl'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
                'HF_HUB_DISABLE_TELEMETRY':'1','HF_HUB_DISABLE_XET':'1','PYTHONDONTWRITEBYTECODE':'1',
                'YOURFITTINGROOM_WORKER':'1','YOURFITTINGROOM_APP_SID':self.sid_text,'YOURFITTINGROOM_DEVICE':device,
                'YOURFITTINGROOM_DEVICE_INDEX':os.environ.get('YOURFITTINGROOM_DEVICE_INDEX','0'),
                'YOURFITTINGROOM_WEIGHTS':str(self.root/'.runtime/weights'),'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4'}
        index=result['YOURFITTINGROOM_DEVICE_INDEX']
        if not index.isdecimal() or not 0<=int(index)<=15:raise RuntimeError('Invalid configured GPU index.')
        result['SYCL_CACHE_DIR']=str(self.cache/'sycl');result['SYCL_CACHE_PERSISTENT']='1'
        if device=='rocm':
            target=os.environ.get('YOURFITTINGROOM_ROCM_TARGET')
            if target not in AMD_TARGETS[1:]:raise RuntimeError('AMD runtime target is missing. Finish AMD setup first.')
            result['ROCM_SDK_TARGET_FAMILY']=target
        return result

    def spawn(self,module,device='cpu',memory_bytes=MEMORY_BYTES):
        if self.closed:raise RuntimeError('Windows worker runtime is closed.')
        if module not in ('local_ai.windows_probe','local_ai.worker'):raise ValueError('Only fixed worker entry points may be launched.')
        if type(memory_bytes) is not int or not 32*1024**2<=memory_bytes<=MEMORY_BYTES:raise ValueError('Invalid Windows worker memory limit.')
        # -I -S excludes user site, PYTHONPATH, .pth files and working-directory
        # imports. Only these reviewed read-only roots extend the stdlib paths.
        paths=[str(self.code),str(self.root/'.runtime/fashn-src/src'),str(Path(sys.prefix)/'Lib/site-packages')]
        bootstrap=f'import sys,runpy;sys.prefix={str(Path(sys.prefix))!r};sys.exec_prefix=sys.prefix;sys.path[:0]={paths!r};runpy.run_module({module!r},run_name="__main__")'
        process=native.launch([self.executable,'-I','-S','-B','-u','-c',bootstrap],self.environment(device),self.cache,self.sid,memory_bytes)
        process.probe_log=bytearray()
        # Drain diagnostic pipes without retaining images, tokens or user paths.
        def drain():
            try:
                while chunk:=process.stderr.read(4096):
                    # Only the no-photo OS/compute probe may retain a bounded
                    # diagnostic for the local console. Never retain AI logs.
                    if module=='local_ai.windows_probe':
                        process.probe_log.extend(chunk);del process.probe_log[:-4096]
            except (OSError,ValueError):pass
        threading.Thread(target=drain,daemon=True).start();process.diagnostics_drained=True;self.children.append(process);return process

    def probe(self,device=None):
        sentinel=self.base/('outside-'+uuid.uuid4().hex+'.txt');sentinel.write_text('disposable privacy sentinel')
        # Explicitly remove our app SID grant if an earlier test accidentally left one.
        native.change_acl(sentinel,self.sid,None)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));listener.listen(1)
            process=None
            try:
                process=self.spawn('local_ai.windows_probe',device or 'cpu')
                request={'outside':str(sentinel),'port':listener.getsockname()[1]}
                models=self.root/'.runtime/weights'
                if device:
                    request['device']=device
                    candidates=sorted(models.rglob('*.safetensors'))
                    if not candidates:raise RuntimeError('Verified local model files are missing. Finish Windows setup first.')
                    request['models']=str(candidates[0])
                write_frame(process.stdin,request);reply=read_reply(process,timeout=90 if device else 30);process.wait(timeout=5)
                checks=reply.get('checks',{})
                required={'appContainerToken','outsideReadDenied','outsideWriteDenied','codeWriteDenied','cacheWritable','loopbackDenied','internetDenied','childProcessDenied'}
                if device:required.update(('computeAvailable','modelOperatorsAvailable','modelReadAllowed','modelWriteDenied'))
                if set(checks)!=required or any(checks[key] is not True for key in required) or process.returncode!=0:
                    raise RuntimeError('Windows isolation or compute checks failed. AI is disabled; no unrestricted fallback is used.')
                details=reply.get('hardware',{})
                self.hardware={k:v for k,v in details.items() if k in ('torchVersion','device','computeProfile','precision','gpuName','gpuArchitecture','vramBytes','cudaVersion','hipVersion','xpuRuntime') and (isinstance(v,int) or isinstance(v,str) and len(v)<160)}
                return checks
            finally:
                if process:stop(process)
                sentinel.unlink(missing_ok=True)

    def close(self):
        if self.closed:return
        failures=[]
        for child in self.children:
            if child.handle:
                try:stop(child)
                except (OSError,RuntimeError,subprocess.SubprocessError) as error:failures.append(error)
        if failures:raise RuntimeError('Windows worker termination is unconfirmed; stop the companion before retrying.')
        if self.sid:
            for path in reversed(self.grants.copy()):
                if path.exists():
                    try:native.change_acl(path,self.sid,None)
                    except OSError as error:failures.append(error);continue
                self.grants.remove(path)
        # Do not remove shared directories, environments, models or personal files.
        if getattr(self,'lock_owned',False):
            if self.cache.is_dir():
                try:shutil.rmtree(self.cache)
                except OSError as error:failures.append(error)
            if self.profile_created and not failures:
                status=native.api().DeleteAppContainerProfile(self.name)
                if status<0:failures.append(OSError(status,'Windows worker profile cleanup failed.'))
                else:self.profile_created=False
        # Keep the SID, failed grant list and lock for a meaningful cleanup retry.
        if failures:raise RuntimeError('Windows worker stopped, but its private ACL/cache/profile cleanup needs attention.')
        if self.sid:native.api().FreeSid(self.sid);self.sid=None
        self.lock_owned=False
        if self.lock_handle:native.api().CloseHandle(self.lock_handle);self.lock_handle=None
        self.closed=True
