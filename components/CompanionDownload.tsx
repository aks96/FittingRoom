'use client';
import {useEffect,useState} from 'react';
import {ArrowUpRight,Check,Download,FileArchive,Folder,Monitor,ShieldCheck} from 'lucide-react';
import {Button} from './ui';
import {companionDownloads,detectCompanionPlatform,downloadBuild,downloadHref,downloadSize,type CompanionPlatform} from '@/lib/companion-downloads';

export default function CompanionDownload(){
 const [platform,setPlatform]=useState<CompanionPlatform>('mac');
 const [requested,setRequested]=useState<CompanionPlatform|null>(null);
 useEffect(()=>setPlatform(detectCompanionPlatform(navigator.userAgent)),[]);
 const item=companionDownloads[platform];
 return <section id="download-companion" className="download-section" aria-labelledby="download-heading">
  <div className="download-section-heading"><div><p className="eyebrow">A LITTLE SETUP. YOUR OWN FITTING ROOM.</p><h2 id="download-heading">Make room for your next look.</h2></div><span className="sample-chip">{downloadBuild}</span></div>
  <p className="download-intro">Start here: choose your computer, download the companion and follow the steps on this page. Keep this guide open while you set up. Your local fitting room opens in a new tab on this computer.</p>
  <div className="download-grid">
   <div className="download-picker">
    <div className="download-platforms" role="group" aria-label="Choose download platform">
     <Button aria-pressed={platform==='mac'} onClick={()=>setPlatform('mac')}>macOS</Button>
     <Button aria-pressed={platform==='windows'} onClick={()=>setPlatform('windows')}>Windows</Button>
    </div>
    <div className="download-device"><Monitor size={28}/><div><h3>{platform==='mac'?'For your Mac':'For your Windows PC'}</h3><p className="small muted">{platform==='mac'?'Apple silicon · 16 GB+ RAM recommended':'Recent Windows x64 · 16 GB+ RAM target'}</p></div></div>
    <p className="download-support small">{platform==='mac'?'Local try-on tested on M5 with 16 GB RAM. M3 and other Macs still need validation.':'Experimental Windows worker included. NVIDIA, AMD, Intel and CPU profiles need real Windows testing; a recent laptop alone does not establish compatibility.'}</p>
    <a className="btn primary download-primary" href={downloadHref(platform)} download={item.filename} onClick={()=>setRequested(platform)} aria-describedby="download-format download-limits"><Download size={18}/>Download {platform==='mac'?'Mac companion':'Windows experimental companion'}</a>
    <p id="download-format" className="small download-file"><FileArchive size={15}/>{item.format} archive · {downloadSize(item.bytes)}<br/><span>{item.filename}</span></p>
    <div id="download-limits" className="download-build-note"><strong>What this build provides</strong><p className="small">{platform==='mac'?'A development source archive with double-click launchers. Python 3.12 is required; this is not a signed Mac installer.':'An unsigned development ZIP with source, .cmd launchers, an opt-in worker and the local interface. Requires 64-bit Python 3.12. This is an internal test candidate, not a validated Windows release or an .exe installer.'}</p></div>
    {platform==='windows'&&<details className="download-integrity"><summary>Windows hardware & testing limits</summary><p className="small">NVIDIA CUDA and explicit CPU profiles target Windows 10 version 2004+ or Windows 11 x64. AMD ROCm and Intel XPU need Windows 11 with supported GPUs and matching vendor drivers. Intel/AMD processor names do not identify the graphics hardware. Windows ARM and 32-bit systems are unsupported.</p><p className="small">CPU testing can be impractically slow. GPU, isolation or numerical checks that fail stop processing; no unrestricted, automatic CPU or cloud fallback is used. AMD setup can download substantially more data and has a documented development dependency exception. Review WINDOWS_TESTING.md in the ZIP before setup.</p></details>}
    <details className="download-integrity"><summary>File contents & verification</summary><p className="small">{item.fileCount} files · application code, local interface and setup instructions. Python, AI model weights, accounts and personal photos are not included.</p><p className="small">SHA-256 checksum</p><code>{item.sha256}</code><p className="small muted">This identifies the current archive. It does not certify safety or replace publisher signing.</p></details>
   </div>
   <div className="download-next" aria-labelledby="download-next-heading">
    <h3 id="download-next-heading">Your first visit, step by step</h3>
    <div className="download-folder"><Folder size={20}/><strong>{item.folder}</strong><div><FileArchive size={15}/><span>{item.setup}</span></div>{platform==='windows'&&<div><ShieldCheck size={15}/><span>{companionDownloads.windows.test}</span></div>}<div><Monitor size={15}/><span>{item.start}</span></div><div><ShieldCheck size={15}/><span>Local fitting-room interface & setup guide</span></div></div>
    <ol className="download-steps">
     <li><span>01</span><div><strong>{platform==='mac'?'Extract the archive':'Right-click the ZIP → Extract All'}</strong><p>Keep the complete companion folder together.</p></div></li>
     <li><span>02</span><div><strong>Set up once</strong><p>{platform==='mac'?<>Install Python 3.12 if needed, then open <b>{item.setup}</b>. Setup downloads several GB of dependencies and models.</>:<>Install 64-bit Python 3.12 per-user from python.org with its Python launcher, then open <b>{item.setup}</b>. Review the detected adapters and choose NVIDIA CUDA, AMD ROCm, Intel XPU or explicit slow CPU testing. Keep the window open during the several-GB setup.</>}</p></div></li>
     {platform==='windows'&&<li><span>03</span><div><strong>Run the Windows checks first</strong><p>With the companion stopped, open <b>{companionDownloads.windows.test}</b>. Review <b>.runtime/windows-validation/report.json</b>. If any check fails, stop and keep the error. Passing checks do not establish full-model image quality or speed. Begin with the bundled public test photos, not a personal photo.</p></div></li>}
     <li><span>{platform==='mac'?'03':'04'}</span><div><strong>Start the companion</strong><p>Open <b>{item.start}</b> from the extracted folder and keep its window running. {platform==='windows'&&'Explicitly choose experimental testing only after the checks pass. '}Wait for the local fitting room to be ready.</p></div></li>
     <li><span>{platform==='mac'?'04':'05'}</span><div><strong>Open your fitting room and pair</strong><p>Use the button below. Copy the private pairing code from the companion window into the local fitting room. Read the selected-image processing consent and pair only if you agree. Keep the code private; do not enter it on this website.</p></div></li>
     <li><span>{platform==='mac'?'05':'06'}</span><div><strong>Choose your photos and try a look</strong><p>{platform==='windows'?'For the first test, use model.webp and garment.webp in .runtime/fashn-src/examples/data, downloaded by setup. After validating the trial, choose your own photos locally. ':'Upload your clothing image and a clear photo of yourself in the local fitting room. '}Review the garment details and photo, then generate an AI style preview. Compare and save looks there; download any you want to keep before refreshing.</p></div></li>
    </ol>
    <a className="btn primary download-primary" href="http://127.0.0.1:8765" target="_blank" rel="noopener noreferrer">Open your local fitting room <ArrowUpRight size={16}/><span className="sr-only"> (new tab)</span></a>
    {requested===platform&&<p className="download-requested" role="status" aria-live="polite"><Check size={17}/><span>Download requested. Check your browser’s downloads for <b>{item.filename}</b>. Extract it before opening any launcher.</span></p>}
   </div>
  </div>
  <div className="download-return-guide">
   <section aria-labelledby="download-return-heading"><p className="eyebrow">WHEN YOU COME BACK</p><h3 id="download-return-heading">No need to download again.</h3><p>Open <b>{item.start}</b> from the folder you kept, then use <b>Open your local fitting room</b> on this page. Pair with the current code and consent for the new session. Setup and model downloads are only needed again if files were removed or an update requires them. {platform==='windows'&&'Windows remains an experimental opt-in; rerun Test Windows.cmd after changing the backend, runtime or driver.'}</p><p className="small muted">Refreshing the local fitting room ends the temporary photo session. It does not remove the downloaded models. To stop processing, cancel the job or disconnect, then stop the companion with Ctrl+C in its command window.</p></section>
   <section aria-labelledby="download-help-heading"><h3 id="download-help-heading">Need help opening it?</h3><details><summary>The fitting room does not open</summary><p>Check that first-time setup completed and <b>{item.start}</b> is still running on this same computer. If its window shows an error, keep the message for troubleshooting. This website cannot start the companion for you. {platform==='windows'&&'If Test Windows.cmd fails, do not force generation or bypass protection; review WINDOWS_TESTING.md in the ZIP.'}</p></details><details><summary>My computer blocks a launcher</summary><p>Stop and read the warning. These development archives are not signed installers. Do not disable your computer’s security protections or run a file you cannot verify. Signed Mac and Windows installers are still required for a public release.</p></details><p className="small muted">Downloading a file does not install it. This guide does not access your files, approve system prompts or start processing.</p></section>
  </div>
 </section>
}
