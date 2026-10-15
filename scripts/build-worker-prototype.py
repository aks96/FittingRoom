"""Build an ad-hoc-signed local App Sandbox probe, never a distributable notarized release."""
import json,plistlib,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
app=ROOT/'.runtime/app-sandbox-prototype/InferenceWorker.app'
mac=app/'Contents/MacOS';mac.mkdir(parents=True,exist_ok=True)
exe=mac/'InferenceWorker';shutil.copyfile(Path(sys.executable).resolve(),exe);exe.chmod(0o755)
info={'CFBundleIdentifier':'local.yourfittingroom.inference','CFBundleExecutable':'InferenceWorker','CFBundleName':'yourFittingRoom Inference Worker','CFBundleVersion':'1','CFBundlePackageType':'APPL'}
(app/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
cache=ROOT/'.runtime/app-sandbox-prototype/cache';cache.mkdir(exist_ok=True)
code=ROOT/'.runtime/app-sandbox-prototype/code';(code/'local_ai').mkdir(parents=True,exist_ok=True)
for name in ['inference.py','garment_details.py','garment_catalog.py','compute.py','protocol.py','worker.py']:shutil.copyfile(ROOT/'local_ai'/name,code/'local_ai'/name)
(code/'security').mkdir(exist_ok=True)
shutil.copyfile(ROOT/'security/garment-catalog.json',code/'security/garment-catalog.json')
(code/'local_ai/__init__.py').write_text('')
(code/'.runtime').mkdir(exist_ok=True)
for name,target in [('weights',ROOT/'.runtime/weights')]:
    link=code/'.runtime'/name
    if not link.exists():link.symlink_to(target,target_is_directory=True)
read=[code,Path(sys.base_prefix),Path(sys.prefix),ROOT/'local_ai',ROOT/'security',ROOT/'.runtime/weights',ROOT/'.runtime/fashn-src/src']
entitlements={'com.apple.security.app-sandbox':True,
 'com.apple.security.temporary-exception.files.absolute-path.read-only':[str(p.resolve())+'/' for p in read],
 'com.apple.security.temporary-exception.files.absolute-path.read-write':[str(cache.resolve())+'/']}
ent=ROOT/'.runtime/app-sandbox-prototype/worker.plist';ent.write_bytes(plistlib.dumps(entitlements))
subprocess.run(['/usr/bin/codesign','--force','--sign','-','--identifier','local.yourfittingroom.inference','--entitlements',str(ent),str(app)],check=True)
print('Internal App Sandbox probe built with ad-hoc identity; not notarized, not for public distribution.')
