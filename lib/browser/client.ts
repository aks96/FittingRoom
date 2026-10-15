/// <reference types="@webgpu/types" />
import {MODEL_CACHE,validateManifest,type BrowserState,type WorkerReply} from './contracts.ts';
import type {Garment,GarmentAnalysis,TryOnStatus} from '../services';
let state:BrowserState={stage:'idle',message:'Browser AI has not been enabled.',downloaded:0,total:0,analysisReady:false,generationReady:false,consent:false,cached:false};
let setupEpoch=0,setupRequest:AbortController|null=null;const ownedJobs=new Set<string>();
let worker:Worker|null=null,requestId=0;const listeners=new Set<()=>void>(),pending=new Map<number,{resolve:(value:unknown)=>void;reject:(error:Error)=>void}>();
export const getBrowserState=()=>state;
export function subscribeBrowser(listener:()=>void){listeners.add(listener);return()=>{listeners.delete(listener)}}
function update(value:Partial<BrowserState>){state={...state,...value};listeners.forEach(fn=>fn())}
export async function browserCompatibility(){if(!window.isSecureContext)throw new Error('Use HTTPS or localhost for browser AI.');if(!navigator.gpu)throw new Error('WebGPU is unavailable in this browser. Use a supported desktop browser; no model was downloaded.');if(!('Worker' in window)||!('OffscreenCanvas' in window)||!('caches' in window))throw new Error('This browser lacks the worker, canvas or model-cache features required.');const adapter=await navigator.gpu.requestAdapter();if(!adapter)throw new Error('No compatible browser GPU was found.');if(!adapter.features.has('shader-f16'))throw new Error('This experiment needs GPU float16 support. No model was downloaded.');return {maxBufferSize:adapter.limits.maxBufferSize}}
export async function startBrowserAI(consent:boolean){
 if(!consent)throw new Error('Consent is required before downloading models or processing selected images.');
 stopBrowserAI(false);const epoch=++setupEpoch;setupRequest=new AbortController();update({stage:'checking',message:'Checking browser and GPU compatibility',consent:true,downloaded:0,total:0,cached:false});
 try{await browserCompatibility();const r=await fetch('/api/browser-models/manifest.json',{cache:'no-store',signal:setupRequest.signal});if(!r.ok)throw new Error('The developer has not prepared browser models yet.');const manifest=validateManifest(await r.json());const total=manifest.models.reduce((n,m)=>n+m.bytes,0);update({total});const cache=await caches.open(MODEL_CACHE);let missing=0;for(const model of manifest.models){if(!await cache.match(location.origin+model.url+'?sha256='+model.sha256))missing+=model.bytes}const quota=await navigator.storage.estimate();if(quota.quota&&quota.quota-(quota.usage||0)<missing+256_000_000)throw new Error('Not enough browser storage for these models. Free space or clear cached models, then retry.');
 if(epoch!==setupEpoch||!state.consent)return;worker=new Worker(new URL('../../workers/browser-ai.worker.ts',import.meta.url),{type:'module'});
 worker.onmessage=(event:MessageEvent<WorkerReply>)=>{if(epoch!==setupEpoch)return;const m=event.data;if(m.type==='progress')update(m.state);else if(m.type==='result'){pending.get(m.id)?.resolve(m.value);pending.delete(m.id)}else if(m.id!==undefined){pending.get(m.id)?.reject(new Error(m.message));pending.delete(m.id)}else{update({stage:'failed',message:m.message,generationReady:false,analysisReady:false});worker?.terminate();worker=null}};
 worker.onerror=()=>{update({stage:'failed',message:'Browser AI stopped unexpectedly. Retry setup; your selected images remain in this tab.',generationReady:false,analysisReady:false});stopWorker()};worker.postMessage({type:'setup',manifest});
 }catch(e){if(epoch!==setupEpoch)return;update({stage:state.total?'failed':'unsupported',message:(e as Error).message,analysisReady:false,generationReady:false})}
}
function stopWorker(){worker?.terminate();worker=null;pending.forEach(p=>p.reject(new Error('Browser AI was stopped.')));pending.clear()}
export function stopBrowserAI(announce=true){setupEpoch++;setupRequest?.abort();setupRequest=null;stopWorker();update({stage:announce?'cancelled':'idle',message:announce?'Browser AI stopped. Downloaded models may remain cached.':'Browser AI has not been enabled.',analysisReady:false,generationReady:false,consent:false})}
export async function clearBrowserModels(){stopBrowserAI();await caches.delete(MODEL_CACHE);update({stage:'idle',message:'This app’s cached models were removed. Your selected photos remain in temporary tab memory.',cached:false,downloaded:0,total:0})}
function rpc<T>(type:string,value:unknown):Promise<T>{if(!worker||!state.consent||!state.analysisReady)throw new Error('Enable browser AI with consent before processing images.');const id=++requestId;return new Promise((resolve,reject)=>{pending.set(id,{resolve:value=>resolve(value as T),reject});worker!.postMessage({type,id,value})})}
export function browserAnalyze(image:string){return rpc<GarmentAnalysis>('analyze',{image})}
export async function browserGenerate(person:string,garment:Garment){if(!state.generationReady)throw new Error('Browser try-on is not ready. The generator must pass its local execution check first.');const job=await rpc<TryOnStatus>('generate',{person,garment});ownedJobs.add(job.id);return job}
export function browserJob(id:string){if(!worker&&ownedJobs.has(id))return Promise.resolve({id,stage:'cancelled'} as TryOnStatus);return rpc<TryOnStatus>('status',{id})}
export function browserCancel(id:string){if(!worker){ownedJobs.delete(id);return Promise.resolve()}return rpc<void>('cancel',{id}).then(()=>{ownedJobs.delete(id)})}

// Development reloads must not leave obsolete workers holding GPU memory.
if(typeof module!=='undefined'){const hot=(module as unknown as {hot?:{dispose:(fn:()=>void)=>void}}).hot;hot?.dispose(()=>stopBrowserAI(false))}
