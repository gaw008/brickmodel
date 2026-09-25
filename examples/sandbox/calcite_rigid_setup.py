"""Load recorded source-only thermochemistry and explicit constant solid volumes."""
import json

from calcite_closed_setup import build_closed


def build_rigid(root,config):
    records=build_closed(root,config)
    volume=json.loads((root/config['volume_source_file']).read_text())
    return (*records,volume)
