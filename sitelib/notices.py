"""Security advisories and notices from gl-i.net, shown on every page of this site.

gl-i.net (the GL.iNet community app site) publishes what it currently shows
as a bar at https://gl-i.net/notices.json: open security advisories, recently
fixed ones and short notices such as maintenance of GL.iNet's servers.
The build reads that file once (fail-soft: unreachable means no banner) and
puts the notices

  * above the header of every HTML page (page_head in sitelib.design),
  * at the top of the text pages for curl (sitelib.text_pages),
  * into api/notices (tab-separated, for cli.sh) and api/notices.json.

cli.sh reads https://gl-i.net/notices.tsv itself first, so the terminal menu is
current even between two builds of this site; api/notices is its fallback.
check_notices.py (every 30 minutes) starts a build when gl-i.net's notices change.
"""
import html as html_lib
import json
import os
import textwrap
import urllib.request
from datetime import datetime, timedelta, timezone

from sitelib.core import SITE_URL

NOTICES_URL = 'https://gl-i.net/notices.json'
NOTICES_TIMEOUT = 10
LEVELS = ('critical', 'warning', 'info', 'resolved')

_current = []


def _moment(value):
    """'2026-11-28' (end of that day, UTC) or an ISO date-time with zone -> aware datetime, or None."""
    try:
        if len(value) == 10:
            return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=timezone.utc) + timedelta(days=1, seconds=-1)
        moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def parse_notices(data, now=None):
    """The notices of a notices.json document that are valid and not expired.
    Unknown levels, missing text, non-https links and passed `until` dates are dropped."""
    now = now or datetime.now(timezone.utc)
    items = data.get('notices') if isinstance(data, dict) else None
    out = []
    for n in items if isinstance(items, list) else []:
        if not isinstance(n, dict):
            continue
        level, text, url = n.get('level'), ' '.join(str(n.get('text') or '').split()), str(n.get('url') or '')
        if level not in LEVELS or not text or not url.startswith('https://'):
            continue
        until = str(n.get('until') or '')
        if until and (_moment(until) or now) < now:
            continue
        out.append({
            'kind': 'advisory' if n.get('kind') == 'advisory' else 'notice',
            'id': ' '.join(str(n.get('id') or '').split()),
            'level': level,
            'severity': str(n.get('severity') or ''),
            'text': text,
            'url': url,
            'updated': str(n.get('updated') or ''),
            'until': until,
        })
    return out


def _load_json(url, timeout):
    req = urllib.request.Request(url, headers={'User-Agent': 'glinet-firmware-overview'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def fetch_notices(url=NOTICES_URL, fallback=f'{SITE_URL}/api/notices.json', timeout=NOTICES_TIMEOUT):
    """Download and parse notices.json. When gl-i.net cannot be read, the notices this
    site showed so far (`fallback`, its own api/notices.json) stay, so an outage there
    does not drop a banner. Never fails the build: without either source there are none."""
    for source in (url, fallback):
        if not source:
            continue
        try:
            return parse_notices(_load_json(source, timeout))
        except Exception as e:  # network, HTTP or JSON error
            print(f"  WARNING notices from {source} not loaded: {type(e).__name__}: {e}")
    return []


def set_notices(notices):
    """Notices for every page rendered from now on (write_site sets them once per build)."""
    global _current
    _current = list(notices or [])


def current():
    return list(_current)


def label(n):
    """'Critical security advisory', 'Resolved', 'Notice'."""
    if n['level'] == 'resolved':
        return 'Resolved'
    if n['kind'] == 'advisory':
        return f"{n['severity'].capitalize()} security advisory" if n['severity'] else 'Security advisory'
    return 'Notice'


NOTICES_CSS = """
/* Notices from gl-i.net (sitelib.notices) */
.notices { font-size: 14px; line-height: 1.45; }
.notice { margin: 0; padding: 10px 24px; text-align: center; text-wrap: balance; color: #fff; background: #B3261E; }
.notice.warning { color: #2B1A00; background: #F5A524; }
.notice.info { background: #0A66C2; }
.notice.resolved { background: #1E6B43; }
.notice b { font-weight: 650; }
.notice a { margin-left: 8px; font-weight: 650; white-space: nowrap; color: inherit; text-underline-offset: 3px; }
.notice .ico { width: 15px; height: 15px; margin-right: 6px; vertical-align: -2px; }
@media (prefers-color-scheme: dark) {
  .notice { background: #A3241B; } .notice.warning { background: #E59A22; color: #1D1100; }
  .notice.info { background: #0B5CAD; } .notice.resolved { background: #17573A; }
}
@media (max-width: 700px) { .notice { text-align: left; padding: 10px 16px; } .notice a { display: inline-block; margin: 4px 0 0; } }
"""


def notices_css():
    return NOTICES_CSS if _current else ''


def banner_html():
    """The notices as bars above the header; empty without notices."""
    if not _current:
        return ''
    rows = []
    for n in _current:
        e = html_lib.escape
        ico = '<svg class="ico" aria-hidden="true"><use href="#i-warn"/></svg>' if n['level'] in ('critical', 'warning') else ''
        link_text = 'Details on gl-i.net' if n['kind'] == 'advisory' else 'Details'
        rows.append(f'<p class="notice {n["level"]}">{ico}<b>{e(label(n))}:</b> {e(n["text"])}'
                    f'<a href="{e(n["url"], quote=True)}">{link_text}&nbsp;&#8594;</a></p>')
    return '<aside class="notices" aria-label="Notices from gl-i.net">\n' + '\n'.join(rows) + '\n</aside>\n'


def notices_text(width=78):
    """The notices as a plain-text block for the top of a text page; empty without notices."""
    lines = []
    for n in _current:
        mark = '!! ' if n['level'] in ('critical', 'warning') else '-- '
        head = label(n).upper() + (f"  {n['id']}" if n['id'] else '')
        lines.append(mark + head)
        lines += [mark + line for line in textwrap.wrap(n['text'], width - len(mark))]
        lines += [mark + n['url'], '']
    return '\n'.join(lines) + '\n' if lines else ''


def with_notices(text):
    """Prefix a text page with the notices block."""
    return notices_text() + text


def write_notices_api(api_dir='api'):
    """api/notices (level, id, updated, url, text; tab-separated, no header) and
    api/notices.json. Both are written even when empty, so scripts get a file, not a 404."""
    with open(os.path.join(api_dir, 'notices'), 'w', encoding='utf-8') as f:
        for n in _current:
            f.write('\t'.join([n['level'], n['id'], n['updated'], n['url'], n['text']]) + '\n')
    with open(os.path.join(api_dir, 'notices.json'), 'w', encoding='utf-8') as f:
        json.dump({'source': NOTICES_URL, 'notices': _current}, f, indent=2, ensure_ascii=False)
