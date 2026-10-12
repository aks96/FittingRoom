"""Install immutable, checksummed model artifacts. Runs only during initial setup."""
import hashlib,json,os,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'security/model-revisions.json').read_text())
folders={'fashn-ai/fashn-vton-1.5':'','fashn-ai/DWPose':'dwpose','fashn-ai/fashn-human-parser':'parser'}
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def verify():
    for model in manifest['models']:
        for file in model['files']:
            target=ROOT/'.runtime/weights'/folders[model['id']]/file['name']
            if not target.is_file() or digest(target)!=file['sha256']:raise RuntimeError('Model integrity check failed: '+file['name']+'. Run setup again.')
if __name__=='__main__':
    for model in manifest['models']:
        folder=ROOT/'.runtime/weights'/folders[model['id']];folder.mkdir(parents=True,exist_ok=True)
        files=list(model['files'])
        if folders[model['id']]=='parser':files+=[{'name':'config.json'}]
        for file in files:
            target=folder/file['name']
            if target.exists() and ('sha256' not in file or digest(target)==file['sha256']):continue
            url='https://huggingface.co/'+model['id']+'/resolve/'+model['revision']+'/'+file['name']
            temporary=target.with_suffix(target.suffix+'.part')
            try:
                with urllib.request.urlopen(url,timeout=120) as src,temporary.open('wb') as dst:
                    for chunk in iter(lambda:src.read(1024*1024),b''):dst.write(chunk)
                if 'sha256' in file and digest(temporary)!=file['sha256']:raise RuntimeError('Downloaded model checksum mismatch.')
                os.replace(temporary,target)
            finally:temporary.unlink(missing_ok=True)
    verify();print('Pinned model files verified.')
