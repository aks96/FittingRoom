// Photo proxies are deliberately disabled: a hosted server must never process visitor photos.
export function sameOrigin(request:Request){const origin=request.headers.get('origin');try{return !!origin&&new URL(origin).origin===new URL(request.url).origin}catch{return false}}
export async function localAI(_path:string,_method='GET',_body?:unknown){return Response.json({detail:'Photo processing is available only through the paired local companion. This server never proxies personal photos.'},{status:410,headers:{'Cache-Control':'no-store'}})}
export async function limitedJson(_request:Request):Promise<never>{throw new Error('Cloud photo processing is disabled. Connect the local companion.')}
