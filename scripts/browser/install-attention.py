"""Install a locally benchmarked attention graph; never publishes anything."""
import json,hashlib,os
from pathlib import Path
import onnx
ROOT=Path(__file__).resolve().parents[2]
directory=ROOT/'.runtime/browser-models'
report=json.loads((ROOT/'.runtime/browser-attention-equivalent-benchmark.json').read_text())
rows=[v for v in report['variants'] if v['name']=='equivalent ONNX attention function on GPU']
if len(rows)!=1 or rows[0].get('error') or not rows[0].get('finite') or len(rows[0].get('runSeconds',[]))!=2 or rows[0].get('relativeRmsError',1)>.01:
    raise SystemExit('Candidate did not pass both measured runs and numerical checks. Not installed.')
candidate=directory/'denoiser.webgpu.onnx'
data=candidate.read_bytes();digest=hashlib.sha256(data).hexdigest()
if digest!=report.get('candidateSha256'):raise SystemExit('Candidate digest differs from the checked graph. Not installed.')
model=onnx.load(str(candidate),load_external_data=False)
if any(n.op_type in ('Attention','MultiHeadAttention') for n in model.graph.node):raise SystemExit('Expected only expanded GPU attention primitives.')
onnx.checker.check_model(str(candidate))
manifest=json.loads((directory/'manifest.json').read_text())
for entry in manifest['models']:
    if entry['name']=='denoiser.onnx':entry.update(bytes=len(data),sha256=digest)
manifest.update(version='browser-gpu-attention-v2',attention='expanded-standard-onnx')
# Atomic file replacements. Existing browser workers retain their old graph;
# fresh setup fetches the updated manifest. Personal photos are never involved.
temporary=directory/'denoiser.install.tmp';temporary.write_bytes(data);os.replace(temporary,directory/'denoiser.onnx')
temporary=directory/'manifest.install.tmp';temporary.write_text(json.dumps(manifest,indent=2));os.replace(temporary,directory/'manifest.json')
print('Installed verified local GPU attention graph. Existing weight files/checksums unchanged. Stop/re-enable browser AI to load it; no page refresh is required.')
