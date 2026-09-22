"""Archive explicitly selected research trajectories with byte round-trip review.

No digest is generated. The manifest records JSONL structure and actual terminal
status, so stopped or incomplete prefixes remain distinct from completed runs.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import shutil


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    settings=json.loads(args.parameters.read_text());root=args.parameters.resolve().parent
    entries=[]
    for item in settings['records']:
        source,target=root/item['source'],root/item['archive']
        target.parent.mkdir(parents=True,exist_ok=True)
        with source.open('rb') as raw,target.open('xb') as output:
            with gzip.GzipFile(filename='',mode='wb',fileobj=output,
                compresslevel=settings['gzip_compression_level'],mtime=settings['gzip_mtime_s']) as packed:
                shutil.copyfileobj(raw,packed,length=settings['io_block_bytes'])
        same=True
        with source.open('rb') as raw,gzip.open(target,'rb') as unpacked:
            while True:
                a,b=raw.read(settings['io_block_bytes']),unpacked.read(settings['io_block_bytes'])
                same=same and a==b
                if not a and not b:
                    break
        counts=Counter();last=None
        with gzip.open(target,'rt') as stream:
            for line in stream:
                last=json.loads(line);counts[last['kind']]+=1
        entries.append({**item,'raw_bytes':source.stat().st_size,'archive_bytes':target.stat().st_size,
            'byte_identical_roundtrip':same,'record_counts':dict(counts),'last_record_kind':last['kind'],
            'terminal_status':last['status'] if last['kind']=='summary' else 'recorded_prefix_without_summary',
            'last_time_s':last.get('time_s')})
    with args.output.open('x') as stream:
        json.dump({'settings':settings,'records':entries,
            'scope':'Lossless storage review only; no physical accuracy, source authorship, code identity or checksum claim.'},
            stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'archives':len(entries),'compressed_bytes':sum(p['archive_bytes'] for p in entries),
                      'all_roundtrips_equal':all(p['byte_identical_roundtrip'] for p in entries)}))


if __name__=='__main__':
    main()
