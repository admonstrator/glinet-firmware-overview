import urllib.request
import urllib.error
import json
import html as html_lib
import re
import socket
import sys
from datetime import datetime
import os
import shutil
import time

from sitelib.core import *  # noqa: F401,F403  (constants and shared helpers)
from sitelib.overview import generate_html
from sitelib.device import generate_device_pages
from sitelib.text_pages import generate_text_pages
from sitelib.docs_page import generate_docs_pages
from sitelib.feeds import generate_feeds
from sitelib.status_page import generate_status_html

API_URL = "https://firmware-api.gl-inet.com/cloud-api/model/info"

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

def check_link(url, max_attempts=LINK_ATTEMPTS):
    """HEAD the URL, retrying transient failures within the global budget.

    Returns (ok, reason, attempts, duration). The reason explains the failure
    for the build log and the status page instead of collapsing it into a bool.
    """
    global _retry_budget_left

    if not url or url == "#":
        return False, "no download URL in API response", 0, 0.0

    total = 0.0
    reason = "not checked"
    for attempt in range(1, max_attempts + 1):
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

    return False, reason, max_attempts, round(total, 2)

def find_reachable_fallback(candidates):
    """Newest older build whose download still responds, or None.

    Used only when the current build's own download is unreachable, so that
    the overview can still offer something downloadable.
    """
    checked = 0
    for candidate in candidates[:FALLBACK_CANDIDATES]:
        link = entry_link(candidate)
        if not link:
            continue
        checked += 1
        ok, _reason, _attempts, _duration = check_link(link, max_attempts=1)
        if ok:
            return candidate, link, checked
    return None, '', checked

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
            candidates = sorted(buckets[model_code][stage],
                                key=lambda e: e.get('release_time', ''),
                                reverse=True)
            newest = candidates[0]
            link = entry_link(newest)
            ok, reason, attempts, duration = check_link(link)

            # The newest version stays published either way, but when its own
            # download is dead, offer the newest older build that still works.
            fallback, fallback_link, probed = (None, '', 0)
            if not ok:
                fallback, fallback_link, probed = find_reachable_fallback(candidates[1:])

            stored = dict(newest)
            stored['changelog'] = changelog_to_plain_text(extract_changelog(newest))
            stored['_link_ok'] = ok
            stored['_link_reason'] = reason
            if fallback is not None:
                stored['_fallback_version'] = fallback.get('version', 'N/A')
                stored['_fallback_link'] = fallback_link
                stored['_fallback_release_time'] = fallback.get('release_time', '')
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
                'candidates_probed': probed,
                'fallback_version': fallback.get('version', 'N/A') if fallback else None,
                'fallback_release_time': fallback.get('release_time', '') if fallback else '',
                'fallback_link': fallback_link,
            })

            if ok:
                summary.append(f"{stage} {version}")
            elif fallback is not None:
                summary.append(f"{stage} {version} (link dead, offering "
                               f"{fallback.get('version', 'N/A')})")
                problems.append(diagnostics[-1])
            else:
                summary.append(f"{stage} {version} (link unreachable)")
                problems.append(diagnostics[-1])

        log_progress(f"[{idx+1}/{total}] {model_code}: " + " · ".join(summary))

        for d in problems:
            tries = "attempt" if d['attempts'] == 1 else "attempts"
            print(f"  WARNING {model_code} ({d['stage']}) {d['version']}: download unreachable after "
                  f"{d['attempts']} {tries} ({d['reason']}, {d['duration']}s). "
                  f"Version is still published.")
            print(f"          {d['link'] or '<no link>'}")
            if d['fallback_version']:
                print(f"          offering {d['fallback_version']} instead as the newest reachable "
                      f"download ({d['candidates_probed']} older build(s) probed)")
                extra = f", offering {d['fallback_version']} as the newest reachable download"
            else:
                extra = (f", and none of the {d['candidates_probed']} older build(s) probed responded"
                         if d['candidates_probed'] else "")
            log_annotation('warning', f"{model_code} ({d['stage']}) {d['version']}: download link "
                                      f"unreachable ({d['reason']}) after {d['attempts']} {tries}{extra}")

    unreachable = sum(1 for d in diagnostics if d['status'] == 'unreachable')
    with_fallback = sum(1 for d in diagnostics if d['fallback_version'])
    attempts = sum(d['attempts'] + d['candidates_probed'] for d in diagnostics)
    offered = f" ({with_fallback} with an older reachable build to offer)" if unreachable else ""
    print(f"Processing complete: {len(diagnostics)} model/stage entries, {attempts} HEAD requests, "
          f"{unreachable} unreachable download{'' if unreachable == 1 else 's'}{offered}. "
          f"Retry budget left: {max(0, round(_retry_budget_left))}s of {RETRY_BUDGET}s.")
    return models, diagnostics

def generate_api_index_files(models, models_metadata):
    """Tab-separated index files for scripts that want to avoid JSON parsing:
    api/models (code, type, name, release version) and api/<model>/stages
    (stage, version, date, url, md5, link state, fallback version, fallback url)."""
    grouped = group_models_by_type(models, models_metadata)
    with open(os.path.join('api', 'models'), 'w', encoding='utf-8') as f:
        for m_type in ['ROUTER', 'IOT', 'KVM']:
            for code in grouped.get(m_type, []):
                release = models[code].get('RELEASE', {}).get('version', '')
                f.write('\t'.join([code.lower(), m_type, models_metadata.get(code, {}).get('name', code), release]) + '\n')
    for code, stages in models.items():
        model_dir = os.path.join('api', code.lower())
        os.makedirs(model_dir, exist_ok=True)
        with open(os.path.join(model_dir, 'stages'), 'w', encoding='utf-8') as f:
            for stage in ordered_stages(stages):
                info = stages[stage]
                link_state = 'ok' if info.get('_link_ok', True) else (info.get('_link_reason', 'unreachable') or 'unreachable').replace('\t', ' ')
                f.write('\t'.join([
                    api_stage_name(stage), info.get('version', ''), info.get('release_time', ''), entry_link(info),
                    (info.get('download') or [{}])[0].get('md5', '') or '', link_state,
                    info.get('_fallback_version', '') or '', info.get('_fallback_link', '') or '',
                ]) + '\n')

def write_step_summary(diagnostics, empty_models):
    """Render the same findings into the GitHub Actions job summary."""
    path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not path:
        return

    unreachable = [d for d in diagnostics if d['status'] == 'unreachable']

    lines = ['## Firmware link check', '']
    lines.append(f"- Model/stage entries: **{len(diagnostics)}**")
    lines.append(f"- HEAD requests: "
                 f"**{sum(d['attempts'] + d['candidates_probed'] for d in diagnostics)}**")
    lines.append(f"- Unreachable downloads: **{len(unreachable)}**")
    lines.append(f"- Models without API data: **{len(empty_models)}**")
    lines.append('')

    if empty_models:
        lines.append(f"\u26a0\ufe0f No API data for: {', '.join(empty_models)}")
        lines.append('')

    if unreachable:
        lines.append('The versions below are still published; only their download link failed.')
        lines.append('')
        lines.append('| Model | Stage | Version | Reason | Attempts | Latest reachable |')
        lines.append('| --- | --- | --- | --- | --- | --- |')
        for d in sorted(unreachable, key=lambda d: (d['model'], d['stage'])):
            fallback = d['fallback_version'] or f"none ({d['candidates_probed']} probed)"
            lines.append(f"| {d['model']} | {d['stage']} | {d['version']} | `{d['reason']}` "
                         f"| {d['attempts']} | {fallback} |")
    else:
        lines.append('\u2705 Every download link responded.')

    lines.append('')
    with open(path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

def generate_api_files(models, models_metadata, diagnostics, empty_models, generated_at=None):
    api_dir = 'api'
    if os.path.exists(api_dir):
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
        available_stages = sorted([api_stage_name(s) for s in stages.keys()])
        branches_content = '\n'.join(available_stages) + '\n'
        
        # 1. Provide at api/model_code/branches
        with open(os.path.join(model_dir, 'branches'), 'w') as f:
            f.write(branches_content)
            
        # 2. Provide at api/model_code/index.html (served as /api/model_code/)
        with open(os.path.join(model_dir, 'index.html'), 'w') as f:
            f.write(branches_content)
            
        all_data[model_code_lower] = {}
        
        for stage, info in stages.items():
            s_name = api_stage_name(stage)
            version = info.get('version', 'N/A')
            release_time = info.get('release_time', '')
            download_url = info.get('download', [{}])[0].get('link', '')
            # Try to find a hash (md5 is common in GL.iNet API)
            md5_hash = info.get('download', [{}])[0].get('md5', '')
            changelog = (info.get('changelog') or '').strip()
            changelog_path = f"{SITE_URL}/api/{model_code_lower}/{s_name}/changelog"
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

            # Only present when this entry's own download did not respond.
            if info.get('_fallback_link'):
                all_data[model_code_lower][s_name]['latest_reachable'] = {
                    'version': info['_fallback_version'],
                    'release_time': info.get('_fallback_release_time', ''),
                    'download': info['_fallback_link'],
                }
                summary_content += (f"latest_reachable: {info['_fallback_version']} "
                                    f"{info['_fallback_link']}\n")
            
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

    generate_api_index_files(models, models_metadata)

    unreachable = [d for d in diagnostics if d['status'] == 'unreachable']
    status_data = {
        'generated_at': generated_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'link_timeout_seconds': LINK_TIMEOUT,
        'link_attempts': LINK_ATTEMPTS,
        'summary': {
            'entries': len(diagnostics),
            'head_requests': sum(d['attempts'] + d['candidates_probed'] for d in diagnostics),
            'unreachable': len(unreachable),
            'models_without_api_data': len(empty_models),
        },
        'models_without_api_data': empty_models,
        'unreachable': unreachable,
    }
    with open(os.path.join(api_dir, 'status.json'), 'w', encoding='utf-8') as f:
        json.dump(status_data, f, indent=2, ensure_ascii=False)

def write_site(models, models_metadata, diagnostics, empty_models, generated_at):
    """Write the whole site into the current directory. No network access happens here,
    so tests/build_offline.py can call it with fixture data. Returns the number of device pages."""
    print("Generating API files...")
    generate_api_files(models, models_metadata, diagnostics, empty_models, generated_at)

    print(f"Generating device pages for {len(models)} models...")
    pages_written = generate_device_pages(models, models_metadata, generated_at)

    print("Generating plain-text pages for curl...")
    generate_text_pages(models, models_metadata, generated_at)

    print("Generating docs pages...")
    generate_docs_pages(models, models_metadata, generated_at)

    print("Generating feeds...")
    feeds_written = generate_feeds(models, models_metadata, generated_at)
    if feeds_written:
        print(f"  {feeds_written} feed files")

    print(f"Generating HTML for {len(models)} models...")
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(generate_html(models, models_metadata, diagnostics, generated_at))

    print("Generating status page...")
    with open('status.html', 'w', encoding='utf-8') as f:
        f.write(generate_status_html(diagnostics, empty_models, generated_at))
    return pages_written

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
        generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')

        pages_written = write_site(models, models_metadata, diagnostics, empty_models, generated_at)
        write_step_summary(diagnostics, empty_models)
        print(f"Done. index.html, status.html, api/ files and {pages_written} device pages (HTML + text) created.")
    else:
        message = "Failed to fetch or process data: the API returned no firmware entries at all."
        print(message)
        log_annotation('error', message)
        exit(1)

if __name__ == "__main__":
    main()

