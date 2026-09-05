"""Runtime evidence loaders cannot accept schema examples or stale identities."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from model import ROOT


class BindingTests(unittest.TestCase):
    def test_schema_example_rejected_and_missing_not_passed(self):
        self.assertIsNotNone(importlib.util.find_spec('binding'),'binding absent')
        from binding import load_evidence, capture_identity, verify_identity
        self.assertEqual(load_evidence(None)['binding_status'],'missing')
        with self.assertRaises(ValueError): load_evidence('B2_VALIDATION_STATUS_FIXTURES.json')
        with self.assertRaises(ValueError): load_evidence('../verification.json')
        # Content checks happen even when a claimed source_commit is unchanged.
        identity=capture_identity(require_commit=False)
        self.assertTrue(verify_identity(identity,require_commit=False))
        identity['source_files'][0]['sha256']='0'*64
        self.assertFalse(verify_identity(identity,require_commit=False))

if __name__=='__main__': unittest.main()
