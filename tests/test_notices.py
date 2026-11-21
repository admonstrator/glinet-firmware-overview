"""Notices from gl-i.net: parsing, banner, text block, API files and an offline build with a notice."""
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import build_offline  # noqa: E402
import check_site  # noqa: E402
from sitelib import notices  # noqa: E402

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)

ADVISORY = {
    'kind': 'advisory', 'id': 'CSA-2026-01', 'level': 'critical', 'severity': 'critical',
    'text': 'An attacker used a flaw in GL.iNet\'s cloud remote management to install malware on some '
            'routers and KVM devices. GL.iNet recommends a factory reset.',
    'url': 'https://gl-i.net/security/csa-2026-01/', 'updated': '2026-11-21',
    'title': 'Cloud remote management flaw', 'status': 'Under investigation', 'exploited': True,
}


def doc(*items):
    return {'version': 1, 'generated': '2026-11-21T11:00:00Z', 'notices': list(items)}


class ParseTests(unittest.TestCase):
    def test_keeps_valid_advisory(self):
        [n] = notices.parse_notices(doc(ADVISORY), NOW)
        self.assertEqual((n['kind'], n['id'], n['level'], n['severity']), ('advisory', 'CSA-2026-01', 'critical', 'critical'))
        self.assertEqual(n['url'], ADVISORY['url'])

    def test_drops_invalid_entries(self):
        bad = [
            dict(ADVISORY, level='urgent'),
            dict(ADVISORY, text='   '),
            dict(ADVISORY, url='http://gl-i.net/security/'),
            dict(ADVISORY, url='javascript:alert(1)'),
            'not a dict',
        ]
        self.assertEqual(notices.parse_notices(doc(*bad), NOW), [])
        self.assertEqual(notices.parse_notices({'notices': 'nope'}, NOW), [])
        self.assertEqual(notices.parse_notices(None, NOW), [])

    def test_until(self):
        past = {'kind': 'notice', 'id': 'm', 'level': 'info', 'text': 'Maintenance', 'url': 'https://forum.gl-inet.com/', 'until': '2026-11-20'}
        today = dict(past, until='2026-11-21')
        later = dict(past, until='2026-11-21T13:00:00+01:00')  # 12:00 UTC, still valid at 12:00
        earlier = dict(past, until='2026-11-21T11:59Z')
        kept = notices.parse_notices(doc(past, today, later, earlier), NOW)
        self.assertEqual([n['until'] for n in kept], ['2026-11-21', '2026-11-21T13:00:00+01:00'])

    def test_whitespace_is_normalised(self):
        [n] = notices.parse_notices(doc(dict(ADVISORY, text='one\ttwo\nthree  four', id='CSA\t1')), NOW)
        self.assertEqual(n['text'], 'one two three four')
        self.assertEqual(n['id'], 'CSA 1')


class RenderTests(unittest.TestCase):
    def tearDown(self):
        notices.set_notices([])

    def test_nothing_without_notices(self):
        notices.set_notices([])
        self.assertEqual(notices.banner_html(), '')
        self.assertEqual(notices.notices_text(), '')
        self.assertEqual(notices.notices_css(), '')
        self.assertEqual(notices.with_notices('page\n'), 'page\n')

    def test_banner_is_escaped(self):
        notices.set_notices(notices.parse_notices(doc(dict(ADVISORY, text='<script>x</script> & "q"')), NOW))
        html = notices.banner_html()
        self.assertIn('<b>Critical security advisory:</b>', html)
        self.assertIn('&lt;script&gt;x&lt;/script&gt; &amp; &quot;q&quot;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('href="https://gl-i.net/security/csa-2026-01/"', html)

    def test_labels(self):
        notice = {'kind': 'notice', 'id': 'm', 'level': 'info', 'text': 'Maintenance', 'url': 'https://forum.gl-inet.com/'}
        parsed = notices.parse_notices(doc(ADVISORY, dict(ADVISORY, level='resolved'), notice), NOW)
        self.assertEqual([notices.label(n) for n in parsed], ['Critical security advisory', 'Resolved', 'Notice'])

    def test_text_block_fits_the_terminal(self):
        notices.set_notices(notices.parse_notices(doc(ADVISORY), NOW))
        block = notices.notices_text()
        self.assertTrue(block.startswith('!! CRITICAL SECURITY ADVISORY  CSA-2026-01\n'))
        self.assertIn('!! https://gl-i.net/security/csa-2026-01/\n', block)
        self.assertTrue(all(len(line) <= 78 for line in block.splitlines()))

    def test_api_files(self):
        notices.set_notices(notices.parse_notices(doc(ADVISORY), NOW))
        with tempfile.TemporaryDirectory() as tmp:
            notices.write_notices_api(tmp)
            with open(os.path.join(tmp, 'notices'), encoding='utf-8') as f:
                fields = f.read().rstrip('\n').split('\t')
            self.assertEqual(fields, ['critical', 'CSA-2026-01', '2026-11-21', ADVISORY['url'], ADVISORY['text']])
            notices.set_notices([])
            notices.write_notices_api(tmp)
            self.assertEqual(os.path.getsize(os.path.join(tmp, 'notices')), 0)


class SiteWithNoticeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = build_offline.build(os.path.join(cls.tmp.name, 'site'), notices=notices.parse_notices(doc(ADVISORY), NOW))

    @classmethod
    def tearDownClass(cls):
        notices.set_notices([])
        cls.tmp.cleanup()

    def read(self, *parts):
        with open(os.path.join(self.out, *parts), encoding='utf-8') as f:
            return f.read()

    def test_banner_on_html_pages(self):
        for rel in (('index.html',), ('mt3000', 'index.html'), ('status.html',), ('docs', 'index.html')):
            page = self.read(*rel)
            self.assertIn('class="notices"', page, rel)
            self.assertLess(page.index('class="notices"'), page.index('<header class="floe">'), rel)

    def test_block_on_text_pages_but_not_in_the_script(self):
        for rel in (('index.txt',), ('mt3000', 'index.txt'), ('mt3000', 'release', 'index.txt'), ('new', 'index.txt')):
            self.assertTrue(self.read(*rel).startswith('!! CRITICAL SECURITY ADVISORY'), rel)
        self.assertTrue(self.read('cli', 'index.txt').startswith('#!/bin/sh'))

    def test_api_mirror(self):
        self.assertTrue(self.read('api', 'notices').startswith('critical\tCSA-2026-01\t'))
        self.assertIn('"CSA-2026-01"', self.read('api', 'notices.json'))

    def test_site_is_consistent(self):
        self.assertEqual(check_site.check(self.out, no_external_assets=True), [])


class CliTests(unittest.TestCase):
    def test_cli_reads_notices_and_has_valid_syntax(self):
        script = os.path.join(REPO, 'cli.sh')
        with open(script, encoding='utf-8') as f:
            text = f.read()
        self.assertIn('NOTICES_URL="https://gl-i.net/notices.tsv"', text)
        self.assertIn('fetch api/notices', text)
        subprocess.run(['sh', '-n', script], check=True)


if __name__ == '__main__':
    unittest.main()
