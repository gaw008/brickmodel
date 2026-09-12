"""Read-only freeze and syntax verification; no application imports or EOS."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def main() -> None:
    root = Path(__file__).resolve().parents[6]
    source = root / 'src/sludge_sandbox'
    freeze_path = Path('/private/tmp/brick-source-resume-v1/root/SOURCE_FREEZE.json')
    freeze = json.loads(freeze_path.read_bytes())
    checked = {}
    for name, expected in freeze['source_files'].items():
        raw = (source / name).read_bytes()
        actual = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        assert actual == expected, name
        ast.parse(raw, filename=name)
        checked[name] = actual
    assert set(checked) == {path.name for path in source.glob('*.py')}
    for name, digest in freeze['execution_sources'].items():
        assert checked[name]['sha256'] == digest, name
    manifest_path, manifest_bytes, manifest_digest = freeze['manifest_asset']
    raw = (root / manifest_path).read_bytes()
    assert len(raw) == manifest_bytes
    assert hashlib.sha256(raw).hexdigest() == manifest_digest
    assert json.loads(raw)['execution_sources'] == freeze['execution_sources']
    suite = ET.parse(Path(__file__).with_name('probes.xml')).getroot().find('testsuite')
    assert suite is not None and suite.attrib['tests'] == '7'
    assert suite.attrib['errors'] == suite.attrib['failures'] == suite.attrib['skipped'] == '0'
    result = {
        'status': 'passed',
        'scope': 'frozen source bytes, AST syntax, runtime manifest and seven existing pure probes',
        'source_file_count': len(checked),
        'execution_sources': freeze['execution_sources'],
        'source_freeze_sha256': hashlib.sha256(freeze_path.read_bytes()).hexdigest(),
        'manifest_sha256': manifest_digest,
        'pure_probes': dict(suite.attrib),
        'static_analyzer_availability': {
            name: importlib.util.find_spec(name) is not None
            for name in ('ruff', 'mypy', 'pylint', 'black', 'bandit')
        },
        'native_or_eos_calls': 0,
        'application_imports_by_this_script': 0,
    }
    Path(__file__).with_name('STATIC_CHECK.json').write_text(
        json.dumps(result, indent=2, sort_keys=True) + '\n'
    )


if __name__ == '__main__':
    main()
