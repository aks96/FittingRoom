"""Reject source/model tampering before executing downloaded AI code."""
import hashlib,io,json,subprocess,sys,tarfile,tempfile,unittest,zipfile
from pathlib import Path
from local_ai.source_integrity import extract_source,source_entries,verify_tree
from local_ai.download_models import verify_recognition

class IntegrityTests(unittest.TestCase):
    def archive(self,path,members):
        with tarfile.open(path,'w:gz') as tar:
            for name,data,kind in members:
                member=tarfile.TarInfo(name)
                if kind=='link':member.type=tarfile.SYMTYPE;member.linkname='../../outside';tar.addfile(member)
                else:member.size=len(data);tar.addfile(member,io.BytesIO(data))
        return hashlib.sha256(path.read_bytes()).hexdigest()
    def test_wrong_digest_and_unsafe_paths_do_not_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive=root/'source.tar.gz';target=root/'source'
            digest=self.archive(archive,[('upstream/pyproject.toml',b'[project]','file')])
            with self.assertRaisesRegex(RuntimeError,'integrity'):extract_source(archive,target,'0'*64)
            self.assertFalse(target.exists())
            for name,kind in [('../outside','file'),('/absolute','file'),('upstream/../../outside','file'),('upstream/link','link'),('upstream/C:\\escape','file')]:
                digest=self.archive(archive,[('upstream/pyproject.toml',b'[project]','file'),(name,b'bad',kind)])
                with self.assertRaises(RuntimeError):extract_source(archive,target,digest)
                self.assertFalse(target.exists())
    def test_changed_existing_source_and_injected_modules_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='source integrity ') as temp:
            root=Path(temp);archive=root/'source.tar.gz';target=root/'source'
            digest=self.archive(archive,[('upstream/pyproject.toml',b'[project]','file'),('upstream/src/module.py',b'x=1','file')])
            extract_source(archive,target,digest);entries=source_entries(archive,digest);verify_tree(target,entries)
            (target/'src/module.py').write_text('x=2')
            with self.assertRaises(RuntimeError):verify_tree(target,entries)
            (target/'src/module.py').write_text('x=1');(target/'src/injected.py').write_text('bad')
            with self.assertRaisesRegex(RuntimeError,'Unexpected Python'):verify_tree(target,entries)
    def test_recognition_artifacts_fail_closed_on_missing_or_modified_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'security').mkdir();model=root/'.runtime/weights/clip/config.json';model.parent.mkdir(parents=True)
            model.write_bytes(b'{}');baseline={'files':[{'name':'clip/config.json','bytes':2,'sha256':hashlib.sha256(b'{}').hexdigest()}]}
            (root/'security/recognition-files.json').write_text(json.dumps(baseline));verify_recognition(root)
            model.write_bytes(b'[]')
            with self.assertRaisesRegex(RuntimeError,'integrity'):verify_recognition(root)
            model.unlink()
            with self.assertRaisesRegex(RuntimeError,'integrity'):verify_recognition(root)

    def test_pip_hash_lock_rejects_modified_wheel_without_installing(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);wheel=root/'yfr_integrity_fixture-1.0-py3-none-any.whl'
            with zipfile.ZipFile(wheel,'w') as archive:
                archive.writestr('yfr_integrity_fixture-1.0.dist-info/METADATA','Metadata-Version: 2.1\nName: yfr-integrity-fixture\nVersion: 1.0\n')
                archive.writestr('yfr_integrity_fixture-1.0.dist-info/WHEEL','Wheel-Version: 1.0\nGenerator: local-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
                archive.writestr('yfr_integrity_fixture-1.0.dist-info/RECORD','')
            lock=root/'requirements.txt';lock.write_text('yfr-integrity-fixture @ '+wheel.as_uri()+' --hash=sha256:'+'0'*64+'\n')
            result=subprocess.run([sys.executable,'-m','pip','--isolated','--disable-pip-version-check','install','--dry-run','--no-index','--require-hashes','--only-binary=:all:','-r',str(lock)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('DO NOT MATCH THE HASHES',result.stderr.upper())

if __name__=='__main__':unittest.main()
