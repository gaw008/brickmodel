"""Offline reproducibility package; exact tests consumed by the selected demo."""
import argparse
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import sys
from model import ROOT, canonical
from paths import checked_path, safe_directory, relative
from binding import capture_identity, verify_identity, reference, load_evidence, digest
from exports import write_json


def validate_members(members):
    seen=set(); total=0
    for member in members:
        p=PurePosixPath(member.name)
        if p.is_absolute() or '..' in p.parts or not member.isfile() or member.name in seen or '\\' in member.name: raise ValueError('archive_member_rejected')
        seen.add(member.name); total+=member.size
        if total>256*1024*1024: raise ValueError('archive_uncompressed_limit')


def collect(run,tests):
    run=safe_directory(run); tests=safe_directory(tests)
    manifest=json.loads((run/'manifest.json').read_text()); expected=reference(tests/'verification.json')
    if manifest['focused_evidence']!=expected: raise ValueError('tests_not_consumed_by_run')
    binding=load_evidence(expected['path'])
    if binding['binding_status']!='bound' or manifest['binding_status']!='bound' or not verify_identity(manifest): raise ValueError('repro_identity')
    for ref in manifest['expanded_inputs']+manifest['raw_result_files']+[manifest['current_audit']]:
        if digest(checked_path(ref['path']))!=ref['sha256']: raise ValueError('run_bytes_changed')
    identity=capture_identity(); paths={ROOT/r['path'] for r in identity['source_files']+identity['contract_artifacts']}
    omitted=[]
    for directory in (run,tests):
        for p in directory.rglob('*'):
            if p.is_symlink(): omitted.append(relative(p)); continue
            if p.is_file() and not any(x.is_symlink() for x in p.parents if x!=ROOT): paths.add(p)
    for name in ('reproduction_result.json','reproduction_commands.json','acceptance_evidence.json','ENGINEER_HANDOFF.md','command_ledger.json','preflight.json'):
        p=ROOT/'validation'/name
        if p.is_file() and not p.is_symlink(): paths.add(p)
    return sorted(paths),identity,omitted


def main():
    p=argparse.ArgumentParser(); p.add_argument('--run',required=True); p.add_argument('--tests',required=True); p.add_argument('--out',required=True); a=p.parse_args()
    try:
        target=checked_path(a.out)
        if target.exists(): raise ValueError('archive_output_exists')
        paths,identity,omitted=collect(a.run,a.tests)
        target.parent.mkdir(parents=True,exist_ok=True)
        snapshot=canonical({'kind':'offline_source_snapshot','identity':identity,'scope':'byte_identity_not_a_signature_or_new_Safety_approval'})
        with tarfile.open(target,'w:gz') as tar:
            for src in paths:
                info=tar.gettarinfo(str(src),arcname=relative(src)); info.uid=info.gid=0; info.uname=info.gname=''; info.mtime=0
                if not info.isfile(): raise ValueError('archive_member_type')
                with src.open('rb') as stream: tar.addfile(info,stream)
            info=tarfile.TarInfo('SOURCE_SNAPSHOT.json'); info.size=len(snapshot); info.mode=0o644; tar.addfile(info,io.BytesIO(snapshot))
        if target.stat().st_size>20*1024*1024: raise RuntimeError('archive_resource_limit')
        with tarfile.open(target,'r:gz') as tar:
            members=tar.getmembers(); validate_members(members)
            inventory=[{'path':m.name,'bytes':m.size} for m in members]
        result={'archive':reference(target),'bytes':target.stat().st_size,'member_count':len(inventory),'members':inventory,
                'omitted_test_fixture_symlinks':omitted,'reason':'Hostile links were runtime path tests, never executable archive members',
                'source_commit':identity['source_commit'],'bound_tests':reference(checked_path(a.tests)/'verification.json')}
        write_json(target.with_suffix(target.suffix+'.manifest.json'),result)
        print(json.dumps({k:v for k,v in result.items() if k!='members'},allow_nan=False)); return 0
    except (ValueError,OSError,RuntimeError):
        print(json.dumps({'passed':False,'reason':'reproduction_package_rejected'})); return 1


if __name__=='__main__': sys.exit(main())
