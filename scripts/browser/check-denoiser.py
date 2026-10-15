"""Developer numerical parity check. Uses synthetic tensors, never personal photos."""
import os, sys, time, json, gc
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['MPLCONFIGDIR'] = str(ROOT / '.runtime/matplotlib')
sys.path.insert(0, str(ROOT / '.runtime/fashn-src/src'))
import torch
import onnxruntime as ort
ort.disable_telemetry_events()
from safetensors.torch import load_file
from fashn_vton.tryon_mmdit import TryOnModel
import fashn_vton.tryon_mmdit as mmdit

torch.set_num_threads(4)
def rope(pos, dim, theta):
    scale = torch.arange(0, dim, 2, dtype=torch.float32, device=pos.device) / dim
    out = torch.einsum('...n,d->...nd', pos, 1.0 / (theta ** scale))
    out = torch.stack([torch.cos(out), -torch.sin(out), torch.sin(out), torch.cos(out)], dim=-1)
    return out.reshape(*out.shape[:-1], 2, 2).float()
mmdit.rope = rope

rng = np.random.default_rng(42)
shape = (1, 3, 432, 288)
feeds = {name: rng.normal(size=shape).astype(np.float16) for name in ['x', 'person', 'garment']}
feeds.update({name: rng.uniform(-1, 1, (1, 1, 432, 288)).astype(np.float16) for name in ['person_pose', 'garment_pose']})
feeds.update(t=np.array([.25], np.float16), category=np.array([1], np.int64), mask=np.array([True], bool))
fixture='--browser-fixture' in sys.argv
if fixture:
    # Match the standalone browser benchmark's scalar half truncation exactly.
    def synthetic(count):
        f=(np.sin(np.arange(count,dtype=np.float64)*.017)*.6).astype(np.float32)
        bits=f.view(np.uint32);sign=(bits>>16)&0x8000
        exponent=((bits>>23)&255).astype(np.int32)-112;mantissa=bits&0x7fffff
        normal=sign|((np.maximum(exponent,0).astype(np.uint32)<<10)|(mantissa>>13))
        subnormal=sign|((mantissa|0x800000)>>np.clip(14-exponent,0,31).astype(np.uint32))
        return np.where(exponent<=0,np.where(exponent< -10,sign,subnormal),normal).astype(np.uint16).view(np.float16)
    for name in ['x','person','garment','person_pose','garment_pose']:
        feeds[name]=synthetic(feeds[name].size).reshape(feeds[name].shape)
device = 'mps' if torch.backends.mps.is_available() else 'cpu'
with torch.device('meta'):
    model = TryOnModel(input_shape=(432, 288))
model.load_state_dict(load_file(str(ROOT / '.runtime/weights/model.safetensors')), assign=True)
model.to(device=device, dtype=torch.float16).eval()
print('Running original PyTorch model on ' + device, flush=True)
start = time.perf_counter()
with torch.inference_mode():
    inputs = {name: torch.from_numpy(value).to(device) for name, value in feeds.items()}
    expected = model(inputs['x'], inputs['t'], inputs['person'], inputs['garment'], inputs['person_pose'], inputs['garment_pose'], mask=inputs['mask'], garment_categories=inputs['category'])['x'].float().cpu().numpy()
print('PyTorch seconds:', round(time.perf_counter() - start, 2), flush=True)
if fixture:
    expected.astype('<f4').tofile(ROOT/'.runtime/browser-synthetic-reference.f32')
    print('Saved original PyTorch synthetic output for browser comparison; no photos used.',flush=True)
    raise SystemExit(0)
del model, inputs
gc.collect()
if device == 'mps': torch.mps.empty_cache()
options = ort.SessionOptions()
options.intra_op_num_threads = 4
options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
print('Running converted graph on CPU (conversion parity, not browser benchmark)', flush=True)
session = ort.InferenceSession(str(ROOT / '.runtime/browser-models/denoiser.onnx'), sess_options=options, providers=['CPUExecutionProvider'])
start = time.perf_counter()
actual = session.run(['velocity'], feeds)[0].astype(np.float32)
delta = actual - expected
report = {'finite': bool(np.isfinite(actual).all()), 'mean_absolute_error': float(np.abs(delta).mean()), 'max_absolute_error': float(np.abs(delta).max()), 'reference_rms': float(np.sqrt((expected ** 2).mean())), 'relative_rms_error': float(np.sqrt((delta ** 2).mean()) / np.sqrt((expected ** 2).mean())), 'onnx_cpu_seconds': time.perf_counter() - start}
(ROOT / '.runtime/browser-model-parity.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
if not report['finite'] or report['relative_rms_error'] > .05:
    raise SystemExit('Conversion parity failed. Do not treat execution checks as quality validation.')
