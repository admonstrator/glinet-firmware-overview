"""Shared page frame of the new design: tokens and base CSS, icon sprite, <head>, header band, footer.

Part of the phase contract. Renderers build pages as

    page_head(...) + site_header(...) + <main ...>...</main> + site_footer(root) + '</body>\n</html>\n'

and put page-specific CSS into their own module (pass it as `extra_css`). The design is plain
HTML and CSS: no framework, no CDN, no web fonts, no JavaScript required.
"""
import html as html_lib

from sitelib.core import (AUTHOR_URL, DOCS_DIR, FORUM_URL, GITHUB_URL, OG_IMAGE_PATH, OG_IMAGE_SIZE,
                          SITE_NAME, SITE_URL, SPONSOR_URL)

THEME_COLOR_NEW = '#12344D'
UNOFFICIAL_NOTE = 'Unofficial community project, not affiliated with GL.iNet'

DESIGN_CSS = """
:root {
  color-scheme: light dark;
  --ice: #F3F6F8; --paper: #FFFFFF; --deep: #12344D; --deep-2: #1B4A6B; --on-deep: #E8F1F7; --on-deep-2: #A9C3D6;
  --ink: #1D2A33; --muted: #5B6B77; --line: #DCE3E8; --frost: #C9D1D6;
  --blush: #E8838F; --blush-ink: #5E1F29; --focus: #1F5FBF;
  --release: #1E7A46; --beta: #1F5FBF; --snapshot: #0B7285; --rc: #B35900; --other: #6B4FA0;
  --display: ui-rounded, "SF Pro Rounded", "Nunito", system-ui, sans-serif;
  --text: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  --code: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --ice: #0D1A22; --paper: #13232D; --deep: #081E2D; --deep-2: #0F2E44; --on-deep: #E3EEF5; --on-deep-2: #8FB0C6;
    --ink: #E1EAF0; --muted: #98A9B5; --line: #223542; --frost: #3A4E5B;
    --blush-ink: #3B1017; --focus: #7FB0FF;
    --release: #5CCB8A; --beta: #7FB0FF; --snapshot: #5FD0DE; --rc: #FFB26B; --other: #B9A2F0;
  }
}
* { box-sizing: border-box; }
html { background: var(--ice); scrollbar-color: var(--frost) transparent; }
body { margin: 0; font: 15px/1.5 var(--text); color: var(--ink); background: var(--ice); font-variant-numeric: tabular-nums; }
a { color: inherit; }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; border-radius: 4px; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 0 24px; }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.ico { width: 15px; height: 15px; vertical-align: -2px; flex: none; }

/* Header band */
.floe { background: linear-gradient(180deg, var(--deep) 0%, var(--deep-2) 100%); color: var(--on-deep); position: relative; }
.floe .wrap { position: relative; padding-top: 30px; padding-bottom: 32px; }
.floe h1 { font: 700 clamp(26px, 3.4vw, 38px)/1.1 var(--display); letter-spacing: -0.01em; margin: 0 0 8px; }
.floe h1 a { text-decoration: none; }
.floe .lead { margin: 0 0 16px; color: var(--on-deep-2); max-width: 60ch; font-size: 16px; }
.unofficial { display: inline-flex; gap: 8px; align-items: center; margin: 0; padding: 6px 12px 6px 10px; border-radius: 999px;
  background: var(--blush); color: var(--blush-ink); font-weight: 600; font-size: 13.5px; }
.unofficial::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--blush-ink); opacity: .55; }
.sitenav { position: absolute; right: 24px; top: 26px; display: flex; gap: 6px; align-items: center; margin: 0; padding: 0; list-style: none; font-size: 14px; }
.sitenav a { display: inline-flex; gap: 7px; align-items: center; padding: 6px 11px; border-radius: 9px; color: var(--on-deep-2); text-decoration: none; }
.sitenav a:hover, .sitenav a[aria-current] { color: var(--on-deep); background: rgba(255, 255, 255, .08); }
.sitenav .api { color: var(--on-deep); border: 1px solid rgba(255, 255, 255, .28); font-weight: 600; }
.sitenav .api:hover { border-color: rgba(255, 255, 255, .5); }
.floe h1, .floe .lead, .floe .crumbs { margin-right: 330px; }

/* Toolbar */
.toolbar { display: flex; flex-wrap: wrap; gap: 12px 20px; align-items: center; padding-top: 24px; padding-bottom: 14px; }
.search { position: relative; flex: 1 1 260px; max-width: 360px; }
.search[hidden] { display: none; }
.find-hint { margin: 0; font-size: 13.5px; color: var(--muted); }
.search .ico { position: absolute; left: 11px; top: 50%; transform: translateY(-50%); color: var(--muted); }
.search input { width: 100%; font: inherit; padding: 8px 12px 8px 34px; border-radius: 10px; border: 1px solid var(--line); background: var(--paper); color: var(--ink); }
.filters { display: inline-flex; padding: 3px; border-radius: 12px; background: var(--paper); border: 1px solid var(--line); }
.filters input { position: absolute; opacity: 0; pointer-events: none; }
.filters label { padding: 5px 12px; border-radius: 9px; cursor: pointer; font-weight: 500; color: var(--muted); user-select: none; }
.filters label span { font-size: 12.5px; margin-left: 4px; opacity: .8; }
.filters input:checked + label { background: var(--deep); color: var(--on-deep); }
.filters input:focus-visible + label { outline: 2px solid var(--focus); outline-offset: 1px; }
.status { margin-left: auto; display: flex; gap: 16px; font-size: 13.5px; color: var(--muted); }
.status a { display: inline-flex; gap: 6px; align-items: center; text-decoration: none; color: var(--release); font-weight: 500; }
.status a:hover { text-decoration: underline; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 13px; color: var(--muted); padding-bottom: 18px; }
.legend > span { display: inline-flex; align-items: center; gap: 6px; }

/* Category filter without JavaScript */
body:has(#f-router:checked) .cat:not(#router),
body:has(#f-iot:checked) .cat:not(#iot),
body:has(#f-kvm:checked) .cat:not(#kvm) { display: none; }

/* Tables */
.cat { margin-bottom: 34px; }
.cat h2 { font: 600 19px/1.2 var(--display); margin: 0 0 10px; display: flex; gap: 10px; align-items: baseline; }
.cat h2 small { font: 500 13px var(--text); color: var(--muted); }
.sheet { background: var(--paper); border: 1px solid var(--line); border-radius: 14px; }
table { width: 100%; border-collapse: separate; border-spacing: 0; }
thead th { position: sticky; top: 0; z-index: 1; background: var(--paper); text-align: left; font-weight: 600; font-size: 13px; color: var(--muted);
  padding: 11px 12px 9px; border-bottom: 1px solid var(--line); }
thead th:first-child { border-top-left-radius: 14px; } thead th:last-child { border-top-right-radius: 14px; }
tbody th, tbody td { padding: 10px 12px; border-bottom: 1px solid var(--line); vertical-align: top; text-align: left; }
tbody tr:last-child > * { border-bottom: 0; }
tbody tr:hover > * { background: color-mix(in srgb, var(--ice) 60%, var(--paper)); }
.model { min-width: 170px; font-weight: 400; }
.model a { text-decoration: none; display: block; }
.model .nick { font-weight: 650; font-size: 15.5px; }
.model a:hover .nick { text-decoration: underline; text-underline-offset: 3px; }
.model .sku { display: block; font-size: 12.5px; color: var(--muted); }
td.empty::after { content: ""; display: inline-block; width: 14px; height: 2px; border-radius: 2px; background: var(--frost); vertical-align: middle; }
.build { white-space: nowrap; }
.build + .build { margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--line); }
.ver { display: inline-flex; gap: 5px; align-items: center; font-weight: 650; text-decoration: none; font-size: 15px; }
.ver:hover { text-decoration: underline; text-underline-offset: 3px; }
.ver.release { color: var(--release); } .ver.beta { color: var(--beta); } .ver.snapshot { color: var(--snapshot); } .ver.rc { color: var(--rc); } .ver.other { color: var(--other); }
.meta { display: flex; gap: 8px; align-items: center; font-size: 12.5px; color: var(--muted); margin-top: 1px; white-space: nowrap; }
.meta a { display: inline-flex; color: var(--muted); } .meta a:hover { color: var(--ink); }
.tag { font-size: 11px; font-weight: 650; padding: 1px 6px; border-radius: 6px; line-height: 1.5; }
.tag.fresh { background: color-mix(in srgb, var(--release) 16%, transparent); color: var(--release); }
.tag.op { background: color-mix(in srgb, var(--frost) 55%, transparent); color: var(--ink); }
.nomatch { display: none; padding: 30px 0; color: var(--muted); }

/* Footer */
footer { margin-top: 18px; border-top: 1px solid var(--line); padding: 26px 0 40px; color: var(--muted); font-size: 14px; }
footer .cols { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr); gap: 28px; }
footer h2 { font: 600 16px var(--display); color: var(--ink); margin: 0 0 8px; }
footer p { margin: 0 0 10px; max-width: 68ch; }
footer details { background: var(--paper); border: 1px solid var(--line); border-radius: 12px; padding: 12px 16px; margin-bottom: 10px; }
footer summary { cursor: pointer; color: var(--ink); font-weight: 600; }
footer pre { font: 12.5px/1.6 var(--code); color: var(--ink); background: var(--ice); padding: 10px 12px; border-radius: 8px; overflow-x: auto; margin: 10px 0 4px; }
footer .links { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 6px; }

/* API & terminal page */
.doc { max-width: 860px; padding-top: 28px; padding-bottom: 10px; }
.doc h2 { font: 650 21px/1.25 var(--display); margin: 34px 0 8px; }
.doc h2:first-child { margin-top: 0; }
.doc p { max-width: 70ch; margin: 0 0 12px; }
.doc code { font: 13.5px var(--code); background: var(--paper); border: 1px solid var(--line); border-radius: 6px; padding: 1px 5px; }
.doc pre { font: 13.5px/1.65 var(--code); background: var(--deep); color: var(--on-deep); padding: 14px 18px; border-radius: 12px; overflow-x: auto; margin: 0 0 14px; }
.doc pre .c { color: var(--on-deep-2); }
.doc table { background: var(--paper); border: 1px solid var(--line); border-radius: 14px; border-spacing: 0; margin: 4px 0 14px; font-size: 14px; }
.doc th, .doc td { text-align: left; vertical-align: top; padding: 9px 14px; border-bottom: 1px solid var(--line); }
.doc thead th { position: static; font-size: 13px; color: var(--muted); font-weight: 600; }
.doc tbody tr:last-child > * { border-bottom: 0; }
.doc td code, .doc th code { border: 0; background: none; padding: 0; }
.doc .out { color: var(--muted); font: 13px var(--code); white-space: pre-wrap; word-break: break-all; }
.codes { columns: 3 220px; column-gap: 24px; margin: 6px 0 14px; padding: 0; list-style: none; font-size: 14px; }
.codes li { break-inside: avoid; padding: 2px 0; }
.codes code { display: inline-block; min-width: 88px; }
.jump { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 14px; margin: 0 0 6px; }

/* Device page */
.crumbs { font-size: 13.5px; color: var(--on-deep-2); margin: 0 0 10px; display: flex; gap: 8px; flex-wrap: wrap; }
.crumbs a { color: var(--on-deep); text-decoration: none; } .crumbs a:hover { text-decoration: underline; }
.crumbs span[aria-hidden] { opacity: .6; }
.sku-line { font: 500 15px var(--text); color: var(--on-deep-2); margin: -2px 0 14px; }
.builds { display: grid; gap: 12px; padding-top: 30px; }
.buildcard { background: var(--paper); border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; }
.buildcard .row { display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; }
.buildcard .stage { font: 650 15px var(--display); min-width: 90px; }
.buildcard .stage.release { color: var(--release); } .buildcard .stage.beta { color: var(--beta); } .buildcard .stage.snapshot { color: var(--snapshot); } .buildcard .stage.other { color: var(--other); }
.buildcard .v { font-weight: 700; font-size: 20px; }
.buildcard .d { color: var(--muted); font-size: 13.5px; }
.btn { margin-left: auto; display: inline-flex; gap: 7px; align-items: center; padding: 7px 14px; border-radius: 10px; background: var(--deep); color: var(--on-deep);
  text-decoration: none; font-weight: 600; font-size: 14px; }
.btn:hover { background: var(--deep-2); }
.buildcard details { margin-top: 10px; }
.buildcard summary { cursor: pointer; color: var(--muted); font-size: 14px; }
.buildcard summary:hover { color: var(--ink); }
.buildcard pre { white-space: pre-wrap; font: 13.5px/1.6 var(--text); background: var(--ice); padding: 12px 14px; border-radius: 10px; margin: 10px 0 0; max-height: 420px; overflow: auto; }

@media (max-width: 600px) {
  .legend { display: none; }
}
@media (max-width: 960px) {
  .floe .wrap { padding-bottom: 26px; }
  .sitenav { position: static; flex-wrap: wrap; margin: 14px 0 0 -11px; }
  .floe h1, .floe .lead, .floe .crumbs { margin-right: 0; }
  .floe .wrap { display: flex; flex-direction: column; }
  .sitenav { order: 10; }
  .status { margin-left: 0; flex-wrap: wrap; }

  thead { display: none; }
  table, tbody, tr, tbody th, tbody td { display: block; }
  tbody tr { padding: 12px 14px; border-bottom: 1px solid var(--line); display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px 14px; }
  tbody tr:last-child { border-bottom: 0; }
  tbody th, tbody td { padding: 0; border: 0; }
  tbody .model { grid-column: 1 / -1; min-width: 0; }
  tbody td::before { content: attr(data-stage); display: block; font-size: 12px; color: var(--muted); }
  td.empty { display: none; }
  tbody tr:hover > * { background: none; }
  footer .cols { grid-template-columns: 1fr; }
  .btn { margin-left: 0; }
}
"""

ICON_SPRITE = """<svg xmlns="http://www.w3.org/2000/svg" style="display:none">
  <symbol id="i-dl" viewBox="0 0 16 16"><path d="M8 1.5v8m0 0L4.8 6.3M8 9.5l3.2-3.2M2.5 11v2.5h11V11" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></symbol>
  <symbol id="i-notes" viewBox="0 0 16 16"><path d="M4 1.5h5.5L12.5 4.5v10h-8.5zM9.5 1.5v3h3M6 8h4.5M6 10.5h4.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></symbol>
  <symbol id="i-ok" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M5 8.2l2 2 4-4.4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></symbol>
  <symbol id="i-warn" viewBox="0 0 16 16"><path d="M8 1.8l6.5 12H1.5zM8 6.3v3.4M8 11.6v.2" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/></symbol>
  <symbol id="i-code" viewBox="0 0 16 16"><path d="M2 3.5h12v9H2zM4.5 6.5l2 1.5-2 1.5M8 10h3.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></symbol>
  <symbol id="i-search" viewBox="0 0 16 16"><circle cx="7" cy="7" r="4.8" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M10.6 10.6l3.4 3.4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></symbol>
  <symbol id="i-feed" viewBox="0 0 16 16"><path d="M3 2.5a10.5 10.5 0 0 1 10.5 10.5M3 6.5A6.5 6.5 0 0 1 9.5 13" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="3.6" cy="12.4" r="1.4" fill="currentColor"/></symbol>
</svg>"""


def icon(name, cls='ico'):
    """Inline SVG icon from the sprite: dl, notes, ok, warn, search, code, feed."""
    return f'<svg class="{cls}" aria-hidden="true"><use href="#i-{name}"/></svg>'


def page_head(title, description='', canonical='', root='', feeds=(), extra_css='', noindex=False):
    """<!DOCTYPE> up to and including <body> and the icon sprite.
    `root` is the relative path to the site root ('' or '../' or '../../').
    `feeds` is a sequence of (title, href) for <link rel="alternate" type="application/atom+xml">."""
    t = html_lib.escape(title, quote=True)
    d = html_lib.escape(description, quote=True)
    og_image = f"{SITE_URL}/{OG_IMAGE_PATH}"
    lines = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="color-scheme" content="light dark">',
        f'<meta name="theme-color" content="{THEME_COLOR_NEW}">',
        f'<title>{t}</title>',
    ]
    if d:
        lines += [f'<meta name="description" content="{d}">', f'<meta property="og:description" content="{d}">',
                  f'<meta name="twitter:description" content="{d}">']
    if canonical:
        lines += [f'<link rel="canonical" href="{canonical}">', f'<meta property="og:url" content="{canonical}">']
    if noindex:
        lines.append('<meta name="robots" content="noindex">')
    lines += [
        f'<meta property="og:site_name" content="{SITE_NAME} (unofficial)">',
        f'<meta property="og:title" content="{t}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:image" content="{og_image}">',
        f'<meta property="og:image:width" content="{OG_IMAGE_SIZE[0]}">',
        f'<meta property="og:image:height" content="{OG_IMAGE_SIZE[1]}">',
        f'<meta property="og:image:alt" content="{SITE_NAME}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{t}">',
        f'<meta name="twitter:image" content="{og_image}">',
        f'<link rel="icon" href="{root}favicon.ico" sizes="any">',
        f'<link rel="icon" type="image/png" sizes="32x32" href="{root}images/favicon-32.png">',
        f'<link rel="icon" type="image/png" sizes="192x192" href="{root}images/favicon-192.png">',
        f'<link rel="apple-touch-icon" sizes="180x180" href="{root}images/apple-touch-icon.png">',
    ]
    for feed_title, href in feeds:
        lines.append(f'<link rel="alternate" type="application/atom+xml" title="{html_lib.escape(feed_title, quote=True)}" href="{href}">')
    lines.append(f'<style>{DESIGN_CSS}{extra_css}</style>')
    lines += ['</head>', '<body>', ICON_SPRITE]
    return '\n'.join(lines) + '\n'


def site_nav(root, current=''):
    """Header navigation. `current` is 'docs', 'status' or ''."""
    items = [
        (f'{root}{DOCS_DIR}/', 'API &amp; terminal', 'docs', icon('code'), ' class="api"'),
        (f'{root}status.html', 'Link status', 'status', '', ''),
        (GITHUB_URL, 'GitHub', 'github', '', ''),
    ]
    lis = []
    for href, label, key, ico, cls in items:
        cur = ' aria-current="page"' if key == current else ''
        lis.append(f'<li><a href="{href}"{cls}{cur}>{ico}{label}</a></li>')
    return f'<ul class="sitenav" aria-label="Site">{"".join(lis)}</ul>'


def site_header(root, title, lead='', crumbs=(), sku='', current='', extra=''):
    """The deep-blue header band: navigation, optional breadcrumbs, title, optional model line,
    optional lead sentence, the unofficial note and optional extra HTML.
    `crumbs` is a sequence of (label, href); the last one may have href None (current page).
    `lead`, `sku` and `extra` are HTML (escape text yourself); `title` is plain text."""
    parts = ['<header class="floe">', '  <div class="wrap">', f'    {site_nav(root, current)}']
    if crumbs:
        items = []
        for i, (label, href) in enumerate(crumbs):
            if i:
                items.append('<span aria-hidden="true">/</span>')
            if href:
                items.append(f'<a href="{href}">{html_lib.escape(label)}</a>')
            else:
                items.append(f'<span aria-current="page">{html_lib.escape(label)}</span>')
        parts.append(f'    <nav class="crumbs" aria-label="Breadcrumb">{"".join(items)}</nav>')
    parts.append(f'    <h1>{html_lib.escape(title)}</h1>')
    if sku:
        parts.append(f'    <p class="sku-line">{sku}</p>')
    if lead:
        parts.append(f'    <p class="lead">{lead}</p>')
    parts.append(f'    <p class="unofficial">{UNOFFICIAL_NOTE}</p>')
    if extra:
        parts.append(f'    {extra}')
    parts += ['  </div>', '</header>']
    return '\n'.join(parts) + '\n'


def site_footer(root, example_model='mt3000'):
    """Footer with the disclaimer and the pointer to the API & terminal docs."""
    host = SITE_URL.split('://', 1)[-1]
    return f"""
<footer>
  <div class="wrap cols">
    <section>
      <h2>About this site</h2>
      <p>This is an unofficial community project by <a href="{AUTHOR_URL}">admon</a>. It is not affiliated with, endorsed or supported by GL.iNet.</p>
      <p>The official firmware page needs JavaScript to show anything. This page is the lightweight alternative: plain HTML that works in any browser, over slow or metered connections, from the router's own shell, and with scripts blocked.</p>
      <p>Versions come from GL.iNet's public firmware API. Every download link points straight to GL.iNet's servers (fw.gl-inet.com) and is checked once a day. For help with a device, contact GL.iNet or the <a href="{FORUM_URL}">GL.iNet forum</a>.</p>
      <div class="links"><a href="{GITHUB_URL}">Source on GitHub</a><a href="{root}status.html">Link status</a><a href="{SPONSOR_URL}">Support the project</a></div>
    </section>
    <section>
      <h2>From a script or the terminal</h2>
      <p>Every page is also available as plain text, and each value has its own URL:</p>
      <pre>curl {host}/api/{example_model}/release/version</pre>
      <p><a href="{root}{DOCS_DIR}/">How to use the API and the terminal menu</a></p>
    </section>
  </div>
</footer>
"""
