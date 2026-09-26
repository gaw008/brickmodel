"""Bundle completed local gzip records for separate GitHub research attachments.

This operation prepares local artifacts only. Network publication and readback
are recorded separately. No checksums or scientific qualification are inferred.
"""
import argparse
import json
from pathlib import Path
import tarfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text())
    root = args.parameters.resolve().parent
    manifest = json.loads((root / p['archive_manifest']).read_text())
    directory = root / p['bundle_directory']
    directory.mkdir(parents=True, exist_ok=True)
    groups = []
    current = []
    total = 0
    for record in manifest['records']:
        for part in record['parts']:
            if current and total + part['archive_bytes'] > p['maximum_compressed_payload_bytes_per_bundle']:
                groups.append(current)
                current = []
                total = 0
            current.append(part)
            total += part['archive_bytes']
    if current:
        groups.append(current)
    bundles = []
    for index, parts in enumerate(groups, start=1):
        path = directory / f"{p['bundle_basename']}-{index:03d}.tar"
        with tarfile.open(path, 'x', format=tarfile.PAX_FORMAT) as archive:
            for part in parts:
                archive.add(root / part['path'], arcname=part['path'], recursive=False)
        equal = True
        with tarfile.open(path, 'r') as archive:
            for part in parts:
                with archive.extractfile(part['path']) as archived, (root / part['path']).open('rb') as original:
                    while True:
                        block = archived.read(p['io_block_bytes'])
                        if not block:
                            break
                        equal = (original.read(len(block)) == block) and equal
                    equal = (original.read(1) == b'') and equal
        row = {'path': str(path.relative_to(root)), 'name': path.name, 'bytes': path.stat().st_size,
               'members': [part['path'] for part in parts], 'byte_identical_members': equal}
        bundles.append(row)
        print(json.dumps({key: row[key] for key in ['name', 'bytes', 'byte_identical_members']}), flush=True)
    with args.output.open('x') as stream:
        json.dump({'settings': p, 'bundles': bundles, 'remote_publication_completed': False,
                   'reconstruction': 'Unpack each tar at the repository root to restore the manifest-relative gzip part paths; then concatenate decompressed parts in manifest order.',
                   'material_qualified': False, 'training_eligible': False}, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
