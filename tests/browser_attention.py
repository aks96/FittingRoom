"""Attention conversion parity and fail-closed coverage; synthetic tensors only."""
import copy, importlib.util, unittest
from pathlib import Path
import numpy as np
import onnx
from onnx import helper, TensorProto
import onnxruntime as ort
ort.disable_telemetry_events()
spec=importlib.util.spec_from_file_location('attention_converter',Path(__file__).resolve().parents[1]/'scripts/browser/prepare-attention.py')
converter=importlib.util.module_from_spec(spec);spec.loader.exec_module(converter)

def attention_model(shape,dtype=TensorProto.FLOAT,**attrs):
    values=[helper.make_tensor_value_info(name,dtype,shape) for name in ['q','k','v']]
    output=helper.make_tensor_value_info('output',dtype,shape)
    node=helper.make_node('Attention',['q','k','v'],['output'],**attrs)
    graph=helper.make_graph([node],'reference',values,[output],value_info=values)
    model=helper.make_model(graph,opset_imports=[helper.make_opsetid('',23)])
    model.ir_version=10
    return model

class AttentionTests(unittest.TestCase):
    def test_expanded_half_precision_preserves_standard_attention(self):
        shape=[1,2,9,8];original=attention_model(shape,dtype=TensorProto.FLOAT16)
        expanded=converter.convert_attention(copy.deepcopy(original),expanded=True,expected_count=1)
        rng=np.random.default_rng(12);inputs={name:rng.normal(size=shape).astype(np.float16) for name in ['q','k','v']}
        reference=ort.InferenceSession(original.SerializeToString(),providers=['CPUExecutionProvider']).run(None,inputs)[0]
        actual=ort.InferenceSession(expanded.SerializeToString(),providers=['CPUExecutionProvider']).run(None,inputs)[0]
        np.testing.assert_allclose(actual,reference,rtol=.002,atol=.002)
    def test_transpose_head_mapping_and_scale(self):
        for shape,attrs in [([1,2,9,8],{}),([2,3,7,4],{'scale':.23})]:
            original=attention_model(shape,**attrs)
            rng=np.random.default_rng(42)
            inputs={name:rng.normal(size=shape).astype(np.float32) for name in ['q','k','v']}
            reference=ort.InferenceSession(original.SerializeToString(),providers=['CPUExecutionProvider']).run(None,inputs)[0]
            for precise,expanded in [(False,False),(True,False),(True,True)]:
                converted=converter.convert_attention(copy.deepcopy(original),precise=precise,expanded=expanded,expected_count=1)
                onnx.checker.check_model(converted)
                actual=ort.InferenceSession(converted.SerializeToString(),providers=['CPUExecutionProvider']).run(None,inputs)[0]
                np.testing.assert_allclose(actual,reference,rtol=1e-5,atol=1e-6)
    def test_unsupported_masks_causality_and_shapes_are_rejected(self):
        for attrs in [{'is_causal':1},{'softcap':.5}]:
            with self.assertRaises(ValueError):converter.convert_attention(attention_model([1,2,9,8],**attrs),expected_count=1)
        with self.assertRaises(ValueError):converter.convert_attention(attention_model([1,9,16]),expected_count=1)
        with self.assertRaises(ValueError):converter.convert_attention(attention_model([1,2,9,8]),expected_count=28)

if __name__=='__main__':unittest.main()
