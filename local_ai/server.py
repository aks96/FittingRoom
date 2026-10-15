"""Loopback broker. Image decoding and AI run only in the supervised App Sandbox worker."""
import asyncio,time,os
from contextlib import asynccontextmanager
from typing import Annotated
from pathlib import Path
from fastapi import FastAPI,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field,StrictInt
from local_ai.security import guard,pair,PAIR_CODE
from local_ai.sessions import sessions,active,revoke,expire,register_cleanup,pending
from local_ai.supervisor import Supervisor,Busy,Stopped,WorkerFailure
from local_ai.garment_catalog import native_category,compatibility_error
ROOT=Path(__file__).resolve().parents[1]
engine=Supervisor();register_cleanup(engine.revoke_owner)
@asynccontextmanager
async def lifespan(app):
    try:await asyncio.to_thread(engine.warmup)
    except (RuntimeError,WorkerFailure):engine.problem='OS-isolated inference is unavailable. Generation is disabled; no unrestricted fallback is used.'
    async def cleanup():
        while True:
            await asyncio.sleep(1)
            await asyncio.to_thread(expire)
            engine.expire_results()
    task=asyncio.create_task(cleanup())
    try:yield
    finally:task.cancel();engine.shutdown();sessions.clear()
app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
app.middleware('http')(guard)
print('yourFittingRoom local pairing code: '+PAIR_CODE,flush=True)
print('Keep this code private. Pair only with the local yourFittingRoom workspace.',flush=True)

class ImageInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    image:Annotated[str,Field(max_length=18*1024*1024)]
class TryOnInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    person:Annotated[str,Field(max_length=18*1024*1024)]
    garment:Annotated[str,Field(max_length=18*1024*1024)]
    category:str
    photoType:str
    audience:str
    wearerProfile:str
    steps:StrictInt=30
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse,Response
@app.exception_handler(RequestValidationError)
async def invalid(request,error):return JSONResponse({'detail':'Invalid image request. Check the selected files and details.'},status_code=422)

def allowed_image(value):
    if not value.startswith(('data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,')):
        raise HTTPException(422,'Choose valid local JPG, PNG or WebP image data. No paths or remote image URLs are accepted.')
def ready(owner):
    if not active(owner):raise HTTPException(401,'The engine session ended. Pair again with consent.')
    if not engine.sandbox_ready:raise HTTPException(503,engine.problem or 'The isolated worker is not ready.')
@app.post('/pair')
def pair_browser():
    result=pair()
    if not result:raise HTTPException(429,'Too many paired sessions. End a session before pairing again.')
    return result
@app.post('/session/revoke')
def end_session(http:Request):
    try:return revoke(http.state.owner)
    except WorkerFailure as error:raise HTTPException(503,str(error))
@app.get('/health')
def health(http:Request):
    token=http.headers.get('authorization','').removeprefix('Bearer ')
    # Do not let a health check drop expired credentials before cleanup is attempted.
    if token in sessions and not active(token):
        try:revoke(token)
        except WorkerFailure:pass # Pending revocation remains visible and retryable below.
    return {'ready':engine.sandbox_ready,'paired':active(token),'cleanupPending':pending(token),'device':engine.device,'model':'FASHN VTON 1.5','loaded':engine.worker is not None,'localOnly':True,'isolation':('Windows AppContainer + Job Object candidate' if os.name=='nt' else 'macOS App Sandbox prototype') if engine.sandbox_ready else 'unavailable','error':engine.problem}
@app.post('/analyze')
def analyze(request:ImageInput,http:Request):
    ready(http.state.owner);allowed_image(request.image)
    try:
        result=engine.analyze(http.state.owner,request.image)
        if not active(http.state.owner):raise HTTPException(401,'The engine session ended; its processing was stopped.')
        return result
    except Busy as error:raise HTTPException(429,str(error))
    except PermissionError:raise HTTPException(401,'The engine session ended.')
    except Stopped:raise HTTPException(401,'The engine session ended or its processing was stopped.')
    except WorkerFailure as error:raise HTTPException(422,str(error))
@app.post('/tryon')
def tryon(request:TryOnInput,http:Request):
    ready(http.state.owner)
    try:native_category(request.category)
    except ValueError as error:raise HTTPException(400,str(error))
    mismatch=compatibility_error(request.audience,request.wearerProfile)
    if mismatch:raise HTTPException(400,mismatch)
    if request.photoType not in ('model','flat-lay'):raise HTTPException(400,'Review the garment photo type.')
    if request.steps not in (20,30):raise HTTPException(400,'Invalid quality setting.')
    allowed_image(request.person);allowed_image(request.garment)
    try:
        job=engine.generate(http.state.owner,request.model_dump())
        return {'id':job['id'],'stage':job['stage'],'engine':'companion'}
    except Busy as error:raise HTTPException(429,str(error))
    except PermissionError:raise HTTPException(401,'The engine session ended.')
@app.get('/jobs/{job_id}')
def job_status(job_id:str,http:Request):
    with engine.lock:
        job=engine.jobs.get(job_id)
        if not job or job['owner']!=http.state.owner:raise HTTPException(404,'Local job has expired or was deleted.')
        return {**{key:job.get(key) for key in ('id','stage','image','error','engine','totalSteps')},'elapsedMs':int((job.get('finished',time.time())-job['started'])*1000)}
@app.post('/jobs/{job_id}')
def delete_job(job_id:str,http:Request):
    try:return engine.cancel_job(job_id,http.state.owner)
    except KeyError:raise HTTPException(404,'Local job has expired or was deleted.')
    except WorkerFailure as error:raise HTTPException(503,str(error))

from local_ai.workspace import bundle
@app.get('/')
def workspace_root():return bundle.response('/') if bundle.has('/') else Response('Local workspace build is missing. Run the developer build first.',status_code=503)
@app.get('/{asset_path:path}')
def workspace_asset(asset_path:str):return bundle.response('/'+asset_path)
