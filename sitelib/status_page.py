"""The build & link status page (status.html)."""
import html as html_lib
from datetime import datetime

from sitelib.core import *  # noqa: F401,F403
from sitelib.design import *  # noqa: F401,F403

STATUS_PAGE_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Build Status - GL.iNet Firmware Overview</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
""" + favicon_links_html() + """
    <style>
        body { background-color: #f8f9fa; padding-top: 20px; }
        .card { margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: none; }
        .card-header { background-color: #343a40; color: white; font-weight: bold; padding: 12px 20px; }
        .timestamp { font-size: 0.8rem; color: #6c757d; }
        .stat-card { background: #fff; border-radius: 8px; padding: 18px; text-align: center;
                     box-shadow: 0 4px 6px rgba(0,0,0,0.08); height: 100%; }
        .stat-value { font-size: 1.8rem; font-weight: bold; line-height: 1.1; }
        .stat-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #6c757d; }
        .reason { font-family: monospace; font-size: 0.85rem; }
        .fw-version { font-family: monospace; font-weight: bold; }
        .file-link { font-family: monospace; font-size: 0.75rem; word-break: break-all; }
        .section-title { margin-bottom: 15px; font-weight: bold; color: #495057;
                         display: flex; align-items: center; }
        .section-title i { margin-right: 10px; }
        footer { margin-top: 50px; padding: 40px 0; text-align: center; color: #6c757d;
                 font-size: 0.9rem; border-top: 1px solid #dee2e6; }
    </style>
</head>
<body>
<div class="container">
"""

def stat_card(value, label, color=''):
    color_class = f' text-{color}' if color else ''
    return f"""
        <div class="col-6 col-md-4 col-lg-2 mb-3">
            <div class="stat-card">
                <div class="stat-value{color_class}">{value}</div>
                <div class="stat-label">{label}</div>
            </div>
        </div>"""

def generate_status_html(diagnostics, empty_models, generated_at=None):
    esc = html_lib.escape

    unreachable = [d for d in diagnostics if d['status'] == 'unreachable']
    attempts = sum(d['attempts'] + d['candidates_probed'] for d in diagnostics)

    html = STATUS_PAGE_HEAD
    html += f"""
    <div class="row justify-content-center">
        <div class="col-12 text-center mb-4">
            <h1><i class="fas fa-heart-pulse text-primary"></i> Build &amp; Link Status</h1>
            <p class="lead">Which firmware downloads could not be reached</p>
            <p class="timestamp mb-1">Last build: {(generated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))}</p>
            <p class="timestamp"><a href="index.html" class="text-decoration-none">
                <i class="fas fa-arrow-left"></i> Back to the firmware overview</a></p>
        </div>
    </div>

    <div class="alert alert-light border shadow-sm">
        <h5 class="alert-heading"><i class="fas fa-circle-info text-primary me-2"></i>How the check works</h5>
        <p class="mb-2 small">
            The overview always lists the newest firmware the GL.iNet API reports. Its download link is
            verified with a <code>HEAD</code> request ({LINK_TIMEOUT}s timeout, up to {LINK_ATTEMPTS}
            attempts for temporary failures). A link that does not respond never changes which version is
            listed &ndash; showing an older release as the current one would be worse than showing the
            current one without a working download. Instead the entry keeps its version, and on the
            overview its download is greyed out and flagged with a warning sign. Where an older build
            still downloads, the overview offers that one as a second link so there is always
            something to grab.
        </p>
        <p class="mb-0 small">
            A <span class="badge bg-warning text-dark">timeout</span> is usually temporary and resolves
            itself on the next daily run. An <span class="badge bg-danger">HTTP 404</span> means the file
            is really gone from GL.iNet's server; that one will not fix itself.
        </p>
    </div>

    <div class="row justify-content-center mb-4">"""

    html += stat_card(len(diagnostics), 'Model / stage entries')
    html += stat_card(attempts, 'HEAD requests')
    html += stat_card(len(unreachable), 'Unreachable downloads', 'danger' if unreachable else 'success')
    html += stat_card(len(empty_models), 'Models without API data', 'danger' if empty_models else 'success')
    html += """
    </div>
"""

    if not unreachable and not empty_models:
        html += """
    <div class="alert alert-success shadow-sm">
        <i class="fas fa-circle-check me-2"></i>
        Every tracked model and stage is showing the newest firmware the GL.iNet API reports,
        and every download link responded. Nothing to report.
    </div>
"""

    if empty_models:
        html += """
    <h3 class="section-title"><i class="fas fa-plug-circle-xmark text-danger"></i> Models without API data</h3>
    <div class="card">
        <div class="card-body">
            <p class="small mb-2">
                The GL.iNet API returned no firmware entries for these models during this build, so they
                carry no versions on the overview. This is almost always a temporary API hiccup.
            </p>
            <p class="mb-0">"""
        html += ' '.join(f'<span class="badge bg-secondary">{esc(m)}</span>' for m in empty_models)
        html += """</p>
        </div>
    </div>
"""

    if unreachable:
        html += """
    <h3 class="section-title"><i class="fas fa-link-slash text-danger"></i> Unreachable downloads</h3>
    <div class="card">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover table-striped mb-0">
                    <thead class="table-dark">
                        <tr>
                            <th scope="col" class="ps-4" style="min-width: 200px;">Model</th>
                            <th scope="col">Stage</th>
                            <th scope="col">Version</th>
                            <th scope="col">Released</th>
                            <th scope="col">Reason</th>
                            <th scope="col">Attempts</th>
                            <th scope="col">Latest reachable</th>
                            <th scope="col">File</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        for d in sorted(unreachable, key=lambda d: (d['model'], d['stage'])):
            filename = d['link'].rsplit('/', 1)[-1] if d['link'] else ''
            file_cell = (f'<a class="file-link" href="{esc(d["link"], quote=True)}" target="_blank" '
                         f'rel="noopener">{esc(filename)}</a>') if d['link'] else '<span class="text-muted">-</span>'
            if d['fallback_version']:
                fallback_cell = (
                    f'<a class="fw-version text-decoration-none" href="{esc(d["fallback_link"], quote=True)}" '
                    f'target="_blank" rel="noopener"><i class="fas fa-download small me-1"></i>'
                    f'{esc(d["fallback_version"])}</a>'
                    f'<div class="timestamp">{esc(d["fallback_release_time"].split(" ")[0])}</div>')
            else:
                fallback_cell = (f'<span class="text-muted small">none '
                                 f'({d["candidates_probed"]} probed)</span>')
            html += f"""
                        <tr>
                            <td class="ps-4">
                                <div class="fw-bold">{esc(d['name'])}</div>
                                <div class="text-muted small" style="font-size: 0.7rem;">{esc(d['model'])}</div>
                            </td>
                            <td>{esc(d['stage'])}</td>
                            <td><span class="fw-version">{esc(d['version'])}</span></td>
                            <td><span class="timestamp">{esc(d['release_time'].split(' ')[0])}</span></td>
                            <td><span class="reason">{esc(d['reason'])}</span></td>
                            <td>{d['attempts']}</td>
                            <td>{fallback_cell}</td>
                            <td>{file_cell}</td>
                        </tr>"""
        html += f"""
                    </tbody>
                </table>
            </div>
        </div>
        <div class="card-footer bg-white small text-muted">
            These versions are still listed on the overview &ndash; only their download link did not
            respond during this build. <em>Latest reachable</em> is the newest older build whose download
            still works (up to {FALLBACK_CANDIDATES} are probed); the overview offers it as a
            second link so there is always something to download.
        </div>
    </div>
"""

    html += """
    <footer>
        <p class="mb-0">Machine-readable version of this page: <code><a href="api/status.json">/api/status.json</a></code></p>
        <p class="mb-0 mt-3 small">Data is automatically verified and updated daily from GL.iNet Firmware API.</p>
    </footer>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    return html
