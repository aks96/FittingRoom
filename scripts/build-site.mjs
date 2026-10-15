// Preserve Next.js for local development; export its UI into a narrowly scoped Sites worker.
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const root=process.cwd(),stage=path.join(root,'.site-build');
await fs.rm(stage,{recursive:true,force:true});await fs.mkdir(stage,{recursive:true});
for(const item of ['app','components','lib','public','tsconfig.json','postcss.config.mjs'])await fs.cp(path.join(root,item),path.join(stage,item),{recursive:true});
await fs.mkdir(path.join(stage,'security'));for(const file of ['companion-downloads.json','garment-catalog.json'])await fs.copyFile(path.join(root,'security',file),path.join(stage,'security',file));
await fs.rm(path.join(stage,'app/api'),{recursive:true,force:true});
await fs.rm(path.join(stage,'app/development'),{recursive:true,force:true});
await fs.writeFile(path.join(stage,'package.json'),JSON.stringify({name:'yourfittingroom-site-ui',type:'module',private:true}));
await fs.writeFile(path.join(stage,'next.config.ts'),"export default {output:'export',devIndicators:false};\n");
const result=spawnSync(process.execPath,[path.join(root,'node_modules/next/dist/bin/next'),'build',stage],{stdio:'inherit',env:{...process.env,NEXT_TELEMETRY_DISABLED:'1'}});if(result.status!==0)process.exit(result.status||1);
const assets={},hashes=new Set();
const types={'.html':'text/html;charset=utf-8','.js':'text/javascript;charset=utf-8','.css':'text/css;charset=utf-8','.png':'image/png','.svg':'image/svg+xml','.ico':'image/x-icon','.woff2':'font/woff2','.txt':'text/plain;charset=utf-8','.gz':'application/gzip'};
async function scan(dir){for(const item of await fs.readdir(dir,{withFileTypes:true})){const filename=path.join(dir,item.name);if(item.isDirectory())await scan(filename);else{const data=await fs.readFile(filename),relative='/'+path.relative(path.join(stage,'out'),filename).split(path.sep).join('/');assets[relative]={type:types[path.extname(filename)]||'application/octet-stream',body:data.toString('base64')};if(filename.endsWith('.html'))for(const m of data.toString().matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)){if(m[1])hashes.add(createHash('sha256').update(m[1]).digest('base64'))}}}}
await scan(path.join(stage,'out'));await fs.rm(path.join(root,'dist'),{recursive:true,force:true});await fs.mkdir(path.join(root,'dist/server'),{recursive:true});await fs.mkdir(path.join(root,'dist/.openai'),{recursive:true});
await fs.copyFile(path.join(root,'hosting/worker.mjs'),path.join(root,'dist/server/index.js'));
await fs.writeFile(path.join(root,'dist/server/assets.mjs'),'export const assets='+JSON.stringify(assets)+';\nexport const scriptHashes='+JSON.stringify([...hashes])+';\n');
await fs.copyFile(path.join(root,'.openai/hosting.json'),path.join(root,'dist/.openai/hosting.json'));
console.log('Private Sites worker built. No photo proxy, model weights or personal photos included.');
