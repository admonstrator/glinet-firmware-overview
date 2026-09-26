"""The build & link status page (status.html) in the design of sitelib.design."""
import html as html_lib
from datetime import datetime

from sitelib.core import *  # noqa: F401,F403
from sitelib.design import *  # noqa: F401,F403

STATUS_CSS = """
.statuspage { padding-top: 28px; padding-bottom: 10px; }
.statuspage h2 { font: 650 21px/1.25 var(--display); margin: 32px 0 8px; display: flex; gap: 8px; align-items: center; }
.statuspage h2 .ico { width: 18px; height: 18px; }
.statuspage h2.bad .ico { color: var(--rc); }
.statuspage p { max-width: 75ch; margin: 0 0 12px; }
.statuspage code { font: 13.5px var(--code); }
.tally { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 0 0 22px; padding: 0; list-style: none; }
.tally li { background: var(--paper); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px; }
.tally .n { display: flex; gap: 8px; align-items: center; font: 700 28px/1.15 var(--display); }
.tally .n .ico { width: 18px; height: 18px; }
.tally .l { color: var(--muted); font-size: 13.5px; }
.tally .good .n .ico { color: var(--release); }
.tally .bad .n { color: var(--rc); }
.allgood { display: flex; gap: 10px; align-items: flex-start; max-width: 80ch; margin: 0 0 22px; padding: 12px 16px;
  background: var(--paper); border: 1px solid var(--line); border-left: 4px solid var(--release); border-radius: 12px; }
.allgood .ico { color: var(--release); margin-top: 3px; }
.floe .lead time { white-space: nowrap; }
.problems td { white-space: nowrap; }
.problems td:last-child { white-space: normal; }
.problems .v { font-weight: 650; }
.problems .reason { font: 12.5px/1.6 var(--code); padding: 1px 6px; border-radius: 6px; white-space: nowrap;
  background: color-mix(in srgb, var(--rc) 14%, transparent); color: var(--rc); }
.problems .file { font: 12.5px var(--code); word-break: break-all; color: var(--muted); }
.problems .file:hover { color: var(--ink); }
.problems .none { color: var(--muted); font-size: 13.5px; }
.problems .stage.release { color: var(--release); } .problems .stage.beta { color: var(--beta); }
.problems .stage.snapshot { color: var(--snapshot); } .problems .stage.rc { color: var(--rc); } .problems .stage.other { color: var(--other); }
.problems .stage { font-weight: 600; }
.tablenote { color: var(--muted); font-size: 13.5px; margin-top: 10px; }
.nodata { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 12px; padding: 0; list-style: none; }
.nodata li { font: 13.5px var(--code); background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 2px 8px; }
.check .reason { font: 12.5px var(--code); padding: 1px 6px; border-radius: 6px; background: var(--paper); border: 1px solid var(--line); }
@media (max-width: 960px) {
  .problems td[data-stage="File"] { grid-column: 1 / -1; }
  footer .cols { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 700px) {
  .tally { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
"""


def status_row_id(model, stage):
    """Anchor of one unreachable download on status.html, e.g. 'mt6000-release'."""
    return f'{model.lower()}-{api_stage_name(stage)}'


def _tally(value, label, problem=None):
    """One counter tile. `problem` True/False colours it; None leaves it neutral."""
    cls = '' if problem is None else (' class="bad"' if problem else ' class="good"')
    mark = '' if problem is None else icon('warn' if problem else 'ok')
    return f'<li{cls}><span class="n">{mark}{value}</span><span class="l">{label}</span></li>'


def _problem_row(d):
    esc = html_lib.escape
    nick, sku = split_name(d.get('name') or d['model'], d['model'])
    model_inner = f'<span class="nick">{esc(nick)}</span><span class="sku">{esc(sku or d["model"])}</span>'
    page = device_page_url(d['model'])
    model_cell = f'<a href="{esc(page, quote=True)}">{model_inner}</a>' if page else model_inner
    stage = d['stage']
    date = esc((d.get('release_time') or '').split(' ')[0])
    if d.get('link'):
        filename = d['link'].rsplit('/', 1)[-1]
        file_cell = f'<a class="file" href="{esc(d["link"], quote=True)}">{esc(filename)}</a>'
    else:
        file_cell = '<span class="none">no link in the API response</span>'
    if d.get('fallback_version'):
        fb_date = esc((d.get('fallback_release_time') or '').split(' ')[0])
        fallback_cell = (f'<a class="ver {stage_class(stage)}" href="{esc(d["fallback_link"], quote=True)}" '
                         f'title="Download {esc(d["fallback_version"])}">{esc(d["fallback_version"])}{icon("dl")}</a>'
                         f'<div class="meta"><time datetime="{fb_date}">{fb_date}</time></div>')
    else:
        fallback_cell = f'<span class="none">none ({d.get("candidates_probed", 0)} probed)</span>'
    return (f'<tr id="{esc(status_row_id(d["model"], stage), quote=True)}">'
            f'<th scope="row" class="model">{model_cell}</th>'
            f'<td data-stage="Stage"><span class="stage {stage_class(stage)}">{esc(stage_title(stage))}</span></td>'
            f'<td data-stage="Version"><span class="v">{esc(d.get("version") or "")}</span></td>'
            f'<td data-stage="Released"><time datetime="{date}">{date}</time></td>'
            f'<td data-stage="Reason"><span class="reason">{esc(d.get("reason") or "")}</span></td>'
            f'<td data-stage="Attempts">{d.get("attempts", 0)}</td>'
            f'<td data-stage="Latest reachable">{fallback_cell}</td>'
            f'<td data-stage="File">{file_cell}</td></tr>')


def generate_status_html(diagnostics, empty_models, generated_at=None):
    """status.html: counters, unreachable downloads, models without API data and how the check works."""
    esc = html_lib.escape
    root = ''
    built = generated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    stamp = parse_generated_at(built).strftime('%Y-%m-%dT%H:%M:%SZ')

    unreachable = sorted((d for d in diagnostics if d['status'] == 'unreachable'),
                         key=lambda d: (d['model'].lower(), d['stage']))
    attempts = sum(d['attempts'] + d['candidates_probed'] for d in diagnostics)

    parts = ['<main class="wrap statuspage">',
             '  <ul class="tally">'
             + _tally(len(diagnostics), 'Model and stage entries')
             + _tally(attempts, 'HEAD requests')
             + _tally(len(unreachable), 'Unreachable downloads', bool(unreachable))
             + _tally(len(empty_models), 'Models without API data', bool(empty_models))
             + '</ul>']

    if not unreachable and not empty_models:
        parts.append(f'  <p class="allgood">{icon("ok")}<span>Every tracked model and stage is showing the newest '
                     'firmware the GL.iNet API reports, and every download link responded. Nothing to report.</span></p>')

    if unreachable:
        rows = ''.join(_problem_row(d) for d in unreachable)
        parts.append(f"""  <h2 id="unreachable" class="bad">{icon('warn')}Unreachable downloads</h2>
  <div class="sheet problems">
    <table>
      <thead><tr><th scope="col">Model</th><th scope="col">Stage</th><th scope="col">Version</th><th scope="col">Released</th><th scope="col">Reason</th><th scope="col">Attempts</th><th scope="col">Latest reachable</th><th scope="col">File</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <p class="tablenote">These versions are still listed on the overview; only their download link did not respond during this build. <em>Latest reachable</em> is the newest older build whose download still works (up to {FALLBACK_CANDIDATES} are probed), offered as a second download so there is always something to grab.</p>""")

    if empty_models:
        items = ''.join(f'<li>{esc(m)}</li>' for m in empty_models)
        parts.append(f"""  <h2 id="no-data" class="bad">{icon('warn')}Models without API data</h2>
  <p>The GL.iNet API returned no firmware entries for these models during this build, so they carry no versions on the overview. This is almost always a temporary API hiccup.</p>
  <ul class="nodata">{items}</ul>""")

    parts.append(f"""  <h2 id="how">How the check works</h2>
  <div class="check">
  <p>The overview always lists the newest firmware the GL.iNet API reports. Its download link is verified with a <code>HEAD</code> request ({LINK_TIMEOUT}&nbsp;s timeout, up to {LINK_ATTEMPTS} attempts for temporary failures). A link that does not respond never changes which version is listed: showing an older release as the current one would be worse than showing the current one without a working download. Instead the entry keeps its version and its download is flagged with a warning sign. Where an older build still downloads, that one is offered as a second link.</p>
  <p>A <span class="reason">timeout</span> is usually temporary and resolves itself on the next daily run. An <span class="reason">HTTP 404</span> means the file is really gone from GL.iNet's server; that one will not fix itself.</p>
  </div>
  <p>Machine-readable version of this page: <a href="{root}api/status.json"><code>/api/status.json</code></a>. More for scripts on the <a href="{root}{DOCS_DIR}/">API and terminal</a> page.</p>
</main>
""")

    return (page_head(f'Build and link status | {SITE_NAME} (unofficial)',
                      'Which GL.iNet firmware downloads could not be reached in the last build of the unofficial '
                      'firmware overview, and how the daily link check works.',
                      canonical=f'{SITE_URL}/status.html', root=root, extra_css=STATUS_CSS)
            + site_header(root, 'Build and link status',
                          lead=f'Which firmware downloads could not be reached in the last build, '
                               f'<time datetime="{stamp}">{esc(built)}</time>. The site is rebuilt every day.',
                          crumbs=(('All devices', './'), ('Build and link status', None)), current='status')
            + '\n'.join(parts) + site_footer(root) + '</body>\n</html>\n')
