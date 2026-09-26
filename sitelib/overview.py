"""The overview page (index.html)."""
import html as html_lib

from sitelib.core import *  # noqa: F401,F403
from sitelib.design import *  # noqa: F401,F403

def generate_html(models, models_metadata, diagnostics, generated_at=None):
    generated_at = generated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    grouped_models = group_models_by_type(models, models_metadata)
    sorted_stages = overview_stage_columns(models)

    issue_count = sum(1 for d in diagnostics if d['status'] != 'ok')
    if issue_count:
        status_link = (f'<a href="status.html" class="text-decoration-none">'
                       f'<i class="fas fa-triangle-exclamation text-warning"></i> '
                       f'{issue_count} download{"" if issue_count == 1 else "s"} unreachable</a>')
    else:
        status_link = ('<a href="status.html" class="text-decoration-none">'
                       '<i class="fas fa-circle-check text-success"></i> All links verified</a>')

    head = html_head(
        SITE_NAME,
        description="Latest verified GL.iNet firmware versions for all routers, IoT and KVM devices, with a flat-file API.",
        canonical=f"{SITE_URL}/",
    )

    html = f"""
<!DOCTYPE html>
<html lang="en">
{head}
<body>

<div class="container">
    <div class="row justify-content-center">
        <div class="col-12 text-center mb-4">
            <h1><i class="fas fa-microchip text-primary"></i> GL.iNet Firmware Overview</h1>
            <p class="lead">Latest verified firmware versions</p>
            <div class="mb-2">
                <span class="badge bg-info text-dark">Community Project by <a href="https://admon.me" target="_blank" class="text-dark text-decoration-none fw-bold">admon (admon.me)</a></span>
            </div>
            <p class="timestamp mb-1">Last updated: {generated_at}</p>
            <p class="timestamp">{status_link}</p>
        </div>
    </div>

    <div id="recent"></div>
    <div class="row justify-content-center search-container">
        <div class="col-md-8">
            <div class="input-group">
                <span class="input-group-text bg-white"><i class="fas fa-search text-muted"></i></span>
                <input type="text" id="searchInput" class="form-control form-control-lg border-start-0" placeholder="Search for model (e.g. AX1800) or code (e.g. flint)...">
            </div>
        </div>
    </div>

    <div class="row justify-content-center mb-4">
        <div class="col-md-10">
            <div class="accordion shadow-sm" id="apiAccordion">
                <div class="accordion-item border-0">
                    <h2 class="accordion-header" id="headingAPI">
                        <button class="accordion-button collapsed fw-bold bg-white text-primary" type="button" data-bs-toggle="collapse" data-bs-target="#collapseAPI" aria-expanded="false" aria-controls="collapseAPI">
                            <i class="fas fa-code me-2"></i> How to use the Flat-File API
                        </button>
                    </h2>
                    <div id="collapseAPI" class="accordion-collapse collapse" aria-labelledby="headingAPI" data-bs-parent="#apiAccordion">
                        <div class="accordion-body api-info m-0 border-top">
                            <p class="small mb-2">
                                This dashboard provides a machine-readable flat-file API. You can access firmware information directly:
                            </p>
                            <ul class="small mb-0">
                                <li><strong>Available stages:</strong> <code>/api/&lt;model&gt;/branches</code> (e.g., <code>/api/ax1800/branches</code>)</li>
                                <li><strong>Version string:</strong> <code>/api/&lt;model&gt;/&lt;stage&gt;/version</code> (e.g., <code>/api/ax1800/release/version</code>)</li>
                                <li><strong>Download URL:</strong> <code>/api/&lt;model&gt;/&lt;stage&gt;/url</code></li>
                                <li><strong>Latest changelog:</strong> <code>/api/&lt;model&gt;/&lt;stage&gt;/changelog</code></li>
                                <li><strong>Specific attributes:</strong> <code>/api/&lt;model&gt;/&lt;stage&gt;/[version|url|date|hash|changelog]</code></li>
                                <li><strong>Consolidated data:</strong> <code>/api/all.json</code></li>
                                <li><strong>Build &amp; link status:</strong> <code>/api/status.json</code> (see the <a href="status.html">status page</a>)</li>
                                <li><strong>Device page (deep link):</strong> <code>/&lt;model&gt;/</code> (e.g., <a href="{device_page_url('ax1800')}"><code>/ax1800/</code></a>) &ndash; click a model name below</li>
                                <li><strong>Terminal:</strong> <code>curl {SITE_URL}/</code> answers with a plain-text menu, <code>curl -s {SITE_URL}/cli | sh</code> starts an <a href="cli/">interactive menu</a> (works on the router too)</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    """

    for m_type in ['ROUTER', 'IOT', 'KVM']:
        codes = grouped_models.get(m_type, [])
        if not codes:
            continue
            
        icon = TYPE_ICONS.get(m_type, 'fa-device')
        name = TYPE_NAMES.get(m_type, m_type)

        html += f"""
    <h3 class="section-title" id="{m_type.lower()}"><i class="fas {icon} text-primary"></i> {name}</h3>
    <div class="card mb-5">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover table-striped mb-0 firmware-table">
                    <thead class="table-dark">
                        <tr>
                            <th scope="col" class="ps-4" style="min-width: 200px;">Model</th>
                            {''.join([f'<th scope="col">{s}</th>' for s in sorted_stages])}
                        </tr>
                    </thead>
                    <tbody>
        """

        for code in codes:
            meta = models_metadata.get(code, {})
            full_name = html_lib.escape(meta.get('name', code))
            page_url = device_page_url(code)
            name_html = f'<a href="{page_url}" class="model-link" title="Open device page for {full_name}">{full_name} <i class="fas fa-link ms-1"></i></a>' if page_url else full_name
            
            html += f"""
            <tr id="{code.lower()}">
                <td class='ps-4'>
                    <div class="fw-bold">{name_html}</div>
                    <div class="text-muted small" style="font-size: 0.7rem;">{html_lib.escape(code)}</div>
                </td>
            """
            for stage in sorted_stages:
                info = models[code].get(stage)
                # Gather all OpenWrt "open" variants (op24, op25, ...) alongside the BETA column
                open_stages = sorted(s for s in models[code] if s.startswith('BETA_OPEN')) if stage == 'BETA' else []
                # (actual_stage, entry) pairs to render in this cell
                render_list = [(stage, info)] if info else []
                render_list += [(s, models[code][s]) for s in open_stages]
                if render_list:
                    cells = []
                    for entry_stage, entry_info in render_list:
                        version = entry_info.get('version', 'N/A')
                        release_time = entry_info.get('release_time', '').split(' ')[0]
                        download_link = entry_link(entry_info) or '#'
                        changelog_text = (entry_info.get('changelog') or '').strip()
                        timestamp_html = f'<span class="timestamp">{release_time}</span>'
                        if changelog_text:
                            changelog_path = f"api/{code.lower()}/{api_stage_name(entry_stage)}/changelog"
                            timestamp_html = f'<a class="timestamp text-decoration-none" href="{changelog_path}" target="_blank" title="Open latest changelog TXT">{release_time} <i class="fas fa-file-lines small ms-1"></i></a>'
                        open_badge = open_badge_html(entry_info)
                        fallback_html = ''
                        if entry_info.get('_link_ok', True):
                            version_html = (f'<a href="{download_link}" target="_blank" '
                                            f'class="fw-version text-decoration-none stage-{stage}">'
                                            f'{version} <i class="fas fa-download small ms-1"></i></a>')
                        else:
                            # The version stays published; only the download is marked as broken.
                            hint = html_lib.escape(
                                f"Download link unreachable ({entry_info.get('_link_reason', 'unknown')}) "
                                f"- see the status page", quote=True)
                            version_html = (f'<span class="fw-version text-muted">{version}</span> '
                                            f'<a href="status.html" class="text-decoration-none" title="{hint}">'
                                            f'<i class="fas fa-triangle-exclamation small text-warning"></i></a>')
                            if entry_info.get('_fallback_link'):
                                fb_version = entry_info['_fallback_version']
                                fb_link = html_lib.escape(entry_info['_fallback_link'], quote=True)
                                fallback_html = (
                                    f'<a href="{fb_link}" target="_blank" class="fallback-link text-decoration-none" '
                                    f'title="Newest version with a working download">'
                                    f'<i class="fas fa-download small me-1"></i>{fb_version} instead</a>')
                        cells.append(f'''
                                <div class="d-flex flex-column{'  border-top pt-1 mt-1' if entry_info.get('_is_open') and info else ''}">
                                    {version_html}
                                    <div>{timestamp_html}{open_badge}</div>
                                    {fallback_html}
                                </div>''')
                    html += f"<td>{''.join(cells)}</td>"
                else:
                    html += "<td><span class='text-muted'>-</span></td>"
            html += "</tr>"

        html += """
                    </tbody>
                </table>
            </div>
        </div>
    </div>
        """

    html += """
    <footer>
        <div class="row justify-content-center">
            <div class="col-md-8">
                <p class="mb-0 mt-3 small">Data is automatically verified and updated daily from GL.iNet Firmware API.</p>
            </div>
        </div>
    </footer>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    document.getElementById('searchInput').addEventListener('keyup', function() {
        var input = this.value.toLowerCase();
        var tables = document.querySelectorAll('.firmware-table');
        
        tables.forEach(function(table) {
            var rows = table.querySelectorAll('tbody tr');
            var visibleRows = 0;
            
            rows.forEach(function(row) {
                var text = row.textContent.toLowerCase();
                if (text.includes(input)) {
                    row.style.display = '';
                    visibleRows++;
                } else {
                    row.style.display = 'none';
                }
            });
            
            // Hide the entire table section if no rows are visible
            var card = table.closest('.card');
            var title = card.previousElementSibling;
            if (visibleRows === 0) {
                card.style.display = 'none';
                if (title && title.classList.contains('section-title')) {
                    title.style.display = 'none';
                }
            } else {
                card.style.display = '';
                if (title && title.classList.contains('section-title')) {
                    title.style.display = '';
                }
            }
        });
    });
</script>

</body>
</html>
    """
    return html
