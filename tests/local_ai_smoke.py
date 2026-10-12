"""Integration checks against the running local servers; only supplied test photos are used.
Run with .runtime/ai-venv/bin/python tests/local_ai_smoke.py.
This checks real analysis, invalid input, scope enforcement and cancellable jobs.
"""
import base64, io, json, time, urllib.request, urllib.error, getpass
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8765'
TOKEN=''
PAIR_CODE=getpass.getpass('Local pairing code (hidden): ')

def request(path, body=None, origin='http://127.0.0.1:3000',token=None,extra=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(BASE+path,data=data,headers={'Content-Type':'application/json','Origin':origin,'Authorization':'Bearer '+(TOKEN if token is None else token),**(extra or {})})
    try:
        with urllib.request.urlopen(req,timeout=320) as response:return response.status,json.load(response)
    except urllib.error.HTTPError as error:return error.code,json.load(error)

def image(path):return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()
def wait_deleted(job_id):
    for _ in range(80):
        code,_=request('/jobs/'+job_id)
        if code==404:return
        time.sleep(.5)
    raise AssertionError('Cancelled job was not purged')

code,paired=request('/pair',{},token=PAIR_CODE)
assert code==200,paired
TOKEN=paired['token']
code,health=request('/health')
assert code==200 and health['ready'] and health['localOnly'],health
code,_=request('/analyze',{'image':'not-image'},token='wrong')
assert code==401,code
code,_=request('/analyze',{'image':'not-image'})
assert code==422,code
code,_=request('/analyze',{'image':'not-image'},origin='https://example.com')
assert code>=400,code
fixture=ROOT/'screenshots/qa-tshirt.png'
if not fixture.exists():
    Image.open(ROOT/'.runtime/fashn-src/examples/data/garment.webp').save(fixture)
garment=image(fixture)
code,analysis=request('/analyze',{'image':garment})
assert code==200 and analysis['category']=='T-shirt' and analysis['colour']=='Black',analysis
assert analysis['size']=='Not determined from the image',analysis
print('Real local garment recognition and invalid/origin checks passed.',flush=True)
person='data:image/webp;base64,'+base64.b64encode((ROOT/'.runtime/fashn-src/examples/data/model.webp').read_bytes()).decode()
payload={'person':person,'garment':garment,'category':'Shirt','audience':'Men','photoType':'model','steps':20}
code,_=request('/tryon',payload)
assert code==400,code
payload['category']='T-shirt'
code,job=request('/tryon',payload)
assert code==200,job
code,second=request('/pair',{},token=PAIR_CODE)
assert code==200,second
assert request('/jobs/'+job['id'],token=second['token'])[0]==404
assert request('/jobs/'+job['id'],{},token=second['token'])[0]==404
assert request('/tryon',payload,origin='https://wearview-desktop-beta.kumar-ankush0796.chatgpt.site')[0]==401
code,_=request('/jobs/'+job['id'],{})
assert code==200,code
wait_deleted(job['id'])
print('Scope enforcement, cross-session isolation, hosted permission rejection and cancellation/purge passed.',flush=True)
blank=io.BytesIO();Image.new('RGB',(432,864),'white').save(blank,format='PNG')
payload['person']='data:image/png;base64,'+base64.b64encode(blank.getvalue()).decode()
code,job=request('/tryon',payload)
assert code==200,job
try:
    for _ in range(100):
        code,status=request('/jobs/'+job['id'])
        if status.get('stage')=='failed':break
        time.sleep(.5)
    assert status['stage']=='failed' and 'person could not be detected' in status['error'],status
finally:request('/jobs/'+job['id'],{})
print('Non-person photo rejection passed. No test preview was substituted.',flush=True)
