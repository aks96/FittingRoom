"""Real local integration on upstream public fixtures, never user photos.

Requires the updated project companion on port 8765. Pairing is read hidden
from stdin and kept only in process memory. Generates one balanced preview.
"""
import base64,getpass,io,json,time,urllib.request,urllib.error
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8765'
code=getpass.getpass('Project companion pairing code (hidden): ')
token='';job_id=None
def request(path,body=None,key=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(BASE+path,data=data,headers={'Content-Type':'application/json','Origin':BASE,'Authorization':'Bearer '+(key if key is not None else token)})
    try:
        with urllib.request.urlopen(req,timeout=320) as response:return response.status,json.load(response)
    except urllib.error.HTTPError as error:return error.code,json.load(error)
def encoded(path):
    mime='webp' if path.suffix=='.webp' else 'png'
    return 'data:image/'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()
status,session=request('/pair',{},key=code);code=''
assert status==200,'Could not pair with the project companion'
token=session['token'];session=None
try:
    garment=encoded(ROOT/'.runtime/fashn-src/examples/data/garment.webp')
    person=encoded(ROOT/'.runtime/fashn-src/examples/data/model.webp')
    status,analysis=request('/analyze',{'image':garment});assert status==200,analysis
    assert analysis['category']=='T-shirt',analysis
    assert 'fabricAppearance' in analysis and analysis['audienceReview'] is True,analysis
    print('Actual garment recognition:',json.dumps(analysis),flush=True)
    payload={'person':person,'garment':garment,'category':'T-shirt','photoType':analysis['photoType'],'audience':'Women','wearerProfile':'Men','steps':30}
    status,blocked=request('/tryon',payload);assert status==400 and 'selected wearer profile is Men' in blocked.get('detail',''),blocked
    print('Actual API mismatch blocked before generation.',flush=True)
    payload.update(audience='Unisex',wearerProfile='Men')
    started=time.monotonic();status,job=request('/tryon',payload);assert status==200,job
    job_id=job['id'];last_stage=None
    for _ in range(620):
        status,result=request('/jobs/'+job_id);assert status==200,result
        stage=result['stage']
        if stage!=last_stage:print('Native stage:',stage,flush=True);last_stage=stage
        if stage=='complete':break
        if stage in ('failed','cancelled'):raise AssertionError(result.get('error',stage))
        time.sleep(1)
    assert result['stage']=='complete','Preview did not complete'
    folder=ROOT/'.runtime/quality-review';folder.mkdir(exist_ok=True)
    data=base64.b64decode(result['image'].split(',',1)[1]);output=folder/'native-balanced.png';output.write_bytes(data)
    with Image.open(io.BytesIO(data)) as image:resolution=list(image.size)
    report={'fixtures':'upstream public model.webp and garment.webp','steps':30,'generationSeconds':round(time.monotonic()-started,2),'resolution':resolution,'analysis':analysis,'qualityConclusion':'Execution verified; inspect the output visually. No photorealism guarantee.'}
    (folder/'report.json').write_text(json.dumps(report,indent=2))
    print('Balanced preview completed:',json.dumps({key:report[key] for key in ['steps','generationSeconds','resolution']}),flush=True)
    status,_=request('/jobs/'+job_id,{});assert status==200;job_id=None
    status,health=request('/health');assert status==200 and not health['loaded'],health
    print('Result collected, worker terminated and model memory released.',flush=True)
finally:
    if job_id:request('/jobs/'+job_id,{})
    if token:request('/session/revoke',{});token=''
