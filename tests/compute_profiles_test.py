"""Backend/configuration contracts; no Windows/GPU compatibility claim."""
import hashlib
import io
import json
import tarfile
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from local_ai.compute import select_device,inference_dtype,rotary_dtype
from local_ai import windows_profiles as profiles,rocm_bootstrap
from local_ai.windows_setup import install_commands,dependency_findings
from local_ai.windows_hardware import parse_adapters
from local_ai import windows_worker

def fake_torch(hip=None,cuda=True,xpu=True,mps=False,count=2):
    def backend(available):return types.SimpleNamespace(is_available=lambda:available,device_count=lambda:count,set_device=lambda index:None,is_bf16_supported=lambda:True)
    return types.SimpleNamespace(version=types.SimpleNamespace(hip=hip),backends=types.SimpleNamespace(mps=backend(mps)),
                                 cuda=backend(cuda),xpu=backend(xpu),float16='fp16',bfloat16='bf16',float32='fp32',float64='fp64')

class ComputeContracts(unittest.TestCase):
    def test_vendor_profiles_route_to_the_correct_torch_api(self):
        self.assertEqual(select_device(fake_torch(),'cuda',1),('cuda:1','cuda'))
        self.assertEqual(select_device(fake_torch(hip='7.14.0'),'rocm'),('cuda:0','rocm'))
        self.assertEqual(select_device(fake_torch(cuda=False),'xpu'),('xpu:0','xpu'))
        self.assertEqual(select_device(fake_torch(cuda=False,xpu=False),'cpu'),('cpu','cpu'))
    def test_amd_is_not_mistaken_for_nvidia(self):
        with self.assertRaisesRegex(RuntimeError,'Wrong Torch build'):select_device(fake_torch(hip='7.14.0'),'cuda')
        with self.assertRaisesRegex(RuntimeError,'Wrong Torch build'):select_device(fake_torch(),'rocm')
    def test_missing_gpu_never_silently_downgrades_to_cpu(self):
        torch=fake_torch(cuda=False,xpu=False)
        for requested in ('auto','cuda','rocm','xpu','cloud','directml'):
            with self.subTest(requested=requested),self.assertRaises(RuntimeError):select_device(torch,requested)
    def test_bad_adapter_index_fails_before_set_device(self):
        torch=fake_torch()
        for index in (-1,2,16,True,'0'):
            with self.subTest(index=index),patch.object(torch.cuda,'set_device') as select:
                with self.assertRaises(RuntimeError):select_device(torch,'cuda',index)
                select.assert_not_called()
    def test_precision_does_not_require_intel_or_amd_fp64(self):
        torch=fake_torch()
        for device,profile in (('mps','mps'),('xpu','xpu'),('cuda','rocm')):
            self.assertEqual(inference_dtype(torch,device,profile),'fp16')
            self.assertEqual(rotary_dtype(torch,device,profile),'fp32')
        self.assertEqual(inference_dtype(torch,'cuda','cuda'),'bf16')
        self.assertEqual(inference_dtype(torch,'cpu','cpu'),'fp32')
    def test_mac_selection_is_preserved(self):
        self.assertEqual(select_device(fake_torch(mps=True),'auto'),('mps','mps'))

class WindowsProfileContracts(unittest.TestCase):
    def test_windows_10_allows_cpu_cuda_but_not_new_amd_intel_profiles(self):
        with patch.object(windows_worker.os,'name','nt'),patch.object(windows_worker.platform,'machine',return_value='AMD64'),patch.object(windows_worker.sys,'version_info',(3,12,0)),patch.object(windows_worker.sys,'getwindowsversion',return_value=types.SimpleNamespace(build=19045),create=True):
            windows_worker.require_windows('cpu');windows_worker.require_windows('cuda')
            for profile in ('rocm','xpu'):
                with self.assertRaisesRegex(RuntimeError,'requires Windows 11'):windows_worker.require_windows(profile)
    def test_worker_environment_does_not_inherit_arbitrary_secrets(self):
        runtime=windows_worker.WindowsRuntime.__new__(windows_worker.WindowsRuntime)
        runtime.cache=Path('/disposable/cache');runtime.root=Path('/disposable/project');runtime.sid_text='disposable SID'
        def windows_directory(buffer,size):buffer.value='C:/Windows';return len(buffer.value)
        with patch.object(windows_worker,'require_windows'),patch.object(windows_worker.native,'api',return_value=types.SimpleNamespace(GetWindowsDirectoryW=windows_directory)),patch.dict(windows_worker.os.environ,{'PRIVATE_TEST_SECRET':'never inherited','YOURFITTINGROOM_ROCM_TARGET':'gfx1100','YOURFITTINGROOM_DEVICE_INDEX':'1'}):
            for profile in ('rocm','xpu'):
                env=runtime.environment(profile)
                self.assertNotIn('PRIVATE_TEST_SECRET',env);self.assertEqual(env['YOURFITTINGROOM_DEVICE_INDEX'],'1')
                self.assertEqual(env['SYCL_CACHE_DIR'],str(runtime.cache/'sycl'))
            self.assertEqual(runtime.environment('rocm')['ROCM_SDK_TARGET_FAMILY'],'gfx1100')
    def test_backend_environments_are_separate_and_models_are_shared(self):
        root=Path('/disposable/project')
        folders={profiles.runtime_folder(root,p) for p in profiles.PROFILES}
        self.assertEqual(len(folders),4)
        self.assertNotEqual(profiles.runtime_folder(root,'rocm','gfx1100'),profiles.runtime_folder(root,'rocm','gfx1201'))
        for folder in folders:self.assertTrue(folder.is_relative_to(root/'.runtime/windows-venvs'))
    def test_untrusted_runtime_and_amd_target_values_are_rejected(self):
        for compute,target,index in (('../elsewhere','all',0),('rocm','../../secret',0),('xpu','gfx1100',0),('cpu','all',1),('xpu','all',True)):
            with self.subTest(compute=compute,target=target,index=index),self.assertRaises(ValueError):profiles.validate(compute,target,index)
        with self.assertRaises(ValueError):profiles.device_environment({'compute':'rocm','runtimeTarget':'all'})
    def test_amd_environment_uses_confirmed_gpu_target_and_index(self):
        env=profiles.device_environment({'compute':'rocm','amdTarget':'all','runtimeTarget':'gfx1201','deviceIndex':1})
        self.assertEqual(env['YOURFITTINGROOM_DEVICE'],'rocm');self.assertEqual(env['YOURFITTINGROOM_DEVICE_INDEX'],'1')
        self.assertEqual(env['ROCM_SDK_TARGET_FAMILY'],'gfx1201')
    def test_malformed_config_cannot_select_an_arbitrary_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'.runtime').mkdir();file=root/'.runtime/companion-device.json'
            for data in ([],{'compute':'cloud'},{'compute':'rocm','runtimeTarget':'untrusted'},{'schemaVersion':2,'compute':'xpu'}):
                file.write_text(json.dumps(data))
                with self.assertRaises(ValueError):profiles.read_config(root)
            config={'schemaVersion':1,'compute':'xpu','executable':'/not/used'}
            file.write_text(json.dumps(config));profiles.read_config(root)
            with self.assertRaises(RuntimeError):profiles.runtime_python(root,config)
    def test_intel_and_amd_install_plans_are_pinned_and_isolated(self):
        root=Path('/project with spaces');python=root/'private/python.exe'
        xpu=install_commands(python,'xpu',root)
        self.assertEqual(xpu[1][-1],'https://download.pytorch.org/whl/xpu');self.assertIn('torch==2.13.0',xpu[1])
        amd=install_commands(python,'rocm',root,'gfx1201')
        self.assertIn('--no-deps',amd[1]);self.assertIn('--no-build-isolation',amd[1]);self.assertEqual(amd[1][-1],root/'.runtime/rocm-bootstrap-build')
        self.assertIn('torch[device-gfx1201]==2.12.0+rocm7.14.0',amd[2]);self.assertIn('--only-binary=:all:',amd[2])
        self.assertEqual(amd[2][amd[2].index('--index-url')+1],'https://repo.amd.com/rocm/whl-multi-arch/')
        self.assertIn('--constraint',amd[2]);self.assertTrue(any('rocm-bootstrap @ https://repo.amd.com/' in str(arg) and '#sha256=' in str(arg) for arg in amd[2]))
        self.assertEqual(amd[0][-1],root/'local_ai/requirements-windows-rocm-bootstrap-hashed.txt')
        self.assertEqual(xpu[0][-1],root/'local_ai/requirements-windows-bootstrap-hashed.txt')
        self.assertFalse(any('--extra-index-url' in cmd for cmd in amd))
    def test_dependency_conflicts_are_not_hidden_by_the_onnx_exception(self):
        expected='fashn-vton 1.5.0 requires onnxruntime-gpu, which is not installed.\n'
        dependency_findings(types.SimpleNamespace(returncode=0,stdout='No broken requirements found.'))
        with patch('builtins.print'):dependency_findings(types.SimpleNamespace(returncode=1,stdout=expected))
        for output in (expected+'torch requires setuptools<82 but you have 84.0.0\n','', 'another missing dependency'):
            with self.assertRaises(RuntimeError):dependency_findings(types.SimpleNamespace(returncode=1,stdout=output))
    def test_display_inventory_does_not_return_device_identifiers(self):
        result=parse_adapters(json.dumps([{'Name':'Intel Arc\nGraphics','DriverVersion':'1.2','VendorId':'8086','PNPDeviceID':'private serial'},
                                         {'Name':'AMD Radeon','VendorId':'1002'},{'Name':'NVIDIA','VendorId':'10DE'}]))
        self.assertEqual([x['vendor'] for x in result],['Intel','AMD','NVIDIA']);self.assertEqual(result[0]['name'],'Intel ArcGraphics')
        self.assertNotIn('private serial',json.dumps(result));self.assertNotIn('PNPDeviceID',json.dumps(result))

class BootstrapContracts(unittest.TestCase):
    def source(self):
        stream=io.BytesIO()
        with tarfile.open(fileobj=stream,mode='w:gz') as archive:
            for name,data in [('package/pyproject.toml',b'[build-system]\n'),('package/src/rocm_sdk/__init__.py',b'# disposable test source\n')]:
                entry=tarfile.TarInfo(name);entry.size=len(data);archive.addfile(entry,io.BytesIO(data))
        return stream.getvalue()
    def test_verified_build_copy_and_tamper_rejection(self):
        data=self.source();config={'rocmBootstrap':{'url':'https://example.invalid/not-used','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}}
        with tempfile.TemporaryDirectory() as directory,patch.object(rocm_bootstrap,'CONFIG',config):
            root=Path(directory);(root/'.runtime').mkdir();archive=root/'.runtime/rocm-bootstrap-7.14.0.tar.gz';archive.write_bytes(data)
            build=rocm_bootstrap.prepare(root,download=True);(build/'src/rocm_sdk/__init__.py').write_text('# build metadata mutation')
            self.assertTrue(rocm_bootstrap.prepare(root,download=False).is_dir())
            archive.write_bytes(data+b'tampered')
            with self.assertRaises(RuntimeError):rocm_bootstrap.prepare(root,download=False)
    def test_oversized_download_is_never_reused_or_extracted(self):
        data=self.source();config={'rocmBootstrap':{'url':'https://example.invalid/not-used','bytes':10,'sha256':hashlib.sha256(data).hexdigest()}}
        with tempfile.TemporaryDirectory() as directory,patch.object(rocm_bootstrap,'CONFIG',config),patch.object(rocm_bootstrap.urllib.request,'urlopen',return_value=io.BytesIO(data)):
            root=Path(directory)
            with self.assertRaises(RuntimeError):rocm_bootstrap.prepare(root)
            self.assertFalse((root/'.runtime/rocm-bootstrap-7.14.0.tar.gz').exists());self.assertEqual(list((root/'.runtime').iterdir()),[])

class OperatorContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:import torch
        except ImportError:raise unittest.SkipTest('Torch is not installed in this test environment')
        cls.torch=torch
    def test_query_slicing_preserves_full_attention_with_unequal_lengths(self):
        from local_ai.compute import model_attention
        torch=self.torch
        q=torch.sin(torch.arange(2*3*15*8).float()).reshape(2,3,15,8)
        k=torch.cos(torch.arange(2*3*19*8).float()).reshape(2,3,19,8);v=k*.75
        reference=torch.nn.functional.scaled_dot_product_attention(q,k,v)
        for profile in ('rocm','xpu'):
            result=model_attention(torch,q,k,v,profile,chunk_size=4)
            self.assertEqual(result.shape,reference.shape);self.assertTrue(torch.allclose(result,reference,atol=1e-5,rtol=1e-5))
    def test_first_query_still_attends_to_keys_beyond_its_slice(self):
        from local_ai.compute import model_attention
        torch=self.torch;q=torch.ones((1,1,5,8));k=torch.zeros((1,1,9,8));v=torch.zeros_like(k);v[...,8,:]=9
        result=model_attention(torch,q,k,v,'xpu',chunk_size=2)
        self.assertTrue(torch.allclose(result,torch.ones_like(result)))
    def test_invalid_chunk_sizes_are_rejected(self):
        from local_ai.compute import model_attention
        q=self.torch.ones((1,1,2,8))
        for size in (0,-1,257,True):
            with self.assertRaises(ValueError):model_attention(self.torch,q,q,q,'rocm',chunk_size=size)
    def test_real_cpu_operator_probe(self):
        from local_ai.compute import probe_compute
        checks,info=probe_compute(self.torch,'cpu')
        self.assertEqual(checks,{'computeAvailable':True,'modelOperatorsAvailable':True});self.assertEqual(info['computeProfile'],'cpu')

if __name__=='__main__':unittest.main()
