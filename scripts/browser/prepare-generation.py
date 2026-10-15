"""Prepare browser experiment graph without changing trained weights."""
import sys,os,json,hashlib,shutil
from pathlib import Path
import onnx
from onnx import helper,TensorProto,numpy_helper
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'.runtime/browser-models'
model=onnx.load(str(OUT/'denoiser.onnx'),load_external_data=False)
# Match the existing Metal adapter: rotary-position arithmetic uses float32,
# since WebGPU does not support float64 tensors.
for value in list(model.graph.value_info)+list(model.graph.input)+list(model.graph.output):
 if value.type.tensor_type.elem_type==TensorProto.DOUBLE:value.type.tensor_type.elem_type=TensorProto.FLOAT
for i,value in enumerate(model.graph.initializer):
 if value.data_type==TensorProto.DOUBLE:
  replacement=numpy_helper.from_array(numpy_helper.to_array(value,base_dir=str(OUT)).astype(np.float32),name=value.name)
  model.graph.initializer[i].CopyFrom(replacement)
for node in model.graph.node:
 for attr in node.attribute:
  if node.op_type=='Cast' and attr.name=='to' and attr.i==TensorProto.DOUBLE:attr.i=TensorProto.FLOAT
  if attr.type==onnx.AttributeProto.TENSOR and attr.t.data_type==TensorProto.DOUBLE:
   attr.t.CopyFrom(numpy_helper.from_array(numpy_helper.to_array(attr.t).astype(np.float32)))
nodes=[]
for index,node in enumerate(model.graph.node):
 if node.op_type!='RMSNormalization':nodes.append(node);continue
 prefix='browser_rms_'+str(index);attrs={a.name:helper.get_attribute_value(a) for a in node.attribute}
 axis=int(attrs.get('axis',-1));epsilon=float(attrs.get('epsilon',1e-5))
 model.graph.initializer.extend([helper.make_tensor(prefix+'_axes',TensorProto.INT64,[1],[axis]),helper.make_tensor(prefix+'_eps',TensorProto.FLOAT,[],[epsilon])])
 nodes.extend([
 helper.make_node('Cast',[node.input[0]],[prefix+'_float'],to=TensorProto.FLOAT),
 helper.make_node('Mul',[prefix+'_float',prefix+'_float'],[prefix+'_square']),
 helper.make_node('ReduceMean',[prefix+'_square',prefix+'_axes'],[prefix+'_mean'],keepdims=1),
 helper.make_node('Add',[prefix+'_mean',prefix+'_eps'],[prefix+'_stable']),
 helper.make_node('Sqrt',[prefix+'_stable'],[prefix+'_root']),
 helper.make_node('Div',[prefix+'_float',prefix+'_root'],[prefix+'_norm']),
 helper.make_node('Cast',[prefix+'_norm'],[prefix+'_half'],to=TensorProto.FLOAT16),
 helper.make_node('Mul',[prefix+'_half',node.input[1]],list(node.output))])
del model.graph.node[:];model.graph.node.extend(nodes)
onnx.save_model(model,str(OUT/'denoiser.onnx'))
shutil.copyfile(ROOT/'.runtime/weights/dwpose/dw-ll_ucoco_384.onnx',OUT/'pose.onnx')
entries=[]
for name in ['garment.onnx','parser.onnx','pose.onnx','denoiser.onnx','denoiser.onnx.data']:
 h=hashlib.sha256()
 with (OUT/name).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 entries.append({'name':name,'bytes':(OUT/name).stat().st_size,'sha256':h.hexdigest(),'url':'/api/browser-models/'+name})
(OUT/'manifest.json').write_text(json.dumps({'version':'browser-experiment-v1','purpose':'experimental-tryon','generationPrepared':True,'resolution':[432,288],'models':entries},indent=2))
print('Browser generator graph prepared. End-to-end browser verification is still required.')
