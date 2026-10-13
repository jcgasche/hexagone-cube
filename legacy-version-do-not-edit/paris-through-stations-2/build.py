#!/usr/bin/env python3
"""Assembles the site from src/ into one self-contained page. No dependencies beyond Python 3.

    python3 build.py                       # dist/index.html (open it in a browser) and dist/artifact.html (fragment for publishing)
    python3 build.py --only cost,sources   # quick build of some sections, for work on one part
    python3 build.py --out dist/dev.html   # another output path (use one per person when several work at once)

What it does, in order:
 1. reads src/sections/manifest.json (the order and titles of sections);
 2. for each section folder reads section.html, and if present section.css, section.js, data.json, sources.json;
 3. replaces {{ expression | format }} with numbers from the model (see CONTRIBUTING.md), and [[key]] with numbered source links;
 4. checks that every internal link has a target and that no long dash slipped into the text;
 5. writes the page: styles, sections, data, scripts.
"""
import argparse, html, json, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
FONTS = 'https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap'


def read(*p):
    with open(os.path.join(*p), encoding='utf-8') as f: return f.read()
def jload(*p): return json.loads(read(*p))
def exists(*p): return os.path.exists(os.path.join(*p))


class Dot:
    """Lets templates write m.yearly.capex instead of m['yearly']['capex']."""
    def __init__(self, v): object.__setattr__(self, '_v', v)
    def __getattr__(self, k):
        v = object.__getattribute__(self, '_v')
        try: return wrap(v[k])
        except (KeyError, TypeError, IndexError): raise AttributeError(k)
    def __getitem__(self, k): return wrap(object.__getattribute__(self, '_v')[k])
    def __iter__(self): return (wrap(x) for x in object.__getattribute__(self, '_v'))
    def __len__(self): return len(object.__getattribute__(self, '_v'))
    def keys(self): return object.__getattribute__(self, '_v').keys()
    def values(self): return [wrap(x) for x in object.__getattribute__(self, '_v').values()]
def wrap(v): return Dot(v) if isinstance(v, (dict, list)) else v


def num(x, d=0):
    # round on the shortest decimal form of the number, half away from zero, as Intl.NumberFormat does in the browser
    q = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    s = f'{q:,.{d}f}'
    return s[1:] if re.fullmatch(r'-0(\.0+)?', s) else s
FORMATS = {
    '0': lambda x: num(x, 0), '1': lambda x: num(x, 1), '2': lambda x: num(x, 2), '3': lambda x: num(x, 3),
    'pct': lambda x: num(x * 100, 0) + '%', 'pct1': lambda x: num(x * 100, 1) + '%',
    'm': lambda x: num(x * 1000, 0),                 # billions shown as millions
    'bn': lambda x: num(x, 1), 'bn2': lambda x: num(x, 2),
    'int': lambda x: num(round(x), 0), 'str': str,
    'money': lambda x: ('€' + num(x, 2) + 'bn') if abs(x) >= 1 else ('€' + num(abs(x) * 1000, 0) + 'm'),
}


def substitute(text, ctx, where, problems):
    def rep(mo):
        body = mo.group(1); expr, _, fmt = body.rpartition('|') if '|' in body else (body, '', '1')
        expr, fmt = expr.strip(), fmt.strip()
        try:
            val = eval(expr, {'__builtins__': {}, 'abs': abs, 'min': min, 'max': max, 'round': round, 'sum': sum, 'len': len}, ctx)
            return FORMATS[fmt](val)
        except Exception as e:
            problems.append(f'{where}: cannot evaluate {{{{ {body} }}}}: {e!r}'); return '??'
    return re.sub(r'\{\{(.+?)\}\}', rep, text)


CITE = re.compile(r'\[\[([a-z0-9_]+(?:\s*,\s*[a-z0-9_]+)*)\]\]')
def find_cites(text): return [k.strip() for mo in CITE.finditer(text) for k in mo.group(1).split(',')]
def render_cites(text, numbers, sources, where, problems):
    def rep(mo):
        out = []
        for k in [x.strip() for x in mo.group(1).split(',')]:
            if k not in sources: problems.append(f'{where}: unknown source key [[{k}]]'); continue
            s = sources[k]; tip = html.escape(f"{s['publisher']}: {s['about']}", quote=True)
            out.append(f'<a href="#sources.{k}" title="{tip}">{numbers[k]}</a>')
        return '<sup class="cite">' + ' '.join(out) + '</sup>' if out else ''
    return CITE.sub(rep, text)


def sources_table(numbers, sources):
    """One row per document. Keys that share a link share the row; each key keeps its own anchor."""
    groups = {}
    for k, n in numbers.items(): groups.setdefault(n, []).append(k)
    rows = []
    for n in sorted(groups):
        keys = groups[n]; s = sources[keys[0]]; url = html.escape(s['url'], quote=True)
        host = re.sub(r'^https?://(www\.)?', '', s['url']).split('/')[0]
        about = []
        for k in keys:
            if sources[k]['about'] not in about: about.append(sources[k]['about'])
        extra = ''.join(f'<span id="sources.{k}"></span>' for k in keys[1:])
        rows.append(f'<tr class="src-row" id="sources.{keys[0]}"><td class="num">{n}{extra}</td><th>{html.escape(s["publisher"])}</th><td>{html.escape("; ".join(about))}</td>'
                    f'<td><a href="{url}" target="_blank" rel="noopener">{html.escape(host)}</a></td></tr>')
    return ('<div class="tbl-wrap"><table class="tbl"><thead><tr><th class="num">No.</th><th>Publisher and document</th><th>Used for</th><th>Link</th></tr></thead><tbody>'
            + '\n'.join(rows) + '</tbody></table></div>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='', help='comma-separated section ids (sources is always added)')
    ap.add_argument('--out', default=os.path.join(ROOT, 'dist', 'index.html'))
    ap.add_argument('--strict', action='store_true', help='fail on warnings too')
    a = ap.parse_args()

    man = jload(SRC, 'sections', 'manifest.json')
    secs = man['sections']
    only = [x for x in a.only.split(',') if x]
    if only: secs = [s for s in secs if s['id'] in only or s['id'] == 'sources']

    # data: global files, then one optional data.json per section
    data = {os.path.splitext(f)[0]: jload(SRC, 'data', f) for f in sorted(os.listdir(os.path.join(SRC, 'data'))) if f.endswith('.json')}
    sources = data.pop('sources')
    problems, warnings = [], []
    for s in man['sections']:
        d = os.path.join(SRC, 'sections', s['id'])
        if exists(d, 'data.json'): data[s['id']] = jload(d, 'data.json')
        if exists(d, 'sources.json'):
            for k, v in jload(d, 'sources.json').items():
                if k in sources and sources[k]['url'] != v['url']: problems.append(f"{s['id']}/sources.json: key {k} already used for another source")
                sources[k] = v
    fin = data['finance']
    ctx = {'m': wrap(data['model']), 'f': wrap(fin['cases']), 'b': wrap(fin['base']), 'fp': wrap(fin['params']), 'pts': wrap(data['points']), 'd': wrap(data)}

    # pass 1: read sections, substitute numbers, number the sources in order of first citation
    by_url = {}
    numbers, parts, css, js = {}, [], [read(SRC, 'css', 'base.css'), read(SRC, 'css', 'components.css')], [read(SRC, 'js', f) for f in ('core.js', 'charts.js', 'model.js')]
    chapter = 0; annex = 0
    for s in secs:
        d = os.path.join(SRC, 'sections', s['id'])
        if s['id'] == 'summary': s['label'], s['eyebrow'] = '', 'Summary'
        elif s['group'] == 'Report': chapter += 1; s['label'], s['eyebrow'] = str(chapter), f'Chapter {chapter}'
        else: annex += 1; s['label'] = 'ABCDEFGH'[annex - 1]; s['eyebrow'] = f"Annex {s['label']}"
        if not exists(d, 'section.html'):
            warnings.append(f"section {s['id']} has no section.html yet"); body = '<p class="lede">This section is not written yet.</p>'
        else:
            body = substitute(read(d, 'section.html'), ctx, s['id'] + '/section.html', problems)
        for k in find_cites(body):
            if k in numbers or k not in sources: continue
            url = sources[k]['url']
            if url not in by_url: by_url[url] = len(by_url) + 1          # two keys that point to the same document share a number
            numbers[k] = by_url[url]
        s['body'] = body
        if exists(d, 'section.css'): css.append(f"/* ---- {s['id']} */\n" + read(d, 'section.css'))
        if exists(d, 'section.js'): js.append(f"/* ---- {s['id']} */\n" + read(d, 'section.js'))

    # pass 2: render
    nav, group = [], None
    for s in secs:
        if s['group'] != group: group = s['group']; nav.append(f'    <h4>{group}</h4>')
        nav.append(f'    <a href="#{s["id"]}"><i>{s["label"]}</i><span>{html.escape(s["nav"])}</span></a>')
        body = s['body'].replace('<!--SOURCES-->', sources_table(numbers, sources))
        body = render_cites(body, numbers, sources, s['id'], problems)
        lede = ''
        mo = re.match(r'\s*(<p class="lede">.*?</p>)', body, re.S)
        if mo: lede = mo.group(1); body = body[mo.end():]
        parts.append(f'<section class="page" id="{s["id"]}" data-title="{html.escape(s["nav"], quote=True)}" hidden>\n<header><span class="eyebrow">{s["eyebrow"]}</span><h1>{html.escape(s["heading"])}</h1>{lede}</header>\n{body}\n</section>')
    page = read(SRC, 'shell.html').replace('<!--NAV-->', '\n'.join(nav)).replace('<!--SECTIONS-->', '\n'.join(parts))

    # checks
    ids = set(re.findall(r'\bid="([^"]+)"', page))
    if not only:                                       # a link target must exist in the static page (ids made by scripts are not seen here)
        for target in sorted(set(re.findall(r'href="#([^"]+)"', page))):
            if target not in ids: problems.append(f'link to #{target} has no target')
    for s in secs:
        d = os.path.join(SRC, 'sections', s['id'])
        for fn in ('section.html', 'section.js', 'data.json'):
            if exists(d, fn):
                for i, line in enumerate(read(d, fn).split('\n'), 1):
                    if '—' in line or '–' in line: warnings.append(f"{s['id']}/{fn}:{i}: long dash in text (use a comma, a semicolon or 'to')")
    data_js = 'window.PTS_DATA = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + ';'
    style = '\n'.join(css); script = '\n'.join(js).replace('</script', '<\\/script')
    head = f'<title>{man["title"]}</title>\n<link rel="stylesheet" href="{FONTS}">\n<style>\n{style}\n</style>\n'
    tail = f'<script>\n{data_js}\n</script>\n<script>\n{script}\nPTS.start();\n</script>\n'
    full = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + head + '</head>\n<body>\n' + page + tail + '</body>\n</html>\n')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f: f.write(full)
    if not only and os.path.abspath(a.out) == os.path.join(ROOT, 'dist', 'index.html'):
        with open(os.path.join(ROOT, 'dist', 'artifact.html'), 'w', encoding='utf-8') as f: f.write(head + page + tail)
    for w in warnings: print('warning:', w)
    for p in problems: print('ERROR:', p)
    print(f'{len(secs)} sections, {len(set(numbers.values()))} sources, {os.path.getsize(a.out) / 1024:.0f} KB -> {os.path.relpath(a.out, ROOT)}')
    if problems or (a.strict and warnings): sys.exit(1)


if __name__ == '__main__':
    main()
