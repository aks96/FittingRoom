// The hosted site never proxies photos. Credentials exist only in this tab's memory.
const BASE='http://127.0.0.1:8765';
let pairing:{token:string;challenge:string;expiresAt:number}|null=null;
export function isPaired(){return !!pairing&&pairing.expiresAt>Date.now()}
export function disconnectEngine(){pairing=null}
export async function engineRequest<T>(path:string,body?:unknown,permit?:string):Promise<T>{
 if(!/^\/(health|pair|analyze|tryon|jobs\/[a-f0-9]{32})$/.test(path))throw new Error('Invalid engine route.');
 if(path!='/health'&&!isPaired())throw new Error('Connect the local engine with the pairing code shown in its terminal.');
 const response=await fetch(BASE+path,{method:body!==undefined?'POST':'GET',headers:{...(body!==undefined?{'Content-Type':'application/json'}:{}),...(pairing?{Authorization:`Bearer ${pairing.token}`} :{}),...(permit?{'X-WearView-Permit':permit}:{})},body:body!==undefined?JSON.stringify(body):undefined,cache:'no-store',signal:AbortSignal.timeout(path==='/analyze'?300000:20000)});
 const data=await response.json();if(!response.ok){const error=new Error(data.detail||'Local engine unavailable. Your images are kept.');Object.assign(error,{status:response.status});throw error}return data;
}
export async function pairEngine(code:string){
 const response=await fetch(BASE+'/pair',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${code.trim()}`},body:'{}',cache:'no-store'});
 const data=await response.json();if(!response.ok)throw new Error(data.detail||'Pairing failed.');
 if(typeof data.token!=='string'||typeof data.challenge!=='string'||typeof data.expiresAt!=='number')throw new Error('Invalid engine response.');pairing=data;
}
export async function engineHealth(){const data=await engineRequest<{ready:boolean;device:string;model:string;loaded:boolean;localOnly:boolean}>('/health');return {...data,ready:data.ready&&isPaired()}}
export async function generationPermit():Promise<string|undefined>{
 if(!isPaired())throw new Error('Pair the local engine first.');
 if(['localhost','127.0.0.1'].includes(location.hostname))return undefined; // Explicit local development, protected by pairing.
 const response=await fetch('/api/auth/permit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({challenge:pairing!.challenge}),cache:'no-store'});
 const data=await response.json();if(!response.ok)throw new Error(data.error||'Sign in to generate. Your selected photos remain in this tab.');
 if(typeof data.permit!=='string')throw new Error('Generation permission unavailable.');return data.permit;
}
export function signIn(){if(['localhost','127.0.0.1'].includes(location.hostname))throw new Error('Local development uses device pairing. Managed sign-in is available on the private hosted beta.');const popup=window.open('/signin-with-chatgpt?return_to=%2Fauth%2Ffinish','yourfittingroom-signin','popup,width=520,height=720');if(!popup)throw new Error('Allow the sign-in popup, then retry. Your photo stays in this tab.')}
export function cancelOnExit(id:string){if(pairing)void fetch(BASE+'/jobs/'+id,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${pairing.token}`},body:'{}',keepalive:true}).catch(()=>{})}
