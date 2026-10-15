import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';

export const photography=['sample-plum-garment.png','sample-sage-garment.png','sample-original.png','sample-photography.png'];
export const digest=data=>createHash('sha256').update(data).digest('hex');
export const scriptDigest=data=>createHash('sha256').update(data).digest('base64');

export async function filesIn(directory,prefix=''){
 const files=[];
 for(const entry of await fs.readdir(path.join(directory,prefix),{withFileTypes:true})){
  const name=path.posix.join(prefix,entry.name);
  if(entry.isSymbolicLink())throw new Error('Symbolic links cannot be published: '+name);
  if(entry.isDirectory())files.push(...await filesIn(directory,name));
  else if(entry.isFile())files.push(name);
  else throw new Error('Unsupported publish file: '+name);
 }
 return files.sort();
}

export async function verifyDownloads(directory,manifest){
 for(const item of Object.values(manifest.packages)){
  if(!/^yourFittingRoom-companion(?:-windows)?\.(?:tar\.gz|zip)$/.test(item.filename))throw new Error('Unexpected download filename.');
  const data=await fs.readFile(path.join(directory,item.filename));
  if(data.length!==item.bytes||digest(data)!==item.sha256)throw new Error('Download differs from its metadata: '+item.filename+'. Rebuild companion downloads first.');
 }
}

export async function inlineScriptHashes(directory,files){
 const hashes=new Set();
 for(const name of files.filter(file=>file.endsWith('.html'))){
  const html=await fs.readFile(path.join(directory,name),'utf8');
  for(const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g))if(match[1])hashes.add(scriptDigest(match[1]));
 }
 return [...hashes].sort();
}

export function securityHeaders(hashes){
 return {
  'Content-Security-Policy':[
   "default-src 'none'",`script-src 'self' ${hashes.map(hash=>`'sha256-${hash}'`).join(' ')}`,
   "script-src-attr 'none'","style-src 'self' 'unsafe-inline'","img-src 'self' data:","font-src 'self'",
   "connect-src 'self'","worker-src 'none'","frame-src 'none'","object-src 'none'",
   "base-uri 'none'","frame-ancestors 'none'","form-action 'none'"
  ].join('; '),
  'X-Content-Type-Options':'nosniff',
  'X-Frame-Options':'DENY',
  'Referrer-Policy':'no-referrer',
  'Permissions-Policy':'camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=()',
  'Cross-Origin-Opener-Policy':'same-origin',
  'Cross-Origin-Resource-Policy':'same-origin',
  'Strict-Transport-Security':'max-age=31536000',
  'X-Robots-Tag':'noindex, nofollow'
 };
}

export function headersFile(hashes,manifest){
 const block=(route,values)=>route+'\n'+Object.entries(values).map(([key,value])=>`  ${key}: ${value}`).join('\n');
 return [
  '# Generated for the exact exported HTML. Rebuild after any website change.',
  block('/*',securityHeaders(hashes)),
  ...['/','/index.html','/404.html','/index.txt','/checksums.txt'].map(route=>block(route,{'Cache-Control':'public, max-age=0, must-revalidate'})),
  block('/_next/static/*',{'Cache-Control':'public, max-age=31536000, immutable'}),
  ...Object.values(manifest.packages).map(item=>block('/'+item.filename,{
   'Content-Type':item.format==='ZIP'?'application/zip':'application/gzip',
   'Content-Disposition':`attachment; filename="${item.filename}"`,
   'Cache-Control':'public, max-age=0, must-revalidate'
  }))
 ].join('\n\n')+'\n';
}

export function assertPublishPaths(files,manifest){
 const rootFiles=new Set(['index.html','404.html','index.txt','_not-found.html','_not-found.txt','_headers','robots.txt','checksums.txt',...photography,...Object.values(manifest.packages).map(item=>item.filename)]);
 for(const name of files){
  if(rootFiles.has(name))continue;
  if(name.startsWith('_next/static/')&&/\.(?:js|css|woff2?|png|svg|ico)$/.test(name)&&!name.includes('..'))continue;
  throw new Error('Unexpected file in static publish directory: '+name);
 }
 for(const required of ['index.html','404.html','_headers','robots.txt','checksums.txt',...photography,...Object.values(manifest.packages).map(item=>item.filename)]){
  if(!files.includes(required))throw new Error('Missing publish file: '+required);
 }
}
