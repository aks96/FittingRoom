import fs from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {createHash} from 'node:crypto';
// Explicit release allowlist: never recursively copy credentials or user files.
const common=[
 'local_ai/source_integrity.py','local_ai/server.py','local_ai/security.py','local_ai/download_models.py','local_ai/finish_setup.py','local_ai/garment_details.py','local_ai/garment_catalog.py',
 'local_ai/sessions.py','local_ai/inference.py','local_ai/compute.py','local_ai/isolation.py','local_ai/protocol.py','local_ai/supervisor.py','local_ai/worker.py','local_ai/workspace.py',
 'local_ai/requirements-bootstrap-hashed.txt','local_ai/requirements-lock.txt','local_ai/requirements.txt','local_ai/SETUP.md',
 'security/issuer.json','security/model-revisions.json','security/recognition-files.json','security/garment-catalog.json'
];
function run(program,args,options={}){const result=spawnSync(program,args,{stdio:'inherit',...options});if(result.error)throw result.error;if(result.status)throw new Error(`Packaging failed (${result.status}).`)}
const selected=process.argv[2]||'all';
if(!['all','mac','windows'].includes(selected))throw new Error('Choose all, mac or windows.');
const metadataPath=path.resolve('security/companion-downloads.json');
const metadata=JSON.parse(await fs.readFile(metadataPath,'utf8'));
async function countFiles(folder){let count=0;for(const entry of await fs.readdir(folder,{withFileTypes:true}))count+=entry.isDirectory()?await countFiles(path.join(folder,entry.name)):1;return count}
for(const platform of selected==='all'?['mac','windows']:[selected]){
 const stage=path.resolve(`.runtime/companion-package/${platform}/yourFittingRoom-companion`);
 await fs.rm(stage,{recursive:true,force:true});
 const files=[...common,...(platform==='mac'?['scripts/ai.sh','scripts/setup-ai.sh','scripts/build-worker-prototype.py','local_ai/setup_tls.py','local_ai/requirements-mac-hashed.txt']:['local_ai/windows_setup.py','local_ai/windows_start.py','local_ai/windows_native.py','local_ai/windows_worker.py','local_ai/windows_probe.py','local_ai/windows_validate.py','local_ai/windows_profiles.py','local_ai/windows_hardware.py','local_ai/windows_entry.py','local_ai/rocm_bootstrap.py','security/windows-compute.json','WINDOWS_TESTING.md','local_ai/requirements-windows.txt','local_ai/requirements-windows-bootstrap-hashed.txt','local_ai/requirements-windows-rocm-bootstrap-hashed.txt','local_ai/requirements-windows-rocm-constraints.txt'])];
 for(const file of files){const target=path.join(stage,file);await fs.mkdir(path.dirname(target),{recursive:true});await fs.copyFile(file,target);if(file.endsWith('.sh'))await fs.chmod(target,0o755)}
 for(const file of platform==='mac'?['Set up.command','Start AI.command']:['Set up.cmd','Start AI.cmd','Test Windows.cmd']){await fs.copyFile(path.join('scripts/companion',file),path.join(stage,file));await fs.chmod(path.join(stage,file),0o755)}
 await fs.copyFile('local_ai/SETUP.md',path.join(stage,'README.md'));
 const workspace=path.resolve('.runtime/local-workspace');
 const manifest=JSON.parse(await fs.readFile(path.join(workspace,'manifest.json'),'utf8'));
 for(const [url,record] of Object.entries(manifest.assets)){
  const source=path.resolve(workspace,'.'+url);if(!source.startsWith(workspace+path.sep))throw new Error('Invalid workspace path.');
  const data=await fs.readFile(source);if(data.length!==record.bytes||createHash('sha256').update(data).digest('hex')!==record.sha256)throw new Error('Workspace integrity failed.');
  const target=path.join(stage,'workspace',url.slice(1));await fs.mkdir(path.dirname(target),{recursive:true});await fs.writeFile(target,data);
 }
 await fs.copyFile(path.join(workspace,'manifest.json'),path.join(stage,'workspace/manifest.json'));
 if(platform==='mac')run('tar',['-czf',path.resolve('public/yourFittingRoom-companion.tar.gz'),'-C',path.dirname(stage),'yourFittingRoom-companion'],{env:{...process.env,COPYFILE_DISABLE:'1'}});
 else{
  const python=path.resolve('.runtime/ai-venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
  await fs.access(python); // Use the existing project Python, never an implicit OS installer.
  run(python,['scripts/zip-companion.py',stage,path.resolve('public/yourFittingRoom-companion-windows.zip')]);
 }
 const archive=await fs.readFile(path.resolve('public',metadata.packages[platform].filename));
 Object.assign(metadata.packages[platform],{bytes:archive.length,sha256:createHash('sha256').update(archive).digest('hex'),fileCount:await countFiles(stage)});
}
await fs.writeFile(metadataPath,JSON.stringify(metadata,null,2)+'\n');
console.log('Development source archives created with the fixed local workspace. Mac App Sandbox prototype; Windows worker is an unvalidated opt-in test candidate. No photos, secrets, environments or weights. Not signed production installers.');
