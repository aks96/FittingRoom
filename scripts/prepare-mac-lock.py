"""Build-time helper: record official wheel hashes for the pinned Mac profile.
Updating hashes is a release-review step; installers must never generate their own hashes.
"""
import concurrent.futures,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def requirement(line):
    name,version=line.split('==',1)
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',name) or not re.fullmatch(r'[A-Za-z0-9_.+!-]+',version):raise ValueError('Invalid pinned requirement.')
    with urllib.request.urlopen('https://pypi.org/pypi/'+name+'/'+version+'/json',timeout=20) as response:data=json.load(response)
    if data.get('vulnerabilities'):raise RuntimeError('Known advisory for '+line+'. Resolve before locking.')
    hashes=sorted({f['digests']['sha256'] for f in data['urls'] if f['packagetype']=='bdist_wheel' and not f.get('yanked')})
    if not hashes or any(not re.fullmatch('[0-9a-f]{64}',h) for h in hashes):raise RuntimeError('No approved wheel hashes for '+line)
    return line+' \\\n'+' \\\n'.join('    --hash=sha256:'+h for h in hashes)+'\n'
if __name__=='__main__':
    lines=[line for line in (ROOT/'local_ai/requirements-lock.txt').read_text().splitlines() if line and not line.startswith('#')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:locked=list(pool.map(requirement,lines))
    bootstrap=requirement('pip==26.2.1')
    header='# Build-time wheel hashes (release review required) from official PyPI metadata. Mac profile; not a malware certification.\n'
    (ROOT/'local_ai/requirements-mac-hashed.txt').write_text(header+'\n'.join(locked))
    (ROOT/'local_ai/requirements-bootstrap-hashed.txt').write_text(header+bootstrap)
    print('Hashed',len(locked),'pinned Mac dependencies and the pip bootstrap. No packages were installed.')
