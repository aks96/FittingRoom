"""Windows loopback launcher. Never changes firewall rules or requests elevation."""
import argparse
import os
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--experimental-worker',action='store_true')
    args=parser.parse_args()
    if not args.experimental_worker:
        raise RuntimeError('The Windows worker is an unvalidated internal candidate. Run Test Windows.cmd first, then explicitly choose experimental testing in Start AI.cmd. No AI process was started.')
    from local_ai.windows_worker import require_windows
    require_windows()
    from local_ai.windows_profiles import read_config,runtime_python,device_environment
    config=read_config(ROOT);python=runtime_python(ROOT,config)
    require_windows(config['compute'])
    env={**os.environ,**device_environment(config),'HF_HOME':str(ROOT / '.runtime/hf-cache'),
         'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1',
         'MPLCONFIGDIR':str(ROOT / '.runtime/mpl-cache'),'PYTHONPATH':str(ROOT / '.runtime/fashn-src/src')}
    print('Verifying model integrity. No downloads. Keep this window open; Ctrl+C stops processing.',flush=True)
    from local_ai.source_integrity import prepare
    prepare(ROOT,download=False)
    if config['compute']=='rocm':
        from local_ai.rocm_bootstrap import prepare as verify_rocm
        verify_rocm(ROOT,download=False)
    from local_ai.download_models import verify
    verify()
    print('Internal Windows test candidate. Each worker launch checks OS isolation and compute before accepting images.',flush=True)
    return subprocess.call([str(python),'-m','uvicorn','local_ai.server:app','--host','127.0.0.1','--port','8765','--no-access-log'],cwd=ROOT,env=env)

if __name__=='__main__':
    try:sys.exit(main())
    except KeyboardInterrupt:sys.exit(130)
    except (OSError,RuntimeError,ValueError) as error:print(f'Start failed: {error}',file=sys.stderr);sys.exit(1)
