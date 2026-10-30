#!/usr/bin/env python3
"""Assembles the site from src/ into self-contained pages, one in English and one in French. No dependencies beyond Python 3.

    python3 build.py                       # writes '../index.html' (French, the default) and '../en.html' (English); open either in a browser
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
from html.parser import HTMLParser
import argparse, ast, base64, gzip, hashlib, html, json, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGES = {'fr': os.path.join(ROOT, '..', 'index.html'),       # the study in French: the page a reader opens first (and GitHub Pages serves)
         'en': os.path.join(ROOT, '..', 'en.html')}          # the same study in English, linked from the top bar
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
    'hm': lambda x: (lambda m: f"{m // 60}\u00a0h\u00a0{m % 60:02d}" if LANG['v'] == 'fr' else f'{m // 60}h{m % 60:02d}')(int(round(x))),   # minutes as hours and minutes
    'g': lambda x: num(x, 0) if abs(x - round(x)) < 1e-9 else num(x, 1),     # 2, 2.5: one decimal only when there is one
    'money': lambda x: ((num(x, 2) + '\u00a0Md€') if abs(x) >= 1 else (num(abs(x) * 1000, 0) + '\u00a0M€')) if LANG['v'] == 'fr' else
                       (('€' + num(x, 2) + 'bn') if abs(x) >= 1 else ('€' + num(abs(x) * 1000, 0) + 'm')),
}


def substitute(text, ctx, where, problems, record=None, mark=False):
    def rep(mo):
        body = mo.group(1); expr, _, fmt = body.rpartition('|') if '|' in body else (body, '', '1')
        expr, fmt = expr.strip(), fmt.strip()
        try:
            val = eval(expr, {'__builtins__': {}, 'abs': abs, 'min': min, 'max': max, 'round': round, 'sum': sum, 'len': len}, ctx)
            out = FORMATS[fmt](val)
            if record is not None:
                record.append((body, out))
                if mark: return MARK_A + str(len(record) - 1) + MARK_B + out + MARK_Z
            return out
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


# ---------------------------------------------------------------- "See the algorithm used": the code and data behind each figure
ALGO_WORDS = {'en': {'link': 'See the algorithm used', 'title': 'Algorithm used', 'explain': 'Explanation', 'code': 'Code', 'close': 'Close',
                     'uses': 'This part uses', 'figures': 'Figures of this part that it computes', 'expr': 'What it is, and its model value', 'shown': 'Shown as',
                     'more': 'and {n} more', 'download': 'Download a runnable .py', 'lines': 'lines {a} to {z}',
                     'run': 'Runs with Python 3.8 or later, nothing to install: the model files and the inputs it needs are packed into it. Run it with: python3 {file}',
                     'what': 'What the script runs', 'from': 'From the model in source/model/ of the study’s repository',
                     'doc': 'Hexagone³, Paris through stations: one algorithm of the study, with the model files and inputs it needs.'},
              'fr': {'link': 'Voir l’algorithme utilisé', 'title': 'Algorithme utilisé', 'explain': 'Explication', 'code': 'Code', 'close': 'Fermer',
                     'uses': 'Cette partie utilise', 'figures': 'Chiffres de cette partie qu’il calcule', 'expr': 'Ce que c’est, et sa valeur dans le modèle', 'shown': 'Affiché',
                     'more': 'et {n} de plus', 'download': 'Télécharger un .py exécutable', 'lines': 'lignes {a} à {z}',
                     'run': 'Fonctionne avec Python 3.8 ou plus récent, sans rien installer : les fichiers du modèle et les données nécessaires sont inclus. Lancez-le avec : python3 {file}',
                     'what': 'Ce qu’exécute le script', 'from': 'Tiré du modèle, dans source/model/ du dépôt de l’étude',
                     'doc': 'Hexagone³, gares traversantes à Paris : un algorithme de l’étude, avec les fichiers du modèle et les données dont il a besoin.'}}
KEY = re.compile(r'(?<![\w.\'"])(m|f|b|fp|pts|d)((?:\.[A-Za-z_]\w*)+)')
MODEL = os.path.join(ROOT, 'model')
QUOTE3 = "'" * 3



MARK_A, MARK_B, MARK_Z = '', '', ''          # around a figure in a block: MARK_A n MARK_B value MARK_Z
VOID = {'br', 'img', 'input', 'hr', 'meta', 'link', 'wbr', 'col', 'area', 'source'}


class _Tree(HTMLParser):
    """Just enough of a DOM to find the words around a figure: tags, classes and text, in order."""
    def __init__(self):
        super().__init__(convert_charrefs=True); self.root = {'tag': '', 'cls': [], 'kids': [], 'up': None}; self.at = self.root
    def handle_starttag(self, tag, attrs):
        a = dict(attrs); n = {'tag': tag, 'cls': (a.get('class') or '').split(), 'kids': [], 'up': self.at, 'span': int(a.get('colspan') or 1)}
        self.at['kids'].append(n)
        if tag not in VOID: self.at = n
    def handle_startendtag(self, tag, attrs): self.at['kids'].append({'tag': tag, 'cls': [], 'kids': [], 'up': self.at})
    def handle_endtag(self, tag):
        n = self.at
        while n is not self.root and n['tag'] != tag: n = n['up']
        if n is not self.root: self.at = n['up']
    def handle_data(self, d): self.at['kids'].append(d)


def _text(n):
    return n if isinstance(n, str) else ''.join(_text(k) for k in n['kids'] if n.get('tag') not in ('style', 'script'))


def _clean(t, keep):
    """Words of a node: the figure `keep` marked for the page to show in bold, the other figures as their values, no citations."""
    t = re.sub(MARK_A + r'(\d+)' + MARK_B + '(.*?)' + MARK_Z, lambda m: ('\u0001' + m.group(2) + '\u0002') if int(m.group(1)) == keep else m.group(2), t)
    t = re.sub(r'\[\[[^\]]*\]\]', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def figure_context(marked):
    """For each figure n of a block (marked by substitute(mark=True)): the words of the page that say what it is. A figure in a tile is
    named by the tile's label; in a table, by its row and its column; elsewhere, by the sentence it stands in."""
    tr = _Tree(); tr.feed(marked); out = {}
    def walk(n):
        for k in n['kids']:
            if isinstance(k, str):
                for m in re.finditer(MARK_A + r'(\d+)' + MARK_B, k): out.setdefault(int(m.group(1)), describe(n, int(m.group(1))))
            else: walk(k)
    def up(n, test):
        while n is not None and n is not tr.root:
            if test(n): return n
            n = n['up']
        return None
    def describe(n, i):
        tile = up(n, lambda x: 'tile' in x['cls'])
        if tile and up(n, lambda x: 'n' in x['cls']):
            k = next((c for c in tile['kids'] if not isinstance(c, str) and 'k' in c['cls']), None)
            if k: return _clean(_text(k), i)
        cell = up(n, lambda x: x['tag'] in ('td', 'th'))
        if cell and not up(cell, lambda x: x['tag'] == 'thead') and len(_clean(_text(cell), -1)) <= 60:     # a long cell is prose: its sentence says more
            row = cell['up']; cells = [c for c in row['kids'] if not isinstance(c, str) and c['tag'] in ('td', 'th')]
            table = up(row, lambda x: x['tag'] == 'table')
            parts = []
            if cells and cells[0] is not cell: parts.append(_clean(_text(cells[0]), -1))
            if table:
                th = [x for x in table['kids'] if not isinstance(x, str) and x['tag'] == 'thead']
                rows = [r for r in th[0]['kids'] if not isinstance(r, str) and r['tag'] == 'tr'] if th else []
                if rows:
                    col = sum(c.get('span', 1) for c in cells[:cells.index(cell)])
                    hs = []
                    for r in rows:                               # the heading over that column, on each heading row
                        x = 0; hc = [c for c in r['kids'] if not isinstance(c, str) and c['tag'] in ('td', 'th')]
                        skip = len(cells) and len(hc) and r is not rows[0] and sum(c.get('span', 1) for c in hc) < sum(c.get('span', 1) for c in cells)
                        x = sum(c.get('span', 1) for c in cells) - sum(c.get('span', 1) for c in hc) if skip else 0
                        for c in hc:
                            if x <= col < x + c.get('span', 1): hs.append(_clean(_text(c), -1)); break
                            x += c.get('span', 1)
                    hs = [h for h in hs if h]
                    if hs: parts.append(', '.join(hs))
            if parts: return ': '.join(parts) if len(parts) == 2 else parts[0]
        svgt = up(n, lambda x: x['tag'] == 'text')
        if svgt: return _clean(_text(svgt), i)
        box = up(n, lambda x: x['tag'] in ('p', 'li', 'figcaption', 'dd', 'dt', 'td', 'th', 'summary', 'span') and (x['tag'] != 'span' or x['cls'])) or n
        t = _clean(_text(box), i)
        sents = re.split(r'(?<=[.;!?])\s+(?=[A-ZÀ-Ý\u0001(])', t)
        s = next((x for x in sents if '\u0001' in x), t)
        if len(s) > 220:                                       # a long sentence: the words around the figure
            p = s.index('\u0001'); a = max(0, p - 120); z = min(len(s), p + 100)
            s = ('… ' if a else '') + s[a:z].strip() + (' …' if z < len(s) else '')
        return s
    walk(tr.root)
    return out


def algo_catalogue():
    """The algorithms of src/algorithms/algorithms.json, with the code of each piece cut from the model files at build time."""
    cat = jload(SRC, 'algorithms', 'algorithms.json')
    trees = {}
    def tree(f):
        if f not in trees:
            text = read(ROOT, f); trees[f] = (text.split('\n'), ast.parse(text))
        return trees[f]
    def span(lines, node):                       # a statement, and the comment lines that continue it below (indented, nothing but a comment)
        a, z = node.lineno, node.end_lineno
        if getattr(node, 'decorator_list', None): a = min(d.lineno for d in node.decorator_list)
        while z < len(lines) and re.match(r'\s+#', lines[z]): z += 1
        return a, z
    for al in cat['algorithms']:
        pieces = []
        for f, names in al['code']:
            lines, tr = tree(f)
            for n in names:
                if isinstance(n, dict):                # the lines from one marker to the end of the statement that holds the other
                    a = next(i for i, l in enumerate(lines, 1) if l.startswith(n['from']))
                    z0 = next(i for i, l in enumerate(lines, 1) if i >= a and n['to'] in l)
                    z = max([s.end_lineno for s in ast.walk(tr) if isinstance(s, ast.stmt) and s.lineno <= z0 <= s.end_lineno
                             and s.end_lineno - s.lineno < 40] or [z0])
                    pieces.append((f, a, z)); continue
                found = None
                for s in tr.body:
                    if isinstance(s, (ast.FunctionDef, ast.ClassDef)) and s.name == n: found = s
                    elif isinstance(s, (ast.Assign, ast.AnnAssign)):
                        tg = s.targets if isinstance(s, ast.Assign) else [s.target]
                        if n in [x.id for t in tg for x in ([t] if isinstance(t, ast.Name) else getattr(t, 'elts', [])) if isinstance(x, ast.Name)]: found = s
                    if found: break
                if found is None: raise SystemExit(f"algorithms.json: {al['id']}: no {n} in {f}")
                pieces.append((f, *span(lines, found)))
        order = [x[0] for x in al['code']]
        out = []                                       # in file order, overlapping or touching pieces merged
        for f, a, z in sorted(set(pieces), key=lambda p: (order.index(p[0]), p[1])):
            if out and out[-1][0] == f and a <= out[-1][2] + 1: out[-1][2] = max(out[-1][2], z)
            else: out.append([f, a, z])
        al['pieces'] = [{'file': f, 'start': a, 'text': '\n'.join(tree(f)[0][a - 1:z])} for f, a, z in out]
        # the files the runnable script needs: the model modules it imports, and the inputs they read
        imports = lambda text: re.findall(r'^\s*(?:import|from)\s+(\w+)', text, re.M)
        mods, todo = [], imports(al['run'])
        while todo:
            x = todo.pop()
            if x in mods or not os.path.exists(os.path.join(MODEL, x + '.py')): continue
            mods.append(x); todo += imports(read(MODEL, x + '.py'))
        al['files'] = sorted('model/' + x + '.py' for x in mods) + cat['data']['base'] + (cat['data']['french'] if 'french' in mods else []) + al.get('data', [])
        for x in al['files']:
            if x.endswith('.py') and QUOTE3 in read(ROOT, x): raise SystemExit(f'{x}: holds three single quotes in a row, so it cannot be packed into a raw string')
    cat['by_key'] = sorted(((tuple(k.split('.')), al['id']) for al in cat['algorithms'] for k in al['keys']), key=lambda kv: -len(kv[0]))
    return cat


def algo_of(cat, key):
    parts = tuple(key.split('.'))
    return next((a for k, a in cat['by_key'] if parts[:len(k)] == k), None)


def top_blocks(text):
    """[(start, end, id)] of the outermost <div class="block"> of a section: end is the position of its closing </div>."""
    out, stack = [], []
    for mo in re.finditer(r'<div\b([^>]*)>|</div>', text):
        if mo.group(0) != '</div>':
            cls = re.search(r'class="([^"]*)"', mo.group(1) or ''); idm = re.search(r'\bid="([^"]*)"', mo.group(1) or '')
            stack.append((mo.start(), 'block' in (cls.group(1).split() if cls else []), idm.group(1) if idm else None))
        elif stack:
            a, is_block, bid = stack.pop()
            if is_block and not any(s[1] for s in stack): out.append((a, mo.start(), bid))
    return sorted(out)


def algo_blocks(cat, sec, raw, ctx):
    """For each block of a section: the algorithms its figures come from (most used first) and each figure with its value as shown."""
    res = []
    for i, (a, z, bid) in enumerate(top_blocks(raw)):
        rec, count, figs = [], {}, []
        words = figure_context(substitute(raw[a:z], ctx, sec, [], rec, mark=True))
        for n, (body, shown) in enumerate(rec):
            expr = body.rpartition('|')[0].strip() if '|' in body else body.strip()
            ids = [x for x in (algo_of(cat, mo.group(1) + mo.group(2)) for mo in KEY.finditer(expr)) if x]
            for x in ids: count[x] = count.get(x, 0) + 1
            if ids and not any(f[0] == expr for f in figs): figs.append([expr, shown, sorted(set(ids), key=ids.index), words.get(n, '')])
        algos = sorted(count, key=lambda x: -count[x]) or cat['blocks'].get(bid, [])
        res.append((bid or f'{sec}.{i + 1}', algos, figs))
    return res


POINT = re.compile(r'<(p|li)>(<strong>(?:(?!</strong>).)*[.:!?]</strong>)')
def mark_points(body):
    """A paragraph or list item that opens with a bold phrase ending in a full stop or a colon is a point: it gets the class pt, and the
    page shows the phrase as a small heading over its text."""
    return POINT.sub(lambda m: f'<{m.group(1)} class="pt">{m.group(2)}', body)


TAG = re.compile(r'<(/?)(div|figure|details|table|ul|ol)\b([^>]*)>|<p class="pt"><strong>((?:(?!</strong>).)*)</strong>')
def promote_points(body, longest=110):
    """A point that stands in the running text of a block, not in a card, a figure or a list, is a sub-part: its bold phrase becomes an
    <h3>, numbered with the others, and the rest of the paragraph its content."""
    stack, found = [], []
    for mo in TAG.finditer(body):
        if mo.group(4) is not None:
            title = mo.group(4)
            if stack and all(t == 'div' and c.split() and c.split()[0] in ('block', 'cols', 'prose') for t, c in stack) and len(re.sub(r'<[^>]+>', '', title)) <= longest:
                found.append(mo)
        elif mo.group(1): stack and stack.pop()
        elif not mo.group(0).endswith('/>'):
            c = re.search(r'class="([^"]*)"', mo.group(3) or ''); stack.append((mo.group(2), c.group(1) if c else ''))
    for mo in reversed(found):
        title = re.sub(r'[\s\u00a0]*[.:]$', '', mo.group(4)); z = body.index('</p>', mo.end()); rest = body[mo.end():z].strip()
        body = body[:mo.start()] + f'<h3 class="sub">{title}</h3>' + (f'\n<p>{rest}</p>' if rest else '') + body[z + 4:]
    return body


FIG_WORD = {'en': 'Figure', 'fr': 'Figure'}
H2 = re.compile(r'<h2>'); H3 = re.compile(r'<h3( class="sub")?>'); FIG = re.compile(r'<figure class="fig[^"]*"[^>]*>'); FIG_HEAD = re.compile(r'<div class="fig-head">')


def number_body(body, label, lang):
    """Numbers the parts of a chapter: its blocks with an <h2> are L.1, L.2..., their <h3> L.1.1, L.1.2..., its figures Figure L.1...
    Returns the body, {block id: number} and the list of (id, number, title) for the contents."""
    nums, entries, out, k = {}, [], [], 0
    for a, z, bid in top_blocks(body):
        chunk = body[a:z]
        mo = H2.search(chunk)
        if not mo: continue
        k += 1; n = f'{label}.{k}'
        title = re.sub(r'<[^>]+>', '', chunk[mo.end():chunk.index('</h2>', mo.end())]).strip()
        chunk = chunk[:mo.start()] + f'<h2><span class="num">{n}</span>' + chunk[mo.end():]
        j = [0]
        def h3(m): j[0] += 1; return f'<h3{m.group(1) or ""}><span class="num">{n}.{j[0]}</span>'
        chunk = H3.sub(h3, chunk)
        out.append((a, z, chunk))
        if bid: nums[bid] = n; entries.append((bid, n, title))
    for a, z, chunk in sorted(out, key=lambda x: -x[0]): body = body[:a] + chunk + body[z:]
    f = [0]
    def fig(m):
        head = FIG_HEAD.search(body, m.end()); nxt = FIG.search(body, m.end())
        if not head or (nxt and nxt.start() < head.start()): return m.group(0)       # a figure with no head is not numbered
        f[0] += 1; return m.group(0) + f'\x00{FIG_WORD[lang]} {label}.{f[0]}\x00'
    body = FIG.sub(fig, body)
    body = re.sub(r'\x00([^\x00]*)\x00(.*?<div class="fig-head">)', lambda m: m.group(2) + f'<span class="fig-num">{m.group(1)}</span>', body, flags=re.S)
    return body, nums, entries


XREF = re.compile(r'<a class="xref" href="#([^"]+)">')
def number_xrefs(page, nums):
    """A cross-reference to a numbered part or chapter carries its number."""
    return XREF.sub(lambda m: m.group(0) + (f'<i class="xnum">{nums[m.group(1)]}</i>' if m.group(1) in nums else ''), page)


def algo_link(lang, key, algos):
    return (f'<p class="algo-link"><button type="button" class="algo-btn" data-block="{html.escape(key, quote=True)}" data-algos="{" ".join(algos)}">'
            f'{ALGO_WORDS[lang]["link"]}</button></p>\n')


def algo_data(cat, lang, blocks):
    """What the page carries for the modal: per algorithm its words and code, per block its figures, and the files the scripts pack."""
    files, algos = {}, {}
    for al in cat['algorithms']:
        algos[al['id']] = {'title': al['title_' + lang], 'explain': [al['goal_' + lang]] + al['explain_' + lang], 'pieces': al['pieces'], 'run': al['run'], 'files': al['files']}
        for x in al['files']:
            if x in files: continue
            data = open(os.path.join(ROOT, x), 'rb').read()
            files[x] = ['text', data.decode('utf-8')] if x.endswith('.py') else ['gz', base64.b64encode(gzip.compress(data, 9, mtime=0)).decode('ascii')]
    return {'words': ALGO_WORDS[lang], 'algos': algos, 'blocks': blocks, 'files': files}


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
    numbers, parts, css, js = {}, [], [read(SRC, 'css', 'base.css'), read(SRC, 'css', 'components.css'), read(SRC, 'algorithms', 'algo.css')], [read(SRC, 'js', f) for f in ('core.js', 'charts.js', 'model.js')] + [read(SRC, 'algorithms', 'algo.js')]
    cat = algo_catalogue(); algo_figs = {}
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
            raw = TR_MARK.sub('', read(d, src_name), count=1)
            body = substitute(raw, ctx, s['id'] + '/' + src_name, problems)
            if s['group'] != 'Presentation' and s['id'] not in cat['skip']:        # the full report: which algorithm each block's figures come from
                s['algo'] = algo_blocks(cat, s['id'], raw, ctx)
                for key, algos, figs in s['algo']:
                    if algos: algo_figs[key] = figs
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
    nav, group, part_nums = [], None, {}
    for s in secs:
        if s['group'] != group: group = s['group']; nav.append(f'    <h4>{GROUP_TITLES[lang].get(group, group)}</h4>' if group != 'Presentation' else '')
        nav.append(f'    <a href="#{s["id"]}"><i>{s["label"]}</i><span>{html.escape(s["nav"])}</span></a>')
        body = s['body'].replace('<!--SOURCES-->', sources_table(numbers, sources, lang))
        body = render_cites(body, numbers, sources, s['id'], problems)
        body = promote_points(mark_points(body))
        if s.get('algo'):                              # a link under every block whose figures come from the model
            blocks = top_blocks(body)
            if len(blocks) != len(s['algo']): problems.append(f"{s['id']}: {len(s['algo'])} blocks in the source, {len(blocks)} once built")
            else:
                for (_, z, _), (key, algos, _) in sorted(zip(blocks, s["algo"]), key=lambda x: -x[0][1]):
                    if algos: body = body[:z] + algo_link(lang, key, algos) + body[z:]
        if s.get('label') or s['id'] == 'summary':     # chapters and annexes: numbered parts, figures, and their list in the contents
            body, bn, entries = number_body(body, s['label'] or 'S', lang)
            part_nums.update(bn); part_nums[s['id']] = s['label'] or 'S'
            if entries: nav.append('    <div class="subs">' + ''.join(f'<a href="#{i}"><i>{n}</i><span>{html.escape(t)}</span></a>' for i, n, t in entries) + '</div>')
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
    page = shell.replace('<!--NAV-->', '\n'.join(nav)).replace('<!--SECTIONS-->', number_xrefs('\n'.join(parts), part_nums))

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
    algo_js = json.dumps(algo_data(cat, lang, algo_figs), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    tail = f'<script type="application/json" id="pts-algo">{algo_js}</script>\n<script>\n{data_js}\n</script>\n<script>\n{script}\nPTS.start();\n</script>\n'
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
