"""Explicit Windows beta setup. Installs into this folder; no admin rights or policy changes."""
import argparse
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_ai.source_integrity import prepare,extract_source
from local_ai.windows_profiles import CONFIG,PROFILES,AMD_TARGETS,runtime_folder,validate
TORCH_INDEX = {name:profile['index'] for name,profile in PROFILES.items()}

def validate_platform(system, machine, version, bits=64):
    if system != 'Windows' or machine.lower() not in ('amd64','x86_64') or bits!=64:
        raise RuntimeError('This Windows beta needs 64-bit x86 Windows. ARM Windows and other systems are not supported by this launcher.')
    if tuple(version[:2]) != (3,12):
        raise RuntimeError('Install 64-bit Python 3.12 from python.org with the Python launcher, then reopen Set up.cmd.')

def environment(root):
    return {**os.environ,'HF_HOME':str(root / '.runtime/hf-cache'),'MPLCONFIGDIR':str(root / '.runtime/mpl-cache'),
            'HF_HUB_OFFLINE':'0','TRANSFORMERS_OFFLINE':'0','HF_HUB_DISABLE_TELEMETRY':'1','HF_HUB_DISABLE_XET':'1'}

def run(args, env):
    subprocess.run([str(item) for item in args],cwd=ROOT,env=env,check=True)

def dependency_findings(result):
    if result.returncode==0:return
    lines=[line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    # The app deliberately uses CPU ONNX pose estimation on every backend.
    # Keep this existing metadata deviation explicit; reject every other conflict.
    expected='fashn-vton 1.5.0 requires onnxruntime-gpu, which is not installed.'
    if result.returncode!=1 or not lines or any(line!=expected for line in lines):
        raise RuntimeError('Windows dependency consistency check failed. No setup readiness was granted. '+result.stdout[-2000:])
    print('Dependency check: documented FASHN CPU ONNX substitution; no other metadata conflicts.',flush=True)

def install_commands(python, compute, root,amd_target='all'):
    validate(compute,amd_target);profile=PROFILES[compute]
    suffix='[device-'+amd_target+']' if compute=='rocm' else ''
    commands=[
        [python,'-m','pip','--isolated','--disable-pip-version-check','install','--only-binary=:all:','--require-hashes','--index-url','https://pypi.org/simple','-r',root / ('local_ai/requirements-windows-rocm-bootstrap-hashed.txt' if compute=='rocm' else 'local_ai/requirements-windows-bootstrap-hashed.txt')],
        [python,'-m','pip','--isolated','--disable-pip-version-check','install','--only-binary=:all:','torch'+suffix+'=='+profile['torch'],'torchvision'+suffix+'=='+profile['torchvision'],'--index-url',profile['index']],
        [python,'-m','pip','--isolated','--disable-pip-version-check','install','--only-binary=:all:','--index-url','https://pypi.org/simple','-r',root / 'local_ai/requirements-windows.txt'],
        [python,'-m','pip','--isolated','--disable-pip-version-check','install','--no-deps','--no-build-isolation',root / '.runtime/fashn-src'],
    ]
    if compute=='rocm':
        constraints=['--constraint',root/'local_ai/requirements-windows-rocm-constraints.txt']
        runtime=CONFIG['rocmRuntimeBootstrap']
        commands[1].extend(constraints+['rocm-bootstrap @ '+runtime['url']+'#sha256='+runtime['sha256']])
        commands[2].extend(constraints)
        commands.insert(1,[python,'-m','pip','--isolated','--disable-pip-version-check','install','--no-deps','--no-build-isolation',root/'.runtime/rocm-bootstrap-build'])
    return commands

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--compute',choices=list(PROFILES),required=True)
    parser.add_argument('--amd-target',choices=AMD_TARGETS,default='all');parser.add_argument('--device-index',type=int,default=0)
    args=parser.parse_args();validate_platform(platform.system(),platform.machine(),sys.version_info,struct.calcsize('P')*8)
    validate(args.compute,args.amd_target,args.device_index)
    from local_ai.windows_worker import require_windows
    require_windows(args.compute)
    print('Experimental Windows setup. Downloads several GB; no personal photos are sent.',flush=True)
    runtime=ROOT / '.runtime';runtime.mkdir(exist_ok=True)
    for folder in ['weights/dwpose','hf-cache','mpl-cache']:(runtime / folder).mkdir(parents=True,exist_ok=True)
    folder=runtime_folder(ROOT,args.compute,args.amd_target);python=folder/'Scripts/python.exe';env=environment(ROOT)
    if not python.is_file():run([sys.executable,'-m','venv',folder],env)
    prepare(ROOT)
    if args.compute=='rocm':
        from local_ai.rocm_bootstrap import prepare as prepare_rocm
        print('AMD setup verifies a small source bootstrap before building it locally; other runtime dependencies use binary wheels.',flush=True)
        if args.amd_target=='all':print('AMD all-target testing installs multiple GPU kernel packages and can use substantially more disk space. An exact --amd-target reduces downloads.',flush=True)
        prepare_rocm(ROOT)
        if args.amd_target!='all':env['ROCM_SDK_TARGET_FAMILY']=args.amd_target
    for command in install_commands(python,args.compute,ROOT,args.amd_target):run(command,env)
    dependency_findings(subprocess.run([str(python),'-m','pip','--isolated','check'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60))
    # Fail before downloading model weights if the chosen GPU backend is unavailable.
    probe='import sys,json;sys.path.insert(0,sys.argv[1]);import torch;from local_ai.compute import probe_compute;checks,info=probe_compute(torch,sys.argv[2],int(sys.argv[3]));print("YFR_COMPUTE_REPORT="+json.dumps(info))'
    try:result=subprocess.run([str(python),'-c',probe,str(ROOT),args.compute,str(args.device_index)],cwd=ROOT,env=env,check=True,capture_output=True,text=True,timeout=120)
    except subprocess.CalledProcessError as error:
        raise RuntimeError('The selected compute backend failed before model downloads. Local diagnostic: '+(error.stderr or '')[-2000:]) from error
    lines=[line.removeprefix('YFR_COMPUTE_REPORT=') for line in result.stdout.splitlines() if line.startswith('YFR_COMPUTE_REPORT=')]
    if len(lines)!=1:raise RuntimeError('Compute probe did not return a valid result.')
    info=json.loads(lines[0]);print('Compute/operator check passed:',info.get('gpuName','CPU'),flush=True)
    config={'schemaVersion':1,'compute':args.compute,'amdTarget':args.amd_target,'deviceIndex':args.device_index}
    if args.compute=='rocm':
        target=info.get('gpuArchitecture','').split(':',1)[0]
        if target not in AMD_TARGETS[1:]:raise RuntimeError('The AMD GPU architecture is outside this pinned profile. Choose explicit CPU testing or wait for a reviewed profile.')
        if args.amd_target!='all' and target!=args.amd_target:raise RuntimeError('AMD target does not match the selected GPU.')
        config['runtimeTarget']=target
    run([python,ROOT / 'local_ai/download_models.py'],env)
    run([python,ROOT / 'local_ai/finish_setup.py'],env)
    # Device preference only; never photo data or credentials.
    config_file=runtime/'companion-device.json';pending=config_file.with_suffix('.tmp');pending.write_text(json.dumps(config));os.replace(pending,config_file)
    print('Windows setup complete. Open Start AI.cmd. Do not close its window while processing.',flush=True)

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('\nSetup cancelled. Reopen Set up.cmd to retry.');sys.exit(130)
    except (RuntimeError,ValueError,subprocess.SubprocessError,OSError,tarfile.TarError) as error:
        print(f'\nSetup failed: {error}\nNo readiness was granted. Fix the reported problem and reopen Set up.cmd.',file=sys.stderr);sys.exit(1)
