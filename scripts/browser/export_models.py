"""Developer-only conversion of installed, pinned models. No personal photos used."""
import os,sys,json,hashlib,time,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
sys.path.insert(0,str(ROOT/'.runtime/fashn-src/src'))
import torch
import torch.nn.functional as F
from transformers import CLIPModel,CLIPProcessor,SegformerForSemanticSegmentation
OUT=ROOT/'.runtime/browser-models';OUT.mkdir(exist_ok=True)
torch.set_num_threads(4)
labels=['a t-shirt with a crew neck and no buttons','a button-front collared shirt','a blouse or womens top','a dress covering torso and thighs','a solid-colour garment','a floral print garment','a striped garment','a checked plaid garment','a garment with a graphic print','a sleeveless garment','a short-sleeve garment','a long-sleeve garment']

def export_analysis():
    if not (OUT/'garment.onnx').exists():
        clip=CLIPModel.from_pretrained(str(ROOT/'.runtime/weights/clip'),local_files_only=True,attn_implementation='eager').eval()
        proc=CLIPProcessor.from_pretrained(str(ROOT/'.runtime/weights/clip'),local_files_only=True)
        tokens=proc(text=['a photo of '+x for x in labels],padding=True,return_tensors='pt')
        with torch.no_grad():
            text=clip.text_projection(clip.text_model(**tokens).pooler_output);text=F.normalize(text,dim=-1)
        class Vision(torch.nn.Module):
            def __init__(self):
                super().__init__();self.vision=clip.vision_model;self.projection=clip.visual_projection;self.register_buffer('text',text);self.register_buffer('scale',clip.logit_scale.exp().detach())
            def forward(self,pixels):
                vision=self.projection(self.vision(pixel_values=pixels).pooler_output)
                return F.normalize(vision,dim=-1)@self.text.T*self.scale
        torch.onnx.export(Vision().eval(),(torch.zeros(1,3,224,224),),str(OUT/'garment.onnx'),input_names=['pixels'],output_names=['logits'],opset_version=17,dynamo=False)
        del clip;gc.collect()
    if not (OUT/'parser.onnx').exists():
        parser=SegformerForSemanticSegmentation.from_pretrained(str(ROOT/'.runtime/weights/parser'),local_files_only=True).eval()
        class Parser(torch.nn.Module):
            def __init__(self):super().__init__();self.model=parser
            def forward(self,pixels):return self.model(pixel_values=pixels).logits.argmax(dim=1).to(torch.int32)
        torch.onnx.export(Parser().eval(),(torch.zeros(1,3,576,384),),str(OUT/'parser.onnx'),input_names=['pixels'],output_names=['mask'],opset_version=17,dynamo=False)
    entries=[]
    for name in ['garment.onnx','parser.onnx']:
        data=(OUT/name).read_bytes();entries.append({'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'url':'/api/browser-models/'+name})
    (OUT/'manifest.json').write_text(json.dumps({'version':'analysis-v1','purpose':'clothing-analysis','generationReady':False,'models':entries},indent=2))
    print('Browser analysis artifacts exported.',flush=True)

def export_generation():
    from safetensors.torch import load_file
    from fashn_vton.tryon_mmdit import TryOnModel
    class Denoise(torch.nn.Module):
        def __init__(self):
            super().__init__()
            with torch.device('meta'):self.model=TryOnModel(input_shape=(432,288))
            self.model.load_state_dict(load_file(str(ROOT/'.runtime/weights/model.safetensors')),assign=True)
            self.model.to(dtype=torch.float16).eval()
        def forward(self,x,t,person,garment,person_pose,garment_pose,category,mask):
            return self.model(x,t,person,garment,person_pose,garment_pose,mask=mask,garment_categories=category)['x']
    model=Denoise().eval()
    images=[torch.zeros(1,3,432,288,dtype=torch.float16) for _ in range(3)];poses=[torch.zeros(1,1,432,288,dtype=torch.float16) for _ in range(2)]
    inputs=(images[0],torch.zeros(1,dtype=torch.float16),images[1],images[2],*poses,torch.zeros(1,dtype=torch.int64),torch.ones(1,dtype=torch.bool))
    torch.onnx.export(model,inputs,str(OUT/'denoiser.onnx'),input_names=['x','t','person','garment','person_pose','garment_pose','category','mask'],output_names=['velocity'],opset_version=23,dynamo=True,external_data=True)
    print('Experimental 432×288 denoiser exported. Browser inference still requires verification.',flush=True)
if __name__=='__main__':
    if '--generation' in sys.argv:export_generation()
    else:export_analysis()
