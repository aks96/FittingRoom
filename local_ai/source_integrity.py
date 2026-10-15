"""Verify pinned source before installation; reject unsafe archive entries before extraction."""
import hashlib,json,os,shutil,sys,tarfile,tempfile,urllib.request
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
MAX_ARCHIVE=10*1024*1024
MAX_EXPANDED=64*1024*1024

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def source_entries(archive_path,expected_hash):
    if not expected_hash or sha256(archive_path)!=expected_hash:
        raise RuntimeError('Source archive integrity check failed. No downloaded code was installed.')
    entries={};root=None;total=0
    with tarfile.open(archive_path,'r:gz') as archive:
        members=archive.getmembers()
        if len(members)>2000:raise RuntimeError('Source archive has too many entries.')
        for member in members:
            name=PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or '\\' in member.name or ':' in member.name or member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
                raise RuntimeError('Unsafe source archive entry. Setup stopped.')
            if not name.parts:raise RuntimeError('Empty source archive entry.')
            root=root or name.parts[0]
            if name.parts[0]!=root:raise RuntimeError('Unexpected source archive structure.')
            if member.isdir():continue
            relative=str(PurePosixPath(*name.parts[1:]));total+=member.size
            if relative=='.' or relative in entries or total>MAX_EXPANDED:
                raise RuntimeError('Invalid or oversized source archive.')
            stream=archive.extractfile(member)
            if stream is None:raise RuntimeError('Unreadable source archive entry.')
            entries[relative]=stream.read()
    if 'pyproject.toml' not in entries:raise RuntimeError('Source project metadata is missing.')
    return entries

def verify_tree(destination,entries):
    destination=Path(destination)
    if destination.is_symlink():raise RuntimeError('Source folder must not be a symbolic link.')
    for name,data in entries.items():
        target=destination/name
        if any((destination/parent).is_symlink() for parent in Path(name).parents if str(parent)!='.') or target.is_symlink() or not target.is_file() or target.read_bytes()!=data:
            raise RuntimeError('Installed source differs from the verified archive: '+name)
    expected_python={name for name in entries if name.startswith('src/') and name.endswith('.py')}
    actual_python={str(p.relative_to(destination)).replace(os.sep,'/') for p in (destination/'src').rglob('*.py')}
    if actual_python!=expected_python:raise RuntimeError('Unexpected Python source files. Setup stopped.')

def extract_source(archive_path,destination,expected_hash):
    entries=source_entries(archive_path,expected_hash)
    destination=Path(destination)
    if destination.exists():
        verify_tree(destination,entries);return
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        staged=Path(temp)/'source';staged.mkdir()
        for name,data in entries.items():
            target=staged/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        shutil.move(str(staged),str(destination))
    verify_tree(destination,entries)

def prepare(root=ROOT,download=True):
    root=Path(root);config=json.loads((root/'security/model-revisions.json').read_text())
    revision=config['source'];expected=config['sourceArchiveSha256']
    archive=root/'.runtime/fashn-source.tar.gz';destination=root/'.runtime/fashn-src'
    archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():
        if not download:raise RuntimeError('Verified source archive is missing. Run setup before starting.')
        with tempfile.NamedTemporaryFile(dir=archive.parent,delete=False) as temp:partial=Path(temp.name)
        try:
            url='https://codeload.github.com/fashn-AI/fashn-vton-1.5/tar.gz/'+revision
            with urllib.request.urlopen(url,timeout=120) as response,partial.open('wb') as output:
                total=0
                while chunk:=response.read(1024*1024):
                    total+=len(chunk)
                    if total>MAX_ARCHIVE:raise RuntimeError('Source download too large.')
                    output.write(chunk)
            source_entries(partial,expected) # validate the whole archive before making it reusable
            os.replace(partial,archive)
        finally:partial.unlink(missing_ok=True)
    if download:extract_source(archive,destination,expected)
    else:verify_tree(destination,source_entries(archive,expected))
    print('Pinned source integrity verified.')

if __name__=='__main__':
    try:prepare(download='--verify-only' not in sys.argv)
    except (RuntimeError,OSError,tarfile.TarError) as error:print(str(error),file=sys.stderr);sys.exit(1)
