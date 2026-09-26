"""API & terminal documentation (/docs/, HTML + text twin) and the /cli/ landing page."""
import html as html_lib
import os

from sitelib.core import *  # noqa: F401,F403
from sitelib.design import *  # noqa: F401,F403

def cli_page_html():
    """Landing page of /cli/ for browsers: how to start the terminal menu."""
    head = html_head(f"Terminal menu | {SITE_NAME}",
                     description="Browse GL.iNet firmware versions from the terminal with curl.",
                     canonical=f"{SITE_URL}/cli/", root='../')
    return f"""<!DOCTYPE html>
{DEVICE_PAGE_MARKER}
<html lang="en">
{head}
<body>
<div class="container">
    <nav aria-label="breadcrumb" class="mb-3"><ol class="breadcrumb small mb-0">
        <li class="breadcrumb-item"><a href="../" class="text-decoration-none"><i class="fas fa-microchip me-1"></i>{SITE_NAME}</a></li>
        <li class="breadcrumb-item active" aria-current="page">Terminal menu</li></ol></nav>
    <div class="text-center mb-4"><h1><i class="fas fa-terminal text-primary"></i> Terminal menu</h1>
        <p class="lead">Browse firmware versions, read changelogs and download builds without leaving the shell.</p></div>
    <div class="card"><div class="card-body">
        <p class="mb-2">Interactive menu (needs only <code>sh</code> and <code>curl</code>):</p>
        <pre class="changelog-text">sh &lt;(curl -s {SITE_URL}/cli)      # bash / zsh
curl -s {SITE_URL}/cli | sh        # any POSIX sh</pre>
        <p class="mt-3 mb-2">Or walk the site page by page; every page ends with the commands for the next step:</p>
        <pre class="changelog-text">curl {SITE_URL}/            # menu
curl {SITE_URL}/routers     # one category
curl {SITE_URL}/mt3000      # one device
curl {SITE_URL}/mt3000/release   # one build with its changelog</pre>
        <p class="small text-muted mt-3 mb-0">The script is plain text: <a href="index.txt">read it first</a> if you like. It only talks to <code>{SITE_URL}/api/</code> and, when you ask it to download a build, to <code>fw.gl-inet.com</code>.</p>
    </div></div>
    <footer><p class="mb-2"><a href="../" class="text-decoration-none"><i class="fas fa-arrow-left me-1"></i> Back to the firmware overview</a></p></footer>
</div>
</body>
</html>
"""

def generate_docs_text(models, models_metadata, generated_at):
    """Text twin of /docs/ for curl (placeholder until the docs agent fills it)."""
    lines = [f'{SITE_NAME} - API and terminal', '', f'See {SITE_URL}/{DOCS_DIR}/ in a browser.', '']
    return '\n'.join(lines)

def generate_docs_html(models, models_metadata, generated_at):
    """HTML of /docs/ (placeholder until the docs agent fills it)."""
    root = '../'
    return (page_head(f'API and terminal | {SITE_NAME} (unofficial)', 'How to use the unofficial GL.iNet firmware overview from scripts and the terminal.',
                      canonical=f'{SITE_URL}/{DOCS_DIR}/', root=root)
            + site_header(root, 'API and terminal', lead='Placeholder.', current='docs')
            + '<main class="wrap"></main>' + site_footer(root) + '</body>\n</html>\n')

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
