import fs from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
const stage=path.resolve('.runtime/companion-package/wearview-companion');await fs.rm(stage,{recursive:true,force:true});await fs.mkdir(stage,{recursive:true});
for(const item of ['local_ai','security'])await fs.cp(item,path.join(stage,item),{recursive:true,filter:source=>!source.includes('__pycache__')&&!source.endsWith('.pyc')});
await fs.mkdir(path.join(stage,'scripts'),{recursive:true});for(const file of ['ai.sh','setup-ai.sh'])await fs.copyFile('scripts/'+file,path.join(stage,'scripts',file));
for(const file of ['ai.sh','setup-ai.sh'])await fs.chmod(path.join(stage,'scripts',file),0o755);
const result=spawnSync('tar',['-czf',path.resolve('public/wearview-companion.tar.gz'),'-C',path.dirname(stage),'wearview-companion'],{stdio:'inherit'});if(result.status)process.exit(result.status);
console.log('Companion source archive created. No credentials, personal photos, virtual environment or weights included.');
