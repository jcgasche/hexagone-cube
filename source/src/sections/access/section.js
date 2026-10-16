PTS.section('access', function (root) {
  'use strict';
  const P = PTS.data.points, G = PTS.data.paris_geo, M = PTS.data.model, F = PTS.fmt, h = PTS.h, s = PTS.s, C = PTS.chart;
  const $ = function (sel) { return root.querySelector(sel); };
  const KEYS = ['Nord', 'Est', 'Lyon', 'Montparnasse'], W = P.w, ROWS = P.rows, N = ROWS.length;
  const col = function (name) { const i = P.cols.indexOf(name); if (i < 0) console.error('access: column ' + name + ' is missing from points.json'); return i; };
  const idx = function (prefix) { return { Nord: col(prefix + '_N'), Est: col(prefix + '_E'), Lyon: col(prefix + '_L'), Montparnasse: col(prefix + '_M') }; };
  const TI = idx('today'), PI = { station: idx('station'), ride: idx('ride') }, ARR = col('arr'), LAT = col('lat'), LON = col('lon'), ID = col('id');
  const STATION = { Nord: 'Gare du Nord', Est: 'Gare de l’Est', Lyon: 'Gare de Lyon', Montparnasse: 'Montparnasse' };
  const DIR = {
    all: { name: 'All directions', toward: 'all directions, weighted by traffic' },
    Nord: { name: 'North', toward: 'the north', ex: 'Lille, London, Brussels' },
    Est: { name: 'East', toward: 'the east', ex: 'Reims, Strasbourg' },
    Lyon: { name: 'South-east', toward: 'the south-east', ex: 'Lyon, Marseille' },
    Montparnasse: { name: 'Atlantic', toward: 'the Atlantic', ex: 'Bordeaux, Rennes, Nantes' }
  };
  const MEASURE = { station: 'to the station entrance', ride: 'counting the ride across Paris' };
  const MEASURES = ['station', 'ride'];
  const NONE = 0.05;                                   // under 3 seconds counts as no change, as in the model's share of quicker points
  const MIN = [[15, 'Under 15 min'], [20, '15 to 20'], [25, '20 to 25'], [30, '25 to 30'], [35, '30 to 35'], [Infinity, '35 min or more']];
  const SAV = [[NONE, 'No change'], [1, 'Up to 1 min saved'], [2, '1 to 2'], [5, '2 to 5'], [10, '5 to 10'], [Infinity, 'More than 10 min saved']];
  const bin = function (v, B) { for (let i = 0; i < B.length; i++) if (v < B[i][0]) return i; return B.length - 1; };
  /* Savings: "no change" is under 0.05 minute; the other classes include their upper bound ("1 to 2" is more than 1 and up to 2). A saving is never negative. */
  const binSaved = function (v) { if (v < NONE) return 0; for (let i = 1; i < SAV.length; i++) if (v <= SAV[i][0] + 1e-9) return i; return SAV.length - 1; };
  const f1 = function (v) { return F.n(v, 1); };
  const ord = function (n) { return n + (n === 1 ? 'st' : n === 2 ? 'nd' : n === 3 ? 'rd' : 'th'); };
  const state = { view: 'saved', measure: 'station', dir: 'all', sel: null };

  // ---------------------------------------------------------------- values
  const wsum = function (p, I) { let t = 0; KEYS.forEach(function (k) { t += W[k] * p[I[k]]; }); return t; };
  const today = function (p, d) { return d === 'all' ? wsum(p, TI) : p[TI[d]]; };
  const proj = function (p, d, m) { return d === 'all' ? wsum(p, PI[m]) : p[PI[m][d]]; };
  const saved = function (p, d, m) { return today(p, d) - proj(p, d, m); };
  const value = function (p) { return state.view === 'today' ? today(p, state.dir) : state.view === 'project' ? proj(p, state.dir, state.measure) : saved(p, state.dir, state.measure); };
  let worst = 0;                                       // the data must never make a point slower than today
  ROWS.forEach(function (p) { MEASURES.forEach(function (m) { ['all'].concat(KEYS).forEach(function (d) { worst = Math.min(worst, saved(p, d, m)); }); }); });
  if (worst < -1e-6) console.error('access: a point is slower than today by ' + (-worst) + ' minutes; the data is broken');

  /* Summary of the 1,000 points. For all directions the figures are the ones exported by the model (computed before rounding),
     so that the map and the text of the report agree to the last digit; for one direction they come from the rows. */
  const cache = {};
  function summary(d, m) {
    const key = d + m; if (cache[key]) return cache[key];
    let st = 0, sp = 0, quick = 0, max = 0;
    ROWS.forEach(function (p) { const a = today(p, d), b = proj(p, d, m); st += a; sp += b; if (a - b >= NONE) quick++; max = Math.max(max, a - b); });
    const out = { today: st / N, project: sp / N, quicker: quick / N, max: max };
    if (d === 'all') { out.today = P.avg.today; out.project = P.avg[m]; out.quicker = P.share_quicker[m]; out.max = P.max_gain[m]; }
    else if (M.by_dir && M.by_dir[d]) { out.today = M.by_dir[d].today; out.project = M.by_dir[d][m]; }
    return (cache[key] = out);
  }

  // ---------------------------------------------------------------- where to board: the two halves of the trains for one direction
  /* Every train stops at two stations. For a direction, half of the trains come through one other station and half through the
     other; each half can be boarded at the direction's own station or at the train's first stop, with the ride between the two
     counted on the ride measure (the run only, P.th, from points.json: the train is already at the platform, so its stop is not counted). The ride measure takes the better half, the passenger picking the train; the station measure averages the halves. */
  function plan(p, d, m) {
    const t = { Nord: p[TI.Nord], Est: p[TI.Est], Lyon: p[TI.Lyon], Montparnasse: p[TI.Montparnasse] }, L = P.th.L, A = P.th.M, LM = P.th.LM;
    const hall = d === 'Est' ? (t.Est <= t.Nord ? 'Est' : 'Nord') : (t.Nord <= t.Est ? 'Nord' : 'Est');
    const ne = function (ride) { return { k: 'NE', hall: hall, name: 'Paris Nord-Est, ' + STATION[hall] + ' hall', t: t[hall], ride: ride }; };
    const st = function (k, ride) { return { k: k, name: STATION[k], t: t[k], ride: ride }; };
    let halves;
    if (d === 'Nord' || d === 'Est') halves = [
      { who: 'from the south-east', c: [ne(0), st('Lyon', L)] },
      { who: 'from the Atlantic', c: [ne(0), st('Montparnasse', A)] }];
    else if (d === 'Lyon') halves = [
      { who: 'from the north or the east', c: [st('Lyon', 0), ne(L)] },
      { who: 'from the Atlantic, by the direct link', c: [st('Lyon', 0), st('Montparnasse', LM)] }];
    else halves = [
      { who: 'from the north or the east', c: [st('Montparnasse', 0), ne(A)] },
      { who: 'from the south-east, by the direct link', c: [st('Montparnasse', 0), st('Lyon', LM)] }];
    const withRide = m !== 'station';
    halves.forEach(function (hf) {
      hf.best = hf.c[0]; hf.total = Infinity;
      hf.c.forEach(function (c) { const tot = c.t + (withRide ? c.ride : 0); if (tot < hf.total - 1e-9) { hf.total = tot; hf.best = c; } });
    });
    const picked = halves[0].total <= halves[1].total + 1e-9 ? halves[0] : halves[1];
    return { today: { name: STATION[d], t: t[d] }, value: p[PI[m][d]], saved: t[d] - p[PI[m][d]], halves: halves, hall: hall, picked: picked,
             same: halves[0].best.k === halves[1].best.k && Math.abs(halves[0].total - halves[1].total) < 1e-9 };
  }

  // ---------------------------------------------------------------- base map
  const lon0 = 2.2235, lon1 = 2.4705, lat1 = 48.9235, kx = Math.cos(48.86 * Math.PI / 180), sx = 1000 / ((lon1 - lon0) * kx);
  const X = function (lon) { return (lon - lon0) * kx * sx; }, Y = function (lat) { return (lat1 - lat) * sx; };
  const path = function (rings) { return rings.map(function (r) { return 'M' + r.map(function (c) { return X(c[0]).toFixed(1) + ',' + Y(c[1]).toFixed(1); }).join('L') + 'Z'; }).join(''); };
  const svg = $('#access-svg'), keys = $('#access-keys');
  svg.appendChild(s('path', { class: 'acc-land', d: path(G.outline) }));
  G.bois.forEach(function (b) { svg.appendChild(s('path', { class: 'acc-park', d: path(b.r) })); });
  G.arr.forEach(function (a) { svg.appendChild(s('path', { class: 'acc-arr', d: path(a.r) })); });
  const gDots = s('g', null); svg.appendChild(gDots);
  const px = ROWS.map(function (p) { return X(p[LON]); }), py = ROWS.map(function (p) { return Y(p[LAT]); });
  const dots = ROWS.map(function (p, i) { const c = s('circle', { class: 'acc-dot', cx: px[i].toFixed(1), cy: py[i].toFixed(1), r: 7.6, 'data-i': i }); gDots.appendChild(c); return c; });
  const mark = s('g', { class: 'acc-mark', 'pointer-events': 'none', visibility: 'hidden' }, s('circle', { class: 'halo', r: 11.5 }), s('circle', { class: 'ring', r: 11.5 }));
  svg.appendChild(mark);
  const NUDGE = { 10: [20, 30] };                        // the number of the 10th arrondissement would sit under the Gare de l’Est hall
  G.arr.forEach(function (a) { const o = NUDGE[a.n] || [0, 0]; svg.appendChild(s('text', { class: 'acc-arrn', x: (X(a.c[0]) + o[0]).toFixed(1), y: (Y(a.c[1]) + 4 + o[1]).toFixed(1), text: a.n })); });

  // stations: today four terminals; with the project Nord-Est is one station drawn with its two halls
  const T = {}; KEYS.forEach(function (k) { T[k] = [X(G.term[k][0]), Y(G.term[k][1])]; });
  const sq = function (c, size) { return s('rect', { x: c[0] - size / 2, y: c[1] - size / 2, width: size, height: size }); };
  const lab = function (c, dx, dy, anchor, text, cls) { return s('text', { x: c[0] + dx, y: c[1] + dy, 'text-anchor': anchor, class: cls || null, text: text }); };
  const stn = {
    Nord: s('g', { class: 'acc-stn acc-ne-today' }, sq(T.Nord, 14), lab(T.Nord, -13, -9, 'end', STATION.Nord)),
    Est: s('g', { class: 'acc-stn acc-ne-today' }, sq(T.Est, 14), lab(T.Est, 14, 17, 'start', STATION.Est)),
    NE: s('g', { class: 'acc-stn acc-ne-proj' },
      s('line', { class: 'acc-ne-out', x1: T.Nord[0], y1: T.Nord[1], x2: T.Est[0], y2: T.Est[1] }), s('line', { class: 'acc-ne-in', x1: T.Nord[0], y1: T.Nord[1], x2: T.Est[0], y2: T.Est[1] }),
      sq(T.Nord, 11), sq(T.Est, 11),
      lab(T.Nord, 20, -13, 'start', 'Paris Nord-Est'), lab(T.Nord, -20, 5, 'end', 'Gare du Nord hall', 'acc-hall'), lab(T.Est, 20, 14, 'start', 'Gare de l’Est hall', 'acc-hall')),
    Lyon: s('g', { class: 'acc-stn' }, sq(T.Lyon, 14), lab(T.Lyon, 14, 6, 'start', STATION.Lyon)),
    Montparnasse: s('g', { class: 'acc-stn' }, sq(T.Montparnasse, 14), lab(T.Montparnasse, 14, 6, 'start', STATION.Montparnasse))
  };
  const base = { Nord: 'acc-stn acc-ne-today', Est: 'acc-stn acc-ne-today', NE: 'acc-stn acc-ne-proj', Lyon: 'acc-stn', Montparnasse: 'acc-stn' };
  const gSt = s('g', { 'pointer-events': 'none' }); Object.keys(stn).forEach(function (k) { gSt.appendChild(stn[k]); }); svg.appendChild(gSt);
  /* The frame holds Paris with its two woods. On a narrow screen the woods, where there are no points, are cut at the sides so that the dots are larger. */
  PTS.onResize(keys, function (w) { const narrow = w < 520; svg.setAttribute('viewBox', narrow ? '96 118 704 552' : '0 118 1000 552'); svg.classList.toggle('acc-narrow', narrow); });

  // ---------------------------------------------------------------- drawing
  const tiles = { today: $('#access-t-today'), project: $('#access-t-project'), saved: $('#access-t-saved') };
  function render() {
    const d = state.dir, m = state.measure, sav = state.view === 'saved', B = sav ? SAV : MIN, counts = B.map(function () { return 0; });
    gDots.setAttribute('class', sav ? 'acc-sav' : 'acc-min');
    svg.classList.toggle('acc-today', state.view === 'today');
    ROWS.forEach(function (p, i) { const b = sav ? binSaved(value(p)) : bin(value(p), B); counts[b]++; dots[i].setAttribute('class', 'acc-dot b' + b); });
    const a = summary(d, m);
    Object.keys(tiles).forEach(function (k) { tiles[k].setAttribute('aria-pressed', String(state.view === k)); });
    $('#access-n-today').innerHTML = f1(a.today) + '<small>min</small>';
    $('#access-n-project').innerHTML = f1(a.project) + '<small>min</small>';
    $('#access-n-saved').innerHTML = f1(a.today - a.project) + '<small>min</small>';
    $('#access-d-project').textContent = m === 'station' ? 'Average time to the entrance of the nearest station where your train stops' : 'The same, plus the train’s ' + F.n(P.th.L, 0) + '-minute run between its Paris stops (the stop is not counted), picking a train that calls at your best station';
    const forDir = d === 'all' ? 'Trains for all directions, weighted by traffic' : 'Trains for ' + DIR[d].toward + ' (' + DIR[d].ex + ')';
    $('#access-title').textContent = state.view === 'today' ? 'Today: minutes to the terminal that serves your direction'
      : state.view === 'project' ? 'With the project: minutes to a station where your train stops, ' + MEASURE[m]
      : 'Minutes saved against today, ' + MEASURE[m];
    $('#access-sub').textContent = forDir + '. ' + (state.view === 'today'
      ? (d === 'all' ? 'Each direction has its own terminal.' : 'Filled square: the terminal for this direction.')
      : (d === 'all' ? 'Every train stops at two of the three stations.' : 'Filled square: every train for this direction stops there. Outlined square: half of them do.'));
    // legend
    $('#access-legend-title').textContent = sav ? 'Minutes saved against today' : 'Minutes to the station';
    const lg = PTS.clear($('#access-legend'));
    B.forEach(function (b, i) {
      lg.appendChild(h('li', null, h('i', sav && i === 0 ? { class: 'none' } : { style: { '--c': sav ? 'var(--acc-g' + i + ')' : 'var(--acc-m' + i + ')' } }), h('span', { text: b[1] }), h('b', { text: F.n(counts[i], 0) })));
    });
    lg.appendChild(h('li', { class: 'acc-legend-note' }, h('span', { text: sav ? 'Number of points in each class, on the same scale for the two measures. There is no class for “slower”: no point is.' : 'Number of points in each class. The same scale is used for today and for the project.' })));
    // statistics
    $('#access-stats-for').textContent = forDir + '; with the project, ' + MEASURE[m] + '.';
    const st = PTS.clear($('#access-stats'));
    [['Average today', F.min(a.today)], ['Average with the project', F.min(a.project)], ['Average saved', F.min(a.today - a.project)],
     ['Points quicker than today', F.pct(a.quicker)], ['Largest gain', F.min(a.max)], ['Points slower than today', 'none']]
      .forEach(function (r) { st.appendChild(h('dt', { text: r[0] })); st.appendChild(h('dd', { text: r[1] })); });
    // stations
    let on;
    if (state.view === 'today') on = d === 'all' ? { Nord: 'on', Est: 'on', Lyon: 'on', Montparnasse: 'on' } : { Nord: 'off', Est: 'off', Lyon: 'off', Montparnasse: 'off' };
    else on = d === 'all' ? { NE: 'on', Lyon: 'on', Montparnasse: 'on' } : d === 'Lyon' ? { NE: '', Lyon: 'on', Montparnasse: '' } : d === 'Montparnasse' ? { NE: '', Lyon: '', Montparnasse: 'on' } : { NE: 'on', Lyon: '', Montparnasse: '' };
    if (state.view === 'today' && d !== 'all') on[d] = 'on';
    Object.keys(stn).forEach(function (k) { stn[k].setAttribute('class', base[k] + (on[k] ? ' ' + on[k] : '')); });
    readout();
  }

  // ---------------------------------------------------------------- read-out of one point
  const legText = function (c, m) { return m !== 'station' && c.ride > 0 ? f1(c.t) + ' min to ' + c.name + ', then ' + F.n(c.ride, 0) + ' min on the train: ' + f1(c.t + c.ride) + ' min' : f1(c.t) + ' min to ' + c.name; };
  function dirBlock(p, d, m) {
    const pl = plan(p, d, m), box = h('div', { class: 'acc-dir' + (state.dir === d ? ' cur' : '') });
    box.appendChild(h('div', { class: 'acc-dir-h' }, h('b', { text: DIR[d].name }), pl.saved >= NONE ? h('span', { class: 'gain', text: f1(pl.saved) + ' min saved' }) : h('span', { text: 'no change' })));
    box.appendChild(h('p', null, 'Today: ', h('b', { text: f1(pl.today.t) + ' min' }), ' to ' + pl.today.name + '.'));
    if (m === 'ride' && !pl.same) {
      const c = pl.picked.best;
      box.appendChild(h('p', null, 'With the project, picking a train ', h('b', { text: pl.picked.who }), ': ', h('b', { text: f1(pl.value) + ' min' }), ' (' + legText(c, m) + ').'));
      box.appendChild(h('p', { class: 'acc-hint', text: 'The next train, whichever half: ' + f1((pl.halves[0].total + pl.halves[1].total) / 2) + ' min on average.' }));
    } else if (pl.same) {
      const c = pl.halves[0].best; let why = '';
      if (c.k === d) why = ', as today';
      else if (c.k === 'NE' && (d === 'Nord' || d === 'Est')) why = c.hall === d ? ', the same hall as today' : ', the nearer hall of the same station';
      else if (c.k === 'NE') why = ', where half of the trains for ' + DIR[d].toward + ' also stop';
      box.appendChild(h('p', null, 'With the project: ', h('b', { text: f1(pl.value) + ' min' }), m !== 'station' && c.ride > 0 ? ' (' + legText(c, m) + why + ').' : ' to ' + c.name + why + '.'));
    } else {
      box.appendChild(h('p', null, 'With the project: ', h('b', { text: f1(pl.value) + ' min' }), ' on average.'));
      box.appendChild(h('ul', null, pl.halves.map(function (hf, i) { return h('li', null, 'Trains ' + hf.who + ' (half): ' + legText(hf.best, m) + '.'); })));
    }
    return box;
  }
  function readout() {
    const box = $('#access-read'), hint = $('#access-read-hint'), line = $('#access-pick');
    if (state.sel == null) {
      box.hidden = true; hint.hidden = false; $('#access-read-title').textContent = 'One point';
      line.textContent = 'Tap or hover a dot to read its times. With a keyboard, move to the map and use the arrow keys.'; return;
    }
    const p = ROWS[state.sel], d = state.dir, m = state.measure, a = today(p, d), b = proj(p, d, m), where = ord(p[ARR]) + ' arrondissement';
    PTS.clear(line);
    line.appendChild(h('b', { text: 'Point ' + p[ID] + ', ' + where })); line.appendChild(document.createTextNode(', trains for ' + DIR[d].toward + ': ' + f1(a) + ' min today, ' + f1(b) + ' with the project, '));
    line.appendChild(h('b', { text: a - b >= NONE ? f1(a - b) + ' min saved' : 'no change' })); line.appendChild(document.createTextNode('. The read-out gives each direction.'));
    box.hidden = false; hint.hidden = true; PTS.clear(box);
    $('#access-read-title').textContent = 'Point ' + p[ID] + ', ' + where;
    box.appendChild(h('p', { class: 'acc-hint', text: 'Minutes by public transport from this point. With the project, ' + MEASURE[m] + '.' }));
    const order = d === 'all' ? KEYS : [d].concat(KEYS.filter(function (k) { return k !== d; }));
    box.appendChild(h('div', { class: 'acc-dirs' }, order.map(function (k) { return dirBlock(p, k, m); })));
    const ta = today(p, 'all'), pa = proj(p, 'all', m);
    box.appendChild(h('p', { class: 'acc-sum', text: 'All directions, weighted by traffic: ' + f1(ta) + ' min today, ' + f1(pa) + ' with the project, ' + (ta - pa >= NONE ? f1(ta - pa) + ' saved.' : 'no change.') }));
  }

  // ---------------------------------------------------------------- choosing a point: hover, tap, arrow keys
  let pinned = false; const mem = { x: 0, y: 0 };
  function pick(i, keep) {
    if (i === state.sel) return;
    state.sel = i;
    if (i == null) mark.setAttribute('visibility', 'hidden');
    else { mark.setAttribute('transform', 'translate(' + px[i].toFixed(1) + ' ' + py[i].toFixed(1) + ')'); mark.setAttribute('visibility', 'visible'); if (!keep) { mem.x = px[i]; mem.y = py[i]; } }
    readout();
  }
  /* The dot nearest to the pointer is chosen, within two dot widths, so that a finger does not have to hit a dot exactly. */
  function nearest(e) {
    const m = svg.getScreenCTM(); if (!m) return null;
    const x = (e.clientX - m.e) / m.a, y = (e.clientY - m.f) / m.d; let best = null, dist = 30 * 30;
    for (let j = 0; j < N; j++) { const q = (px[j] - x) * (px[j] - x) + (py[j] - y) * (py[j] - y); if (q < dist) { dist = q; best = j; } }
    return best;
  }
  svg.addEventListener('pointermove', function (e) { if (pinned || e.pointerType !== 'mouse') return; const i = nearest(e); if (i != null) pick(i); });
  svg.addEventListener('click', function (e) {
    const i = nearest(e); if (i == null) return;
    if (pinned && state.sel === i) { pinned = false; return; }
    pinned = true; pick(i);
  });
  function move(ux, uy) {
    const cur = state.sel; let pmin = Infinity; const cand = [];
    for (let j = 0; j < N; j++) {
      if (j === cur) continue;
      const dx = px[j] - px[cur], dy = py[j] - py[cur], along = dx * ux + dy * uy, across = Math.abs(dx * uy - dy * ux);
      if (along < 1 || across > 1.5 * along) continue;
      cand.push([j, along]); if (along < pmin) pmin = along;
    }
    let best = null, score = Infinity;
    cand.forEach(function (c) { if (c[1] > pmin + 2) return; const off = ux ? Math.abs(py[c[0]] - mem.y) : Math.abs(px[c[0]] - mem.x); if (off < score) { score = off; best = c[0]; } });
    if (best == null) return;
    pick(best, true); if (ux) mem.x = px[best]; else mem.y = py[best];
  }
  const centre = function () { let best = 0, dist = Infinity; for (let j = 0; j < N; j++) { const q = Math.pow(px[j] - 500, 2) + Math.pow(py[j] - 345, 2); if (q < dist) { dist = q; best = j; } } return best; };
  keys.addEventListener('keydown', function (e) {
    const v = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
    if (v) { e.preventDefault(); pinned = true; if (state.sel == null) pick(centre()); else move(v[0], v[1]); }
    else if (e.key === 'Escape' && state.sel != null) { pinned = false; pick(null); }
  });
  keys.addEventListener('focus', function () { let kb = false; try { kb = keys.matches(':focus-visible'); } catch (e) { kb = true; } if (kb && state.sel == null) { pinned = true; pick(centre()); } });

  // ---------------------------------------------------------------- controls
  Object.keys(tiles).forEach(function (k) { tiles[k].addEventListener('click', function () { state.view = k; render(); }); });
  PTS.seg($('#access-measure'), [['station', 'To the station entrance'], ['ride', 'Counting the ride across Paris']], state.measure, function (v) { state.measure = v; render(); }, 'With the project, measured');
  $('#access-dir').value = state.dir;
  $('#access-dir').addEventListener('change', function (e) { state.dir = e.target.value; render(); });
  render();

  // ---------------------------------------------------------------- findings: by direction
  const dirRows = [{ k: 'all', label: 'All directions', sub: 'weighted by traffic', hl: true }].concat(KEYS.map(function (k) { return { k: k, label: DIR[k].name, sub: F.pct(W[k]) + ' of traffic' }; }));
  C.ranges($('#access-dir-chart'), {
    label: 'Average minutes to a station where the train stops, by direction, today and with the project on the two measures',
    domain: [20, 30], fmt: function (v) { return F.n(v, 0); }, axisLabel: 'minutes (the axis starts at 20)', rowH: 34,
    kinds: { today: { label: 'Today', color: 'var(--today)', shape: 'dot' },
             station: { label: 'With the project, to the station entrance (used for TGV benefits)', color: 'var(--s1)', shape: 'dot' },
             ride: { label: 'With the project, counting the ride across Paris and picking the train', color: 'var(--s1)', shape: 'ring' } },
    rows: dirRows.map(function (r) {
      const a = summary(r.k, 'station'), b = summary(r.k, 'ride'), name = '<b>' + r.label + '</b><br>';
      return { label: r.label, sub: r.sub, hl: r.hl, lo: a.project, hi: a.today, marks: [
        { value: a.today, kind: 'today', tip: name + 'Today: <b>' + F.min(a.today) + '</b>' },
        { value: b.project, kind: 'ride', tip: name + 'With the project, counting the ride across Paris: <b>' + F.min(b.project) + '</b><br><small>' + f1(b.today - b.project) + ' min saved</small>' },
        { value: a.project, kind: 'station', tip: name + 'With the project, to the station entrance: <b>' + F.min(a.project) + '</b><br><small>' + f1(a.today - a.project) + ' min saved</small>' }] };
    })
  });

  // ---------------------------------------------------------------- findings: by arrondissement
  const by = {};
  ROWS.forEach(function (p) { const g = by[p[ARR]] = by[p[ARR]] || { arr: p[ARR], n: 0, today: 0, station: 0, ride: 0 }; g.n++; g.today += today(p, 'all'); g.station += proj(p, 'all', 'station'); g.ride += proj(p, 'all', 'ride'); });
  const arrs = Object.keys(by).map(function (k) { const g = by[k]; g.today /= g.n; g.station /= g.n; g.ride /= g.n; g.savedS = g.today - g.station; g.savedR = g.today - g.ride; g.name = ord(g.arr); return g; });
  arrs.sort(function (a, b) { return b.savedS - a.savedS; });
  C.bars($('#access-arr-chart'), { fmt: function (v) { return f1(v) + ' min'; }, rows: arrs.map(function (g) {
    return { label: g.name, value: g.savedS, mark: g.savedR, color: 'var(--good)',
      tip: '<b>' + g.name + ' arrondissement</b>, ' + g.n + ' points<br>Today: ' + F.min(g.today) + '<br>To the station entrance: ' + F.min(g.station) + ', <b>' + f1(g.savedS) + ' saved</b><br>Counting the ride and picking the train: ' + F.min(g.ride) + ', <b>' + f1(g.savedR) + ' saved</b>' };
  }) });
  PTS.table($('#access-arr-table'), [
    { key: 'name', label: 'Arrondissement' }, { key: 'n', label: 'Points', num: true },
    { key: 'today', label: 'Today', num: true, fmt: f1 }, { key: 'station', label: 'To the station entrance', num: true, fmt: f1 }, { key: 'savedS', label: 'Saved at the entrance', num: true, fmt: f1 },
    { key: 'ride', label: 'Counting the ride', num: true, fmt: f1 }, { key: 'savedR', label: 'Saved with the ride', num: true, fmt: f1 }],
    arrs.slice().sort(function (a, b) { return a.arr - b.arr; }));
});
