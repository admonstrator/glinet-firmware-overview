"""Device pages (<model>/index.html at the site root)."""
import html as html_lib
import os
import shutil

from sitelib.core import *  # noqa: F401,F403
from sitelib.design import *  # noqa: F401,F403

def generate_device_page(code, stages, meta, generated_at):
    """Build the standalone HTML page of a single model, served at /<model>/."""
    code_lower = code.lower()
    full_name = meta.get('name', code)
    m_type = meta.get('type', 'ROUTER')
    icon = TYPE_ICONS.get(m_type, 'fa-microchip')
    type_name = TYPE_NAMES.get(m_type, m_type)
    esc_name = html_lib.escape(full_name)
    esc_code = html_lib.escape(code)
    canonical = f"{SITE_URL}/{device_page_url(code)}"
    # Device pages live one directory level below the site root
    root = '../'
    api_rel = f"{root}api/{code_lower}"
    api_abs = f"{SITE_URL}/api/{code_lower}"

    display_stages = ordered_stages(stages)

    summary_parts = []
    rows = []
    changelog_blocks = []
    endpoint_items = []
    for stage in display_stages:
        info = stages[stage]
        s_api = api_stage_name(stage)
        label = base_stage(stage)
        version = info.get('version', 'N/A')
        esc_version = html_lib.escape(version)
        release_time = info.get('release_time', '')
        release_date = release_time.split(' ')[0]
        download_link = html_lib.escape(entry_link(info) or '#', quote=True)
        md5_hash = (info.get('download') or [{}])[0].get('md5', '') or ''
        changelog_text = (info.get('changelog') or '').strip()
        badge = open_badge_html(info)
        link_ok = info.get('_link_ok', True)

        summary_parts.append(f"{stage_label(stage, info)} {version}")

        hash_html = f'<div class="timestamp font-monospace" title="MD5">MD5 {html_lib.escape(md5_hash)}</div>' if md5_hash else ''
        if link_ok:
            version_html = f'<span class="fw-version">{esc_version}</span>'
            download_cell = (f'<a href="{download_link}" target="_blank" class="btn btn-sm btn-outline-primary text-nowrap">'
                             f'<i class="fas fa-download me-1"></i>Download</a>')
        else:
            # The version stays published; only the download is marked as broken (same rule as the overview).
            hint = html_lib.escape(
                f"Download link unreachable ({info.get('_link_reason', 'unknown')}) - see the status page", quote=True)
            version_html = f'<span class="fw-version text-muted">{esc_version}</span>'
            download_cell = (f'<a href="{root}status.html" class="badge bg-warning text-dark text-decoration-none" title="{hint}">'
                             f'<i class="fas fa-triangle-exclamation me-1"></i>Unreachable</a>')
            if info.get('_fallback_link'):
                fb_link = html_lib.escape(info['_fallback_link'], quote=True)
                fb_version = html_lib.escape(info.get('_fallback_version', 'N/A'))
                download_cell += (f'<div class="mt-1"><a href="{fb_link}" target="_blank" class="btn btn-sm btn-outline-secondary text-nowrap" '
                                  f'title="Newest version with a working download"><i class="fas fa-download me-1"></i>{fb_version} instead</a></div>')

        if changelog_text:
            changelog_cell = f'<a href="#changelog-{s_api}" class="text-decoration-none" title="Jump to changelog"><i class="fas fa-file-lines me-1"></i>Changelog</a>'
            changelog_blocks.append(f"""
                <details id="changelog-{s_api}" class="mb-3"{' open' if not changelog_blocks else ''}>
                    <summary class="fw-bold"><span class="stage-{label}">{label}</span>{badge} <span class="fw-version">{esc_version}</span> <span class="timestamp ms-1">{html_lib.escape(release_date)}</span>
                        <a href="{api_rel}/{s_api}/changelog" target="_blank" class="small text-decoration-none ms-2" title="Open as plain text">TXT <i class="fas fa-arrow-up-right-from-square small"></i></a></summary>
                    <pre class="changelog-text mt-2">{html_lib.escape(changelog_text)}</pre>
                </details>""")
        else:
            changelog_cell = '<span class="text-muted">-</span>'

        rows.append(f"""
                        <tr id="{s_api}">
                            <td class="ps-4"><span class="fw-bold stage-{label}">{label}</span>{badge}</td>
                            <td>{version_html}{hash_html}</td>
                            <td class="text-nowrap"><span class="timestamp" title="{html_lib.escape(release_time, quote=True)}">{html_lib.escape(release_date)}</span></td>
                            <td>{download_cell}</td>
                            <td>{changelog_cell}</td>
                        </tr>""")

        attr_links = ' &middot; '.join(
            f'<a href="{api_rel}/{s_api}/{attr}" target="_blank">{attr}</a>'
            for attr in ['version', 'url', 'date', 'hash', 'changelog']
        )
        endpoint_items.append(f'<li class="mb-1"><strong>{label}{badge}:</strong> <code>{api_abs}/{s_api}/</code> <span class="ms-1">[ {attr_links} ]</span></li>')

    if rows:
        firmware_section = f"""
    <h3 class="section-title"><i class="fas fa-download text-primary"></i> Firmware versions</h3>
    <div class="card">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover table-striped mb-0 align-middle">
                    <thead class="table-dark">
                        <tr>
                            <th scope="col" class="ps-4">Stage</th>
                            <th scope="col">Version</th>
                            <th scope="col">Released</th>
                            <th scope="col">Download</th>
                            <th scope="col">Changelog</th>
                        </tr>
                    </thead>
                    <tbody>{''.join(rows)}
                    </tbody>
                </table>
            </div>
        </div>
    </div>"""
        example_stage = api_stage_name(display_stages[0])
    else:
        firmware_section = """
    <div class="alert alert-warning shadow-sm" role="alert">
        <i class="fas fa-triangle-exclamation me-2"></i> No verified firmware download is currently available for this model.
    </div>"""
        example_stage = 'release'

    changelog_section = ''
    if changelog_blocks:
        changelog_section = f"""
    <h3 class="section-title"><i class="fas fa-file-lines text-primary"></i> Changelogs</h3>
    <div class="card">
        <div class="card-body">{''.join(changelog_blocks)}
        </div>
    </div>"""

    description = f"Latest verified GL.iNet firmware for {full_name} ({code})"
    if summary_parts:
        description += ": " + ", ".join(summary_parts)
    description += "."

    head = html_head(f"{full_name} Firmware | {SITE_NAME}", description=description, canonical=canonical, root=root)

    return f"""<!DOCTYPE html>
{DEVICE_PAGE_MARKER}
<html lang="en">
{head}
<body>

<div class="container">
    <nav aria-label="breadcrumb" class="mb-3">
        <ol class="breadcrumb small mb-0">
            <li class="breadcrumb-item"><a href="{root}" class="text-decoration-none"><i class="fas fa-microchip me-1"></i>GL.iNet Firmware Overview</a></li>
            <li class="breadcrumb-item"><a href="{root}#{m_type.lower()}" class="text-decoration-none">{html_lib.escape(type_name)}</a></li>
            <li class="breadcrumb-item active" aria-current="page">{esc_name}</li>
        </ol>
    </nav>

    <div class="row justify-content-center">
        <div class="col-12 text-center mb-4">
            <h1><i class="fas {icon} text-primary"></i> {esc_name}</h1>
            <p class="lead mb-2">Latest verified firmware versions</p>
            <div class="mb-2">
                <span class="badge bg-dark font-monospace">{esc_code}</span>
                <span class="badge bg-secondary">{html_lib.escape(type_name)}</span>
            </div>
            <p class="timestamp mb-1">Last updated: {generated_at}</p>
            <p class="timestamp">Permalink: <a href="{canonical}" class="text-decoration-none font-monospace">{canonical}</a></p>
        </div>
    </div>
{firmware_section}
{changelog_section}
    <h3 class="section-title"><i class="fas fa-code text-primary"></i> API endpoints for this device</h3>
    <div class="card">
        <div class="card-body api-info m-0">
            <ul class="small mb-2">
                <li class="mb-1"><strong>Available stages:</strong> <code>{api_abs}/branches</code> <span class="ms-1">[ <a href="{api_rel}/branches" target="_blank">open</a> ]</span></li>
                {''.join(endpoint_items)}
            </ul>
            <p class="small mb-0"><strong>Example:</strong> <code>curl -s {api_abs}/{example_stage}/version</code></p>
        </div>
    </div>

    <footer>
        <div class="row justify-content-center">
            <div class="col-md-8">
                <p class="mb-2"><a href="{root}" class="text-decoration-none"><i class="fas fa-arrow-left me-1"></i> Back to the firmware overview</a></p>
                <p class="mb-0 mt-3 small">Data is automatically verified and updated daily from GL.iNet Firmware API.</p>
            </div>
        </div>
    </footer>
</div>

</body>
</html>
"""

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
