"""Lossless line-aligned gzip parts for large scientific trajectories.

Parts concatenate to the original byte stream in manifest order. The manifest
reports real terminal status; incomplete prefixes are not called completed.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path


def archive(root,item,settings):
    source=root/item['source'];directory=root/item['archive_directory']
    directory.mkdir(parents=True,exist_ok=True)
    parts=[];counts=Counter();last=None;stream=packed=None;part=None
    def close_part():
        packed.close();stream.close()
        part['archive_bytes']=(root/part['path']).stat().st_size
        parts.append(part)
    with source.open('rb') as raw:
        for line in raw:
            if part is None or part['raw_bytes']+len(line)>settings['raw_bytes_per_part']:
                if part is not None:
                    close_part()
                path=directory/('part-'+str(len(parts)+1).zfill(settings['part_number_width'])+'.jsonl.gz')
                stream=path.open('xb');packed=gzip.GzipFile(filename='',mode='wb',fileobj=stream,
                    compresslevel=settings['gzip_compression_level'],mtime=settings['gzip_mtime_s'])
                part={'path':str(path.relative_to(root)),'raw_bytes':0,'records':0}
            packed.write(line);part['raw_bytes']+=len(line);part['records']+=1
            last=json.loads(line);counts[last['kind']]+=1
    close_part()
    same=True
    with source.open('rb') as raw:
        for part in parts:
            with gzip.open(root/part['path'],'rb') as unpacked:
                while True:
                    block=unpacked.read(settings['io_block_bytes'])
                    if not block:
                        break
                    same=same and raw.read(len(block))==block
        same=same and raw.read(1)==b''
    return {**item,'parts':parts,'raw_bytes':source.stat().st_size,
        'archive_bytes':sum(p['archive_bytes'] for p in parts),'byte_identical_roundtrip':same,
        'record_counts':dict(counts),'last_record_kind':last['kind'],
        'terminal_status':last['status'] if last['kind']=='summary' else 'recorded_prefix_without_summary',
        'last_time_s':last.get('time_s')}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.parameters.resolve().parent
    settings=json.loads(args.parameters.read_text());records=[]
    for item in settings['records']:
        record=archive(root,item,settings);records.append(record)
        print(json.dumps({'source':item['source'],'parts':len(record['parts']),
            'archive_bytes':record['archive_bytes'],'byte_identical_roundtrip':record['byte_identical_roundtrip'],
            'terminal_status':record['terminal_status']}),flush=True)
    with args.output.open('x') as stream:
        json.dump({'settings':settings,'records':records,
            'reconstruction':'For each record, decompress and concatenate parts in the listed order; no repeated header or inserted byte.',
            'scope':'Lossless storage only; no digest, authenticity or physical qualification.'},stream,indent=2,allow_nan=False)
        stream.write('\n')


if __name__=='__main__':
    main()
