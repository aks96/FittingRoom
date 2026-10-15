"""Run without loading the AI model: python -m unittest tests/security_test.py."""
import base64,json,time,unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.testclient import TestClient
from local_ai import security

def encode(value):return base64.urlsafe_b64encode(value).decode().rstrip('=')
class SecurityTests(unittest.TestCase):
    def test_permissions_reject_tampering_expiry_and_wrong_engine(self):
        private=Ed25519PrivateKey.generate();previous=security.key;security.key=private.public_key()
        now=time.time();claims={'iss':security.SITE,'aud':'engine','sub':'user','iat':now,'exp':now+120}
        def signed(value):
            payload=encode(json.dumps(value).encode());return payload+'.'+encode(private.sign(payload.encode()))
        try:
            valid=signed(claims);self.assertTrue(security.permission(valid,{'challenge':'engine'}));self.assertFalse(security.permission(valid,{'challenge':'other'}));self.assertFalse(security.permission(valid+'x',{'challenge':'engine'}))
            for update in [{'exp':now-1},{'exp':now+3600},{'iss':'https://evil.example'},{'iat':now+1000}]:self.assertFalse(security.permission(signed({**claims,**update}),{'challenge':'engine'}))
        finally:security.key=previous
    def test_host_origin_pairing_and_payload_boundaries(self):
        app=FastAPI();app.middleware('http')(security.guard)
        @app.post('/pair')
        def pair():return security.pair()
        @app.post('/analyze')
        def analyze():return {'ok':True}
        @app.get('/jobs/test')
        def job():return {'ok':True}
        with TestClient(app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',1234)) as client:
            good={'Origin':'http://127.0.0.1:3000','Content-Type':'application/json','Authorization':'Bearer '+security.PAIR_CODE}
            self.assertEqual(client.post('/pair',headers={**good,'Host':'evil.example'},json={}).status_code,403)
            self.assertEqual(client.post('/pair',headers={**good,'Origin':'https://evil.example'},json={}).status_code,403)
            self.assertEqual(client.post('/pair',headers={**good,'Origin':security.SITE},json={}).status_code,403)
            self.assertEqual(client.post('/pair',headers={**good,'Authorization':'Bearer wrong'},json={}).status_code,401)
            session=client.post('/pair',headers=good,json={}).json();auth={**good,'Authorization':'Bearer '+session['token']}
            self.assertEqual(client.post('/analyze',headers={**auth,'Content-Length':str(40*1024*1024)},content='{}').status_code,413)
            self.assertEqual(client.post('/analyze',headers={**auth,'Content-Type':'text/plain'},content='{}').status_code,415)
            self.assertEqual(client.post('/analyze',headers=auth,json={}).status_code,200)
            same_origin={'Authorization':auth['Authorization'],'Sec-Fetch-Site':'same-origin'}
            self.assertEqual(client.get('/jobs/test',headers=same_origin).status_code,200)
            self.assertEqual(client.get('/jobs/test',headers={'Authorization':auth['Authorization'],'Sec-Fetch-Site':'cross-site'}).status_code,403)
            security.sessions[session['token']]['expires']=0
            self.assertEqual(client.post('/analyze',headers=auth,json={}).status_code,401)
