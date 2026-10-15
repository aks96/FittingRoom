"""Inspect actual download artifacts; never install packages, execute workers or read personal photos."""
import hashlib
import io
import json
import tarfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]

class CompanionArchiveTests(unittest.TestCase):
    def test_downloads_contain_current_source_and_verified_workspace_only(self):
        metadata=json.loads((ROOT/'security/companion-downloads.json').read_text())
        for platform,item in metadata['packages'].items():
            with self.subTest(platform=platform):
                raw=(ROOT/'public'/item['filename']).read_bytes()
                self.assertEqual(len(raw),item['bytes'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(),item['sha256'])
                if platform=='mac':
                    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
                        self.assertTrue(all(m.isdir() or m.isfile() for m in archive.getmembers()))
                        entries={m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
                else:
                    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                        entries={n:archive.read(n) for n in archive.namelist() if not n.endswith('/')}
                self.assertEqual(len(entries),item['fileCount'])
                prefix=item['folder']+'/'
                for name in entries:
                    p=PurePosixPath(name)
                    self.assertFalse(p.is_absolute())
                    self.assertNotIn('..',p.parts)
                    self.assertTrue(name.startswith(prefix))
                    self.assertFalse(any(part.startswith('.') for part in p.parts))
                    self.assertNotIn('__pycache__',p.parts)
                    self.assertNotRegex(name,r'\.(?:onnx|safetensors|pyc|pem|key)$')
                for name,data in entries.items():
                    relative=name[len(prefix):]
                    if relative.startswith(('local_ai/','security/','scripts/')):
                        self.assertEqual(data,(ROOT/relative).read_bytes(),relative+' is stale')
                for name in [item['setup'],item['start']]+(['Test Windows.cmd'] if platform=='windows' else []):
                    self.assertEqual(entries[prefix+name],(ROOT/'scripts/companion'/name).read_bytes())
                if platform=='windows':
                    for name in ['windows_worker.py','windows_profiles.py','windows_validate.py','windows_native.py','rocm_bootstrap.py']:
                        self.assertIn(prefix+'local_ai/'+name,entries)
                    self.assertIn(prefix+'WINDOWS_TESTING.md',entries)
                workspace=json.loads(entries[prefix+'workspace/manifest.json'])
                actual={name.removeprefix(prefix+'workspace') for name in entries if name.startswith(prefix+'workspace/') and not name.endswith('/manifest.json')}
                self.assertEqual(actual,set(workspace['assets']))
                for url,record in workspace['assets'].items():
                    data=entries[prefix+'workspace'+url]
                    self.assertEqual(len(data),record['bytes'])
                    self.assertEqual(hashlib.sha256(data).hexdigest(),record['sha256'])

if __name__=='__main__':unittest.main()
