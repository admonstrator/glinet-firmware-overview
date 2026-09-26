"""Atom feeds: /feed.xml (all devices) and /<model>/feed.xml (one device)."""
import os
from xml.sax.saxutils import escape as xml_escape

from sitelib.core import *  # noqa: F401,F403


def generate_feeds(models, models_metadata, generated_at):
    """Write the global feed and one feed per device. Returns the number of feed files written.
    Placeholder until the feeds agent fills it."""
    return 0
