import base64,io,os,gc
from pathlib import Path
from contextlib import nullcontext
ROOT=Path(__file__).resolve().parents[1]
WEIGHTS=Path(os.environ.get('YOURFITTINGROOM_WEIGHTS',str(ROOT/'.runtime/weights')))
import numpy as np
import torch
from PIL import Image, ImageOps
from transformers import CLIPModel, CLIPProcessor
from fashn_human_parser import FashnHumanParser
from fashn_vton import TryOnPipeline
from fashn_vton.tryon_mmdit import TryOnModel
from fashn_vton import tryon_mmdit
from safetensors.torch import load_file
from einops import rearrange
from local_ai.garment_details import garment_view, detail_suggestions, FABRIC_PROMPTS, AUDIENCE_PROMPTS
from local_ai.garment_catalog import CATALOG, BY_CATEGORY, native_category
from local_ai.compute import select_device,inference_dtype,rotary_dtype,model_attention


parser=clip=processor=pipeline=None
requested=os.environ.get('YOURFITTINGROOM_DEVICE','auto')
DEVICE,COMPUTE_PROFILE=select_device(torch,requested,int(os.environ.get('YOURFITTINGROOM_DEVICE_INDEX','0')))
DEVICE_LABEL=COMPUTE_PROFILE+(':'+str(torch.device(DEVICE).index) if torch.device(DEVICE).index else '')
torch.set_num_threads(4)
def decode(value):
    if not value.startswith(('data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,')):
        raise ValueError('Only local JPG, PNG or WebP image data is accepted.')
    raw=base64.b64decode(value.split(',',1)[1],validate=True)
    if len(raw)>12*1024*1024: raise ValueError('Image exceeds 12 MB after editing.')
    with Image.open(io.BytesIO(raw)) as image:
        if image.width*image.height>24_000_000: raise ValueError('Image is too large. Choose a smaller photo.')
        if image.format not in ('JPEG','PNG','WEBP') or getattr(image,'n_frames',1)!=1:
            raise ValueError('Only single-frame JPG, PNG or WebP images are supported.')
        image.load()
        return ImageOps.exif_transpose(image).convert('RGB')

def get_parser():
    global parser
    if parser is None: parser=FashnHumanParser(model_id=str(WEIGHTS/'parser'),device='cpu')
    return parser

def get_clip():
    global clip,processor
    if clip is None:
        clip=CLIPModel.from_pretrained(str(WEIGHTS/'clip'),local_files_only=True).eval()
        processor=CLIPProcessor.from_pretrained(str(WEIGHTS/'clip'),local_files_only=True)
    return clip,processor

def classify(image,labels):
    model,proc=get_clip()
    values=proc(text=[f'a photo of {text}' for text in labels],images=image,return_tensors='pt',padding=True)
    with torch.inference_mode(): scores=model(**values).logits_per_image[0].softmax(-1).cpu().numpy()
    order=np.argsort(-scores)
    return int(order[0]),float(scores[order[0]]-scores[order[1]])

def classify_groups(image, groups):
    model,proc=get_clip()
    texts=[f'a photo of {label}' for labels in groups.values() for label in labels]
    values=proc(text=texts,images=image,return_tensors='pt',padding=True)
    with torch.inference_mode(): logits=model(**values).logits_per_image[0].float().cpu().numpy()
    results={};start=0
    for name,labels in groups.items():
        values=logits[start:start+len(labels)];start+=len(labels)
        scores=np.exp(values-values.max());scores/=scores.sum();order=np.argsort(-scores)
        results[name]=(int(order[0]),float(scores[order[0]]-scores[order[1]]))
    return results

def color_name(rgb):
    import colorsys
    r,g,b=np.asarray(rgb)/255.; h,s,v=colorsys.rgb_to_hsv(r,g,b); h*=360
    if v<.18:return 'Black'
    if s<.12:return 'White' if v>.86 else 'Grey'
    if s<.3 and v>.8:return 'Ivory' if h<70 else 'Light grey'
    if h<20 or h>=345:return 'Pink' if v>.7 and s<.55 else 'Maroon' if v<.55 else 'Red'
    if h<45:return 'Brown' if v<.6 else 'Beige' if s<.45 else 'Orange'
    if h<70:return 'Yellow'
    if h<165:return 'Sage' if s<.35 and v>.4 else 'Green'
    if h<200:return 'Teal'
    if h<260:return 'Navy' if v<.45 else 'Blue'
    if h<320:return 'Plum' if v<.6 else 'Purple'
    return 'Pink'

def analyze_image(value):
    try:
        image=decode(value)
        with nullcontext():
            mask=get_parser().predict(image)
            categories=[item['prompt'] for item in CATALOG]
            index,margin=classify(image,categories)
            category=CATALOG[index]['value']
            photo_type='model' if np.isin(mask,[1,2,12,13,14]).sum()/mask.size>.035 else 'flat-lay'
            pixels=np.array(image)
            garment_mask=np.isin(mask,BY_CATEGORY[category]['maskIds'])
            reliable=garment_mask.sum()>mask.size*.01
            if reliable: values=pixels[garment_mask]
            else:
                # Fallback only estimates foreground pixels; it does not claim segmentation success.
                edge=np.concatenate([pixels[0],pixels[-1],pixels[:,0],pixels[:,-1]])
                background=np.median(edge,axis=0)
                foreground=np.linalg.norm(pixels.astype(float)-background,axis=2)>35
                values=pixels[foreground]
            if len(values)<100: colour='Uncertain'; swatch='#888888'
            else:
                values=values[::max(1,len(values)//12000)]
                # Dominant cluster preserves dark and pale garment colours; no background sample substitution.
                import cv2
                cv2.setRNGSeed(42)
                _,label,centres=cv2.kmeans(values.astype(np.float32),min(3,len(values)),None,(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,25,.5),3,cv2.KMEANS_PP_CENTERS)
                rgb=centres[np.argmax(np.bincount(label.ravel()))].clip(0,255).astype(int)
                colour=color_name(rgb);swatch='#'+''.join(f'{c:02x}' for c in rgb)
            isolated=garment_view(image,mask,category,photo_type)
            try:
                scores=classify_groups(isolated if isolated is not None else image,{
                    'pattern':['a solid-colour garment','a floral print garment','a striped garment','a checked plaid garment','a garment with a graphic print'],
                    'sleeves':['a sleeveless garment','a short-sleeve garment','a long-sleeve garment'],
                    'fabric':FABRIC_PROMPTS,'audience':AUDIENCE_PROMPTS,
                })
                extra=detail_suggestions(scores,isolated is not None)
            finally:
                if isolated is not None:isolated.close()
            pattern_index,pattern_margin=scores['pattern']
            pattern=['Solid','Floral','Striped','Checked','Graphic'][pattern_index]
            sleeve_index,sleeve_margin=scores['sleeves']
        return {'category':category,'colour':colour,'swatch':swatch,'photoType':photo_type,'pattern':pattern if pattern_margin>.12 else 'Uncertain','sleeves':'Not applicable' if BY_CATEGORY[category]['native']=='bottoms' else ['Sleeveless','Short sleeves','Long sleeves'][sleeve_index] if sleeve_margin>.12 else 'Uncertain','categoryReview':margin<.2 or category=='Unsupported','colourReview':not reliable,**extra,'size':'Not determined from the image','fit':'Needs garment dimensions and body measurements','method':'Local CLIP visual suggestions + garment segmentation + colour clustering; clothing range and fabric appearance require review'}
    except Exception: raise ValueError('Could not analyse this image. Choose a clear garment image or confirm details manually.')
    finally:
        if 'image' in locals():image.close()

# Metal/Intel and the AMD candidate use FP32 rotary embeddings; no FP64 requirement.
def metal_rope(pos,dim,theta):
    scale=torch.arange(0,dim,2,dtype=rotary_dtype(torch,pos.device.type,COMPUTE_PROFILE),device=pos.device)/dim
    out=torch.einsum('...n,d->...nd',pos,1.0/(theta**scale))
    out=torch.stack([torch.cos(out),-torch.sin(out),torch.sin(out),torch.cos(out)],dim=-1)
    return rearrange(out,'b n d (i j) -> b n d i j',i=2,j=2).float()

class LocalPipeline(TryOnPipeline):
    def _setup_tryon_model(self):
        self.inference_dtype=inference_dtype(torch,self.device.type,COMPUTE_PROFILE)
        state=load_file(str(WEIGHTS/'model.safetensors'),device='cpu')
        with torch.device('meta'): self.tryon_model=TryOnModel()
        self.tryon_model.load_state_dict(state,assign=True)
        self.tryon_model.to(self.device,dtype=self.inference_dtype).eval()
        del state
    def _setup_hp_model(self): self.hp_model=get_parser()
    def _setup_pose_model(self):
        # Both packages use CPU ONNX pose estimation; only diffusion uses CUDA/Metal.
        from fashn_vton.dwpose import DWposeDetector
        self.pose_model=DWposeDetector(checkpoints_dir=str(WEIGHTS/'dwpose'),device='cpu')


def generate(payload,stage):
    global pipeline
    person=garment=None
    try:
        person=decode(payload['person']);garment=decode(payload['garment'])
        native=native_category(payload['category'])
        stage('aligning-images')
        mask=get_parser().predict(person)
        if (mask==1).sum()/mask.size<.001 or (mask!=0).sum()/mask.size<.03:
            raise ValueError('A clear person could not be detected. Upload a front-facing photo with your face and torso visible; include hips and legs for lower-body or one-piece outfits.')
        if native in ('bottoms','one-pieces') and np.isin(mask,[4,5,6,14,15]).sum()/mask.size<.02:
            raise ValueError('A clear person could not be detected with enough lower-body coverage. Upload a full-body photo showing hips and legs for this garment.')
        stage('loading-model')
        if pipeline is None:
            tryon_mmdit.rope=metal_rope
            if COMPUTE_PROFILE in ('rocm','xpu'):
                tryon_mmdit._attn_processor=lambda q,k,v:model_attention(torch,q,k,v,COMPUTE_PROFILE)
            pipeline=LocalPipeline(weights_dir=str(WEIGHTS),device=DEVICE)
        original=pipeline.tryon_model.forward_for_cfg
        def progress(*args,**kwargs):stage('generating');return original(*args,**kwargs)
        pipeline.tryon_model.forward_for_cfg=progress
        try:
            result=pipeline(person_image=person,garment_image=garment,category=native,garment_photo_type=payload['photoType'],num_timesteps=payload['steps'],guidance_scale=1.5,skip_cfg_last_n_steps=1,num_samples=1,seed=42,segmentation_free=True)
        finally:pipeline.tryon_model.forward_for_cfg=original
        output=io.BytesIO();result.images[0].save(output,format='PNG')
        return 'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()
    finally:
        if person is not None:person.close()
        if garment is not None:garment.close()
        gc.collect()
        if DEVICE=='mps':torch.mps.empty_cache()
        elif COMPUTE_PROFILE in ('cuda','rocm'):torch.cuda.empty_cache()
        elif COMPUTE_PROFILE=='xpu':torch.xpu.empty_cache()
