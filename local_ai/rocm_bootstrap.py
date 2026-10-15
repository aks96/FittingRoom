"""Bounded, pinned AMD bootstrap source for development setup only.

AMD publishes this small meta-package as source. Verify before extraction/build;
do not enable arbitrary sdists for other dependencies or disable TLS checks.
"""
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path
from local_ai.source_integrity import source_entries,extract_source
from local_ai.windows_profiles import CONFIG

def prepare(root,download=True):
    root=Path(root);config=CONFIG['rocmBootstrap'];runtime=root/'.runtime';runtime.mkdir(parents=True,exist_ok=True)
    archive=runtime/'rocm-bootstrap-7.14.0.tar.gz';source=runtime/'rocm-bootstrap-source';build=runtime/'rocm-bootstrap-build'
    if not archive.exists():
        if not download:raise RuntimeError('Verified AMD bootstrap source is missing. Rerun Windows setup.')
        with tempfile.NamedTemporaryFile(dir=runtime,delete=False) as stream:partial=Path(stream.name)
        try:
            with urllib.request.urlopen(config['url'],timeout=60) as response,partial.open('wb') as output:
                total=0
                while chunk:=response.read(65536):
                    total+=len(chunk)
                    if total>config['bytes']:raise RuntimeError('AMD bootstrap download exceeds its pinned size.')
                    output.write(chunk)
                if total!=config['bytes']:raise RuntimeError('Incomplete AMD bootstrap download.')
            source_entries(partial,config['sha256']);os.replace(partial,archive)
        finally:partial.unlink(missing_ok=True)
    entries=source_entries(archive,config['sha256']);extract_source(archive,source,config['sha256'])
    if not download:return source
    # Build metadata can change with GPU discovery. Build a disposable copy and
    # keep the original verified source immutable for later startup checks.
    if build.is_symlink():raise RuntimeError('Invalid AMD build directory.')
    if build.exists():shutil.rmtree(build)
    build.mkdir()
    for name,data in entries.items():
        target=build/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    return build
