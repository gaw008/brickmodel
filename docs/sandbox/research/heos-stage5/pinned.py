import runpy
from pathlib import Path
p=Path('/private/tmp/brick-heos-stage5')
for name in ('smoke-pinned.py','inverse-pinned.py'):runpy.run_path(str(p/name),run_name='__main__')
