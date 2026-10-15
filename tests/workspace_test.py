"""Fixed local asset integrity, CSP and path boundary checks; no network calls."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from local_ai.workspace import Workspace
class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name);self.content=b'<html>Public test workspace</html>'
        (self.folder/'index.html').write_bytes(self.content)
        (self.folder/'manifest.json').write_text(json.dumps({'assets':{'/index.html':{'bytes':len(self.content),'sha256':hashlib.sha256(self.content).hexdigest(),'type':'text/html'}},'scriptHashes':[]}))
        self.workspace=Workspace(self.folder)
    def tearDown(self):self.temp.cleanup()
    def test_only_manifest_assets_are_served(self):
        response=self.workspace.response('/');self.assertEqual(response.status_code,200)
        self.assertIn("connect-src 'self'",response.headers['content-security-policy']);self.assertIn("frame-src 'none'",response.headers['content-security-policy'])
        self.assertNotIn('https:',response.headers['content-security-policy']);self.assertEqual(response.headers['cache-control'],'no-store')
        self.assertEqual(self.workspace.response('/../SECURITY.md').status_code,404)
        (self.folder/'private.txt').write_text('disposable fixture');self.assertEqual(self.workspace.response('/private.txt').status_code,404)
    def test_changed_assets_fail_closed(self):
        (self.folder/'index.html').write_bytes(b'changed');self.assertEqual(self.workspace.response('/').status_code,503)
    def test_manifest_cannot_escape_the_workspace(self):
        self.workspace.assets['/../outside.txt']={'bytes':0,'sha256':'','type':'text/plain'}
        self.assertEqual(self.workspace.response('/../outside.txt').status_code,503)
