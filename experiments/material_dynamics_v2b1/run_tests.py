#!/usr/bin/env python3
"""Run ONLY this experiment's focused suite and persist real test output."""
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed_names = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_names.append(test.id())


def main():
    out = HERE/"validation"
    out.mkdir(exist_ok=True)
    start = time.monotonic()
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py")
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedResult).run(suite)
    assert isinstance(result, RecordedResult)
    log = stream.getvalue()
    (out/"focused_tests.log").write_text(log, encoding="utf-8")
    record = dict(status="passed" if result.wasSuccessful() else "failed", tests_run=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                  successful_tests=result.passed_names, wall_seconds=time.monotonic()-start,
                  command="python3 experiments/material_dynamics_v2b1/run_tests.py",
                  runner="stdlib_unittest", python_version=sys.version.split()[0],
                  created_at_utc=datetime.now(timezone.utc).isoformat(), legacy_suite_run=False)
    (out/"test_results.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    print(log, end="")
    print(json.dumps(record,indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
