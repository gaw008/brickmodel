"""Archive member policy is tested without claiming a numerical replay."""
import importlib.util
import io
import tarfile
import unittest

class ArchiveTests(unittest.TestCase):
    def test_member_policy(self):
        self.assertIsNotNone(importlib.util.find_spec('build_repro'),'archive implementation absent')
        from build_repro import validate_members
        a=tarfile.TarInfo('model.py'); a.size=12
        validate_members([a])
        for name,kind in [('/escape',tarfile.REGTYPE),('../escape',tarfile.REGTYPE),('link',tarfile.SYMTYPE),('device',tarfile.CHRTYPE)]:
            x=tarfile.TarInfo(name); x.type=kind
            with self.assertRaises(ValueError): validate_members([x])
        with self.assertRaises(ValueError): validate_members([a,a])

if __name__=='__main__': unittest.main()
