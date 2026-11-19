PTS.section('headway', function (root) {
  'use strict';
  const D = PTS.data.headway, F = PTS.fmt, h = PTS.h;
  const $ = function (sel) { return root.querySelector(sel); };
  const state = { hour: 'full', sig: 'auto', perf: 'central' };
  const APPROACH = { north: 'North approach', east: 'East approach', southeast: 'South-east approach', atlantic: 'Atlantic approach' };
  const STATION = { NE: 'Nord-Est', MP: 'Montparnasse', LY: 'Gare de Lyon' };
  const PAIR = { tgv_tgv: 'TGV behind a TGV', ter_tgv: 'TGV behind a TER', tgv_ter: 'TER behind a TGV', ter_ter: 'TER behind a TER' };
  const order = ['north', 'east', 'southeast', 'atlantic'];

  function name(r) {
    if (r.use === 'tun') { const w = r.way.split(' '); return STATION[w[0]] + ' to ' + STATION[w[1]]; }
    return APPROACH[r.tube] + (r.use === 'in' ? ', arriving' : ', leaving');
  }
  function line(r) {
    const w = r.worst, cls = (r.short ? 'hw-bad ' : '') + (r.taken > D.params.uic_peak ? 'hw-over' : '');
    return h('tr', { class: cls || null },
      h('th', { text: name(r) }),
      h('td', { class: 'num', text: F.n(r.trains) + ' (' + F.n(r.tgv) + ' + ' + F.n(r.ter) + ')' }),
      h('td', { class: 'hw-pair', text: PAIR[w.first + '_' + w.second] }),
      h('td', { class: 'num', text: F.n(w.gap) }),
      h('td', { class: 'num', text: F.n(w.need) }),
      h('td', { class: 'num hw-spare', text: F.n(w.spare) }),
      h('td', { class: 'num', text: F.n(r.short) }),
      h('td', { class: 'num hw-taken' },
        h('span', { class: 'hw-bar', 'aria-hidden': 'true' }, h('i', { style: { width: Math.min(100, r.taken * 100) + '%' } }), h('b', { style: { left: D.params.uic_peak * 100 + '%' } })),
        F.pct(r.taken)));
  }
  function draw() {
    const c = D.cases[state.perf + '_' + state.sig].hours[state.hour], rows = c.rows, host = $('#hw-table');
    const group = function (label, list) { return [h('tr', { class: 'hw-group' }, h('th', { colspan: 8, text: label }))].concat(list.map(line)); };
    const inn = rows.filter(function (r) { return r.use === 'in'; }).sort(function (a, b) { return order.indexOf(a.tube) - order.indexOf(b.tube); });
    const out = rows.filter(function (r) { return r.use === 'out'; }).sort(function (a, b) { return order.indexOf(a.tube) - order.indexOf(b.tube); });
    const tri = rows.filter(function (r) { return r.use === 'tun'; });
    PTS.clear(host);
    host.appendChild(h('div', { class: 'tbl-wrap' }, h('table', { class: 'tbl hw-rows' },
      h('thead', null, h('tr', null,
        h('th', { text: 'Track' }),
        h('th', { class: 'num', text: 'Trains an hour (TGVs + TER)' }),
        h('th', { text: 'Closest pair' }),
        h('th', { class: 'num', text: 'Time the timetable gives it (s)' }),
        h('th', { class: 'num', text: 'Least time it needs (s)' }),
        h('th', { class: 'num', text: 'In hand (s)' }),
        h('th', { class: 'num', text: 'Pairs too close' }),
        h('th', { class: 'num', text: 'Share of the hour taken' }))),
      h('tbody', null, group('Approach tunnels, towards the station', inn), group('The triangle', tri), group('Approach tunnels, away from the station', out)))));
    const s = c.sum, sum = $('#hw-sum');
    PTS.clear(sum);
    sum.appendChild(h('span', { text: F.n(s.short) + ' of ' + F.n(s.pairs) + ' pairs of trains closer than they need.' }));
    sum.appendChild(document.createTextNode(' '));
    sum.appendChild(h('span', { text: 'The mark on each bar is the limit planners keep in the busiest hour.' }));
  }
  const ctl = $('#hw-ctl');
  PTS.seg(ctl, [['today', 'About today'], ['full', 'Southern lines full'], ['max', 'Nord-Est filled too']], state.hour, function (v) { state.hour = v; draw(); }, 'Hour shown');
  PTS.seg(ctl, [['auto', 'Short blocks, automatic driving'], ['short', 'Short blocks, a driver'], ['long', 'Blocks of 400 m, a driver']], state.sig, function (v) { state.sig = v; draw(); }, 'Signalling');
  PTS.seg(ctl, [['central', 'Central trains'], ['cautious', 'Cautious trains']], state.perf, function (v) { state.perf = v; draw(); }, 'Trains');
  draw();

  // ---------------------------------------------------------------- the simulator: two kinds of train, the blocks, every setting
  /* The same calculation as model/headway.py (profile, needs, at, blocks, least), written again here so that every setting can be moved.
     With the values of the study it gives the figures of the tables below (checked by tools/check_headway_sim.js). */
  (function () {
    const host = $('#hw-sim'); if (!host) return;
    const s = PTS.s, K = D.params, G = 9.81, DX = 1, RUN = K.run_min * 60;
    const KIND = { tgv: 'TGV', ter: 'TER' }, COL = { tgv: 'var(--accent)', ter: 'var(--alt)' };

    function defaults(scene) {
      const tun = scene === 'tun';
      return { scene: scene, k1: 'ter', k2: 'tgv', gap: K.plan.path, tracks: 1,
        km: tun ? K.tubes_km.nemont : K.tubes_km.north, depth: K.depth, vline: tun ? K.v_line_kmh : K.v_approach,
        vthroat: K.v_throat, throat: K.throat['v' + K.v_throat], len_tgv: K.len.tgv, len_ter: K.len.ter,
        acc_tgv: K.perf.central.tgv.acc, brk_tgv: K.perf.central.tgv.brk, acc_ter: K.perf.central.ter.acc, brk_ter: K.perf.central.ter.brk,
        block: K.signal.auto.block, tblock: K.signal.auto.throat, react: K.signal.auto.react, tsys: K.t_sys, tpoints: K.t_points, overlap: K.overlap };
    }

    // --- the run of one train, metre by metre
    function profile(dist, acc, brk, v0, v1, caps, slope) {
      const n = Math.round(dist / DX), cap = new Float64Array(n + 1).fill(1e9), A = new Float64Array(n + 1).fill(acc), B = new Float64Array(n + 1).fill(brk);
      caps.forEach(function (c) { for (let i = Math.max(0, Math.floor(c[0] / DX)); i <= Math.min(n, Math.ceil(c[1] / DX)); i++) cap[i] = Math.min(cap[i], c[2]); });
      (slope || []).forEach(function (c) { for (let i = Math.max(0, Math.floor(c[0] / DX)); i <= Math.min(n, Math.ceil(c[1] / DX)); i++) { A[i] = Math.max(0.05, acc - G * c[2]); B[i] = Math.max(0.05, brk + G * c[2]); } });
      const v = new Float64Array(n + 1), t = new Float64Array(n + 1);
      v[0] = Math.min(v0, cap[0]);
      for (let i = 0; i < n; i++) v[i + 1] = Math.min(cap[i + 1], Math.sqrt(v[i] * v[i] + 2 * A[i] * DX));
      v[n] = Math.min(v[n], v1);
      for (let i = n - 1; i >= 0; i--) v[i] = Math.min(v[i], Math.sqrt(v[i + 1] * v[i + 1] + 2 * B[i] * DX));
      for (let i = 0; i < n; i++) t[i + 1] = t[i] + 2 * DX / (v[i] + v[i + 1]);
      return { v: v, t: t, n: n, brk: B, T: t[n] };
    }
    function at(p, x) {                                   // time at which the head is x metres along
      if (x <= 0) return p.t[0];
      const i = x / DX; if (i >= p.n) return p.T + (x - p.n * DX) / Math.max(p.v[p.n], 0.1);
      const k = Math.floor(i); return p.t[k] + (i - k) * (p.t[k + 1] - p.t[k]);
    }
    function needs(p, x) {                                // time at which the head reaches the last point from which it can still stop before x
      for (let i = 0; i <= p.n; i++) if (i * DX + p.v[i] * p.v[i] / (2 * p.brk[i]) >= x) return p.t[i];
      return p.T;
    }
    function where(p, tau) {                              // metres along at time tau (before the start: on its way in, or waiting; after the end: running on, or at rest)
      if (tau <= 0) return p.v[0] * tau;
      if (tau >= p.T) return p.n * DX + p.v[p.n] * (tau - p.T);
      let a = 0, b = p.n; while (b - a > 1) { const m = (a + b) >> 1; if (p.t[m] <= tau) a = m; else b = m; }
      return (a + (tau - p.t[a]) / Math.max(1e-9, p.t[b] - p.t[a])) * DX;
    }
    function cut(a, b, size) { const n = Math.max(1, Math.ceil((b - a) / size - 1e-9)), out = []; for (let i = 0; i < n; i++) out.push([a + (b - a) * i / n, a + (b - a) * (i + 1) / n]); return out; }

    // --- one set of values: the two runs, the blocks, the time each train keeps each block, the least time for each pair
    function compute(P) {
      const L = { tgv: P.len_tgv, ter: P.len_ter }, perf = { tgv: [P.acc_tgv, P.brk_tgv], ter: [P.acc_ter, P.brk_ter] };
      const Dm = P.km * 1000, th = P.throat, vt = P.vthroat / 3.6, vl = P.vline / 3.6, plat = L.tgv + K.stop_clear;
      const r = Dm - plat - th, g = P.scene === 'tun' ? 0 : P.depth / r, start = P.scene !== 'in', end = P.scene !== 'out';
      const run = function (kind) {
        const acc = perf[kind][0], brk = perf[kind][1];
        if (P.scene === 'in') return profile(Dm, acc, brk, vl, 0, [[r, Dm, vt], [0, Dm, vl]], [[0, r, -g]]);
        if (P.scene === 'out') return profile(Dm, acc, brk, 0, vl, [[0, th + L[kind], vt], [0, Dm, vl]], [[Dm - r, Dm, g]]);
        const caps = function (top) { return [[0, th + L[kind], vt], [Dm - plat - th, Dm, vt], [0, Dm, top]]; };
        const fast = profile(Dm, acc, brk, 0, 0, caps(vl));
        if (fast.T >= RUN) { fast.fastest = fast.T; fast.cruise = vl; return fast; }
        let lo = 20 / 3.6, hi = vl;
        for (let k = 0; k < 40; k++) { const mid = (lo + hi) / 2; if (profile(Dm, acc, brk, 0, 0, caps(mid)).T > RUN) lo = mid; else hi = mid; }
        const p = profile(Dm, acc, brk, 0, 0, caps(hi)); p.cruise = hi; p.fastest = fast.T; return p;
      };
      const prof = { tgv: run('tgv'), ter: run('ter') };
      const whole = P.tblock >= th, bl = []; let a = 0, b = Dm, xd = Dm;
      if (start) { bl.push([whole ? 0 : th - P.tblock, th, P.overlap, P.tpoints, 'start']); a = th; }
      if (end) { xd = Dm - plat; b = xd - th; }
      cut(a, b, P.block).forEach(function (c) { bl.push([c[0], c[1], P.overlap, 0, 'tunnel']); });
      if (end) {
        const tb = whole ? [[b, xd]] : cut(b, xd, P.tblock);
        tb.forEach(function (c, i) { bl.push(i < tb.length - 1 ? [c[0], c[1], P.overlap, 0, 'end'] : [c[0], c[1], 0, P.tpoints, 'end']); });
      }
      const ref = P.scene === 'in' ? 'stop' : 'start', off = {}, hold = {};
      ['tgv', 'ter'].forEach(function (k) {
        const p = prof[k]; off[k] = ref === 'stop' ? p.T : 0;
        hold[k] = bl.map(function (c) { return { from: needs(p, c[0]) - off[k] - P.react, to: at(p, c[1] + c[2] + L[k]) - off[k] + P.tsys + c[3] }; });
      });
      const need = {};
      ['tgv', 'ter'].forEach(function (x) { ['tgv', 'ter'].forEach(function (y) {
        let best = -1e9, bi = 0; bl.forEach(function (c, i) { const d = hold[x][i].to - hold[y][i].from; if (d > best) { best = d; bi = i; } });
        need[x + '_' + y] = { s: best, i: bi, place: bl[bi][4] };
      }); });
      return { P: P, L: L, perf: perf, D: Dm, th: th, plat: plat, r: r, g: g, start: start, end: end, xd: xd, prof: prof, blocks: bl, off: off, hold: hold, need: need };
    }
    PTS.headwaySim = { defaults: defaults, compute: compute };

    // --- what the stream of trains gives: train j at j x gap, kinds in turn, tracks in turn
    const kindOf = function (P, j) { return ((j % 2) + 2) % 2 ? P.k2 : P.k1; };
    function pairs(c) {
      const P = c.P, seen = {}, out = [];
      for (let j = 0; j < 2 * P.tracks; j++) { const a = kindOf(P, j), b = kindOf(P, j + P.tracks), k = a + '_' + b; if (!seen[k]) { seen[k] = 1; out.push({ key: k, first: a, second: b, need: c.need[k].s, place: c.need[k].place, i: c.need[k].i }); } }
      return out;
    }

    // --- state and controls
    let P = defaults('in'), C = null, T = 0, playing = !(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches), speed = 15, last = 0, width = 0, frame = null;
    const sliders = {}, top = h('div', { class: 'controls' }), view = h('div', { class: 'hw-sim-view' }), play = h('div', { class: 'controls hw-sim-play' }), grid = h('div', { class: 'hw-sim-grid' }), res = h('div', { class: 'hw-sim-res' });
    const legend = h('ul', { class: 'legend hw-sim-legend' },
      h('li', null, h('i', { style: { '--c': COL.tgv } }), 'TGV'), h('li', null, h('i', { style: { '--c': COL.ter } }), 'TER'),
      h('li', null, h('i', { class: 'hw-lg-res' }), 'Block kept free ahead of a train'), h('li', null, h('i', { class: 'hw-lg-occ' }), 'Block taken by a train, or not yet given back'),
      h('li', null, h('i', { style: { '--c': 'var(--bad)' } }), 'Two trains need the same block: the second must brake'),
      h('li', null, h('i', { class: 'hw-lg-brk' }), 'Distance the train needs to stop'));
    host.appendChild(top); host.appendChild(view); host.appendChild(play); host.appendChild(legend); host.appendChild(grid); host.appendChild(h('h4', { text: 'What these settings give' })); host.appendChild(res);

    const unit = function (u, d) { return function (v) { return F.n(v, d || 0) + ' ' + u; }; };
    const SL = [
      ['Trains', [
        ['gap', 'Time between two trains, one after the other', 30, 300, 5, unit('s')],
        ['brk_tgv', 'Braking of a TGV, on the level', 0.2, 1.2, 0.05, unit('m/s²', 2)],
        ['acc_tgv', 'Acceleration of a TGV', 0.2, 1.2, 0.05, unit('m/s²', 2)],
        ['len_tgv', 'Length of a TGV', 200, 400, 50, unit('m')],
        ['brk_ter', 'Braking of a TER, on the level', 0.2, 1.2, 0.05, unit('m/s²', 2)],
        ['acc_ter', 'Acceleration of a TER', 0.2, 1.2, 0.05, unit('m/s²', 2)],
        ['len_ter', 'Length of a TER', 110, 330, 110, unit('m')]]],
      ['Tunnel and station', [
        ['vline', 'Speed in the tunnel', 40, 160, 5, unit('km/h')],
        ['vthroat', 'Speed over the points', 30, 100, 5, unit('km/h')],
        ['km', 'Length of the tunnel', 1.5, 8, 0.1, unit('km', 1)],
        ['depth', 'Depth of the platforms below the tunnel mouth', 0, 70, 1, function (v) { return F.n(v) + ' m'; }],
        ['throat', 'Length of the fan of points', 100, 600, 25, unit('m')]]],
      ['Signalling', [
        ['block', 'Length of a block in the tunnel', 50, 1000, 50, unit('m')],
        ['tblock', 'Length of a block in the fan of points', 50, 600, 25, unit('m')],
        ['react', 'Time to react before the braking point', 0, 15, 1, unit('s')],
        ['tsys', 'Time for the signalling to give a block back', 0, 30, 1, unit('s')],
        ['tpoints', 'Time to move the points', 0, 20, 1, unit('s')],
        ['overlap', 'Safety distance behind a train', 0, 200, 10, unit('m')]]]
    ];
    const change = function () { C = compute(P); layout(); results(); };
    SL.forEach(function (grp) {
      const box = h('div', { class: 'hw-sim-group' }, h('h4', { text: grp[0] }));
      grp[1].forEach(function (d) { sliders[d[0]] = PTS.slider(box, { label: d[1], min: d[2], max: d[3], step: d[4], value: P[d[0]], format: d[5] }, function (v) { P[d[0]] = v; change(); }); });
      grid.appendChild(box);
    });
    const setAll = function (vals) { Object.keys(vals).forEach(function (k) { P[k] = vals[k]; if (sliders[k]) sliders[k].set(vals[k], true); }); };
    const scene = PTS.seg(top, [['in', 'Arriving at a station'], ['tun', 'Between two stations'], ['out', 'Leaving a station']], P.scene, function (v) { const d = defaults(v); P.scene = v; setAll({ km: d.km, vline: d.vline, depth: d.depth }); T = 0; change(); }, 'Where');
    const first = PTS.seg(top, [['tgv', 'TGV'], ['ter', 'TER']], P.k1, function (v) { P.k1 = v; change(); }, 'First train');
    const second = PTS.seg(top, [['tgv', 'TGV'], ['ter', 'TER']], P.k2, function (v) { P.k2 = v; change(); }, 'Second train');
    const tracks = PTS.seg(top, [['1', '1'], ['2', '2']], String(P.tracks), function (v) { P.tracks = +v; change(); }, 'Tracks each way');
    const sig = PTS.seg(top, [['auto', 'Short blocks, automatic driving'], ['short', 'Short blocks, a driver'], ['long', 'Blocks of 400 m, a driver']], 'auto', function (v) { const S = K.signal[v]; setAll({ block: S.block, tblock: S.throat == null ? 600 : S.throat, react: S.react }); change(); }, 'Signalling');
    const trains = PTS.seg(top, [['central', 'Central trains'], ['cautious', 'Cautious trains']], 'central', function (v) { const q = K.perf[v]; setAll({ acc_tgv: q.tgv.acc, brk_tgv: q.tgv.brk, acc_ter: q.ter.acc, brk_ter: q.ter.brk }); change(); }, 'Trains');
    top.appendChild(h('button', { type: 'button', class: 'btn', text: 'Back to the values of the study', onclick: function () { const d = defaults(P.scene); setAll(d); first.set(d.k1, true); second.set(d.k2, true); tracks.set('1', true); sig.set('auto', true); trains.set('central', true); change(); } }));
    const btn = h('button', { type: 'button', class: 'btn', onclick: function () { playing = !playing; label(); } }), clock = h('span', { class: 'hw-sim-clock' });
    const label = function () { btn.textContent = PTS.tr(playing ? 'Pause' : 'Play'); };
    play.appendChild(btn); label();
    PTS.seg(play, [['5', '×5'], ['15', '×15'], ['40', '×40']], String(speed), function (v) { speed = +v; }, 'Speed of the film');
    play.appendChild(clock);

    // --- the drawing: the track with its blocks and trains, and under it the time each train keeps each block
    let geo = null;
    function layout() {
      const W = Math.max(300, width || view.clientWidth || 600), ml = 44, mr = 10, c = C, n = P.tracks;
      const x0 = c.start ? -(c.plat + 40) : -120, x1 = c.end ? c.D + 40 : c.D + 160;
      const X = function (x) { return ml + (x - x0) / (x1 - x0) * (W - ml - mr); };
      const rowH = 40, topH = 46, H1 = topH + rowH * n + 6;
      PTS.clear(view);
      const svg = s('svg', { class: 'hw-sim-svg', viewBox: '0 0 ' + W + ' ' + H1, width: W, height: H1, role: 'img', 'aria-label': PTS.tr('Trains and blocks on the track') });
      // zones and their names
      const zone = function (a, b, cls, name) { svg.appendChild(s('rect', { x: X(a), y: 16, width: Math.max(0, X(b) - X(a)), height: H1 - 16, class: cls })); if (name) svg.appendChild(s('text', { x: (X(a) + X(b)) / 2, y: 11, class: 'hw-sim-zl', 'text-anchor': 'middle', text: PTS.tr(name) })); };
      if (c.start) { zone(-c.plat, 0, 'hw-z-plat', 'Platforms'); zone(0, c.th, 'hw-z-pts', 'Points'); }
      if (c.end) { zone(c.xd - c.th, c.xd, 'hw-z-pts', 'Points'); zone(c.xd, c.D, 'hw-z-plat', 'Platforms'); }
      const ta = c.start ? c.th : 0, tb = c.end ? c.xd - c.th : c.D;
      svg.appendChild(s('text', { x: (X(ta) + X(tb)) / 2, y: 11, class: 'hw-sim-zl', 'text-anchor': 'middle', text: PTS.tr('Tunnel') }));
      // the slope
      const yg = 22, dy = 16;
      if (P.scene !== 'tun' && c.g > 0) {
        const pts = P.scene === 'in' ? [[0, 0], [c.r, 1], [c.D, 1]] : [[0, 1], [c.D - c.r, 1], [c.D, 0]];
        svg.appendChild(s('polyline', { class: 'hw-sim-slope', points: pts.map(function (q) { return X(q[0]) + ',' + (yg + q[1] * dy); }).join(' ') }));
        svg.appendChild(s('text', { x: X(P.scene === 'in' ? c.r / 2 : c.D - c.r / 2), y: yg + dy + 4, class: 'hw-sim-zl', 'text-anchor': 'middle', text: PTS.tr('Slope') + ' ' + F.n(c.g * 100, 1) + (PTS.lang === 'fr' ? ' %' : '%') }));
      }
      const rows = [];
      for (let q = 0; q < n; q++) {
        const y = topH + rowH * q + 12;
        svg.appendChild(s('line', { x1: X(x0), x2: X(x1), y1: y, y2: y, class: 'hw-sim-rail' }));
        const cells = c.blocks.map(function (b) { const e = s('rect', { x: X(b[0]) + 0.5, y: y + 8, width: Math.max(1, X(b[1]) - X(b[0]) - 1), height: 9, class: 'hw-sim-blk' }); svg.appendChild(e); return e; });
        rows.push({ y: y, cells: cells, layer: svg.appendChild(s('g', null)) });
      }
      view.appendChild(svg);
      // the diagram of blocking times, for the pair with the least in hand
      const pr = pairs(c).sort(function (a, b) { return b.need - a.need; })[0], given = P.gap * n, hl = c.hold[pr.first], hf = c.hold[pr.second];
      let t0 = 1e9, t1 = -1e9; hl.forEach(function (x) { t0 = Math.min(t0, x.from); }); hf.forEach(function (x) { t1 = Math.max(t1, x.to + given); });
      const H2 = 250, mt = 8, mb = 26, Y = function (t) { return mt + (t - t0) / (t1 - t0) * (H2 - mt - mb); };
      const dg = s('svg', { class: 'hw-sim-svg', viewBox: '0 0 ' + W + ' ' + H2, width: W, height: H2, role: 'img', 'aria-label': PTS.tr('Time each of the two trains keeps each block') });
      const step = (t1 - t0) > 400 ? 120 : 60;
      for (let t = Math.ceil(t0 / step) * step; t <= t1; t += step) { dg.appendChild(s('line', { x1: ml, x2: W - mr, y1: Y(t), y2: Y(t), class: 'hw-sim-grid-l' })); dg.appendChild(s('text', { x: ml - 6, y: Y(t) + 4, class: 'hw-sim-ax', 'text-anchor': 'end', text: F.n(t) })); }
      const kmStep = c.D > 4500 ? 1000 : 500;
      for (let x = 0; x <= c.D; x += kmStep) dg.appendChild(s('text', { x: X(x), y: H2 - 8, class: 'hw-sim-ax', 'text-anchor': 'middle', text: F.n(x) + ' m' }));
      dg.appendChild(s('text', { x: 4, y: 12, class: 'hw-sim-ax', text: 's' }));
      c.blocks.forEach(function (b, i) {
        const xa = X(b[0]) + 0.5, w = Math.max(1, X(b[1]) - X(b[0]) - 1);
        dg.appendChild(s('rect', { x: xa, y: Y(hl[i].from), width: w, height: Y(hl[i].to) - Y(hl[i].from), fill: COL[pr.first], class: 'hw-sim-box' }));
        dg.appendChild(s('rect', { x: xa, y: Y(hf[i].from + given), width: w, height: Y(hf[i].to + given) - Y(hf[i].from + given), fill: COL[pr.second], class: 'hw-sim-box' }));
        if (hl[i].to > hf[i].from + given) dg.appendChild(s('rect', { x: xa, y: Y(hf[i].from + given), width: w, height: Y(hl[i].to) - Y(hf[i].from + given), class: 'hw-sim-clash' }));
      });
      const path = function (kind, shift, back) {
        const p = c.prof[kind], pts = [], o = c.off[kind];
        for (let i = 0; i <= p.n; i += 20) pts.push(X(i * DX - back) + ',' + Y(p.t[i] - o + shift));
        pts.push(X(c.D - back) + ',' + Y(p.T - o + shift));
        return s('polyline', { points: pts.join(' '), class: 'hw-sim-path' + (back ? ' hw-sim-tail' : ''), stroke: COL[kind] });
      };
      dg.appendChild(path(pr.first, 0, 0)); dg.appendChild(path(pr.first, 0, c.L[pr.first])); dg.appendChild(path(pr.second, given, 0)); dg.appendChild(path(pr.second, given, c.L[pr.second]));
      const now = dg.appendChild(s('line', { x1: ml, x2: W - mr, y1: 0, y2: 0, class: 'hw-sim-now' }));
      view.appendChild(h('p', { class: 'note', text: PTS.tr('Below: the time each of the two trains keeps each block. The second train runs freely as long as the two sets of boxes do not overlap.') }));
      view.appendChild(dg);
      geo = { X: X, x0: x0, x1: x1, rows: rows, now: now, Y: Y, t0: t0, t1: t1, lead: (P.k1 === P.k2 || (pr.first === P.k1 && (n === 2 || pr.second === P.k2))) ? 0 : 1 };
      paint();
    }

    function paint() {
      if (!geo || !C) return;
      const c = C, n = P.tracks, gap = P.gap, period = 4 * gap, X = geo.X;
      const span = Math.ceil(900 / gap) + 2, j0 = Math.floor(T / gap);
      geo.rows.forEach(function (row, q) {
        PTS.clear(row.layer);
        const count = c.blocks.map(function () { return { n: 0, kind: null, in: false }; });
        for (let j = j0 - span; j <= j0 + span; j++) {
          if ((((j % n) + n) % n) !== q) continue;
          const kind = kindOf(P, j), p = c.prof[kind], rel = T - j * gap, tau = rel + c.off[kind], L = c.L[kind];
          let x = where(p, tau), alpha = 1;
          if (P.scene === 'in' && tau > p.T) alpha = 1 - (tau - p.T) / 45;                       // at the platform: it fades, the next one takes another platform track
          if (P.scene !== 'in' && tau < 0) { x = 0; alpha = 1 + tau / 45; }                       // waiting at the platform before it leaves
          if (P.scene === 'tun' && tau > p.T) alpha = 1 - (tau - p.T) / 45;
          c.hold[kind].forEach(function (hd, i) { if (rel >= hd.from && rel < hd.to) { count[i].n++; count[i].kind = kind; if (x >= c.blocks[i][0]) count[i].in = true; } });
          if (alpha <= 0 || x - L > geo.x1 || x < geo.x0) continue;
          const lane = (Math.floor((j - q) / n) % 2 + 2) % 2 ? 1 : -1;
          const yof = function (xx) { let f = 0; if (c.end && xx > c.xd - c.th) f = Math.min(1, (xx - (c.xd - c.th)) / c.th); if (c.start && xx < c.th) f = Math.min(1, (c.th - xx) / c.th); return row.y + lane * 6 * f; };
          const xa = Math.max(geo.x0, x - L), xb = Math.min(geo.x1, x);
          row.layer.appendChild(s('line', { x1: X(xa), y1: yof(xa), x2: X(xb), y2: yof(xb), class: 'hw-sim-train', stroke: COL[kind], opacity: Math.min(1, alpha) }));
          const i = Math.max(0, Math.min(p.n, Math.round(x / DX))), v = (tau > 0 && tau < p.T) ? p.v[i] : (tau >= p.T ? p.v[p.n] : p.v[0]);
          if (v > 0.5 && x >= 0 && x <= c.D) { const sd = v * v / (2 * p.brk[i]); row.layer.appendChild(s('line', { x1: X(x), x2: X(Math.min(geo.x1, x + sd)), y1: row.y - 9, y2: row.y - 9, class: 'hw-sim-brk', stroke: COL[kind] })); }
        }
        row.cells.forEach(function (e, i) {
          const k = count[i];
          e.setAttribute('class', 'hw-sim-blk' + (k.n > 1 ? ' hw-clash' : k.n === 1 ? (k.in ? ' hw-occ' : ' hw-res') : ''));
          if (k.n === 1) e.style.fill = COL[k.kind]; else e.style.fill = '';
        });
      });
      const rel = ((((T - geo.lead * gap - geo.t0) % period) + period) % period) + geo.t0, y = rel <= geo.t1 ? geo.Y(rel) : -10;
      geo.now.setAttribute('y1', y); geo.now.setAttribute('y2', y);
      clock.textContent = F.n(Math.floor(((T % 3600) + 3600) % 3600)) + ' s';
    }

    function results() {
      const c = C, n = P.tracks, given = P.gap * n, pr = pairs(c), rows = [];
      const worst = pr.slice().sort(function (a, b) { return (given - a.need) - (given - b.need); })[0], spare = given - worst.need;
      const PLACE = { start: 'Least time, set at the points on leaving', end: 'Least time, set at the points on arriving', tunnel: 'Least time, set in the tunnel' };
      const row = function (label, value, cls, extra) { rows.push(h('tr', { class: cls || null }, h('th', { text: label }), h('td', { class: 'num', text: value }), h('td', { class: 'hw-sim-why', text: extra || '' }))); };
      const sec = function (v) { return F.n(v) + ' s'; };
      pr.forEach(function (x) { row(PAIR[x.first + '_' + x.second], sec(x.need), null, PLACE[x.place]); });
      row('Time the settings give two trains on one track', sec(given));
      row('In hand on the closest pair', (spare >= 0 ? '+' : '−') + sec(Math.abs(spare)), spare < 0 ? 'hw-bad' : 'hw-ok', spare < 0 ? 'Too close: the second train must brake' : 'The second train runs freely');
      let per;                                                     // trains an hour one track takes with nothing in hand
      if (n === 1) per = 2 * 3600 / (c.need[P.k1 + '_' + P.k2].s + c.need[P.k2 + '_' + P.k1].s); else per = (3600 / c.need[P.k1 + '_' + P.k1].s + 3600 / c.need[P.k2 + '_' + P.k2].s) / 2;
      const taken = (3600 / given) / per;
      row('Trains an hour each way at this spacing', F.n(3600 / P.gap, 1));
      row('Share of the hour each track is taken', F.pct(taken), taken > K.uic_peak ? 'hw-bad' : null, 'Planners keep it under ' + F.pct(K.uic_peak) + ' in the busiest hour');
      row('Most trains an hour each way, nothing in hand', F.n(per * n, 1));
      row('Most trains an hour each way, with the reserve planners keep', F.n(per * n * K.uic_peak, 1));
      if (P.scene !== 'tun') {
        const k = P.k2, b = c.perf[k][1], eff = Math.max(0.05, P.scene === 'in' ? b - G * c.g : b + G * c.g), v = P.vline / 3.6;
        row('Slope of the approach', F.pct(c.g, 1), null, F.n(P.depth) + ' m over ' + F.n(c.r) + ' m');
        if (P.scene === 'in') { row('Braking left to the second train on the way down', F.n(eff, 2) + ' m/s²', null, KIND[k]); row('Distance it needs to stop from the speed of the tunnel', F.n(v * v / (2 * eff)) + ' m'); }
      } else {
        ['tgv', 'ter'].forEach(function (k) { if (k !== P.k1 && k !== P.k2) return; const p = c.prof[k]; row('Fastest run from start to stop', sec(p.fastest), p.fastest > RUN ? 'hw-bad' : null, KIND[k] + ', for ' + sec(RUN) + ' in the timetable'); });
      }
      PTS.clear(res);
      res.appendChild(h('div', { class: 'tbl-wrap' }, h('table', { class: 'tbl hw-sim-tbl no-stack' }, h('tbody', null, rows))));
      const d = defaults(P.scene), same = Object.keys(d).every(function (k) { return Math.abs((+P[k] || 0) - (+d[k] || 0)) < 1e-9 || P[k] === d[k]; });
      res.appendChild(h('p', { class: 'note', text: same ? 'These are the values the study retains; the tables below give their results for every tunnel.' : 'Some values differ from those the study retains. The tables below keep the values of the study.' }));
    }

    function tick(now) {
      frame = requestAnimationFrame(tick);
      const dt = Math.min(0.1, (now - last) / 1000 || 0); last = now;
      if (!playing || !host.offsetParent) return;
      T += dt * speed;
      paint();
    }
    PTS.onResize(view, function (w) { width = w; if (!C) C = compute(P); layout(); });
    if (!C) { C = compute(P); layout(); }
    results();
    frame = requestAnimationFrame(tick);
  })();
});
