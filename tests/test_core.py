"""Unit tests for the phase contract helpers in sitelib.core."""
import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sitelib import core  # noqa: E402

NOW = datetime(2026, 9, 26, 13, 23, 7)


def entry(date, version='1.0'):
    return {'version': version, 'release_time': f'{date} 10:00:00', 'download': [{'link': 'https://fw.gl-inet.com/x.bin'}]}


class AgeTests(unittest.TestCase):
    def test_parse_generated_at(self):
        self.assertEqual(core.parse_generated_at('2026-09-26 13:23:07 UTC'), NOW)

    def test_days_since(self):
        self.assertEqual(core.days_since(entry('2026-09-20'), NOW), 6)
        self.assertEqual(core.days_since({'release_time': ''}, NOW), None)
        self.assertEqual(core.days_since(entry('2026-09-30'), NOW), 0)  # future dates clamp to 0

    def test_age_text(self):
        cases = {None: 'unknown', 0: 'today', 1: 'yesterday', 5: '5 days ago', 13: '13 days ago', 14: '2 weeks ago',
                 59: '8 weeks ago', 60: '2 months ago', 729: '24 months ago', 730: '2 years ago'}
        for days, text in cases.items():
            self.assertEqual(core.age_text(days), text, days)

    def test_age_short(self):
        cases = {None: '-', 0: '0d', 13: '13d', 14: '2w', 60: '2mo', 800: '2y'}
        for days, text in cases.items():
            self.assertEqual(core.age_short(days), text, days)

    def test_is_fresh(self):
        self.assertTrue(core.is_fresh(entry('2026-09-12'), NOW))
        self.assertFalse(core.is_fresh(entry('2026-09-11'), NOW))

    def test_latest_update(self):
        stages = {'RELEASE': entry('2026-01-01'), 'SNAPSHOT': entry('2026-09-01'), 'BETA': entry('2026-05-01')}
        self.assertEqual(core.latest_update(stages)[0], 'SNAPSHOT')
        self.assertEqual(core.latest_update({}), (None, None))


class RecentTests(unittest.TestCase):
    models = {
        'mt3000': {'RELEASE': entry('2026-09-20', '4.9.0'), 'SNAPSHOT': entry('2026-09-25', '4.9.1'), 'BETA': entry('2026-08-01', '4.8.9')},
        'be9300': {'RELEASE': entry('2026-09-22', '4.10.1')},
    }
    meta = {'mt3000': {'name': 'GL-MT3000 Beryl AX', 'type': 'ROUTER'}, 'be9300': {'name': 'GL-BE9300 Flint 3', 'type': 'ROUTER'}}

    def test_recent_excludes_snapshots_and_old(self):
        recent = core.recent_builds(self.models, self.meta, NOW)
        self.assertEqual([(b['code'], b['stage']) for b in recent], [('be9300', 'RELEASE'), ('mt3000', 'RELEASE')])
        self.assertEqual(recent[0]['days'], 4)

    def test_builds_newest_first(self):
        allb = core.builds_newest_first(self.models, self.meta)
        self.assertEqual(allb[0]['stage'], 'SNAPSHOT')
        self.assertEqual(len(allb), 4)


class NamingTests(unittest.TestCase):
    def test_split_name(self):
        self.assertEqual(core.split_name('GL-MT3000 Beryl AX', 'mt3000'), ('Beryl AX', 'GL-MT3000'))
        self.assertEqual(core.split_name('GL-MT2500/GL-MT2500A Brume 2', 'mt2500'), ('Brume 2', 'GL-MT2500/GL-MT2500A'))
        self.assertEqual(core.split_name('GL-S10', 's10'), ('GL-S10', ''))
        self.assertEqual(core.split_name('GL-S20 (BLE Firmware)', 's20ble'), ('GL-S20 (BLE Firmware)', 'S20BLE'))
        self.assertEqual(core.split_name('VIXMINI', 'vixmini'), ('VIXMINI', ''))

    def test_stage_class_and_title(self):
        self.assertEqual(core.stage_class('RELEASE'), 'release')
        self.assertEqual(core.stage_class('BETA_OPEN25'), 'beta')
        self.assertEqual(core.stage_class('TOR'), 'other')
        self.assertEqual(core.stage_title('BETA_OPEN24', {'_openwrt_base': '24'}), 'Beta OP24')
        self.assertEqual(core.stage_title('CLEAN'), 'Clean')

    def test_feed_urls(self):
        self.assertEqual(core.feed_url(), 'feed.xml')
        self.assertEqual(core.feed_url('MT3000', root='../'), '../mt3000/feed.xml')
        self.assertEqual(core.feed_url(absolute=True), 'https://firmware.gl-i.net/feed.xml')
        self.assertEqual(core.feed_entry_id('mt3000', 'BETA_OPEN25', '4.9.1'), 'tag:firmware.gl-i.net,2026:mt3000/beta-open25/4.9.1')

    def test_reserved_names(self):
        for name in ('docs', 'new', 'sitelib', 'tests'):
            self.assertIn(name, core.RESERVED_ROOT_NAMES)


if __name__ == '__main__':
    unittest.main()
