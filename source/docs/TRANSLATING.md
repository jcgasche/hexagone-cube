# The French page

`python3 build.py` writes two pages from the same source: `index.html` (French, the default) and
`en.html` (English). The button at the right of the top bar opens the other one at the same place.
Everything the reader sees must exist in both languages.

## Where the French text lives

| What | English | French |
|---|---|---|
| The text of a section | `src/sections/<id>/section.html` | `src/sections/<id>/section.fr.html` |
| Words a section's script writes (labels, tooltips, legends, read-outs, buttons, table headings, SVG text) | strings in `section.js`, `data.json` or `src/data/*.json` | `src/sections/<id>/fr.json` |
| Words the shared scripts write (`core.js`, `charts.js`, `model.js`) and the labels of `src/data/*.json` | | `src/i18n/fr.json` |
| What each source is used for (the "Used for" column of the sources) | `about` in the sources files | `src/i18n/sources.fr.json`, `{"key": "texte"}` |
| Navigation title and heading of a section | `nav`, `heading` in `manifest.json` | `nav_fr`, `heading_fr` in `manifest.json` |

### section.fr.html

- The first line is `<!-- en: HASH -->`, where HASH is the first 10 characters of the SHA-1 of the English `section.html` it
  translates: `python3 -c "import hashlib;print(hashlib.sha1(open('src/sections/ID/section.html',encoding='utf-8').read().encode()).hexdigest()[:10])"`.
  The build warns when the English changes afterwards, so the French can be brought up to date.
- Same HTML as the English, element for element: the same ids, classes, `href="#..."` links, `[[source]]` citations and
  `{{ expression | format }}` templates, in the same places. Translate only the words, and `title`, `aria-label` and `alt` text.
- The build writes numbers in French (`1 234,5`, `45 %`). Move units after the number, with a non-breaking space:
  `€{{ x | 1 }}bn` becomes `{{ x | 1 }}&nbsp;Md€`; `€{{ x | m }}m` becomes `{{ x | m }}&nbsp;M€`; `€{{ x | 2 }}` becomes `{{ x | 2 }}&nbsp;€`;
  `{{ x | money }}` and `{{ x | pct }}` stay as they are (the build writes `1,23 Md€`, `45 %`). Numbers typed in the text are written
  the French way too (`1 000`, `2,5 km`, `3 h 31` or `3h31`).
- No long dash anywhere (— or –): use a comma, a colon, brackets or "à". French often uses them; this site does not.

### fr.json

```json
{ "exact":    { "Minutes saved against today": "Minutes gagnées par rapport à aujourd’hui" },
  "patterns": [ ["{0} trains standing at a platform, {1} on the move", "{0} trains à quai, {1} en circulation"] ] }
```

- The page translates, as it appears, every text node and every `title`, `aria-label` and `placeholder` the scripts write.
  A text node is the text between two tags: `'<b>' + a + '</b> to ' + b` makes two nodes, `a` and `' to ' + b`.
- `exact`: the whole text of the node, trimmed. `patterns`: for text built with numbers or names, `{0}`, `{1}`... stand for
  the variable parts; each part is translated again (so a name needs its own `exact` entry). When French grammar changes
  with the part (de + le = du, à + le = au), list the full sentences as `exact` entries instead of one pattern.
- Numbers reach these strings already written the French way (`27,4`, `1 234`), because `PTS.fmt` follows the page's language.
- Keep the keys exactly as the script writes them, typographic apostrophes included (’).

## Words

| English | Français |
|---|---|
| through station | gare traversante |
| terminal, terminus | gare terminus, terminus |
| the triangle; the direct link (Montparnasse to Gare de Lyon) | le triangle ; la liaison directe |
| twin-track tunnel, two-track tunnel | tunnel à double voie |
| platform track; platform | voie à quai ; quai |
| portal (where a tunnel comes up) | tête de tunnel |
| ring road | périphérique |
| track field, fan of tracks | faisceau de voies |
| hall (of a station) | halle |
| welcome area | espace d’accueil |
| TGV, high-speed train, high-speed line | TGV, train à grande vitesse, LGV |
| regional express train | TER |
| suburban train, suburban line | train de banlieue (Transilien), ligne de banlieue |
| RER F (today's lines H, K and L), RER G (today's lines P and N) | RER F (les lignes H, K et L d’aujourd’hui), RER G (les lignes P et N d’aujourd’hui) |
| the north, the east, the south-east, the Atlantic (lines) | le Nord, l’Est, le Sud-Est, l’Atlantique |
| Paris Nord-Est, Gare du Nord, Gare de l’Est, Gare de Lyon, Montparnasse, Saint-Lazare | unchanged |
| regular timetable; the Swiss pulse; beat (12 minutes) | horaire cadencé ; le cadencement à la suisse ; cadence (de 12 minutes) |
| the yearly bill; yearly cost | la facture annuelle ; le coût annuel |
| benefits | avantages (socio-économiques) |
| net present value (NPV); benefit-cost ratio; discount rate | valeur actualisée nette (VAN) ; rapport avantages/coûts ; taux d’actualisation |
| paid back in 2073 | remboursé en 2073 |
| grant; regional business tax package; payroll transport levy | subvention ; bouquet de taxes régionales sur les entreprises ; versement mobilité |
| track charges; trainsets | péages ferroviaires ; rames |
| wider effects; value of time | effets élargis ; valeur du temps |
| the French rules (of appraisal) | les règles françaises d’évaluation |
| assumption (tag); illustrative sketch (tag); study point | hypothèse ; croquis indicatif ; point à étudier |
| €41.7bn; €300m | 41,7 Md€ ; 300 M€ |

Write natural, plain French for a general reader, in the same tone as the English: short sentences, no jargon left unexplained.
