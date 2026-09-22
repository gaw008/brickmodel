"""Read an explicit stopped sorptive-column checkpoint and its retained prefix."""
import json
from collections import deque


def read_checkpoint(path):
    with path.open() as stream:
        header=json.loads(next(stream));tail=deque(stream,maxlen=2)
    checkpoint,summary=map(json.loads,tail)
    if checkpoint['kind']!='checkpoint' or summary['kind']!='summary' or summary['status']!='stopped_at_checkpoint':
        raise ValueError('resume requires a trajectory explicitly stopped at a checkpoint')
    def prefix_lines():
        with path.open() as stream:
            pending=deque()
            for line in stream:
                pending.append(line)
                if len(pending)>2:
                    yield pending.popleft()
    return header,checkpoint,prefix_lines()
