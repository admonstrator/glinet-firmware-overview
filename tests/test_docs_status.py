"""The /docs/ page (HTML + text twin), the /cli/ landing page and status.html, checked on the offline build."""
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import build_offline  # noqa: E402
import check_site  # noqa: E402
from sitelib.core import device_page_url  # noqa: E402
from sitelib.docs_page import DOCS_SECTIONS, DOCS_TEXT_WIDTH  # noqa: E402
from sitelib.status_page import generate_status_html  # noqa: E402

OWN_PAGES = ('status.html', os.path.join('docs', 'index.html'), os.path.join('cli', 'index.html'))


class DocsStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = build_offline.build(os.path.join(cls.tmp.name, 'site'))
        with open(os.path.join(build_offline.FIXTURES, 'site_data.json'), encoding='utf-8') as f:
            cls.models = json.load(f)
        cls.docs_html = cls.read('docs', 'index.html')
        cls.docs_text = cls.read('docs', 'index.txt')
        cls.status = cls.read('status.html')
        cls.cli = cls.read('cli', 'index.html')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def read(cls, *parts):
        with open(os.path.join(cls.out, *parts), encoding='utf-8') as f:
            return f.read()

    # /docs/ -----------------------------------------------------------------

    def test_docs_sections_in_r5_order(self):
        self.assertEqual([sid for sid, _ in DOCS_SECTIONS], ['menu', 'text', 'api', 'feeds', 'examples', 'codes'])
        positions = [self.docs_html.find(f'<h2 id="{sid}">') for sid, _ in DOCS_SECTIONS]
        self.assertNotIn(-1, positions)
        self.assertEqual(positions, sorted(positions))
        for sid, _ in DOCS_SECTIONS:
            self.assertIn(f'<a href="#{sid}">', self.docs_html, 'jump link')

    def test_docs_text_same_order(self):
        positions = [self.docs_text.find(f'\n{title}\n{"-" * len(title)}\n') for _, title in DOCS_SECTIONS]
        self.assertNotIn(-1, positions)
        self.assertEqual(positions, sorted(positions))

    def test_docs_text_mentions_entry_points(self):
        for needle in ('/cli', '/feed.xml', '/new', '/api/all.json', '/api/status.json', '/api/models'):
            self.assertIn(needle, self.docs_text)
        self.assertIn('Menu:', self.docs_text)
        long_lines = [ln for ln in self.docs_text.splitlines() if len(ln) > DOCS_TEXT_WIDTH and 'https://' not in ln]
        self.assertEqual(long_lines, [])

    def test_docs_lists_every_model_code(self):
        for code in self.models:
            slug = code.lower()
            # left column after the two-space indent, right column after at least four spaces
            self.assertRegex(self.docs_text, r'(?m)(?:^  | {4})' + re.escape(slug) + r' {2}', slug)
            if device_page_url(code):
                self.assertIn(f'href="../{slug}/"', self.docs_html, slug)
            else:
                self.assertNotIn(f'href="../{slug}/"', self.docs_html, slug)
                self.assertIn(f'<code>{slug}</code>', self.docs_html, slug)

    def test_docs_escapes_names(self):
        self.assertIn('Test &lt;Empty&gt; &amp; Co', self.docs_html)
        self.assertNotIn('<Empty>', self.docs_html)
        self.assertIn('Test <Empty> & Co', self.docs_text)

    def test_docs_example_output_is_real(self):
        mt3000 = self.models['mt3000']['RELEASE']
        with open(os.path.join(self.out, 'api', 'mt3000', 'release', 'index.html'), encoding='utf-8') as f:
            summary = f.read()
        self.assertIn(mt3000['download'][0]['link'], self.docs_html)
        self.assertIn(summary.splitlines()[0], self.docs_text)
        for stage in ('release', 'beta', 'beta-open24', 'beta-open25', 'snapshot', 'clean', 'legacy', 'tor'):
            self.assertIn(f'<code>{stage}</code>', self.docs_html)
        self.assertIn('href="../feed.xml"', self.docs_html)
        self.assertIn('href="../cli/index.txt"', self.docs_html)

    # /cli/ ------------------------------------------------------------------

    def test_cli_landing_page(self):
        self.assertIn('/cli | sh', self.cli)
        self.assertIn('wget -qO-', self.cli)
        self.assertIn('href="index.txt"', self.cli)
        self.assertIn('href="../docs/"', self.cli)

    # status.html ------------------------------------------------------------

    def test_status_lists_problems(self):
        for row_id in ('mt6000-release', 'mt6000-beta'):
            self.assertIn(f'id="{row_id}"', self.status)
        for needle in ('HTTP 404 Not Found', 'timeout', '4.7.9', 'mt6000-4.7.9-fixture.bin', 'none (5 probed)',
                       'zz-empty', 'href="api/status.json"', '2026-09-26 13:23:07 UTC'):
            self.assertIn(needle, self.status)
        self.assertNotIn('Nothing to report', self.status)

    def test_status_all_good(self):
        page = generate_status_html([], [], '2026-09-26 13:23:07 UTC')
        self.assertIn('Nothing to report', page)
        self.assertNotIn('id="unreachable"', page)
        self.assertNotIn('id="no-data"', page)

    # all three --------------------------------------------------------------

    def test_new_design_and_no_external_assets(self):
        for rel in OWN_PAGES:
            page = check_site.parse_page(os.path.join(self.out, rel))
            self.assertEqual(page.external, [], rel)
            html = self.read(rel)
            self.assertIn('class="floe"', html, rel)
            self.assertIn('Unofficial community project, not affiliated with GL.iNet', html, rel)
            self.assertIn('(unofficial)</title>', html, rel)
            for legacy in ('bootstrap', 'font-awesome', 'cdn.jsdelivr', '<script'):
                self.assertNotIn(legacy, html, f'{rel}: {legacy}')

    def test_own_pages_pass_site_check(self):
        own = [p for p in check_site.check(self.out, no_external_assets=True)
               if p.split(':', 1)[0] in OWN_PAGES]
        self.assertEqual(own, [], '\n'.join(own))


if __name__ == '__main__':
    unittest.main()
