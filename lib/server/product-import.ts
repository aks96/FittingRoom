import https from 'node:https';
import {lookup} from 'node:dns/promises';
import {isIP} from 'node:net';

export class ImportFailure extends Error {status:number;constructor(message:string,status=422){super(message);this.status=status}}
export function publicAddress(address:string):boolean {
 if(isIP(address)===4){const [a,b]=address.split('.').map(Number);return !(a===0||a===10||a===127||a===169&&b===254||a===172&&b>=16&&b<=31||a===192&&(b===168||b===0)||a===100&&b>=64&&b<=127||a===198&&(b===18||b===19||b===51)||a===203&&b===0||a>=224)}
 if(isIP(address)===6)return /^[23][0-9a-f]{3}:/i.test(address)&&!/^2001:db8:/i.test(address);
 return false;
}
export function externalUrl(value:string):URL {
 let url:URL;try{url=new URL(value)}catch{throw new ImportFailure('Enter a complete HTTPS product or image URL.',400)}
 if(url.protocol!=='https:'||url.username||url.password||url.port&&url.port!=='443'||url.hostname==='localhost'||url.hostname.endsWith('.local')||url.hostname.endsWith('.internal'))throw new ImportFailure('Only public HTTPS product and image URLs are supported.',400);
 if(isIP(url.hostname.replace(/^\[|\]$/g,''))&&!publicAddress(url.hostname.replace(/^\[|\]$/g,'')))throw new ImportFailure('Private or local addresses cannot be imported.',400);
 url.hash='';return url;
}
export async function fetchPublic(value:string,maxBytes=4*1024*1024,redirects=0):Promise<{body:Buffer;type:string;url:string}> {
 const url=externalUrl(value);const addresses=await lookup(url.hostname.replace(/^\[|\]$/g,''),{all:true});
 if(!addresses.length||addresses.some(a=>!publicAddress(a.address)))throw new ImportFailure('This URL does not resolve to a public address.',400);
 const address=addresses.find(a=>a.family===4)||addresses[0];
 return new Promise((resolve,reject)=>{
 const request=https.get(url,{family:address.family,headers:{'User-Agent':'WearView/0.2 (product image preview)','Accept':'text/html,application/xhtml+xml,image/jpeg,image/png,image/webp'},lookup:(_host,_options,cb)=>cb(null,address.address,address.family)},response=>{
 const code=response.statusCode||500;
 if(code>=300&&code<400&&response.headers.location){response.resume();if(redirects>=4){reject(new ImportFailure('Too many redirects. Upload the clothing image instead.'));return}let dest:string;try{dest=new URL(response.headers.location,url).href}catch{reject(new ImportFailure('Invalid retailer redirect.'));return}fetchPublic(dest,maxBytes,redirects+1).then(resolve,reject);return}
 if(code===401||code===403||code===429){response.resume();reject(new ImportFailure('The retailer restricts access or requires verification. Upload a product image or screenshot instead.'));return}
 if(code<200||code>=300){response.resume();reject(new ImportFailure(`The retailer returned HTTP ${code}. Try an image upload instead.`));return}
 let size=0;const chunks:Buffer[]=[];response.on('data',(chunk:Buffer)=>{size+=chunk.length;if(size>maxBytes){request.destroy(new ImportFailure('The page or image is too large. Upload an image up to 10 MB instead.'));return}chunks.push(chunk)});
 response.on('end',()=>resolve({body:Buffer.concat(chunks),type:String(response.headers['content-type']||'').split(';')[0].toLowerCase(),url:url.href}));response.on('error',reject);
 });request.setTimeout(15000,()=>request.destroy(new ImportFailure('The retailer did not respond. Try uploading the clothing image.')));request.on('error',reject);
 });
}
function decode(s:string){return s.replace(/&(?:amp|quot|apos|lt|gt|#39|#x[0-9a-f]+|#\d+);/gi,x=>{const chars:Record<string,string>={'&amp;':'&','&quot;':'"','&apos;':"'",'&#39;':"'",'&lt;':'<','&gt;':'>'};if(chars[x.toLowerCase()])return chars[x.toLowerCase()];const n=x.startsWith('&#x')?parseInt(x.slice(3,-1),16):parseInt(x.slice(2,-1),10);return n<=0x10ffff?String.fromCodePoint(n):''})}
export type ImportedProduct={name:string;category:'Top'|'Shirt'|'Dress';images:string[];originalUrl:string;colour:string};
export function parseProduct(html:string,pageUrl:string):ImportedProduct {
 const metas=new Map<string,string[]>();
 for(const tag of html.match(/<meta\s[^>]*>/gi)||[]){const attrs=new Map<string,string>();for(const m of tag.matchAll(/([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g))attrs.set(m[1].toLowerCase(),decode(m[2]??m[3]));const key=attrs.get('property')||attrs.get('name');const content=attrs.get('content');if(key&&content)metas.set(key.toLowerCase(),[...(metas.get(key.toLowerCase())||[]),content])}
 const products:Record<string,unknown>[]=[];let visits=0;
 function visit(data:unknown){if(++visits>3000)return;if(Array.isArray(data)){data.forEach(visit);return}if(!data||typeof data!=='object')return;const o=data as Record<string,unknown>;const type=o['@type'];if(type==='Product'||type==='ProductGroup'||Array.isArray(type)&&type.includes('Product'))products.push(o);for(const v of Object.values(o))if(typeof v==='object')visit(v)}
 for(const match of html.matchAll(/<script\b[^>]*type\s*=\s*["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)){try{visit(JSON.parse(match[1]))}catch{/* malformed retailer structured data */}}
 const product=products[0];const name=String(product?.name||metas.get('og:title')?.[0]||decode(html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1]||'Imported garment')).replace(/<[^>]*>/g,'').trim().slice(0,200);
 const candidates:string[]=[];
 function images(value:unknown){if(typeof value==='string')candidates.push(value);else if(Array.isArray(value))value.forEach(images);else if(value&&typeof value==='object'){const o=value as Record<string,unknown>;images(o.url||o.contentUrl)}}
 products.forEach(p=>images(p.image));images(metas.get('og:image'));images(metas.get('og:image:secure_url'));images(metas.get('twitter:image'));
 const urls=Array.from(new Set(candidates.flatMap(v=>{try{return [externalUrl(new URL(v,pageUrl).href).href]}catch{return []}}))).slice(0,12);
 if(!urls.length)throw new ImportFailure('No usable product image was found. This page may need JavaScript or retailer sign-in. Upload its clothing image instead.');
 const descriptor=`${name} ${String(product?.category||'')} ${new URL(pageUrl).pathname}`.toLowerCase();
 return {name,images:urls,originalUrl:pageUrl,colour:String(product?.color||'Not specified').slice(0,80),category:/\bdress(?:es)?\b/.test(descriptor)?'Dress':/\bshirt(?:s)?\b/.test(descriptor)?'Shirt':'Top'};
}
