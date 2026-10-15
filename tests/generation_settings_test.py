"""API rejects unsupported/mismatched requests before invoking any inference."""
import contextlib,io,time,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from fastapi.testclient import TestClient
with contextlib.redirect_stdout(io.StringIO()):
    from local_ai import server
from local_ai import sessions

class GenerationSettingsTests(unittest.TestCase):
    def setUp(self):
        self.token='category-test';sessions.sessions[self.token]={'expires':time.time()+60,'generations':[]}
        self.engine=SimpleNamespace(sandbox_ready=True,generate=Mock(return_value={'id':'f'*32,'stage':'queued'}))
        self.patch=patch.object(server,'engine',self.engine);self.patch.start()
        self.client=TestClient(server.app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',1234))
        self.headers={'Authorization':'Bearer '+self.token,'Origin':'http://127.0.0.1:8765'}
        self.payload={'person':'data:image/png;base64,fixture','garment':'data:image/png;base64,fixture','category':'Pants','photoType':'flat-lay','audience':'Women','wearerProfile':'Women'}
    def tearDown(self):
        self.client.close();self.patch.stop();sessions.sessions.pop(self.token,None)
    def post(self,**patches):return self.client.post('/tryon',json={**self.payload,**patches},headers=self.headers)
    def test_default_balanced_and_explicit_fast_reach_worker(self):
        self.assertEqual(self.post().status_code,200)
        self.assertEqual(self.engine.generate.call_args.args[1]['steps'],30)
        self.assertEqual(self.post(steps=20,audience='Unisex',wearerProfile='Men',category='Jeans').status_code,200)
        self.assertEqual(self.engine.generate.call_args.args[1]['steps'],20)
    def test_womens_garment_on_mens_profile_is_blocked(self):
        response=self.post(wearerProfile='Men');self.assertEqual(response.status_code,400)
        self.assertIn('selected wearer profile is Men',response.json()['detail']);self.engine.generate.assert_not_called()
    def test_reverse_mismatch_is_also_blocked(self):
        self.assertEqual(self.post(audience='Men').status_code,400);self.engine.generate.assert_not_called()
    def test_unsupported_and_unconfirmed_ranges_do_not_invoke_worker(self):
        self.assertEqual(self.post(category='Shoes').status_code,400)
        self.assertEqual(self.post(audience='Uncertain').status_code,400)
        self.assertEqual(self.post(wearerProfile='').status_code,400);self.engine.generate.assert_not_called()
    def test_invalid_quality_and_missing_profile_do_not_invoke_worker(self):
        self.assertEqual(self.post(steps=50).status_code,400)
        self.assertEqual(self.post(steps='30').status_code,422)
        payload={**self.payload};payload.pop('wearerProfile')
        self.assertEqual(self.client.post('/tryon',json=payload,headers=self.headers).status_code,422)
        self.engine.generate.assert_not_called()

if __name__=='__main__':unittest.main()
