"""Unit fixture location; only a dedicated, module-relative harness variable."""
import os
from paths import checked_path


def fixture_root():
    p=checked_path(os.environ.get('B2_TEST_OUT','validation'))
    p.mkdir(parents=True,exist_ok=True)
    return p
