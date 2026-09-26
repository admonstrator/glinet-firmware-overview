"""Atom 1.0 feeds: /feed.xml (newest builds of all devices) and /<model>/feed.xml (one device).

Global feed: the newest GLOBAL_FEED_LIMIT builds across all devices, every stage except
RECENT_EXCLUDED_STAGES (snapshots appear too often). Device feed: every stage of one device,
snapshots included. One entry per build; the entry id stays the same as long as the version does.
"""
import os
import re
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape

from sitelib.core import *  # noqa: F401,F403

# Changelogs longer than this are shortened in the feed (at a line break) and link the full text.
CHANGELOG_LIMIT = 2000

# Characters XML 1.0 does not allow at all; GL.iNet changelogs occasionally carry control characters.
_XML_INVALID = re.compile('[^\t\n\r -퟿-�\U00010000-\U0010ffff]')


def _text(value):
    """Escape a value for XML element content."""
    return xml_escape(_XML_INVALID.sub('', str(value)))


def _attr(value):
    """Escape a value for a double-quoted XML attribute."""
    return xml_escape(_XML_INVALID.sub('', str(value)), {'"': '&quot;'})


def atom_time(release_time):
    """'2026-09-20 18:00:48' -> '2026-09-20T18:00:48Z' (RFC 3339), a bare date gets midnight,
    None when the value is empty or unreadable.

    GL.iNet does not document the timezone of release_time; the feeds publish it as UTC ('Z')
    so every entry carries a valid, sortable timestamp."""
    value = (release_time or '').strip()
    for fmt, size in (('%Y-%m-%d %H:%M:%S', 19), ('%Y-%m-%d', 10)):
        try:
            return datetime.strptime(value[:size], fmt).strftime('%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            continue
    return None


def display_name(code, name):
    """'Beryl AX (GL-MT3000)' for 'GL-MT3000 Beryl AX'; names without a nickname stay whole."""
    nick, sku = split_name(name, code)
    return f'{nick} ({sku})' if sku else nick


def build_page_url(code, stage):
    """Absolute browser URL of one build, or the overview for model codes without a device page.

    /<model>/<stage>/ is the stage directory: curl gets its index.txt, browsers get a stub that
    redirects to the stage block /<model>/#<stage> of the device page. The feed links the stage
    directory rather than the #fragment URL because tests/check_site.py resolves feed links as
    files and does not strip fragments."""
    page = device_page_url(code)
    if page is None:
        return f'{SITE_URL}/'
    return f'{SITE_URL}/{page}{api_stage_name(stage)}/'


def shorten_changelog(text, limit=CHANGELOG_LIMIT):
    """(text, shortened): cut after the last line break before `limit` characters."""
    text = (text or '').strip()
    if len(text) <= limit:
        return text, False
    cut = text.rfind('\n', 0, limit)
    if cut < limit // 2:
        cut = text.rfind(' ', 0, limit)
    if cut < limit // 2:
        cut = limit
    return text[:cut].rstrip(), True


def entry_content(code, stage, entry):
    """Plain-text entry body: version, date, download, then the (possibly shortened) changelog."""
    s_api = api_stage_name(stage)
    link = entry_link(entry)
    md5_hash = (entry.get('download') or [{}])[0].get('md5', '') or ''
    lines = [f"Version: {entry.get('version', 'N/A')}",
             f"Released: {entry.get('release_time') or 'unknown'} (as published by GL.iNet)",
             f"Download: {link or 'none published'}"]
    if md5_hash:
        lines.append(f'MD5: {md5_hash}')
    if not entry.get('_link_ok', True):
        reason = entry.get('_link_reason') or 'no response'
        lines.append(f'Link check: this download did not respond in the last check ({reason}); the version stays listed.')
        if entry.get('_fallback_link'):
            fb_date = (entry.get('_fallback_release_time') or '')[:10]
            fb_when = f' (released {fb_date})' if fb_date else ''
            lines.append(f"Fallback: the related download of this entry is {entry.get('_fallback_version', 'N/A')}{fb_when}, "
                         f"the newest build whose download responds: {entry['_fallback_link']}")
    changelog, shortened = shorten_changelog(entry.get('changelog'))
    full_url = f'{SITE_URL}/api/{code.lower()}/{s_api}/changelog'
    lines += ['', 'Changelog:', changelog or '(no changelog published for this build)']
    if shortened:
        lines += ['[...]', f'Full changelog: {full_url}']
    return '\n'.join(lines)


def feed_entry(code, name, stage, entry, fallback_updated):
    """One <entry> element as a string (indented for a <feed> child)."""
    version = entry.get('version', 'N/A')
    title = f'{display_name(code, name)}: {stage_title(stage, entry)} {version}'
    updated = atom_time(entry.get('release_time')) or fallback_updated
    download = entry_link(entry)
    if not entry.get('_link_ok', True) and entry.get('_fallback_link'):
        download = entry['_fallback_link']
    parts = [
        '  <entry>',
        f'    <id>{_text(feed_entry_id(code, stage, version))}</id>',
        f'    <title>{_text(title)}</title>',
        f'    <updated>{updated}</updated>',
        f'    <published>{updated}</published>',
        f'    <link rel="alternate" type="text/html" href="{_attr(build_page_url(code, stage))}"/>',
    ]
    if download:
        parts.append(f'    <link rel="related" href="{_attr(download)}"/>')
    parts += [
        f'    <category term="{_attr(api_stage_name(stage))}" label="{_attr(stage_title(stage, entry))}"/>',
        f'    <content type="text">{_text(entry_content(code, stage, entry))}</content>',
        '  </entry>',
    ]
    return '\n'.join(parts)


def atom_feed(feed_id, title, subtitle, alternate_url, builds, fallback_updated):
    """A complete Atom document. `builds` are dicts {code, name, stage, entry}, newest first."""
    entries = [feed_entry(b['code'], b['name'], b['stage'], b['entry'], fallback_updated) for b in builds]
    stamps = [atom_time(b['entry'].get('release_time')) for b in builds]
    updated = max((s for s in stamps if s), default=fallback_updated)
    head = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">',
        f'  <id>{_text(feed_id)}</id>',
        f'  <title>{_text(title)}</title>',
        f'  <subtitle>{_text(subtitle)}</subtitle>',
        f'  <updated>{updated}</updated>',
        f'  <link rel="self" type="application/atom+xml" href="{_attr(feed_id)}"/>',
        f'  <link rel="alternate" type="text/html" href="{_attr(alternate_url)}"/>',
        f'  <author><name>admon</name><uri>{_text(AUTHOR_URL)}</uri></author>',
        f'  <generator uri="{_attr(GITHUB_URL)}">glinet-firmware-overview</generator>',
        f'  <icon>{_text(SITE_URL)}/images/favicon-192.png</icon>',
    ]
    return '\n'.join(head + entries + ['</feed>', ''])


def generate_global_feed(models, models_metadata, generated_at):
    fallback = parse_generated_at(generated_at).strftime('%Y-%m-%dT%H:%M:%SZ')
    builds = builds_newest_first(models, models_metadata, exclude=RECENT_EXCLUDED_STAGES)[:GLOBAL_FEED_LIMIT]
    excluded = ', '.join(api_stage_name(s) for s in sorted(RECENT_EXCLUDED_STAGES)) or 'none'
    subtitle = (f'Unofficial community feed, not affiliated with GL.iNet: the newest {GLOBAL_FEED_LIMIT} '
                f'firmware builds of all GL.iNet devices (excluded stages: {excluded}).')
    return atom_feed(feed_url(absolute=True), f'{SITE_NAME} (unofficial)', subtitle, f'{SITE_URL}/', builds, fallback)


def generate_device_feed(code, stages, meta, generated_at):
    fallback = parse_generated_at(generated_at).strftime('%Y-%m-%dT%H:%M:%SZ')
    name = meta.get('name', code)
    builds = builds_newest_first({code: stages}, {code: meta})
    subtitle = (f'Unofficial community feed, not affiliated with GL.iNet: every firmware build '
                f'of the GL.iNet {name}, all stages including snapshots.')
    return atom_feed(feed_url(code, absolute=True), f'{display_name(code, name)} firmware (unofficial)', subtitle,
                     f'{SITE_URL}/{device_page_url(code)}', builds, fallback)


def generate_feeds(models, models_metadata, generated_at):
    """Write the global feed and one feed per device. Returns the number of feed files written."""
    with open(FEED_FILE, 'w', encoding='utf-8') as f:
        f.write(generate_global_feed(models, models_metadata, generated_at))
    written = 1
    for code, stages in models.items():
        if device_page_url(code) is None:
            continue
        os.makedirs(code.lower(), exist_ok=True)
        with open(feed_url(code), 'w', encoding='utf-8') as f:
            f.write(generate_device_feed(code, stages, models_metadata.get(code, {}), generated_at))
        written += 1
    return written
