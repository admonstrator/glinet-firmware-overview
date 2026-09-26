"""The overview page (index.html): toolbar, recently released builds and one table per category."""
import html as html_lib
from datetime import datetime

from sitelib.core import (FRESH_DAYS, RECENT_DAYS, SITE_NAME, SITE_URL, age_short, age_text, api_stage_name,
                          build_date, days_since, device_page_url, entry_link, feed_url, group_models_by_type,
                          is_fresh, latest_update, ordered_stages, overview_stage_columns, parse_generated_at,
                          recent_builds, split_name, stage_class, stage_title)
from sitelib.design import icon, page_head, site_footer, site_header

# Category order, section id (also the target of the device page breadcrumbs), filter label, section title
CATEGORIES = [
    ('ROUTER', 'router', 'Routers', 'Routers'),
    ('IOT', 'iot', 'IoT', 'IoT devices'),
    ('KVM', 'kvm', 'KVM', 'KVM over IP (Comet)'),
]
CATEGORY_LABELS = {key: label for key, _, label, _ in CATEGORIES}
CATEGORY_IDS = {key: slug for key, slug, _, _ in CATEGORIES}
CATEGORY_TITLES = {key: title for key, _, _, title in CATEGORIES}

# Ids used by the page itself; a table row never takes one of these as its model anchor
PAGE_IDS = {'recent', 'recent-h', 'search', 'q', 'nomatch', 'router', 'iot', 'kvm',
            'f-all', 'f-router', 'f-iot', 'f-kvm'}

OVERVIEW_CSS = """
[hidden] { display: none !important; }
.status a.bad { color: var(--rc); }
.ver.dead { color: var(--muted); }
a.warn { display: inline-flex; color: var(--rc); }
.fallback { display: inline-flex; gap: 5px; align-items: center; margin-top: 2px; font-size: 12.5px; font-weight: 600; color: var(--ink); text-decoration: none; }
.fallback:hover { text-decoration: underline; text-underline-offset: 3px; }
th.age, td.age { text-align: right; white-space: nowrap; }
td.age { font-size: 13px; color: var(--muted); }
td.age .l { display: none; }
@media (min-width: 961px) { td.age { padding-top: 12px; } }
.recent { margin-bottom: 30px; }
.recent h2 { font: 600 19px/1.2 var(--display); margin: 0 0 10px; display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; }
.recent h2 small { font: 500 13px var(--text); color: var(--muted); }
.recent h2 a { margin-left: auto; display: inline-flex; gap: 6px; align-items: center; font: 500 13px var(--text); color: var(--muted); text-decoration: none; }
.recent h2 a:hover { color: var(--ink); text-decoration: underline; }
.recent ol { list-style: none; margin: 0; padding: 6px; display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }
.recent li { padding: 7px 12px; min-width: 0; }
.recent .dev { display: block; text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recent .dev .nick { font-weight: 650; }
.recent .dev .sku { font-size: 12.5px; color: var(--muted); margin-left: 4px; }
.recent a.dev:hover .nick { text-decoration: underline; text-underline-offset: 3px; }
.recent .line { display: flex; flex-wrap: wrap; gap: 2px 9px; align-items: baseline; font-size: 13px; color: var(--muted); }
.recent .none { margin: 0; padding: 14px 18px; color: var(--muted); }
@media (max-width: 960px) {
  footer .cols { grid-template-columns: minmax(0, 1fr); }
  th.age, td.age { text-align: left; }
  td.age .s { display: none; }
  td.age .l { display: inline; }
}
"""

# Progressive enhancement, well under 1 KB: shows the search box and filters rows by code and name.
SEARCH_JS = """(()=>{const d=document,q=d.getElementById('q'),n=d.getElementById('nomatch'),r=d.getElementById('recent');
d.getElementById('search').hidden=false;
const run=()=>{const t=q.value.trim().toLowerCase(),f=d.querySelector('[name=cat]:checked').id.slice(2);let any=0;
d.querySelectorAll('.cat').forEach(s=>{let v=0;s.querySelectorAll('tbody tr').forEach(tr=>{const h=tr.dataset.search.includes(t);tr.hidden=!h;v+=h});
s.hidden=!v;if(f=='all'||f==s.id)any+=v});r.hidden=!!t;n.style.display=any?'':'block'};
q.addEventListener('input',run);d.querySelector('.filters').addEventListener('change',run)})();"""


def esc(text, quote=False):
    return html_lib.escape(str(text), quote=quote)


def open_tag(stage, entry):
    """'OP24' tag of an OpenWrt open build, '' for every other stage."""
    if not stage.upper().startswith('BETA_OPEN'):
        return ''
    label = stage_title(stage, entry).rsplit(' ', 1)[-1]
    return f'<span class="tag op" title="OpenWrt {label[2:]} open build">{label}</span>'


def version_html(entry, cls, root=''):
    """Version as a download link, or muted with a warning (and the fallback build) when the
    download did not respond in the last build. Returns (version_html, fallback_html)."""
    version = esc(entry.get('version', 'N/A'))
    if not entry.get('_link_ok', True):
        reason = esc(entry.get('_link_reason') or 'unknown', quote=True)
        html = (f'<span class="ver dead">{version}</span> '
                f'<a class="warn" href="{root}status.html" title="Download did not respond ({reason}), see the link status page">'
                f'{icon("warn")}<span class="visually-hidden">Download did not respond</span></a>')
        fallback = ''
        if entry.get('_fallback_link'):
            fallback = (f'<a class="fallback" href="{esc(entry["_fallback_link"], quote=True)}" '
                        f'title="Newest build whose download works">{icon("dl")}{esc(entry.get("_fallback_version", ""))} instead</a>')
        return html, fallback
    link = entry_link(entry)
    if not link:
        return f'<span class="ver {cls}">{version}</span>', ''
    return f'<a class="ver {cls}" href="{esc(link, quote=True)}" title="Download {version}">{version}{icon("dl")}</a>', ''


def time_html(entry, text=None, title=''):
    """<time> element with the release date; `text` defaults to the date itself."""
    d = build_date(entry)
    if d is None:
        return ''
    t = f' title="{esc(title, quote=True)}"' if title else ''
    return f'<time datetime="{d.isoformat()}"{t}>{esc(text if text is not None else d.isoformat())}</time>'


def build_html(code, stage, entry, now):
    """One build inside a table cell: version, tags, date and changelog link."""
    ver, fallback = version_html(entry, stage_class(stage))
    tag = open_tag(stage, entry)
    fresh = (f' <span class="tag fresh" title="Released {age_text(days_since(entry, now))}">new</span>'
             if is_fresh(entry, now) else '')
    notes = ''
    if (entry.get('changelog') or '').strip():
        notes = (f'<a href="api/{code.lower()}/{api_stage_name(stage)}/changelog" title="Changelog (plain text)">'
                 f'{icon("notes")}<span class="visually-hidden">Changelog</span></a>')
    return (f'<div class="build">{tag}{" " if tag else ""}{ver}{fresh}'
            f'<div class="meta">{time_html(entry)}{notes}</div>{fallback}</div>')


def last_update_html(stages, now):
    """Right-most cell: age of the newest build of any stage."""
    stage, entry = latest_update(stages)
    if entry is None or build_date(entry) is None:
        return '<td class="age empty" data-stage="Last update"></td>'
    days = days_since(entry, now)
    date = build_date(entry).isoformat()
    title = esc(f'{age_text(days)}, {date} ({stage_title(stage, entry)} {entry.get("version", "")})', quote=True)
    return (f'<td class="age" data-stage="Last update"><time datetime="{date}" title="{title}">'
            f'<span class="s">{age_short(days)}</span><span class="l">{age_text(days)}</span></time></td>')


def category_columns(codes, models):
    """Stage columns one category actually uses; OpenWrt open builds live in the Beta column."""
    sub = {c: models[c] for c in codes}
    cols = overview_stage_columns(sub)
    if 'BETA' not in cols and any(s.startswith('BETA_OPEN') for stages in sub.values() for s in stages):
        cols = ordered_stages(cols + ['BETA'])
    return cols


def row_html(code, models, meta, cols, now):
    stages = models[code]
    name = meta.get('name', code)
    nick, sku = split_name(name, code)
    label = f'<span class="nick">{esc(nick)}</span><span class="sku">{esc(sku)}</span>'
    page = device_page_url(code)
    device = f'<a href="{page}">{label}</a>' if page else label
    row_id = f' id="{esc(code.lower(), quote=True)}"' if code.lower() not in PAGE_IDS else ''
    cells = []
    for col in cols:
        builds = [(col, stages[col])] if col in stages else []
        if col == 'BETA':
            builds += [(s, stages[s]) for s in sorted(stages) if s.startswith('BETA_OPEN')]
        if builds:
            cells.append(f'<td data-stage="{stage_title(col)}">{"".join(build_html(code, s, e, now) for s, e in builds)}</td>')
        else:
            cells.append('<td class="empty"></td>')
    search = esc(f'{code} {name}'.lower(), quote=True)
    return (f'\n        <tr{row_id} data-search="{search}"><th scope="row" class="model">{device}</th>'
            f'{"".join(cells)}{last_update_html(stages, now)}</tr>')


def category_html(m_type, codes, models, models_metadata, now):
    slug, title = CATEGORY_IDS[m_type], CATEGORY_TITLES[m_type]

    def sort_key(code):
        nick, sku = split_name(models_metadata.get(code, {}).get('name', code), code)
        return (nick.lower(), sku.lower(), code.lower())

    codes = sorted(codes, key=sort_key)
    cols = category_columns(codes, models)
    head = ''.join(f'<th scope="col">{stage_title(s)}</th>' for s in cols)
    rows = ''.join(row_html(c, models, models_metadata.get(c, {}), cols, now) for c in codes)
    count = f'{len(codes)} device{"" if len(codes) == 1 else "s"}'
    return f"""
  <section class="cat" id="{slug}">
    <h2>{title} <small>{count}</small></h2>
    <div class="sheet"><table>
      <thead><tr><th scope="col">Device</th>{head}<th scope="col" class="age">Last update</th></tr></thead>
      <tbody>{rows}
      </tbody>
    </table></div>
  </section>"""


def recent_item_html(b):
    code, stage, entry = b['code'], b['stage'], b['entry']
    nick, sku = split_name(b['name'], code)
    label = f'<span class="nick">{esc(nick)}</span>' + (f'<span class="sku">{esc(sku)}</span>' if sku else '')
    page = device_page_url(code)
    device = (f'<a class="dev" href="{page}#{api_stage_name(stage)}">{label}</a>' if page
              else f'<span class="dev">{label}</span>')
    ver, _ = version_html(entry, stage_class(stage))
    when = time_html(entry, age_text(b['days']), build_date(entry).isoformat() if build_date(entry) else '')
    return f'\n      <li>{device}<div class="line"><span>{stage_title(stage, entry)}</span>{ver}{when}</div></li>'


def recent_html(models, models_metadata, now):
    """'Recently released' section (id="recent", the target of /new in a browser)."""
    builds = recent_builds(models, models_metadata, now)
    if builds:
        body = f'<ol class="sheet">{"".join(recent_item_html(b) for b in builds)}\n    </ol>'
    else:
        body = f'<p class="sheet none">No new firmware in the last {RECENT_DAYS} days.</p>'
    return f"""
  <section class="recent" id="recent" aria-labelledby="recent-h">
    <h2 id="recent-h">Recently released <small>last {RECENT_DAYS} days, without snapshots</small>
      <a href="{feed_url()}" title="Atom feed with new firmware for all devices">{icon("feed")}Feed</a></h2>
    {body}
  </section>"""


def status_html(diagnostics):
    """Link status line of the toolbar, linking to status.html."""
    total = len(diagnostics)
    bad = sum(1 for d in diagnostics if d.get('status') != 'ok')
    if bad:
        return (f'<a href="status.html" class="bad">{icon("warn")}{bad} of {total} download link'
                f'{"" if total == 1 else "s"} unreachable</a>')
    return f'<a href="status.html">{icon("ok")}All {total} download link{"" if total == 1 else "s"} responded</a>'


def generate_html(models, models_metadata, diagnostics, generated_at=None):
    generated_at = generated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    now = parse_generated_at(generated_at)
    grouped = group_models_by_type(models, models_metadata)
    total = len(models)
    present = [(key, slug, label) for key, slug, label, _ in CATEGORIES if grouped.get(key)]

    filters = ''.join(f'<input type="radio" name="cat" id="f-{slug}"><label for="f-{slug}">{label}<span>{len(grouped[key])}</span></label>'
                      for key, slug, label in present)
    issues = any(d.get('status') != 'ok' for d in diagnostics)
    warn_legend = f'\n    <span>{icon("warn")} Download did not respond</span>' if issues else ''

    head = page_head(
        f'{SITE_NAME} (unofficial)',
        description='Unofficial overview of the latest GL.iNet firmware for all routers, IoT and KVM devices, '
                    'with download links checked daily. Plain HTML, plain text for curl and a flat-file API.',
        canonical=f'{SITE_URL}/',
        root='',
        feeds=[('All devices', feed_url())],
        extra_css=OVERVIEW_CSS,
    )
    header = site_header('', SITE_NAME,
                         lead=f'The latest firmware for {total} GL.iNet routers, IoT and KVM devices on one light page.')
    tables = ''.join(category_html(key, grouped[key], models, models_metadata, now) for key, _, _ in present)
    main = f"""<main class="wrap">
  <div class="toolbar">
    <label class="search" id="search" hidden><span class="visually-hidden">Search devices</span>{icon("search")}<input type="search" id="q" placeholder="Search, e.g. Flint or MT3000" autocomplete="off"></label>
    <noscript><p class="find-hint">Looking for a device? Use your browser's find (Ctrl+F or Cmd+F).</p></noscript>
    <div class="filters" role="radiogroup" aria-label="Device type">
      <input type="radio" name="cat" id="f-all" checked><label for="f-all">All<span>{total}</span></label>{filters}
    </div>
    <div class="status">
      <span>Updated <time datetime="{now.strftime('%Y-%m-%dT%H:%M:%SZ')}">{now.strftime('%Y-%m-%d %H:%M')} UTC</time></span>
      {status_html(diagnostics)}
    </div>
  </div>
  <div class="legend">
    <span>{icon("dl")} Version: download</span>
    <span>{icon("notes")} Changelog</span>
    <span><span class="tag fresh">new</span> Released in the last {FRESH_DAYS} days</span>
    <span><span class="tag op">OP24</span> OpenWrt open build</span>{warn_legend}
    <span>Last update: newest build of any stage</span>
  </div>
{recent_html(models, models_metadata, now)}
{tables}
  <p class="nomatch" id="nomatch">No device matches your search. Try the model number printed on the label, e.g. MT3000.</p>
</main>
"""
    return (head + header + main + site_footer('') + f'<script>{SEARCH_JS}</script>\n' + '</body>\n</html>\n')
