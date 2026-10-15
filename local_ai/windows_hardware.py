"""Read only display-adapter names/vendor/driver; never serials or user files."""
import json
import os
import subprocess
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def parse_adapters(value):
    records=json.loads(value)
    if isinstance(records,dict):records=[records]
    if not isinstance(records,list) or len(records)>32:raise ValueError('Invalid adapter inventory.')
    result=[]
    for item in records:
        if not isinstance(item,dict):raise ValueError('Invalid display adapter.')
        def clean(name):return ''.join(c for c in str(item.get(name) or '') if c.isprintable())[:160]
        vendor={'10DE':'NVIDIA','1002':'AMD','8086':'Intel'}.get(clean('VendorId').upper(),'Unknown')
        result.append({'name':clean('Name'),'vendor':vendor,'driverVersion':clean('DriverVersion')})
    return result

def inventory():
    if os.name!='nt':raise RuntimeError('Display-adapter inventory runs only on Windows.')
    from local_ai.windows_native import api,C
    buffer=C.create_unicode_buffer(32768);size=api().GetWindowsDirectoryW(buffer,len(buffer))
    if not 0<size<len(buffer):raise RuntimeError('Windows system directory unavailable.')
    executable=Path(buffer.value)/'System32/WindowsPowerShell/v1.0/powershell.exe'
    # This constant query never interpolates user input or changes device settings.
    script="@(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,@{Name='VendorId';Expression={if ($_.PNPDeviceID -match 'VEN_([0-9A-Fa-f]{4})') {$Matches[1]} else {''}}}) | ConvertTo-Json -Compress"
    result=subprocess.run([str(executable),'-NoProfile','-NonInteractive','-Command',script],capture_output=True,text=True,timeout=20,check=True)
    if len(result.stdout)>65536:raise RuntimeError('Adapter inventory exceeds its size limit.')
    return parse_adapters(result.stdout)

if __name__=='__main__':
    try:
        print('Detected display adapters (CPU brand does not identify the GPU):')
        for adapter in inventory():print(f"  {adapter['vendor']}: {adapter['name']} | driver {adapter['driverVersion']}")
        print('Choose the GPU backend below. Detection alone does not prove model compatibility.')
    except (RuntimeError,ValueError,OSError,subprocess.SubprocessError):
        print('Display adapter details unavailable. Check Task Manager > Performance > GPU, or explicitly choose slow CPU testing.')
