// Developer-local delivery of prepared models only. Never accepts photos, paths or arbitrary URLs.
import {createReadStream} from 'node:fs';
import {stat,readFile} from 'node:fs/promises';
import path from 'node:path';
import {Readable} from 'node:stream';
export const runtime='nodejs';
const allowed=new Set(['manifest.json','garment.onnx','parser.onnx','denoiser.onnx','denoiser.onnx.data','pose.onnx']);
export async function GET(request:Request,{params}:{params:Promise<{name:string}>}){
 const url=new URL(request.url);if(!['127.0.0.1','localhost'].includes(url.hostname))return Response.json({error:'Browser model delivery is available only in local development.'},{status:403});
 const {name}=await params;if(!allowed.has(name))return new Response('Not found',{status:404});
 const filename=path.join(process.cwd(),'.runtime/browser-models',name);
 try{const info=await stat(filename);if(name==='manifest.json')return new Response(await readFile(filename),{headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
 return new Response(Readable.toWeb(createReadStream(filename)) as ReadableStream,{headers:{'Content-Type':'application/octet-stream','Content-Length':String(info.size),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}})}catch{return Response.json({error:'Browser models have not been prepared by the developer yet. No personal image was processed.'},{status:503})}
}
