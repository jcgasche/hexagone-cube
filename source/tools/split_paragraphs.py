#!/usr/bin/env python3
"""Splits long paragraphs and list items of the report at sentence ends, so that each reads as a short unit. Words are not changed.

    python3 tools/split_paragraphs.py            # every section, English and French; run again after adding a long paragraph
    python3 tools/split_paragraphs.py --check    # only says how many would be split

A paragraph over MAX characters (as read, figures and citations counted short) becomes paragraphs of about TARGET characters, cut only
where a sentence ends outside any inline element. A list item keeps its first part and continues in <p class="cont">. Notes, ledes and
table cells are left alone. The first line of each French file is then updated to the hash of its English file. No packages needed.
"""
import hashlib, json, os, re, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'sections')
MAX, TARGET, MIN_LAST = 480, 340, 130
LINE = re.compile(r'^(\s*)<(p|li)((?: class="[^"]*")?)>(.*)</\2>\s*$')
UP = 'A-ZÀ-ÖØ-Ý'


def plain(x):
    return re.sub(r'<[^>]+>', '', re.sub(r'\[\[.*?\]\]', '', re.sub(r'\{\{.*?\}\}', '9', x)))


def sentences(x):
    """Cuts x after each sentence end that lies outside tags, inline elements, {{ }} and [[ ]]."""
    out, start, i, depth, n = [], 0, 0, 0, len(x)
    while i < n:
        if x.startswith('{{', i): i = x.index('}}', i) + 2; continue
        if x.startswith('[[', i): i = x.index(']]', i) + 2; continue
        if x[i] == '<':
            z = x.index('>', i); t = x[i:z + 1]
            if t.startswith('</'): depth -= 1
            elif not t.endswith('/>') and not re.match(r'<(br|img|wbr)\b', t): depth += 1
            i = z + 1; continue
        if x[i] in '.?!' and depth == 0:
            mo = re.compile(r'(?:\[\[[^\]]*\]\])?(?:</sup>)?\s+(?=[' + UP + r'“"«(]|<strong|<a |\{\{)').match(x, i + 1)
            word = re.search(r'([^\s(]*)$', x[start:i]).group(1)
            if mo and len(word) > 2 and not re.fullmatch(r'(?:e\.g|i\.e|etc|cf|n°|No|no|St|Dr|Mr|vs|av|env|p)', word):
                out.append(x[start:mo.end()].rstrip()); start = i = mo.end(); continue
        i += 1
    out.append(x[start:].rstrip())
    return [s for s in out if s]


def group(parts):
    total = sum(len(plain(p)) for p in parts)
    k = max(1, round(total / TARGET)); target = total / k
    out, cur, size = [], [], 0
    for i, p in enumerate(parts):
        cur.append(p); size += len(plain(p)); rest = sum(len(plain(q)) for q in parts[i + 1:])
        if size >= target * .85 and rest >= MIN_LAST: out.append(' '.join(cur)); cur, size = [], 0
    if cur: out.append(' '.join(cur))
    return out


def split_text(t):
    lines, n = [], 0
    for l in t.split('\n'):
        mo = LINE.match(l)
        if not mo or 'note' in mo.group(3) or 'lede' in mo.group(3) or 'cont' in mo.group(3) or len(plain(mo.group(4))) <= MAX: lines.append(l); continue
        ind, tag, cls, body = mo.groups(); ch = group(sentences(body))
        if len(ch) < 2: lines.append(l); continue
        n += 1
        if tag == 'p': lines += [f'{ind}<p{cls}>{c}</p>' for c in ch]
        else: lines += [f'{ind}<li{cls}>{ch[0]}'] + [f'{ind}  <p class="cont">{c}</p>' for c in ch[1:]] + [f'{ind}</li>']
    return '\n'.join(lines), n


def main():
    man = json.load(open(os.path.join(ROOT, 'manifest.json'), encoding='utf-8')); total = 0
    for s in man['sections']:
        if s['group'] == 'Presentation' or s['id'] in ('sources', 'about'): continue
        d = os.path.join(ROOT, s['id']); en = os.path.join(d, 'section.html'); fr = os.path.join(d, 'section.fr.html')
        changed = False
        for p in (en, fr):
            if not os.path.exists(p): continue
            t = open(p, encoding='utf-8').read(); new, n = split_text(t); total += n
            if n and '--check' not in sys.argv: open(p, 'w', encoding='utf-8').write(new); changed = True
        if changed and os.path.exists(fr):
            h = hashlib.sha1(open(en, encoding='utf-8').read().encode('utf-8')).hexdigest()[:10]
            t = open(fr, encoding='utf-8').read()
            open(fr, 'w', encoding='utf-8').write(re.sub(r'<!-- en: [0-9a-f]{10} -->', '<!-- en: ' + h + ' -->', t, count=1))
    print(total, 'paragraphs and list items split' + (' (check only)' if '--check' in sys.argv else ''))


if __name__ == '__main__':
    main()
