"""Fixed Windows backend/runtime choices. No user-supplied executable or index."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'security/windows-compute.json').read_text())
PROFILES=CONFIG['profiles'];AMD_TARGETS=tuple(CONFIG['amdTargets'])

def validate(compute,amd_target='all',device_index=0):
    if not isinstance(compute,str) or compute not in PROFILES:raise ValueError('Choose NVIDIA CUDA, AMD ROCm, Intel XPU or explicit CPU testing.')
    if amd_target not in AMD_TARGETS:raise ValueError('Unsupported AMD target profile.')
    if compute!='rocm' and amd_target!='all':raise ValueError('AMD target applies only to the ROCm profile.')
    if type(device_index) is not int or not 0<=device_index<=15:raise ValueError('Invalid GPU adapter index.')
    if compute=='cpu' and device_index!=0:raise ValueError('CPU mode does not select a GPU adapter.')
    return compute

def runtime_folder(root,compute,amd_target='all'):
    validate(compute,amd_target)
    return Path(root)/'.runtime/windows-venvs'/(compute+'-'+amd_target if compute=='rocm' else compute)

def read_config(root=ROOT):
    file=Path(root)/'.runtime/companion-device.json'
    if not file.is_file():raise RuntimeError('Finish Set up.cmd first. No completed Windows setup was found.')
    config=json.loads(file.read_text())
    if not isinstance(config,dict):raise ValueError('Invalid Windows device configuration.')
    validate(config.get('compute'),config.get('amdTarget','all'),config.get('deviceIndex',0))
    if 'schemaVersion' in config and (type(config['schemaVersion']) is not int or config['schemaVersion']!=1):raise ValueError('Unsupported Windows setup version. Rerun Set up.cmd.')
    if config.get('compute')=='rocm' and config.get('runtimeTarget') not in AMD_TARGETS[1:]:raise ValueError('The AMD runtime target is missing or unsupported. Rerun AMD setup.')
    return config

def device_environment(config):
    validate(config.get('compute'),config.get('amdTarget','all'),config.get('deviceIndex',0))
    result={'YOURFITTINGROOM_DEVICE':config['compute'],'YOURFITTINGROOM_DEVICE_INDEX':str(config.get('deviceIndex',0))}
    if config['compute']=='rocm':
        target=config.get('runtimeTarget')
        if target not in AMD_TARGETS[1:]:raise ValueError('Invalid AMD runtime target.')
        result['YOURFITTINGROOM_ROCM_TARGET']=target;result['ROCM_SDK_TARGET_FAMILY']=target
    return result

def runtime_python(root,config):
    compute=config.get('compute');target=config.get('amdTarget','all')
    validate(compute,target,config.get('deviceIndex',0))
    # Existing private CUDA/CPU test installations can still start. New setup
    # isolates backends so switching never replaces another backend's Torch.
    legacy='schemaVersion' not in config and compute in ('cuda','cpu')
    folder=Path(root)/'.runtime/ai-venv' if legacy else runtime_folder(root,compute,target)
    python=folder/'Scripts/python.exe'
    if not python.is_file():raise RuntimeError('The selected Windows runtime is missing. Rerun Set up.cmd for that profile.')
    return python
