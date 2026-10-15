/// <reference lib="webworker" />
/// <reference types="@webgpu/types" />
import * as ort from 'onnxruntime-web/webgpu';
import {MODEL_CACHE,validateManifest,floatToHalf,packFloat16,tensorFloat32,browserGarmentCategory,type BrowserManifest,type ModelArtifact,type BrowserState} from '../lib/browser/contracts';
import type {Garment,GarmentAnalysis,TryOnStatus} from '../lib/services';
const scope=self as unknown as DedicatedWorkerGlobalScope;
ort.env.wasm.wasmPaths='/browser-runtime/';ort.env.wasm.numThreads=1;ort.env.wasm.proxy=false;
let clip:ort.InferenceSession,parser:ort.InferenceSession,pose:ort.InferenceSession,denoiser:ort.InferenceSession;
let prepared:BrowserManifest;
let downloaded=0,total=0,cached=true,processing=false;
const jobs=new Map<string,TryOnStatus>();
const startedAt=new Map<string,number>();
function progress(state:Partial<BrowserState>){scope.postMessage({type:'progress',state:{downloaded,total,cached,...state}})}
async function artifact(model:ModelArtifact){
 const cache=await caches.open(MODEL_CACHE),key=scope.location.origin+model.url+'?sha256='+model.sha256;let response=await cache.match(key),bytes:Uint8Array;
 if(response){progress({stage:'verifying',message:'Verifying cached '+model.name});bytes=new Uint8Array(await response.arrayBuffer())}
 else{cached=false;progress({stage:'downloading',message:'Downloading '+model.name});response=await fetch(model.url,{cache:'no-store'});if(!response.ok||!response.body)throw new Error('Model download unavailable: '+model.name);const reader=response.body.getReader(),chunks:Uint8Array[]=[];let size=0;
 while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>model.bytes){await reader.cancel();throw new Error('Model download size mismatch.')}chunks.push(value);downloaded+=value.length;progress({stage:'downloading',message:'Downloading '+model.name})}
 bytes=new Uint8Array(size);let offset=0;for(const part of chunks){bytes.set(part,offset);offset+=part.length}}
 if(bytes.byteLength!==model.bytes)throw new Error('Model download was incomplete. Retry setup.');progress({stage:'verifying',message:'Checking '+model.name+' integrity'});
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes.buffer as ArrayBuffer)),b=>b.toString(16).padStart(2,'0')).join('');if(hash!==model.sha256){await cache.delete(key);throw new Error('Model integrity check failed. Retry the download.')}
 if(!cached||!await cache.match(key)){try{await cache.put(key,new Response(bytes as Uint8Array<ArrayBuffer>))}catch{throw new Error('Browser could not cache the model. Check available storage and retry.')}}
 return bytes;
}
async function session(model:ModelArtifact,external?:ModelArtifact){let data:Uint8Array|undefined;if(external)data=await artifact(external);const graph=await artifact(model);progress({stage:'loading',message:'Loading '+model.name+' on the browser GPU'});return ort.InferenceSession.create(graph,{executionProviders:['webgpu'],graphOptimizationLevel:'disabled',freeDimensionOverrides:{batch:1},...(external?{externalData:[{path:external.name,data:data!}]}:{})})}
function zeros(size:number,half=false){return half?new Uint16Array(size):new Float32Array(size)}
function denoiseFeeds(person:Float32Array,garment:Float32Array,pp:Float32Array,gp:Float32Array,x:Float32Array,t:number,category:number,condition=true){const half=(v:Float32Array)=>new ort.Tensor('float16',packFloat16(v),[1,v.length===432*288?1:3,432,288]);return {x:half(x),t:new ort.Tensor('float16',new Uint16Array([floatToHalf(t)]),[1]),person:half(person),garment:half(garment),person_pose:half(pp),garment_pose:half(gp),category:new ort.Tensor('int64',BigInt64Array.from([BigInt(category)]),[1]),mask:new ort.Tensor('bool',new Uint8Array([condition?1:0]),[1])}}
async function setup(manifest:BrowserManifest){const m=validateManifest(manifest);prepared=m;total=m.models.reduce((n,x)=>n+x.bytes,0);const get=(name:string)=>{const found=m.models.find(x=>x.name===name);if(!found)throw new Error('Missing browser model: '+name);return found};
 clip=await session(get('garment.onnx'));parser=await session(get('parser.onnx'));progress({stage:'testing',message:'Running real clothing-analysis model checks in the browser'});
 const input=new ort.Tensor('float32',new Float32Array(3*224*224),[1,3,224,224]);const result=await clip.run({pixels:input});if(result.logits.data.length!==12)throw new Error('Browser classification check failed.');input.dispose();Object.values(result).forEach(t=>t.dispose());
 const image=new ort.Tensor('float32',new Float32Array(3*576*384),[1,3,576,384]);const masks=await parser.run({pixels:image});if(masks.mask.data.length!==144*96)throw new Error('Browser segmentation check failed.');image.dispose();Object.values(masks).forEach(t=>t.dispose());
 if(m.generationPrepared){await clip.release();await parser.release();clip=parser=undefined as unknown as ort.InferenceSession;pose=await session(get('pose.onnx'));const poseInput=new ort.Tensor('float32',new Float32Array(3*384*288),[1,3,384,288]);const poseOutput=await pose.run({input:poseInput});poseInput.dispose();Object.values(poseOutput).forEach(t=>t.dispose());await pose.release();pose=undefined as unknown as ort.InferenceSession;denoiser=await session(get('denoiser.onnx'),get('denoiser.onnx.data'));progress({stage:'testing',message:'Testing the experimental try-on generator on this GPU'});const p=new Float32Array(3*432*288),s=new Float32Array(432*288);const feeds=denoiseFeeds(p,p,s,s,p,0,0);const out=await denoiser.run(feeds);if(out.velocity.data.length!==p.length)throw new Error('Browser generator check failed.');Object.values(feeds).forEach(t=>t.dispose());Object.values(out).forEach(t=>t.dispose());await denoiser.release();denoiser=undefined as unknown as ort.InferenceSession;progress({stage:'ready',message:'Browser execution checks passed · preview quality is not validated',generationReady:true,analysisReady:true})}
 else progress({stage:'ready',message:'Browser clothing analysis ready. Browser try-on models are not prepared yet.',generationReady:false,analysisReady:true});
}
async function bitmap(src:string){if(!/^data:image\/(png|jpeg|webp);base64,/.test(src)||src.length>18_000_000)throw new Error('Select a supported local image under 12 MB.');const value=await createImageBitmap(await (await fetch(src)).blob());if(value.width*value.height>24_000_000){value.close();throw new Error('Image exceeds 24 megapixels.')}return value}
function canvasOf(image:ImageBitmap,w:number,h:number,crop=false,pad=false){const c=new OffscreenCanvas(w,h),ctx=c.getContext('2d')!;ctx.fillStyle='black';ctx.fillRect(0,0,w,h);if(crop){const s=Math.min(image.width,image.height);ctx.drawImage(image,(image.width-s)/2,(image.height-s)/2,s,s,0,0,w,h)}else if(pad){const f=Math.min(w/image.width,h/image.height),rw=Math.round(image.width*f),rh=Math.round(image.height*f);ctx.drawImage(image,(w-rw)/2,(h-rh)/2,rw,rh)}else ctx.drawImage(image,0,0,w,h);return c}
function pixels(c:OffscreenCanvas,mean:number[],std:number[]){const rgba=c.getContext('2d')!.getImageData(0,0,c.width,c.height).data,n=c.width*c.height,out=new Float32Array(n*3);for(let i=0;i<n;i++)for(let j=0;j<3;j++)out[j*n+i]=(rgba[i*4+j]/255-mean[j])/std[j];return out}
async function segment(image:ImageBitmap){const c=canvasOf(image,384,576),input=new ort.Tensor('float32',pixels(c,[.485,.456,.406],[.229,.224,.225]),[1,3,576,384]);const result=await parser.run({pixels:input}),mask=new Int32Array(result.mask.data as Int32Array);input.dispose();Object.values(result).forEach(t=>t.dispose());return {c,mask}}
function suggestion(logits:ArrayLike<number>,start:number,length:number){const values=Array.from({length},(_,i)=>Number(logits[start+i])),max=Math.max(...values),exps=values.map(v=>Math.exp(v-max)),sum=exps.reduce((a,b)=>a+b,0),order=exps.map((v,i)=>({i,v:v/sum})).sort((a,b)=>b.v-a.v);return {index:order[0].i,uncertain:order[0].v-order[1].v<.2}}
function colour(rgb:number[]){const [r,g,b]=rgb,max=Math.max(...rgb),min=Math.min(...rgb);if(max<50)return 'Black';if(max-min<25)return max>220?'White':'Grey';if(r>g*1.2&&r>b*1.2)return max<145?'Maroon':'Red';if(g>r&&g>b)return 'Green';if(b>r&&b>g)return max<130?'Navy':'Blue';if(r>g&&b>g)return 'Purple';return max>180?'Beige':'Brown'}
async function ensureAnalysis(){if(!clip)clip=await session(prepared.models.find(m=>m.name==='garment.onnx')!);if(!parser)parser=await session(prepared.models.find(m=>m.name==='parser.onnx')!)}
async function analyze(src:string):Promise<GarmentAnalysis>{await ensureAnalysis();const image=await bitmap(src);try{const c=canvasOf(image,224,224,true),input=new ort.Tensor('float32',pixels(c,[.48145466,.4578275,.40821073],[.26862954,.26130258,.27577711]),[1,3,224,224]);const out=await clip.run({pixels:input}),values=out.logits.data as Float32Array,cat=suggestion(values,0,4),pattern=suggestion(values,4,5),sleeves=suggestion(values,9,3),seg=await segment(image);input.dispose();Object.values(out).forEach(t=>t.dispose());const rgba=seg.c.getContext('2d')!.getImageData(0,0,384,576).data;const groups=new Map<number,{sum:number[];n:number}>();let body=0,garment=0;for(let y=0;y<144;y++)for(let x=0;x<96;x++){const label=seg.mask[y*96+x];if([1,2,12,13,14].includes(label))body++;if(label!==(cat.index===3?4:3))continue;garment++;const pos=((y*4+2)*384+x*4+2)*4,r=rgba[pos],g=rgba[pos+1],b=rgba[pos+2],key=(r>>5)*64+(g>>5)*8+(b>>5),group=groups.get(key)||{sum:[0,0,0],n:0};group.n++;group.sum[0]+=r;group.sum[1]+=g;group.sum[2]+=b;groups.set(key,group)}const best=[...groups.values()].sort((a,b)=>b.n-a.n)[0],rgb=best?best.sum.map(v=>Math.round(v/best.n)):[136,136,136];return {category:(['T-shirt','Shirt','Top','Dress'] as const)[cat.index],colour:best?colour(rgb):'Uncertain',swatch:'#'+rgb.map(v=>v.toString(16).padStart(2,'0')).join(''),photoType:body/seg.mask.length>.035?'model':'flat-lay',pattern:pattern.uncertain?'Uncertain':['Solid','Floral','Striped','Checked','Graphic'][pattern.index],sleeves:sleeves.uncertain?'Uncertain':['Sleeveless','Short sleeves','Long sleeves'][sleeves.index],categoryReview:cat.uncertain,colourReview:garment/seg.mask.length<.01,size:'Not determined from the image',fit:'Needs garment dimensions and body measurements',method:'Browser CLIP + FASHN segmentation · WebGPU'}}finally{image.close();progress({stage:'ready',message:'Clothing image analysed entirely in this browser.'})}}
async function poseTensor(image:ImageBitmap,flat=false){const w=288,h=432;if(flat)return new Float32Array(w*h).fill(-1);const c=new OffscreenCanvas(288,384),ctx=c.getContext('2d')!;ctx.fillStyle='black';ctx.fillRect(0,0,288,384);let scaleW=image.width*1.25,scaleH=image.height*1.25;if(scaleW/scaleH>288/384)scaleH=scaleW*384/288;else scaleW=scaleH*288/384;const factor=288/scaleW;ctx.drawImage(image,(288-image.width*factor)/2,(384-image.height*factor)/2,image.width*factor,image.height*factor);const rgba=ctx.getImageData(0,0,288,384).data,n=288*384,data=new Float32Array(n*3),mean=[123.675,116.28,103.53],std=[58.395,57.12,57.375];for(let i=0;i<n;i++)for(let j=0;j<3;j++)data[j*n+i]=(rgba[i*4+2-j]-mean[j])/std[j];const tensor=new ort.Tensor('float32',data,[1,3,384,288]),out=await pose.run({input:tensor}),xs=out.simcc_x.data as Float32Array,ys=out.simcc_y.data as Float32Array,nx=out.simcc_x.dims[2],ny=out.simcc_y.dims[2];const points:Array<{x:number;y:number;s:number}>=[];for(let i=0;i<133;i++){let bx=0,by=0;for(let j=1;j<nx;j++)if(xs[i*nx+j]>xs[i*nx+bx])bx=j;for(let j=1;j<ny;j++)if(ys[i*ny+j]>ys[i*ny+by])by=j;points.push({x:(bx/2/288*scaleW+image.width/2-scaleW/2)/image.width,y:(by/2/384*scaleH+image.height/2-scaleH/2)/image.height,s:Math.min(xs[i*nx+bx],ys[i*ny+by])})}tensor.dispose();Object.values(out).forEach(t=>t.dispose());
 const neck={x:(points[5].x+points[6].x)/2,y:(points[5].y+points[6].y)/2,s:points[5].s>.3&&points[6].s>.3?1:0};
 points.splice(17,0,neck);
 const old=points.slice(),mmp=[17,6,8,10,7,9,12,14,16,13,15,2,1,4,3],open=[1,2,3,4,6,7,8,9,10,12,13,14,15,16,17];
 open.forEach((v,i)=>{points[v]=old[mmp[i]]});
 // Draw at the source resolution, then nearest-neighbour resize/pad, as in
 // FASHN's draw_pose + ResizePad. Do not invent different joint intensities.
 const drawing=new OffscreenCanvas(image.width,image.height),dc=drawing.getContext('2d')!;
 dc.fillStyle='black';dc.fillRect(0,0,drawing.width,drawing.height);
 const xy=(i:number)=>({x:Math.floor(points[i].x*image.width),y:Math.floor(points[i].y*image.height)});
 const visible=(i:number)=>points[i].s>.3;
 const limbs=[[1,2],[1,5],[2,3],[3,4],[5,6],[6,7],[1,8],[8,9],[9,10],[1,11],[11,12],[12,13],[1,0],[0,14],[14,16],[0,15],[15,17]];
 const shade=(v:number)=>`rgb(${v},${v},${v})`;
 dc.globalCompositeOperation='lighten';
 limbs.forEach(([a,b],i)=>{
  if(!visible(a)||!visible(b))return;const p=xy(a),q=xy(b),dx=p.x-q.x,dy=p.y-q.y;
  dc.fillStyle=shade(Math.floor(Math.floor(20+i*220/17)*.6));dc.beginPath();
  dc.ellipse(Math.floor((p.x+q.x)/2),Math.floor((p.y+q.y)/2),Math.floor(Math.hypot(dx,dy)/2),4,Math.trunc(Math.atan2(dy,dx)*180/Math.PI)*Math.PI/180,0,Math.PI*2);dc.fill();
 });
 dc.globalCompositeOperation='source-over';
 const dot=(i:number,radius:number,grey:number)=>{if(!visible(i))return;const p=xy(i);if(i>=18&&(p.x<=.01||p.y<=.01))return;dc.fillStyle=shade(grey);dc.beginPath();dc.arc(p.x,p.y,radius,0,Math.PI*2);dc.fill()};
 for(let i=0;i<18;i++){const limb=limbs.findIndex(pair=>pair.includes(i));if(limb>=0)dot(i,4,Math.min(255,Math.floor(Math.floor(20+limb*220/17)*1.3)))}
 const edges=[[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[0,9],[9,10],[10,11],[11,12],[0,13],[13,14],[14,15],[15,16],[0,17],[17,18],[18,19],[19,20]];
 for(const start of [92,113]){
  edges.forEach(([a,b],i)=>{a+=start;b+=start;if(!visible(a)||!visible(b))return;const p=xy(a),q=xy(b);if(Math.min(p.x,p.y,q.x,q.y)<=.01)return;dc.strokeStyle=shade(Math.floor(160+i*60/19));dc.lineWidth=2;dc.beginPath();dc.moveTo(p.x,p.y);dc.lineTo(q.x,q.y);dc.stroke()});
  for(let i=start;i<start+21;i++)dot(i,4,240);
 }
 for(let i=24;i<92;i++)dot(i,3,200);
 const padded=new OffscreenCanvas(w,h),output=padded.getContext('2d')!,f=Math.min(w/image.width,h/image.height),rw=Math.round(image.width*f),rh=Math.round(image.height*f);
 output.fillStyle='black';output.fillRect(0,0,w,h);output.imageSmoothingEnabled=false;
 output.drawImage(drawing,Math.floor((w-rw)/2),Math.floor((h-rh)/2),rw,rh);
 const drawn=output.getImageData(0,0,w,h).data,result=new Float32Array(w*h);
 for(let i=0;i<result.length;i++)result[i]=drawn[i*4]/127.5-1;return result;
}

function gaussian(n:number){let seed=42;const random=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return ((seed>>>0)+1)/4294967297};const data=new Float32Array(n);for(let i=0;i<n;i+=2){const r=Math.sqrt(-2*Math.log(random())),angle=2*Math.PI*random();data[i]=r*Math.cos(angle);if(i+1<n)data[i+1]=r*Math.sin(angle)}return data}
async function generate(id:string,src:string,garment:Garment){const job=jobs.get(id)!;let person:ImageBitmap|undefined,cloth:ImageBitmap|undefined;try{
 processing=true;job.stage='aligning-images';await ensureAnalysis();person=await bitmap(src);cloth=await bitmap(garment.image!);const personMask=await segment(person);const faces=Array.from(personMask.mask).filter(x=>x===1).length;if(faces/personMask.mask.length<.001)throw new Error('A clear person could not be detected. Choose a front-facing photo with your face and torso visible.');const clothMask=await segment(cloth);const pc=canvasOf(person,288,432,false,true),gc=canvasOf(cloth,288,432,false,true);
 if(garment.photoType!=='flat-lay'){const ctx=gc.getContext('2d')!,data=ctx.getImageData(0,0,288,432),factor=Math.min(288/cloth.width,432/cloth.height),rw=Math.round(cloth.width*factor),rh=Math.round(cloth.height*factor),ox=Math.floor((288-rw)/2),oy=Math.floor((432-rh)/2),labels=garment.category==='Dress'?[3,4,10,5,6,7]:[3,4,10];for(let y=0;y<432;y++)for(let x=0;x<288;x++){if(x<ox||y<oy||x>=ox+rw||y>=oy+rh)continue;const label=clothMask.mask[Math.min(143,Math.floor((y-oy)/rh*144))*96+Math.min(95,Math.floor((x-ox)/rw*96))];if(!labels.includes(label)){const i=(y*288+x)*4;data.data[i]=data.data[i+1]=data.data[i+2]=127}}ctx.putImageData(data,0,0)}
 await clip.release();clip=undefined as unknown as ort.InferenceSession;pose=await session(prepared.models.find(m=>m.name==='pose.onnx')!);const pp=await poseTensor(person),gp=await poseTensor(cloth,garment.photoType==='flat-lay'),p=pixels(pc,[.5,.5,.5],[.5,.5,.5]),g=pixels(gc,[.5,.5,.5],[.5,.5,.5]);await parser.release();parser=undefined as unknown as ort.InferenceSession;await pose.release();pose=undefined as unknown as ort.InferenceSession;job.stage='loading-model';denoiser=await session(prepared.models.find(m=>m.name==='denoiser.onnx')!,prepared.models.find(m=>m.name==='denoiser.onnx.data')!);let x=gaussian(p.length);job.stage='generating';job.completedSteps=0;job.totalSteps=20;const steps=20,schedule=Array.from({length:steps+1},(_,i)=>{const t=i/steps;return t===0?0:Math.exp(-1.5)/(Math.exp(-1.5)+(1/t-1))});
 // Static conditioning is packed once per job. Both CFG calls share the
 // same noise/time tensors; only mask changes between them.
 const feeds=denoiseFeeds(p,g,pp,gp,x,0,browserGarmentCategory(garment.category));
 // ORT exposes numeric Float16Array on newer browsers. Keep raw bit views
 // for in-place packing; writing half bit integers into Float16Array corrupts data.
 const xStorage=feeds.x.data as Uint16Array,timeStorage=feeds.t.data as Uint16Array;
 const xBits=new Uint16Array(xStorage.buffer,xStorage.byteOffset,xStorage.length),timeBits=new Uint16Array(timeStorage.buffer,timeStorage.byteOffset,timeStorage.length);
 try{
  for(let step=0;step<steps;step++){
   if((job as TryOnStatus).stage==='cancelled')return;
   const stepStart=performance.now();
   packFloat16(x,xBits);timeBits[0]=floatToHalf(schedule[step]);
   const run=async(condition:boolean)=>{
    (feeds.mask.data as Uint8Array)[0]=condition?1:0;
    const output=await denoiser.run(feeds);
    try{const result=tensorFloat32(output.velocity.data as Uint16Array|Float32Array);if(!result.every(Number.isFinite))throw new Error('Browser model produced invalid pixels. This preview cannot be used.');return result}
    finally{Object.values(output).forEach(t=>t.dispose())}
   };
   const conditional=await run(true),unconditional=step===steps-1?conditional:await run(false),dt=schedule[step+1]-schedule[step];
   for(let i=0;i<x.length;i++)x[i]+=dt*(step===steps-1?conditional[i]:unconditional[i]+1.5*(conditional[i]-unconditional[i]));
   job.completedSteps=step+1;job.lastStepMs=performance.now()-stepStart;job.elapsedMs=performance.now()-startedAt.get(id)!;
   await new Promise(resolve=>setTimeout(resolve,0));
  }
 }finally{Object.values(feeds).forEach(t=>t.dispose())}

 if((job as TryOnStatus).stage==='cancelled')return;const output=new OffscreenCanvas(288,432),ctx=output.getContext('2d')!,rgba=ctx.createImageData(288,432),n=288*432;for(let i=0;i<n;i++){for(let j=0;j<3;j++)rgba.data[i*4+j]=Math.round(Math.max(0,Math.min(255,(x[j*n+i]+1)*127.5)));rgba.data[i*4+3]=255}ctx.putImageData(rgba,0,0);const factor=Math.min(288/person.width,432/person.height),rw=Math.round(person.width*factor),rh=Math.round(person.height*factor),cropped=new OffscreenCanvas(rw,rh);cropped.getContext('2d')!.drawImage(output,Math.floor((288-rw)/2),Math.floor((432-rh)/2),rw,rh,0,0,rw,rh);const blob=await cropped.convertToBlob({type:'image/png'}),bytes=new Uint8Array(await blob.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));job.image='data:image/png;base64,'+btoa(binary);job.stage='complete';job.elapsedMs=performance.now()-startedAt.get(id)!;
 }catch(error){job.stage='failed';job.error=error instanceof Error?error.message:'Browser generation failed. No sample was substituted.'}finally{person?.close();cloth?.close();processing=false;if(denoiser){await denoiser.release();denoiser=undefined as unknown as ort.InferenceSession}progress({stage:'ready',message:'Browser GPU processing finished.'});if(job.stage==='cancelled')jobs.delete(id);setTimeout(()=>{jobs.delete(id);startedAt.delete(id)},30*60*1000)}}
scope.onmessage=async(event:MessageEvent)=>{const {type,id,value,manifest}=event.data;try{
 if(type==='setup'){await setup(manifest);return}
 if(type==='analyze'){if(processing)throw new Error('Browser GPU is busy generating a preview.');processing=true;try{scope.postMessage({type:'result',id,value:await analyze(value.image)})}finally{processing=false}return}
 if(type==='generate'){if(processing)throw new Error('A browser preview is already running.');if(!prepared?.generationPrepared)throw new Error('Browser generation is not available.');if(!['Top','Shirt','T-shirt','Dress'].includes(value.garment.category))throw new Error('This category needs the native companion; the experimental browser model has not been validated for it.');const jobId=crypto.randomUUID().replaceAll('-',''),job:TryOnStatus={id:jobId,stage:'queued',engine:'browser',resolution:[432,288]};jobs.set(jobId,job);startedAt.set(jobId,performance.now());scope.postMessage({type:'result',id,value:job});void generate(jobId,value.person,value.garment);return}
 if(type==='status'){const job=jobs.get(value.id);if(!job)throw new Error('Browser job expired or was deleted.');if(!['complete','failed','cancelled'].includes(job.stage))job.elapsedMs=performance.now()-startedAt.get(value.id)!;scope.postMessage({type:'result',id,value:job});return}
 if(type==='cancel'){const job=jobs.get(value.id);if(job){job.stage='cancelled';job.image=undefined;if(!processing)jobs.delete(value.id)}scope.postMessage({type:'result',id,value:null});return}
 }catch(error){scope.postMessage({type:'error',id,message:error instanceof Error?error.message:'Browser inference failed.'})}};
