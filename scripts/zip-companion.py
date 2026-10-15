"""Create a Windows-friendly ZIP from the explicitly allowlisted package staging folder."""
import sys,zipfile
from pathlib import Path
stage=Path(sys.argv[1]);output=Path(sys.argv[2])
with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
    for file in sorted(stage.rglob('*')):
        if file.is_file():archive.write(file,arcname=str(Path(stage.name)/file.relative_to(stage)))
