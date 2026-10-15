import {nativeCategory,type Category} from '../garment-catalog.ts';
export const MODEL_CACHE='yourfittingroom-models-v1';
export type ModelArtifact={name:string;bytes:number;sha256:string;url:string};
export type BrowserManifest={version:string;generationPrepared:boolean;models:ModelArtifact[]};
const allowed=new Set(['garment.onnx','parser.onnx','pose.onnx','denoiser.onnx','denoiser.onnx.data']);
// FASHN CATEGORY_TO_LABEL: 0 is unconditional, 1 tops, 2 bottoms, 3 one-pieces.
export function browserGarmentCategory(category:Category):number{
 const native=nativeCategory(category);
 return native==='tops'?1:native==='bottoms'?2:3;
}
export function validateManifest(value:unknown):BrowserManifest{
 const data=value as BrowserManifest;if(!data||typeof data.version!=='string'||!Array.isArray(data.models)||data.models.length<2||data.models.length>5)throw new Error('Invalid browser model manifest.');
 const seen=new Set();let total=0;
 for(const m of data.models){if(!allowed.has(m.name)||seen.has(m.name)||m.url!=='/api/browser-models/'+m.name||!Number.isSafeInteger(m.bytes)||m.bytes<=0||m.bytes>2_000_000_000||!/^[a-f0-9]{64}$/.test(m.sha256))throw new Error('Invalid browser model artifact.');seen.add(m.name);total+=m.bytes}
 if(total>3_500_000_000||!seen.has('garment.onnx')||!seen.has('parser.onnx'))throw new Error('Invalid browser model set.');
 return data;
}
export type BrowserState={stage:'idle'|'checking'|'downloading'|'verifying'|'loading'|'testing'|'ready'|'failed'|'unsupported'|'cancelled';message:string;downloaded:number;total:number;analysisReady:boolean;generationReady:boolean;consent:boolean;cached:boolean};
export type WorkerReply={type:'progress';state:Partial<BrowserState>}|{type:'result';id:number;value:unknown}|{type:'error';id?:number;message:string};
// Reuse views rather than allocating two typed arrays for every image scalar.
// IEEE 754 round-to-nearest, ties-to-even matches torch's float16 cast.
const floatScratch=new Float32Array(1),bitsScratch=new Uint32Array(floatScratch.buffer);
export function floatToHalf(value:number):number{
 floatScratch[0]=value;const u=bitsScratch[0],sign=(u>>>16)&0x8000,exponent=(u>>>23)&255,mantissa=u&0x7fffff;
 if(exponent===255)return sign|0x7c00|(mantissa?0x200:0);
 const e=exponent-127+15;if(e>=31)return sign|0x7c00;if(e< -10)return sign;
 const shift=e<=0?14-e:13,m=e<=0?mantissa|0x800000:mantissa;
 const base=m>>>shift,remainder=m&((1<<shift)-1),mid=1<<(shift-1);
 const rounded=base+(remainder>mid||(remainder===mid&&(base&1))?1:0);
 return sign|((e<=0?0:e<<10)+rounded);
}
export function packFloat16(values:Float32Array,target:Uint16Array=new Uint16Array(values.length)):Uint16Array{
 if(target.length!==values.length)throw new Error('Half tensor length mismatch.');
 for(let i=0;i<values.length;i++)target[i]=floatToHalf(values[i]);return target;
}
export function halfToFloat(h:number):number{const sign=(h&0x8000)?-1:1,e=(h>>>10)&31,m=h&1023;return e===0?sign*2**-14*(m/1024):e===31?(m?NaN:sign*Infinity):sign*2**(e-15)*(1+m/1024)}

export function tensorFloat32(data:Float32Array|Uint16Array):Float32Array{return data instanceof Uint16Array?Float32Array.from(data,halfToFloat):Float32Array.from(data)}
