"""Has gl-i.net changed its notices since the last build of this site?

    python3 check_notices.py

Run every 30 minutes by .github/workflows/notices_watch.yml. Compares the
notices gl-i.net publishes now (https://gl-i.net/notices.json) with the ones
this site currently shows (/api/notices.json, written by the last build), both
read through sitelib.notices.parse_notices, so an expired notice counts as a
change and a whitespace difference does not.

Prints the result and writes `changed=true|false` to $GITHUB_OUTPUT. When
gl-i.net cannot be read the answer is false: an outage there must not start a
build that would drop the banner.
"""
import json
import os
import time
import urllib.request

from sitelib.core import SITE_URL
from sitelib.notices import NOTICES_URL, parse_notices

TIMEOUT = 15


def load(url):
    """JSON document at `url`, or None on any error."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'glinet-firmware-overview notices check',
                                                   'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Could not read {url}: {type(e).__name__}: {e}")
        return None


def fingerprint(notices):
    """What a page shows of each notice, order included."""
    return [(n['level'], n['id'], n['updated'], n['url'], n['text']) for n in notices]


def changed(source, live, now=None):
    """True when the notices from gl-i.net (`source`) differ from the ones on this site (`live`).
    False when gl-i.net could not be read; True when this site has no notices file yet."""
    if source is None:
        return False
    if live is None:
        return True
    return fingerprint(parse_notices(source, now)) != fingerprint(parse_notices(live, now))


def main():
    source = load(NOTICES_URL)
    # The query string gets past caches in front of the site
    live = load(f"{SITE_URL}/api/notices.json?t={int(time.time())}")
    result = changed(source, live)
    print(f"gl-i.net: {len(parse_notices(source)) if source else '?'} notice(s), "
          f"this site: {len(parse_notices(live)) if live else '?'} notice(s), changed: {str(result).lower()}")
    out = os.environ.get('GITHUB_OUTPUT')
    if out:
        with open(out, 'a', encoding='utf-8') as f:
            f.write(f"changed={str(result).lower()}\n")


if __name__ == '__main__':
    main()
