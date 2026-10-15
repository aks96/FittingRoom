import {test} from 'node:test';
import assert from 'node:assert/strict';
import {pairEngine,engineHealth,engineRequest,isPaired,hasEngineSession,disconnectEngine,clearPairing} from '../lib/engine.ts';

test('local pairing gates image requests and detects engine restart and expiry',async()=>{
 const original=globalThis.fetch;
 const calls:{url:string;options?:RequestInit}[]=[];
 let now=Date.now(),paired=false;
 globalThis.fetch=async(url,options)=>{
  calls.push({url:String(url),options});
  if(String(url).endsWith('/pair')){paired=true;return Response.json({token:'test-session',challenge:'test-challenge',expiresAt:now+10000})}
  if(String(url).endsWith('/health'))return Response.json({ready:true,paired,localOnly:true});
  return Response.json({ok:true});
 };
 try{
  clearPairing();await assert.rejects(engineRequest('/analyze',{image:'photo'}),/Connect the local engine/);assert.equal(calls.length,0);
  await pairEngine('private-code');assert.ok(isPaired());assert.ok(calls[0].options?.signal);assert.equal((await engineHealth()).ready,true);
  await engineRequest('/analyze',{image:'photo'});assert.equal((calls.at(-1)?.options?.headers as Record<string,string>).Authorization,'Bearer test-session');
  paired=false;assert.equal((await engineHealth()).ready,false);assert.equal(isPaired(),false);
  await assert.rejects(engineRequest('/tryon',{person:'photo'}),/Connect the local engine/);
  now=Date.now()-20000;await pairEngine('private-code');assert.equal(isPaired(),false);
  await assert.rejects(engineRequest('/arbitrary-command',{}),/Invalid engine route/);
 }finally{clearPairing();globalThis.fetch=original}
});

test('pairing failures explain wrong codes and an unavailable local engine',async()=>{
 const original=globalThis.fetch;
 try{
  globalThis.fetch=async()=>Response.json({detail:'Incorrect pairing code. Check the local terminal.'},{status:401});
  await assert.rejects(pairEngine('wrong'),/Incorrect pairing code/);assert.equal(isPaired(),false);
  globalThis.fetch=async()=>{throw new TypeError('fetch failed')};
  await assert.rejects(pairEngine('code'),/Open Start AI.command/);assert.equal(isPaired(),false);
 }finally{clearPairing();globalThis.fetch=original}
});

test('withdrawal blocks image requests immediately and retains credentials only for failed cleanup retry',async()=>{
 const original=globalThis.fetch;let fail=true;let revokeRequests=0;
 globalThis.fetch=async(url)=>{
  if(String(url).endsWith('/pair'))return Response.json({token:'test-session',challenge:'test-challenge',expiresAt:Date.now()+10000});
  if(String(url).endsWith('/session/revoke')){revokeRequests++;if(fail)throw new TypeError('offline');return Response.json({revoked:true,cancelled:1,purged:1})}
  return Response.json({ok:true});
 };
 try{
  clearPairing();await pairEngine('code');await assert.rejects(disconnectEngine(),/cleanup is not confirmed/);
  assert.equal(isPaired(),false);assert.equal(hasEngineSession(),true);
  await assert.rejects(engineRequest('/analyze',{image:'test'}),/Connect the local engine/);
  fail=false;assert.equal((await disconnectEngine()).revoked,true);assert.equal(isPaired(),false);assert.equal(revokeRequests,2);
 }finally{clearPairing();globalThis.fetch=original}
});

test('an image response arriving after consent withdrawal is discarded',async()=>{
 const original=globalThis.fetch;let finish:((response:Response)=>void)|undefined;
 globalThis.fetch=async(url)=>{
  if(String(url).endsWith('/pair'))return Response.json({token:'test-session',challenge:'test-challenge',expiresAt:Date.now()+10000});
  if(String(url).endsWith('/session/revoke'))return Response.json({revoked:true,cancelled:1,purged:0});
  return new Promise<Response>(resolve=>{finish=resolve});
 };
 try{
  clearPairing();await pairEngine('code');const inFlight=engineRequest('/analyze',{image:'test'});
  const rejected=assert.rejects(inFlight,/response was discarded/);
  await disconnectEngine();finish!(Response.json({colour:'Red'}));await rejected;
 }finally{clearPairing();globalThis.fetch=original}
});
