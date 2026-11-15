PTS.section('times', function (root) {
  'use strict';
  const D = PTS.data.times, F = PTS.fmt, s = PTS.s, h = PTS.h;
  const $ = function (sel) { return root.querySelector(sel); };
  const ST = D.st, n = ST.length, NAME = 0, X = 1, Y = 2, LINES = 3, ENT = 4, RT = 5, RP = 6;     // a station: name, km east and north of Notre-Dame, lines, entries a day, average minutes to the others today and with the project
  const n0 = function (v) { return F.n(v, 0); }, n1 = function (v) { return F.n(v, 1); };
  const host = $('#tm-map'), legend = $('#tm-legend'), ctl = $('#tm-controls');
  const state = { view: 'saved', from: -1 };                     // from: -1 = the average of every station, else the station the times start from
  let T = null, G = null;                                        // the two tables, one byte a pair of stations: minutes today, minutes saved + 127; 255 = no figure

  // ---- classes
  const SAV = [[-0.999, 'slower', 'var(--tm-slow)'], [1, 'under 1', 'var(--tm-g0)'], [2, '1 to 2', 'var(--tm-g1)'], [5, '2 to 5', 'var(--tm-g2)'], [10, '5 to 10', 'var(--tm-g3)'], [20, '10 to 20', 'var(--tm-g4)'], [1e9, '20 and more', 'var(--tm-g5)']];
  const MIN = [[15, 'under 15', 'var(--tm-m0)'], [30, '15 to 30', 'var(--tm-m1)'], [45, '30 to 45', 'var(--tm-m2)'], [60, '45 to 60', 'var(--tm-m3)'], [90, '60 to 90', 'var(--tm-m4)'], [1e9, 'over 90', 'var(--tm-m5)']];
  const bin = function (v, B) { for (let i = 0; i < B.length; i++) if (v < B[i][0]) return i; return B.length - 1; };
  // minutes for station j in the current view: [today, with the project], or null where the table has no figure
  const pairOf = function (j) {
    if (state.from < 0) return [ST[j][RT], ST[j][RP]];
    if (j === state.from || !T) return null;
    const a = T[state.from * n + j], g = G[state.from * n + j];
    return a === 255 || g === 255 ? null : [a, a - (g - 127)];
  };
  const valueOf = function (p) { return state.view === 'today' ? p[0] : state.view === 'plan' ? p[1] : p[0] - p[1]; };

  // ---- the three tiles choose what the map shows
  const tiles = { today: $('#tm-t-today'), plan: $('#tm-t-plan'), saved: $('#tm-t-saved') };
  Object.keys(tiles).forEach(function (k) { tiles[k].addEventListener('click', function () { state.view = k; draw(); }); });

  // ---- choosing a station
  const list = h('datalist', { id: 'tm-names' }); ST.forEach(function (p) { list.appendChild(h('option', { value: p[NAME] })); });
  const input = h('input', { type: 'text', class: 'tm-input', list: 'tm-names', placeholder: 'Type the name of a station', 'aria-label': 'Station the times start from' });
  const all = h('button', { type: 'button', class: 'tm-all', text: 'All stations' });
  const note = h('span', { class: 'tm-note' });
  ctl.appendChild(h('div', { class: 'field' }, h('span', { text: 'Times from' }), h('div', { class: 'tm-pick' }, input, list, all)));
  ctl.appendChild(note);
  const byName = {}; ST.forEach(function (p, i) { byName[p[NAME].toLowerCase()] = i; });
  const pick = function (i) { if (i >= 0 && !T) return; state.from = i; input.value = i < 0 ? '' : ST[i][NAME]; draw(); };
  input.addEventListener('change', function () { const i = byName[input.value.trim().toLowerCase()]; if (i != null) pick(i); });
  all.addEventListener('click', function () { pick(-1); });
  function unpack(b64) {
    const bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    return new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer().then(function (b) { return new Uint8Array(b); });
  }
  if (window.DecompressionStream) {
    Promise.all([unpack(D.today), unpack(D.saved)]).then(function (r) { T = r[0]; G = r[1]; note.textContent = 'or click a station on the map'; input.disabled = false; })
      .catch(function () { note.textContent = 'The table of station-to-station times could not be opened: the map shows the averages only.'; });
    input.disabled = true; note.textContent = 'Opening the table of times…';
  } else { input.disabled = true; note.textContent = 'This browser cannot open the table of station-to-station times: the map shows the averages only.'; }

  // ---- the map: one drawing, moved and zoomed by its view box
  const HOME = [-37.5, -31, 75, 62], W_MAX = 190, W_MIN = 3;
  let RATIO = HOME[3] / HOME[2];                                 // height over width of the map; taller on a phone
  let vb = HOME.slice();
  const svg = s('svg', { role: 'img', class: 'tm-svg', 'aria-label': 'Map of the stations of the Paris region, coloured by travel time' });
  const gG = s('g', { class: 'tm-geo' }), gD = s('g', { class: 'tm-dots' }), gL = s('g', { class: 'tm-lab' });
  svg.appendChild(gG); svg.appendChild(gD); svg.appendChild(gL);
  const tools = h('div', { class: 'tm-tools' });
  const btn = function (txt, label, fn) { const b = h('button', { type: 'button', class: 'tm-zb', 'aria-label': label, title: label, text: txt }); b.addEventListener('click', fn); tools.appendChild(b); };
  btn('+', 'Zoom in', function () { zoomBy(0.6); });
  btn('−', 'Zoom out', function () { zoomBy(1 / 0.6); });
  btn('Paris', 'Show Paris', function () { goTo([-10.5, -8.2, 21, 17.4]); });
  btn('Suburbs', 'Show Paris and its suburbs', function () { goTo(HOME); });
  btn('Region', 'Show the whole region', function () { goTo([-80, -62, 160, 132]); });
  const hint = h('div', { class: 'tm-hint' }, h('span', { class: 'tm-hint-m', text: 'Drag to move. Click the map, then scroll to zoom.' }), h('span', { class: 'tm-hint-t', text: 'Two fingers to move and zoom.' }));
  host.appendChild(svg); host.appendChild(tools); host.appendChild(hint);
  let engaged = false, timer = null;
  const setBox = function () { svg.setAttribute('viewBox', vb.join(' ')); };
  const clampBox = function () {
    vb[2] = Math.max(W_MIN, Math.min(W_MAX, vb[2])); vb[3] = vb[2] * RATIO;
    vb[0] = Math.max(-100 - vb[2] / 2, Math.min(100 - vb[2] / 2, vb[0])); vb[1] = Math.max(-90 - vb[3] / 2, Math.min(90 - vb[3] / 2, vb[1]));
  };
  const later = function () { clearTimeout(timer); timer = setTimeout(drawMap, 140); };
  function zoomAt(f, cx, cy) {
    const w = Math.max(W_MIN, Math.min(W_MAX, vb[2] * f)); f = w / vb[2];
    vb[0] = cx - (cx - vb[0]) * f; vb[1] = cy - (cy - vb[1]) * f; vb[2] = w; clampBox(); setBox(); later();
  }
  function zoomBy(f) { zoomAt(f, vb[0] + vb[2] / 2, vb[1] + vb[3] / 2); }
  function goTo(v) { const w = v[2], cx = v[0] + v[2] / 2, cy = v[1] + v[3] / 2; vb = [cx - w / 2, cy - w * RATIO / 2, w, w * RATIO]; clampBox(); setBox(); drawMap(); }
  const toMap = function (e) { const r = svg.getBoundingClientRect(); return [vb[0] + (e.clientX - r.left) / r.width * vb[2], vb[1] + (e.clientY - r.top) / r.height * vb[3]]; };
  const ptrs = new Map(); let moved = false, pinch = 0;
  svg.addEventListener('pointerdown', function (e) {
    ptrs.set(e.pointerId, [e.clientX, e.clientY]); moved = false;
    if (ptrs.size === 2) { const a = Array.from(ptrs.values()); pinch = Math.hypot(a[0][0] - a[1][0], a[0][1] - a[1][1]); }
    if (e.pointerType !== 'touch' || engaged || ptrs.size === 2) { try { svg.setPointerCapture(e.pointerId); } catch (x) { /* not capturable */ } }
  });
  svg.addEventListener('pointermove', function (e) {
    const r = svg.getBoundingClientRect(), was = ptrs.get(e.pointerId);
    if (was && (e.pointerType !== 'touch' || engaged || ptrs.size === 2)) {
      const dx = e.clientX - was[0], dy = e.clientY - was[1];
      if (ptrs.size === 2) {
        ptrs.set(e.pointerId, [e.clientX, e.clientY]);
        const a = Array.from(ptrs.values()), d = Math.hypot(a[0][0] - a[1][0], a[0][1] - a[1][1]);
        vb[0] -= dx / 2 / r.width * vb[2]; vb[1] -= dy / 2 / r.height * vb[3];
        if (pinch > 0 && d > 0) { const mx = (a[0][0] + a[1][0]) / 2, my = (a[0][1] + a[1][1]) / 2; zoomAt(pinch / d, vb[0] + (mx - r.left) / r.width * vb[2], vb[1] + (my - r.top) / r.height * vb[3]); pinch = d; }
        else { clampBox(); setBox(); later(); }
        moved = true; PTS.tip.hide(); return;
      }
      if (moved || Math.abs(dx) + Math.abs(dy) > 3) {
        moved = true; ptrs.set(e.pointerId, [e.clientX, e.clientY]);
        vb[0] -= dx / r.width * vb[2]; vb[1] -= dy / r.height * vb[3]; clampBox(); setBox(); later(); svg.classList.add('tm-drag'); PTS.tip.hide(); return;
      }
    }
    const t = e.target.closest ? e.target.closest('[data-i]') : null;
    if (t) PTS.tip.show(tipOf(+t.getAttribute('data-i')), e); else PTS.tip.hide();
  });
  const up = function (e) {
    const had = ptrs.has(e.pointerId); ptrs.delete(e.pointerId); pinch = 0; svg.classList.remove('tm-drag');
    if (!had || moved) return;
    engaged = true; host.classList.add('tm-on');
    const el = document.elementFromPoint(e.clientX, e.clientY), t = el && el.closest ? el.closest('#tm-map [data-i]') : null;     // the pointer is captured by the map: e.target is not the dot
    if (t) { const i = +t.getAttribute('data-i'); pick(i === state.from ? -1 : i); }
  };
  svg.addEventListener('pointerup', up); svg.addEventListener('pointercancel', function (e) { ptrs.delete(e.pointerId); pinch = 0; });
  svg.addEventListener('pointerleave', function () { PTS.tip.hide(); });
  const release = function () { engaged = false; host.classList.remove('tm-on'); };
  host.addEventListener('pointerleave', function (e) { if (e.pointerType !== 'touch') release(); });
  document.addEventListener('pointerdown', function (e) { if (engaged && !host.contains(e.target)) release(); });
  svg.addEventListener('touchmove', function (e) { if (e.touches.length === 2 && e.cancelable) e.preventDefault(); }, { passive: false });
  svg.addEventListener('wheel', function (e) {
    if (!engaged && !e.ctrlKey && !e.metaKey) return;
    e.preventDefault(); const p = toMap(e); zoomAt(Math.exp(Math.max(-60, Math.min(60, e.deltaY)) * 0.004), p[0], p[1]);
  }, { passive: false });

  function tipOf(i) {
    const p = ST[i], q = pairOf(i);
    const num = function (l) { return /^\d/.test(l) ? parseFloat(l) : 100; };
    let t = '<b>' + p[NAME] + '</b><br><small>' + p[LINES].split('|').sort(function (u, v) { return num(u) - num(v) || (u < v ? -1 : 1); }).join(', ') + '</small>';
    t += '<br><span>Passengers entering on a working day:</span> <b>' + n0(Math.round(p[ENT] / 100) * 100) + '</b>';
    if (i === state.from) return t + '<br><span>The times on the map start from this station.</span>';
    if (!q) return t + '<br><span>No time within the morning for this pair of stations.</span>';
    t += '<br><span>' + (state.from < 0 ? 'On average to all the other stations' : 'Starting from') + '</span>' + (state.from < 0 ? '' : ' <b>' + ST[state.from][NAME] + '</b>');
    const nn = state.from < 0 ? n1 : n0, d = q[0] - q[1];
    t += '<br><span>Today:</span> <b>' + nn(q[0]) + ' min</b><br><span>With the project:</span> <b>' + nn(q[1]) + ' min</b>';
    t += '<br>' + (Math.abs(d) < 0.25 ? '<span>No change</span>' : '<span>' + (d > 0 ? 'Saved:' : 'Lost:') + '</span> <b>' + nn(Math.abs(d)) + ' min</b>' + (q[0] > 0 ? ' (' + F.pct(Math.abs(d) / q[0]) + ')' : ''));
    return t + (state.from < 0 && T ? '<br><small><span>Click to see the times from this station.</span></small>' : '');
  }

  const GEO = (PTS.data.flows && PTS.data.flows.geo) || {};
  function drawGeo() {
    PTS.clear(gG);
    const sw = vb[2] / 900;
    (GEO.parks || []).forEach(function (r) { gG.appendChild(s('polygon', { points: r.map(function (p) { return p[0] + ',' + (-p[1]); }).join(' '), class: 'tm-park' })); });
    (GEO.rivers || []).forEach(function (r) { gG.appendChild(s('polyline', { points: r[1].map(function (p) { return p[0] + ',' + (-p[1]); }).join(' '), class: 'tm-river', 'stroke-width': sw * (r[0] === 'Seine' ? 2.4 : 1.7) })); });
    (GEO.dep || []).forEach(function (d) { gG.appendChild(s('polygon', { points: d[1].map(function (p) { return p[0] + ',' + (-p[1]); }).join(' '), class: d[0] === '75' ? 'tm-paris' : 'tm-dep', 'stroke-width': sw * (d[0] === '75' ? 1.6 : 1) })); });
    const FL = PTS.data.flows;                                     // the railway lines, as thin grey threads under the stations
    if (FL && FL.links) FL.links.forEach(function (l) { const a = FL.nodes[l[0]], b = FL.nodes[l[1]]; gG.appendChild(s('line', { x1: a[0], y1: -a[1], x2: b[0], y2: -b[1], class: 'tm-rail', 'stroke-width': sw * 1.1 })); });
  }
  let B = SAV, bins = [];
  function drawMap() {
    const want = (host.clientWidth || 800) < 520 ? 1.15 : HOME[3] / HOME[2];
    if (want !== RATIO) { const cy = vb[1] + vb[3] / 2; RATIO = want; vb[3] = vb[2] * RATIO; vb[1] = cy - vb[3] / 2; }
    setBox(); drawGeo(); PTS.clear(gD); PTS.clear(gL);
    const px = (host.clientWidth || 800) / vb[2], zoom = Math.pow(75 / vb[2], 0.42);
    const rad = function (e) { return Math.max(2.6, Math.min(16, (1.9 + Math.sqrt(e) / 40) * zoom)) / px; };      // the area of a dot follows the passengers of the station
    const inView = function (x, y) { return x > vb[0] && x < vb[0] + vb[2] && y > vb[1] && y < vb[1] + vb[3]; };
    const quiet = function (i) { return state.view === 'saved' && bins[i] === 1; };       // a station that hardly changes: drawn first and small, so that the others stand out
    const dot = function (i) {
      const p = ST[i], x = p[X], y = -p[Y]; if (x < vb[0] - vb[2] * 0.6 || x > vb[0] + vb[2] * 1.6 || y < vb[1] - vb[3] * 0.6 || y > vb[1] + vb[3] * 1.6) return;
      const b = bins[i], q = quiet(i), r = rad(p[ENT]) * (q || b < 0 ? 0.8 : 1.15);
      gD.appendChild(s('circle', { cx: x, cy: y, r: r, 'data-i': i, class: i === state.from ? 'tm-from' : b < 0 ? 'tm-none' : q ? 'tm-b' : 'tm-b tm-hi', fill: i === state.from || b < 0 ? null : B[b][2], 'stroke-width': 0.7 / px }));
    };
    ST.forEach(function (p, i) { if (quiet(i) || bins[i] < 0) dot(i); });      // within each group the busiest first, so that small stations are drawn on top
    ST.forEach(function (p, i) { if (!quiet(i) && bins[i] >= 0) dot(i); });
    if (state.from >= 0) { const p = ST[state.from]; gD.appendChild(s('circle', { cx: p[X], cy: -p[Y], r: rad(p[ENT]) + 5 / px, class: 'tm-ring', 'stroke-width': 2 / px })); }
    // names: the selected station, then the stations that gain most (or the busiest), where there is room
    const fs = Math.max(10, Math.min(13, (host.clientWidth || 800) / 66)) / px, placed = [], most = (host.clientWidth || 800) * (host.clientWidth || 800) * RATIO / 17000;
    const order = ST.map(function (p, i) { return i; }).filter(function (i) { return inView(ST[i][X], -ST[i][Y]); });
    const score = function (i) { const q = pairOf(i); return i === state.from ? 1e9 : (state.view === 'saved' && q ? Math.max(0, q[0] - q[1]) * 1e6 : 0) + Math.sqrt(ST[i][ENT]) * (state.view === 'saved' ? 6 : 1e4); };
    order.sort(function (a, b) { return score(b) - score(a); });
    order.forEach(function (i) {
      if (placed.length >= most) return;
      const p = ST[i], x = p[X], y = -p[Y], r = rad(p[ENT]);
      if (vb[2] > 50 && Math.hypot(x, y) < 6.5 && i !== state.from && placed.length > 3) return;       // inner Paris is too dense to name from afar
      const txt = p[NAME].replace(' - Montigny-le-Bretonneux', '').replace(' (Terminal 2) - TGV', ''), w = txt.length * fs * 0.6 + fs * 0.5, hgt = fs * 1.25, gap = r + fs * 0.3;
      const spots = [[x + gap, y + fs * 0.35, 'start'], [x - gap, y + fs * 0.35, 'end'], [x, y - r - fs * 0.45, 'middle'], [x, y + r + fs * 1.05, 'middle']];
      const box = function (q) { return [q[2] === 'start' ? q[0] : q[2] === 'end' ? q[0] - w : q[0] - w / 2, q[1] - fs * 0.95]; };
      const free = spots.filter(function (q) { const b = box(q); return b[0] > vb[0] && b[0] + w < vb[0] + vb[2] && !(b[1] < vb[1] + 46 / px && b[0] + w > vb[0] + vb[2] - 290 / px) && !(b[1] + hgt > vb[1] + vb[3] - 30 / px && b[0] < vb[0] + 330 / px) && !placed.some(function (o) { return b[0] < o[0] + o[2] && b[0] + w > o[0] && b[1] < o[1] + hgt && b[1] + hgt > o[1]; }); })[0];
      if (!free) return;
      placed.push([box(free)[0], box(free)[1], w]);
      gL.appendChild(s('text', { x: free[0], y: free[1], 'font-size': fs, 'text-anchor': free[2], 'stroke-width': fs * 0.28, class: i === state.from ? 'tm-lab-from' : null, text: txt }));
    });
  }

  function draw() {
    B = state.view === 'saved' ? SAV : MIN;
    const cnt = B.map(function () { return [0, 0]; }); let none = 0;
    bins = ST.map(function (p, i) {
      const q = pairOf(i); if (!q) { if (i !== state.from) none++; return -1; }
      const b = bin(valueOf(q), B); cnt[b][0]++; cnt[b][1] += p[ENT]; return b;
    });
    Object.keys(tiles).forEach(function (k) { tiles[k].setAttribute('aria-pressed', String(state.view === k)); });
    // the three figures: the region, or the chosen station
    let a, b;
    if (state.from < 0) { a = D.k.today; b = D.k.plan; } else { a = ST[state.from][RT]; b = ST[state.from][RP]; }
    $('#tm-n-today').innerHTML = n1(a) + '<small>min</small>'; $('#tm-n-plan').innerHTML = n1(b) + '<small>min</small>';
    $('#tm-n-saved').innerHTML = (state.from < 0 ? F.n(D.k.gain, 2) : n1(a - b)) + '<small>min</small>';
    const who = state.from < 0 ? 'Average time from a station to all the others; every station counts by the passengers who enter it' : 'Average time from this station to all the others, each counted by the passengers who enter it';
    $('#tm-d-today').textContent = who; $('#tm-d-plan').textContent = 'The same, with the trains of the project'; $('#tm-d-saved').textContent = 'The difference between the two';
    const title = $('#tm-title'); PTS.clear(title);
    if (state.from < 0) title.appendChild(h('span', { text: state.view === 'saved' ? 'Each station: minutes saved on average to reach all the others' : state.view === 'today' ? 'Each station: average minutes to reach all the others, today' : 'Each station: average minutes to reach all the others, with the project' }));
    else { title.appendChild(h('span', { text: state.view === 'saved' ? 'Minutes saved to each station, from' : state.view === 'today' ? 'Minutes to each station today, from' : 'Minutes to each station with the project, from' })); title.appendChild(document.createTextNode(' ')); title.appendChild(h('b', { text: ST[state.from][NAME] })); }
    all.disabled = state.from < 0;
    // legend: the classes, with the stations in each and the passengers who enter them
    PTS.clear(legend);
    const row = h('div', { class: 'tm-leg-row' }, h('span', { class: 'tm-leg-t', text: state.view === 'saved' ? 'Minutes saved against today' : 'Minutes' }));
    B.forEach(function (c, i) {
      if (!cnt[i][0]) return;
      row.appendChild(h('span', { class: 'tm-leg-i' }, h('i', { class: 'tm-chip', style: { background: c[2] } }), h('span', { text: c[1] }), h('b', { text: n0(cnt[i][0]) }), h('small', null, '(', n0(Math.round(cnt[i][1] / 1000) * 1000), ')')));
    });
    legend.appendChild(row);
    legend.appendChild(h('div', { class: 'tm-leg-note' }, h('span', { text: 'In bold, the stations in each class; in brackets, the passengers who enter them on a working day. The size of a dot follows those passengers.' })));
    drawMap();
  }
  draw();
  PTS.onResize(host, drawMap);

  // ---- how many commuters gain how much
  const CL = ['Slower by more than 1 minute', 'Within 1 minute of today', '1 to 5 minutes quicker', '5 to 10 minutes quicker', 'More than 10 minutes quicker'];
  const COL = ['var(--tm-slow)', 'var(--neutral-mark)', 'var(--tm-g2)', 'var(--tm-g3)', 'var(--tm-g5)'];
  PTS.chart.bars($('#tm-classes'), { rows: D.trips.classes.map(function (c, i) { return { label: CL[i], value: c.commuters, color: COL[i], text: n0(c.commuters) }; }).filter(function (r, i) { return i !== 1; }), fmt: n0 });
  PTS.table($('#tm-classes-table'), [
    { key: 'label', label: 'Trip to work' },
    { key: 'commuters', label: 'Commuters', num: true, fmt: n0 },
    { key: 'mean', label: 'Minutes saved on average, one trip', num: true, fmt: function (v) { return (v < -0.05 ? '\u2212' : '') + n1(Math.abs(v)) + ' min'; } },
    { key: 'hours', label: 'Hours saved a working day, both ways', num: true, fmt: function (v) { return (v < 0 ? '\u2212' : '') + n0(Math.abs(2 * v)); } }
  ], D.trips.classes.map(function (c, i) { return { label: CL[i], commuters: c.commuters, mean: c.mean, hours: c.hours }; }));

  // ---- examples, line by line, versions
  const mins = function (v) { return n0(v) + ' min'; };
  const short = function (t) { return t.replace(' - Montigny-le-Bretonneux', '').replace(' Arrondissement', ''); };
  PTS.table($('#tm-od'), [
    { key: 'from', label: 'From' }, { key: 'to', label: 'To' },
    { key: 'commuters', label: 'People a day', num: true, fmt: n0 },
    { key: 'today', label: 'Today', num: true, fmt: mins }, { key: 'plan', label: 'With the project', num: true, fmt: mins },
    { key: 'saved', label: 'Saved', num: true, fmt: mins }
  ], D.od.map(function (o) { return { from: short(o.from), to: short(o.to), commuters: o.commuters, today: o.today, plan: o.plan, saved: o.today - o.plan }; }));
  PTS.table($('#tm-pairs'), [
    { key: 'from', label: 'From' }, { key: 'to', label: 'To' },
    { key: 'today', label: 'Today', num: true, fmt: mins }, { key: 'plan', label: 'With the project', num: true, fmt: mins },
    { key: 'saved', label: 'Saved', num: true, fmt: mins }, { key: 'share', label: 'Share of the trip', num: true, fmt: function (v) { return F.pct(v); } }
  ], D.pairs.map(function (p) { return Object.assign({}, p, { from: short(p.from) }); }));
  const lineName = function (l) { return l === 'metro' ? 'Metro, all lines' : (l.length === 1 && 'ABCDE'.indexOf(l) >= 0 ? 'RER ' : 'Line ') + l; };
  PTS.table($('#tm-lines'), [
    { key: 'name', label: 'Line' },
    { key: 'weight', label: 'Passengers a working day', num: true, fmt: n0 },
    { key: 'today', label: 'Average to the other stations today', num: true, fmt: function (v) { return n1(v) + ' min'; } },
    { key: 'gain', label: 'Saved on average', num: true, fmt: function (v) { return F.n(v, 1) + ' min'; } },
    { key: 'share_1', label: 'Passengers at stations that save 1 minute or more', num: true, fmt: function (v) { return F.pct(v); } },
    { key: 'bestTxt', label: 'Station that gains most' }
  ], D.lines.slice().sort(function (a, b) { return b.gain - a.gain; }).map(function (l) { return { name: lineName(l.line), weight: l.weight, today: l.today, gain: l.gain, share_1: l.share_1, bestTxt: l.best + ', ' + n1(l.best_gain) + ' min' }; }));
  PTS.table($('#tm-versions'), [
    { key: 'label', label: 'Version of the network' },
    { key: 'gain', label: 'Saved on average, station to station', num: true, fmt: function (v) { return F.n(v, 2) + ' min'; } },
    { key: 'entries_1', label: 'Passengers at stations that save 1 minute or more', num: true, fmt: n0 },
    { key: 'commuters_5', label: 'Commuters who save 5 minutes or more', num: true, fmt: n0 },
    { key: 'slower', label: 'Commuters slower by 1 minute or more', num: true, fmt: n0 },
    { key: 'hours_day', label: 'Hours saved a working day, journeys to work', num: true, fmt: n0 }
  ], D.versions.map(function (v) { return Object.assign({}, v, v.id === 'plan' ? { _class: 'tm-plan-row' } : {}); }));
});
