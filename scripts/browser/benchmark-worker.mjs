import * as ort from '/ort.mjs';
ort.env.wasm.wasmPaths='/';ort.env.wasm.numThreads=1;ort.env.wasm.proxy=false;
const tell=(message,report,done=false)=>postMessage({message,report,done});
const scratch=new Float32Array(1),bits=new Uint32Array(scratch.buffer);
function half(v){scratch[0]=v;const u=bits[0],sign=(u>>>16)&0x8000,e=((u>>>23)&255)-112,m=u&0x7fffff;if(e<=0)return e< -10?sign:sign|((m|0x800000)>>>(14-e));if(e>=31)return sign|0x7c00;return sign|(e<<10)|(m>>>13)}
function floats(data){if(!(data instanceof Uint16Array))return Float32Array.from(data);return Float32Array.from(data,h=>{const s=h&0x8000?-1:1,e=(h>>>10)&31,m=h&1023;return e===0?s*2**-14*m/1024:e===31?(m?NaN:s*Infinity):s*2**(e-15)*(1+m/1024)})}
onmessage=async(event)=>{const publicCase=event.data==='public';const report={kind:publicCase?'numerical denoiser check using native-preprocessed bundled public photos':'synthetic denoiser benchmark, no photos; not full generation',variants:[]};try{
 if(!navigator.gpu)throw new Error('WebGPU unavailable.');
 tell('Reading existing local model files. No model cache or photos are changed.');let mark=performance.now();
 const [graph,weights,candidate,fp16,torchReference]=await Promise.all(['/graph.onnx','/weights.bin','/candidate.onnx','/candidate-fp16.onnx','/reference.f32'].map(async p=>{const r=await fetch(p);if(!r.ok)throw new Error('Local model missing.');return new Uint8Array(await r.arrayBuffer())}));report.localReadSeconds=(performance.now()-mark)/1000;
 report.candidateSha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',candidate)),v=>v.toString(16).padStart(2,'0')).join('');
 const base={};for(const [name,channels] of [['x',3],['person',3],['garment',3],['person_pose',1],['garment_pose',1]])base[name]=new ort.Tensor('float16',Uint16Array.from({length:channels*432*288},(_,i)=>half(Math.sin(i*.017)*.6)),[1,channels,432,288]);
 base.t=new ort.Tensor('float16',new Uint16Array([half(.25)]),[1]);base.category=new ort.Tensor('int64',new BigInt64Array([1n]),[1]);base.mask=new ort.Tensor('bool',new Uint8Array([1]),[1]);
 if(publicCase){const [raw,meta]=await Promise.all([fetch('/public-fixture.bin').then(r=>r.arrayBuffer()),fetch('/public-fixture.json').then(r=>r.json())]);for(const entry of meta.tensors){base[entry.name].dispose();base[entry.name]=new ort.Tensor('float16',new Uint16Array(raw.slice(entry.offset,entry.offset+entry.bytes)),entry.dims)}report.fixture=meta.source}
 let reference;report.reference='original browser graph with standard ONNX attention';
 for(const variant of [{name:'original standard attention',level:'disabled',gpu:false,runs:1},{name:'equivalent ONNX attention function on GPU',level:'disabled',gpu:false,runs:2,candidate:true},{name:'equivalent attention + basic optimisation',level:'basic',gpu:false,runs:2,candidate:true}]){
  let session;const buffers=[],tensors=[];const row={name:variant.name};report.variants.push(row);
  try{
   tell('Loading '+variant.name,report);mark=performance.now();session=await ort.InferenceSession.create(variant.fp16?fp16:variant.candidate?candidate:graph,{executionProviders:['webgpu'],graphOptimizationLevel:variant.level,externalData:[{path:'denoiser.onnx.data',data:weights}]});row.loadSeconds=(performance.now()-mark)/1000;
   const feeds={...base};if(variant.gpu){const device=ort.env.webgpu.device;for(const name of ['x','person','garment','person_pose','garment_pose']){const src=base[name].data,buf=device.createBuffer({size:Math.ceil(src.byteLength/16)*16,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST|GPUBufferUsage.COPY_SRC});device.queue.writeBuffer(buf,0,src.buffer,src.byteOffset,src.byteLength);buffers.push(buf);feeds[name]=ort.Tensor.fromGpuBuffer(buf,{dataType:'float16',dims:base[name].dims});tensors.push(feeds[name])}}
   row.runSeconds=[];for(let run=0;run<variant.runs;run++){tell('Running '+variant.name+' · '+(run+1)+' of '+variant.runs+' synthetic passes',report);mark=performance.now();const out=await session.run(feeds),actual=floats(out.velocity.data);row.runSeconds.push((performance.now()-mark)/1000);row.finite=actual.every(Number.isFinite);if(!row.finite)throw new Error('Non-finite numerical output.');if(!reference)reference=actual;else{let error=0,norm=0,max=0;for(let i=0;i<actual.length;i++){const delta=actual[i]-reference[i];error+=delta*delta;norm+=reference[i]*reference[i];max=Math.max(max,Math.abs(delta))}row.relativeRmsError=Math.sqrt(error/norm);row.maxAbsoluteError=max;if(row.relativeRmsError>.01)throw new Error('Optimisation changed numerical output beyond tolerance.')}Object.values(out).forEach(t=>t.dispose())}
  }catch(error){row.error=error.message}finally{tensors.forEach(t=>t.dispose());if(session)await session.release();buffers.forEach(b=>b.destroy())}
 }
 Object.values(base).forEach(t=>t.dispose());tell('Synthetic benchmark complete. Full-image quality and end-to-end timing are still separate checks.',report,true);
}catch(error){tell(error.message,report,true)}};
