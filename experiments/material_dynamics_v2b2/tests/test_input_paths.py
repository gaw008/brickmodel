"""Real filesystem containment and no-overwrite checks."""
import importlib.util
from pathlib import Path
import unittest
from model import ROOT
from test_support import fixture_root


class PathTests(unittest.TestCase):
    def test_local_regular_paths_and_existing_output(self):
        self.assertIsNotNone(importlib.util.find_spec('paths'), 'safe paths implementation absent')
        from paths import safe_file, new_directory
        import tempfile
        # Keep fixtures persistent and inside the authorized module, no cleanup deletion.
        base=Path(tempfile.mkdtemp(prefix='paths-',dir=fixture_root()))
        p=base/'data.json'; p.write_text('{}\n'); rel=str(p.relative_to(ROOT))
        self.assertEqual(safe_file(rel),p)
        for invalid in ('../escape',str(p),'https://invalid.invalid/x',str(base.relative_to(ROOT))):
            with self.assertRaises(ValueError): safe_file(invalid)
        link=base/'link'; link.symlink_to(p)
        with self.assertRaises(ValueError): safe_file(str(link.relative_to(ROOT)))
        parent=base/'linked_parent'; parent.symlink_to(base,target_is_directory=True)
        with self.assertRaises(ValueError): new_directory(str((parent/'out').relative_to(ROOT)))
        output=new_directory(str((base/'out').relative_to(ROOT)))
        sentinel=output/'sentinel'; sentinel.write_bytes(b'unchanged')
        with self.assertRaises(ValueError): new_directory(str(output.relative_to(ROOT)))
        self.assertEqual(sentinel.read_bytes(),b'unchanged')

if __name__=='__main__': unittest.main()
