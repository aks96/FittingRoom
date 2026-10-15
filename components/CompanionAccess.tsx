'use client';
import {useCallback,useEffect,useId,useState} from 'react';
import {Download,CheckCircle2,Monitor} from 'lucide-react';
import {Button} from './ui';
import {pairEngine,engineHealth,isPaired,hasEngineSession,signIn,disconnectEngine,consentWithdrawnEvent} from '@/lib/engine';
import {selectProcessingMode} from '@/lib/processing-mode';
import type {LocalHealth} from '@/lib/services';

export default function CompanionAccess({onHealth}:{onHealth:(health:LocalHealth|null)=>void}){
 const id=useId();const bundled=process.env.NEXT_PUBLIC_BUNDLED_WORKSPACE==='1';
 const [code,setCode]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 const [connected,setConnected]=useState(false),[consent,setConsent]=useState(false),[hydrated,setHydrated]=useState(false);
 const [available,setAvailable]=useState(false),[hosted,setHosted]=useState(false),[account,setAccount]=useState(false);
 const [platform,setPlatform]=useState<'mac'|'windows'>('mac');
 const [engineProblem,setEngineProblem]=useState('');
 const setupLauncher=platform==='mac'?'Set up.command':'Set up.cmd';
 const startLauncher=platform==='mac'?'Start AI.command':'Start AI.cmd';
 const check=useCallback(async()=>{
  try{const h=await engineHealth();onHealth(h);setEngineProblem(h.error||'');setAvailable(true);setConnected(h.ready);return h.ready}
  catch{onHealth(null);setAvailable(false);setConnected(false);return false}
 },[onHealth]);
 useEffect(()=>{
  setHydrated(true);setConsent(isPaired());selectProcessingMode('companion');void check();
  if(navigator.userAgent.includes('Windows'))setPlatform('windows');
  const local=['localhost','127.0.0.1'].includes(location.hostname);setHosted(!local);
  const refresh=()=>{void check();if(!local)fetch('/api/auth/session',{cache:'no-store'}).then(r=>r.json()).then(d=>setAccount(d.authenticated===true)).catch(()=>{})};
  const receive=(event:MessageEvent)=>{if(event.origin===location.origin&&event.data==='wearview-auth-finished')refresh()};
  if(!local)refresh();
  const withdrawn=()=>{setConsent(false);setConnected(false);onHealth(null)};window.addEventListener(consentWithdrawnEvent,withdrawn);
  const timer=setInterval(()=>void check(),30000);
  window.addEventListener('focus',refresh);window.addEventListener('message',receive);
  return()=>{window.removeEventListener(consentWithdrawnEvent,withdrawn);clearInterval(timer);window.removeEventListener('focus',refresh);window.removeEventListener('message',receive)};
 },[check]);
 async function disconnect(){setBusy(true);setConsent(false);setConnected(false);onHealth(null);setMessage('Withdrawing consent and ending this engine session…');try{await disconnectEngine();setMessage('Consent withdrawn. The engine session was revoked, its processing stopped and its stored results purged. Your selected browser photos remain until you clear them.')}catch(error){setMessage((error as Error).message)}finally{setBusy(false)}}
 return <section className="engine-status companion-setup" aria-label="Desktop companion setup">
  <div className="companion-heading"><Monitor size={22}/><div><strong>{connected?'This computer is ready':'Set up free local try-on'}</strong><p className="small muted">Desktop companion · no AI API fees</p></div>{connected&&<CheckCircle2 size={22} aria-label="Paired"/>}</div>
  <p className="small">The companion processes your selected photos on your own computer. It uses your GPU, memory and electricity. No photos go to a cloud AI service.</p>
  {!connected&&!bundled&&<details className="companion-guide" open>
   <summary>One-time download & setup</summary>
   <div className="actions" role="group" aria-label="Choose companion operating system"><Button aria-pressed={platform==='mac'} onClick={()=>setPlatform('mac')}>macOS</Button><Button aria-pressed={platform==='windows'} onClick={()=>setPlatform('windows')}>Windows · not ready</Button></div>
   <p className="small muted">{platform==='mac'?'Tested on an Apple M5 MacBook with 16 GB memory. Other Macs still need validation.':'Windows generation is disabled until an OS-isolated worker is implemented and tested on Windows. This source package is for development review only; do not install it expecting working try-on.'} Both packages need Python 3.12. Phones cannot generate.</p>
   {platform==='mac'&&<a className="btn primary companion-download" href={platform==='mac'?'/yourFittingRoom-companion.tar.gz':'/yourFittingRoom-companion-windows.zip'} download><Download size={17}/>{platform==='mac'?'Download Mac companion':'Download Windows source (ZIP)'}</a>}
   {platform==='mac'&&<ol className="setup-steps">
    <li><strong>Extract the download.</strong> Open the archive to get the <code>yourFittingRoom-companion</code> folder. Keep it in a location you own.</li>
    <li><strong>Install Python 3.12 if needed.</strong> Use <a href="https://www.python.org/downloads/" target="_blank" rel="noopener noreferrer">python.org (new tab)</a>. No account or API key is needed.</li>
    <li><strong>Open “{setupLauncher}” inside that folder.</strong> It opens a command window and downloads several GB of dependencies and models. Wait for “Setup complete”. Initial setup requires internet and free disk space; it sends no photos.</li>
   </ol>}
   <div className="notice"><strong>{platform==='mac'?'Mac says “cannot check for malicious software”?':'Windows may warn about an unsigned download'}</strong><p className="small">These launchers are unsigned source scripts, not verified installers. {platform==='mac'?<>Apple has not verified their developer or notarization. That warning alone is not a malware detection. Only if you have reviewed and trust this package, follow <a href="https://support.apple.com/en-us/102445" target="_blank" rel="noopener noreferrer">Apple’s per-app approval instructions (new tab)</a> yourself.</>:<>Windows installation is experimental. Review the source package before running it; follow your organisation’s policy if the download is blocked.</>} If protection reports detected malware, stop. We do not remove quarantine, disable antivirus, change execution policy or request admin rights.</p></div>
  </details>}
  {bundled&&<p className="small muted">Installed local workspace · development build. Release signing is pending. {platform==='mac'?'The Mac AI worker uses an App Sandbox prototype.':'The Windows AppContainer worker is an unverified experimental candidate; run Test Windows.cmd before using personal photos.'} Selected photos stay in this local workspace. Enter the companion’s private pairing code to enable processing.</p>}
  <div className="companion-session"><strong>{connected?'For your next session':'Each time you use the app'}</strong><p className="small">{bundled?'Keep this installed companion running.':<>Open <b>{startLauncher}</b> in the extracted folder and keep its command window open.</>} Copy its private pairing code here. Models are reused; they are not downloaded for each preview. Starting the engine checks their integrity.</p></div>
  <p className="engine-availability small" role="status">{connected?'Paired · local processing enabled':available?'Engine found · consent and pairing required':'Engine not connected · start the companion, then check again'}</p>
  {engineProblem&&<p className="small" role="alert">{engineProblem}</p>}
  {!connected&&<form onSubmit={async e=>{
   e.preventDefault();if(!consent||busy)return;setBusy(true);setMessage('Connecting to this computer…');
   try{await pairEngine(code);selectProcessingMode('companion');setCode('');if(await check())setMessage('Connected. You can upload clothing and your photo, review the garment, then try it on.');else{await disconnectEngine();setMessage('The isolated engine is not ready. Check its startup error; no unrestricted processing is available.')}}
   catch(error){onHealth(null);setConnected(false);setMessage(error instanceof Error?error.message:'Connection failed. Your photos are kept.')}
   finally{setBusy(false)}
  }}>
   <label htmlFor={`${id}-code`}>Private pairing code from the companion window</label>
   <input id={`${id}-code`} type="password" value={code} onChange={e=>setCode(e.target.value)} autoComplete="off" required maxLength={128} disabled={!hydrated||busy} aria-describedby={`${id}-privacy`}/>
   <label className="companion-consent small"><input type="checkbox" checked={consent} disabled={!hydrated||busy} onChange={e=>setConsent(e.target.checked)}/><span>I allow this tab to send only my selected clothing and person images to the companion at 127.0.0.1 on this computer for analysis and try-on.</span></label>
   <Button variant="primary" disabled={!hydrated||busy||!consent||!code.trim()} type="submit">{busy?'Connecting…':'Pair this computer'}</Button>
  </form>}
  <div className="actions"><Button variant="ghost" disabled={busy} onClick={async()=>{setBusy(true);setMessage('Checking the companion…');const ready=await check();setMessage(ready?'Local engine paired and ready.':'If the engine is running, enter its current code and consent to pair. If it was restarted or your four-hour session expired, pair again.');setBusy(false)}}>Check local engine</Button>{(connected||hasEngineSession())&&<Button variant="ghost" disabled={busy} onClick={()=>void disconnect()}>Disconnect & withdraw consent</Button>}{hosted&&!account&&<Button variant="ghost" onClick={()=>{try{signIn();setMessage('Complete sign-in, then select Try it on. Photos stay in this tab.')}catch(error){setMessage((error as Error).message)}}}>Sign in for generation</Button>}</div>
  <p id={`${id}-privacy`} className="small muted">Refresh ends this temporary photo session and requires pairing again. Pairing lasts up to four hours. Your model downloads stay on disk. Disconnect revokes this tab’s engine session and stops its jobs. Closing the companion ends all its sessions. {hosted?'Hosted generation also requires sign-in.':'Local use needs no sign-in or paid account.'}</p>
  {message&&<p className="companion-message small" role="status" aria-live="polite">{message}</p>}
 </section>
}
