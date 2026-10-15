"""Revocation, cleanup retries and expiry without loading AI models."""
import time,unittest
from fastapi import FastAPI,Request
from fastapi.testclient import TestClient
from local_ai import security
from local_ai import sessions as lifecycle
class SessionTests(unittest.TestCase):
    def setUp(self):
        lifecycle.sessions.clear();lifecycle.revocations.clear();security.pair_attempts.clear();self.cleaned=[]
        lifecycle.register_cleanup(lambda token:self.cleaned.append(token) or {'cancelled':1,'purged':2})
    def tearDown(self):lifecycle.register_cleanup(lambda token:{'cancelled':0,'purged':0});lifecycle.sessions.clear();lifecycle.revocations.clear()
    def test_revoke_invalidates_and_is_idempotent_without_touching_another_owner(self):
        a=security.pair();b=security.pair();result=lifecycle.revoke(a['token'])
        self.assertFalse(lifecycle.active(a['token']));self.assertTrue(lifecycle.active(b['token']))
        self.assertEqual(result['cancelled'],1);self.assertEqual(result['purged'],2)
        self.assertEqual(lifecycle.revoke(a['token']),result);self.assertEqual(self.cleaned,[a['token']])
    def test_failed_cleanup_is_retryable_but_authorization_stays_revoked(self):
        a=security.pair()
        def failure(token):raise RuntimeError('controlled cleanup failure')
        lifecycle.register_cleanup(failure)
        with self.assertRaises(RuntimeError):lifecycle.revoke(a['token'])
        self.assertFalse(lifecycle.active(a['token']));self.assertTrue(lifecycle.pending(a['token']));self.assertTrue(lifecycle.may_revoke(a['token']))
        lifecycle.register_cleanup(lambda token:{'cancelled':1,'purged':1})
        self.assertTrue(lifecycle.revoke(a['token'])['revoked']);self.assertFalse(lifecycle.pending(a['token']))
    def test_expiry_cleans_owner_jobs(self):
        a=security.pair();lifecycle.sessions[a['token']]['expires']=time.time()-1;lifecycle.expire()
        self.assertFalse(lifecycle.active(a['token']));self.assertEqual(self.cleaned,[a['token']])
    def test_expiry_retries_failed_cleanup_and_continues_other_sessions(self):
        a=security.pair();b=security.pair()
        for token in (a['token'],b['token']):lifecycle.sessions[token]['expires']=0
        def cleanup(token):
            if token==a['token']:raise RuntimeError('controlled failure')
            self.cleaned.append(token);return {'cancelled':1,'purged':0}
        lifecycle.register_cleanup(cleanup)
        self.assertEqual(lifecycle.expire(),1);self.assertEqual(self.cleaned,[b['token']]);self.assertTrue(lifecycle.pending(a['token']))
        lifecycle.register_cleanup(lambda token:{'cancelled':1,'purged':0})
        self.assertEqual(lifecycle.expire(),0);self.assertFalse(lifecycle.pending(a['token']))
    def test_http_revocation_rejects_replay_and_allows_cleanup_retry(self):
        app=FastAPI();app.middleware('http')(security.guard)
        @app.post('/pair')
        def pair():return security.pair()
        @app.post('/session/revoke')
        def revoke(request:Request):return lifecycle.revoke(request.state.owner)
        @app.post('/analyze')
        def analyze():return {'ok':True}
        with TestClient(app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',1234)) as client:
            base={'Origin':'http://127.0.0.1:3000','Authorization':'Bearer '+security.PAIR_CODE}
            paired=client.post('/pair',headers=base,json={}).json();headers={**base,'Authorization':'Bearer '+paired['token']}
            self.assertTrue(client.post('/session/revoke',headers=headers,json={}).json()['revoked'])
            self.assertEqual(client.post('/analyze',headers=headers,json={}).status_code,401)
            self.assertEqual(client.post('/session/revoke',headers=headers,json={}).status_code,200)
            self.assertEqual(client.post('/session/revoke',headers={**headers,'Authorization':'Bearer invented'},json={}).status_code,401)
