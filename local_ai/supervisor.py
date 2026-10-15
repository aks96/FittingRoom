"""Single supervised OS-restricted worker. No child processes are permitted."""
import os,queue,subprocess,threading,time,uuid
from pathlib import Path
from local_ai.protocol import read_frame,write_frame
from local_ai.isolation import command,worker_environment
from local_ai.sessions import active as session_active
ROOT=Path(__file__).resolve().parents[1]
ANALYSIS_TIMEOUT=300;GENERATION_TIMEOUT=600;MAX_RSS_KB=12*1024*1024
class Busy(Exception):pass
class Stopped(Exception):pass
class WorkerFailure(Exception):pass
class Supervisor:
    def __init__(self):
        self.lock=threading.RLock();self.worker=None;self.messages=None;self.current=None;self.jobs={};self.device='not loaded';self.last_owner=None;self.sandbox_ready=False;self.problem=None;self.runtime=None;self.cache=ROOT/('.runtime/windows-worker/cache' if os.name=='nt' else '.runtime/app-sandbox-prototype/cache')
    def _spawn(self):
        with self.lock:
            if self.worker and self.worker.poll() is None:return self.worker,self.messages
            cache=self.cache;cache.mkdir(parents=True,exist_ok=True)
            if os.name=='nt':
                from local_ai.windows_worker import WindowsRuntime
                try:
                    self.runtime=WindowsRuntime();self.runtime.probe(os.environ.get('YOURFITTINGROOM_DEVICE','cuda'))
                    process=self.runtime.spawn('local_ai.worker',os.environ.get('YOURFITTINGROOM_DEVICE','cuda'))
                except (RuntimeError,OSError) as error:
                    self.sandbox_ready=False
                    if self.runtime:
                        try:self.runtime.close()
                        except RuntimeError as cleanup_error:raise WorkerFailure('Windows validation failed and cleanup is incomplete. Stop the companion before retrying.') from cleanup_error
                        self.runtime=None
                    raise WorkerFailure('Windows isolation or compute validation failed. Generation is disabled; run Test Windows.cmd for a local report.') from error
            else:
                process=subprocess.Popen(command(cache,script=ROOT/'local_ai/worker.py'),env=worker_environment(cache),cwd=cache,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
            messages=queue.Queue(maxsize=64);self.worker=process;self.messages=messages
            def reader():
                try:
                    while True:messages.put(read_frame(process.stdout),timeout=2)
                except (EOFError,ValueError,OSError,RecursionError,queue.Full):
                    try:messages.put({'kind':'closed'},timeout=2)
                    except queue.Full:pass
            def diagnostics():
                # Drain logs without retaining photo data, environment or raw exceptions.
                while process.stderr.read(4096):pass
            threading.Thread(target=reader,daemon=True).start()
            if not getattr(process,'diagnostics_drained',False):threading.Thread(target=diagnostics,daemon=True).start()
            return process,messages
    def warmup(self):
        process,messages=self._spawn()
        try:
            message=messages.get(timeout=90 if os.name=='nt' else 40)
            if message.get('kind')!='ready':raise WorkerFailure('Restricted inference worker could not start.')
            self.device=message['device'];self.sandbox_ready=True;self.problem=None
        except (queue.Empty,WorkerFailure) as error:
            with self.lock:self._stop_locked()
            self.sandbox_ready=False;self.problem='OS-isolated inference worker could not start. No unrestricted fallback is used.'
            raise WorkerFailure(self.problem) from error
    def _stop_locked(self):
        process=self.worker
        if process:
            try:
                if process.poll() is None:process.terminate()
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                try:process.kill();process.wait(timeout=3)
                except (OSError,subprocess.TimeoutExpired) as error:
                    self.sandbox_ready=False;self.problem='Worker termination is not confirmed. Processing is disabled; retry cleanup or stop the companion.'
                    raise WorkerFailure(self.problem) from error
            except ProcessLookupError:pass
            except OSError as error:
                self.sandbox_ready=False;self.problem='Worker termination is not confirmed. Processing is disabled; retry cleanup or stop the companion.'
                raise WorkerFailure(self.problem) from error
            self.worker=None;self.messages=None
            for stream in (process.stdin,process.stdout,process.stderr):
                try:stream.close()
                except OSError:pass
            if hasattr(process,'close'):process.close()
        if self.runtime:
            try:self.runtime.close()
            except RuntimeError as error:
                self.sandbox_ready=False;self.problem='Windows worker cleanup is incomplete. Processing is disabled; stop the companion and retry cleanup.'
                raise WorkerFailure(self.problem) from error
            self.runtime=None
        # Only this application-owned disposable worker cache is removed.
        cache=self.cache
        import shutil
        if cache.is_dir():
            for child in cache.iterdir():
                if child.is_dir() and not child.is_symlink():shutil.rmtree(child)
                else:child.unlink(missing_ok=True)
        self.last_owner=None
    def _reserve(self,owner,operation,payload,job=None):
        with self.lock:
            if not session_active(owner):raise PermissionError('Engine session ended.')
            if self.current:raise Busy('Local processor is busy. Finish or cancel its current operation.')
            if self.last_owner and self.last_owner!=owner:self._stop_locked()
            record={'owner':owner,'operation':operation,'cancelled':False,'started':time.monotonic(),'job':job}
            self.current=record;self.last_owner=owner
            return record
    def _exchange(self,record,message):
        deadline=record['started']+(ANALYSIS_TIMEOUT if record['operation']=='analyze' else GENERATION_TIMEOUT)
        succeeded=False
        try:
            with self.lock:
                if self.current is not record or record['cancelled'] or not session_active(record['owner']):raise Stopped('Session ended or processing cancelled.')
                process,messages=self._spawn()
            write_frame(process.stdin,message);message=None
            while True:
                if record['cancelled'] or not session_active(record['owner']):raise Stopped('Session ended or processing cancelled.')
                if time.monotonic()>deadline:raise WorkerFailure('Local processing reached its safety time limit. Choose clearer or smaller images and retry.')
                # Bound resident process memory, in addition to queue/input/file limits.
                if os.name!='nt':
                    try:
                        rss=subprocess.check_output(['/bin/ps','-o','rss=','-p',str(process.pid)],text=True,timeout=2).strip()
                        if rss and int(rss)>MAX_RSS_KB:raise WorkerFailure('Local processing exceeded the 12 GB resident-memory safety limit.')
                    except (subprocess.SubprocessError,ValueError):pass
                # Windows has kernel-enforced per-process/job committed-memory caps,
                # configured before the first worker instruction. GPU VRAM is separate.
                try:reply=messages.get(timeout=.25)
                except queue.Empty:continue
                kind=reply.get('kind')
                if kind=='ready':self.device=reply['device'];continue
                if kind=='stage':
                    if reply.get('stage') not in ('loading-model','aligning-images','generating'):raise WorkerFailure('Invalid inference worker stage.')
                    job=record.get('job')
                    if job and not job.get('purge'):job['stage']=reply['stage']
                elif kind=='result':
                    if record['operation']=='analyze' and not isinstance(reply.get('analysis'),dict):raise WorkerFailure('Invalid inference analysis response.')
                    if record['operation']=='generate' and (not isinstance(reply.get('image'),str) or not reply['image'].startswith('data:image/png;base64,')):raise WorkerFailure('Invalid inference preview response.')
                    succeeded=True;return reply
                elif kind=='error':raise WorkerFailure(reply.get('error','Local processing failed.'))
                elif kind=='closed':raise WorkerFailure('Restricted inference worker stopped unexpectedly. Retry after checking memory and device availability.')
                else:raise WorkerFailure('Invalid inference worker response.')
        except (EOFError,BrokenPipeError,OSError,ValueError) as error:raise WorkerFailure('Restricted inference worker stopped. Your photos were not replaced.') from error
        finally:
            with self.lock:
                if self.current is record:
                    if record['cancelled'] or not succeeded:self._stop_locked()
                    self.current=None
    def analyze(self,owner,image):
        record=self._reserve(owner,'analyze',None)
        return self._exchange(record,{'operation':'analyze','image':image})['analysis']
    def generate(self,owner,payload):
        job={'id':uuid.uuid4().hex,'owner':owner,'stage':'queued','image':None,'started':time.time(),'engine':'companion','totalSteps':payload.get('steps',30)}
        record=self._reserve(owner,'generate',None,job)
        with self.lock:self.jobs[job['id']]=job
        def work():
            try:
                reply=self._exchange(record,{'operation':'generate','payload':payload})
                with self.lock:
                    if not job.get('purge') and session_active(owner):job['image']=reply['image'];job['stage']='complete'
            except Stopped:job['stage']='cancelled'
            except WorkerFailure as error:job['stage']='failed';job['error']=str(error)
            finally:
                job['finished']=time.time()
                with self.lock:
                    if job.get('purge'):self.jobs.pop(job['id'],None)
        threading.Thread(target=work,daemon=True).start();return job
    def cancel_job(self,key,owner):
        with self.lock:
            job=self.jobs.get(key)
            if job and job['owner']!=owner:raise KeyError('Unknown job.')
            if job:
                job['image']=None;job['purge']=True
                if self.current and self.current.get('job') is job:
                    self.current['cancelled']=True;self._stop_locked();self.current=None
                elif self.last_owner==owner and not self.current:self._stop_locked()
                self.jobs.pop(key,None)
            return {'deleted':True,'processingStopped':True}
    def revoke_owner(self,owner):
        with self.lock:
            cancelled=0;purged=0
            for key,job in list(self.jobs.items()):
                if job['owner']==owner:
                    job['image']=None;job['purge']=True;self.jobs.pop(key,None);purged+=1
            if self.current and self.current['owner']==owner:
                self.current['cancelled']=True;cancelled=1;self._stop_locked();self.current=None
            elif self.last_owner==owner and not self.current:self._stop_locked()
            return {'cancelled':cancelled,'purged':purged}
    def expire_results(self):
        with self.lock:
            for key,job in list(self.jobs.items()):
                if job.get('finished',time.time())<time.time()-1800:self.cancel_job(key,job['owner'])
    def shutdown(self):
        with self.lock:
            if self.current:self.current['cancelled']=True
            self._stop_locked();self.current=None;self.jobs.clear()
