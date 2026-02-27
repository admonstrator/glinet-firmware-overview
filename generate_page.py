import urllib.request
import json
from datetime import datetime
import os
import time

API_URL = "https://firmware-api.gl-inet.com/cloud-api/model/info"

def check_link(url):
    """Performs a HEAD request to check if the URL exists."""
    if not url or url == "#":
        return False
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception:
        return False

import time

def fetch_data(url):
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                if 'info' in data:
                    return data['info']
    except Exception as e:
        print(f"\nError fetching URL {url}: {e}")
        pass
    return []

def fetch_data_individual(model_codes):
    all_info = []
    total = len(model_codes)
    for idx, model in enumerate(model_codes):
        url = f"{API_URL}?model={model}"
        print(f"Fetching firmware info for {model} ({idx+1}/{total})...", end="\r")
        all_info.extend(fetch_data(url))
        all_info.extend(fetch_data(f"{API_URL}?model={model}-open"))
        time.sleep(0.1) # Be nice to the API
    
    print(f"\nFetched total {len(all_info)} firmware entries.")
    return {'info': all_info}

def process_data(data, models_metadata):
    if not data or 'info' not in data:
        return {}

    # Structure: models[model_code][stage] = firmware_info
    models = {}
    
    # Initialize with all known models from metadata
    for code in models_metadata:
        models[code] = {}

    total_entries = len(data['info'])
    for idx, entry in enumerate(data['info']):
        model_code = entry.get('model')
        stage = entry.get('stage')
        
        if not model_code or not stage:
            continue

        if model_code.endswith('-open'):
            model_code = model_code[:-5]

        if model_code not in models:
            models[model_code] = {}

        # Check if this entry is newer or the first one we see for this stage
        current_stored = models[model_code].get(stage)
        is_newer = False
        if not current_stored or entry.get('release_time', '') > current_stored.get('release_time', ''):
            is_newer = True
        
        if is_newer:
            # Validate the link before storing it
            download_link = "#"
            if 'download' in entry and entry['download']:
                 download_link = entry['download'][0].get('link', '#')
            
            print(f"[{idx+1}/{total_entries}] Validating link for {model_code} ({stage})...", end="\r")
            if check_link(download_link):
                models[model_code][stage] = entry
            else:
                # If the newer one is broken, keep the old one if it exists and was valid
                # Or just don't store it. For now, we only store if valid.
                pass

    print(f"\nProcessing complete.")
    return models

def generate_html(models, models_metadata):
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
    
    # Collect all unique stages to create table headers
    all_stages = set()
    for model in models:
        all_stages.update(models[model].keys())
    
    # Define a preferred order for columns
    stage_order = ['RELEASE', 'BETA', 'SNAPSHOT', 'TESTING', 'RC', 'OP24']
    sorted_stages = [s for s in stage_order if s in all_stages] + [s for s in sorted(all_stages) if s not in stage_order]

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
        .stage-BETA {{ color: #ffc107; }}
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
            <p class="timestamp">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
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
                                <li><strong>Specific attributes:</strong> <code>/api/&lt;model&gt;/&lt;stage&gt;/[version|url|date|hash]</code></li>
                                <li><strong>Consolidated data:</strong> <code>/api/all.json</code></li>
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
                if info:
                    version = info.get('version', 'N/A')
                    release_time = info.get('release_time', '').split(' ')[0]
                    download_link = "#"
                    if 'download' in info and info['download']:
                         download_link = info['download'][0].get('link', '#')
                    
                    html += f"""
                        <td>
                            <div class="d-flex flex-column">
                                <a href="{download_link}" target="_blank" class="fw-version text-decoration-none stage-{stage}">
                                    {version} <i class="fas fa-download small ms-1"></i>
                                </a>
                                <span class="timestamp">{release_time}</span>
                            </div>
                        </td>
                    """
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

def generate_api_files(models):
    api_dir = 'api'
    if not os.path.exists(api_dir):
        os.makedirs(api_dir)
    
    # Also generate a consolidated JSON
    all_data = {}

    for model_code, stages in models.items():
        model_code_lower = model_code.lower()
        model_dir = os.path.join(api_dir, model_code_lower)
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
        # List available branches/stages for this model
        available_stages = sorted([s.lower() for s in stages.keys()])
        branches_content = '\n'.join(available_stages) + '\n'
        
        # 1. Provide at api/model_code/branches
        with open(os.path.join(model_dir, 'branches'), 'w') as f:
            f.write(branches_content)
            
        # 2. Provide at api/model_code/index.html (served as /api/model_code/)
        with open(os.path.join(model_dir, 'index.html'), 'w') as f:
            f.write(branches_content)
            
        all_data[model_code_lower] = {}
        
        for stage, info in stages.items():
            version = info.get('version', 'N/A')
            release_time = info.get('release_time', '')
            download_url = info.get('download', [{}])[0].get('link', '')
            # Try to find a hash (md5 is common in GL.iNet API)
            md5_hash = info.get('download', [{}])[0].get('md5', '')
            
            summary_content = f"version: {version}\nhash: {md5_hash}\ndownload: {download_url}\ndate: {release_time}\n"
            
            s_name = stage.lower()
            all_data[model_code_lower][s_name] = {
                'version': version,
                'release_time': release_time,
                'download': download_url,
                'md5': md5_hash
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

    with open(os.path.join(api_dir, 'all.json'), 'w') as f:
        json.dump(all_data, f, indent=2)

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
    raw_data = fetch_data_individual(models_metadata.keys())
    
    if raw_data and raw_data.get('info'):
        print(f"Data fetched. Processing {len(raw_data['info'])} entries...")
        models = process_data(raw_data, models_metadata)
        
        print("Generating API files...")
        generate_api_files(models)
        
        print(f"Generating HTML for {len(models)} models...")
        html_content = generate_html(models, models_metadata)
        
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("Done. index.html and api/ files created.")
    else:
        print("Failed to fetch or process data.")
        exit(1)



if __name__ == "__main__":
    main()
