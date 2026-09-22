"""Read an explicit stopped sorptive-column checkpoint and its retained prefix."""
import json


def read_checkpoint(path):
    lines=path.read_text().splitlines(keepends=True)
    header=json.loads(lines[0]);checkpoint=json.loads(lines[-2]);summary=json.loads(lines[-1])
    if checkpoint['kind']!='checkpoint' or summary['kind']!='summary' or summary['status']!='stopped_at_checkpoint':
        raise ValueError('resume requires a trajectory explicitly stopped at a checkpoint')
    return header,checkpoint,lines[:-2]
