"""Device pages (<model>/index.html at the site root)."""
import html as html_lib
import os
import shutil

from sitelib.core import (DEVICE_PAGE_MARKER, DOCS_DIR, RESERVED_ROOT_NAMES, SITE_NAME, SITE_URL, age_text,
                          api_stage_name, build_date, days_since, device_page_url, entry_link, feed_url, is_fresh,
                          latest_update, ordered_stages, parse_generated_at, split_name, stage_class, stage_title)
from sitelib.design import icon, page_head, site_footer, site_header
from sitelib.overview import CATEGORY_IDS, CATEGORY_LABELS, open_tag

DEVICE_CSS = """
.buildcard .stage.rc { color: var(--rc); }
.buildcard .stage .tag { vertical-align: 2px; margin-left: 4px; }
.buildcard .v.dead { color: var(--muted); }
.buildcard .d .tag { margin-left: 6px; }
.btn.alt { background: transparent; color: var(--ink); border: 1px solid var(--frost); padding: 6px 13px; }
.btn.alt:hover { background: var(--ice); }
.warnline { display: flex; gap: 8px; align-items: baseline; margin: 10px 0 0; font-size: 14px; }
.warnline .ico { color: var(--rc); position: relative; top: 2px; }
.md5 { margin: 8px 0 0; font-size: 13px; color: var(--muted); }
.md5 code { font: 12.5px var(--code); word-break: break-all; }
.nobuilds { background: var(--paper); border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; margin: 0; }
.term { padding-top: 30px; }
.term h2 { font: 600 19px/1.2 var(--display); margin: 0 0 10px; }
.term pre { font: 13.5px/1.65 var(--code); background: var(--deep); color: var(--on-deep); padding: 14px 18px; border-radius: 12px; overflow-x: auto; margin: 0 0 12px; }
.term pre .c { color: var(--on-deep-2); }
.term p { margin: 0; display: flex; flex-wrap: wrap; gap: 8px 22px; font-size: 14px; }
.term p a { display: inline-flex; gap: 6px; align-items: center; }
@media (max-width: 960px) {
  footer .cols { grid-template-columns: minmax(0, 1fr); }
}
"""


def esc(text, quote=False):
    return html_lib.escape(str(text), quote=quote)


def date_html(entry, now):
    d = build_date(entry)
    if d is None:
        return ''
    return f'Released <time datetime="{d.isoformat()}" title="{age_text(days_since(entry, now))}">{d.isoformat()}</time>'


def build_block(stage, entry, now, open_changelog, code=''):
    """One stage: version, date, "new" tag, download (or warning and fallback), MD5, changelog."""
    s_api = api_stage_name(stage)
    cls = stage_class(stage)
    version = esc(entry.get('version', 'N/A'))
    tag = open_tag(stage, entry)
    stage_name = 'Beta' if tag else stage_title(stage, entry)
    fresh = '<span class="tag fresh">new</span>' if is_fresh(entry, now) else ''
    link_ok = entry.get('_link_ok', True)
    link = entry_link(entry)
    action = ''
    warn = ''
    if link_ok and link:
        action = f'<a class="btn" href="{esc(link, quote=True)}">{icon("dl")}Download</a>'
    elif not link_ok:
        reason = esc(entry.get('_link_reason') or 'unknown')
        if entry.get('_fallback_link'):
            fb_version = esc(entry.get('_fallback_version', ''))
            action = (f'<a class="btn alt" href="{esc(entry["_fallback_link"], quote=True)}" '
                      f'title="Newest build whose download works">{icon("dl")}Download {fb_version} instead</a>')
            detail = f'{fb_version} is the newest build that still downloads.'
        else:
            detail = 'No older build downloads either.'
        warn = (f'\n      <p class="warnline">{icon("warn")}<span>The download of {version} did not respond in the last check '
                f'({reason}). {detail} <a href="../status.html{'#' + code.lower() + '-' + s_api if code else ''}">Link status</a></span></p>')
    md5 = ((entry.get('download') or [{}])[0].get('md5') or '').strip()
    md5_html = f'\n      <p class="md5">MD5 <code>{esc(md5)}</code></p>' if md5 else ''
    changelog = (entry.get('changelog') or '').strip()
    changelog_html = ''
    if changelog:
        changelog_html = (f'\n      <details{" open" if open_changelog else ""}><summary>Changelog</summary>'
                          f'<pre>{esc(changelog)}</pre></details>')
    return f"""
    <article class="buildcard" id="{s_api}">
      <div class="row">
        <span class="stage {cls}">{stage_name}{tag}</span>
        <span class="v{'' if link_ok else ' dead'}">{version}</span>
        <span class="d">{date_html(entry, now)}{fresh}</span>
        {action}
      </div>{warn}{md5_html}{changelog_html}
    </article>"""


def terminal_html(code, first_stage):
    """Compact 'Use it from the terminal' part with this device's curl commands."""
    slug = code.lower()
    lines = ['<span class="c"># This page as plain text</span>', f'curl {SITE_URL}/{slug}']
    if first_stage:
        s_api = api_stage_name(first_stage)
        lines += [f'<span class="c"># Latest {stage_title(first_stage).lower()} version, then download it</span>',
                  f'curl {SITE_URL}/api/{slug}/{s_api}/version',
                  f'curl -LO "$(curl -s {SITE_URL}/api/{slug}/{s_api}/url)"']
    return f"""
  <section class="term" id="terminal">
    <h2>Use it from the terminal</h2>
<pre>{chr(10).join(lines)}</pre>
    <p><a href="{feed_url(code, root='../')}">{icon("feed")}Feed for this device</a><a href="../{DOCS_DIR}/">{icon("code")}API and terminal docs</a></p>
  </section>"""


def generate_device_page(code, stages, meta, generated_at):
    """Build the standalone HTML page of a single model, served at /<model>/."""
    now = parse_generated_at(generated_at)
    root = '../'
    name = meta.get('name', code)
    nick, sku = split_name(name, code)
    m_type = meta.get('type', 'ROUTER')
    display_stages = ordered_stages(stages)

    display = f'{nick} ({sku})' if sku else nick
    versions = ', '.join(f'{stage_title(s, stages[s])} {stages[s].get("version", "N/A")}' for s in display_stages)
    description = (f'Latest GL.iNet firmware for the {name} ({code.lower()}): {versions}.' if versions else
                   f'GL.iNet firmware for the {name} ({code.lower()}): no firmware listed at the moment.')

    lead = ''
    stage, entry = latest_update(stages)
    if entry is not None and build_date(entry) is not None:
        d = build_date(entry).isoformat()
        lead = (f'Last update <time datetime="{d}" title="{d}">{age_text(days_since(entry, now))}</time> '
                f'({esc(stage_title(stage, entry))} {esc(entry.get("version", ""))})')

    head = page_head(
        f'{display} firmware, {SITE_NAME} (unofficial)',
        description=description,
        canonical=f'{SITE_URL}/{device_page_url(code)}',
        root=root,
        feeds=[(f'{nick} firmware', feed_url(code, root=root)), ('All devices', feed_url(root=root))],
        extra_css=DEVICE_CSS,
    )
    # The marker right after the doctype lets remove_stale_device_pages() recognise generated pages.
    head = head.replace('<!DOCTYPE html>\n', f'<!DOCTYPE html>\n{DEVICE_PAGE_MARKER}\n', 1)
    crumbs = [('All devices', root),
              (CATEGORY_LABELS.get(m_type, 'Routers'), f'{root}#{CATEGORY_IDS.get(m_type, "router")}'),
              (nick, None)]
    header = site_header(root, nick, lead=lead, crumbs=crumbs, sku=esc(sku))

    blocks = []
    with_changelog = 0
    for s in display_stages:
        has_changelog = bool((stages[s].get('changelog') or '').strip())
        blocks.append(build_block(s, stages[s], now, open_changelog=has_changelog and not with_changelog, code=code))
        with_changelog += has_changelog
    if blocks:
        body = f'<div class="builds">{"".join(blocks)}\n  </div>'
    else:
        body = ('<div class="builds"><p class="nobuilds">GL.iNet lists no firmware for this device at the moment. '
                f'The <a href="{root}">overview</a> shows every device that has one.</p></div>')
    main = f"""<main class="wrap">
  {body}
{terminal_html(code, display_stages[0] if display_stages else None)}
</main>
"""
    # The footer example asks for /release/version, so it names this device only when it has a release build.
    example = code.lower() if 'RELEASE' in stages else 'mt3000'
    return head + header + main + site_footer(root, example_model=example) + '</body>\n</html>\n'


def remove_stale_device_pages():
    """Delete root-level directories that hold a device page from a previous run.
    Only directories whose index.html carries DEVICE_PAGE_MARKER are touched."""
    for name in os.listdir('.'):
        page = os.path.join(name, 'index.html')
        if name in RESERVED_ROOT_NAMES or not os.path.isdir(name) or not os.path.isfile(page):
            continue
        with open(page, encoding='utf-8', errors='ignore') as f:
            if DEVICE_PAGE_MARKER in f.read(2048):
                shutil.rmtree(name)


def generate_device_pages(models, models_metadata, generated_at):
    """Write one standalone HTML page per model to <model>/index.html at the site
    root. Returns the number of pages written."""
    remove_stale_device_pages()

    written = 0
    for code, stages in models.items():
        page_url = device_page_url(code)
        if page_url is None:
            print(f"  WARNING Skipping device page for '{code}': it would collide with a reserved directory.")
            continue
        meta = models_metadata.get(code, {})
        page_dir = code.lower()
        os.makedirs(page_dir, exist_ok=True)
        with open(os.path.join(page_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(generate_device_page(code, stages, meta, generated_at))
        written += 1
    return written
