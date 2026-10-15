// Export the existing React UI for the user's own loopback broker. No hosting metadata or publication.
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const root=process.cwd(),stage=path.join(root,'.runtime/local-ui-build'),output=path.join(root,'.runtime/local-workspace');
await fs.rm(stage,{recursive:true,force:true});await fs.mkdir(stage,{recursive:true});
for(const item of ['components','lib','workers','tsconfig.json','postcss.config.mjs'])await fs.cp(path.join(root,item),path.join(stage,item),{recursive:true});
await fs.mkdir(path.join(stage,'security'));for(const file of ['companion-downloads.json','garment-catalog.json'])await fs.copyFile(path.join(root,'security',file),path.join(stage,'security',file));
await fs.mkdir(path.join(stage,'app'));for(const item of ['layout.tsx','globals.css'])await fs.copyFile(path.join(root,'app',item),path.join(stage,'app',item));
await fs.writeFile(path.join(stage,'app/page.tsx'),"import YourFittingRoom from '@/components/YourFittingRoom';\nexport default function Page(){return <YourFittingRoom/>}\n");
await fs.mkdir(path.join(stage,'public'));for(const item of ['sample-plum-garment.png','sample-sage-garment.png','sample-original.png','sample-photography.png'])await fs.copyFile(path.join(root,'public',item),path.join(stage,'public',item));
await fs.symlink(path.join(root,'node_modules'),path.join(stage,'node_modules'),'dir');
await fs.writeFile(path.join(stage,'package.json'),JSON.stringify({name:'yourfittingroom-local-workspace',type:'module',private:true}));
await fs.writeFile(path.join(stage,'next.config.ts'),"export default {output:'export',devIndicators:false,poweredByHeader:false};\n");
const result=spawnSync(process.execPath,[path.join(root,'node_modules/next/dist/bin/next'),'build',stage],{stdio:'inherit',env:{...process.env,NEXT_TELEMETRY_DISABLED:'1',NEXT_PUBLIC_BUNDLED_WORKSPACE:'1'}});if(result.status!==0)process.exit(result.status||1);
await fs.rm(output,{recursive:true,force:true});await fs.cp(path.join(stage,'out'),output,{recursive:true});
const assets={},hashes=new Set();
const types={'.html':'text/html;charset=utf-8','.js':'text/javascript;charset=utf-8','.css':'text/css;charset=utf-8','.png':'image/png','.svg':'image/svg+xml','.ico':'image/x-icon','.woff2':'font/woff2','.txt':'text/plain;charset=utf-8'};
async function scan(folder){for(const entry of await fs.readdir(folder,{withFileTypes:true})){const filename=path.join(folder,entry.name);if(entry.isDirectory())await scan(filename);else{const data=await fs.readFile(filename),url='/'+path.relative(output,filename).split(path.sep).join('/');assets[url]={sha256:createHash('sha256').update(data).digest('hex'),bytes:data.length,type:types[path.extname(filename)]||'application/octet-stream'};if(filename.endsWith('.html'))for(const match of data.toString().matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g))if(match[1])hashes.add(createHash('sha256').update(match[1]).digest('base64'))}}}
await scan(output);await fs.writeFile(path.join(output,'manifest.json'),JSON.stringify({kind:'local-workspace',version:'0.2.0-development',assets,scriptHashes:[...hashes]},null,2));
console.log('Local workspace built. Contains fixed UI assets; no photos, credentials, dependencies, model weights or hosting configuration.');
