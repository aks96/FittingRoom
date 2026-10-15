"""Convert standard ONNX Attention to supported WebGPU MultiHeadAttention.

Trained weights, resolution, denoising steps and guidance are unchanged.
The original graph remains available for numerical benchmark comparisons.
"""
from pathlib import Path
import sys
import onnx
from onnx import helper, numpy_helper
import numpy as np
def convert_attention(model, precise=True, expected_count=28, expanded=False):
    values=list(model.graph.value_info)+list(model.graph.input)+list(model.graph.output)
    shapes={v.name:[d.dim_value for d in v.type.tensor_type.shape.dim] for v in values}
    types={v.name:v.type.tensor_type.elem_type for v in values}
    nodes=[];count=0
    for node in model.graph.node:
        if node.op_type!='Attention' or node.domain not in ('','ai.onnx'):
            nodes.append(node);continue
        attrs={a.name:helper.get_attribute_value(a) for a in node.attribute}
        if len(node.input)!=3 or len(node.output)!=1 or attrs.get('is_causal',0) or attrs.get('softcap',0):
            raise ValueError('Unsupported attention variant; conversion must not guess.')
        shape=shapes.get(node.input[0],[])
        if len(shape)!=4: raise ValueError('Static BNSH attention shape required.')
        b,heads,length,head_dim=shape
        if shapes.get(node.input[1])!=shape or shapes.get(node.input[2])!=shape: raise ValueError('Only equal-shape self-attention is supported.')
        if not all((b,heads,length,head_dim)): raise ValueError('Static attention shape required.')
        prefix='webgpu_attention_'+str(count)
        if expanded:
            # Expand the standard ONNX function body, including its split scale
            # and intermediate dtype. This avoids silently changing FP16 rounding.
            dtype=types[node.input[0]]
            scale=float(attrs.get('scale',head_dim**-.5))**.5
            model.graph.initializer.append(numpy_helper.from_array(np.array(scale,dtype=helper.tensor_dtype_to_np_dtype(dtype)),prefix+'_scale'))
            nodes.extend([
                helper.make_node('Mul',[node.input[0],prefix+'_scale'],[prefix+'_q_scaled']),
                helper.make_node('Mul',[node.input[1],prefix+'_scale'],[prefix+'_k_scaled']),
                helper.make_node('Cast',[prefix+'_q_scaled'],[prefix+'_q_float'],to=onnx.TensorProto.FLOAT),
                helper.make_node('Cast',[prefix+'_k_scaled'],[prefix+'_k_float'],to=onnx.TensorProto.FLOAT),
                helper.make_node('Transpose',[prefix+'_k_float'],[prefix+'_kt'],perm=[0,1,3,2]),
                helper.make_node('MatMul',[prefix+'_q_float',prefix+'_kt'],[prefix+'_scores_float']),
                helper.make_node('Cast',[prefix+'_scores_float'],[prefix+'_scores'],to=dtype),
                helper.make_node('Cast',[prefix+'_scores'],[prefix+'_softmax_input'],to=onnx.TensorProto.FLOAT),
                helper.make_node('Softmax',[prefix+'_softmax_input'],[prefix+'_probabilities_float'],axis=-1),
                helper.make_node('Cast',[prefix+'_probabilities_float'],[prefix+'_probabilities'],to=dtype),
                helper.make_node('Cast',[prefix+'_probabilities'],[prefix+'_prob_float'],to=onnx.TensorProto.FLOAT),
                helper.make_node('Cast',[node.input[2]],[prefix+'_v_float'],to=onnx.TensorProto.FLOAT),
                helper.make_node('MatMul',[prefix+'_prob_float',prefix+'_v_float'],[prefix+'_out_float']),
                helper.make_node('Cast',[prefix+'_out_float'],list(node.output),to=dtype)])
            count+=1
            continue
        model.graph.initializer.extend([
            numpy_helper.from_array(np.array([b,length,heads*head_dim],np.int64),prefix+'_flat_shape'),
            numpy_helper.from_array(np.array([b,length,heads,head_dim],np.int64),prefix+'_head_shape')])
        nodes.extend([
            helper.make_node('Transpose',[node.input[0]],[prefix+'_q_bsnh'],perm=[0,2,1,3]),
            helper.make_node('Reshape',[prefix+'_q_bsnh',prefix+'_flat_shape'],[prefix+'_q'])])
        attention_inputs=[prefix+'_q',node.input[1],node.input[2]]
        if precise:
            for i,value in enumerate(attention_inputs):
                target=prefix+'_float_'+str(i)
                nodes.append(helper.make_node('Cast',[value],[target],to=onnx.TensorProto.FLOAT))
                attention_inputs[i]=target
        nodes.append(helper.make_node('MultiHeadAttention',attention_inputs,[prefix+'_out_float' if precise else prefix+'_out'],domain='com.microsoft',num_heads=heads,scale=float(attrs.get('scale',head_dim**-.5))))
        if precise:nodes.append(helper.make_node('Cast',[prefix+'_out_float'],[prefix+'_out'],to=types[node.input[0]]))
        nodes.extend([
            helper.make_node('Reshape',[prefix+'_out',prefix+'_head_shape'],[prefix+'_out_bsnh']),
            helper.make_node('Transpose',[prefix+'_out_bsnh'],list(node.output),perm=[0,2,1,3])])
        count+=1
    if count!=expected_count: raise ValueError(f'Expected {expected_count} attention nodes, got {count}. Inspect before continuing.')
    del model.graph.node[:];model.graph.node.extend(nodes)
    if not any(o.domain=='com.microsoft' for o in model.opset_import):model.opset_import.append(helper.make_opsetid('com.microsoft',1))

    return model

if __name__=='__main__':
    ROOT=Path(__file__).resolve().parents[2]
    directory=ROOT/'.runtime/browser-models'
    source=directory/'denoiser.onnx'
    reference=directory/'denoiser.reference.onnx'
    current=onnx.load(str(source),load_external_data=False)
    if any(n.op_type=='Attention' and n.domain in ('','ai.onnx') for n in current.graph.node):
        reference.write_bytes(source.read_bytes())
    if not reference.exists():raise ValueError('Original reference graph is missing. Re-export before continuing.')
    model=onnx.load(str(reference),load_external_data=False)
    precise='--fp16' not in sys.argv
    model=convert_attention(model,precise=precise,expanded='--expanded' in sys.argv)
    candidate=directory/'denoiser.webgpu.onnx'
    onnx.save_model(model,str(candidate))
    onnx.checker.check_model(str(candidate))
    print(f'Prepared 28-node WebGPU attention candidate, fp32={precise}. Not installed; numerical/speed benchmark required.')
