"""Loopback pairing and signed site permissions. Never stores photo data."""
import asyncio, base64, json, secrets, time
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from starlette.responses import JSONResponse

config=json.loads((Path(__file__).resolve().parents[1]/'security/issuer.json').read_text())
SITE=config['origin']
ORIGINS={SITE,'http://127.0.0.1:3000','http://localhost:3000'}
PAIR_CODE=secrets.token_urlsafe(24)
sessions={}
pair_attempts=[]
active=asyncio.Semaphore(2)
def unbase(value):return base64.urlsafe_b64decode(value+'='*((-len(value))%4))
key=Ed25519PublicKey.from_public_bytes(unbase(config['publicKey']['x']))

def permission(value,session):
    try:
        payload,signature=value.split('.')
        key.verify(unbase(signature),payload.encode())
        claims=json.loads(unbase(payload))
        now=time.time()
        return claims['iss']==SITE and claims['aud']==session['challenge'] and isinstance(claims['sub'],str) and 0<len(claims['sub'])<=128 and now<claims['exp']<=now+300 and now-300<=claims['iat']<=now+30
    except Exception:return False

def pair():
    now=time.time()
    for token,s in list(sessions.items()):
        if s['expires']<now:sessions.pop(token,None)
    if len(sessions)>=8:return None
    token=secrets.token_urlsafe(32)
    sessions[token]={'challenge':secrets.token_urlsafe(24),'expires':now+14400,'generations':[]}
    return {'token':token,'challenge':sessions[token]['challenge'],'expiresAt':int((now+14400)*1000)}

async def guard(request,call_next):
    def fail(status,message):return JSONResponse({'detail':message},status_code=status)
    if not request.client or request.client.host not in ('127.0.0.1','::1'):return fail(403,'Local requests only.')
    if request.headers.get('host') not in ('127.0.0.1:8765','localhost:8765'):return fail(403,'Invalid local host.')
    origin=request.headers.get('origin')
    if origin and origin not in ORIGINS:return fail(403,'This website is not allowed to use the local engine.')
    cors={'Access-Control-Allow-Origin':origin,'Vary':'Origin'} if origin in ORIGINS else {}
    async def response(value):
        value.headers.update(cors);value.headers['Cache-Control']='no-store';value.headers['X-Content-Type-Options']='nosniff';return value
    if request.method=='OPTIONS':
        if origin not in ORIGINS:return fail(403,'Website origin required.')
        return await response(JSONResponse({},headers={'Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Authorization, Content-Type, X-WearView-Permit','Access-Control-Allow-Private-Network':'true','Access-Control-Max-Age':'300'}))
    if request.url.path=='/health' and request.method=='GET':return await response(await call_next(request))
    if origin not in ORIGINS:return fail(403,'Website origin required.')
    bearer=request.headers.get('authorization','').removeprefix('Bearer ')
    if request.url.path=='/pair':
        now=time.time();pair_attempts[:]=[t for t in pair_attempts if t>now-60]
        if len(pair_attempts)>=5:return await response(fail(429,'Too many pairing attempts. Wait a minute.'))
        pair_attempts.append(now)
        if not secrets.compare_digest(bearer,PAIR_CODE):return await response(fail(401,'Incorrect pairing code. Check the local terminal.'))
    else:
        session=sessions.get(bearer)
        if not session or session['expires']<time.time():return await response(fail(401,'Pair this browser with the local engine again.'))
        request.state.owner=bearer
        if request.url.path=='/tryon':
            if origin==SITE and not permission(request.headers.get('x-wearview-permit',''),session):return await response(fail(401,'Sign in again to authorize generation. No photo has been processed.'))
            now=time.time();session['generations'][:]=[t for t in session['generations'] if t>now-60]
            if len(session['generations'])>=4:return await response(fail(429,'Too many generation requests. Wait a minute.'))
            session['generations'].append(now)
    if request.method=='POST':
        if request.headers.get('content-type','').split(';')[0]!='application/json':return await response(fail(415,'JSON requests required.'))
        try:
            if int(request.headers.get('content-length','0'))>36*1024*1024:return await response(fail(413,'Image request too large.'))
            async def read():
                data=bytearray()
                async for chunk in request.stream():
                    data.extend(chunk)
                    if len(data)>36*1024*1024:raise ValueError()
                return bytes(data)
            request._body=await asyncio.wait_for(read(),30)
        except (ValueError,asyncio.TimeoutError):return await response(fail(413,'Image request too large or timed out.'))
    if request.url.path in ('/analyze','/tryon'):
        try:await asyncio.wait_for(active.acquire(),.05)
        except asyncio.TimeoutError:return await response(fail(429,'Local processor is busy.'))
        try:return await response(await call_next(request))
        finally:active.release()
    return await response(await call_next(request))
