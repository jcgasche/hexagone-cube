PTS.section('flows', function (root) {
  'use strict';
  const D = PTS.data.flows, F = PTS.fmt, s = PTS.s, h = PTS.h;
  const $ = function (sel) { return root.querySelector(sel); };
  const host = $('#fl-map'), ctl = $('#fl-controls'), legend = $('#fl-legend');
  const N = D.nodes, LK = D.links, SER = D.series, GRP = SER.map(function (x) { return { id: x.id, name: x.name, kind: x.kind }; }).concat(D.groups);
  const n0 = function (v) { return F.n(v, 0); };
  const kn = function (v) { return v >= 1e6 ? F.n(v / 1e6, 2) + ' million' : F.n(Math.round(v / 1000) * 1000, 0); };

  // ---- what is shown
  const VIEW = { region: [-64, -52, 138, 118], paris: [-13.5, -9.6, 27, 18.6] };     // km east and south of Notre-Dame: x, y, width, height
  const RATIO = VIEW.region[3] / VIEW.region[2], W_MAX = 150, W_MIN = 2.5;           // the map keeps one shape; widest and closest views, km across
  const perPax = function (w) { return 4.4e-6 * Math.pow(w / 138, 0.82); };          // km of width for one passenger a day: lines grow a little on the screen as one zooms in
  const state = { when: 'today', by: 'line', colour: 'crowd' };
  let vb = VIEW.region.slice();
  const CROWD = [[0.4, 'var(--fl-c0)', 'under 40%'], [0.6, 'var(--fl-c1)', '40% to 60%'], [0.8, 'var(--fl-c2)', '60% to 80%'], [1.0, 'var(--fl-c3)', '80% to 100%'], [9, 'var(--fl-c4)', 'over 100%']];
  const QUAL = {
    fit: 'Counted: fitted to the boardings counted at the stations of the line',
    'fit+': 'Counted in part: fitted to the station counts and to the published total of the line',
    split: 'Estimate: the published total of the terminal, shared out by the trains of the timetable',
    published: 'Published total of the line at its Paris terminal, the same along the line',
    study: 'From the model of this study',
    none: 'No passenger figure is published for this line'
  };
  const colourOf = function (b) {
    if (state.by === 'line') return b.p == null ? 'var(--neutral-mark)' : 'var(--fl-' + lineKey(SER[b.s]) + ')';
    const v = state.colour === 'crowd' ? b.crowd : b.use;
    if (v == null) return 'var(--neutral-mark)';
    for (let i = 0; i < CROWD.length; i++) if (v < CROWD[i][0]) return CROWD[i][1];
    return CROWD[CROWD.length - 1][1];
  };
  function lineKey(x) { return x.kind === 'ter' ? 'ter' : x.kind === 'tgv' ? 'tgv' : x.id; }
  const bands = function () {
    if (state.by === 'line') return D[state.when].map(function (r) { return { l: r[0], s: r[1], p: r[2], q: r[3], h: r[4], d: r[5], ld: r[6], pl: r[7], cap: r[8], tun: r[9] }; });
    return D[state.when + '_tracks'].map(function (r) { return { l: r[0], s: r[1], p: r[2], q: r[3], h: r[4], crowd: r[5], use: r[6], cap: r[7], who: r[8], tun: r[9] }; });
  };
  const missing = function (b) { return state.by === 'line' ? b.p == null : (state.colour === 'crowd' ? b.crowd : b.use) == null; };

  // ---- controls
  PTS.seg(ctl, [['today', 'Today'], ['project', 'With the project']], state.when, function (v) { state.when = v; draw(); }, 'Situation');
  PTS.seg(ctl, [['line', 'By line'], ['track', 'By track and tunnel']], state.by, function (v) { state.by = v; draw(); }, 'Passengers shown');
  const colBox = h('div', { class: 'fl-col' }); ctl.appendChild(colBox);
  PTS.seg(colBox, [['crowd', 'Places on the trains used'], ['use', 'Train paths used']], state.colour, function (v) { state.colour = v; draw(); }, 'Colour');

  // ---- the map: one drawing, moved and zoomed by its view box, redrawn when the zoom settles so that widths and names fit the new scale
  const svg = s('svg', { role: 'img', class: 'fl-svg', 'aria-label': 'Map of the railway lines of the Paris region; the width of each line is in proportion to its passengers a day' });
  const gG = s('g', { class: 'fl-geo' }), gB = s('g', null), gL = s('g', { class: 'fl-lab' });
  svg.appendChild(gG); svg.appendChild(gB); svg.appendChild(gL);
  const tools = h('div', { class: 'fl-tools' });
  const btn = function (txt, label, fn) { const b = h('button', { type: 'button', class: 'fl-zb', 'aria-label': label, title: label, text: txt }); b.addEventListener('click', fn); tools.appendChild(b); return b; };
  btn('+', 'Zoom in', function () { zoomBy(0.6); });
  btn('−', 'Zoom out', function () { zoomBy(1 / 0.6); });
  btn('Paris', 'Show Paris', function () { goTo(VIEW.paris); });
  btn('Region', 'Show the whole region', function () { goTo(VIEW.region); });
  const hint = h('div', { class: 'fl-hint' }, h('span', { class: 'fl-hint-m', text: 'Drag to move. Click the map, then scroll to zoom.' }), h('span', { class: 'fl-hint-t', text: 'Two fingers to move and zoom.' }));
  host.appendChild(svg); host.appendChild(tools); host.appendChild(hint);
  let cur = [], engaged = false, timer = null;
  const setBox = function () { svg.setAttribute('viewBox', vb.join(' ')); };
  const clampBox = function () {
    vb[2] = Math.max(W_MIN, Math.min(W_MAX, vb[2])); vb[3] = vb[2] * RATIO;
    vb[0] = Math.max(-90 - vb[2] / 2, Math.min(90 - vb[2] / 2, vb[0])); vb[1] = Math.max(-80 - vb[3] / 2, Math.min(80 - vb[3] / 2, vb[1]));
  };
  const later = function () { clearTimeout(timer); timer = setTimeout(draw, 140); };
  function zoomAt(f, cx, cy) {                                     // f under 1 zooms in; (cx, cy) is the point of the map that stays in place
    const w = Math.max(W_MIN, Math.min(W_MAX, vb[2] * f)); f = w / vb[2];
    vb[0] = cx - (cx - vb[0]) * f; vb[1] = cy - (cy - vb[1]) * f; vb[2] = w; clampBox(); setBox(); later();
  }
  function zoomBy(f) { zoomAt(f, vb[0] + vb[2] / 2, vb[1] + vb[3] / 2); }
  function goTo(v) { const w = v[2], cx = v[0] + v[2] / 2, cy = v[1] + v[3] / 2; vb = [cx - w / 2, cy - w * RATIO / 2, w, w * RATIO]; clampBox(); setBox(); draw(); }
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
      if (ptrs.size === 2) {                                        // two fingers: move by half of each finger's move, zoom by the change of their spread
        ptrs.set(e.pointerId, [e.clientX, e.clientY]);
        const a = Array.from(ptrs.values()), d = Math.hypot(a[0][0] - a[1][0], a[0][1] - a[1][1]);
        vb[0] -= dx / 2 / r.width * vb[2]; vb[1] -= dy / 2 / r.height * vb[3];
        if (pinch > 0 && d > 0) { const mx = (a[0][0] + a[1][0]) / 2, my = (a[0][1] + a[1][1]) / 2; zoomAt(pinch / d, vb[0] + (mx - r.left) / r.width * vb[2], vb[1] + (my - r.top) / r.height * vb[3]); pinch = d; }
        else { clampBox(); setBox(); later(); }
        moved = true; PTS.tip.hide(); return;
      }
      if (moved || Math.abs(dx) + Math.abs(dy) > 3) {
        moved = true; ptrs.set(e.pointerId, [e.clientX, e.clientY]);
        vb[0] -= dx / r.width * vb[2]; vb[1] -= dy / r.height * vb[3]; clampBox(); setBox(); later(); svg.classList.add('fl-drag'); PTS.tip.hide(); return;
      }
    }
    const t = e.target.closest ? e.target.closest('[data-i]') : null;
    if (t) PTS.tip.show(tipOf(cur[+t.getAttribute('data-i')]), e); else PTS.tip.hide();
  });
  const up = function (e) { ptrs.delete(e.pointerId); pinch = 0; svg.classList.remove('fl-drag'); if (!moved) { engaged = true; host.classList.add('fl-on'); } };
  svg.addEventListener('pointerup', up); svg.addEventListener('pointercancel', up);
  svg.addEventListener('pointerleave', function () { PTS.tip.hide(); });
  const release = function () { engaged = false; host.classList.remove('fl-on'); };
  host.addEventListener('pointerleave', function (e) { if (e.pointerType !== 'touch') release(); });
  document.addEventListener('pointerdown', function (e) { if (engaged && !host.contains(e.target)) release(); });
  svg.addEventListener('touchmove', function (e) { if (e.touches.length === 2 && e.cancelable) e.preventDefault(); }, { passive: false });     // two fingers belong to the map, one finger to the page
  svg.addEventListener('dblclick', function (e) { const p = toMap(e); zoomAt(0.5, p[0], p[1]); });
  svg.addEventListener('wheel', function (e) {
    if (!engaged && !e.ctrlKey && !e.metaKey) return;               // the page scrolls as usual until the map has been clicked
    e.preventDefault(); const p = toMap(e); zoomAt(Math.exp(Math.max(-60, Math.min(60, e.deltaY)) * 0.004), p[0], p[1]);
  }, { passive: false });

  function tipOf(b) {
    const a = N[LK[b.l][0]][2], c = N[LK[b.l][1]][2], g = state.by === 'line' ? SER[b.s] : GRP[b.s];
    let t = '<b>' + g.name + '</b>';
    if (b.tun) t += '<br><span>' + b.tun + '</span>';
    else if (a && c) t += '<br><span>From ' + a + ' to ' + c + '</span>';
    if (state.by === 'track' && b.who) t += '<br><small>' + b.who.map(function (i) { return '<span>' + SER[i].name + '</span>'; }).join(', ') + '</small>';
    t += '<br><span>Passengers a day, both ways:</span> ' + (b.p == null ? '<b>no figure</b>' : '<b>' + kn(b.p) + '</b>');
    if (b.h) t += '<br><span>Trains in the busiest hour, one way:</span> <b>' + n0(b.h) + '</b>' + (b.cap ? ' <span>of ' + n0(b.cap) + ' train paths</span>' : '');
    if (state.by === 'line') {
      if (b.d) t += '<br><span>Trains a day, both ways:</span> <b>' + n0(b.d) + '</b>';
      if (b.ld != null && b.pl) t += '<br><span>Busiest hour, busier way:</span> <b>' + kn(b.ld) + '</b> <span>passengers for ' + kn(b.pl) + ' places</span> (' + F.pct(b.ld / b.pl) + ')';
      else if (b.ld != null) t += '<br><span>Busiest hour, busier way:</span> <b>' + kn(b.ld) + '</b> <span>passengers; the size of the trains is not published</span>';
      t += '<br><small>' + QUAL[b.q] + '</small>';
    } else {
      t += '<br><span>Places on the trains used in the busiest hour:</span> ' + (b.crowd == null ? '<b>no figure</b>' : '<b>' + F.pct(b.crowd) + '</b>');
      t += '<br><span>Train paths used:</span> ' + (b.use == null ? '<b>no capacity published for this section</b>' : '<b>' + F.pct(b.use) + '</b>');
    }
    return t;
  }
  const RIVER_AT = { Seine: [[-33, 5.5], [9.5, -8.5], [38, -47]], Marne: [[14, -1.2], [42, 7.5]], Oise: [[-17, 22.5], [2, 40]] };     // where each river is named, km from Notre-Dame
  const PARK_AT = [[-6.8, 1.3, 'Bois de Boulogne'], [6.3, -2.6, 'Bois de Vincennes']];
  function drawGeo() {
    PTS.clear(gG);
    const sw = vb[2] / 900;
    (D.geo.parks || []).forEach(function (r) { gG.appendChild(s('polygon', { points: r.map(function (p) { return p[0] + ',' + (-p[1]); }).join(' '), class: 'fl-park' })); });
    (D.geo.rivers || []).forEach(function (r) { gG.appendChild(s('polyline', { points: r[1].map(function (p) { return p[0] + ',' + (-p[1]); }).join(' '), class: 'fl-river', 'stroke-width': sw * (r[0] === 'Seine' ? 2.4 : 1.7) })); });
    (D.geo.dep || []).forEach(function (d) { gG.appendChild(s('polygon', { points: d[1].map(function (p) { return p[0] + ',' + (-p[1]); }).join(' '), class: d[0] === '75' ? 'fl-paris' : 'fl-dep', 'stroke-width': sw * (d[0] === '75' ? 1.6 : 1) })); });
    if (vb[2] < 45) PARK_AT.forEach(function (p) { if (D.geo.parks && D.geo.parks.length) gG.appendChild(s('text', { x: p[0], y: -p[1], class: 'fl-rname fl-pname', 'font-size': vb[2] / 80, text: p[2] })); });
    if ((D.geo.rivers || []).length) Object.keys(RIVER_AT).forEach(function (name) {
      RIVER_AT[name].forEach(function (p) { if (p[0] > vb[0] && p[0] < vb[0] + vb[2] && -p[1] > vb[1] && -p[1] < vb[1] + vb[3]) gG.appendChild(s('text', { x: p[0], y: -p[1], class: 'fl-rname', 'font-size': vb[2] / 75, text: name })); });
    });
  }
  function draw() {
    colBox.style.display = state.by === 'track' ? '' : 'none';
    setBox();
    const k = perPax(vb[2]), minW = vb[2] * 0.0014;
    cur = bands();
    const byLink = {};
    cur.forEach(function (b, i) { b.i = i; b.w = b.p == null ? minW : Math.max(minW, b.p * k); (byLink[b.l] = byLink[b.l] || []).push(b); });
    drawGeo(); PTS.clear(gB); PTS.clear(gL);
    const pad = vb[2] * 0.6;                                        // drawn a little beyond the frame, so that a drag shows lines at once
    const near = function (x, y) { return x > vb[0] - pad && x < vb[0] + vb[2] + pad && y > vb[1] - pad && y < vb[1] + vb[3] + pad; };
    const inView = function (x, y) { return x > vb[0] && x < vb[0] + vb[2] && y > vb[1] && y < vb[1] + vb[3]; };
    Object.keys(byLink).forEach(function (l) {
      const A = N[LK[l][0]], B = N[LK[l][1]];
      let x1 = A[0], y1 = -A[1], x2 = B[0], y2 = -B[1];
      if (!near(x1, y1) && !near(x2, y2)) return;
      if (x1 * x1 + y1 * y1 > x2 * x2 + y2 * y2) { const t = [x1, y1]; x1 = x2; y1 = y2; x2 = t[0]; y2 = t[1]; }       // drawn outwards from the centre, so that side-by-side lines keep their side
      const len = Math.hypot(x2 - x1, y2 - y1) || 1, nx = -(y2 - y1) / len, ny = (x2 - x1) / len;
      const list = byLink[l].sort(function (a, b) { return a.s - b.s; }), total = list.reduce(function (t, b) { return t + b.w; }, 0);
      let off = -total / 2;
      list.forEach(function (b) {
        const o = off + b.w / 2; off += b.w;
        const el = s('line', { x1: x1 + nx * o, y1: y1 + ny * o, x2: x2 + nx * o, y2: y2 + ny * o, stroke: colourOf(b), 'stroke-width': b.w, 'stroke-linecap': 'round', 'data-i': b.i, class: missing(b) ? 'fl-miss' : null });
        if (missing(b)) el.setAttribute('stroke-dasharray', (minW * 2.2) + ' ' + (minW * 2.6));
        gB.appendChild(el);
      });
    });
    const px = (host.clientWidth || 800) / vb[2];
    const fs = Math.max(10, Math.min(13.5, (host.clientWidth || 800) / 62)) / px, placed = [], dots = vb[2] < 60, most = (host.clientWidth || 800) * (host.clientWidth || 800) * RATIO / 15000;     // about one name for a patch of 120 px by 120 px     // names at 10 to 13.5 px whatever the zoom
    D.label.forEach(function (i, rank) {                           // listed by priority: the first to come keeps its place
      const n = N[i], x = n[0], y = -n[1];
      if (!inView(x, y)) return;
      if (vb[2] > 100 && Math.hypot(x, y) < 17 && rank > 3) return;                               // the centre is too dense to name at the scale of the region
      const txt = n[2].replace(' (Terminal 2) - TGV', '').replace(' - Montigny-le-Bretonneux', '');
      const w = txt.length * fs * 0.6 + fs * 0.5, hgt = fs * 1.25, gap = fs * 0.45;
      const spots = [[x + gap, y - fs * 0.35, 'start'], [x - gap, y - fs * 0.35, 'end'], [x + gap, y + fs * 1.05, 'start'], [x - gap, y + fs * 1.05, 'end']];   // right, left, then under
      if (x < 0 && vb[2] < 60) spots.splice(0, 4, spots[1], spots[0], spots[3], spots[2]);        // west of the centre: the name goes to the left first
      const box = function (p) { return [p[2] === 'start' ? p[0] : p[0] - w, p[1] - fs * 0.95]; };
      const free = spots.filter(function (p) { const b = box(p); return b[0] > vb[0] && b[0] + w < vb[0] + vb[2] && !placed.some(function (q) { return b[0] < q[0] + q[2] && b[0] + w > q[0] && b[1] < q[1] + hgt && b[1] + hgt > q[1]; }); })[0];
      if (!free || placed.length >= most) { if (dots) gL.appendChild(s('circle', { cx: x, cy: y, r: fs * 0.13, 'stroke-width': fs * 0.07, class: 'fl-dot' })); return; }      // no room for the name: a small dot marks the station when the view is close
      placed.push([box(free)[0], box(free)[1], w]);
      gL.appendChild(s('circle', { cx: x, cy: y, r: fs * 0.22, 'stroke-width': fs * 0.1 }));
      gL.appendChild(s('text', { x: free[0], y: free[1], 'font-size': fs, 'text-anchor': free[2], 'stroke-width': fs * 0.28, text: txt }));
    });
    drawLegend(k, vb);
  }
  function drawLegend(k, vb) {
    PTS.clear(legend);
    const px = (host.clientWidth || 800) / vb[2];
    const scale = h('div', { class: 'fl-leg-row' }, h('span', { class: 'fl-leg-t', text: 'Width: passengers a day, both ways' }));
    [100000, 300000, 600000].forEach(function (v) {
      scale.appendChild(h('span', { class: 'fl-leg-i' }, h('i', { class: 'fl-bar', style: { height: Math.max(1, v * k * px) + 'px' } }), kn(v)));
    });
    legend.appendChild(scale);
    const row = h('div', { class: 'fl-leg-row' });
    if (state.by === 'line') {
      const seen = {};
      cur.forEach(function (b) { if (b.p != null) seen[lineKey(SER[b.s])] = SER[b.s]; });
      Object.keys(seen).forEach(function (key) {
        const x = seen[key];
        row.appendChild(h('span', { class: 'fl-leg-i' }, h('i', { class: 'fl-chip', style: { background: 'var(--fl-' + key + ')' } }), x.kind === 'ter' ? 'TER' : x.kind === 'tgv' ? 'TGV' : x.name));
      });
      row.appendChild(h('span', { class: 'fl-leg-i' }, h('i', { class: 'fl-chip fl-chip-miss' }), 'No passenger figure published'));
    } else {
      row.appendChild(h('span', { class: 'fl-leg-t', text: state.colour === 'crowd' ? 'Colour: places on the trains used in the busiest hour, busier way' : 'Colour: trains in the busiest hour against the train paths of the section' }));
      CROWD.forEach(function (c) { row.appendChild(h('span', { class: 'fl-leg-i' }, h('i', { class: 'fl-chip', style: { background: c[1] } }), c[2])); });
      row.appendChild(h('span', { class: 'fl-leg-i' }, h('i', { class: 'fl-chip fl-chip-miss' }), state.colour === 'crowd' ? 'Size of the trains not published' : 'No capacity published'));
    }
    legend.appendChild(row);
  }
  PTS.onResize(host, draw);

  // ---- the lines, one by one
  const srcName = { sncf: 'SNCF count', idfm: 'IDFM validations' };
  PTS.table($('#fl-lines'), [
    { key: 'name', label: 'Line' },
    { key: 'counted', label: 'Boardings counted a working day', num: true, fmt: function (v) { return n0(v); } },
    { key: 'how', label: 'Stations counted, year' },
    { key: 'fit', label: 'Passengers a day on the map', num: true, fmt: function (v) { return n0(Math.round(v / 1000) * 1000); } },
    { key: 'pub', label: 'Published for the line' },
    { key: 'busiest', label: 'Busiest section' },
    { key: 'max_p', label: 'Passengers a day there', num: true, fmt: function (v) { return v ? n0(Math.round(v / 1000) * 1000) : ''; } },
    { key: 'max_h', label: 'Trains in its busiest hour, one way', num: true },
    { key: 'full', label: 'Places used in that hour', num: true }
  ], D.lines.map(function (l) {
    return { name: l.name, counted: l.counted, how: l.stations + ' of ' + l.of + ' stations, ' + l.years.join(' and ') + ' (' + l.by.map(function (b) { return srcName[b]; }).join(', ') + ')', fit: l.fit,
      pub: l.published ? n0(l.published) + (l.pub_year ? ' (' + l.pub_year + ')' : '') : 'none found', busiest: l.max_at ? 'From ' + l.max_at[0] + ' to ' + l.max_at[1] : '', max_p: l.max_p, max_h: l.max_h,
      full: l.places && l.max_ld && l.max_h ? F.pct(l.max_ld / (l.places * l.max_h)) : 'train size not published' };
  }));
});
