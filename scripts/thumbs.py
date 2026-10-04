#!/usr/bin/env python3
"""Screenshot each explainer's live page into thumbs/<name>.jpg.

  thumbs.py --pending   print how many thumbnails are missing or stale (no browser needed)
  thumbs.py             take them (needs `pip install playwright && playwright install chromium`)

A thumbnail is retaken when the repo has been pushed to since the last shot. Pages that declare
<meta property="og:image"> are skipped: that image is used directly.
"""
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'explainers.json'
data = json.loads(DATA.read_text())


def pending():
    return [e for e in data['items'] if not e.get('image')
            and (e.get('thumb_stamp') != e['pushed_at'] or not (ROOT / 'thumbs' / f"{e['name']}.jpg").exists())]


if '--pending' in sys.argv:
    print(len(pending())); sys.exit(0)

todo = pending()
if not todo: sys.exit(0)
from playwright.sync_api import sync_playwright  # noqa: E402

(ROOT / 'thumbs').mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(channel=os.environ.get('PW_CHANNEL') or None, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    for e in todo:
        out = ROOT / 'thumbs' / f"{e['name']}.jpg"
        try:
            pg = b.new_page(viewport={'width': 1280, 'height': 720}, device_scale_factor=0.75)
            pg.goto(e['url'], wait_until='load', timeout=45000)
            pg.wait_for_timeout(3000)
            pg.screenshot(path=str(out), type='jpeg', quality=72)
            e['thumb'], e['thumb_stamp'] = f"thumbs/{e['name']}.jpg", e['pushed_at']
            print('shot', e['name'])
        except Exception as ex:
            print(f"WARN thumb {e['name']}: {ex}", file=sys.stderr)
        finally:
            try: pg.close()
            except Exception: pass
    b.close()
DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
