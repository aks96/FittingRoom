"""Internal fixed-code Mac bundle. No end-user pip, Node or source build; not a signed installer."""
import hashlib,json,os,shutil,sys,importlib.metadata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.runtime/fixed-mac-bundle/yourFittingRoom-local'
if sys.platform!='darwin':raise RuntimeError('Build the Mac profile on macOS.')
if not (ROOT/'.runtime/local-workspace/manifest.json').is_file():raise RuntimeError('Build the local workspace first.')
if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir(parents=True)
def copy(source,target):
    shutil.copytree(source,target,dirs_exist_ok=True,ignore_dangling_symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
copy(Path(sys.base_prefix),OUT/'runtime/python')
copy(Path(sys.prefix)/'lib/python3.12/site-packages',OUT/'runtime/python/lib/python3.12/site-packages')
copy(ROOT/'local_ai',OUT/'local_ai');copy(ROOT/'security',OUT/'security')
(OUT/'scripts').mkdir();shutil.copyfile(ROOT/'scripts/build-worker-prototype.py',OUT/'scripts/build-worker-prototype.py')
(OUT/'.runtime').mkdir();copy(ROOT/'.runtime/local-workspace',OUT/'.runtime/local-workspace')
shutil.copyfile(ROOT/'.runtime/fashn-source.tar.gz',OUT/'.runtime/fashn-source.tar.gz')
# Extract only the checksum-verified source; never build or install it on first run.
sys.path.insert(0,str(ROOT));from local_ai.source_integrity import extract_source
manifest=json.loads((OUT/'security/model-revisions.json').read_text())
extract_source(OUT/'.runtime/fashn-source.tar.gz',OUT/'.runtime/fashn-src',manifest['sourceArchiveSha256'])
# This internal test bundle reuses this machine's verified MODEL DATA only, not a Python environment or owner photo files.
(OUT/'.runtime/weights').symlink_to(ROOT/'.runtime/weights',target_is_directory=True)
launch='''#!/bin/sh
set -eu
cd "$(dirname "$0")"
export PYTHONHOME="$PWD/runtime/python" PYTHONPATH="$PWD" PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
./runtime/python/bin/python3.12 -B local_ai/source_integrity.py --verify-only
./runtime/python/bin/python3.12 -B -c 'from local_ai.download_models import verify; verify()'
./runtime/python/bin/python3.12 -B scripts/build-worker-prototype.py
printf '\\nOpen http://127.0.0.1:8765 and pair with the code below. Ctrl+C stops the companion.\\n'
exec ./runtime/python/bin/python3.12 -B -m uvicorn local_ai.server:app --host 127.0.0.1 --port 8765 --no-access-log
'''
(OUT/'Start local workspace.command').write_text(launch);(OUT/'Start local workspace.command').chmod(0o755)
(OUT/'README.md').write_text('Internal fixed-code Mac bundle. Embedded Python/dependencies and local UI; no end-user pip or Node. Launch from this folder. Not signed/notarized for distribution. Model data is linked to the verified developer installation on this machine: this is NOT a portable installer or a public download. Photos/credentials/hosting configuration are excluded. A relocatable model store and platform signing remain release gates.\n')
files={}
components=[]
for distribution in importlib.metadata.distributions(path=[str(OUT/'runtime/python/lib/python3.12/site-packages')]):
    components.append({'type':'library','name':distribution.metadata['Name'],'version':distribution.version,'purl':'pkg:pypi/'+distribution.metadata['Name'].lower().replace('_','-')+'@'+distribution.version})
(OUT/'SBOM.cdx.json').write_text(json.dumps({'bomFormat':'CycloneDX','specVersion':'1.6','version':1,'components':sorted(components,key=lambda component:component['name'].lower())},indent=2)+'\n')
for file in OUT.rglob('*'):
    if file.is_file() and not file.is_symlink() and not file.is_relative_to(OUT/'.runtime/weights'):
        h=hashlib.sha256()
        with file.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
        files[str(file.relative_to(OUT))]={'bytes':file.stat().st_size,'sha256':h.hexdigest()}
(OUT/'BUILD-INVENTORY.json').write_text(json.dumps({'kind':'internal-mac-fixed-code-bundle','releaseReady':False,'modelDataLinked':True,'files':files},indent=2)+'\n')
print('Fixed-code internal Mac bundle created. No photo files, credentials, Node, package installs or hosting configuration. Model link is developer-only; releaseReady=false.')
