'use client';
import type {PreviewQuality} from '@/lib/services';
export default function PreviewSettings({value,onChange,disabled}:{value:PreviewQuality;onChange:(quality:PreviewQuality)=>void;disabled:boolean}){
 return <section className="card preview-settings" aria-labelledby="preview-settings-heading">
  <h2 id="preview-settings-heading">Preview detail</h2>
  <label htmlFor="preview-quality">Local generation setting</label>
  <select id="preview-quality" value={value} disabled={disabled} onChange={e=>onChange(e.target.value as PreviewQuality)} aria-describedby="preview-quality-help"><option value="balanced">Balanced · 30 model steps</option><option value="fast">Fast · 20 model steps</option></select>
  <p id="preview-quality-help" className="small muted">Balanced gives the model more sampling steps and takes longer. It may help fine detail; it does not guarantee realistic fabric. No filters or artificial sharpening are applied.</p>
  <p className="small muted">Use sharp, evenly lit photos. Tiny product thumbnails, blur, heavy compression and overlapping clothes can lose texture. This model’s native canvas is 576 × 864 pixels; zooming does not restore missing detail.</p>
 </section>
}
