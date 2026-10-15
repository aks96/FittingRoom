"""Cross-platform failure-contract tests. These are NOT Windows execution evidence."""
import ctypes as C
import io
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from local_ai import windows_native as native,windows_worker as worker
from local_ai.protocol import write_frame

class FakeWin32:
    """Real disposable pipes; fake security APIs only to test fail-closed ordering."""
    def __init__(self,fail=None):self.events=[];self.fds=set();self.fail=fail;self.attrs={};self.limits=None
    def CloseHandle(self,handle):
        if handle in self.fds:os.close(handle);self.fds.remove(handle)
        return True
    def CreatePipe(self,read,write,*_):
        r,w=os.pipe();self.fds.update((r,w))
        C.cast(read,C.POINTER(native.H))[0]=r;C.cast(write,C.POINTER(native.H))[0]=w;return True
    def SetHandleInformation(self,*_):return True
    def InitializeProcThreadAttributeList(self,buffer,count,flags,size):
        C.cast(size,C.POINTER(native.S))[0]=256;return buffer is not None
    def UpdateProcThreadAttribute(self,buffer,flags,key,value,size,*_):
        if key==0x20009:
            caps=C.cast(value,C.POINTER(native.SecurityCapabilities)).contents
            self.attrs['capabilities']=(caps.count,caps.capabilities)
        if key==0x20002:self.attrs['handleCount']=size//C.sizeof(native.H)
        if key==0x2000E:self.attrs['childrenRestricted']=C.cast(value,C.POINTER(native.D))[0]
        return True
    def DeleteProcThreadAttributeList(self,*_):self.events.append('deleteAttributes')
    def CreateJobObjectW(self,*_):return 100001
    def SetInformationJobObject(self,job,kind,value,size):
        self.limits=native.ExtendedLimit.from_buffer_copy(C.string_at(value,size));self.events.append('setLimits');return self.fail!='limits'
    def CreateProcessW(self,exe,cmd,pa,ta,inherit,flags,env,cwd,si,pi):
        self.events.append('createSuspended');self.flags=flags
        result=C.cast(pi,C.POINTER(native.ProcessInformation)).contents
        result.process=100002;result.thread=100003;result.pid=42;return True
    def AssignProcessToJobObject(self,*_):self.events.append('assignJob');return self.fail!='assign'
    def ResumeThread(self,*_):self.events.append('resume');return 0
    def TerminateProcess(self,*_):self.events.append('terminate');return True
    def WaitForSingleObject(self,*_):return 0
    def GetExitCodeProcess(self,handle,value):C.cast(value,C.POINTER(native.D))[0]=0;return True

class WindowsLaunchContracts(unittest.TestCase):
    def launch(self,fake):
        with patch.object(native,'api',return_value=fake),patch.dict(sys.modules,{'msvcrt':types.SimpleNamespace(open_osfhandle=lambda handle,flags:handle)}),patch.object(os,'O_BINARY',0,create=True):
            return native.launch(['C:/Python312/python.exe','-I','-S','-c','pass'],{'TEMP':'C:/app/cache'},'C:/app/cache',native.H(123),256*1024**2)
    def test_failed_job_assignment_kills_before_first_instruction(self):
        fake=FakeWin32('assign')
        with self.assertRaises(OSError):self.launch(fake)
        self.assertIn('createSuspended',fake.events);self.assertIn('terminate',fake.events)
        self.assertNotIn('resume',fake.events);self.assertFalse(fake.fds)
    def test_failed_memory_configuration_never_creates_worker(self):
        fake=FakeWin32('limits')
        with self.assertRaises(OSError):self.launch(fake)
        self.assertNotIn('createSuspended',fake.events);self.assertFalse(fake.fds)
    def test_only_restricted_assigned_process_can_resume(self):
        fake=FakeWin32();process=self.launch(fake)
        try:
            self.assertLess(fake.events.index('setLimits'),fake.events.index('createSuspended'))
            self.assertLess(fake.events.index('assignJob'),fake.events.index('resume'))
            self.assertTrue(fake.flags&4);self.assertTrue(fake.flags&0x80000)
            self.assertEqual(fake.attrs,{'capabilities':(0,None),'handleCount':3,'childrenRestricted':1})
            self.assertEqual(fake.limits.basic.active_processes,1)
            self.assertTrue(fake.limits.basic.flags&0x2000)
            self.assertEqual(fake.limits.process_memory,256*1024**2)
            self.assertEqual(fake.limits.job_memory,256*1024**2)
        finally:
            with patch.object(native,'api',return_value=fake):process.close()
            # fdopen owns parent descriptors after transfer; FakeWin32 no longer does.
            fake.fds.clear()
    def test_x64_native_structure_layouts(self):
        if C.sizeof(C.c_void_p)!=8:self.skipTest('x64 layout')
        for cls,size in ((native.StartupInfo,104),(native.StartupInfoEx,112),(native.BasicLimit,64),(native.ExtendedLimit,144),(native.SecurityCapabilities,24)):
            self.assertEqual(C.sizeof(cls),size)

class WindowsWorkerContracts(unittest.TestCase):
    @unittest.skipIf(os.name=='nt','Non-Windows rejection contract')
    def test_mac_cannot_be_reported_as_windows_validation(self):
        with self.assertRaisesRegex(RuntimeError,'cannot be validated on a Mac'):worker.WindowsRuntime()
    def test_closed_runtime_never_launches(self):
        runtime=worker.WindowsRuntime.__new__(worker.WindowsRuntime);runtime.closed=True
        with patch.object(native,'launch') as launch:
            with self.assertRaises(RuntimeError):runtime.spawn('local_ai.worker')
            launch.assert_not_called()
    def test_arbitrary_entry_point_never_launches(self):
        runtime=worker.WindowsRuntime.__new__(worker.WindowsRuntime);runtime.closed=False
        with patch.object(native,'launch') as launch:
            with self.assertRaises(ValueError):runtime.spawn('os.system')
            launch.assert_not_called()
    def test_invalid_compute_has_no_cpu_or_cloud_fallback(self):
        runtime=worker.WindowsRuntime.__new__(worker.WindowsRuntime)
        for device in ('auto','mps','amd','intel','cloud'):
            with self.assertRaises(RuntimeError):runtime.environment(device)
    def test_validation_requires_all_os_denials(self):
        checks={name:True for name in ('appContainerToken','outsideReadDenied','outsideWriteDenied','codeWriteDenied','cacheWritable','loopbackDenied','internetDenied','childProcessDenied')}
        with tempfile.TemporaryDirectory() as directory:
            runtime=worker.WindowsRuntime.__new__(worker.WindowsRuntime);runtime.base=runtime.root=Path(directory);runtime.sid=None
            process=types.SimpleNamespace(stdin=io.BytesIO(),returncode=0,wait=lambda timeout:0)
            with patch.object(runtime,'spawn',return_value=process),patch.object(native,'change_acl'),patch.object(worker.socket,'socket') as socket,patch.object(worker,'stop') as stop:
                socket.return_value.__enter__.return_value.getsockname.return_value=('127.0.0.1',12345)
                for change in (None,False,'true'):
                    broken=checks.copy()
                    if change is None:broken.pop('outsideReadDenied')
                    else:broken['outsideReadDenied']=change
                    with patch.object(worker,'read_reply',return_value={'checks':broken}):
                        with self.assertRaises(RuntimeError):runtime.probe()
                self.assertEqual(stop.call_count,3);self.assertFalse(list(Path(directory).glob('outside-*')))
                with patch.object(worker,'read_reply',return_value={'checks':checks}):self.assertEqual(runtime.probe(),checks)
    def test_closed_pipe_is_failure_not_a_success_report(self):
        process=types.SimpleNamespace(stdout=io.BytesIO())
        with self.assertRaises(RuntimeError):worker.read_reply(process,timeout=1)
    def test_failed_acl_cleanup_retains_state_for_retry(self):
        runtime=worker.WindowsRuntime.__new__(worker.WindowsRuntime)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);approved=root/'approved';approved.mkdir();cache=root/'cache';cache.mkdir()
            runtime.closed=False;runtime.children=[];runtime.sid=native.H(123);runtime.grants=[approved];runtime.cache=cache
            runtime.lock_owned=True;runtime.lock_handle=456;runtime.profile_created=True;runtime.name='disposable-test'
            api=types.SimpleNamespace(DeleteAppContainerProfile=lambda name:0,FreeSid=lambda sid:None,CloseHandle=lambda handle:None)
            with patch.object(native,'api',return_value=api),patch.object(native,'change_acl',side_effect=[PermissionError('controlled ACL failure'),None]):
                with self.assertRaises(RuntimeError):runtime.close()
                self.assertFalse(runtime.closed);self.assertEqual(runtime.grants,[approved]);self.assertTrue(runtime.sid);self.assertEqual(runtime.lock_handle,456)
                runtime.close();self.assertTrue(runtime.closed);self.assertFalse(runtime.grants);self.assertIsNone(runtime.sid);self.assertIsNone(runtime.lock_handle)

if __name__=='__main__':unittest.main()
