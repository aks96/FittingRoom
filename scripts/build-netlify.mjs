// Local static export only. No Netlify CLI, credentials, network publication or AI startup.
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {photography,filesIn,digest,verifyDownloads,inlineScriptHashes,headersFile,assertPublishPaths} from './netlify-assets.mjs';

const root=process.cwd(),stage=path.join(root,'.runtime/netlify-build'),output=path.join(root,'netlify-dist');
const manifest=JSON.parse(await fs.readFile(path.join(root,'security/companion-downloads.json'),'utf8'));
await verifyDownloads(path.join(root,'public'),manifest);
await fs.rm(stage,{recursive:true,force:true});
await fs.mkdir(stage,{recursive:true});
// Stage trusted source separately. Only the download landing route is compiled.
for(const name of ['components','lib','workers','tsconfig.json','postcss.config.mjs'])await fs.cp(path.join(root,name),path.join(stage,name),{recursive:true});
await fs.mkdir(path.join(stage,'security'));
for(const name of ['companion-downloads.json','garment-catalog.json'])await fs.copyFile(path.join(root,'security',name),path.join(stage,'security',name));
await fs.mkdir(path.join(stage,'app'));
for(const name of ['layout.tsx','globals.css'])await fs.copyFile(path.join(root,'app',name),path.join(stage,'app',name));
await fs.writeFile(path.join(stage,'app/page.tsx'),"import DownloadLanding from '@/components/DownloadLanding';\nexport default function Page(){return <DownloadLanding/>}\n");
await fs.mkdir(path.join(stage,'public'));
await fs.writeFile(path.join(stage,'public/robots.txt'),'User-agent: *\nDisallow: /\n');
// Never copy the whole public directory: it also has the browser AI experiment.
for(const name of [...photography,...Object.values(manifest.packages).map(item=>item.filename)]){
 const source=path.join(root,'public',name);
 if(!(await fs.lstat(source)).isFile())throw new Error('Only regular allowlisted public files may be exported.');
 await fs.copyFile(source,path.join(stage,'public',name));
}
await fs.symlink(path.join(root,'node_modules'),path.join(stage,'node_modules'),'dir');
await fs.writeFile(path.join(stage,'package.json'),JSON.stringify({name:'yourfittingroom-static-downloads',type:'module',private:true}));
await fs.writeFile(path.join(stage,'next.config.ts'),"export default {output:'export',devIndicators:false,poweredByHeader:false,productionBrowserSourceMaps:false};\n");
const result=spawnSync(process.execPath,[path.join(root,'node_modules/next/dist/bin/next'),'build',stage],{
 stdio:'inherit',env:{...process.env,NEXT_TELEMETRY_DISABLED:'1',NEXT_PUBLIC_BUNDLED_WORKSPACE:'0'}
});
if(result.error)throw result.error;
if(result.status!==0)process.exit(result.status||1);
const exported=path.join(stage,'out');
const hashes=await inlineScriptHashes(exported,await filesIn(exported));
await fs.writeFile(path.join(exported,'_headers'),headersFile(hashes,manifest));
await fs.writeFile(path.join(exported,'checksums.txt'),Object.values(manifest.packages).map(item=>`${item.sha256}  ${item.filename}`).join('\n')+'\n');
const files=await filesIn(exported);
assertPublishPaths(files,manifest);
await verifyDownloads(exported,manifest);
// Do not replace a previous successful export until this build has passed its checks.
await fs.rm(output,{recursive:true,force:true});
await fs.cp(exported,output,{recursive:true});
const inventory={};
for(const name of files){const data=await fs.readFile(path.join(output,name));inventory[name]={bytes:data.length,sha256:digest(data)}}
await fs.writeFile(path.join(root,'.runtime/netlify-build-report.json'),JSON.stringify({kind:'static-download-website',deployed:false,assets:inventory,scriptHashes:hashes},null,2)+'\n');
console.log('Static website prepared in netlify-dist/. No APIs, photo workspace, model weights or hosting identity. Nothing deployed.');
