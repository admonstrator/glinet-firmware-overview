"""Render the fixture site offline and check it end to end."""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import build_offline  # noqa: E402
import check_site  # noqa: E402

# Every HTML page is rendered with sitelib.design: no stylesheet, script, image or font from another host.
EXTERNAL_ASSETS_ALLOWED = False


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = build_offline.build(os.path.join(cls.tmp.name, 'site'))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def path(self, *parts):
        return os.path.join(self.out, *parts)

    def test_core_files_exist(self):
        for rel in ('index.html', 'index.txt', 'status.html', 'docs/index.html', 'docs/index.txt',
                    'cli/index.html', 'cli/index.txt', 'mt3000/index.html', 'mt3000/index.txt',
                    'mt3000/release/index.txt', 'api/all.json', 'api/models', 'api/mt3000/stages',
                    'new/index.txt', 'new/index.html', 'feed.xml', 'mt3000/feed.xml'):
            self.assertTrue(os.path.isfile(self.path(rel)), rel)

    def test_reserved_model_gets_no_page(self):
        self.assertFalse(os.path.exists(self.path('api', 'index.html')))

    def test_site_is_consistent(self):
        problems = check_site.check(self.out, no_external_assets=not EXTERNAL_ASSETS_ALLOWED)
        self.assertEqual(problems, [], '\n'.join(problems[:30]))


if __name__ == '__main__':
    unittest.main()
