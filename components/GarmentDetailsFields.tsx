'use client';
import {garmentCatalog,type Audience,type Category,type Garment} from '@/lib/services';

export default function GarmentDetailsFields({garment,onChange}:{garment:Garment;onChange:(garment:Garment)=>void}){
 const update=(patch:Partial<Garment>)=>onChange({...garment,...patch,confirmed:false});
 return <>
  <label htmlFor="garment-audience">Intended clothing range (confirm or correct)</label>
  <select id="garment-audience" value={garment.audience||''} onChange={e=>update({audience:e.target.value as Audience||undefined})} aria-describedby="clothing-range-help">
   <option value="">Choose a range</option><option>Women</option><option>Men</option><option>Unisex</option>
  </select>
  <p id="clothing-range-help" className="small muted">{garment.analysis?.audience&&garment.analysis.audience!=='Uncertain'?`Image suggestion: ${garment.analysis.audience}. Please verify the product label.`:'The intended range is uncertain; choose from the product information.'} This describes the clothing, not the person’s gender. The confirmed range is checked against the wearer profile before generating.</p>
  <label htmlFor="garment-category">Suggested category (confirm or correct)</label>
  <select id="garment-category" value={garment.category} onChange={e=>update({category:e.target.value as Category})}>{['Tops','Lower-body','One-piece','Other'].map(group=><optgroup key={group} label={group}>{garmentCatalog.filter(item=>item.group===group).map(item=><option value={item.value} key={item.value}>{item.value==='Unsupported'?'Other / unsupported':item.value}</option>)}</optgroup>)}</select>
  <p className="small muted">Choose one garment at a time. New lower-body and one-piece categories are experimental; shoes, accessories and layered multi-item outfits are unsupported.</p>
  <label htmlFor="photo-type">Garment photograph</label>
  <select id="photo-type" value={garment.photoType||'model'} onChange={e=>update({photoType:e.target.value as 'model'|'flat-lay'})} aria-describedby="garment-photo-help"><option value="model">Worn by a retailer model</option><option value="flat-lay">Garment only / flat lay</option></select>
  <p id="garment-photo-help" className="small muted">Choose the correct view: the model processes worn garments and garment-only photographs differently. Prefer a clear front view of one garment.</p>
  <label htmlFor="garment-fabric">Fabric appearance (visual suggestion)</label>
  <input id="garment-fabric" value={garment.fabricAppearance||''} onChange={e=>update({fabricAppearance:e.target.value})} placeholder="e.g. Knit / jersey-like" maxLength={120} aria-describedby="garment-fabric-help"/>
  <p id="garment-fabric-help" className="small muted">{garment.analysis?.fabricAppearance?`Image suggestion: ${garment.analysis.fabricAppearance}. `:''}Appearance cannot verify cotton, polyester, silk, blends or fibre percentages.</p>
  <label htmlFor="garment-material">Material from the garment label (optional)</label>
  <input id="garment-material" value={garment.material||''} onChange={e=>update({material:e.target.value})} placeholder="e.g. 95% cotton, 5% elastane" maxLength={160}/>
  <p className="small muted">These notes help you review the product. The try-on model uses your garment image; it does not simulate the material from this text.</p>
  {garment.analysis&&<div className="detected-details"><span className="colour-swatch" style={{background:garment.analysis.swatch}}/><p>Pattern: {garment.analysis.pattern}<br/>Sleeves: {garment.analysis.sleeves}</p><p className="small muted">{garment.analysis.categoryReview?'Category is uncertain. Please check it.':'Category suggested by local image recognition.'}<br/>{garment.analysis.colourReview?'Colour estimate may include background pixels.':'Colour estimated from segmented garment pixels.'}</p></div>}
 </>
}
