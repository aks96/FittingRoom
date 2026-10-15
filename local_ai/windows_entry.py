"""Choose only the configured, app-owned Python runtime for Windows diagnostics."""
import os
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from local_ai.windows_profiles import read_config,runtime_python,device_environment

def main():
    from local_ai.windows_worker import require_windows
    require_windows()
    if sys.argv[1:]!=['test']:raise ValueError('Only the fixed Windows validation action is supported.')
    config=read_config(ROOT);python=runtime_python(ROOT,config)
    require_windows(config['compute'])
    print('Testing configured backend:',config['compute'],flush=True)
    return subprocess.call([str(python),str(ROOT/'local_ai/windows_validate.py'),'--compute',config['compute']],
                           cwd=ROOT,env={**os.environ,**device_environment(config)})

if __name__=='__main__':
    try:sys.exit(main())
    except (RuntimeError,ValueError,OSError) as error:print('Windows test could not start:',error,file=sys.stderr);sys.exit(1)
