"""Plain-text twins (index.txt) for curl, wget & co.

Cloudflare rewrites requests from those clients to these files, see cloudflare/README.md.
The pages form a small menu tree:  /  ->  /routers /iot /kvm /all /new  ->  /<model>  ->  /<model>/<stage>
"""
import html as html_lib
import os

from sitelib.core import *  # noqa: F401,F403

# The interactive menu script lives next to generate_page.py in the repository root.
CLI_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cli.sh')

TEXT_WIDTH = 78

def text_table(rows, headers=None):
    """Align rows (lists of strings) into columns separated by two spaces."""
    rows = [list(r) for r in rows]
    all_rows = ([list(headers)] if headers else []) + rows
    widths = [max(len(r[i]) for r in all_rows) for i in range(len(all_rows[0]))]
    return '\n'.join('  '.join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in all_rows)

def text_title(left, right=''):
    """Title line with `right` flush at TEXT_WIDTH, underlined with '='."""
    if right and len(left) + 2 + len(right) <= TEXT_WIDTH:
        line = left + ' ' * (TEXT_WIDTH - len(left) - len(right)) + right
    else:
        line = f'{left}  {right}'.rstrip()
    return [line, '=' * len(line)]

def text_version(entry):
    """Version for text output; a trailing '!' marks a download that did not respond."""
    version = entry.get('version', 'N/A')
    return version if entry.get('_link_ok', True) else version + '!'

def text_notes(has_open, flagged, indent=''):
    notes = []
    if has_open:
        notes.append(f'{indent}beta-openNN  OpenWrt NN open build (beta channel)')
    if flagged:
        notes.append(f'{indent}x.y.z!       download link did not respond in the last build, see {SITE_URL}/status.html')
    return notes

def text_group_table(codes, models, models_metadata, columns):
    """Rows of the model table for one group; returns (table, has_open, flagged)."""
    rows, has_open, flagged = [], False, False
    for code in codes:
        cells = []
        for stage in columns:
            info = models[code].get(stage)
            parts = [text_version(info)] if info else []
            if stage == 'BETA':
                for s in sorted(k for k in models[code] if k.startswith('BETA_OPEN')):
                    parts.append(f"op{models[code][s].get('_openwrt_base', '24')}:{text_version(models[code][s])}")
                    has_open = True
            flagged = flagged or any(p.endswith('!') for p in parts)
            cells.append(' '.join(parts) if parts else '-')
        rows.append([code.lower(), models_metadata.get(code, {}).get('name', code)] + cells)
    return text_table(rows, ['MODEL', 'NAME'] + columns), has_open, flagged

def generate_text_index(models, models_metadata, generated_at):
    """The menu served to curl as / ."""
    grouped = group_models_by_type(models, models_metadata)
    lines = text_title(SITE_NAME, SITE_URL.split('://', 1)[-1])
    lines += ['Latest verified firmware for GL.iNet routers, IoT and KVM devices.',
              f'Updated {generated_at} - web: {SITE_URL}/', '']
    rows, n = [], 0
    for m_type in ['ROUTER', 'IOT', 'KVM']:
        codes = grouped.get(m_type, [])
        if not codes:
            continue
        n += 1
        rows.append([f'  [{n}]', TYPE_NAMES.get(m_type, m_type), f'{len(codes)} models', f'curl {SITE_URL}/{TYPE_SLUGS[m_type]}'])
    rows.append(['  [*]', 'All models as one table', '', f'curl {SITE_URL}/all'])
    rows.append(['  [i]', 'Interactive menu', '', f'curl -s {SITE_URL}/cli | sh'])
    lines.append(text_table(rows))
    lines += ['', text_table([
        ['Jump to a device:', f'curl {SITE_URL}/<model>', 'e.g. mt3000, mt6000, be9300'],
        ['One value only:', f'curl {SITE_URL}/api/<model>/<stage>/version', 'also: url, date, hash, changelog'],
        ['JSON for scripts:', f'curl {SITE_URL}/api/all.json', ''],
    ]), '']
    return '\n'.join(lines)

def generate_text_group(m_type, codes, models, models_metadata, generated_at):
    """Category page served as /routers, /iot or /kvm."""
    slug = TYPE_SLUGS[m_type]
    columns = [s for s in overview_stage_columns(models) if any(s in models[c] for c in codes)]
    lines = text_title(f'{TYPE_NAMES.get(m_type, m_type)} ({len(codes)})', f'{SITE_URL}/{slug}')
    lines += [f'Updated {generated_at}', '']
    table, has_open, flagged = text_group_table(codes, models, models_metadata, columns)
    lines.append(table)
    notes = text_notes(has_open, flagged)
    if notes:
        lines += [''] + notes
    example = next((c.lower() for c in codes if device_page_url(c)), 'mt3000')
    lines += ['', text_table([
        ['Open a device:', f'curl {SITE_URL}/<model>', f'e.g. curl {SITE_URL}/{example}'],
        ['Back:', f'curl {SITE_URL}/', ''],
    ]), '']
    return '\n'.join(lines)

def generate_text_all(models, models_metadata, generated_at):
    """Every model in one table, served as /all."""
    grouped = group_models_by_type(models, models_metadata)
    columns = overview_stage_columns(models)
    lines = text_title(f'{SITE_NAME} - all models', f'{SITE_URL}/all')
    lines += [f'Updated {generated_at}', '']
    has_open = flagged = False
    for m_type in ['ROUTER', 'IOT', 'KVM']:
        codes = grouped.get(m_type, [])
        if not codes:
            continue
        table, o, f = text_group_table(codes, models, models_metadata, columns)
        has_open, flagged = has_open or o, flagged or f
        lines += [f'{TYPE_NAMES.get(m_type, m_type)} ({len(codes)})', table, '']
    notes = text_notes(has_open, flagged)
    if notes:
        lines += notes + ['']
    lines += [text_table([
        ['Open a device:', f'curl {SITE_URL}/<model>'],
        ['Back:', f'curl {SITE_URL}/'],
    ]), '']
    return '\n'.join(lines)

def generate_device_text(code, stages, meta, generated_at):
    """Device menu served as /<model>."""
    code_lower = code.lower()
    m_type = meta.get('type', 'ROUTER')
    lines = text_title(f"{meta.get('name', code)} ({code})", TYPE_NAMES.get(m_type, m_type))
    lines += [f'Updated {generated_at} - web: {SITE_URL}/{code_lower}/', '']
    ordered = ordered_stages(stages)
    if not ordered:
        lines += ['No verified firmware download is currently available for this model.']
    else:
        rows = []
        for n, stage in enumerate(ordered, 1):
            info = stages[stage]
            s_api = api_stage_name(stage)
            rows.append([f'  [{n}]', s_api, text_version(info), (info.get('release_time') or '')[:10] or '-', f'curl {SITE_URL}/{code_lower}/{s_api}'])
        lines.append(text_table(rows))
        notes = text_notes(any(s.startswith('BETA_OPEN') for s in ordered),
                           any(not stages[s].get('_link_ok', True) for s in ordered), indent='  ')
        if notes:
            lines += [''] + notes
        latest_stage = ordered[0]
        latest = stages[latest_stage]
        first = api_stage_name(latest_stage)
        link = entry_link(latest)
        if not latest.get('_link_ok', True) and latest.get('_fallback_link'):
            link = latest['_fallback_link']
        shortcuts = [['  changelog', f'curl {SITE_URL}/api/{code_lower}/{first}/changelog', '']]
        if link:
            note = '' if link == entry_link(latest) else f"({latest.get('_fallback_version', '?')}, newest build whose download responds)"
            shortcuts.append(['  download', f'curl -LO {link}', note])
        lines += ['', f'Shortcuts for {first} {latest.get("version", "N/A")}:', text_table(shortcuts)]
    lines += ['', text_table([['Back:', f'curl {SITE_URL}/{TYPE_SLUGS.get(m_type, "")}'], ['Menu:', f'curl {SITE_URL}/']]), '']
    return '\n'.join(lines)

def generate_stage_text(code, stage, info, meta, generated_at):
    """Stage page served as /<model>/<stage>: all details plus the changelog."""
    code_lower = code.lower()
    s_api = api_stage_name(stage)
    version = info.get('version', 'N/A')
    link = entry_link(info)
    md5_hash = (info.get('download') or [{}])[0].get('md5', '') or ''
    lines = text_title(f"{meta.get('name', code)} ({code}) - {s_api} {version}", f'{SITE_URL}/{code_lower}/{s_api}')
    fields = [
        ['Version:', version],
        ['Released:', info.get('release_time', '') or '-'],
        ['Download:', link or '-'],
        ['MD5:', md5_hash or 'not published by GL.iNet'],
    ]
    if info.get('_is_open'):
        fields.append(['Build:', f"OpenWrt {info.get('_openwrt_base', '24')} open build"])
    if info.get('_link_ok', True):
        fields.append(['Link check:', f'ok ({generated_at})'])
    else:
        fields.append(['Link check:', f"unreachable in the last build ({info.get('_link_reason', 'unknown')}); the version stays listed"])
        if info.get('_fallback_link'):
            fields.append(['', f"newest reachable build: {info.get('_fallback_version', 'N/A')} {info['_fallback_link']}"])
    lines += [text_table(fields), '']
    actions = []
    if link:
        actions.append(['  download', f'curl -LO {link}'])
    actions += [
        ['  changelog', f'curl {SITE_URL}/api/{code_lower}/{s_api}/changelog', '(also below)'],
        ['  one value', f'curl {SITE_URL}/api/{code_lower}/{s_api}/version', 'also: url, date, hash'],
    ]
    lines += [text_table(actions), '', text_table([['Back:', f'curl {SITE_URL}/{code_lower}'], ['Menu:', f'curl {SITE_URL}/']])]
    changelog = (info.get('changelog') or '').strip()
    lines += ['', 'Changelog', '---------', changelog if changelog else '(no changelog published for this build)', '']
    return '\n'.join(lines)

def redirect_stub_html(target, label):
    """Tiny HTML page for directories that only exist for their index.txt:
    browsers get sent to the real page instead of a 404."""
    esc_target = html_lib.escape(target, quote=True)
    return f"""<!DOCTYPE html>
{DEVICE_PAGE_MARKER}
<html lang="en"><head><meta charset="UTF-8"><meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={esc_target}"><title>{html_lib.escape(label)}</title></head>
<body><p>Redirecting to <a href="{esc_target}">{html_lib.escape(label)}</a>.</p></body></html>
"""

def generate_text_pages(models, models_metadata, generated_at):
    """Write the text menu tree next to the HTML pages. Returns the number of
    device text files written."""
    with open('index.txt', 'w', encoding='utf-8') as f:
        f.write(generate_text_index(models, models_metadata, generated_at))

    grouped = group_models_by_type(models, models_metadata)
    for m_type, slug in TYPE_SLUGS.items():
        os.makedirs(slug, exist_ok=True)
        with open(os.path.join(slug, 'index.txt'), 'w', encoding='utf-8') as f:
            f.write(generate_text_group(m_type, grouped.get(m_type, []), models, models_metadata, generated_at))
        with open(os.path.join(slug, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(redirect_stub_html(f'../#{m_type.lower()}', TYPE_NAMES.get(m_type, m_type)))

    os.makedirs('all', exist_ok=True)
    with open(os.path.join('all', 'index.txt'), 'w', encoding='utf-8') as f:
        f.write(generate_text_all(models, models_metadata, generated_at))
    with open(os.path.join('all', 'index.html'), 'w', encoding='utf-8') as f:
        f.write(redirect_stub_html('../', SITE_NAME))

    os.makedirs('cli', exist_ok=True)
    if os.path.exists(CLI_SCRIPT):
        with open(CLI_SCRIPT, encoding='utf-8') as f:
            script = f.read().replace('__SITE_URL__', SITE_URL)
        with open(os.path.join('cli', 'index.txt'), 'w', encoding='utf-8') as f:
            f.write(script)
    else:
        print("  WARNING cli.sh not found, /cli will be empty")
    # cli/index.html (the landing page for browsers) is written by sitelib.docs_page

    written = 0
    for code, stages in models.items():
        if device_page_url(code) is None:
            continue
        page_dir = code.lower()
        meta = models_metadata.get(code, {})
        os.makedirs(page_dir, exist_ok=True)
        with open(os.path.join(page_dir, 'index.txt'), 'w', encoding='utf-8') as f:
            f.write(generate_device_text(code, stages, meta, generated_at))
        for stage, info in stages.items():
            s_api = api_stage_name(stage)
            stage_dir = os.path.join(page_dir, s_api)
            os.makedirs(stage_dir, exist_ok=True)
            with open(os.path.join(stage_dir, 'index.txt'), 'w', encoding='utf-8') as f:
                f.write(generate_stage_text(code, stage, info, meta, generated_at))
            with open(os.path.join(stage_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(redirect_stub_html(f'../#{s_api}', f"{meta.get('name', code)} {s_api}"))
        written += 1
    return written
