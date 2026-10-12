"""Offline person-photo try-on. All input/output bytes live in process memory."""
import base64, io, os, threading, time, uuid, gc, asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('HF_HOME', str(ROOT / '.runtime/hf-cache'))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.runtime/mpl-cache'))
import numpy as np
import torch
from PIL import Image, ImageOps
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from transformers import CLIPModel, CLIPProcessor
from fashn_human_parser import FashnHumanParser
from fashn_vton import TryOnPipeline
from fashn_vton.tryon_mmdit import TryOnModel
from fashn_vton import tryon_mmdit
from safetensors.torch import load_file
from einops import rearrange

@asynccontextmanager
async def lifespan(app):
    async def expire_results():
        while True:
            await asyncio.sleep(60)
            for key,job in list(jobs.items()):
                if job.get('finished',time.time())<time.time()-1800:jobs.pop(key,None)
    task=asyncio.create_task(expire_results())
    yield
    task.cancel()
    for job in jobs.values():job['cancel'].set()

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=1)
parser = clip = processor = pipeline = None
jobs = {}
DEVICE = 'mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu'
torch.set_num_threads(4)

from local_ai.security import guard, pair, PAIR_CODE
app.middleware('http')(guard)
print('yourFittingRoom local pairing code: '+PAIR_CODE,flush=True)
print('Keep this code private. Pair only with the yourFittingRoom website or localhost.',flush=True)
@app.post('/pair')
def pair_browser():
    result=pair()
    if not result:raise HTTPException(429,'Too many paired sessions. Restart the engine to clear them.')
    return result

from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse
@app.exception_handler(RequestValidationError)
async def validation_error(request,exception):
    return JSONResponse({'detail':'Invalid image request. Check the selected files and details.'},status_code=422)

class ImageInput(BaseModel):
    image: str
class TryOnInput(BaseModel):
    person: str
    garment: str
    category: str
    photoType: str
    audience: str = 'Women'
    steps: int = 20


def decode(value):
    if not value.startswith(('data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,')):
        raise ValueError('Only local JPG, PNG or WebP image data is accepted.')
    raw=base64.b64decode(value.split(',',1)[1],validate=True)
    if len(raw)>12*1024*1024: raise ValueError('Image exceeds 12 MB after editing.')
    image=Image.open(io.BytesIO(raw))
    if image.width*image.height>24_000_000: raise ValueError('Image is too large. Choose a smaller photo.')
    image.load()
    return ImageOps.exif_transpose(image).convert('RGB')

def get_parser():
    global parser
    if parser is None: parser=FashnHumanParser(model_id=str(ROOT/'.runtime/weights/parser'),device='cpu')
    return parser

def get_clip():
    global clip,processor
    if clip is None:
        clip=CLIPModel.from_pretrained(str(ROOT/'.runtime/weights/clip'),local_files_only=True).eval()
        processor=CLIPProcessor.from_pretrained(str(ROOT/'.runtime/weights/clip'),local_files_only=True)
    return clip,processor

def classify(image,labels):
    model,proc=get_clip()
    values=proc(text=[f'a photo of {text}' for text in labels],images=image,return_tensors='pt',padding=True)
    with torch.inference_mode(): scores=model(**values).logits_per_image[0].softmax(-1).cpu().numpy()
    order=np.argsort(-scores)
    return int(order[0]),float(scores[order[0]]-scores[order[1]])

def color_name(rgb):
    import colorsys
    r,g,b=np.asarray(rgb)/255.; h,s,v=colorsys.rgb_to_hsv(r,g,b); h*=360
    if v<.18:return 'Black'
    if s<.12:return 'White' if v>.86 else 'Grey'
    if s<.3 and v>.8:return 'Ivory' if h<70 else 'Light grey'
    if h<20 or h>=345:return 'Pink' if v>.7 and s<.55 else 'Maroon' if v<.55 else 'Red'
    if h<45:return 'Brown' if v<.6 else 'Beige' if s<.45 else 'Orange'
    if h<70:return 'Yellow'
    if h<165:return 'Sage' if s<.35 and v>.4 else 'Green'
    if h<200:return 'Teal'
    if h<260:return 'Navy' if v<.45 else 'Blue'
    if h<320:return 'Plum' if v<.6 else 'Purple'
    return 'Pink'

@app.get('/health')
def health():
    required=['model.safetensors','dwpose/yolox_l.onnx','dwpose/dw-ll_ucoco_384.onnx','clip/config.json','clip/model.safetensors','clip/processor_config.json']
    ready=all((ROOT/'.runtime/weights'/name).exists() for name in required) and (ROOT/'.runtime/weights/parser/model.safetensors').is_file()
    return {'ready':ready,'device':DEVICE,'model':'FASHN VTON 1.5','loaded':pipeline is not None,'localOnly':True}

@app.post('/analyze')
def analyze(request:ImageInput):
    try:
        image=decode(request.image)
        with lock:
            mask=get_parser().predict(image)
            categories=['a t-shirt with a crew neck and no buttons','a button-front collared shirt','a blouse or womens top','a dress covering torso and thighs']
            index,margin=classify(image,categories)
            category=['T-shirt','Shirt','Top','Dress'][index]
            photo_type='model' if np.isin(mask,[1,2,12,13,14]).sum()/mask.size>.035 else 'flat-lay'
            pixels=np.array(image)
            garment_mask=(mask==4) if category=='Dress' else (mask==3)
            reliable=garment_mask.sum()>mask.size*.01
            if reliable: values=pixels[garment_mask]
            else:
                # Fallback only estimates foreground pixels; it does not claim segmentation success.
                edge=np.concatenate([pixels[0],pixels[-1],pixels[:,0],pixels[:,-1]])
                background=np.median(edge,axis=0)
                foreground=np.linalg.norm(pixels.astype(float)-background,axis=2)>35
                values=pixels[foreground]
            if len(values)<100: colour='Uncertain'; swatch='#888888'
            else:
                values=values[::max(1,len(values)//12000)]
                # Dominant cluster preserves dark and pale garment colours; no background sample substitution.
                import cv2
                cv2.setRNGSeed(42)
                _,label,centres=cv2.kmeans(values.astype(np.float32),min(3,len(values)),None,(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,25,.5),3,cv2.KMEANS_PP_CENTERS)
                rgb=centres[np.argmax(np.bincount(label.ravel()))].clip(0,255).astype(int)
                colour=color_name(rgb);swatch='#'+''.join(f'{c:02x}' for c in rgb)
            pattern_index,pattern_margin=classify(image,['a solid-colour garment','a floral print garment','a striped garment','a checked plaid garment','a garment with a graphic print'])
            pattern=['Solid','Floral','Striped','Checked','Graphic'][pattern_index]
            sleeve_index,sleeve_margin=classify(image,['a sleeveless garment','a short-sleeve garment','a long-sleeve garment'])
        return {'category':category,'colour':colour,'swatch':swatch,'photoType':photo_type,'pattern':pattern if pattern_margin>.12 else 'Uncertain','sleeves':['Sleeveless','Short sleeves','Long sleeves'][sleeve_index] if sleeve_margin>.12 else 'Uncertain','categoryReview':margin<.2,'colourReview':not reliable,'size':'Not determined from the image','fit':'Needs garment dimensions and body measurements','method':'Local CLIP classification + garment segmentation + colour clustering'}
    except Exception: raise HTTPException(422,'Could not analyse this image. Choose a clear garment image or confirm details manually.')

# Metal has no float64 tensor support. Compute rotary embeddings in float32 there.
def metal_rope(pos,dim,theta):
    scale=torch.arange(0,dim,2,dtype=torch.float32 if pos.device.type=='mps' else torch.float64,device=pos.device)/dim
    out=torch.einsum('...n,d->...nd',pos,1.0/(theta**scale))
    out=torch.stack([torch.cos(out),-torch.sin(out),torch.sin(out),torch.cos(out)],dim=-1)
    return rearrange(out,'b n d (i j) -> b n d i j',i=2,j=2).float()

class LocalPipeline(TryOnPipeline):
    def _setup_tryon_model(self):
        self.inference_dtype=torch.float16 if self.device.type=='mps' else torch.bfloat16 if self.device.type=='cuda' else torch.float32
        state=load_file(str(ROOT/'.runtime/weights/model.safetensors'),device='cpu')
        with torch.device('meta'): self.tryon_model=TryOnModel()
        self.tryon_model.load_state_dict(state,assign=True)
        self.tryon_model.to(self.device,dtype=self.inference_dtype).eval()
        del state
    def _setup_hp_model(self): self.hp_model=get_parser()

class Cancelled(Exception):pass

def run_job(job_id,person,garment,request):
    global pipeline
    job=jobs[job_id]
    try:
        with lock:
            if job['cancel'].is_set():raise Cancelled()
            job['stage']='loading-model'
            if pipeline is None:
                tryon_mmdit.rope=metal_rope
                pipeline=LocalPipeline(weights_dir=str(ROOT/'.runtime/weights'),device=DEVICE)
            if job['cancel'].is_set():raise Cancelled()
            job['stage']='aligning-images'
            person_mask=get_parser().predict(person)
            if (person_mask==1).sum()/person_mask.size<.001 or (person_mask!=0).sum()/person_mask.size<.03:
                raise ValueError('A clear person could not be detected. Upload a front-facing photo with your face and torso visible; include your legs for a dress.')
            # Check cancellation at each model step; no invented progress percentage.
            original=pipeline.tryon_model.forward_for_cfg
            def checked(*args,**kwargs):
                if job['cancel'].is_set():raise Cancelled()
                job['stage']='generating'
                return original(*args,**kwargs)
            pipeline.tryon_model.forward_for_cfg=checked
            try:
                result=pipeline(person_image=person,garment_image=garment,category='one-pieces' if request.category=='Dress' else 'tops',garment_photo_type=request.photoType,num_timesteps=request.steps,num_samples=1,seed=42,segmentation_free=True)
            finally: pipeline.tryon_model.forward_for_cfg=original
            if job['cancel'].is_set():raise Cancelled()
            output=io.BytesIO();result.images[0].save(output,format='PNG')
            job['image']='data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()
            job['stage']='complete'
    except Cancelled: job['stage']='cancelled'
    except ValueError as error:job['stage']='failed';job['error']=str(error) if str(error).startswith('A clear person could not be detected.') else 'Local generation failed. Choose a clear person photo.'
    except Exception:job['stage']='failed';job['error']='Local generation failed. Use a clear front-facing person photo, then retry. No sample was substituted.'
    finally:
        person.close();garment.close();gc.collect()
        if DEVICE=='mps':torch.mps.empty_cache()
        job['finished']=time.time()
        if job.get('purge'):jobs.pop(job_id,None)

@app.post('/tryon')
def tryon(request:TryOnInput, http:Request):
    if request.category not in ('Top','Shirt','Dress','T-shirt'):raise HTTPException(400,'Unsupported garment category.')
    if request.audience not in ('Women','Men') or request.audience=='Men' and request.category!='T-shirt':raise HTTPException(400,'Men’s scope currently supports T-shirts only.')
    if request.photoType not in ('model','flat-lay'):raise HTTPException(400,'Review the garment photo type.')
    if request.steps not in (20,30):raise HTTPException(400,'Invalid quality setting.')
    try:person,garment=decode(request.person),decode(request.garment)
    except Exception:raise HTTPException(422,'Could not decode the images. Choose valid JPG, PNG or WebP files.')
    for key,j in list(jobs.items()):
        if j.get('finished',time.time())<time.time()-1800:jobs.pop(key,None)
    if sum(j['stage'] not in ('complete','failed','cancelled') for j in list(jobs.values()))>=2:
        person.close();garment.close()
        raise HTTPException(429,'Local processor is busy. Wait for the current preview or cancel it.')
    job_id=uuid.uuid4().hex
    jobs[job_id]={'id':job_id,'owner':http.state.owner,'stage':'queued','cancel':threading.Event(),'image':None,'started':time.time()}
    executor.submit(run_job,job_id,person,garment,request)
    return {'id':job_id,'owner':http.state.owner,'stage':'queued'}

@app.get('/jobs/{job_id}')
def job_status(job_id:str, http:Request):
    job=jobs.get(job_id)
    if not job or job['owner']!=http.state.owner:raise HTTPException(404,'Local job has expired or was deleted.')
    return {key:job.get(key) for key in ('id','stage','image','error')}

@app.post('/jobs/{job_id}')
def delete_job(job_id:str, http:Request):
    job=jobs.get(job_id)
    if job and job['owner']!=http.state.owner:raise HTTPException(404,'Local job has expired or was deleted.')
    if job:
        job['cancel'].set();job['image']=None;job['purge']=True
        if job['stage'] in ('complete','failed','cancelled'):jobs.pop(job_id,None)
    return {'deleted':True,'processingCancellation':'best effort at next model step'}
