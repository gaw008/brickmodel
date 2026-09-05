"""Run exactly one B1 sentinel in this isolated byte-identical source copy."""
import dataclasses
import json
from pathlib import Path
import sys
import time
from model import Config
from solver import simulate

if __name__=='__main__':
    input_path,out_path,budget_seconds=sys.argv[1:]
    cfg=Config.from_json(Path(input_path).read_text())
    started=time.monotonic()
    result=simulate(cfg,deadline=started+float(budget_seconds))
    payload={'input':cfg.to_dict(),'steps':result.steps,'records':[
        {'tau':r.tau,'state':dataclasses.asdict(r.state)} for r in result.records],
        'elapsed_wall_seconds':time.monotonic()-started}
    Path(out_path).write_text(json.dumps(payload,allow_nan=False,separators=(',',':'))+'\n')
