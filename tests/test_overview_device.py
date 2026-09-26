"""Overview and device pages: rendered from the fixture, offline."""
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
from sitelib import core, device, overview  # noqa: E402


class OverviewDevicePagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = build_offline.build(os.path.join(cls.tmp.name, 'site'))
        cls.models, cls.metadata, cls.diagnostics, _, cls.generated_at = build_offline.load_fixture()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, *parts):
        with open(os.path.join(self.out, *parts), encoding='utf-8') as f:
            return f.read()

    def device_codes(self):
        return [c for c in self.models if core.device_page_url(c)]

    # Overview

    def test_overview_title_and_unofficial_note(self):
        page = self.read('index.html')
        self.assertIn('<title>GL.iNet Firmware Overview (unofficial)</title>', page)
        self.assertIn('Unofficial community project, not affiliated with GL.iNet', page)
        self.assertIn(f'The latest firmware for {len(self.models)} GL.iNet routers', page)

    def test_overview_has_no_external_assets(self):
        page = self.read('index.html')
        self.assertNotIn('<script src=', page)
        self.assertNotRegex(page, r'<link[^>]+rel="stylesheet"')
        self.assertNotIn('cdn.jsdelivr.net', page)

    def test_recent_section(self):
        page = self.read('index.html')
        self.assertEqual(page.count('id="recent"'), 1)
        section = page.split('id="recent"', 1)[1].split('</section>', 1)[0]
        self.assertIn(f'href="{core.feed_url()}"', section)
        now = core.parse_generated_at(self.generated_at)
        expected = core.recent_builds(self.models, self.metadata, now)
        self.assertTrue(expected)
        self.assertEqual(section.count('<li>'), len(expected))
        # Newest first, each device linked to the block of its stage on the device page
        first, last = expected[0], expected[-1]
        self.assertIn(f'href="{core.device_page_url(first["code"])}#{core.api_stage_name(first["stage"])}"', section)
        self.assertLess(section.index(f'{core.device_page_url(first["code"])}#'),
                        section.index(f'{core.device_page_url(last["code"])}#'))
        # Snapshots stay out (mt6000 has a snapshot from two days ago)
        self.assertNotIn('Snapshot', section)
        # Sits between the toolbar and the first table
        self.assertLess(page.index('class="toolbar"'), page.index('id="recent"'))
        self.assertLess(page.index('id="recent"'), page.index('class="cat"'))

    def test_recent_section_empty(self):
        page = overview.generate_html(self.models, self.metadata, self.diagnostics, '2030-01-01 00:00:00 UTC')
        self.assertIn('id="recent"', page)
        self.assertIn(f'No new firmware in the last {core.RECENT_DAYS} days.', page)

    def test_overview_feed_link(self):
        page = self.read('index.html')
        self.assertIn(f'<link rel="alternate" type="application/atom+xml" title="All devices" href="{core.feed_url()}">', page)

    def test_overview_categories_and_columns(self):
        page = self.read('index.html')
        for slug in ('router', 'iot', 'kvm'):
            self.assertIn(f'<section class="cat" id="{slug}">', page)
            self.assertIn(f'id="f-{slug}"', page)
        kvm = page.split('id="kvm"', 1)[1].split('</section>', 1)[0]
        head = kvm.split('<thead>', 1)[1].split('</thead>', 1)[0]
        self.assertEqual(re.findall(r'<th scope="col"[^>]*>([^<]+)</th>', head), ['Device', 'Release', 'Beta', 'Last update'])
        router = page.split('id="router"', 1)[1].split('</section>', 1)[0]
        self.assertIn('>Tor</th>', router)

    def test_overview_last_update_column(self):
        page = self.read('index.html')
        self.assertIn('>Last update</th>', page)
        row = page.split('<tr id="mt6000"', 1)[1].split('</tr>', 1)[0]
        # The newest mt6000 build is the snapshot from 2026-09-24
        self.assertIn('<td class="age" data-stage="Last update"><time datetime="2026-09-24"', row)
        self.assertIn('<span class="s">2d</span><span class="l">2 days ago</span>', row)
        empty = page.split('<tr id="zz-empty"', 1)[1].split('</tr>', 1)[0]
        self.assertIn('class="age empty"', empty)

    def test_overview_dead_links_and_fallback(self):
        page = self.read('index.html')
        row = page.split('<tr id="mt6000"', 1)[1].split('</tr>', 1)[0]
        self.assertEqual(row.count('class="ver dead"'), 2)
        self.assertIn('href="status.html" title="Download did not respond (HTTP 404 Not Found)', row)
        self.assertIn('title="Download did not respond (timeout)', row)
        self.assertIn('href="https://fw.gl-inet.com/firmware/mt6000/release/mt6000-4.7.9-fixture.bin"', row)
        self.assertIn('4.7.9 instead', row)
        # Open builds sit in the Beta cell with their tag
        self.assertIn('>OP24</span>', row)
        self.assertIn('>OP25</span>', row)

    def test_overview_rows_sorted_by_nickname(self):
        page = self.read('index.html')
        router = page.split('id="router"', 1)[1].split('</section>', 1)[0]
        nicks = re.findall(r'<span class="nick">([^<]+)</span>', router)
        self.assertEqual(nicks, sorted(nicks, key=str.lower))
        self.assertIn('<a href="mt3000/"><span class="nick">Beryl AX</span><span class="sku">GL-MT3000</span></a>', router)

    def test_overview_reserved_model_has_no_page_link(self):
        page = self.read('index.html')
        row = page.split('data-search="api collision test"', 1)[1].split('</tr>', 1)[0]
        self.assertNotIn('href="api/"', row)

    def test_overview_escapes_names(self):
        page = self.read('index.html')
        self.assertIn('Test &lt;Empty&gt; &amp; Co', page)
        self.assertNotIn('Test <Empty>', page)

    def test_overview_works_without_javascript(self):
        page = self.read('index.html')
        self.assertIn('<label class="search" id="search" hidden>', page)
        self.assertIn('<noscript>', page)
        self.assertIn('type="radio" name="cat" id="f-all" checked', page)
        script = page.split('<script>', 1)[1].split('</script>', 1)[0]
        self.assertLess(len(script.encode('utf-8')), 1024)

    # Device pages

    def test_device_page_marker_follows_doctype(self):
        for code in self.device_codes():
            page = self.read(code.lower(), 'index.html')
            self.assertTrue(page.startswith(f'<!DOCTYPE html>\n{core.DEVICE_PAGE_MARKER}\n'), code)

    def test_device_pages_have_stage_anchors(self):
        self.assertIn('id="release"', self.read('mt3000', 'index.html'))
        for code in self.device_codes():
            page = self.read(code.lower(), 'index.html')
            for stage in self.models[code]:
                self.assertIn(f'id="{core.api_stage_name(stage)}"', page, f'{code} {stage}')

    def test_device_page_stage_order_and_header(self):
        page = self.read('mt3000', 'index.html')
        ids = re.findall(r'<article class="buildcard" id="([^"]+)"', page)
        self.assertEqual(ids, [core.api_stage_name(s) for s in core.ordered_stages(self.models['mt3000'])])
        self.assertIn('<title>Beryl AX (GL-MT3000) firmware, GL.iNet Firmware Overview (unofficial)</title>', page)
        self.assertIn(f'<link rel="canonical" href="{core.SITE_URL}/mt3000/">', page)
        self.assertIn('<h1>Beryl AX</h1>', page)
        self.assertIn('<p class="sku-line">GL-MT3000</p>', page)
        self.assertIn('<a href="../#router">Routers</a>', page)
        self.assertIn('Last update <time datetime="2026-09-05"', page)
        self.assertIn('(Beta 4.11.0)', page)
        self.assertEqual(page.count('<details open>'), 1)

    def test_device_page_feed_links(self):
        page = self.read('mt3000', 'index.html')
        self.assertIn(f'type="application/atom+xml" title="Beryl AX firmware" href="{core.feed_url("mt3000", root="../")}"', page)
        self.assertIn(f'type="application/atom+xml" title="All devices" href="{core.feed_url(root="../")}"', page)

    def test_device_page_terminal_part(self):
        page = self.read('mt3000', 'index.html')
        self.assertIn(f'curl {core.SITE_URL}/mt3000\n', page)
        self.assertIn(f'curl {core.SITE_URL}/api/mt3000/release/version', page)
        self.assertIn(f'href="../{core.DOCS_DIR}/"', page)

    def test_device_page_fallback(self):
        page = self.read('mt6000', 'index.html')
        self.assertIn('Download 4.7.9 instead', page)
        self.assertIn('href="https://fw.gl-inet.com/firmware/mt6000/release/mt6000-4.7.9-fixture.bin"', page)
        self.assertIn('HTTP 404 Not Found', page)
        self.assertIn('(timeout)', page)
        self.assertIn('MD5 <code>d41d8cd98f00b204e9800998ecf8427e</code>', page)

    def test_device_page_empty_model_escapes_name(self):
        page = self.read('zz-empty', 'index.html')
        self.assertIn('<h1>Test &lt;Empty&gt; &amp; Co</h1>', page)
        self.assertNotIn('Test <Empty>', page)
        self.assertIn('lists no firmware for this device', page)
        self.assertNotIn('class="buildcard"', page)
        self.assertNotIn('/api/zz-empty/release', page)

    def test_last_update_everywhere(self):
        self.assertIn('Last update', self.read('index.html'))
        self.assertIn('Last update', self.read('mt3000', 'index.html'))

    def test_generate_device_page_direct(self):
        html = device.generate_device_page('mt3000', self.models['mt3000'], self.metadata['mt3000'], self.generated_at)
        self.assertEqual(html, self.read('mt3000', 'index.html'))

    def test_no_external_assets_in_owned_pages(self):
        problems = check_site.check(self.out, no_external_assets=True)
        owned = [p for p in problems if p.startswith('index.html:')
                 or re.match(r'[^/]+/index\.html:', p) and p.split('/', 1)[0] in {c.lower() for c in self.models}]
        self.assertEqual(owned, [], '\n'.join(owned))


if __name__ == '__main__':
    unittest.main()
