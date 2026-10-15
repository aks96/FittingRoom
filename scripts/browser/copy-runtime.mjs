import fs from 'node:fs/promises';
await fs.mkdir('public/browser-runtime',{recursive:true});
for(const name of await fs.readdir('node_modules/onnxruntime-web/dist'))if(/^ort-wasm-.*\.(mjs|wasm)$/.test(name))await fs.copyFile('node_modules/onnxruntime-web/dist/'+name,'public/browser-runtime/'+name);
console.log('Browser runtime copied locally; no CDN requests needed.');
