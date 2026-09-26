"""Atom feeds, the /new page, ages in the text pages and the text menu, checked against the offline build."""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import build_offline  # noqa: E402
import check_site  # noqa: E402
from sitelib import core, feeds  # noqa: E402

A = '{http://www.w3.org/2005/Atom}'
RFC3339 = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')


class FeedTextSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = build_offline.build(os.path.join(cls.tmp.name, 'site'))
        cls.models, cls.meta, _, _, cls.generated_at = build_offline.load_fixture()
        cls.now = core.parse_generated_at(cls.generated_at)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def read(self, *parts):
        with open(os.path.join(self.out, *parts), encoding='utf-8') as f:
            return f.read()

    def feed(self, *parts):
        return ET.parse(os.path.join(self.out, *parts)).getroot()

    # --- feeds -----------------------------------------------------------

    def test_every_feed_parses_and_is_atom(self):
        paths = glob.glob(os.path.join(self.out, '*.xml')) + glob.glob(os.path.join(self.out, '*', 'feed.xml'))
        device_codes = [c for c in self.models if core.device_page_url(c)]
        self.assertEqual(len(paths), 1 + len(device_codes))
        for path in paths:
            root = ET.parse(path).getroot()
            self.assertEqual(root.tag, f'{A}feed', path)
            for tag in ('id', 'title', 'updated', 'author'):
                self.assertIsNotNone(root.find(f'{A}{tag}'), f'{path} <{tag}>')
            rels = {link.get('rel') for link in root.findall(f'{A}link')}
            self.assertEqual(rels, {'self', 'alternate'}, path)
            ids = [e.findtext(f'{A}id') for e in root.findall(f'{A}entry')]
            self.assertEqual(len(ids), len(set(ids)), f'duplicate entry ids in {path}')

    def test_global_feed(self):
        root = self.feed('feed.xml')
        self.assertEqual(root.findtext(f'{A}id'), core.feed_url(absolute=True))
        self.assertIn('unofficial', root.findtext(f'{A}title'))
        self.assertIn('not affiliated with GL.iNet', root.findtext(f'{A}subtitle'))
        entries = root.findall(f'{A}entry')
        self.assertEqual(len(entries), core.GLOBAL_FEED_LIMIT)
        for e in entries:
            self.assertNotEqual(e.find(f'{A}category').get('term'), 'snapshot')
            self.assertNotIn('/snapshot/', e.findtext(f'{A}id'))
        # newest first, and the feed's <updated> is the newest entry
        stamps = [e.findtext(f'{A}updated') for e in entries]
        self.assertEqual(stamps, sorted(stamps, reverse=True))
        self.assertEqual(root.findtext(f'{A}updated'), stamps[0])

    def test_entry_fields(self):
        root = self.feed('be3600', 'feed.xml')
        entry = next(e for e in root.findall(f'{A}entry') if e.findtext(f'{A}id').endswith('/release/4.10.1'))
        self.assertEqual(entry.findtext(f'{A}id'), core.feed_entry_id('be3600', 'RELEASE', '4.10.1'))
        self.assertEqual(entry.findtext(f'{A}title'), 'Slate 7 (GL-BE3600): Release 4.10.1')
        self.assertEqual(entry.findtext(f'{A}updated'), '2026-09-20T18:00:48Z')
        self.assertEqual(entry.findtext(f'{A}published'), '2026-09-20T18:00:48Z')
        links = {link.get('rel'): link.get('href') for link in entry.findall(f'{A}link')}
        self.assertEqual(links['alternate'], f'{core.SITE_URL}/be3600/release/')
        self.assertEqual(links['related'], core.entry_link(self.models['be3600']['RELEASE']))
        content = entry.find(f'{A}content')
        self.assertEqual(content.get('type'), 'text')
        self.assertIn('Version: 4.10.1', content.text)
        self.assertIn(links['related'], content.text)
        self.assertIn('Changelog:', content.text)

    def test_all_dates_are_rfc3339(self):
        for path in glob.glob(os.path.join(self.out, '*.xml')) + glob.glob(os.path.join(self.out, '*', 'feed.xml')):
            root = ET.parse(path).getroot()
            stamps = [root.findtext(f'{A}updated')]
            for e in root.findall(f'{A}entry'):
                stamps += [e.findtext(f'{A}updated'), e.findtext(f'{A}published')]
            for stamp in stamps:
                self.assertRegex(stamp, RFC3339, path)
                datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ')

    def test_dead_link_uses_fallback_download(self):
        info = self.models['mt6000']['RELEASE']
        for path in (('feed.xml',), ('mt6000', 'feed.xml')):
            root = self.feed(*path)
            entry = next((e for e in root.findall(f'{A}entry')
                          if e.findtext(f'{A}id') == core.feed_entry_id('mt6000', 'RELEASE', info['version'])), None)
            if entry is None:  # older than the newest 50 builds of the global feed
                self.assertEqual(path, ('feed.xml',))
                continue
            related = [link.get('href') for link in entry.findall(f'{A}link') if link.get('rel') == 'related']
            self.assertEqual(related, [info['_fallback_link']])
            text = entry.findtext(f'{A}content')
            self.assertIn('did not respond', text)
            self.assertIn(info['_fallback_version'], text)
            self.assertIn(core.entry_link(info), text)

    def test_device_feed_has_every_stage(self):
        root = self.feed('mt6000', 'feed.xml')
        self.assertEqual(root.findtext(f'{A}id'), core.feed_url('mt6000', absolute=True))
        self.assertIn('Flint 2', root.findtext(f'{A}title'))
        terms = sorted(e.find(f'{A}category').get('term') for e in root.findall(f'{A}entry'))
        self.assertEqual(terms, sorted(core.api_stage_name(s) for s in self.models['mt6000']))
        self.assertIn('snapshot', terms)

    def test_empty_and_reserved_models(self):
        root = self.feed('zz-empty', 'feed.xml')
        self.assertEqual(root.findall(f'{A}entry'), [])
        self.assertIn('Test <Empty> & Co', root.findtext(f'{A}title'))
        self.assertFalse(os.path.exists(os.path.join(self.out, 'api', 'feed.xml')))
        # a reserved model code has no device page: its entries link the overview
        for e in self.feed('feed.xml').findall(f'{A}entry'):
            if e.findtext(f'{A}id').startswith('tag:firmware.gl-i.net,2026:api/'):
                alternate = [link.get('href') for link in e.findall(f'{A}link') if link.get('rel') == 'alternate']
                self.assertEqual(alternate, [f'{core.SITE_URL}/'])

    # --- text pages ------------------------------------------------------

    def test_new_lists_only_recent_builds(self):
        text = self.read('new', 'index.txt')
        lines = text.splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith('MODEL '))
        header = lines[start]
        names = header.split()
        cols = [m.start() for m in re.finditer(r'\S+', header)] + [None]
        rows = []
        for line in lines[start + 1:]:
            if not line.strip():
                break
            rows.append({n: line[cols[i]:cols[i + 1]].strip() for i, n in enumerate(names)})
        self.assertEqual(names, ['MODEL', 'NAME', 'STAGE', 'VERSION', 'RELEASED', 'AGE'])
        expected = core.recent_builds(self.models, self.meta, self.now)
        self.assertTrue(expected, 'the fixture should contain recent builds')
        self.assertEqual([(r['MODEL'], r['STAGE']) for r in rows],
                         [(b['code'].lower(), core.api_stage_name(b['stage'])) for b in expected])
        for r, b in zip(rows, expected):
            released = datetime.strptime(r['RELEASED'], '%Y-%m-%d')
            self.assertLessEqual((self.now.date() - released.date()).days, core.RECENT_DAYS)
            self.assertNotEqual(r['STAGE'], 'snapshot')
            self.assertEqual(r['AGE'], core.age_text(b['days']))
        self.assertIn(f'Recently released ({len(expected)})', lines[0])
        self.assertIn(core.age_text(expected[0]['days']), text)
        self.assertIn(core.feed_url(absolute=True), text)
        self.assertIn(f'curl {core.SITE_URL}/<model>/<stage>', text)
        self.assertIn('redirect', self.read('new', 'index.html').lower())
        self.assertIn('../#recent', self.read('new', 'index.html'))

    def test_new_without_recent_builds(self):
        from sitelib import text_pages
        text = text_pages.generate_text_new(self.models, self.meta, '2030-01-01 00:00:00 UTC')
        self.assertIn('Recently released (0)', text)
        self.assertIn(f'No firmware build was released in the last {core.RECENT_DAYS} days.', text)
        self.assertNotIn('MODEL ', text)

    def test_category_pages_have_updated_column(self):
        for page in ('routers', 'iot', 'kvm', 'all'):
            text = self.read(page, 'index.txt')
            headers = [line for line in text.splitlines() if line.startswith('MODEL ')]
            self.assertTrue(headers, page)
            for header in headers:
                self.assertTrue(header.rstrip().endswith('UPDATED'), f'{page}: {header}')
        _, newest = core.latest_update(self.models['mt6000'])
        row = next(line for line in self.read('routers', 'index.txt').splitlines() if line.startswith('mt6000 '))
        self.assertEqual(row.split()[-1], core.age_short(core.days_since(newest, self.now)))
        row = next(line for line in self.read('iot', 'index.txt').splitlines() if line.startswith('zz-empty '))
        self.assertEqual(row.split()[-1], '-')

    def test_device_page_shows_last_update(self):
        stage, newest = core.latest_update(self.models['mt6000'])
        expected = (f"Last update: {core.age_text(core.days_since(newest, self.now))} "
                    f"({core.api_stage_name(stage)} {newest['version']})")
        self.assertEqual(self.read('mt6000', 'index.txt').splitlines()[2], expected)
        self.assertNotIn('Last update:', self.read('zz-empty', 'index.txt'))

    def test_menu_links_new_and_docs(self):
        text = self.read('index.txt')
        self.assertIn(f'curl {core.SITE_URL}/new', text)
        self.assertIn(f'curl {core.SITE_URL}/docs', text)
        self.assertIn('Recently released', text)
        self.assertIn('API & terminal docs', text)
        self.assertIn('not affiliated with GL.iNet', text)

    def test_site_is_consistent(self):
        problems = check_site.check(self.out)
        self.assertEqual(problems, [], '\n'.join(problems[:30]))


class FeedHelperTests(unittest.TestCase):
    def test_atom_time(self):
        self.assertEqual(feeds.atom_time('2026-09-20 18:00:48'), '2026-09-20T18:00:48Z')
        self.assertEqual(feeds.atom_time('2026-09-20'), '2026-09-20T00:00:00Z')
        self.assertIsNone(feeds.atom_time(''))
        self.assertIsNone(feeds.atom_time(None))
        self.assertIsNone(feeds.atom_time('soon'))

    def test_shorten_changelog(self):
        short = 'Fixed a bug.\n\nAdded a feature.'
        self.assertEqual(feeds.shorten_changelog(short), (short, False))
        long_text = '\n'.join(f'Line {i}: fixed an issue where something did not work as expected.' for i in range(200))
        text, shortened = feeds.shorten_changelog(long_text)
        self.assertTrue(shortened)
        self.assertLessEqual(len(text), feeds.CHANGELOG_LIMIT)
        self.assertTrue(long_text.startswith(text))
        self.assertTrue(text.endswith('expected.'), 'cut at a line break')

    def test_long_changelog_links_full_text(self):
        entry = {'version': '4.9.0', 'release_time': '2026-09-20 10:00:00', '_link_ok': True,
                 'download': [{'link': 'https://fw.gl-inet.com/x.bin', 'md5': ''}], 'changelog': 'x\n' * 3000}
        content = feeds.entry_content('MT3000', 'RELEASE', entry)
        self.assertIn(f'Full changelog: {core.SITE_URL}/api/mt3000/release/changelog', content)
        self.assertLess(len(content), feeds.CHANGELOG_LIMIT + 500)

    def test_escaping_and_control_characters(self):
        entry = {'version': '1.0', 'release_time': '', '_link_ok': True, 'download': [{'link': 'https://x/a?b=1&c=2'}],
                 'changelog': 'a < b & c\x0b\x01 done'}
        xml = feeds.atom_feed('https://example.test/feed.xml', 'T & <T>', 'sub', 'https://example.test/',
                              [{'code': 'x1', 'name': 'GL-X1 Test & Co', 'stage': 'BETA_OPEN24', 'entry': entry}],
                              '2026-09-26T13:23:07Z')
        root = ET.fromstring(xml.encode('utf-8'))
        e = root.find(f'{A}entry')
        self.assertEqual(e.findtext(f'{A}title'), 'Test & Co (GL-X1): Beta OP24 1.0')
        self.assertEqual(e.findtext(f'{A}updated'), '2026-09-26T13:23:07Z')  # no release_time: build time
        self.assertIn('a < b & c done', e.findtext(f'{A}content'))
        self.assertEqual(e.find(f'{A}category').get('term'), 'beta-open24')


class CliScriptTests(unittest.TestCase):
    def test_cli_has_recent_entry_and_valid_syntax(self):
        path = os.path.join(REPO, 'cli.sh')
        with open(path, encoding='utf-8') as f:
            script = f.read()
        self.assertIn('fetch new/index.txt', script)
        self.assertIn('Recently released', script)
        shell = shutil.which('sh')
        if shell:
            result = subprocess.run([shell, '-n', path], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
