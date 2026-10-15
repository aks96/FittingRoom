import {test} from 'node:test';import assert from 'node:assert/strict';
import {validateManifest,floatToHalf,halfToFloat,packFloat16,tensorFloat32,browserGarmentCategory} from '../lib/browser/contracts.ts';
import {startBrowserAI,getBrowserState} from '../lib/browser/client.ts';
const artifact=(name:string)=>({name,bytes:100,sha256:'a'.repeat(64),url:'/api/browser-models/'+name});
test('browser garment IDs match the native trained FASHN model, with zero reserved for unconditional',()=>{
 for(const category of ['Top','Shirt','T-shirt'] as const)assert.equal(browserGarmentCategory(category),1);
 assert.equal(browserGarmentCategory('Dress'),3);
 for(const category of ['Pants','Jeans','Shorts','Skirt'] as const)assert.equal(browserGarmentCategory(category),2);
 assert.equal(browserGarmentCategory('Jumpsuit'),3);
 assert.throws(()=>browserGarmentCategory('Bottoms' as 'Top'),/not supported/);
});
test('browser model manifests reject arbitrary URLs, paths, duplicates and unreasonable downloads',()=>{const valid={version:'v1',generationPrepared:false,models:[artifact('garment.onnx'),artifact('parser.onnx')]};assert.equal(validateManifest(valid).version,'v1');for(const change of [{...artifact('garment.onnx'),url:'https://evil.example/model'},{...artifact('garment.onnx'),name:'../private'},{...artifact('garment.onnx'),bytes:2_100_000_000},{...artifact('garment.onnx'),sha256:'invalid'},artifact('parser.onnx')])assert.throws(()=>validateManifest({...valid,models:[change,artifact('parser.onnx')]}))});
test('no browser downloads or image processing begin without consent',async()=>{await assert.rejects(startBrowserAI(false),/Consent is required/);assert.equal(getBrowserState().consent,false);assert.equal(getBrowserState().generationReady,false)});
test('half precision conversion preserves denoiser tensor ranges',()=>{for(const value of [-10,-1,-.5,0,.5,1,10])assert.equal(halfToFloat(floatToHalf(value)),value);assert.ok(Math.abs(halfToFloat(floatToHalf(.123))-.123)<.001);assert.equal(halfToFloat(floatToHalf(Infinity)),Infinity)});

test('runtime numeric float16 data and raw half bits are both decoded correctly',()=>{assert.deepEqual(Array.from(tensorFloat32(new Float32Array([.5,-1]))),[.5,-1]);assert.deepEqual(Array.from(tensorFloat32(Uint16Array.from([.5,-1],floatToHalf))),[.5,-1])});

test('half packing uses ties-to-even and preserves subnormals, signed zero and NaN',()=>{
 assert.equal(floatToHalf(1+2**-11),0x3c00);
 assert.equal(floatToHalf(1+3*2**-11),0x3c02);
 assert.equal(floatToHalf(2**-25),0);
 assert.equal(floatToHalf(3*2**-25),2);
 assert.equal(floatToHalf(-0),0x8000);
 assert.equal(floatToHalf(65520),0x7c00);
 assert.ok(Number.isNaN(halfToFloat(floatToHalf(NaN))));
 for(let bits=0;bits<65536;bits++){
  if((bits&0x7c00)===0x7c00&&(bits&1023))continue;
  assert.equal(floatToHalf(halfToFloat(bits)),bits);
 }
});
test('half packing reuses supplied buffers without changing static conditioning',()=>{
 const values=new Float32Array([.5,-1,.123]),target=new Uint16Array(3);
 assert.equal(packFloat16(values,target),target);
 const immutable=new Uint16Array(target);
 packFloat16(new Float32Array([0,1,2]),target);
 assert.deepEqual(Array.from(immutable),Array.from(packFloat16(values)));
 assert.throws(()=>packFloat16(values,new Uint16Array(2)),/length mismatch/);
});
