"""Native Torch backend selection and representative operator probe; no fallback.

AMD ROCm exposes Torch's cuda API. It must never be mistaken for NVIDIA CUDA.
Torch is supplied by the caller so policy tests do not load AI or a GPU runtime.
"""
def select_device(torch,profile,index=0):
    if type(index) is not int or not 0<=index<=15:raise RuntimeError('Invalid GPU adapter index.')
    if profile=='auto':
        profile='mps' if torch.backends.mps.is_available() else 'rocm' if torch.version.hip and torch.cuda.is_available() else 'cuda' if torch.cuda.is_available() else 'xpu' if hasattr(torch,'xpu') and torch.xpu.is_available() else 'unavailable'
    if profile=='cpu':
        if index:raise RuntimeError('CPU mode does not select a GPU.')
        return 'cpu','cpu'
    if profile=='mps':
        if index or not torch.backends.mps.is_available():raise RuntimeError('Selected Apple GPU unavailable.')
        return 'mps','mps'
    if profile in ('cuda','rocm'):
        hip=bool(torch.version.hip)
        if hip!=(profile=='rocm'):raise RuntimeError('Wrong Torch build for the selected GPU. Rerun setup with the matching NVIDIA or AMD profile.')
        backend=torch.cuda
    elif profile=='xpu':backend=getattr(torch,'xpu',None)
    else:raise RuntimeError('No supported GPU selected. Choose a supported backend, or explicitly choose slow CPU testing.')
    if backend is None or not backend.is_available() or index>=backend.device_count():
        raise RuntimeError('Selected GPU unavailable. Check its supported-device list and driver; CPU mode requires an explicit choice.')
    backend.set_device(index)
    return ('cuda' if profile=='rocm' else profile)+':'+str(index),profile

def inference_dtype(torch,device_type,profile):
    if device_type in ('mps','xpu') or profile=='rocm':return torch.float16
    if device_type=='cuda' and torch.cuda.is_bf16_supported():return torch.bfloat16
    return torch.float32

def rotary_dtype(torch,device_type,profile):
    return torch.float32 if device_type in ('mps','xpu') or profile=='rocm' else torch.float64

def model_attention(torch,q,k,v,profile,chunk_size=256):
    """Bound query memory on AMD/Intel without truncating keys or attention.

    Some Windows builds lack fused SDPA kernels. Full mathematical attention can
    allocate gigabytes of scores. Query slices retain the complete key/value
    sequence and preserve the noncausal, zero-dropout model computation.
    """
    if profile not in ('rocm','xpu'):return torch.nn.functional.scaled_dot_product_attention(q,k,v)
    if type(chunk_size) is not int or not 1<=chunk_size<=256:raise ValueError('Invalid attention chunk size.')
    return torch.cat([torch.nn.functional.scaled_dot_product_attention(q[...,start:start+chunk_size,:],k,v)
                      for start in range(0,q.shape[-2],chunk_size)],dim=-2)

def probe_compute(torch,profile,index=0):
    device,profile=select_device(torch,profile,index)
    dtype=inference_dtype(torch,torch.device(device).type,profile)
    info={'torchVersion':str(torch.__version__),'device':device,'computeProfile':profile,'precision':str(dtype)}
    backend=torch.cuda if profile in ('cuda','rocm') else torch.xpu if profile=='xpu' else None
    if backend:
        props=backend.get_device_properties(index)
        info.update(gpuName=props.name,vramBytes=props.total_memory)
        if profile=='rocm':info['gpuArchitecture']=str(getattr(props,'gcnArchName','')).split(':',1)[0]
        info['hipVersion' if profile=='rocm' else 'cudaVersion' if profile=='cuda' else 'xpuRuntime']=str(torch.version.hip if profile=='rocm' else torch.version.cuda if profile=='cuda' else 'native PyTorch')
    # Use nonconstant inputs and compare actual native operations to CPU FP32.
    # This catches missing kernels, silent NaNs and unsupported FP64/SDPA paths
    # before personal images or the large diffusion model reach this worker.
    import torch.nn.functional as F
    with torch.inference_mode():
        a=torch.arange(256,dtype=torch.float32).reshape(16,16)/256
        expected=a@a.T;actual=a.to(device=device,dtype=dtype)@a.T.to(device=device,dtype=dtype)
        compute_ok=torch.allclose(actual.float().cpu(),expected,atol=.04,rtol=.04)
        q=torch.sin(torch.arange(2*4*64*32,dtype=torch.float32)/17).reshape(2,4,64,32)
        gpu=q.to(device=device,dtype=dtype)
        attention=model_attention(torch,gpu,gpu,gpu,profile,chunk_size=32)
        expected_attention=F.scaled_dot_product_attention(q,q,q)
        norm=F.layer_norm(gpu,(32,));reference_norm=F.layer_norm(q,(32,))
        positions=torch.arange(64,device=device,dtype=torch.float32)
        frequencies=torch.arange(0,32,2,device=device,dtype=rotary_dtype(torch,torch.device(device).type,profile))/32
        angles=torch.einsum('n,d->nd',positions,1.0/(10000**frequencies))
        rotary=torch.cos(angles).float().cpu()
        expected_rotary=torch.cos(torch.einsum('n,d->nd',torch.arange(64,dtype=torch.float32),1.0/(10000**(torch.arange(0,32,2,dtype=torch.float32)/32))))
        embedding=F.embedding(torch.tensor([1,2,3],device=device),torch.ones((4,32),device=device,dtype=dtype))
        image=torch.sin(torch.arange(4*16*16,dtype=torch.float32)/13).reshape(1,4,16,16)
        kernel=torch.cos(torch.arange(8*4*3*3,dtype=torch.float32)/7).reshape(8,4,3,3)/36
        convolution=F.conv2d(image.to(device=device,dtype=dtype),kernel.to(device=device,dtype=dtype))
        random=torch.randn((4,4),device=device,dtype=dtype)
        operators_ok=(torch.allclose(attention.float().cpu(),expected_attention,atol=.04,rtol=.04)
                      and torch.allclose(norm.float().cpu(),reference_norm,atol=.04,rtol=.04)
                      and torch.allclose(rotary,expected_rotary,atol=.001,rtol=.001)
                      and torch.allclose(convolution.float().cpu(),F.conv2d(image,kernel),atol=.04,rtol=.04)
                      and bool(torch.isfinite(embedding).all().item()) and bool(torch.isfinite(random).all().item()))
        if backend:backend.synchronize(index)
    if not compute_ok or not operators_ok:raise RuntimeError('Selected backend failed the numerical/operator probe. Generation is disabled.')
    return {'computeAvailable':True,'modelOperatorsAvailable':True},info
