"""Developer-only reference preview from the bundled public FASHN photos.

This does not start a server, accept user paths, or use a remote API.
The result is a native baseline, never a browser-performance benchmark.
"""
import os, sys, time, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['MPLCONFIGDIR'] = str(ROOT / '.runtime/matplotlib')
sys.path.insert(0, str(ROOT / '.runtime/fashn-src/src'))
import torch
import onnxruntime as ort
ort.disable_telemetry_events()
from PIL import Image
from safetensors.torch import load_file
from fashn_human_parser import FashnHumanParser
from fashn_vton.pipeline import TryOnPipeline
from fashn_vton.tryon_mmdit import TryOnModel
import fashn_vton.tryon_mmdit as mmdit

torch.set_num_threads(4)
device = 'mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu'
if device == 'cpu':
    raise SystemExit('No native GPU available. Baseline not run; no CPU timing is substituted.')
def rope(pos, dim, theta):
    scale = torch.arange(0, dim, 2, dtype=torch.float32, device=pos.device) / dim
    out = torch.einsum('...n,d->...nd', pos, 1.0 / (theta ** scale))
    out = torch.stack([torch.cos(out), -torch.sin(out), torch.sin(out), torch.cos(out)], dim=-1)
    return out.reshape(*out.shape[:-1], 2, 2).float()
mmdit.rope = rope

class Baseline(TryOnPipeline):
    def _sample(self,ca_images,garment_images,person_poses,garment_poses,garment_categories,**kwargs):
        if '--export-browser-fixture' not in sys.argv:
            return super()._sample(ca_images,garment_images,person_poses,garment_poses,garment_categories,**kwargs)
        x=torch.randn(ca_images.shape,dtype=self.inference_dtype,device=self.device)
        tensors={'x':x,'person':ca_images,'garment':garment_images,'person_pose':person_poses,'garment_pose':garment_poses}
        entries=[];payload=bytearray()
        for name,tensor in tensors.items():
            raw=tensor.cpu().numpy().astype('<f2').tobytes()
            entries.append({'name':name,'dims':list(tensor.shape),'offset':len(payload),'bytes':len(raw)})
            payload.extend(raw)
        (ROOT/'.runtime/browser-public-fixture.bin').write_bytes(payload)
        (ROOT/'.runtime/browser-public-fixture.json').write_text(json.dumps({'source':'bundled public FASHN examples; no private user photos','tensors':entries,'steps':20,'category':1},indent=2))
        print('Exported native preprocessing and initial noise for the bundled public photos only.',flush=True)
        raise SystemExit(0)
    def _setup_tryon_model(self):
        self.inference_dtype = torch.float16
        with torch.device('meta'):
            self.tryon_model = TryOnModel(input_shape=(432, 288))
        self.tryon_model.load_state_dict(load_file(str(ROOT / '.runtime/weights/model.safetensors')), assign=True)
        self.tryon_model.to(device=self.device, dtype=self.inference_dtype).eval()
    def _setup_hp_model(self):
        self.hp_model = FashnHumanParser(model_id=str(ROOT / '.runtime/weights/parser'), device='cpu')

start = time.perf_counter()
pipeline = Baseline(weights_dir=str(ROOT / '.runtime/weights'), device=device)
loaded = time.perf_counter()
data = ROOT / '.runtime/fashn-src/examples/data'
with Image.open(data / 'model.webp') as person, Image.open(data / 'garment.webp') as garment:
    result = pipeline(person.convert('RGB'), garment.convert('RGB'), category='tops', num_timesteps=20, seed=42)
image = result.images[0]
target = ROOT / '.runtime/browser-native-baseline.png'
image.save(target)
report = {'backend': 'native ' + device, 'resolution': list(image.size), 'steps': 20, 'category': 1, 'model_load_seconds': loaded - start, 'preprocess_and_generation_seconds': time.perf_counter() - loaded, 'note': 'Public sample native reference only. Not WebGPU quality or latency verification.'}
(ROOT / '.runtime/browser-native-baseline.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
