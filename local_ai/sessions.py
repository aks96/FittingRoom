"""In-memory session lifecycle. Authorization ends before cleanup; failed cleanup remains retryable."""
import threading,time
lock=threading.RLock();sessions={};revocations={}
_cleanup=lambda token: {'cancelled':0,'purged':0}
def register_cleanup(callback):
    global _cleanup
    _cleanup=callback
def active(token):
    with lock:
        session=sessions.get(token)
        return bool(session and session['expires']>time.time())
def may_revoke(token):
    with lock:return token in sessions or token in revocations
def pending(token):
    with lock:return token in revocations and not revocations[token]['complete']
def revoke(token):
    with lock:
        existed=sessions.pop(token,None) is not None
        record=revocations.setdefault(token,{'complete':False,'expires':time.time()+900,'result':None})
        if record['complete']:return record['result']
    result={'revoked':True,'existed':existed,**_cleanup(token)}
    with lock:record['complete']=True;record['result']=result
    return result
def expire():
    with lock:
        tokens=[token for token,session in sessions.items() if session['expires']<=time.time()]
        tokens += [token for token,record in revocations.items() if not record['complete']]
        for token,record in list(revocations.items()):
            if record['complete'] and record['expires']<time.time():revocations.pop(token,None)
    failures=0
    for token in set(tokens):
        try:revoke(token)
        except Exception:failures+=1 # Keep revoked authorization and retry cleanup next sweep.
    return failures
