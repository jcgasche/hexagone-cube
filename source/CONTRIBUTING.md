# Working on one part of the site

The site is a set of independent sections. To work on one, you only need this file, the section's own folder and the data it reads.

## Layout of the repository

```
build.py                 assembles everything into ../index.html (French) and ../en.html (English), self-contained pages
src/shell.html           top bar and contents list
src/css/base.css         colours (tokens), type, page shell
src/css/components.css   tiles, cards, tables, figures, controls, bar charts, drawings
src/js/core.js           PTS: section registry, router, formatting, DOM helpers, controls, tooltip
src/js/charts.js         PTS.chart: bars, stack, line, ranges
src/js/model.js          PTS.model: the yearly accounts and the cost build-up, same arithmetic as the Python model
src/data/*.json          model outputs and shared data (written by model/export.py, except sources.json and paris_geo.json)
src/sections/manifest.json   order, titles and headings of sections
src/sections/<id>/       one folder per section:
    section.html         the content (required)
    section.js           the interactive parts (optional)
    section.css          styles only this section needs, every selector prefixed with #<id> (optional)
    data.json            data only this section needs, read as PTS.data['<id>'] (optional)
    sources.json         sources only this section cites, {"key": {"publisher": "", "about": "", "url": ""}} (optional)
model/                   the Python model (see README.md)
tools/shot.js            screenshot of a section, prints console errors and horizontal overflow
tools/check_model.js     checks that src/js/model.js gives the same numbers as the Python model
tools/split_paragraphs.py  cuts long paragraphs at sentence ends, English and French, words unchanged
tools/check_algorithms.js  writes the runnable .py of every algorithm as the page does, and runs each with python3
src/algorithms/          'See the algorithm used': algorithms.json (which figures come from which part of the model, the
                         explanation in English and French, the code to show, what the .py runs), algo.js and algo.css (the dialog)
```

**The presentation** (`src/sections/presentation`) is the landing view, with its own night-blue look. It is `"bare"` in the
manifest (no standard header) and lists in `"borrows"` the sections whose figures it shows as they are: the timetable map and
clocks, the reaching-the-station map and chart, the works before/after. It does not copy them: `PTS.borrow` moves the figure's
nodes into the presentation while it is shown and back when its own section is shown, and the build makes the lending
section's `#<id>` styles also apply under `.borrow-<id>`. A fix to one of those figures therefore shows in both places.

**Two languages.** The build writes the study in French (`index.html`, the default) and in English (`en.html`). A change to the
English text of a section must be carried into its `section.fr.html`, and a new label written by a script into its `fr.json`;
the build warns when a French file is older than its English one. How it works and the words to use: `docs/TRANSLATING.md`.
`node tools/i18n_check.js --hash <ids>` lists what is still in English on the French page.

Build and look at one section while working on it:

```
python3 build.py --only cost --out dist/dev-cost.html
node tools/shot.js --file dist/dev-cost.html --hash cost --out /tmp/cost.png            # 1280 px, light
node tools/shot.js --file dist/dev-cost.html --hash cost --width 400 --dark --full --out /tmp/cost-phone.png
```

`shot.js` needs Playwright (`npm i playwright`, or set `NODE_PATH` to an existing install). Use your own `--out` file so that
two people building at once do not overwrite each other. A full `python3 build.py` also checks every internal link.

## section.html

Start with one `<p class="lede">` (two or three sentences: what this section shows and its main finding). The build puts it under
the heading, which comes from the manifest. Then a series of blocks:

```html
<p class="lede">...</p>

<div class="block" id="cost.units">
  <h2>The prices used</h2>
  <p>Text. A number from the model: €{{ m.cost.A.total | 1 }} billion. A sourced fact.[[cgpc]]</p>
  <figure class="fig">
    <div class="fig-head"><strong>Title that states the finding</strong><span>What is plotted, units</span></div>
    <div id="cost-units-chart"></div>
    <figcaption>How to read it; what is assumption. </figcaption>
  </figure>
</div>
```

- **Anchors.** Every block has an id of the form `<section>.<name>`. Link to any block from anywhere with
  `<a class="xref" href="#cost.units">the prices used</a>`. Link to a whole section with `href="#cost"`. Ids must exist in the
  static HTML (not created by script). The agreed anchors are listed at the end of this file.
- **Numbers from the model** are written `{{ expression | format }}` and filled in at build time, so the text always matches the
  model. Names available: `m` (src/data/model.json), `f` (finance cases, for example `f.A_central.ops_cover`), `b` (finance base),
  `fp` (finance parameters), `pts` (points.json), `d` (all data, `d.<section id>` for a section's own data.json).
  Formats: `0 1 2 3` decimals, `pct`, `pct1`, `m` (billions shown as millions), `int`, `money`, `str`. Arithmetic is allowed:
  `{{ m.cost.A.total - m.cost.B.total | 1 }}`. Never type a model number by hand.
- **Sources** are cited `[[key]]` or `[[key1, key2]]`, keys from src/data/sources.json or the section's sources.json. The build
  turns them into numbered links to the Sources annex. A fact that is not from the model needs a source, or the tag
  `<span class="tag assume">assumption</span>`, or the word "unverified" if it comes from Wikipedia or the press.
- **Drawings that are not to scale or not from a design** carry `<span class="tag sketch">illustrative sketch</span>` in their
  heading, and show as numbers only dimensions that have a source.

- **Points.** A paragraph or list item that opens with a bold phrase ending in a full stop or a colon (`<p><strong>The rule.</strong> ...`)
  is shown with that phrase as a small heading over its text (the build adds the class `pt`). A bold phrase that runs into the sentence
  (`<strong>London had no fast line;</strong> Paris has five`) stays inline.
- **Sub-parts.** Give every point of a part its own title: `<h3>What it is about</h3>` then short text that makes the point. A paragraph that
  opens with a bold phrase (`<p><strong>Who pays.</strong> ...`) in the running text becomes such a title at build time. Both are numbered
  9.1.1, 9.1.2 automatically, and their text lines up under the title.
- **Short paragraphs.** Keep a paragraph under about 480 characters. `python3 tools/split_paragraphs.py` splits longer ones at sentence ends in
  both languages, without changing a word, and updates the French hash. A list item continues in `<p class="cont">`.
- **Formulas.** A rule or a calculation that the text states in words can be set apart, like a displayed equation, in both languages:
  `<div class="formula"><span class="f-label">The platform rule</span><div class="f-math"><span class="cl">...</span><span class="cl">...</span></div><p class="f-note">What the symbols are.</p></div>`.
  Inside `.f-math`: `<var>` for a named quantity, `<span class="op">×</span>` for an operator, `<span class="frac"><span>a</span><span>b</span></span>` for a
  fraction, `<span class="res">` for the result, and one `.cl` per clause (clauses wrap as units). Numbers come from the model as everywhere.
  Keep the paragraph that states the rule in words: the formula restates it, it does not replace it.

Components (all in components.css): `.tiles > .tile` (`.n` number, `.k` label, `.d` detail), `.card`, `.callout` and
`.callout.warn`, `.note`, `.tag`, `.cols` (two columns, stacks on a phone), `.tbl-wrap > table.tbl` (`td.num`, `tr.total`, `tr.hl`),
`figure.fig`, `.controls > .field`, `.seg`, `.slider`, `.steps`, `dl.read`, `.legend`, `.fig-scroll` (horizontal scroll for a wide
drawing), `details` for long evidence tables. A table of four or more columns turns into one card per row on a phone (core.js copies
the column headings into `data-l`); add the class `no-stack` to a table to keep it as a grid, or write your own `data-l` labels.

## section.js

```js
PTS.section('cost', function (root) {          // runs once, the first time the section is shown
  const D = PTS.data.model, F = PTS.fmt, h = PTS.h, s = PTS.s;
  PTS.chart.bars(root.querySelector('#cost-units-chart'), { rows: [...], fmt: F.bn });
});
```

- `PTS.h(tag, attrs, ...children)` and `PTS.s(...)` (SVG) build elements; attrs accept `class`, `text`, `html`, `style` (object),
  `onclick` and any attribute. `PTS.clear(el)`, `PTS.$(sel, root)`, `PTS.$$(sel, root)`.
- `PTS.fmt`: `n(x, d)`, `bn(x)` "€70.5bn", `m(x)` "€286m" (input in billions), `money(x)`, `pct(x)`, `eur(x)`, `M(x)` "2.6 million", `min(x)`, `signed(x)`.
- Controls: `PTS.seg(host, [[value, label], ...], value, onChange, label)`, `PTS.slider(host, {label, min, max, step, value, format, note}, onChange)`,
  `PTS.steps(host, options, value, onChange)`. Each returns `{get, set}`.
- `PTS.tip.bind(el, htmlOrFunction)` gives any element a hover and focus tooltip. `PTS.table(host, cols, rows)` builds a table.
- `PTS.onResize(el, fn)` calls `fn(width)` now and whenever the element's width changes; draw SVG charts inside it.
- Charts: `PTS.chart.bars` (option `compact: true` for narrow cards), `.stack`, `.line`, `.ranges` (option `labelWidth`) (see the comments in charts.js). Series colours are `var(--s1)` to `var(--s8)`, in that fixed order.
- `PTS.model.accounts(options)` and `PTS.model.cost(rates)` recompute the accounts and the cost in the browser.
- `PTS.store.get(key, default)` and `.set(key, value)` remember a small per-viewer choice; the page must work without them.

## See the algorithm used

The build puts a small link "See the algorithm used" under every block of the report whose `{{ }}` figures come from the model. The
keys of the block's expressions (`m.cost...`, `f.central...`, `d.french.cases...`) are matched against the `keys` of each algorithm in
`src/algorithms/algorithms.json`, longest first; a block whose figures come from no algorithm (a section's own design data, a source)
gets no link, and a block with a chart but no `{{ }}` can be given one in `blocks`. The dialog shows the explanation, the figures of the
block with their value, the code of the model (cut from `model/*.py` at build time, by function or constant name, or between two
markers) and a button that builds a runnable .py in the page: the model files the script imports and the inputs they read, packed into
it. When a function is renamed or an algorithm changes, update `algorithms.json` (the build stops if a name is missing) and run
`node tools/check_algorithms.js`.

## Rules that keep the site coherent

1. **Plain words.** The reader is not a rail engineer. Short sentences. Explain a term the first time it appears.
   British spelling. No long dashes anywhere (the build warns): use a comma, a semicolon, "to", or a new sentence.
2. **Honest numbers.** State what the numbers show, including when they are unfavourable. Give ranges where the model has them.
   Say what is measured, what is derived and what is assumed. Do not round a result in a way that changes its meaning.
3. **The triangle only.** The project is three deep through stations (Paris Nord-Est under Gare du Nord and Gare de l'Est,
   Gare de Lyon, Montparnasse) joined by two pairs of tunnels and a direct TGV link between the two southern stations, with 15% risk
   on the cost. The earlier hub at Saint-Denis-Pleyel and the two comparison layouts (A with three pairs, B with two) are no longer
   part of the work; do not mention or compare them. docs/TRIANGLE_BRIEF.md holds the concept, the decisions and the model keys.
4. **Colours are tokens.** Never write a literal colour in a component, a drawing or a script: use the CSS variables of base.css
   (`var(--ink)`, `var(--muted)`, `var(--accent)`, `var(--new)`, `var(--s1)`...). Both light and dark themes must read well.
5. **Charts.** One axis per chart. A legend when there are two or more series. A hover tooltip on every mark. Text in text
   colours, never in a series colour. Titles state the finding. Offer the numbers as a table when a chart carries many.
6. **Drawings.** Inline SVG with a `viewBox`, `role="img"` and an `aria-label`; labels on arrows; wrap in `figure.fig` with a
   caption. Use the `.draw` classes (ground, struct, new, newline, oldline). Wide drawings go in `.fig-scroll`.
7. **Phone width.** Nothing may make the page scroll sideways at 400 px. Check with `shot.js --width 400`.
8. **The published page is sandboxed.** No external requests other than the two Google fonts, no downloads (except the .py the
   algorithm dialog builds in the page), no print dialog,
   no `alert` or `confirm`, no iframes. Everything a section needs is in its folder or in src/data.
9. **Do not edit shared files** (src/css, src/js, build.py, manifest) for the needs of one section; put the code in the
   section's own files and note what could later be shared.

## Numbering

The build numbers the report on its own: in chapter 9, the blocks that open with an `<h2>` are 9.1, 9.2..., the `<h3>` inside them
9.1.1, 9.1.2..., and the figures with a `.fig-head` are Figure 9.1, 9.2... (annexes use their letter: A.1). The contents list shows
the parts of the open chapter. A cross-reference `<a class="xref" href="#cost.units">` to a numbered part or to a chapter carries its
number automatically, so write the words without it. A block with no `<h2>` (an opening row of tiles) is not numbered. Moving or
adding a block renumbers everything at the next build.

## Agreed anchors

```
summary
why        why.terminals why.capacity why.crossing
project    project.network project.networks project.numbers project.parks
stations   stations.nordest stations.lyon stations.montparnasse stations.saintlazare stations.halls stations.depth stations.boarding
works      works.methods works.surface works.stages works.timeline
service    service.hour service.pairing service.link service.platforms
access     access.map access.measure access.findings
crossing   crossing.tgv crossing.regional crossing.suburbs
cost       cost.total cost.units cost.explorer cost.backtest cost.yearly cost.evidence
traffic    traffic.tgv traffic.regional traffic.evidence
financing  financing.accounts financing.operations financing.charge financing.navigo financing.sources financing.capital financing.calculator financing.precedents
economy    economy.benefits economy.tax economy.compare economy.mustbetrue
risks      risks.sensitivity risks.risks risks.stages risks.verify
zurich     zurich.layout zurich.why zurich.results zurich.lessons
elizabeth  elizabeth.line elizabeth.times elizabeth.ridership elizabeth.money elizabeth.lessons
pulse      pulse.idea pulse.nodes pulse.edges pulse.paris
timetable  timetable.cycle timetable.capacity timetable.map timetable.clocks timetable.london timetable.connections timetable.stops timetable.limits
method     method.access method.traffic method.cost method.finance method.assumptions method.changes
sources    sources.<key>
```
