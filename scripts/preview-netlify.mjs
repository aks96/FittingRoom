// Loopback-only QA server for the static export. Never starts the AI companion.
import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {filesIn,assertPublishPaths,verifyDownloads} from './netlify-assets.mjs';

export function parseHeaders(text){
 const rules=[];let current;
 for(const line of text.split(/\r?\n/)){
  if(!line.trim()||line.trimStart().startsWith('#'))continue;
  if(line.startsWith('/')){current={path:line.trim(),headers:{}};rules.push(current)}
  else if(current){const i=line.indexOf(':');if(i<0)throw new Error('Invalid _headers file.');current.headers[line.slice(0,i).trim()]=line.slice(i+1).trim()}
 }
 return rules;
}

export async function createPreviewServer(directory){
 const manifest=JSON.parse(await fs.readFile('security/companion-downloads.json','utf8'));
 const files=await filesIn(directory);assertPublishPaths(files,manifest);await verifyDownloads(directory,manifest);
 const allowed=new Set(files.filter(name=>name!=='_headers'));
 const rules=parseHeaders(await fs.readFile(path.join(directory,'_headers'),'utf8'));
 const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.txt':'text/plain; charset=utf-8','.png':'image/png','.svg':'image/svg+xml','.woff2':'font/woff2','.gz':'application/gzip','.zip':'application/zip'};
 return http.createServer(async(req,res)=>{
  try{
   const url=new URL(req.url,'http://127.0.0.1');const pathname=decodeURIComponent(url.pathname);
   const headers={};
   for(const rule of rules){if(rule.path===pathname||(rule.path.endsWith('*')&&pathname.startsWith(rule.path.slice(0,-1))))Object.assign(headers,rule.headers)}
   if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,{...headers,Allow:'GET, HEAD'});res.end();return}
   const name=pathname==='/'?'index.html':pathname.slice(1);
   const found=allowed.has(name)&&!name.includes('..')&&!name.includes('\\');
   const target=path.join(directory,found?name:'404.html');
   const data=await fs.readFile(target);
   res.writeHead(found?200:404,{'Content-Type':types[path.extname(target)]||'application/octet-stream',...headers,'Content-Length':data.length});
   res.end(req.method==='HEAD'?undefined:data);
  }catch{res.writeHead(400,{'Content-Type':'text/plain','X-Content-Type-Options':'nosniff'});res.end('Invalid request.')}
 });
}

if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 const port=Number(process.env.PORT||3002);
 if(!Number.isInteger(port)||port<1024||port>65535)throw new Error('Use a port between 1024 and 65535.');
 const server=await createPreviewServer(path.resolve('netlify-dist'));
 server.listen(port,'127.0.0.1',()=>console.log(`Local static website: http://127.0.0.1:${port} — no deployment or AI worker.`));
}
