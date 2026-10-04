#!/usr/bin/env python3
"""Explainer home page generator (stdlib only).

  build_index.py fetch   discover repos tagged `explainer`, read each live page's <head>, write data/explainers.json
  build_index.py render  turn data/explainers.json (+ thumbs/) into site/index.html

Discovery: public, non-fork, non-archived repos of OWNER that have the GitHub topic `explainer` and Pages enabled.
Per-page metadata (all optional, read from the live page's <head>):
  <meta name="description">, <meta property="og:title|og:image">,
  <meta name="explainer:topic" content="Science">, <meta name="explainer:tags" content="a, b, c">
Missing topic/tags fall back to fallbacks.json, then to "More" / the repo's GitHub topics.
"""
import datetime as dt, html, json, os, re, shutil, sys, urllib.parse, urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OWNER = os.environ.get('OWNER', 'brijs')
INDEX_TOPIC = os.environ.get('INDEX_TOPIC', 'explainer')
SELF = os.environ.get('GITHUB_REPOSITORY', f'{OWNER}/explainers').split('/')[-1]
GENERIC_TOPICS = {INDEX_TOPIC, 'interactive', 'github-pages'}
NEW_DAYS = 7
DATA = ROOT / 'data' / 'explainers.json'


def http(url, limit=None):
    h = {'User-Agent': 'explainer-index'}
    if 'api.github.com' in url:
        h['Accept'] = 'application/vnd.github+json'
        if os.environ.get('GITHUB_TOKEN'):
            h['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
        return r.read(limit) if limit else r.read()


class Head(HTMLParser):
    def __init__(s):
        super().__init__(); s.meta = {}; s.title = None; s._t = False
    def handle_starttag(s, tag, a):
        a = dict(a)
        if tag == 'meta':
            k = a.get('name') or a.get('property')
            if k and a.get('content') is not None:
                s.meta.setdefault(k.lower(), a['content'].strip())
        elif tag == 'title' and s.title is None:
            s.title, s._t = '', True
    def handle_data(s, d):
        if s._t: s.title += d
    def handle_endtag(s, tag):
        if tag == 'title': s._t = False


def repos():
    out, page = [], 1
    while True:
        batch = json.loads(http(f'https://api.github.com/users/{OWNER}/repos?per_page=100&type=owner&page={page}'))
        out += batch
        if len(batch) < 100: return out
        page += 1


def split_tags(s):
    return [t.strip() for t in re.split(r'[,;]', s or '') if t.strip()]


def fetch():
    prev = {e['name']: e for e in json.loads(DATA.read_text())['items']} if DATA.exists() else {}
    fb = json.loads((ROOT / 'fallbacks.json').read_text())
    found = [r for r in repos() if INDEX_TOPIC in r.get('topics', []) and not r['private'] and not r['fork']
             and not r['archived'] and r['has_pages'] and r['name'] != SELF]
    if not found:
        sys.exit('No explainer repos found; refusing to overwrite data (check token / topic).')
    items = []
    for r in sorted(found, key=lambda r: r['created_at']):
        name = r['name']
        url = r.get('homepage') or f'https://{OWNER}.github.io/{name}/'
        if not url.endswith('/') and not re.search(r'\.\w+$', url): url += '/'
        try:
            p = Head(); p.feed(http(url, 400_000).decode('utf-8', 'replace')); m = p.meta
        except Exception as e:
            print(f'WARN {name}: {e}', file=sys.stderr)
            if name in prev: items.append(prev[name]); continue
            p, m = Head(), {}
        f = fb.get(name, {})
        entry = {
            'name': name, 'url': url,
            'title': (m.get('og:title') or (p.title or '').strip() or name),
            'description': m.get('description') or m.get('og:description') or r.get('description') or '',
            'topic': m.get('explainer:topic') or f.get('topic') or 'More',
            'tags': split_tags(m.get('explainer:tags')) or f.get('tags') or [t for t in r.get('topics', []) if t not in GENERIC_TOPICS],
            'image': urllib.parse.urljoin(url, m['og:image']) if m.get('og:image') else None,
            'added': r['created_at'][:10], 'updated': r['pushed_at'][:10], 'pushed_at': r['pushed_at'],
            'thumb': prev.get(name, {}).get('thumb'), 'thumb_stamp': prev.get(name, {}).get('thumb_stamp'),
        }
        items.append(entry)
        print(f"ok   {name:28} {entry['topic']}")
    DATA.parent.mkdir(exist_ok=True)
    DATA.write_text(json.dumps({'owner': OWNER, 'items': items}, indent=2, ensure_ascii=False) + '\n')


def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
def esc(s): return html.escape(s or '', quote=True)


def render():
    data = json.loads(DATA.read_text()); items = data['items']
    cfg = json.loads((ROOT / 'topics.json').read_text()); cfg.pop('_comment', None)
    known = list(cfg)
    topics = sorted({e['topic'] for e in items}, key=lambda t: (t == 'More', t not in known, known.index(t) if t in known else 0, t))
    today = dt.date.today()
    site = ROOT / 'site'
    shutil.rmtree(site, ignore_errors=True); site.mkdir()
    if (ROOT / 'thumbs').exists(): shutil.copytree(ROOT / 'thumbs', site / 'thumbs')
    (site / '.nojekyll').write_text('')
    shutil.copy(DATA, site / 'data.json')

    def meta(t): return cfg.get(t, {})
    sections, chips = [], [f'<button class="chip" data-topic="" aria-pressed="true">All <span>{len(items)}</span></button>']
    for t in topics:
        c = meta(t); color = c.get('color', '#6b7280'); emoji = c.get('emoji', '📚')
        mine = sorted([e for e in items if e['topic'] == t], key=lambda e: e['added'], reverse=True)
        chips.append(f'<button class="chip" data-topic="{slug(t)}" aria-pressed="false">{emoji} {esc(t)} <span>{len(mine)}</span></button>')
        cards = []
        for e in mine:
            thumb = e.get('image') or e.get('thumb')
            media = (f'<img src="{esc(thumb)}" alt="" loading="lazy" width="640" height="360">' if thumb
                     else f'<div class="ph" aria-hidden="true">{emoji}</div>')
            age = (today - dt.date.fromisoformat(e['added'])).days
            badge = '<span class="new">New</span>' if age <= NEW_DAYS else ''
            tags = ''.join(f'<li>{esc(x)}</li>' for x in e['tags'][:6])
            added = dt.date.fromisoformat(e['added']).strftime('%b %-d, %Y')
            hay = esc(' '.join([e['title'], e['description'], t, *e['tags']]).lower())
            cards.append(f'''<a class="card" href="{esc(e['url'])}" data-hay="{hay}">
  <div class="media">{media}{badge}</div>
  <div class="body"><h3>{esc(e['title'])}</h3><p>{esc(e['description'])}</p>
  <ul class="tags">{tags}</ul><div class="foot">Added {added}</div></div></a>''')
        sections.append(f'''<section class="topic" id="{slug(t)}" data-topic="{slug(t)}" style="--accent:{color}">
<header><span class="ico" aria-hidden="true">{emoji}</span><div><h2>{esc(t)} <small>{len(mine)}</small></h2>{f'<p>{esc(c["blurb"])}</p>' if c.get('blurb') else ''}</div></header>
<div class="grid">{''.join(cards)}</div></section>''')
    page = (ROOT / 'templates' / 'index.html').read_text()
    for k, v in {'{{COUNT}}': str(len(items)), '{{TOPICS}}': str(len(topics)), '{{OWNER}}': esc(data['owner']),
                 '{{UPDATED}}': today.strftime('%b %-d, %Y'), '{{CHIPS}}': '\n'.join(chips), '{{SECTIONS}}': '\n'.join(sections)}.items():
        page = page.replace(k, v)
    (site / 'index.html').write_text(page)
    print(f'rendered {len(items)} explainers in {len(topics)} topics -> site/index.html')


if __name__ == '__main__':
    {'fetch': fetch, 'render': render}.get(sys.argv[1] if len(sys.argv) > 1 else '', lambda: sys.exit(__doc__))()
