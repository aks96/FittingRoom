"""Fixed local UI assets only. No filesystem browser, remote script loader or hosted photo endpoint."""
import hashlib,json
from pathlib import Path
from starlette.responses import Response
ROOT=Path(__file__).resolve().parents[1]
class Workspace:
    def __init__(self,folder):
        self.folder=Path(folder).resolve();self.assets={};self.hashes=[]
        manifest=self.folder/'manifest.json'
        if manifest.is_file():
            data=json.loads(manifest.read_text());self.assets=data['assets'];self.hashes=data['scriptHashes']
    def has(self,path):return ('/index.html' if path=='/' else path) in self.assets
    def response(self,path):
        path='/index.html' if path=='/' else path
        if path not in self.assets:return Response('Not found.',status_code=404)
        filename=(self.folder/path.lstrip('/')).resolve()
        if not filename.is_relative_to(self.folder) or not filename.is_file():return Response('Workspace verification failed.',status_code=503)
        expected=self.assets[path];data=filename.read_bytes()
        if len(data)!=expected['bytes'] or hashlib.sha256(data).hexdigest()!=expected['sha256']:return Response('Workspace verification failed. Obtain a reviewed build.',status_code=503)
        scripts=' '.join("'sha256-"+value+"'" for value in self.hashes)
        csp="default-src 'none'; script-src 'self' "+scripts+"; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; font-src 'self'; connect-src 'self'; worker-src 'none'; frame-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'"
        return Response(data,media_type=expected['type'],headers={'Content-Security-Policy':csp,'X-Frame-Options':'DENY','Cross-Origin-Resource-Policy':'same-origin','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cache-Control':'no-store','Permissions-Policy':'camera=(), microphone=(), geolocation=(), payment=(), usb=()'})
bundle=Workspace(ROOT/'workspace' if (ROOT/'workspace/manifest.json').is_file() else ROOT/'.runtime/local-workspace')
