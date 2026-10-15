"""Read-only known-vulnerability check of installed Python package versions using PyPI metadata.
Does not upload source, photos or credentials and does not detect all malware.
"""
import concurrent.futures,datetime,importlib.metadata,json,urllib.error,urllib.parse,urllib.request
from pathlib import Path

def check(package):
    name,version=package
    if name.lower().replace('_','-')=='fashn-vton':return {'name':name,'version':version,'status':'source-package-uncovered','vulnerabilities':[]}
    url='https://pypi.org/pypi/'+urllib.parse.quote(name,safe='')+'/'+urllib.parse.quote(version,safe='')+'/json'
    try:
        with urllib.request.urlopen(url,timeout=15) as response:data=json.load(response)
        return {'name':name,'version':version,'status':'checked','vulnerabilities':data.get('vulnerabilities',[])}
    except (OSError,ValueError) as error:return {'name':name,'version':version,'status':'unverified','error':type(error).__name__,'vulnerabilities':[]}

if __name__=='__main__':
    packages=sorted({(d.metadata['Name'],d.version) for d in importlib.metadata.distributions()})
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(check,packages))
    summary={'checked':sum(r['status']=='checked' for r in results),'uncovered':sum(r['status']!='checked' for r in results),'withKnownAdvisories':sum(bool(r['vulnerabilities']) for r in results)}
    report={'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'service':'https://pypi.org/pypi/<name>/<version>/json','limitations':'Known advisories only; source package and unavailable registry versions are uncovered. An empty advisory list is not a malware-free certification.','summary':summary,'packages':results}
    Path('.runtime/python-security-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(summary))
    for result in results:
        if result['vulnerabilities']:print(result['name'],result['version'],[v.get('id') for v in result['vulnerabilities']])
