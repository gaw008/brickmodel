"""Compare the installed package and final repository file bytes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

root, output, xml = map(Path, sys.argv[1:4])
expected_count = int(sys.argv[4])
source = root/'src/sludge_sandbox'
installed = Path(next(iter(importlib.util.find_spec('sludge_sandbox').submodule_search_locations)))
assert installed != source and 'site-packages' in str(installed)
records = []
for path in sorted(source.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts:
        continue
    target = installed/path.relative_to(source)
    assert target.is_file(), target
    expected, actual = path.read_bytes(), target.read_bytes()
    assert expected == actual, path
    records.append({'path': str(path.relative_to(source)),
                    'sha256': hashlib.sha256(expected).hexdigest()})
suites = ET.parse(xml).getroot().findall('testsuite')
counts = {key: sum(int(s.attrib[key]) for s in suites)
          for key in ('tests', 'failures', 'errors', 'skipped')}
assert counts['tests'] == expected_count and all(counts[key] == 0 for key in ('failures', 'errors', 'skipped'))
result = {'status': 'matched', 'installed': str(installed), 'source': str(source),
          'module_count': sum(x['path'].endswith('.py') for x in records),
          'package_file_count': len(records), 'test_counts': counts, 'files': records}
output.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({key: value for key, value in result.items() if key != 'files'}))
