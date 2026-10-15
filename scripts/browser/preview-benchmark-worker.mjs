import * as ort from '/ort.mjs';
ort.env.wasm.wasmPaths='/';ort.env.wasm.numThreads=1;ort.env.wasm.proxy=false;
const scratch=new Float32Array(1),bits=new Uint32Array(scratch.buffer);
function half(value){scratch[0]=value;const u=bits[0],sign=(u>>>16)&0x8000,exponent=(u>>>23)&255,mantissa=u&0x7fffff;if(exponent===255)return sign|0x7c00|(mantissa?0x200:0);const e=exponent-112;if(e>=31)return sign|0x7c00;if(e< -10)return sign;const shift=e<=0?14-e:13,m=e<=0?mantissa|0x800000:mantissa,base=m>>>shift,remainder=m&((1<<shift)-1),mid=1<<(shift-1),rounded=base+(remainder>mid||(remainder===mid&&(base&1))?1:0);return sign|((e<=0?0:e<<10)+rounded)}
function floats(data){if(!(data instanceof Uint16Array))return Float32Array.from(data);return Float32Array.from(data,h=>{const s=h&0x8000?-1:1,e=(h>>>10)&31,m=h&1023;return e===0?s*2**-14*m/1024:e===31?(m?NaN:s*Infinity):s*2**(e-15)*(1+m/1024)})}
const tell=(message,report,done=false,png)=>postMessage({message,report,done,png},png?[png]:[]);
onmessage=async()=>{let session;const feeds={};const start=performance.now(),report={kind:'browser model core only; native-preprocessed public sample photos',steps:20,resolution:[288,432]};try{
 tell('Reading local candidate and public sample fixture. No private photo is accessed.',report);
 const [graph,weights,payload,metadata]=await Promise.all(['/candidate.onnx','/weights.bin','/public-fixture.bin','/public-fixture.json'].map(async p=>{const r=await fetch(p);if(!r.ok)throw new Error('Local fixture unavailable.');return p.endsWith('json')?r.json():new Uint8Array(await r.arrayBuffer())}));
 report.candidateSha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',graph)),v=>v.toString(16).padStart(2,'0')).join('');report.localReadSeconds=(performance.now()-start)/1000;
 for(const entry of metadata.tensors){const value=new Uint16Array(payload.buffer.slice(entry.offset,entry.offset+entry.bytes));feeds[entry.name]=new ort.Tensor('float16',value,entry.dims)}
 feeds.t=new ort.Tensor('float16',new Uint16Array(1),[1]);feeds.category=new ort.Tensor('int64',new BigInt64Array([1n]),[1]);feeds.mask=new ort.Tensor('bool',new Uint8Array([1]),[1]);
 let mark=performance.now();tell('Loading browser candidate.',report);session=await ort.InferenceSession.create(graph,{executionProviders:['webgpu'],graphOptimizationLevel:'disabled',externalData:[{path:'denoiser.onnx.data',data:weights}]});report.modelLoadSeconds=(performance.now()-mark)/1000;
 let x=floats(feeds.x.data);const raw=feeds.x.data,time=feeds.t.data,xBits=new Uint16Array(raw.buffer,raw.byteOffset,raw.length),tBits=new Uint16Array(time.buffer,time.byteOffset,time.length),schedule=Array.from({length:21},(_,i)=>{const t=i/20;return t===0?0:Math.exp(-1.5)/(Math.exp(-1.5)+(1/t-1))});
 const sampleStart=performance.now();for(let step=0;step<20;step++){
  for(let i=0;i<x.length;i++)xBits[i]=half(x[i]);tBits[0]=half(schedule[step]);mark=performance.now();
  const run=async(condition)=>{feeds.mask.data[0]=condition?1:0;const out=await session.run(feeds);try{return floats(out.velocity.data)}finally{Object.values(out).forEach(t=>t.dispose())}};
  const conditional=await run(true),unconditional=step===19?conditional:await run(false),dt=schedule[step+1]-schedule[step];
  for(let i=0;i<x.length;i++)x[i]+=dt*(step===19?conditional[i]:unconditional[i]+1.5*(conditional[i]-unconditional[i]));if(!x.every(Number.isFinite))throw new Error('Invalid output; no preview substituted.');
  report.completedSteps=step+1;report.lastStepSeconds=(performance.now()-mark)/1000;report.generationSeconds=(performance.now()-sampleStart)/1000;tell(`${step+1} of 20 actual model steps completed`,report);
 }
 const canvas=new OffscreenCanvas(288,432),ctx=canvas.getContext('2d'),rgba=ctx.createImageData(288,432),n=288*432;for(let i=0;i<n;i++){for(let c=0;c<3;c++)rgba.data[i*4+c]=Math.round(Math.max(0,Math.min(255,(x[c*n+i]+1)*127.5)));rgba.data[i*4+3]=255}ctx.putImageData(rgba,0,0);const blob=await canvas.convertToBlob({type:'image/png'});report.totalSeconds=(performance.now()-start)/1000;report.finite=true;
 tell('Public sample browser preview complete. Inspect quality; this does not certify the full app journey.',report,true,await blob.arrayBuffer());
}catch(error){report.error=error.message;tell('Public sample test failed: '+error.message,report,true)}finally{Object.values(feeds).forEach(t=>t.dispose());if(session)await session.release()}};
