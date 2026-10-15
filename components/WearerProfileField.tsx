'use client';
import type {WearerProfile} from '@/lib/services';
export default function WearerProfileField({value,onChange}:{value?:WearerProfile;onChange:(profile:WearerProfile|undefined)=>void}){
 return <div className="wearer-profile"><label htmlFor="wearer-profile">Wearer profile for this photo (you choose)</label><select id="wearer-profile" value={value||''} onChange={e=>onChange(e.target.value as WearerProfile||undefined)} aria-describedby="wearer-profile-help"><option value="">Choose a profile</option><option>Women</option><option>Men</option></select><p id="wearer-profile-help" className="small muted">Use the profile the wearer specifies. We do not infer or verify gender from the image. Women’s and men’s clothing must match this selection; confirmed unisex clothing works with either profile. Replacing the photo requires a new selection.</p></div>
}
