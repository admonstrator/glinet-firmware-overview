import urllib.request
import urllib.error
import json
import html as html_lib
import re
import socket
import sys
from datetime import datetime
import os
import time

API_URL = "https://firmware-api.gl-inet.com/cloud-api/model/info"

# Seconds a firmware download link gets to answer a single HEAD request. A
# healthy answer takes well under a second, so this is generous on purpose.
LINK_TIMEOUT = 8

# Transient failures (timeout, reset, 5xx, 429) are retried; a 404 is not.
LINK_ATTEMPTS = 3
LINK_BACKOFF = (1, 3)  # seconds to wait before attempt 2 and attempt 3

# Upper bound on the extra time retries may cost across one whole run, so a bad
# day upstream cannot turn a 90 second build into an hour of waiting. Once it is
# used up the remaining links get a single attempt each.
RETRY_BUDGET = 180
_retry_budget_left = RETRY_BUDGET

IS_GITHUB_ACTIONS = os.environ.get('GITHUB_ACTIONS') == 'true'

# Stream the build log instead of flushing it in one block at the end of the step.
try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:  # Python < 3.7
    pass

def log_progress(message):
    """Progress output: transient on a terminal, a real log line in CI."""
    if sys.stdout.isatty():
        print(message, end="\r")
    else:
        print(message)

def log_annotation(level, message):
    """Emit a GitHub Actions annotation so problems show up on the run page."""
    if IS_GITHUB_ACTIONS:
        # Annotations are single-line; encode newlines the way Actions expects.
        print(f"::{level}::{message.replace(chr(10), '%0A')}")

def attempt_link(url):
    """One HEAD request. Returns (ok, reason, retryable, duration).

    A 4xx answer is the server telling us the file is not there, so it is
    final. Timeouts, resets, 5xx and 429 are worth another try.
    """
    started = time.monotonic()
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=LINK_TIMEOUT) as response:
            duration = time.monotonic() - started
            ok = response.status == 200
            return ok, f"HTTP {response.status}", not ok and response.status >= 500, duration
    except urllib.error.HTTPError as e:
        retryable = e.code == 429 or e.code >= 500
        return False, f"HTTP {e.code} {e.reason}", retryable, time.monotonic() - started
    except urllib.error.URLError as e:
        duration = time.monotonic() - started
        if isinstance(e.reason, (socket.timeout, TimeoutError)):
            return False, "timeout", True, duration
        return False, f"{type(e.reason).__name__}: {e.reason}", True, duration
    except (socket.timeout, TimeoutError):
        return False, "timeout", True, time.monotonic() - started
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", True, time.monotonic() - started

def check_link(url):
    """HEAD the URL, retrying transient failures within the global budget.

    Returns (ok, reason, attempts, duration). The reason explains the failure
    for the build log and the status page instead of collapsing it into a bool.
    """
    global _retry_budget_left

    if not url or url == "#":
        return False, "no download URL in API response", 0, 0.0

    total = 0.0
    reason = "not checked"
    for attempt in range(1, LINK_ATTEMPTS + 1):
        if attempt > 1:
            if _retry_budget_left <= 0:
                return False, f"{reason}, no retry budget left", attempt - 1, round(total, 2)
            wait = LINK_BACKOFF[attempt - 2]
            time.sleep(wait)
            total += wait
            _retry_budget_left -= wait

        ok, reason, retryable, duration = attempt_link(url)
        total += duration
        if attempt > 1:
            _retry_budget_left -= duration
        if ok:
            return True, reason, attempt, round(total, 2)
        if not retryable:
            return False, reason, attempt, round(total, 2)

    return False, reason, LINK_ATTEMPTS, round(total, 2)

def extract_changelog(entry):
    """Extract changelog text from known API field variants."""
    changelog_keys = [
        'changelog', 'release_notes', 'release_note', 'notes',
        'description', 'change_log', 'whats_new', 'what_is_new'
    ]

    for key in changelog_keys:
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list):
            parts = [item.strip() for item in value if isinstance(item, str) and item.strip()]
            if parts:
                return '\n'.join(parts)
        if isinstance(value, dict):
            nested_parts = []
            for nested_key in ['en', 'text', 'content', 'message', 'body']:
                nested_val = value.get(nested_key)
                if isinstance(nested_val, str) and nested_val.strip():
                    nested_parts.append(nested_val.strip())
            if nested_parts:
                return '\n'.join(nested_parts)

    return ''

def fix_mojibake(text):
    """Fix double-encoded UTF-8 text (e.g. â€' -> ‑).
    
    This occurs when UTF-8 bytes are misinterpreted as Latin-1/Windows-1252.
    """
    try:
        return text.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text

def changelog_to_plain_text(changelog_text):
    """Convert changelog content to plain text by removing HTML markup."""
    if not changelog_text:
        return ''

    text = changelog_text
    # Fix potential mojibake (double-encoded UTF-8 from upstream API)
    text = fix_mojibake(text)
    # Preserve visual structure for common block/list tags before stripping all tags.
    text = re.sub(r'(?i)<\s*br\s*/?\s*>', '\n', text)
    text = re.sub(r'(?i)</\s*(p|div|h1|h2|h3|h4|h5|h6|li|ul|ol)\s*>', '\n', text)
    text = re.sub(r'(?is)<\s*script[^>]*>.*?<\s*/\s*script\s*>', '', text)
    text = re.sub(r'(?is)<\s*style[^>]*>.*?<\s*/\s*style\s*>', '', text)
    text = re.sub(r'(?s)<[^>]+>', '', text)
    text = html_lib.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def fetch_data(url):
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                raw = response.read()
                charset = response.headers.get_content_charset('utf-8')
                data = json.loads(raw.decode(charset))
                if 'info' in data:
                    return data['info']
    except Exception as e:
        message = f"API request failed for {url}: {type(e).__name__}: {e}"
        print(f"  ERROR {message}")
        log_annotation('error', message)
    return []

def fetch_data_individual(model_codes):
    all_info = []
    empty_models = []
    model_codes = list(model_codes)
    total = len(model_codes)
    for idx, model in enumerate(model_codes):
        entries = fetch_data(f"{API_URL}?model={model}")
        entries += fetch_data(f"{API_URL}?model={model}-open")
        log_progress(f"[{idx+1}/{total}] {model}: {len(entries)} firmware entries")
        if not entries:
            message = f"{model}: API returned no firmware entries"
            print(f"  WARNING {message}")
            log_annotation('warning', message)
            empty_models.append(model)
        all_info.extend(entries)
        time.sleep(0.1) # Be nice to the API

    print(f"Fetched {len(all_info)} firmware entries for {total} models.")
    return {'info': all_info}, empty_models

def detect_openwrt_base(entry):
    """Determine the OpenWrt base major version ('24', '25', ...) of an
    'open' firmware entry from its download filename
    (e.g. 'mt3000-op-4.9.1-op25_beta1-...bin'). Returns None if unknown."""
    try:
        link = entry.get('download', [{}])[0].get('link', '') or ''
    except (IndexError, AttributeError, TypeError):
        link = ''
    match = re.search(r'-op(\d{2})', link)
    return match.group(1) if match else None

def bucket_entries(entries):
    """Group API entries into buckets[model_code][stage] = [entry, ...]."""
    buckets = {}
    for entry in entries:
        model_code = entry.get('model')
        stage = entry.get('stage')

        if not model_code or not stage:
            continue

        if model_code.endswith('-open'):
            model_code = model_code[:-5]
            base = detect_openwrt_base(entry) or '24'
            stage = f'BETA_OPEN{base}'
            entry['_is_open'] = True
            entry['_openwrt_base'] = base

        if stage == 'TESTING':
            stage = 'BETA'

        buckets.setdefault(model_code, {}).setdefault(stage, []).append(entry)
    return buckets

def entry_link(entry):
    if entry.get('download'):
        return entry['download'][0].get('link', '') or ''
    return ''

def process_data(data, models_metadata):
    """Keep the newest firmware the API reports per model and stage.

    The download link is verified, but a link that does not respond never
    changes which version is published: reporting an older release as the
    current one is worse than reporting the current one without a working
    download. An unreachable link is marked as such instead, and the reason
    ends up in the build log, on the status page and in /api/status.json.
    """
    if not data or 'info' not in data:
        return {}, []

    buckets = bucket_entries(data['info'])

    # Structure: models[model_code][stage] = firmware_info
    models = {code: {} for code in models_metadata}
    diagnostics = []

    # Keep the metadata order so the log matches the fetch order above.
    ordered_codes = [c for c in models_metadata if c in buckets]
    ordered_codes += [c for c in buckets if c not in models_metadata]
    total = len(ordered_codes)

    for idx, model_code in enumerate(ordered_codes):
        models.setdefault(model_code, {})
        summary = []
        problems = []

        for stage in sorted(buckets[model_code]):
            newest = max(buckets[model_code][stage],
                         key=lambda e: e.get('release_time', ''))
            link = entry_link(newest)
            ok, reason, attempts, duration = check_link(link)

            stored = dict(newest)
            stored['changelog'] = changelog_to_plain_text(extract_changelog(newest))
            stored['_link_ok'] = ok
            stored['_link_reason'] = reason
            models[model_code][stage] = stored

            version = newest.get('version', 'N/A')
            diagnostics.append({
                'model': model_code,
                'name': models_metadata.get(model_code, {}).get('name', model_code),
                'stage': stage,
                'status': 'ok' if ok else 'unreachable',
                'version': version,
                'release_time': newest.get('release_time', ''),
                'link': link,
                'reason': reason,
                'attempts': attempts,
                'duration': duration,
            })

            if ok:
                summary.append(f"{stage} {version}")
            else:
                summary.append(f"{stage} {version} (link unreachable)")
                problems.append((stage, version, link, reason, attempts, duration))

        log_progress(f"[{idx+1}/{total}] {model_code}: " + " · ".join(summary))

        for stage, version, link, reason, attempts, duration in problems:
            tries = "attempt" if attempts == 1 else "attempts"
            print(f"  WARNING {model_code} ({stage}) {version}: download unreachable after "
                  f"{attempts} {tries} ({reason}, {duration}s). Version is still published.")
            print(f"          {link or '<no link>'}")
            log_annotation('warning', f"{model_code} ({stage}) {version}: download link "
                                      f"unreachable ({reason}) after {attempts} {tries}")

    unreachable = sum(1 for d in diagnostics if d['status'] == 'unreachable')
    attempts = sum(d['attempts'] for d in diagnostics)
    print(f"Processing complete: {len(diagnostics)} model/stage entries, {attempts} HEAD requests, "
          f"{unreachable} unreachable download{'' if unreachable == 1 else 's'}. "
          f"Retry budget left: {max(0, round(_retry_budget_left))}s of {RETRY_BUDGET}s.")
    return models, diagnostics

def generate_html(models, models_metadata, diagnostics):
    # Group models by type
    grouped_models = {'ROUTER': [], 'IOT': [], 'KVM': []}
    for code in models.keys():
        meta = models_metadata.get(code, {})
        m_type = meta.get('type', 'ROUTER')
        if m_type not in grouped_models:
            grouped_models[m_type] = []
        grouped_models[m_type].append(code)

    # Sort within each group
    def get_sort_key(code):
        meta = models_metadata.get(code, {})
        return meta.get('name', code)

    for m_type in grouped_models:
        grouped_models[m_type].sort(key=get_sort_key)
    
    # Collect all unique stages to create table headers, exclude internal BETA_OPEN* variants
    all_stages = set()
    for model in models:
        all_stages.update(s for s in models[model].keys() if not s.startswith('BETA_OPEN'))
    
    # Define a preferred order for columns
    stage_order = ['RELEASE', 'BETA', 'SNAPSHOT', 'RC']
    sorted_stages = [s for s in stage_order if s in all_stages] + [s for s in sorted(all_stages) if s not in stage_order]

    issue_count = sum(1 for d in diagnostics if d['status'] != 'ok')
    if issue_count:
        status_link = (f'<a href="status.html" class="text-decoration-none">'
                       f'<i class="fas fa-triangle-exclamation text-warning"></i> '
                       f'{issue_count} download{"" if issue_count == 1 else "s"} unreachable</a>')
    else:
        status_link = ('<a href="status.html" class="text-decoration-none">'
                       '<i class="fas fa-circle-check text-success"></i> All links verified</a>')

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GL.iNet Firmware Overview</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {{ background-color: #f8f9fa; padding-top: 20px; }}
        .card {{ margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: none; }}
        .card-header {{ background-color: #343a40; color: white; font-weight: bold; padding: 12px 20px; }}
        .badge-stage {{ font-size: 0.8em; }}
        .table-hover tbody tr:hover {{ background-color: #f1f1f1; }}
        .fw-version {{ font-family: monospace; font-weight: bold; }}
        .timestamp {{ font-size: 0.8rem; color: #6c757d; }}
        .search-container {{ margin-bottom: 30px; }}
        footer {{ margin-top: 50px; padding: 40px 0; text-align: center; color: #6c757d; font-size: 0.9rem; border-top: 1px solid #dee2e6; }}
        
        /* Stage specific colors */
        .stage-RELEASE {{ color: #198754; }}
        .stage-BETA {{ color: #0d6efd; }}
        .stage-SNAPSHOT {{ color: #0dcaf0; }}
        .stage-TESTING {{ color: #dc3545; }}
        .stage-RC {{ color: #fd7e14; }}
        
        .model-type {{ font-size: 0.7rem; text-transform: uppercase; color: #adb5bd; letter-spacing: 1px; }}
        .api-info {{ background: #e9ecef; border-radius: 8px; padding: 20px; margin-bottom: 30px; }}
        code {{ background: #f1f3f5; padding: 2px 4px; border-radius: 4px; color: #d63384; }}
        .section-title {{ margin-bottom: 15px; font-weight: bold; color: #495057; display: flex; align-items: center; }}
        .section-title i {{ margin-right: 10px; }}
    </style>
</head>
<body>

<div class="container">
    <div class="row justify-content-center">
        <div class="col-12 text-center mb-4">
            <h1><i class="fas fa-microchip text-primary"></i> GL.iNet Firmware Overview</h1>
            <p class="lead">Latest verified firmware versions</p>
            <div class="mb-2">
                <span class="badge bg-info text-dark">Community Project by <a href="https://admon.me" target="_blank" class="text-dark text-decoration-none fw-bold">admon (admon.me)</a></span>
            </div>
            <p class="timestamp mb-1">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p class="timestamp">{status_link}</p>
        </div>
    </div>

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
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    """

    type_icons = {
        'ROUTER': 'fa-wifi',
        'IOT': 'fa-broadcast-tower',
        'KVM': 'fa-server'
    }

    type_names = {
        'ROUTER': 'Routers',
        'IOT': 'IoT Devices',
        'KVM': 'KVM / Comet Series'
    }

    for m_type in ['ROUTER', 'IOT', 'KVM']:
        codes = grouped_models.get(m_type, [])
        if not codes:
            continue
            
        icon = type_icons.get(m_type, 'fa-device')
        name = type_names.get(m_type, m_type)

        html += f"""
    <h3 class="section-title"><i class="fas {icon} text-primary"></i> {name}</h3>
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
            full_name = meta.get('name', code)
            
            html += f"""
            <tr>
                <td class='ps-4'>
                    <div class="fw-bold">{full_name}</div>
                    <div class="text-muted small" style="font-size: 0.7rem;">{code}</div>
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
                        download_link = "#"
                        if 'download' in entry_info and entry_info['download']:
                             download_link = entry_info['download'][0].get('link', '#')
                        changelog_text = (entry_info.get('changelog') or '').strip()
                        timestamp_html = f'<span class="timestamp">{release_time}</span>'
                        if changelog_text:
                            stage_name = entry_stage.lower().replace('_open', '-open')
                            changelog_path = f"api/{code.lower()}/{stage_name}/changelog"
                            timestamp_html = f'<a class="timestamp text-decoration-none" href="{changelog_path}" target="_blank" title="Open latest changelog TXT">{release_time} <i class="fas fa-file-lines small ms-1"></i></a>'
                        open_badge = ''
                        if entry_info.get('_is_open'):
                            base = entry_info.get('_openwrt_base', '24')
                            open_badge = f'<span class="badge bg-secondary ms-1" style="font-size:0.6rem;vertical-align:middle;" title="OpenWrt {base} open variant">OP{base}</span>'
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
                        cells.append(f'''
                                <div class="d-flex flex-column{'  border-top pt-1 mt-1' if entry_info.get('_is_open') and info else ''}">
                                    {version_html}
                                    <div>{timestamp_html}{open_badge}</div>
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

STATUS_PAGE_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Build Status - GL.iNet Firmware Overview</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
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

def generate_status_html(diagnostics, empty_models):
    esc = html_lib.escape

    unreachable = [d for d in diagnostics if d['status'] == 'unreachable']
    attempts = sum(d['attempts'] for d in diagnostics)

    html = STATUS_PAGE_HEAD
    html += f"""
    <div class="row justify-content-center">
        <div class="col-12 text-center mb-4">
            <h1><i class="fas fa-heart-pulse text-primary"></i> Build &amp; Link Status</h1>
            <p class="lead">Which firmware downloads could not be reached</p>
            <p class="timestamp mb-1">Last build: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
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
            overview its download is greyed out and marked with a warning sign
            (<i class="fas fa-triangle-exclamation text-warning"></i>).
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
                            <th scope="col">Took</th>
                            <th scope="col">File</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        for d in sorted(unreachable, key=lambda d: (d['model'], d['stage'])):
            filename = d['link'].rsplit('/', 1)[-1] if d['link'] else ''
            file_cell = (f'<a class="file-link" href="{esc(d["link"], quote=True)}" target="_blank" '
                         f'rel="noopener">{esc(filename)}</a>') if d['link'] else '<span class="text-muted">-</span>'
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
                            <td><span class="timestamp">{d['duration']}s</span></td>
                            <td>{file_cell}</td>
                        </tr>"""
        html += """
                    </tbody>
                </table>
            </div>
        </div>
        <div class="card-footer bg-white small text-muted">
            These versions are still listed on the overview &ndash; only their download link did not
            respond during this build.
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

def write_step_summary(diagnostics, empty_models):
    """Render the same findings into the GitHub Actions job summary."""
    path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not path:
        return

    unreachable = [d for d in diagnostics if d['status'] == 'unreachable']

    lines = ['## Firmware link check', '']
    lines.append(f"- Model/stage entries: **{len(diagnostics)}**")
    lines.append(f"- HEAD requests: **{sum(d['attempts'] for d in diagnostics)}**")
    lines.append(f"- Unreachable downloads: **{len(unreachable)}**")
    lines.append(f"- Models without API data: **{len(empty_models)}**")
    lines.append('')

    if empty_models:
        lines.append(f"\u26a0\ufe0f No API data for: {', '.join(empty_models)}")
        lines.append('')

    if unreachable:
        lines.append('The versions below are still published; only their download link failed.')
        lines.append('')
        lines.append('| Model | Stage | Version | Reason | Attempts |')
        lines.append('| --- | --- | --- | --- | --- |')
        for d in sorted(unreachable, key=lambda d: (d['model'], d['stage'])):
            lines.append(f"| {d['model']} | {d['stage']} | {d['version']} | `{d['reason']}` | {d['attempts']} |")
    else:
        lines.append('\u2705 Every download link responded.')

    lines.append('')
    with open(path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

def generate_api_files(models, diagnostics, empty_models):
    api_dir = 'api'
    if os.path.exists(api_dir):
        import shutil
        shutil.rmtree(api_dir)
    os.makedirs(api_dir)
    
    # Also generate a consolidated JSON
    all_data = {}

    for model_code, stages in models.items():
        model_code_lower = model_code.lower()
        model_dir = os.path.join(api_dir, model_code_lower)
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
        # List available branches/stages for this model
        available_stages = sorted([s.lower().replace('_open', '-open') for s in stages.keys()])
        branches_content = '\n'.join(available_stages) + '\n'
        
        # 1. Provide at api/model_code/branches
        with open(os.path.join(model_dir, 'branches'), 'w') as f:
            f.write(branches_content)
            
        # 2. Provide at api/model_code/index.html (served as /api/model_code/)
        with open(os.path.join(model_dir, 'index.html'), 'w') as f:
            f.write(branches_content)
            
        all_data[model_code_lower] = {}
        
        for stage, info in stages.items():
            s_name = stage.lower().replace('_open', '-open')
            version = info.get('version', 'N/A')
            release_time = info.get('release_time', '')
            download_url = info.get('download', [{}])[0].get('link', '')
            # Try to find a hash (md5 is common in GL.iNet API)
            md5_hash = info.get('download', [{}])[0].get('md5', '')
            changelog = (info.get('changelog') or '').strip()
            changelog_path = f"https://glinet-firmware.admon.me/api/{model_code_lower}/{s_name}/changelog"
            link_ok = info.get('_link_ok', True)
            link_state = 'ok' if link_ok else f"unreachable ({info.get('_link_reason', 'unknown')})"

            summary_content = (f"version: {version}\nhash: {md5_hash}\ndownload: {download_url}\n"
                               f"date: {release_time}\nchangelog: {changelog_path}\nlink: {link_state}\n")

            all_data[model_code_lower][s_name] = {
                'version': version,
                'release_time': release_time,
                'download': download_url,
                'md5': md5_hash,
                'changelog': changelog_path,
                'link_ok': link_ok
            }
            
            # Simple structure: api/model/stage/attribute
            stage_path = os.path.join(model_dir, s_name)
            
            # If a file exists where we want a directory, remove it
            if os.path.exists(stage_path) and not os.path.isdir(stage_path):
                os.remove(stage_path)
            
            if not os.path.exists(stage_path):
                os.makedirs(stage_path)
            
            # Summary file at the stage directory level
            with open(os.path.join(stage_path, 'index.html'), 'w') as f:
                f.write(summary_content)
            
            # Sub-files for specific attributes
            with open(os.path.join(stage_path, 'version'), 'w') as f:
                f.write(version + '\n')
            with open(os.path.join(stage_path, 'url'), 'w') as f:
                f.write(download_url + '\n')
            with open(os.path.join(stage_path, 'date'), 'w') as f:
                f.write(release_time + '\n')
            with open(os.path.join(stage_path, 'hash'), 'w') as f:
                f.write(md5_hash + '\n')
            with open(os.path.join(stage_path, 'changelog'), 'w', encoding='utf-8') as f:
                f.write(changelog + '\n')

    with open(os.path.join(api_dir, 'all.json'), 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    unreachable = [d for d in diagnostics if d['status'] == 'unreachable']
    status_data = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'link_timeout_seconds': LINK_TIMEOUT,
        'link_attempts': LINK_ATTEMPTS,
        'summary': {
            'entries': len(diagnostics),
            'head_requests': sum(d['attempts'] for d in diagnostics),
            'unreachable': len(unreachable),
            'models_without_api_data': len(empty_models),
        },
        'models_without_api_data': empty_models,
        'unreachable': unreachable,
    }
    with open(os.path.join(api_dir, 'status.json'), 'w', encoding='utf-8') as f:
        json.dump(status_data, f, indent=2, ensure_ascii=False)

def main():
    print("Loading models metadata...")
    models_metadata = {}
    if os.path.exists('models.json'):
        with open('models.json', 'r') as f:
            models_metadata = json.load(f)
    
    if not models_metadata:
        print("No models metadata found. Please run fetch_all_models.py first.")
        exit(1)

    print(f"Fetching firmware data for {len(models_metadata)} models...")
    raw_data, empty_models = fetch_data_individual(models_metadata.keys())

    if raw_data and raw_data.get('info'):
        print(f"Data fetched. Validating download links for {len(raw_data['info'])} entries...")
        models, diagnostics = process_data(raw_data, models_metadata)

        print("Generating API files...")
        generate_api_files(models, diagnostics, empty_models)

        print(f"Generating HTML for {len(models)} models...")
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(generate_html(models, models_metadata, diagnostics))

        print("Generating status page...")
        with open('status.html', 'w', encoding='utf-8') as f:
            f.write(generate_status_html(diagnostics, empty_models))

        write_step_summary(diagnostics, empty_models)
        print("Done. index.html, status.html and api/ files created.")
    else:
        message = "Failed to fetch or process data: the API returned no firmware entries at all."
        print(message)
        log_annotation('error', message)
        exit(1)



if __name__ == "__main__":
    main()
