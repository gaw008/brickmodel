"""Platform units must not turn a small macOS process into a 512 MiB failure."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from resources import Budget


class ResourceUnitTests(unittest.TestCase):
    def test_linux_and_macos_rss_use_same_mib_limit(self):
        for platform, raw_per_mib in (('linux', 1024), ('darwin', 1024 * 1024)):
            with self.subTest(platform=platform):
                with patch('resources.sys.platform', platform), patch(
                    'resources.resource.getrusage',
                    return_value=SimpleNamespace(ru_maxrss=76 * raw_per_mib),
                ):
                    budget = Budget(30, 30, 'rss_units')
                    budget.check()
                    self.assertEqual(budget.snapshot('tested')['peak_rss_mib'], 76)
                with patch('resources.sys.platform', platform), patch(
                    'resources.resource.getrusage',
                    return_value=SimpleNamespace(ru_maxrss=513 * raw_per_mib),
                ):
                    with self.assertRaisesRegex(RuntimeError, 'rss_resource_limit'):
                        Budget(30, 30, 'rss_units').check()


if __name__ == '__main__':
    unittest.main()
