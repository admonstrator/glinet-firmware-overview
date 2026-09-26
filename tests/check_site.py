"""Check a rendered site for broken links, broken markup, external assets and malformed feeds.

    python3 tests/check_site.py DIR [--no-external-assets]

Checks:
  * every relative href/src in HTML (a, link, img, script, meta refresh) resolves to a file or to
    a directory with index.html; fragments must exist in the target page
  * HTML tags are balanced (void elements excepted)
  * every `curl https://firmware.gl-i.net/...` target in a .txt page exists
  * every *.xml file parses; Atom feeds have id, title, updated and entries with id/title/updated/link
  * with --no-external-assets: no stylesheet, script, image or font is loaded from another host
Exit code 1 when a problem was found.
"""
import os
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

SITE_HOST = 'https://firmware.gl-i.net/'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
ATOM = '{http://www.w3.org/2005/Atom}'


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.ids, self.stack, self.errors, self.external = [], set(), [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            self.ids.add(a['id'])
        if tag == 'a' and a.get('name'):
            self.ids.add(a['name'])
        if tag == 'a' and a.get('href'):
            self.refs.append(a['href'])
        if tag == 'link' and a.get('href'):
            rel = (a.get('rel') or '').lower()
            if rel != 'canonical':
                self.refs.append(a['href'])
            if rel in ('stylesheet', 'preload', 'icon') and a['href'].startswith(('http://', 'https://', '//')):
                self.external.append(a['href'])
        if tag in ('img', 'script', 'iframe', 'source') and a.get('src'):
            self.refs.append(a['src'])
            if a['src'].startswith(('http://', 'https://', '//')):
                self.external.append(a['src'])
        if tag == 'meta' and (a.get('http-equiv') or '').lower() == 'refresh' and 'url=' in (a.get('content') or ''):
            self.refs.append(a['content'].split('url=', 1)[1].strip())
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1][0] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            self.errors.append(f'unexpected </{tag}> at line {self.getpos()[0]} (open: {[t for t, _ in self.stack[-3:]]})')


_page_cache = {}


def parse_page(path):
    if path not in _page_cache:
        p = Page()
        with open(path, encoding='utf-8') as f:
            p.feed(f.read())
        p.close()
        _page_cache[path] = p
    return _page_cache[path]


def resolve(base_dir, target, root):
    """Local file for a relative or site-absolute reference, or None when it is external."""
    if target.startswith(SITE_HOST):
        rel = target[len(SITE_HOST):]
        path = os.path.join(root, rel)
    elif target.startswith(('http://', 'https://', 'mailto:', '//', 'data:', 'tag:')):
        return None
    else:
        path = os.path.join(base_dir, target)
    return os.path.normpath(path)


def existing(path, prefer=('index.html',)):
    if os.path.isfile(path):
        return path
    if os.path.isdir(path):
        for name in prefer:
            if os.path.isfile(os.path.join(path, name)):
                return os.path.join(path, name)
    return None


def check(root, no_external_assets=False):
    """Return a list of problem strings (empty when the site is fine)."""
    root = os.path.abspath(root)
    _page_cache.clear()
    problems = []
    for dirpath, _, files in os.walk(root):
        for name in files:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if name.endswith('.html'):
                page = parse_page(path)
                problems += [f'{rel}: {e}' for e in page.errors]
                if page.stack:
                    problems.append(f'{rel}: unclosed tags {[t for t, _ in page.stack[-5:]]}')
                if no_external_assets:
                    problems += [f'{rel}: external asset {u}' for u in page.external]
                for ref in page.refs:
                    target, _, frag = ref.partition('#')
                    if not target:
                        if frag and frag not in page.ids:
                            problems.append(f'{rel}: missing anchor #{frag}')
                        continue
                    local = resolve(dirpath, target, root)
                    if local is None:
                        continue
                    found = existing(local)
                    if not found:
                        problems.append(f'{rel}: broken link {ref}')
                    elif frag and found.endswith('.html') and frag not in parse_page(found).ids:
                        problems.append(f'{rel}: missing anchor {ref}')
            elif name.endswith('.txt'):
                with open(path, encoding='utf-8') as f:
                    text = f.read()
                for url in re.findall(r'curl (?:-\S+ )*(https://firmware\.gl-i\.net/[^\s)|]*)', text):
                    if '<' in url:
                        continue
                    local = resolve(dirpath, url.rstrip('/') or SITE_HOST, root) if url.rstrip('/') != SITE_HOST.rstrip('/') else root
                    if not existing(local, prefer=('index.txt', 'index.html')):
                        problems.append(f'{rel}: curl target missing {url}')
            elif name.endswith('.xml'):
                try:
                    tree = ET.parse(path)
                except ET.ParseError as e:
                    problems.append(f'{rel}: XML parse error {e}')
                    continue
                feed = tree.getroot()
                if feed.tag == f'{ATOM}feed':
                    for tag in ('id', 'title', 'updated'):
                        if feed.find(f'{ATOM}{tag}') is None:
                            problems.append(f'{rel}: feed without <{tag}>')
                    for i, entry in enumerate(feed.findall(f'{ATOM}entry')):
                        for tag in ('id', 'title', 'updated', 'link'):
                            if entry.find(f'{ATOM}{tag}') is None:
                                problems.append(f'{rel}: entry {i} without <{tag}>')
                        for link in entry.findall(f'{ATOM}link'):
                            href = link.get('href', '')
                            local = resolve(dirpath, href, root)
                            if local is not None and not existing(local):
                                problems.append(f'{rel}: entry {i} links to missing {href}')
    return problems


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1:
        sys.exit(__doc__)
    found = check(args[0], no_external_assets='--no-external-assets' in sys.argv)
    for p in found:
        print(p)
    print(f'{len(found)} problem(s)')
    sys.exit(1 if found else 0)
