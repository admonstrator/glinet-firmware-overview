"""Render the whole site from the fixture in tests/fixtures, without network access.

    python3 tests/build_offline.py [--out DIR]

Prints the output directory. Used by tests/test_site.py and handy for looking at pages:
    python3 -m http.server 8800 --directory DIR
"""
import argparse
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO, 'tests', 'fixtures')
if REPO not in sys.path:
    sys.path.insert(0, REPO)


def load_fixture():
    with open(os.path.join(FIXTURES, 'metadata.json'), encoding='utf-8') as f:
        metadata = json.load(f)
    with open(os.path.join(FIXTURES, 'models.json'), encoding='utf-8') as f:
        models = json.load(f)
    with open(os.path.join(FIXTURES, 'run.json'), encoding='utf-8') as f:
        run = json.load(f)
    return models, metadata, run['diagnostics'], run['empty_models'], run['generated_at']


def build(out_dir, quiet=True):
    """Render the fixture site into out_dir (created or emptied). Returns out_dir."""
    import generate_page
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    shutil.copytree(os.path.join(REPO, 'images'), os.path.join(out_dir, 'images'))
    shutil.copy(os.path.join(REPO, 'favicon.ico'), out_dir)
    models, metadata, diagnostics, empty_models, generated_at = load_fixture()
    cwd = os.getcwd()
    os.chdir(out_dir)
    try:
        sink = io.StringIO() if quiet else sys.stdout
        with contextlib.redirect_stdout(sink):
            generate_page.write_site(models, metadata, diagnostics, empty_models, generated_at)
    finally:
        os.chdir(cwd)
    return out_dir


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', default=os.path.join(tempfile.gettempdir(), 'glinet-site'))
    args = parser.parse_args()
    print(build(os.path.abspath(args.out), quiet=False))
