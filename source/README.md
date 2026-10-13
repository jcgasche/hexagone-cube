# Paris Through Stations

A pre-feasibility case, written as an interactive document, for one project, "the triangle": replacing the four Paris terminals used
by high-speed trains by three deep through stations (Paris Nord-Est under Gare du Nord and Gare de l'Est, Gare de Lyon, Montparnasse)
joined by two pairs of tunnels on a Y and a direct high-speed link between the two southern stations, 48.6 km of twin-track tunnel and
40 platform tracks in all. The tunnels come up on the existing tracks at the ring road (on the eastern line at Rosa Parks). No train reverses in Paris; every high-speed train calls at two of the three stations. The concept, the
central figures and the model keys are in `docs/TRIANGLE_BRIEF.md`.

The document is one self-contained HTML page built from independent sections. Each section can be worked on alone:
its text, its interactive parts, its data and its sources live in one folder.

## Read it

Open `Paris Through Stations.html`, at the root of the repository, in a browser. Nothing else is needed (the two web fonts load from Google Fonts; without a connection
the page falls back to system fonts).

## Rebuild it

```
python3 build.py                 # assembles src/ into ../Paris Through Stations.html
```

Python 3 only, no packages. The build fills in the numbers of the text from the model results, numbers the sources, checks that
every internal link has a target, and warns about long dashes.

To work on one section and look at it (see CONTRIBUTING.md for the conventions):

```
python3 build.py --only financing --out dist/dev-financing.html
node tools/shot.js --file dist/dev-financing.html --hash financing --full --out /tmp/financing.png     # needs Playwright
```

## Change a number

Numbers are never typed into the text. They come from the model:

```
python3 model/nordest.py         # access, traffic, cost                 -> model/outputs/nordest.json
python3 model/finance.py         # the two accounts, return, taxes       -> model/outputs/finance.json
python3 model/export.py          # data the site reads                   -> src/data/model.json, finance.json, points.json
python3 model/timetable.py       # the hour of trains (about 20 minutes)  -> src/sections/timetable/data.json
node tools/check_model.js        # the browser model must give the same numbers as the Python one
python3 build.py
```

Change an assumption in `model/nordest.py` or `model/finance.py` (every assumption is a named constant with a comment), run the
six commands in that order, and every chapter follows. `docs/TRIANGLE_BRIEF.md` lists the keys the templates and scripts can read.

## What is where

| Path | What it is |
|---|---|
| `src/sections/manifest.json` | Order, titles and headings of the sections |
| `src/sections/<id>/` | One folder per section: `section.html`, and optionally `section.js`, `section.css`, `data.json`, `sources.json` |
| `src/css/`, `src/js/` | Shared styles and code: page shell, components, charts, the model in the browser |
| `src/data/` | Model results and shared data; `sources.json` is the shared source list, `paris_geo.json` the outline of Paris |
| `model/` | The Python model and its inputs |
| `tools/` | Screenshot and check scripts |
| `../Paris Through Stations.html` | The built page, the study itself (`dist/` holds trial builds and is not kept) |
| `CONTRIBUTING.md` | How to write a section: components, helpers, rules, agreed anchors |
| `docs/TRIANGLE_BRIEF.md` | The project as modelled: concept, central figures, model keys, writing rules, open study points |

### Sections

| id | Chapter | Interactive parts |
|---|---|---|
| `summary` | Summary | Two accounts at a glance |
| `why` | The problem | One platform in one hour; Lille to Lyon today and through |
| `project` | The project | Map of the network with layers; the numbers; the four parks |
| `stations` | The three stations | Plan and cross-sections; follow a passenger to the platform |
| `works` | Works and stages | Building methods; year-by-year timeline |
| `service` | Trains and timetable | One hour of trains; which trains pair; the direct link; platform calculator |
| `access` | Reaching the station | Map of 1,000 points, two measures, by direction |
| `crossing` | Crossing Paris | Pair selector; regional lines |
| `cost` | Cost | Price explorer; test against built projects |
| `traffic` | Traffic | Evidence from other cities; the estimate |
| `financing` | Financing | The two accounts; the passenger charge; calculator |
| `economy` | Economic return | Benefits, taxes, comparison with other projects |
| `risks` | Risks and next steps | One assumption at a time; study points with filters |
| `zurich`, `elizabeth`, `pulse` | Annexes A to C | Zürich main station, the Elizabeth line, the Swiss timetable |
| `timetable` | Annex D | An evenly spaced hour at the three stations: a clock for each station, trains on an animated map, against a pulse timed for changes |
| `method`, `sources` | Annexes E and F | Method and assumptions; numbered sources |

### The model

| File | Role |
|---|---|
| `model/model.py` | Builds the access times of 1,000 points in Paris and 1,265 communes from the regional network data (needs `shapely` and the network file; its results are already in `model/inputs/`, so it only needs re-running if the network or the grid changes) |
| `model/estimate.py` | Shared constants (values of time, traffic by station, elasticities). Earlier material in it that this document no longer uses is not read by the site |
| `model/nordest.py` | The triangle: access with a choice of boarding station, passengers crossing Paris, regional trains, service plan (pairings, the direct link, platform rule), bottom-up cost with 15% risk, yearly cost, sensitivity tests, stages |
| `model/finance.py` | Operations and capital accounts, the passenger charge and its effect on traffic, Navigo, taxes, rate of return |
| `model/export.py` | Writes the JSON files of `src/data/` and the two measures of the access map |
| `model/timetable.py` | The hour of high-speed trains: searches the minutes of every train at full capacity, under stated rules, for an evenly spaced hour (the one shown) and for one timed for changes (the comparison) |
| `model/inputs/` | Access times by point and by commune, three weightings |
| `src/js/model.js` | The accounts and the cost build-up again, in the browser, for the calculators |

## Publishing

`Paris Through Stations.html` is a complete page for any static host, and opens from disk with no server.

## Status

Version of 13 October 2026, evening: one project, the triangle, with 15% risk on the cost, and the approach tunnels ending at the ring road. Nothing here is a design: quantities are planning assumptions and
the drawings are sketches. The access model, traffic estimates and construction cost were checked twice by an independent
reviewer for an earlier report of 12 October 2026. See "What changed in this version" in the Method annex.
