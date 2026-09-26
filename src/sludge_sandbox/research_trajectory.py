"""Line-preserving partitioned storage for large scientific trajectories.

Only one raw part is spooled at a time. Each finished gzip part is read back
against its raw bytes before the temporary spool is removed. No digest is
generated. Record content and ordering are unchanged.
"""
from collections import Counter
import gzip
import json
from pathlib import Path
import tempfile


class PartitionedTrajectoryWriter:
    def __init__(self, manifest, root, policy):
        self.manifest = Path(manifest)
        self.root,self.policy = Path(root),policy
        self.directory = self.manifest.with_suffix('.parts')
        self.directory.mkdir(parents=True)
        self.spool_directory = self.root/policy['spool_directory']
        self.spool_directory.mkdir(parents=True,exist_ok=True)
        self.parts = []
        self.counts = Counter()
        self.current = None
        self.last = None

    def __enter__(self):
        return self

    def _start_part(self):
        name = 'part-'+str(len(self.parts)+1).zfill(self.policy['part_number_width'])+'.jsonl.gz'
        path = self.directory/name
        self.file = path.open('xb')
        self.packed = gzip.GzipFile(filename='',mode='wb',fileobj=self.file,
            compresslevel=self.policy['gzip_compression_level'],mtime=self.policy['gzip_mtime_s'])
        self.raw = tempfile.NamedTemporaryFile(mode='w+b',prefix='trajectory-',suffix='.raw',
                                               dir=self.spool_directory,delete=False)
        self.current = {'path':str(path.relative_to(self.manifest.parent)),'raw_bytes':0,'records':0}

    def _finish_part(self):
        self.packed.close();self.file.close();self.raw.flush();self.raw.seek(0)
        path = self.manifest.parent/self.current['path']
        same = True
        with gzip.open(path,'rb') as restored:
            while True:
                block = restored.read(self.policy['io_block_bytes'])
                if not block:break
                same = same and self.raw.read(len(block))==block
        same = same and self.raw.read(1)==b''
        spool = Path(self.raw.name);self.raw.close()
        self.current.update(archive_bytes=path.stat().st_size,byte_identical_roundtrip=same)
        self.parts.append(self.current);self.current = None
        if not same:
            raise ValueError('Archive bytes differ from the retained raw spool: '+str(spool))
        spool.unlink()

    def write(self,text):
        line = text.encode('utf-8')
        if self.current is not None and self.current['raw_bytes']+len(line)>self.policy['raw_bytes_per_part']:
            self._finish_part()
        if self.current is None:self._start_part()
        self.packed.write(line);self.raw.write(line)
        self.current['raw_bytes']+=len(line);self.current['records']+=1
        self.last = json.loads(text);self.counts[self.last['kind']]+=1
        return len(text)

    def flush(self):
        self.packed.flush();self.file.flush();self.raw.flush()

    def __exit__(self,exception_type,exception,traceback):
        if self.current is not None:self._finish_part()
        result = {'schema':'partitioned_research_jsonl_v1','storage_parameters':self.policy,
            'parts':self.parts,'raw_bytes':sum(p['raw_bytes'] for p in self.parts),
            'archive_bytes':sum(p['archive_bytes'] for p in self.parts),
            'record_counts':dict(self.counts),
            'byte_identical_roundtrip':all(p['byte_identical_roundtrip'] for p in self.parts),
            'last_record_kind':self.last['kind'],
            'terminal_status':self.last['status'] if self.last['kind']=='summary' else 'recorded_prefix_without_summary',
            'writer_exception_type':exception_type.__name__ if exception_type is not None else None,
            'reconstruction':'Decompress and concatenate parts in listed order. Paths are relative to this manifest.',
            'scope':'Storage integrity only, no physical qualification or hash operations.'}
        with self.manifest.open('x') as stream:
            json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
        return False


def trajectory_records(path):
    """Read plain JSONL or an explicitly selected partitioned JSON manifest."""
    path = Path(path)
    if path.suffix=='.jsonl':
        with path.open() as stream:
            for line in stream:yield json.loads(line)
    else:
        manifest = json.loads(path.read_text())
        for part in manifest['parts']:
            with gzip.open(path.parent/part['path'],'rt',encoding='utf-8') as stream:
                for line in stream:yield json.loads(line)
