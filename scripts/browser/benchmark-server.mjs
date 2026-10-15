// Local developer benchmark. Fixed GET assets only; no image or filesystem API.
import http from 'node:http';
import {createReadStream} from 'node:fs';
import {stat} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const assets=new Map([
 ['/', ['scripts/browser/benchmark.html','text/html']],
 ['/preview',['scripts/browser/preview-benchmark.html','text/html']],
 ['/preview-worker.js',['scripts/browser/preview-benchmark-worker.mjs','text/javascript']],
 ['/public-fixture.bin',['.runtime/browser-public-fixture.bin','application/octet-stream']],
 ['/public-fixture.json',['.runtime/browser-public-fixture.json','application/json']],
 ['/native-preview.png',['.runtime/browser-native-baseline.png','image/png']],
 ['/worker.js',['scripts/browser/benchmark-worker.mjs','text/javascript']],
 ['/ort.mjs',['node_modules/onnxruntime-web/dist/ort.webgpu.bundle.min.mjs','text/javascript']],
 ['/graph.onnx',['.runtime/browser-models/denoiser.onnx','application/octet-stream']],
 ['/candidate.onnx',['.runtime/browser-models/denoiser.webgpu.onnx','application/octet-stream']],
 ['/candidate-fp16.onnx',['.runtime/browser-models/denoiser.webgpu-fp16.onnx','application/octet-stream']],
 ['/reference.f32',['.runtime/browser-synthetic-reference.f32','application/octet-stream']],
 ['/weights.bin',['.runtime/browser-models/denoiser.onnx.data','application/octet-stream']],
 ['/manifest.json',['.runtime/browser-models/manifest.json','application/json']],
]);
for(const variant of ['','\.jsep','\.asyncify','\.jspi'].map(x=>x.replace('\\',''))){
 for(const ext of ['mjs','wasm']){const name=`ort-wasm-simd-threaded${variant}.${ext}`;assets.set('/'+name,['node_modules/onnxruntime-web/dist/'+name,ext==='wasm'?'application/wasm':'text/javascript'])}
}
const server=http.createServer(async(req,res)=>{
 const host=req.headers.host;if(!['127.0.0.1:3001','localhost:3001'].includes(host)||req.method!=='GET'){res.writeHead(403);res.end();return}
 const entry=assets.get(new URL(req.url,'http://127.0.0.1:3001').pathname);
 if(!entry){res.writeHead(404);res.end();return}
 try{const file=path.join(root,entry[0]),info=await stat(file);res.writeHead(200,{'Content-Type':entry[1],'Content-Length':info.size,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; img-src 'self' data:; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; worker-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'"});createReadStream(file).pipe(res)}catch{res.writeHead(503);res.end('Prepared local model is unavailable.')}
});
server.listen(3001,'127.0.0.1',()=>console.log('Synthetic browser benchmark: http://127.0.0.1:3001'));
