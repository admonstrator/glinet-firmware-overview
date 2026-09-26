"""API & terminal documentation (/docs/, HTML + text twin) and the /cli/ landing page.

Section order (decision R5): Interactive menu, Plain-text pages, Flat-file API, Feeds, Examples,
Model codes. The HTML page and its text twin are built from the same lists below so they cannot
drift apart. Example output is taken from the API files the generator wrote just before (write_site
renders the API first), with a fallback built from the model data.
"""
import html as html_lib
import json
import os
import textwrap

from sitelib.core import *  # noqa: F401,F403
from sitelib.design import *  # noqa: F401,F403

DOCS_TEXT_WIDTH = 100        # columns of docs/index.txt
EXAMPLE_MODEL = 'mt3000'     # preferred model for example commands and output
REBUILD_TIME = '04:00 UTC'   # schedule of .github/workflows/daily_update.yml

# (anchor id, heading) in the order of decision R5
DOCS_SECTIONS = (
    ('menu', 'Interactive menu'),
    ('text', 'Plain-text pages'),
    ('api', 'Flat-file API'),
    ('feeds', 'Feeds'),
    ('examples', 'Examples'),
    ('codes', 'Model codes'),
)

DOCS_CSS = """
.doc h3 { font: 600 15px/1.3 var(--display); margin: 18px 0 6px; display: flex; gap: 8px; align-items: baseline; }
.doc h3 small { font: 500 13px var(--text); color: var(--muted); }
.doc p code { white-space: nowrap; }
.doc .out { tab-size: 4; margin-top: 2px; }
.doc .out:empty::before { content: "(empty)"; }
.doc .note { color: var(--muted); font-size: 14px; }
.doc ul.can { max-width: 70ch; margin: 0 0 14px; padding-left: 20px; }
.doc ul.can li { margin-bottom: 4px; }
.doc .endpoints th { white-space: nowrap; }
.codes a, .codes .nolink { display: inline-flex; gap: 8px; align-items: baseline; }
.codes a { text-decoration: none; }
.codes a:hover .n { text-decoration: underline; text-underline-offset: 3px; }
.codes code { min-width: 92px; }
@media (max-width: 960px) {
  .doc tbody tr { display: block; padding: 10px 14px; }
  .doc tbody th, .doc tbody td { padding: 0; border: 0; }
  .doc tbody th { white-space: normal; word-break: break-all; margin-bottom: 4px; }
}
"""


# ---------------------------------------------------------------------------
# Facts shared by the HTML page and the text twin
# ---------------------------------------------------------------------------

def site_host():
    """'firmware.gl-i.net' (curl defaults to http://, which the site answers as well)."""
    return SITE_URL.split('://', 1)[-1]


def docs_example(models):
    """(model code, stage key used for the download example) for the example commands.
    Prefers EXAMPLE_MODEL; otherwise the first model with a device page and a release."""
    candidates = [EXAMPLE_MODEL] + sorted(models, key=str.lower)
    code = next((c for c in candidates if c in models and 'RELEASE' in models[c] and device_page_url(c)),
                next(iter(sorted(models, key=str.lower)), EXAMPLE_MODEL))
    stages = models.get(code, {})
    return code, ('BETA' if 'BETA' in stages else 'RELEASE')


def docs_stage_names(models):
    """API names of the stages that actually occur in the data, in display order."""
    seen = set()
    for stages in models.values():
        seen.update(stages)
    return [api_stage_name(s) for s in ordered_stages(seen)]


def _read_api_file(api_dir, *parts):
    try:
        with open(os.path.join(api_dir, *parts), encoding='utf-8') as f:
            return f.read()
    except OSError:
        return None


def api_samples(models, models_metadata, code, api_dir='api'):
    """Real output of the flat-file API for `code`'s release, keyed by endpoint.
    Read from the files the generator wrote (so the page shows exactly what is served);
    composed from the model data when those files are not there."""
    lower = code.lower()
    entry = models.get(code, {}).get('RELEASE', {})
    version = entry.get('version', '')
    link = entry_link(entry)
    md5 = (entry.get('download') or [{}])[0].get('md5', '') or ''
    changelog_url = f'{SITE_URL}/api/{lower}/release/changelog'
    first_line = next((ln.strip() for ln in (entry.get('changelog') or '').splitlines() if ln.strip()), '')

    summary = _read_api_file(api_dir, lower, 'release', 'index.html')
    if summary is None:
        state = 'ok' if entry.get('_link_ok', True) else f"unreachable ({entry.get('_link_reason', 'unknown')})"
        summary = (f'version: {version}\nhash: {md5}\ndownload: {link}\ndate: {entry.get("release_time", "")}\n'
                   f'changelog: {changelog_url}\nlink: {state}\n')

    branches = _read_api_file(api_dir, lower, 'branches')
    if branches is None:
        branches = ''.join(f'{s}\n' for s in sorted(api_stage_name(s) for s in models.get(code, {})))

    stages = _read_api_file(api_dir, lower, 'stages')
    if stages is None:
        state = 'ok' if entry.get('_link_ok', True) else (entry.get('_link_reason') or 'unreachable')
        stages = '\t'.join(['release', version, entry.get('release_time', ''), link, md5, state,
                            entry.get('_fallback_version', ''), entry.get('_fallback_link', '')])
    stages_line = stages.split('\n', 1)[0]

    models_file = _read_api_file(api_dir, 'models')
    models_line = '\n'.join(ln for ln in (models_file or '').splitlines() if ln.startswith(lower))
    if not models_line:
        meta = models_metadata.get(code, {})
        models_line = '\t'.join([lower, meta.get('type', 'ROUTER'), meta.get('name', code), version])

    all_json = {'version': version, 'release_time': entry.get('release_time', ''), 'download': link, 'md5': md5,
                'changelog': changelog_url, 'link_ok': entry.get('_link_ok', True)}
    all_text = _read_api_file(api_dir, 'all.json')
    if all_text:
        try:
            all_json = json.loads(all_text).get(lower, {}).get('release', all_json)
        except ValueError:
            pass

    return {
        'version': version,
        'url': link,
        'date': entry.get('release_time', ''),
        'hash': md5,
        'changelog': f'{first_line} ...' if first_line else '',
        'summary': summary.rstrip('\n'),
        'branches': branches.rstrip('\n'),
        'stages': stages_line,
        'stages_all': stages.rstrip('\n'),
        'models': models_line,
        'all.json': '{"%s": {"release": %s, ...}, ...}' % (lower, json.dumps(all_json, ensure_ascii=False)),
        'status.json': ('{"generated_at": "...", "summary": {"entries": ..., "head_requests": ..., "unreachable": ..., '
                        '"models_without_api_data": ...}, "unreachable": [...], ...}'),
    }


def api_endpoints(samples):
    """(path, description, example output) of every flat-file API endpoint."""
    return [
        ('/api/<model>/<stage>/version', 'Version number', samples['version']),
        ('/api/<model>/<stage>/url', 'Download URL on fw.gl-inet.com', samples['url']),
        ('/api/<model>/<stage>/date', 'Release date and time as published by GL.iNet', samples['date']),
        ('/api/<model>/<stage>/hash', 'MD5 checksum, empty when GL.iNet publishes none', samples['hash']),
        ('/api/<model>/<stage>/changelog', 'Changelog as plain text', samples['changelog']),
        ('/api/<model>/<stage>/', 'All of the above as key: value lines', samples['summary']),
        ('/api/<model>/branches', 'Stages of the model, one per line (also at /api/<model>/)', samples['branches']),
        ('/api/<model>/stages', 'One tab-separated line per stage: stage, version, date, URL, MD5, link state, '
                                'fallback version, fallback URL', samples['stages']),
        ('/api/models', 'One tab-separated line per model: code, type, name, release version', samples['models']),
        ('/api/all.json', 'Everything as one JSON document', samples['all.json']),
        ('/api/status.json', 'Result of the daily link check, one object per unreachable download',
         samples['status.json']),
    ]


def docs_examples(code, dl_stage):
    """(label as HTML, label as text, shell lines) of the example scripts."""
    api = f'{SITE_URL}/api/{code.lower()}'
    dl = api_stage_name(dl_stage)
    dl_word = 'beta' if dl_stage == 'BETA' else 'release'
    return [
        ('Latest release of a device:', 'Latest release of a device:',
         [f'curl -s {api}/release/version']),
        ('Compare with the firmware installed on the router (GL.iNet firmware 4.x keeps its version number in '
         '<code>/etc/glversion</code>; <code>wget</code> works on routers without <code>curl</code>):',
         'Compare with the firmware installed on the router (GL.iNet firmware 4.x keeps its version number in '
         '/etc/glversion; wget works on routers without curl):',
         [f'latest=$(wget -qO- {api}/release/version)',
          'installed=$(cat /etc/glversion)',
          'if [ "$latest" = "$installed" ]; then',
          '  echo "Up to date: $installed"',
          'else',
          '  echo "Installed $installed, latest release $latest"',
          'fi']),
        (f'Download the latest {dl_word} into the current directory:',
         f'Download the latest {dl_word} into the current directory:',
         [f'curl -LO "$(curl -s {api}/{dl}/url)"']),
        ('Every router with its release version, without JSON tools (BusyBox <code>awk</code> is enough):',
         'Every router with its release version, without JSON tools (BusyBox awk is enough):',
         [f"curl -s {SITE_URL}/api/models | awk -F'\\t' '$2 == \"ROUTER\" {{ print $1, $4 }}'"]),
        ('Read a value from the JSON with <code>jq</code>:', 'Read a value from the JSON with jq:',
         [f"curl -s {SITE_URL}/api/all.json | jq -r '.{code.lower()}.release.version'"]),
    ]


def model_code_groups(models, models_metadata):
    """[(type name, [(code, name, href or None), ...]), ...] with codes sorted, per category."""
    groups = []
    for m_type, codes in group_models_by_type(models, models_metadata).items():
        if not codes:
            continue
        items = sorted(((c.lower(), models_metadata.get(c, {}).get('name', c), device_page_url(c)) for c in codes),
                       key=lambda item: item[0])
        groups.append((TYPE_NAMES.get(m_type, m_type), items))
    return groups


def _plain_text_pages(code):
    """(path, comment) of the text pages worth knowing."""
    lower = code.lower()
    return [
        ('', 'menu with all categories'),
        ('/routers', 'one category, also: iot, kvm, all'),
        (f'/{NEW_DIR}', f'builds of the last {RECENT_DAYS} days, snapshots left out'),
        (f'/{lower}', 'one device'),
        (f'/{lower}/release', 'one build, with its changelog'),
        (f'/{DOCS_DIR}', 'this page'),
    ]


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def _pre(rows):
    """<pre> block from (command, comment) rows; comments are aligned and dimmed."""
    width = max(len(cmd) for cmd, _ in rows)
    lines = []
    for cmd, comment in rows:
        line = html_lib.escape(cmd)
        if comment:
            line += ' ' * (width - len(cmd) + 2) + f'<span class="c"># {html_lib.escape(comment)}</span>'
        lines.append(line)
    return '<pre>' + '\n'.join(lines) + '</pre>'


def generate_docs_html(models, models_metadata, generated_at):
    """HTML of /docs/: interactive menu, plain-text pages, flat-file API, feeds, examples, model codes."""
    esc = html_lib.escape
    root = '../'
    host = site_host()
    code, dl_stage = docs_example(models)
    lower = code.lower()
    samples = api_samples(models, models_metadata, code)
    stage_list = ', '.join(f'<code>{esc(s)}</code>' for s in docs_stage_names(models))
    open_note = (' <code>beta-openNN</code> is the OpenWrt NN open build in the beta channel.'
                 if any(s.startswith('beta-open') for s in docs_stage_names(models)) else '')
    build_day = esc((generated_at or '')[:10])

    rows = ''.join(
        f'<tr><th scope="row"><code>{esc(path)}</code></th><td>{esc(desc)}<div class="out">{esc(out)}</div></td></tr>'
        for path, desc, out in api_endpoints(samples))

    examples = ''.join(
        f'  <p>{label}</p>\n{_pre([(line, "") for line in lines])}\n'
        for label, _text_label, lines in docs_examples(code, dl_stage))

    code_lists = ''
    for type_name, items in model_code_groups(models, models_metadata):
        lis = []
        for c, name, href in items:
            inner = f'<code>{esc(c)}</code> <span class="n">{esc(name)}</span>'
            lis.append(f'<li><a href="{root}{esc(href, quote=True)}">{inner}</a></li>' if href
                       else f'<li><span class="nolink">{inner}</span></li>')
        code_lists += (f'  <h3>{esc(type_name)} <small>{len(items)}</small></h3>\n'
                       f'  <ul class="codes">{"".join(lis)}</ul>\n')

    jump = ''.join(f'<a href="#{sid}">{esc(title)}</a>' for sid, title in DOCS_SECTIONS)
    text_rows = [(f'curl {host}{path}', comment) for path, comment in _plain_text_pages(code)]

    main = f"""<main class="wrap doc">
  <nav class="jump" aria-label="On this page">{jump}</nav>

  <h2 id="menu">Interactive menu</h2>
  <p>Browse categories, search by name or model code, read changelogs and download a build into the current directory, with an MD5 check where GL.iNet publishes one. It needs only a POSIX shell and <code>curl</code>, <code>wget</code> or <code>uclient-fetch</code>, so it also runs on the router itself (BusyBox is enough).</p>
{_pre([(f'curl -s {SITE_URL}/cli | sh', ''), (f'wget -qO- {SITE_URL}/cli | sh', 'routers without curl')])}
  <p>The script is plain text: <a href="{root}cli/index.txt">read it before you run it</a>. More on the <a href="{root}cli/">terminal menu page</a>.</p>

  <h2 id="text">Plain-text pages</h2>
  <p>Point <code>curl</code> or <code>wget</code> at any page and you get plain text instead of HTML. Every text page ends with the commands for the next step.</p>
{_pre(text_rows)}
  <p class="note">Cloudflare hands the text version to <code>curl</code>, <code>wget</code>, HTTPie and every client that sends <code>Accept: text/plain</code>. Each text page can also be fetched directly as <code>index.txt</code>, for example <a href="{root}{lower}/index.txt"><code>/{esc(lower)}/index.txt</code></a>.</p>

  <h2 id="api">Flat-file API</h2>
  <p>Each value has its own URL and comes back as plain text with a trailing newline, so it drops straight into a shell variable. Replace <code>&lt;model&gt;</code> with a <a href="#codes">model code</a> and <code>&lt;stage&gt;</code> with one of {stage_list}.{open_note} Not every model has every stage; <code>/api/&lt;model&gt;/branches</code> lists the ones it has. Example output is for the {esc(lower)} release as of the build of {build_day}.</p>
  <table class="endpoints"><thead><tr><th scope="col">URL</th><th scope="col">Returns</th></tr></thead><tbody>{rows}</tbody></table>
  <p>The data is rebuilt once a day at {REBUILD_TIME}. A version whose download link did not respond stays listed: <code>link: ok</code> in the key: value lines and <code>"link_ok": true</code> in the JSON tell you whether the file was reachable. When it was not and an older build still downloads, the key: value lines add <code>latest_reachable:</code> and the JSON a <code>latest_reachable</code> object. The <a href="{root}status.html">link status page</a> shows the same check for people.</p>
  <p class="note">Directory URLs under <code>/api/</code> need the trailing slash (or <code>curl -L</code>). The data changes once a day, so there is no point in polling more often.</p>

  <h2 id="feeds">Feeds</h2>
  <p>Atom feeds for feed readers and notification tools. Each entry is one build with its changelog and download link.</p>
  <table><thead><tr><th scope="col">Feed</th><th scope="col">Contains</th></tr></thead><tbody>
    <tr><th scope="row"><a href="{feed_url(root=root)}"><code>/{FEED_FILE}</code></a></th><td>The newest builds of all devices, up to {GLOBAL_FEED_LIMIT}, snapshots left out</td></tr>
    <tr><th scope="row"><a href="{feed_url(code, root=root)}"><code>/{esc(lower)}/{FEED_FILE}</code></a></th><td>Every stage of one device; replace <code>{esc(lower)}</code> with any <a href="#codes">model code</a></td></tr>
  </tbody></table>

  <h2 id="examples">Examples</h2>
{examples}
  <h2 id="codes">Model codes</h2>
  <p>The code is the model number in lower case, as used in GL.iNet's firmware file names. Each one links to the device page.</p>
{code_lists}</main>
"""
    return (page_head(f'API and terminal | {SITE_NAME} (unofficial)',
                      'Use the unofficial GL.iNet firmware overview from scripts and the terminal: interactive menu, '
                      'plain-text pages, flat-file API, JSON and Atom feeds.',
                      canonical=f'{SITE_URL}/{DOCS_DIR}/', root=root, extra_css=DOCS_CSS)
            + site_header(root, 'API and terminal',
                          lead='Everything on this site is also available as plain text and JSON. '
                               'No key, no sign-up, nothing to install.',
                          crumbs=(('All devices', root), ('API and terminal', None)), current='docs')
            + main + site_footer(root, example_model=lower) + '</body>\n</html>\n')


# ---------------------------------------------------------------------------
# Text twin
# ---------------------------------------------------------------------------

def _text_table(rows, indent='  '):
    """Align rows (lists of strings) into columns separated by two spaces."""
    rows = [list(r) for r in rows]
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    return '\n'.join(indent + '  '.join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows)


def _wrap(text, indent=''):
    return textwrap.fill(text, width=DOCS_TEXT_WIDTH, initial_indent=indent, subsequent_indent=indent,
                         break_long_words=False, break_on_hyphens=False)


def _heading(title):
    return ['', title, '-' * len(title)]


def _code_columns(items, cw, nw, indent='  '):
    """Model codes and names in two newspaper columns (code width cw, name width nw)
    when they fit into DOCS_TEXT_WIDTH, one per line otherwise."""
    cells = [f'{c.ljust(cw)}  {n}' for c, n, _ in items]
    col = cw + 2 + nw
    if len(indent) + 2 * col + 4 > DOCS_TEXT_WIDTH or len(items) < 2:
        return [indent + cell for cell in cells]
    half = (len(cells) + 1) // 2
    left, right = cells[:half], cells[half:]
    return [(indent + left[i].ljust(col) + '    ' + (right[i] if i < len(right) else '')).rstrip()
            for i in range(half)]


def generate_docs_text(models, models_metadata, generated_at):
    """Text twin of /docs/ for curl: same sections, same facts, about 100 columns."""
    code, dl_stage = docs_example(models)
    lower = code.lower()
    samples = api_samples(models, models_metadata, code)
    stage_names = docs_stage_names(models)

    title, right = 'API and terminal', f'{SITE_URL}/{DOCS_DIR}'
    first = title + ' ' * max(2, DOCS_TEXT_WIDTH - len(title) - len(right)) + right
    lines = [first, '=' * len(first),
             _wrap('Everything on this site is also available as plain text and JSON. No key, no sign-up, '
                   f'nothing to install. {UNOFFICIAL_NOTE}.'),
             f'Updated {generated_at} - web: {SITE_URL}/{DOCS_DIR}/']

    # Interactive menu
    lines += _heading('Interactive menu')
    lines += [_wrap('Browse categories, search by name or model code, read changelogs and download a build into the '
                    'current directory, with an MD5 check where GL.iNet publishes one. It needs only a POSIX shell and '
                    'curl, wget or uclient-fetch, so it also runs on the router itself (BusyBox is enough).'), '',
              _text_table([[f'curl -s {SITE_URL}/cli | sh', ''],
                           [f'wget -qO- {SITE_URL}/cli | sh', 'routers without curl'],
                           [f'curl {SITE_URL}/cli', 'read the script before you run it']])]

    # Plain-text pages
    lines += _heading('Plain-text pages')
    lines += [_wrap('Point curl or wget at any page and you get plain text instead of HTML. Every text page ends '
                    'with the commands for the next step. Each one can also be fetched directly as index.txt.'), '',
              _text_table([[f'curl {SITE_URL}{path or "/"}', comment] for path, comment in _plain_text_pages(code)])]

    # Flat-file API
    lines += _heading('Flat-file API')
    lines += [_wrap('Each value has its own URL and comes back as plain text with a trailing newline, so it drops '
                    f'straight into a shell variable. <model> is a model code (see below), <stage> one of: '
                    f'{", ".join(stage_names)}.'
                    + (' beta-openNN is the OpenWrt NN open build in the beta channel.'
                       if any(s.startswith('beta-open') for s in stage_names) else '')
                    + ' Not every model has every stage; /api/<model>/branches lists the ones it has.'), '']
    endpoint_rows = []
    for path, desc, _out in api_endpoints(samples):
        wrapped = textwrap.wrap(desc, width=DOCS_TEXT_WIDTH - 36)
        endpoint_rows.append([path, wrapped[0]])
        endpoint_rows += [['', more] for more in wrapped[1:]]
    lines += [_text_table(endpoint_rows), '',
              f'Example output for the {lower} release as of the build of {(generated_at or "")[:10]}:', '']
    stage_fields = '\n'.join('\t'.join(ln.split('\t')[:3]) for ln in samples['stages_all'].splitlines())
    models_lines = samples['models']
    for command, out in ((f'curl -s {SITE_URL}/api/{lower}/release/version', samples['version']),
                         (f'curl -s {SITE_URL}/api/{lower}/release/', samples['summary']),
                         (f'curl -s {SITE_URL}/api/{lower}/branches', samples['branches']),
                         (f'curl -s {SITE_URL}/api/{lower}/stages | cut -f1-3', stage_fields),
                         (f'curl -s {SITE_URL}/api/models | grep ^{lower}', models_lines)):
        lines.append(f'  $ {command}')
        lines += [f'  {ln}'.rstrip() for ln in out.split('\n')]
    lines += ['', _wrap(f'The data is rebuilt once a day at {REBUILD_TIME}. A version whose download link did not '
                        'respond stays listed: "link: ok" in the key: value lines and "link_ok": true in the JSON tell '
                        'you whether the file was reachable. When it was not and an older build still downloads, the '
                        'key: value lines add "latest_reachable:" and the JSON a latest_reachable object. Directory '
                        'URLs under /api/ need the trailing slash (or curl -L).'),
              f'Link check as a page: {SITE_URL}/status.html']

    # Feeds
    lines += _heading('Feeds')
    lines += [_wrap('Atom feeds for feed readers and notification tools. Each entry is one build with its changelog '
                    'and download link.'), '',
              _text_table([[feed_url(absolute=True), f'newest builds of all devices, up to {GLOBAL_FEED_LIMIT}, '
                                                     'no snapshots'],
                           [feed_url(code, absolute=True), 'every stage of one device']])]

    # Examples
    lines += _heading('Examples')
    for _html_label, text_label, commands in docs_examples(code, dl_stage):
        lines += [_wrap(text_label), '\n'.join(f'  {c}' for c in commands), '']

    # Model codes
    lines += _heading('Model codes')[1:]
    lines += [_wrap("The code is the model number in lower case, as used in GL.iNet's firmware file names.")]
    groups = model_code_groups(models, models_metadata)
    everything = [item for _, items in groups for item in items]
    cw = max((len(c) for c, _, _ in everything), default=0)
    nw = max((len(n) for _, n, _ in everything), default=0)
    for type_name, items in groups:
        lines += ['', f'{type_name} ({len(items)})'] + _code_columns(items, cw, nw)

    lines += ['', _text_table([
        ['Open a device:', f'curl {SITE_URL}/<model>', f'e.g. {lower}'],
        ['Interactive:', f'curl -s {SITE_URL}/cli | sh', ''],
        ['Menu:', f'curl {SITE_URL}/', ''],
    ], indent=''), '']
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# /cli/ landing page
# ---------------------------------------------------------------------------

def cli_page_html():
    """Landing page of /cli/ for browsers: how to start the terminal menu and what it does."""
    root = '../'
    main = f"""<main class="wrap doc">
  <h2 id="start">Start the menu</h2>
  <p>One line in any terminal, on your computer or on the router itself:</p>
{_pre([(f'curl -s {SITE_URL}/cli | sh', ''), (f'wget -qO- {SITE_URL}/cli | sh', 'routers without curl')])}
  <p>It needs only a POSIX shell with <code>awk</code>, <code>sed</code> and <code>cut</code> (BusyBox on OpenWrt is enough) and one of <code>curl</code>, <code>wget</code> or <code>uclient-fetch</code>. Menu input is read from the terminal, so piping the script into <code>sh</code> works.</p>

  <h2 id="features">What it does</h2>
  <ul class="can">
    <li>Lists routers, IoT devices and KVM devices, or finds a device by model code or search term.</li>
    <li>Shows every stage of a device with version and release date, and flags downloads that did not respond in the last check.</li>
    <li>Opens a changelog in your pager.</li>
    <li>Downloads a build into the current directory and checks the MD5 where GL.iNet publishes one. If the newest download did not respond, it offers the newest older build that still downloads.</li>
    <li>Prints the download URL for your own scripts.</li>
  </ul>

  <h2 id="read">Read it first</h2>
  <p>The script is plain text: <a href="index.txt">read it before you run it</a>. It only talks to <code>{site_host()}</code> and, when you download a build, to <code>fw.gl-inet.com</code>.</p>
  <p>Prefer single commands? The <a href="{root}{DOCS_DIR}/">API and terminal page</a> lists the plain-text pages, the flat-file API and the feeds.</p>
</main>
"""
    return (page_head(f'Terminal menu | {SITE_NAME} (unofficial)',
                      'Browse GL.iNet firmware versions, read changelogs and download builds from the terminal, '
                      'also on the router itself.',
                      canonical=f'{SITE_URL}/cli/', root=root, extra_css=DOCS_CSS)
            + site_header(root, 'Terminal menu',
                          lead='Browse firmware versions, read changelogs and download builds without leaving the shell.',
                          crumbs=(('All devices', root), ('Terminal menu', None)))
            + main + site_footer(root) + '</body>\n</html>\n')


def generate_docs_pages(models, models_metadata, generated_at):
    """Write docs/index.html, docs/index.txt and cli/index.html."""
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(generate_docs_html(models, models_metadata, generated_at))
    with open(os.path.join(DOCS_DIR, 'index.txt'), 'w', encoding='utf-8') as f:
        f.write(generate_docs_text(models, models_metadata, generated_at))
    os.makedirs('cli', exist_ok=True)
    with open(os.path.join('cli', 'index.html'), 'w', encoding='utf-8') as f:
        f.write(cli_page_html())
