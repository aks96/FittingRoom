"""Offline setup-contract tests; these do not claim real Windows execution."""
import hashlib,io,os,tarfile,tempfile,unittest,zipfile
from pathlib import Path
from local_ai.windows_setup import validate_platform,install_commands,environment,extract_source
ROOT=Path(__file__).resolve().parents[1]

class CompanionSetupTests(unittest.TestCase):
    def test_windows_platform_bounds(self):
        validate_platform('Windows','AMD64',(3,12,1));validate_platform('Windows','x86_64',(3,12,9))
        with self.assertRaises(RuntimeError):validate_platform('Windows','AMD64',(3,12),bits=32)
        for args in [('Darwin','arm64',(3,12)),('Windows','ARM64',(3,12)),('Windows','AMD64',(3,13))]:
            with self.assertRaises(RuntimeError):validate_platform(*args)

    def test_install_plan_uses_fixed_indexes_and_argument_paths(self):
        root=Path('C:/Users/Test User/companion');python=root/'.runtime/ai-venv/Scripts/python.exe'
        for compute,index in [('cpu','cpu'),('cuda','cu126')]:
            commands=install_commands(python,compute,root)
            self.assertEqual(commands[1][-1],'https://download.pytorch.org/whl/'+index)
            self.assertIn('torch==2.13.0',commands[1]);self.assertIn('torchvision==0.28.0',commands[1]);self.assertIn('--only-binary=:all:',commands[1])
            self.assertEqual(commands[2][-1],root/'local_ai/requirements-windows.txt')
            self.assertEqual(commands[0][0],python);self.assertIn('--require-hashes',commands[0])
        with self.assertRaises(ValueError):install_commands(python,'unknown',root)
        env=environment(root);self.assertEqual(env['HF_HUB_DISABLE_TELEMETRY'],'1')
        self.assertEqual(env['HF_HUB_OFFLINE'],'0') # inbound downloads only during explicit setup
        requirements=(ROOT/'local_ai/requirements-windows.txt').read_text()
        self.assertNotIn('\ntorch==',requirements);self.assertNotIn('\ntorchvision==',requirements)

    def test_archive_traversal_is_rejected_and_normal_source_installs(self):
        with tempfile.TemporaryDirectory(prefix='companion test ') as directory:
            folder=Path(directory);archive=folder/'source.tar.gz';destination=folder/'fashn-src'
            for name in ['../escape','upstream/pyproject.toml']:
                with tarfile.open(archive,'w:gz') as tar:
                    info=tarfile.TarInfo(name);data=b'[project]\n';info.size=len(data);tar.addfile(info,io.BytesIO(data))
                if name.startswith('..'):
                    with self.assertRaises(RuntimeError):extract_source(archive,destination,hashlib.sha256(archive.read_bytes()).hexdigest())
                else:extract_source(archive,destination,hashlib.sha256(archive.read_bytes()).hexdigest());self.assertTrue((destination/'pyproject.toml').is_file())

    def test_distributed_packages_and_launcher_bounds(self):
        with tarfile.open(ROOT/'public/yourFittingRoom-companion.tar.gz') as archive:
            names=archive.getnames();self.assertIn('yourFittingRoom-companion/local_ai/finish_setup.py',names)
            self.assertFalse(any('._' in name or '/.runtime/' in name for name in names))
        with zipfile.ZipFile(ROOT/'public/yourFittingRoom-companion-windows.zip') as archive:
            names=archive.namelist()
            for file in ['Set up.cmd','Start AI.cmd','local_ai/windows_setup.py','local_ai/windows_start.py','security/model-revisions.json']:
                self.assertIn('yourFittingRoom-companion/'+file,names)
            self.assertFalse(any('/.runtime/' in name or '/.env' in name or '__pycache__' in name for name in names))
            for file in ['Set up.cmd','Start AI.cmd']:
                data=archive.read('yourFittingRoom-companion/'+file);text=data.decode()
                self.assertIn(b'\r\n',data);self.assertIn('cd /d "%~dp0"',text)
                self.assertNotIn('ExecutionPolicy',text);self.assertNotIn('runas',text.lower())
            self.assertIn('--host\',\'127.0.0.1',archive.read('yourFittingRoom-companion/local_ai/windows_start.py').decode())

if __name__=='__main__':unittest.main()
