"""Atom feeds: /feed.xml (all devices) and /<model>/feed.xml (one device)."""
import os
from xml.sax.saxutils import escape as xml_escape

from sitelib.core import *  # noqa: F401,F403


def _empty_feed(feed_id, title, self_url, alternate_url, updated):
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom">\n'
            f'  <id>{xml_escape(feed_id)}</id>\n  <title>{xml_escape(title)}</title>\n  <updated>{updated}</updated>\n'
            f'  <link rel="self" href="{xml_escape(self_url)}"/>\n  <link rel="alternate" href="{xml_escape(alternate_url)}"/>\n'
            '</feed>\n')


def generate_feeds(models, models_metadata, generated_at):
    """Write the global feed and one feed per device. Returns the number of feed files written.
    Placeholder: valid Atom documents without entries, until the feeds agent fills them."""
    updated = parse_generated_at(generated_at).strftime('%Y-%m-%dT%H:%M:%SZ')
    with open(FEED_FILE, 'w', encoding='utf-8') as f:
        f.write(_empty_feed(feed_url(absolute=True), f'{SITE_NAME} (unofficial)', feed_url(absolute=True), f'{SITE_URL}/', updated))
    written = 1
    for code in models:
        if device_page_url(code) is None:
            continue
        os.makedirs(code.lower(), exist_ok=True)
        with open(feed_url(code), 'w', encoding='utf-8') as f:
            f.write(_empty_feed(feed_url(code, absolute=True), models_metadata.get(code, {}).get('name', code),
                                feed_url(code, absolute=True), f'{SITE_URL}/{device_page_url(code)}', updated))
        written += 1
    return written
