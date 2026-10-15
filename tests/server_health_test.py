"""Expired-session health responses must not silently discard cleanup credentials."""
import contextlib,io,time,unittest
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient
with contextlib.redirect_stdout(io.StringIO()):
    from local_ai import server
from local_ai import sessions,security
from local_ai.supervisor import WorkerFailure

class HealthTests(unittest.TestCase):
    def setUp(self):
        sessions.sessions.clear();sessions.revocations.clear();self.cleaned=[]
        sessions.sessions['expired-fixture']={'expires':time.time()-1}
        self.fake=SimpleNamespace(sandbox_ready=True,device='fixture',worker=None,problem=None)
        self.patch=patch.object(server,'engine',self.fake);self.patch.start()
        self.client=TestClient(server.app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',1234))
        self.headers={'Authorization':'Bearer expired-fixture','Origin':'http://127.0.0.1:8765'}
    def tearDown(self):
        self.client.close();self.patch.stop();sessions.sessions.clear();sessions.revocations.clear()
        sessions.register_cleanup(lambda token:{'cancelled':0,'purged':0})
    def test_health_attempts_expired_cleanup_before_reporting_session_ended(self):
        sessions.register_cleanup(lambda token:self.cleaned.append(token) or {'cancelled':1,'purged':1})
        health=self.client.get('/health',headers=self.headers).json()
        self.assertFalse(health['paired']);self.assertFalse(health['cleanupPending']);self.assertEqual(self.cleaned,['expired-fixture'])
    def test_health_preserves_pending_cleanup_and_endpoint_allows_retry(self):
        def failed(token):raise WorkerFailure('controlled termination failure')
        sessions.register_cleanup(failed)
        health=self.client.get('/health',headers=self.headers).json()
        self.assertFalse(health['paired']);self.assertTrue(health['cleanupPending'])
        response=self.client.post('/session/revoke',headers=self.headers,json={})
        self.assertEqual(response.status_code,503);self.assertIn('termination failure',response.json()['detail'])
        sessions.register_cleanup(lambda token:{'cancelled':1,'purged':1})
        self.assertTrue(self.client.post('/session/revoke',headers=self.headers,json={}).json()['revoked'])
