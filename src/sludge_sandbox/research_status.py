"""Read declared research evidence without running or qualifying a model.

Required result paths must exist. Explicitly pending results remain pending
until their result file is present; this says nothing about a live process.
"""
from datetime import datetime, timezone
import json
from pathlib import Path


def read_research_status(parameters_path):
    parameters_path = Path(parameters_path).resolve()
    root = parameters_path.parent
    settings = json.loads(parameters_path.read_text())
    cases = []
    loaded = {}
    for case in settings['cases']:
        results = []
        for check in case['checks']:
            path = root / check['result_file']
            if check['availability'] == 'pending' and not path.exists():
                results.append({**check, 'result_state': 'awaiting_result_file', 'recorded_values': None})
                continue
            if path not in loaded:
                loaded[path] = json.loads(path.read_text())
            payload = loaded[path]
            values = []
            for selector in check['selectors']:
                value = payload
                for key in selector['path']:
                    value = value[key]
                values.append({'label': selector['label'], 'path': selector['path'], 'value': value})
            results.append({**check, 'result_state': 'result_file_read', 'recorded_values': values})
        cases.append({**case, 'checks': results})
    return {'snapshot_utc': datetime.now(timezone.utc).isoformat(),
        'parameters_file': str(parameters_path), 'scope': settings['scope'],
        'cases': cases, 'material_dependencies': settings['material_dependencies'],
        'interpretation': settings['interpretation']}
