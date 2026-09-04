"""Run the complete offline pipeline and focused tests, preserving real exit codes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def run_command(command, *, cwd):
    start = time.perf_counter()
    result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=180, check=False)
    return {'argv':command,'command':shlex.join(command),'cwd':str(cwd),
            'exit_code':result.returncode,'elapsed_seconds':time.perf_counter()-start,'output':result.stdout}


def main():
    output = HERE/'artifacts'
    output.mkdir(exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    commands = [[sys.executable,str(HERE/'pipeline.py')],
                [sys.executable,'-m','unittest','discover','-s',str(HERE),'-p','test_pipeline.py','-v'],
                [sys.executable,'-m','compileall','-q',str(HERE/'pipeline.py'),str(HERE/'reporting.py'),str(HERE/'test_pipeline.py'),str(HERE/'verify.py')],
                ['git','diff','--check']]
    citation_tool=Path('/home/ubuntu/.hermes/profiles/engineer/skills/research/grounded-citations/scripts/sources.py')
    if citation_tool.is_file():
        for name in ['DATA_AUDIT.md','DIRECTION_REPORT.md','MODEL_GAP_PRIORITY.md']:
            commands.append([sys.executable,str(citation_tool),'--ledger',str(HERE/'citations.json'),
                'verify',str(output/name),'--evidence'])
    results = []
    for command in commands:
        result = run_command(command,cwd=ROOT)
        results.append(result)
        print(result['command'], 'exit=',result['exit_code'], 'seconds=',round(result['elapsed_seconds'],3))
        if result['exit_code']:
            (output/'verification.json').write_text(json.dumps({'status':'failed','commands':results},ensure_ascii=False,indent=2)+'\n')
            print(result['output'])
            return result['exit_code']
    pipeline = json.loads((output/'pipeline_run.json').read_text())
    match = re.search(r'Ran (\d+) tests',results[1]['output'])
    if match is None:
        raise ValueError('could not confirm test count')
    digest = {str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(output.iterdir()) if p.is_file() and p.name!='verification.json'}
    report = {'status':'passed_implementation_checks_pending_independent_review','started_utc':started,
        'ended_utc':datetime.now(timezone.utc).isoformat(),'commands':results,'tests_run':int(match[1]),
        'test_results':'all focused tests passed; no old project full suite run',
        'citation_checks':'executed in commands' if citation_tool.is_file() else 'optional citation verifier unavailable; not rerun',
        'counts':pipeline['counts'],'pipeline_elapsed_seconds':pipeline['elapsed_seconds'],
        'pipeline_peak_rss_KiB':pipeline['peak_rss_KiB'],'input_sha256_before':pipeline['input_sha256_before'],
        'input_sha256_after':pipeline['input_sha256_after'],'input_hashes_unchanged':pipeline['input_hashes_unchanged'],
        'source_MD5_SHA256':pipeline['raw_file_checks'],'output_sha256':digest,
        'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'pipeline.py',HERE/'reporting.py',HERE/'test_pipeline.py',HERE/'verify.py']},
        'verified':['all four workbooks and all 19 sheets','source/cache recomputation','dry basis and units',
            'sample identity and exact mass joins','source-imputed heights excluded from dependent group statistics',
            'no duplicate specimen/mean counting','chart membership and counts',
            'two offline runs in end-to-end test give identical observation CSV','15 authorized inputs unchanged'],
        'not_verified':['full original DTU paper inaccessible','laboratory chain-of-custody','A2P identity',
            'firing atmosphere/heating/hold','independent experimental validation','real strength or factory applicability',
            'pixel-level rendering of SVG on a CJK-capable viewer'],
        'known_failed_setup':['python3 -m venv failed: ensurepip unavailable; no dependency needed after stdlib fallback',
            'DTU open PDF HTTP403; web_extract failed; Wayback429; full text not claimed'],
        'reproducibility':'Standard library only; Python 3.12; serial; no network during run; fixed public inputs',
        'rollback_notes':'Remove or revert only experiments/material_design_v2 changes after review; original inputs/core solver untouched; no push/merge/deployment',
        'residual_risk':'Research interpretation under declared within-study labels; not production approval; independent Safety review pending'}
    (output/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':report['status'],'tests_run':report['tests_run'],'counts':report['counts']},ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
