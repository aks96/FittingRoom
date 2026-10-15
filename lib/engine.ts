// The hosted site never proxies photos. Credentials exist only in this tab's memory.
const BASE=process.env.NEXT_PUBLIC_BUNDLED_WORKSPACE==='1'?'':'http://127.0.0.1:8765';
let pairing:{token:string;challenge:string;expiresAt:number}|null=null;
export function hasEngineSession(){return pairing!==null}
export function isPaired(){return processingAllowed&&!!pairing&&pairing.expiresAt>Date.now()}
let processingAllowed=true;
export const consentWithdrawnEvent='yourfittingroom-consent-withdrawn';
function withdrawLocally(){processingAllowed=false;if(typeof window!=='undefined')window.dispatchEvent(new Event(consentWithdrawnEvent))}
export function clearPairing(){pairing=null;processingAllowed=true}
export async function disconnectEngine(){
 const current=pairing;withdrawLocally();
 if(!current){clearPairing();return {revoked:true,cancelled:0,purged:0}}
 try{
  const response=await localFetch(BASE+'/session/revoke',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${current.token}`},body:'{}',cache:'no-store',signal:AbortSignal.timeout(20000)});
  if(response.status===401){clearPairing();return {revoked:true,cancelled:0,purged:0}}
  const data=await response.json();if(!response.ok||data.revoked!==true)throw new Error('The engine did not confirm session cleanup.');
  clearPairing();return data as {revoked:boolean;cancelled:number;purged:number};
 }catch{throw new Error('Consent withdrawn in this tab, but engine cleanup is not confirmed. Retry Disconnect or stop the companion to end processing.');}
}
export function revokeOnExit(){if(pairing){withdrawLocally();void fetch(BASE+'/session/revoke',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${pairing.token}`},body:'{}',keepalive:true}).catch(()=>{})}}
export async function engineRequest<T>(path:string,body?:unknown,permit?:string):Promise<T>{
 if(!/^\/(health|pair|analyze|tryon|jobs\/[a-f0-9]{32})$/.test(path))throw new Error('Invalid engine route.');
 if(path!='/health'&&(!isPaired()||!processingAllowed))throw new Error('Connect the local engine with the pairing code shown in its terminal.');
 const session=pairing;
 const response=await localFetch(BASE+path,{method:body!==undefined?'POST':'GET',headers:{...(body!==undefined?{'Content-Type':'application/json'}:{}),...(session?{Authorization:`Bearer ${session.token}`} :{}),...(permit?{'X-WearView-Permit':permit}:{})},body:body!==undefined?JSON.stringify(body):undefined,cache:'no-store',signal:AbortSignal.timeout(path==='/analyze'?300000:20000)});
 const data=await response.json();if(!response.ok){const error=new Error(data.detail||'Local engine unavailable. Your images are kept.');Object.assign(error,{status:response.status});throw error}
 if(path!='/health'&&(!isPaired()||pairing!==session))throw Object.assign(new Error('The engine session ended. Its response was discarded.'),{status:401});return data;
}
export async function pairEngine(code:string){
 if(pairing&&!processingAllowed)await disconnectEngine();
 const response=await localFetch(BASE+'/pair',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${code.trim()}`},body:'{}',cache:'no-store',signal:AbortSignal.timeout(20000)});
 const data=await response.json();if(!response.ok)throw new Error(data.detail||'Pairing failed.');
 if(typeof data.token!=='string'||typeof data.challenge!=='string'||typeof data.expiresAt!=='number')throw new Error('Invalid engine response.');pairing=data;processingAllowed=true;
}
export async function engineHealth(){const session=pairing;const data=await engineRequest<{ready:boolean;paired:boolean;cleanupPending?:boolean;device:string;model:string;loaded:boolean;localOnly:boolean;isolation?:string;error?:string|null}>('/health');if(pairing===session&&!data.paired&&!data.cleanupPending)clearPairing();return {...data,ready:data.ready&&data.paired&&pairing===session&&isPaired()}}
async function localFetch(url:string,options:RequestInit){try{return await fetch(url,options)}catch(error){if(error instanceof Error&&['TimeoutError','AbortError'].includes(error.name))throw new Error('The local engine did not respond in time. Keep the companion’s command window open and check again. Your selected images are kept.');throw new Error('Cannot reach this computer’s companion. Open Start AI.command (Mac) or Start AI.cmd (Windows), wait for startup, then retry. If asked, allow local-network access only for this app; do not disable browser security.')}}
export async function generationPermit():Promise<string|undefined>{
 if(!isPaired()||!processingAllowed)throw new Error('Pair the local engine with consent first.');
 if(['localhost','127.0.0.1'].includes(location.hostname))return undefined; // Explicit local development, protected by pairing.
 const response=await fetch('/api/auth/permit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({challenge:pairing!.challenge}),cache:'no-store'});
 const data=await response.json();if(!response.ok)throw new Error(data.error||'Sign in to generate. Your selected photos remain in this tab.');
 if(typeof data.permit!=='string')throw new Error('Generation permission unavailable.');return data.permit;
}
export function signIn(){if(['localhost','127.0.0.1'].includes(location.hostname))throw new Error('Local development uses device pairing. Managed sign-in is available on the private hosted beta.');const popup=window.open('/signin-with-chatgpt?return_to=%2Fauth%2Ffinish','yourfittingroom-signin','popup,width=520,height=720');if(!popup)throw new Error('Allow the sign-in popup, then retry. Your photo stays in this tab.')}
export function cancelOnExit(id:string){if(pairing)void fetch(BASE+'/jobs/'+id,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${pairing.token}`},body:'{}',keepalive:true}).catch(()=>{})}
