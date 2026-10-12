// Runs only behind Sites' trusted identity dispatcher. Never deploy this worker directly.
import {assets,scriptHashes} from './assets.mjs';
export const SITE='https://wearview-desktop-beta.kumar-ankush0796.chatgpt.site';
const utf8=new TextEncoder();
function b64url(bytes){return btoa(String.fromCharCode(...new Uint8Array(bytes))).replaceAll('+','-').replaceAll('/','_').replaceAll('=','')}
const headers={
 'Content-Security-Policy':`default-src 'self'; script-src 'self' ${scriptHashes.map(h=>"'sha256-"+h+"'").join(' ')}; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self' http://127.0.0.1:8765; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'`,
 'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Permissions-Policy':'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
 'Cross-Origin-Opener-Policy':'same-origin-allow-popups','Cache-Control':'no-store','Strict-Transport-Security':'max-age=31536000'
};
export function identity(request){return new URL(request.url).origin===SITE ? request.headers.get('oai-authenticated-user-id') : null}
function json(data,status=200){return Response.json(data,{status,headers})}
export default {async fetch(request,env){
 const url=new URL(request.url),path=url.pathname;
 if(path==='/api/auth/session')return json({authenticated:!!identity(request)});
 if(path==='/api/auth/permit'){
  if(request.method!=='POST')return json({error:'POST required.'},405);
  if(request.headers.get('origin')!==SITE||request.headers.get('content-type')!=='application/json')return json({error:'Invalid request origin.'},403);
  const user=identity(request);if(!user)return json({error:'Sign in for generation. Your photos stay in this tab.'},401);
  if(!env.WEARVIEW_SIGNING_KEY)return json({error:'Authentication configuration unavailable. Generation remains disabled.'},503);
  try{
   const reader=request.body?.getReader();if(!reader)return json({error:'Challenge required.'},400);
   let text='',bytes=0;const decoder=new TextDecoder();while(true){const {done,value}=await reader.read();if(done)break;bytes+=value.length;if(bytes>2048){await reader.cancel();return json({error:'Request too large.'},413)}text+=decoder.decode(value,{stream:true})}text+=decoder.decode();
   const body=JSON.parse(text);if(Object.keys(body).length!==1||typeof body.challenge!=='string'||!/^[\w-]{32}$/.test(body.challenge))return json({error:'Invalid engine challenge.'},400);
   const now=Math.floor(Date.now()/1000),sub=b64url(await crypto.subtle.digest('SHA-256',utf8.encode(user)));
   const payload=b64url(utf8.encode(JSON.stringify({iss:SITE,aud:body.challenge,sub,iat:now,exp:now+120})));
   const key=await crypto.subtle.importKey('jwk',JSON.parse(env.WEARVIEW_SIGNING_KEY),{name:'Ed25519'},false,['sign']);
   const signature=b64url(await crypto.subtle.sign({name:'Ed25519'},key,utf8.encode(payload)));
   return json({permit:payload+'.'+signature});
  }catch{return json({error:'Could not authorize generation. Try signing in again.'},400)}
 }
 if(path.startsWith('/api/ai/')||path==='/api/product-image')return json({detail:'Hosted photo processing is disabled. Use the paired local companion.'},410);
 if(path==='/api/import')return json({error:'Link import is unavailable in this private beta. Upload the clothing image instead.'},503);
 if(path.startsWith('/api/'))return json({error:'Not found.'},404);
 if(!['GET','HEAD'].includes(request.method))return json({error:'Method not allowed.'},405);
 if(path==='/auth/finish')return new Response('<!doctype html><html lang="en"><meta charset="utf-8"><title>yourFittingRoom sign-in</title><p>Sign-in finished. Return to yourFittingRoom and select Try it on.</p><script src="/auth/finish.js"></script></html>',{headers:{...headers,'Content-Type':'text/html;charset=utf-8'}});
 if(path==='/auth/finish.js')return new Response("if(window.opener){window.opener.postMessage('wearview-auth-finished',location.origin);window.close()}",{headers:{...headers,'Content-Type':'text/javascript;charset=utf-8'}});
 const asset=assets[path==='/'?'/index.html':path]||assets[path+'.html'];
 if(!asset)return new Response('Not found',{status:404,headers});
 const bytes=Uint8Array.from(atob(asset.body),c=>c.charCodeAt(0));
 return new Response(request.method==='HEAD'?null:bytes,{headers:{...headers,'Content-Type':asset.type,...(path.startsWith('/_next/static/')?{'Cache-Control':'public,max-age=31536000,immutable'}:{})}});
}};
