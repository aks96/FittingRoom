"""App Sandbox worker invocation. Ad-hoc internal build, not a notarized distribution."""
import json,os,platform,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def worker_environment(cache):
    cache=Path(cache)
    return {'PATH':'/usr/bin:/bin','HOME':str(cache),'TMPDIR':str(cache),'TEMP':str(cache),'TMP':str(cache),
            'PYTHONHOME':sys.base_prefix,'PYTHONPATH':os.pathsep.join([str(ROOT/'.runtime/app-sandbox-prototype/code'),str(ROOT/'.runtime/fashn-src/src'),str(Path(sys.prefix)/'lib/python3.12/site-packages')]),'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1',
            'HF_HOME':str(cache/'hf'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','HF_HUB_DISABLE_XET':'1',
            'MPLCONFIGDIR':str(cache/'mpl'),'YOURFITTINGROOM_WORKER':'1',
            'YOURFITTINGROOM_DEVICE':os.environ.get('YOURFITTINGROOM_DEVICE','auto'),
            'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','VECLIB_MAXIMUM_THREADS':'4'}
def command(cache,script=None,code=None):
    if platform.system()!='Darwin':
        raise RuntimeError('OS-isolated inference is not implemented on this platform. Generation is disabled; no unrestricted fallback is used.')
    executable=ROOT/'.runtime/app-sandbox-prototype/InferenceWorker.app/Contents/MacOS/InferenceWorker'
    if not executable.is_file():raise RuntimeError('The local App Sandbox worker is missing. Start the companion through its reviewed launcher.')
    return [str(executable),'-B']+(['-c',code] if code is not None else [str(script)])
