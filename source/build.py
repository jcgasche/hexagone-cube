#!/usr/bin/env python3
"""Assembles the site from src/ into self-contained pages, one in English and one in French. No dependencies beyond Python 3.

    python3 build.py                       # writes '../Paris Through Stations.html' and '../Paris Through Stations - FR.html' (open them in a browser)
    python3 build.py --only cost,sources   # quick build of some sections, for work on one part (use --out with it)
    python3 build.py --out dist/dev.html   # another output path, for trial builds (dist/ is not kept in git)
    python3 build.py --lang fr --only cost --out dist/fr.html   # the French page alone (see docs/TRANSLATING.md)

What it does, in order:
 1. reads src/sections/manifest.json (the order and titles of sections);
 2. for each section folder reads section.html, and if present section.css, section.js, data.json, sources.json;
 3. replaces {{ expression | format }} with numbers from the model (see CONTRIBUTING.md), and [[key]] with numbered source links;
 4. checks that every internal link has a target and that no long dash slipped into the text;
 5. writes the page: styles, sections, data, scripts.
"""
import argparse, hashlib, html, json, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGES = {'en': os.path.join(ROOT, '..', 'Paris Through Stations.html'),          # the study: the page a reader opens
         'fr': os.path.join(ROOT, '..', 'Paris Through Stations - FR.html')}     # the same study in French, linked from the top bar
PAGE = PAGES['en']
SRC = os.path.join(ROOT, 'src')
FONTS = 'https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap'


GROUP_TITLES = {'en': {'Report': 'Full report'}, 'fr': {'Report': 'Rapport complet', 'Annexes': 'Annexes'}}   # how a group of the manifest is headed in the contents
WORDS = {'en': {'summary': 'Summary', 'chapter': 'Chapter', 'annex': 'Annex', 'later': 'This section is not written yet.'},
         'fr': {'summary': 'Résumé', 'chapter': 'Chapitre', 'annex': 'Annexe', 'later': 'Cette section n’est pas encore écrite.'}}
# the French top bar: the shell is written once, in English, and these few words are swapped
SHELL_FR = [('>Presentation<', '>Présentation<'), ('>Full report<', '>Rapport complet<'), ('Pre-feasibility case, October 2026', 'Étude de préfaisabilité, octobre 2026'),
            ('>Contents<', '>Sommaire<'), ('aria-label="Views"', 'aria-label="Vues"'), ('aria-label="Contents"', 'aria-label="Sommaire"')]
OTHER = {'en': ('fr', 'FR', 'Lire en français'), 'fr': ('en', 'EN', 'Read in English')}


def en_hash(text): return hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]
TR_MARK = re.compile(r'^\s*<!--\s*en:\s*([0-9a-f]{10})\s*-->\s*\n?')


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


LANG = {'v': 'en'}                     # the language being built; French writes 1\u202f234,5 where English writes 1,234.5
def num(x, d=0):
    # round on the shortest decimal form of the number, half away from zero, as Intl.NumberFormat does in the browser
    q = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    s = f'{q:,.{d}f}'
    s = s[1:] if re.fullmatch(r'-0(\.0+)?', s) else s
    if LANG['v'] == 'fr': s = s.replace(',', '\u202f').replace('.', ',')
    return s
def PCT(): return '\u00a0%' if LANG['v'] == 'fr' else '%'
FORMATS = {
    '0': lambda x: num(x, 0), '1': lambda x: num(x, 1), '2': lambda x: num(x, 2), '3': lambda x: num(x, 3),
    'pct': lambda x: num(x * 100, 0) + PCT(), 'pct1': lambda x: num(x * 100, 1) + PCT(),
    'm': lambda x: num(x * 1000, 0),                 # billions shown as millions
    'bn': lambda x: num(x, 1), 'bn2': lambda x: num(x, 2),
    'int': lambda x: num(round(x), 0), 'str': str,
    'g': lambda x: num(x, 0) if abs(x - round(x)) < 1e-9 else num(x, 1),     # 2, 2.5: one decimal only when there is one
    'money': lambda x: ((num(x, 2) + '\u00a0Md€') if abs(x) >= 1 else (num(abs(x) * 1000, 0) + '\u00a0M€')) if LANG['v'] == 'fr' else
                       (('€' + num(x, 2) + 'bn') if abs(x) >= 1 else ('€' + num(abs(x) * 1000, 0) + 'm')),
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
            s = sources[k]                             # the tooltip of a citation: the document and what it is used for (in French, only what it is used for)
            tip = html.escape(s['about_' + LANG['v']] if 'about_' + LANG['v'] in s else f"{s['publisher']}: {s['about']}", quote=True)
            out.append(f'<a href="#sources.{k}" title="{tip}">{numbers[k]}</a>')
        return '<sup class="cite">' + ' '.join(out) + '</sup>' if out else ''
    return CITE.sub(rep, text)


def sources_table(numbers, sources, lang='en'):
    """One row per document. Keys that share a link share the row; each key keeps its own anchor."""
    groups = {}
    for k, n in numbers.items(): groups.setdefault(n, []).append(k)
    rows = []
    for n in sorted(groups):
        keys = groups[n]; s = sources[keys[0]]; url = html.escape(s['url'], quote=True)
        host = re.sub(r'^https?://(www\.)?', '', s['url']).split('/')[0]
        about = []
        for k in keys:
            ab = sources[k].get('about_' + lang, sources[k]['about']) if lang != 'en' else sources[k]['about']
            if ab not in about: about.append(ab)
        extra = ''.join(f'<span id="sources.{k}"></span>' for k in keys[1:])
        rows.append(f'<tr class="src-row" id="sources.{keys[0]}"><td class="num">{n}{extra}</td><th>{html.escape(s["publisher"])}</th><td>{html.escape(("\u00a0; " if lang == "fr" else "; ").join(about))}</td>'
                    f'<td><a href="{url}" target="_blank" rel="noopener">{html.escape(host)}</a></td></tr>')
    th = ('N°', 'Éditeur et document', 'Utilisé pour', 'Lien') if lang == 'fr' else ('No.', 'Publisher and document', 'Used for', 'Link')
    return (f'<div class="tbl-wrap"><table class="tbl"><thead><tr><th class="num">{th[0]}</th><th>{th[1]}</th><th>{th[2]}</th><th>{th[3]}</th></tr></thead><tbody>'
            + '\n'.join(rows) + '</tbody></table></div>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='', help='comma-separated section ids (sources is always added)')
    ap.add_argument('--out', default=None, help="default: the two pages at the root, English and French; a partial build (--only) goes to dist/dev.html")
    ap.add_argument('--lang', default=None, help="en, fr or both (default: both for a full build, en otherwise)")
    ap.add_argument('--strict', action='store_true', help='fail on warnings too')
    a = ap.parse_args()
    langs = ['en', 'fr'] if (a.lang or ('both' if not (a.only or a.out) else 'en')) == 'both' else [a.lang or 'en']
    bad = False
    for lang in langs:
        out = a.out or (os.path.join(ROOT, 'dist', 'dev' + ('' if lang == 'en' else '-' + lang) + '.html') if a.only else PAGES[lang])
        bad = build(a, lang, out) or bad
    if bad: sys.exit(1)


def build(a, lang, out):
    LANG['v'] = lang
    W = WORDS[lang]
    man = jload(SRC, 'sections', 'manifest.json')
    secs = [dict(s) for s in man['sections']]
    only = [x for x in a.only.split(',') if x]
    if only: secs = [s for s in secs if s['id'] in only or s['id'] == 'sources']
    names = jload(SRC, 'i18n', f'manifest.{lang}.json') if lang != 'en' and exists(SRC, 'i18n', f'manifest.{lang}.json') else {}   # titles of the sections in that language
    if lang != 'en':
        for s in secs:
            t = names.get(s['id'], {})
            s['nav'], s['heading'] = t.get('nav_' + lang, s.get('nav_' + lang, s['nav'])), t.get('heading_' + lang, s.get('heading_' + lang, s['heading']))

    # data: global files, then one optional data.json per section
    data = {os.path.splitext(f)[0]: jload(SRC, 'data', f) for f in sorted(os.listdir(os.path.join(SRC, 'data'))) if f.endswith('.json')}
    sources = data.pop('sources')
    problems, warnings = [], []
    i18n = {'exact': {}, 'patterns': []}                # French only: the words the scripts write, from i18n/fr.json and each section's fr.json
    def take(path):
        t = json.loads(read(path)); i18n['exact'].update(t.get('exact', {})); i18n['patterns'].extend(t.get('patterns', []))
    if lang != 'en' and exists(SRC, 'i18n', lang + '.json'): take(os.path.join(SRC, 'i18n', lang + '.json'))
    for s in man['sections']:
        d = os.path.join(SRC, 'sections', s['id'])
        if exists(d, 'data.json'): data[s['id']] = jload(d, 'data.json')
        if exists(d, 'sources.json'):
            for k, v in jload(d, 'sources.json').items():
                if k in sources and sources[k]['url'] != v['url']: problems.append(f"{s['id']}/sources.json: key {k} already used for another source")
                sources[k] = v
        if lang != 'en' and exists(d, lang + '.json'): take(os.path.join(d, lang + '.json'))
    if lang != 'en' and exists(SRC, 'i18n', 'sources.' + lang + '.json'):          # what each source is used for, in French
        for k, v in jload(SRC, 'i18n', 'sources.' + lang + '.json').items():
            if k in sources: sources[k] = dict(sources[k], **{'about_' + lang: v})
    fin = data['finance']
    ctx = {'m': wrap(data['model']), 'f': wrap(fin['cases']), 'b': wrap(fin['base']), 'fp': wrap(fin['params']), 'pts': wrap(data['points']), 'd': wrap(data)}

    # pass 1: read sections, substitute numbers, number the sources in order of first citation
    by_url = {}
    numbers, parts, css, js = {}, [], [read(SRC, 'css', 'base.css'), read(SRC, 'css', 'components.css')], [read(SRC, 'js', f) for f in ('core.js', 'charts.js', 'model.js')]
    chapter = 0; annex = 0
    lent = {x for sec in man['sections'] for x in sec.get('borrows', [])}
    untranslated = []
    for s in secs:
        d = os.path.join(SRC, 'sections', s['id'])
        if s['group'] == 'Presentation': s['label'], s['eyebrow'] = '', ''
        elif s['id'] == 'summary': s['label'], s['eyebrow'] = '', W['summary']
        elif s['group'] == 'Report': chapter += 1; s['label'], s['eyebrow'] = str(chapter), f"{W['chapter']} {chapter}"
        else: annex += 1; s['label'] = 'ABCDEFGH'[annex - 1]; s['eyebrow'] = f"{W['annex']} {s['label']}"
        src_name = 'section.html'
        if lang != 'en' and exists(d, 'section.html'):
            if exists(d, f'section.{lang}.html'):
                src_name = f'section.{lang}.html'
                mo = TR_MARK.match(read(d, src_name))
                if not mo or mo.group(1) != en_hash(read(d, 'section.html')):
                    warnings.append(f"{s['id']}/{src_name}: the English section.html changed since it was translated (first line: <!-- en: {en_hash(read(d, 'section.html'))} -->)")
            else: untranslated.append(s['id'])
        if not exists(d, 'section.html'):
            warnings.append(f"section {s['id']} has no section.html yet"); body = f'<p class="lede">{W["later"]}</p>'
        else:
            body = substitute(TR_MARK.sub('', read(d, src_name), count=1), ctx, s['id'] + '/' + src_name, problems)
        for k in find_cites(body):
            if k in numbers or k not in sources: continue
            url = sources[k]['url']
            if url not in by_url: by_url[url] = len(by_url) + 1          # two keys that point to the same document share a number
            numbers[k] = by_url[url]
        s['body'] = body
        if exists(d, 'section.css'):
            style = read(d, 'section.css')
            if s['id'] in lent:                        # its figures are also shown in another section: its styles follow them there
                style = re.sub(r'#' + s['id'] + r'(?=[\s,.:>{\[)~+])', f":is(#{s['id']}, .borrow-{s['id']})", style)
            css.append(f"/* ---- {s['id']} */\n" + style)
        if exists(d, 'section.js'): js.append(f"/* ---- {s['id']} */\n" + read(d, 'section.js'))
    if untranslated: warnings.append(f"{lang}: not translated yet, shown in English: {', '.join(untranslated)}")

    # pass 2: render
    nav, group = [], None
    for s in secs:
        if s['group'] != group: group = s['group']; nav.append(f'    <h4>{GROUP_TITLES[lang].get(group, group)}</h4>' if group != 'Presentation' else '')
        nav.append(f'    <a href="#{s["id"]}"><i>{s["label"]}</i><span>{html.escape(s["nav"])}</span></a>')
        body = s['body'].replace('<!--SOURCES-->', sources_table(numbers, sources, lang))
        body = render_cites(body, numbers, sources, s['id'], problems)
        lede = ''
        mo = re.match(r'\s*(<p class="lede">.*?</p>)', body, re.S)
        if mo: lede = mo.group(1); body = body[mo.end():]
        if s.get('bare'):                              # a page that draws its own opening (the presentation)
            parts.append(f'<section class="page {s["id"]}" id="{s["id"]}" data-title="{html.escape(s["nav"], quote=True)}" hidden>\n{lede}{body}\n</section>'); continue
        parts.append(f'<section class="page" id="{s["id"]}" data-title="{html.escape(s["nav"], quote=True)}" hidden>\n<header><span class="eyebrow">{s["eyebrow"]}</span><h1>{html.escape(s["heading"])}</h1>{lede}</header>\n{body}\n</section>')
    shell = read(SRC, 'shell.html')
    if lang == 'fr':
        for x, y in SHELL_FR: shell = shell.replace(x, y)
    other = OTHER[lang]
    shell = (shell.replace('<!--LANG-HREF-->', html.escape(os.path.basename(PAGES[other[0]]), quote=True).replace(' ', '%20'))
             .replace('<!--LANG-OTHER-->', other[0]).replace('<!--LANG-TITLE-->', other[2]).replace('<!--LANG-LABEL-->', other[1]))
    page = shell.replace('<!--NAV-->', '\n'.join(nav)).replace('<!--SECTIONS-->', '\n'.join(parts))

    # checks
    ids = set(re.findall(r'\bid="([^"]+)"', page))
    if not only:                                       # a link target must exist in the static page (ids made by scripts are not seen here)
        for target in sorted(set(re.findall(r'href="#([^"]+)"', page))):
            if target not in ids: problems.append(f'{lang}: link to #{target} has no target')
    for s in secs:
        d = os.path.join(SRC, 'sections', s['id'])
        for fn in ('section.html', 'section.js', 'data.json') + ((f'section.{lang}.html', f'{lang}.json') if lang != 'en' else ()):
            if exists(d, fn):
                for i, line in enumerate(read(d, fn).split('\n'), 1):
                    if '—' in line or '–' in line: warnings.append(f"{s['id']}/{fn}:{i}: long dash in text (use a comma, a semicolon or 'to')")
    data_js = 'window.PTS_DATA = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + ';'
    if lang != 'en': data_js += '\nwindow.PTS_LANG = ' + json.dumps(lang) + ';\nwindow.PTS_I18N = ' + json.dumps(i18n, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + ';'
    style = '\n'.join(css); script = '\n'.join(js).replace('</script', '<\\/script')
    title = names.get('title_' + lang, man.get('title_' + lang, man['title'])) if lang != 'en' else man['title']
    head = f'<title>{title}</title>\n<link rel="stylesheet" href="{FONTS}">\n<style>\n{style}\n</style>\n'
    tail = f'<script>\n{data_js}\n</script>\n<script>\n{script}\nPTS.start();\n</script>\n'
    full = (f'<!doctype html>\n<html lang="{lang}">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + head + '</head>\n<body>\n' + page + tail + '</body>\n</html>\n')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f: f.write(full)
    for w in warnings: print('warning:', w)
    for p in problems: print('ERROR:', p)
    print(f'{lang}: {len(secs)} sections, {len(set(numbers.values()))} sources, {os.path.getsize(out) / 1024:.0f} KB -> {os.path.relpath(out, ROOT)}')
    return bool(problems or (a.strict and warnings))


if __name__ == '__main__':
    main()
