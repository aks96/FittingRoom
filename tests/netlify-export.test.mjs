import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {once} from 'node:events';
import {filesIn,assertPublishPaths,verifyDownloads,inlineScriptHashes,digest} from '../scripts/netlify-assets.mjs';
import {parseHeaders,createPreviewServer} from '../scripts/preview-netlify.mjs';

const output=path.resolve('netlify-dist');
const manifest=JSON.parse(await fs.readFile('security/companion-downloads.json','utf8'));

test('publish artifact is an allowlisted static download site, with no developer/photo routes or weights',async()=>{
 const files=await filesIn(output);assertPublishPaths(files,manifest);
 for(const name of ['api/ai/tryon/route.js','development/fitting-room.html','.env','private-photo.jpg','model.onnx','_next/static/debug.js.map']){
  assert.throws(()=>assertPublishPaths([...files,name],manifest),/Unexpected file/);
 }
 assert.ok(!files.some(name=>/api\/|development\/|browser-runtime|\.openai|\.runtime|\.wasm$/.test(name)));
 const html=await fs.readFile(path.join(output,'index.html'),'utf8');
 assert.match(html,/Get the companion/);assert.doesNotMatch(html,/<input[^>]+type="file"/);
 assert.match(await fs.readFile(path.join(output,'robots.txt'),'utf8'),/Disallow: \//);
});

test('CSP authorizes the exact Next inline scripts without permitting arbitrary inline or remote scripts',async()=>{
 const rules=parseHeaders(await fs.readFile(path.join(output,'_headers'),'utf8'));
 const headers=rules.find(rule=>rule.path==='/*').headers;
 const csp=headers['Content-Security-Policy'];
 const scripts=csp.split(';').find(part=>part.trim().startsWith('script-src '));
 const hashes=await inlineScriptHashes(output,await filesIn(output));
 assert.ok(hashes.length>0);for(const hash of hashes)assert.ok(scripts.includes(`'sha256-${hash}'`));
 assert.doesNotMatch(scripts,/unsafe-inline|unsafe-eval|https:|http:/);
 for(const directive of ["connect-src 'self'","worker-src 'none'","frame-ancestors 'none'","form-action 'none'"])assert.ok(csp.includes(directive));
 assert.equal(headers['X-Content-Type-Options'],'nosniff');assert.equal(headers['Referrer-Policy'],'no-referrer');
});

test('both exported downloads and public checksums match the source metadata',async()=>{
 await verifyDownloads(output,manifest);
 const checksums=await fs.readFile(path.join(output,'checksums.txt'),'utf8');
 for(const item of Object.values(manifest.packages)){
  assert.ok(checksums.includes(`${item.sha256}  ${item.filename}`));
 }
 const invalid=structuredClone(manifest);invalid.packages.mac.sha256='0'.repeat(64);
 await assert.rejects(()=>verifyDownloads(output,invalid),/differs from its metadata/);
});

test('HTTP preview serves the exact downloads with attachment headers and refuses unavailable routes/methods',async t=>{
 const server=await createPreviewServer(output);
 server.listen(0,'127.0.0.1');await once(server,'listening');
 t.after(()=>new Promise(resolve=>{server.close(resolve);server.closeAllConnections()}));
 const base=`http://127.0.0.1:${server.address().port}`;
 const page=await fetch(base);assert.equal(page.status,200);assert.ok(page.headers.get('content-security-policy'));
 for(const item of Object.values(manifest.packages)){
  const response=await fetch(base+'/'+item.filename);assert.equal(response.status,200);
  assert.equal(response.headers.get('content-disposition'),`attachment; filename="${item.filename}"`);
  assert.equal(digest(Buffer.from(await response.arrayBuffer())),item.sha256);
 }
 for(const url of ['/api/ai/tryon','/development/fitting-room','/.env','/.openai/hosting.json'])assert.equal((await fetch(base+url)).status,404);
 assert.equal((await fetch(base,{method:'POST',body:'disposable test'})).status,405);
});
