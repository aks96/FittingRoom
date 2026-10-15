"""Windows-only AppContainer and Job Object primitives (internal test candidate).

No shell, elevation, firewall exceptions or unrestricted subprocess fallback.
Win32 bindings load lazily so policy/structure tests also run on the Mac.
"""
import ctypes as C
import functools
import os
import subprocess
import time

D=C.c_uint32; H=C.c_void_p; S=C.c_size_t; W=C.c_wchar_p; B=C.c_int32

class SecurityAttributes(C.Structure):
    _fields_=[('length',D),('descriptor',H),('inherit',B)]
class StartupInfo(C.Structure):
    _fields_=[('cb',D),('reserved',W),('desktop',W),('title',W),
              ('x',D),('y',D),('width',D),('height',D),('xchars',D),('ychars',D),
              ('fill',D),('flags',D),('show',C.c_uint16),('reserved_size',C.c_uint16),
              ('reserved_bytes',H),('stdin',H),('stdout',H),('stderr',H)]
class StartupInfoEx(C.Structure):
    _fields_=[('info',StartupInfo),('attributes',H)]
class ProcessInformation(C.Structure):
    _fields_=[('process',H),('thread',H),('pid',D),('tid',D)]
class SecurityCapabilities(C.Structure):
    _fields_=[('sid',H),('capabilities',H),('count',D),('reserved',D)]
class BasicLimit(C.Structure):
    _fields_=[('process_time',C.c_int64),('job_time',C.c_int64),('flags',D),
              ('min_working_set',S),('max_working_set',S),('active_processes',D),
              ('affinity',S),('priority',D),('scheduling',D)]
class ExtendedLimit(C.Structure):
    _fields_=[('basic',BasicLimit),('io',C.c_uint64*6),('process_memory',S),
              ('job_memory',S),('peak_process_memory',S),('peak_job_memory',S)]
class Trustee(C.Structure):
    _fields_=[('multiple',H),('operation',D),('form',D),('type',D),('name',H)]
class ExplicitAccess(C.Structure):
    _fields_=[('permissions',D),('mode',D),('inheritance',D),('trustee',Trustee)]

@functools.lru_cache(maxsize=1)
def api():
    if os.name!='nt':raise RuntimeError('Windows AppContainer tests must run on Windows; no fallback is used.')
    class API:pass
    a=API();a.k=C.WinDLL('kernel32',use_last_error=True);a.u=C.WinDLL('userenv',use_last_error=True);a.s=C.WinDLL('advapi32',use_last_error=True)
    def bind(dll,name,result,*args):
        f=getattr(dll,name);f.restype=result;f.argtypes=list(args);setattr(a,name,f)
    bind(a.k,'CloseHandle',B,H);bind(a.k,'LocalFree',H,H)
    bind(a.k,'CreateFileW',H,W,D,D,H,D,D,H)
    bind(a.k,'OpenProcess',H,D,B,D)
    bind(a.k,'WaitForSingleObject',D,H,D);bind(a.k,'GetCurrentProcess',H)
    bind(a.k,'CreateJobObjectW',H,H,W)
    bind(a.k,'SetInformationJobObject',B,H,D,H,D)
    bind(a.k,'AssignProcessToJobObject',B,H,H);bind(a.k,'TerminateJobObject',B,H,D)
    bind(a.k,'TerminateProcess',B,H,D);bind(a.k,'GetExitCodeProcess',B,H,C.POINTER(D))
    bind(a.k,'IsProcessInJob',B,H,H,C.POINTER(B));bind(a.k,'ResumeThread',D,H)
    bind(a.k,'CreatePipe',B,C.POINTER(H),C.POINTER(H),C.POINTER(SecurityAttributes),D)
    bind(a.k,'SetHandleInformation',B,H,D,D)
    bind(a.k,'InitializeProcThreadAttributeList',B,H,D,D,C.POINTER(S))
    bind(a.k,'UpdateProcThreadAttribute',B,H,D,S,H,S,H,H)
    bind(a.k,'DeleteProcThreadAttributeList',None,H)
    bind(a.k,'CreateProcessW',B,W,W,H,H,B,D,H,W,C.POINTER(StartupInfoEx),C.POINTER(ProcessInformation))
    bind(a.k,'GetWindowsDirectoryW',D,W,D)
    bind(a.u,'CreateAppContainerProfile',C.c_int32,W,W,W,H,D,C.POINTER(H))
    bind(a.u,'DeriveAppContainerSidFromAppContainerName',C.c_int32,W,C.POINTER(H))
    bind(a.u,'DeleteAppContainerProfile',C.c_int32,W)
    bind(a.s,'FreeSid',H,H)
    bind(a.s,'ConvertSidToStringSidW',B,H,C.POINTER(W))
    bind(a.s,'GetNamedSecurityInfoW',D,W,D,D,H,H,C.POINTER(H),H,C.POINTER(H))
    bind(a.s,'SetNamedSecurityInfoW',D,W,D,D,H,H,H,H)
    bind(a.s,'SetEntriesInAclW',D,D,C.POINTER(ExplicitAccess),H,C.POINTER(H))
    bind(a.s,'ConvertStringSecurityDescriptorToSecurityDescriptorW',B,W,D,C.POINTER(H),H)
    bind(a.s,'GetSecurityDescriptorSacl',B,H,C.POINTER(B),C.POINTER(H),C.POINTER(B))
    bind(a.s,'OpenProcessToken',B,H,D,C.POINTER(H))
    bind(a.s,'GetTokenInformation',B,H,D,H,D,C.POINTER(D))
    return a

def checked(ok,operation):
    if not ok:raise OSError(getattr(C,'get_last_error',lambda:0)(),f'Windows worker: {operation} failed. No unrestricted fallback.')

def sid_string(sid):
    a=api();out=W();checked(a.ConvertSidToStringSidW(sid,C.byref(out)),'SID lookup')
    try:return out.value
    finally:a.LocalFree(C.cast(out,H))

def assert_worker_token(expected):
    """Check the effective OS token, not merely environment flags."""
    a=api();token=H();checked(a.OpenProcessToken(a.GetCurrentProcess(),8,C.byref(token)),'open worker token')
    def info(kind):
        size=D();a.GetTokenInformation(token,kind,None,0,C.byref(size))
        if not size.value:raise RuntimeError('Windows worker token inspection failed.')
        out=C.create_string_buffer(size.value);checked(a.GetTokenInformation(token,kind,out,size,C.byref(size)),'inspect worker token');return out
    try:
        if D.from_buffer(info(29)).value!=1:raise RuntimeError('Windows worker is not in an AppContainer.')
        if D.from_buffer(info(30)).value!=0:raise RuntimeError('Windows worker unexpectedly has capabilities.')
        # Keep token buffer alive while Windows reads its embedded SID pointer.
        sid_info=info(31);actual=H.from_buffer(sid_info).value
        if sid_string(actual)!=expected:raise RuntimeError('Unexpected Windows worker identity.')
        assigned=B();checked(a.IsProcessInJob(a.GetCurrentProcess(),None,C.byref(assigned)),'inspect worker job')
        if not assigned.value:raise RuntimeError('Windows worker is not resource-limited by a job.')
    finally:a.CloseHandle(token)

def change_acl(path,sid,permissions=None):
    """Change only this private AppContainer SID's ACE; preserve other ACL entries."""
    a=api();old=H();descriptor=H();new=H()
    status=a.GetNamedSecurityInfoW(str(path),1,4,None,None,C.byref(old),None,C.byref(descriptor))
    if status:raise OSError(status,'Unable to inspect an approved worker directory ACL.')
    entry=ExplicitAccess(permissions or 0,4 if permissions is None else 1,3,Trustee(None,0,0,0,sid))
    try:
        status=a.SetEntriesInAclW(1,C.byref(entry),old,C.byref(new))
        if status:raise OSError(status,'Unable to prepare the private worker ACL.')
        status=a.SetNamedSecurityInfoW(str(path),1,4,None,None,new,None)
        if status:raise OSError(status,'Unable to apply the private worker ACL. Administrator access will not be requested.')
    finally:
        if new:a.LocalFree(new)
        if descriptor:a.LocalFree(descriptor)

def label_disposable_cache_low(path):
    """AppContainer low integrity can write only the app-owned disposable cache."""
    a=api();descriptor=H();sacl=H();present=B();default=B()
    checked(a.ConvertStringSecurityDescriptorToSecurityDescriptorW('S:(ML;OICI;NW;;;LW)',1,C.byref(descriptor),None),'create cache label')
    try:
        checked(a.GetSecurityDescriptorSacl(descriptor,C.byref(present),C.byref(sacl),C.byref(default)),'read cache label')
        status=a.SetNamedSecurityInfoW(str(path),1,0x10,None,None,None,sacl)
        if status:raise OSError(status,'Unable to label the disposable Windows worker cache.')
    finally:a.LocalFree(descriptor)

class RestrictedProcess:
    """Popen-compatible subset; the broker alone owns the kill-on-close Job handle."""
    def __init__(self,process,job,pid,streams):
        self.handle=process;self.job=job;self.pid=pid;self.stdin,self.stdout,self.stderr=streams
        self.returncode=None
    def poll(self):
        if self.returncode is not None:return self.returncode
        result=api().WaitForSingleObject(self.handle,0)
        if result==0:
            status=D();checked(api().GetExitCodeProcess(self.handle,C.byref(status)),'read exit status');self.returncode=status.value
        elif result!=258:checked(False,'wait for worker')
        return self.returncode
    def wait(self,timeout=None):
        end=None if timeout is None else time.monotonic()+timeout
        while self.poll() is None:
            if end is not None and time.monotonic()>=end:raise subprocess.TimeoutExpired('restricted Windows worker',timeout)
            time.sleep(.02)
        return self.returncode
    def terminate(self):
        if self.poll() is None:checked(api().TerminateJobObject(self.job,1),'terminate worker job')
    kill=terminate
    def close(self):
        # Never release an unconfirmed live process as though cleanup succeeded.
        if self.poll() is None:raise RuntimeError('Windows worker must stop before its handles are released.')
        for stream in (self.stdin,self.stdout,self.stderr):stream.close()
        if self.job:api().CloseHandle(self.job);self.job=None
        if self.handle:api().CloseHandle(self.handle);self.handle=None

def launch(args,env,cache,sid,memory_bytes):
    """Create suspended, attach limits, then resume. Failed setup always kills it."""
    import msvcrt
    a=api();handles=[];streams=[];job=None;pi=ProcessInformation();attributes=None;initialized=False
    sa=SecurityAttributes(C.sizeof(SecurityAttributes),None,1)
    try:
        pipes=[]
        for i in range(3):
            read=H();write=H();checked(a.CreatePipe(C.byref(read),C.byref(write),C.byref(sa),0),'create private pipe')
            handles.extend([read.value,write.value]);child,parent=(read.value,write.value) if i==0 else (write.value,read.value)
            checked(a.SetHandleInformation(parent,1,0),'limit inherited handles');pipes.append((child,parent))
        size=S();a.InitializeProcThreadAttributeList(None,3,0,C.byref(size))
        attributes=C.create_string_buffer(size.value);checked(a.InitializeProcThreadAttributeList(attributes,3,0,C.byref(size)),'initialize launch attributes');initialized=True
        caps=SecurityCapabilities(sid,None,0,0);inherit=(H*3)(*[p[0] for p in pipes]);child_policy=D(1)
        for key,value in ((0x20009,caps),(0x20002,inherit),(0x2000E,child_policy)):
            checked(a.UpdateProcThreadAttribute(attributes,0,key,C.byref(value),C.sizeof(value),None,None),'restrict worker launch')
        job=a.CreateJobObjectW(None,None);checked(job,'create worker job')
        limits=ExtendedLimit();limits.basic.flags=0x2000|0x8|0x100|0x200 # kill-on-close, one process, memory bounds
        limits.basic.active_processes=1;limits.process_memory=memory_bytes;limits.job_memory=memory_bytes
        checked(a.SetInformationJobObject(job,9,C.byref(limits),C.sizeof(limits)),'set worker limits')
        si=StartupInfoEx();si.info.cb=C.sizeof(si);si.info.flags=0x100
        si.info.stdin,si.info.stdout,si.info.stderr=[p[0] for p in pipes];si.attributes=C.cast(attributes,H)
        command=C.create_unicode_buffer(subprocess.list2cmdline([str(arg) for arg in args]))
        environment=C.create_unicode_buffer('\0'.join(f'{k}={v}' for k,v in sorted(env.items(),key=lambda pair:pair[0].upper()))+'\0\0')
        checked(a.CreateProcessW(str(args[0]),command,None,None,True,0x4|0x400|0x80000|0x8000000,environment,str(cache),C.byref(si),C.byref(pi)),'create AppContainer worker')
        checked(a.AssignProcessToJobObject(job,pi.process),'assign worker to job before execution')
        for child,parent in pipes:
            a.CloseHandle(child);handles.remove(child)
        for i,(_,parent) in enumerate(pipes):
            descriptor=msvcrt.open_osfhandle(parent,(os.O_WRONLY if i==0 else os.O_RDONLY)|os.O_BINARY)
            handles.remove(parent);streams.append(os.fdopen(descriptor,'wb' if i==0 else 'rb',buffering=0))
        checked(a.ResumeThread(pi.thread)!=0xFFFFFFFF,'resume restricted worker')
        a.CloseHandle(pi.thread);pi.thread=None
        process=RestrictedProcess(pi.process,job,pi.pid,streams);pi.process=None;job=None;streams=[];return process
    finally:
        if pi.process:
            a.TerminateProcess(pi.process,1);a.WaitForSingleObject(pi.process,5000);a.CloseHandle(pi.process)
        if pi.thread:a.CloseHandle(pi.thread)
        if job:a.CloseHandle(job)
        for handle in handles:a.CloseHandle(handle)
        for stream in streams:stream.close()
        if initialized:a.DeleteProcThreadAttributeList(attributes)
