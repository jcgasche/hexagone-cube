PTS.section('timetable', function (root) {
  'use strict';
  const T = PTS.data.timetable, P = PTS.data.project, G = PTS.data.paris_geo, F = PTS.fmt, h = PTS.h, s = PTS.s;
  const $ = function (sel) { return root.querySelector(sel); };
  const calm = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const pad = function (m) { m = ((Math.floor(m) % 60) + 60) % 60; return ':' + (m < 10 ? '0' : '') + m; };
  const padh = function (m) { return pad(m) + (Math.abs(m - Math.floor(m) - 0.5) < 0.01 ? '\u00bd' : ''); };     // half minutes, as in a working timetable
  const add = function (g, tag, attrs) { const e = s(tag, attrs); g.appendChild(e); return e; };
  const n0 = function (v) { return F.n(v, 0); };

  // ---------------------------------------------------------------- names and colours
  const ST = { NE: 'Paris Nord-Est', LY: 'Gare de Lyon', MP: 'Montparnasse' }, ORDER = ['MP', 'NE', 'LY'];
  const LINE = { A: 'the Atlantic', S: 'the south-east', N: 'the north', E: 'the east' };
  const SHORT = { A: 'Atlantic', S: 'South-east', N: 'North', E: 'East' };
  const PLACES = { A: 'Bordeaux, Nantes, Rennes', S: 'Lyon, Marseille', N: 'Lille, London, Brussels', E: 'Reims, Strasbourg' };
  // a colour for each pair of lines; the darker shade for trains towards the north or east, and from the Atlantic to the south-east
  const KIND = {
    AN: { c: 'var(--s1)', name: 'Atlantic and north' }, AE: { c: 'var(--s7)', name: 'Atlantic and east' },
    SN: { c: 'var(--s2)', name: 'South-east and north' }, SE: { c: 'var(--s4)', name: 'South-east and east' },
    AS: { c: 'var(--s3)', name: 'Atlantic and south-east, by the link' },
    LO: { c: 'var(--s8)', name: 'London and the south-east (Eurostar)' }
  };
  const kindOf = function (t) {
    const ends = [t.from, t.to], has = function (x) { return ends.indexOf(x) >= 0; };
    const k = has('A') && has('S') ? 'AS' : (has('A') ? 'A' : 'S') + (has('N') ? 'N' : 'E');
    const dark = t.to === 'N' || t.to === 'E' || (t.from === 'A' && t.to === 'S');
    if (t.london) return { k: 'LO', dark: t.to === 'N' };
    return { k: k, dark: dark };
  };
  const TB = T.table && T.table.timetables;                         // the track-by-track hour (model/table_timetable.py) when present
  const GR = T.table && T.table.grid && T.table.grid.timetables;     // the synchronised 12-minute hour, when present
  const SC = GR ? { full: GR.full, std: GR.today, max: GR.max } : TB ? { full: TB.full, std: TB.today, max: TB.max } : { full: T.chosen, std: T.standard, max: T.maximum };
  const NTR = GR ? 3 : 4;                                                     // platform tracks drawn on each side of a station
  const trainsOf = function (sc) {
    if (SC[sc]._t) return SC[sc]._t;
    SC[sc]._t = SC[sc].trains.map(function (t, i) {
      const k = kindOf(t);
      return Object.assign({ id: i, kind: k.k, dark: k.dark, col: k.dark ? KIND[k.k].c : 'color-mix(in srgb, ' + KIND[k.k].c + ' 45%, var(--surface))' }, t);
    });
    return SC[sc]._t;
  };
  const label = function (t) { return t.london ? (t.to === 'N' ? 'Eurostar from ' + LINE[t.from] + ' to London' : 'Eurostar from London to ' + LINE[t.to]) : 'From ' + LINE[t.from] + ' to ' + LINE[t.to]; };
  const tipOf = function (t) {
    const a = t.stops[0], b = t.stops[1];
    return '<b>' + label(t) + '</b><br>' + ST[a.st] + ' ' + pad(a.arr) + ' to ' + pad(a.dep) + ', track ' + a.track +
      '<br>' + ST[b.st] + ' ' + pad(b.arr) + ' to ' + pad(b.dep) + ', track ' + b.track + '<br><small>' + (a.dep_abs - a.arr_abs + b.dep_abs - b.arr_abs) + ' minutes stopped in Paris, ' +
      (b.dep_abs - a.arr_abs) + ' from the first arrival to the last departure</small>';
  };

  // ---------------------------------------------------------------- shared clock: one minute for the clocks and the map
  const state = { sc: 'std', layer: 'tgv', v: 0, playing: false, raf: 0, last: 0, speed: 1 };
  const listeners = [];
  const show = function () { listeners.forEach(function (fn) { fn(state.v); }); };
  const players = [];
  const setLabel = function () { players.forEach(function (b) { b.textContent = calm ? 'Next minute' : state.playing ? 'Pause' : 'Play'; }); };
  const tick = function (now) {
    if (!state.playing) return;
    state.v = (state.v + Math.min(100, now - state.last) / 1000 * state.speed) % 60; state.last = now; show();
    state.raf = requestAnimationFrame(tick);
  };
  const toggle = function () {
    if (calm) { state.v = (Math.floor(state.v) + 1) % 60; show(); return; }
    state.playing = !state.playing; cancelAnimationFrame(state.raf);
    if (state.playing) { state.last = performance.now(); state.raf = requestAnimationFrame(tick); }
    setLabel();
  };
  const scrubs = [];
  listeners.push(function (v) { scrubs.forEach(function (sl) { sl.set(Math.floor(v), true); }); });
  const bar = function (host, withSpeed) {
    const b = h('button', { class: 'btn', type: 'button', onclick: toggle }); players.push(b);
    const sc = h('div'); host.appendChild(b); host.appendChild(sc);
    scrubs.push(PTS.slider(sc, { label: 'Minute', min: 0, max: 59, step: 1, value: 0, format: pad },
      function (v) { state.playing = false; cancelAnimationFrame(state.raf); state.v = v; setLabel(); show(); }));
    if (withSpeed && !calm) { const sp = h('div', { class: 'tt-speed' }); host.appendChild(sp); PTS.seg(sp, [['0.5', 'Slow'], ['1', 'Normal'], ['3', 'Fast']], '1', function (v) { state.speed = +v; }, 'Speed'); }
    setLabel();
  };

  // ---------------------------------------------------------------- 1. a clock for each station: six rings, one for each platform track
  const CX = 190, CY = 190, RD = 70, R0 = RD + 14, RW = 10, GAPG = 6;
  const pt = function (m, r) { const a = m / 60 * 2 * Math.PI; return [CX + r * Math.sin(a), CY - r * Math.cos(a)]; };
  const ringR = function (side, track) { return R0 + (side === 'in' ? track - 1 : NTR + track - 1) * RW + (side === 'in' ? 0 : GAPG); };
  const arcD = function (m1, m2, r) {
    const a = pt(m1, r), b = pt(m2, r), big = (m2 - m1) > 30 ? 1 : 0;
    return 'M' + a[0].toFixed(1) + ',' + a[1].toFixed(1) + ' A' + r + ',' + r + ' 0 ' + big + ' 1 ' + b[0].toFixed(1) + ',' + b[1].toFixed(1);
  };
  const clocks = [];
  const FROM = { NE: 'the north and east', LY: 'the south-east', MP: 'the Atlantic' };
  const drawClocks = function () {
    const host = PTS.clear($('#tt-clocks')); clocks.length = 0;
    const trs = trainsOf(state.sc);
    ORDER.forEach(function (st) {
      const stays = [];
      trs.forEach(function (t) { t.stops.forEach(function (x) { if (x.st === st) stays.push({ t: t, x: x }); }); });
      const n = stays.length;
      const svg = s('svg', { class: 'draw tt-clock', viewBox: '30 30 320 320', role: 'img', 'aria-label': ST[st] + ': ' + n + ' high-speed trains an hour stop here, on six platform tracks drawn as six rings; each coloured arc is a train standing at its track.' });
      add(svg, 'circle', { cx: CX, cy: CY, r: RD, class: 'tt-face' });
      for (let m = 0; m < 60; m++) { const a = pt(m, RD), b = pt(m, RD - (m % 5 ? 4 : 9)); add(svg, 'line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: m % 5 ? 'tt-tick' : 'tt-tick five' }); }
      [[0, ':00'], [15, ':15'], [30, ':30'], [45, ':45']].forEach(function (q) { const p = pt(q[0], RD - 24); add(svg, 'text', { x: p[0], y: p[1] + 6, 'text-anchor': 'middle', class: 'tt-num', text: q[1] }); });
      ['in', 'out'].forEach(function (side) { for (let k = 1; k <= NTR; k++) add(svg, 'circle', { cx: CX, cy: CY, r: ringR(side, k), class: 'tt-ring' }); });
      stays.forEach(function (e) {
        const r = ringR(e.x.side, e.x.track), a1 = e.x.arr_abs, a2 = e.x.dep_abs;
        const g = add(svg, 'g', { class: 'tt-stay', tabindex: 0 }); g.style.setProperty('--c', e.t.col);
        const parts = [[a1, a2]].reduce(function (acc, q) {                    // split an arc that crosses the full hour
          const m1 = ((q[0] % 60) + 60) % 60, m2 = m1 + (q[1] - q[0]);
          return m2 > 60 ? acc.concat([[m1, 60], [0, m2 - 60]]) : acc.concat([[m1, m2]]);
        }, []);
        parts.forEach(function (q) { add(g, 'path', { d: arcD(q[0], q[1], r), class: 'tt-arc' }); });
        PTS.tip.bind(g, function () { return '<b>' + label(e.t) + '</b><br>Track ' + e.x.track + (e.x.side === 'in' ? ' a' : ' b') + ', ' + pad(e.x.arr) + ' to ' + pad(e.x.dep) + ' (' + (a2 - a1) + ' minutes)'; });
        e.el = g;
      });
      const hand = add(svg, 'line', { x1: CX, y1: CY, x2: CX, y2: CY - (R0 + 2 * NTR * RW + GAPG + 2), class: 'tt-handline' }); add(svg, 'circle', { cx: CX, cy: CY, r: 4.5, class: 'tt-hub' });
      const now = h('span', { class: 'tt-cap-now' });
      const box = h('div', { class: 'tt-clockbox' }, st === 'NE' ? h('h4', null, h('span', { class: 'tt-pre', text: 'Paris ' }), 'Nord-Est') : h('h4', { text: ST[st] }), svg,
        h('p', { class: 'tt-cap' }, h('span', { text: n + ' trains an hour' }), now));
      host.appendChild(box);
      clocks.push({ hand: hand, stays: stays, now: now, st: st });
    });
    const leg = $('#tt-ringnote');
    if (leg) leg.textContent = 'Inner ' + ['', 'one', 'two', 'three', 'four'][NTR] + ' rings: tracks a, for trains coming in from the station\u2019s own line; outer ' + ['', 'one', 'two', 'three', 'four'][NTR] + ' rings: tracks b, for trains going out to it. Each arc is a train at its platform, from arrival to departure; an empty ring is a track the hour does not need.';
  };
  listeners.push(function (v) {
    clocks.forEach(function (c) {
      c.hand.setAttribute('transform', 'rotate(' + ((calm ? Math.floor(v) : v) * 6).toFixed(2) + ' ' + CX + ' ' + CY + ')');
      let here = 0;
      c.stays.forEach(function (e) { const on = ((v - e.x.arr_abs) % 60 + 60) % 60 < e.x.dep_abs - e.x.arr_abs; e.el.classList.toggle('on', on); if (on) here++; });
      c.now.textContent = here + (here === 1 ? ' at a platform now' : ' at the platforms now');
    });
  });

  // the pattern of each station as a table (one cycle)
  const drawBoards = function () {
    const host = PTS.clear($('#tt-boards')), trs = trainsOf(state.sc), Pd = SC[state.sc].period;
    ORDER.forEach(function (st) {
      const rows = [];
      trs.forEach(function (t) { t.stops.forEach(function (x, j) { if (x.st === st && x.arr < Pd) rows.push({ t: t, x: x, j: j }); }); });
      rows.sort(function (a, b) { return a.x.arr - b.x.arr; });
      const reps = function (m) { const out = []; for (let k = 0; k < 60; k += Pd) out.push(pad(m + k)); return out.join(' '); };
      const tb = h('tbody');
      rows.forEach(function (r) {
        const other = r.t.stops[1 - r.j];
        tb.appendChild(h('tr', null,
          h('td', { class: 'num', text: pad(r.x.arr) }), h('td', { class: 'num', text: pad(r.x.dep) }), h('td', { class: 'num', text: r.x.track + (r.x.side === 'in' ? ' a' : ' b') }),
          h('td', null, h('i', { class: 'tt-sw', style: { '--c': r.t.col } }), r.t.london ? (r.t.to === 'N' ? 'Eurostar to London' : 'Eurostar from London') : SHORT[r.t.from] + ' to ' + SHORT[r.t.to].toLowerCase()),
          h('td', { text: (r.j === 0 ? 'next ' : 'from ') + ST[other.st] + ' ' + pad(r.j === 0 ? other.arr : other.dep) })));
      });
      host.appendChild(h('details', { class: 'tt-board' }, h('summary', null, h('strong', { text: ST[st] }), Pd >= 60 ? ': the hour, ' + rows.length + ' trains' : ': the ' + Pd + ' minutes that repeat, ' + rows.length + ' trains'),
        h('div', { class: 'tbl-wrap' }, h('table', { class: 'tbl no-stack' },
          h('thead', null, h('tr', null, h('th', { class: 'num', text: 'In' }), h('th', { class: 'num', text: 'Out' }), h('th', { class: 'num', text: 'Track' }), h('th', { text: 'Train' }), h('th', { text: 'Other Paris stop' }))), tb)),
        h('p', { class: 'note', text: (Pd >= 60 ? 'The same minutes every hour. ' : 'The same minutes come back ' + (60 / Pd) + ' times an hour: a train at :0' + (rows.length ? Math.floor(rows[0].x.arr) % 10 : 0) + ' is also at ' + reps(rows.length ? rows[0].x.arr : 0).split(' ').slice(1).join(' and ') + '. ') + 'Tracks a are for trains coming from ' + (st === 'NE' ? 'the north and east' : st === 'LY' ? 'the south-east' : 'the Atlantic') + ', tracks b for trains going there.' })));
    });
  };

  // ---------------------------------------------------------------- 2. the map
  const mapHost = $('#tt-map');
  let mapW = 0, dots = [];
  const drawMap = function () {
    const W = mapW; if (!W) return;
    PTS.clear(mapHost);
    const narrow = W < 460, view = narrow ? { lon: [2.285, 2.415], lat: [48.818, 48.91] } : { lon: [2.275, 2.425], lat: [48.82, 48.906] }, k = Math.cos(48.86 * Math.PI / 180);
    const sc = W / ((view.lon[1] - view.lon[0]) * k), H = Math.round((view.lat[1] - view.lat[0]) * sc);
    const pr = function (ll) { return [(ll[0] - view.lon[0]) * k * sc, (view.lat[1] - ll[1]) * sc]; };
    const dp = function (pts, close) { return pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1); }).join(' ') + (close ? 'Z' : ''); };
    const svg = s('svg', { class: 'draw tt-mapsvg', viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img',
      'aria-label': state.layer === 'all' ? 'Animated schematic map of every train in the tunnels: high-speed trains as squares, regional express trains as ringed dots, the suburban lines RER G and RER F as dots, standing at their platforms and moving along the tunnels at the minutes of the timetable.' : 'Animated schematic map of the three stations and their tunnels. Each dot is a high-speed train; dots stand side by side at the platforms of each station and move along the tunnels at the minutes of the timetable.' });
    svg.appendChild(s('path', { class: 'tt-land', d: G.outline.map(function (r) { return dp(r.map(pr), true); }).join('') }));
    svg.appendChild(s('path', { class: 'tt-seine', d: dp(P.seine.map(pr)) }));
    // routes, in screen points
    const C = {}; P.corridors.forEach(function (c) { C[c.id] = c.path.map(pr); });
    const SID = { 'Paris Nord-Est': 'NE', 'Gare de Lyon': 'LY', 'Montparnasse': 'MP' }, stn = {}, sl = {};
    P.stations.forEach(function (x) { if (SID[x.name]) stn[SID[x.name]] = { at: pr(x.at), axis: x.axis.map(pr) }; else if (x.name === 'Saint-Lazare') { sl.at = pr(x.at); sl.axis = (x.axis || [x.at, x.at]).map(pr); } });
    const tpath = function (t) { return (t.path || t).map(pr); };
    const trunk1 = tpath(P.trunks[0]), trunk2 = tpath(P.trunks[1]);
    const rev = function (a) { return a.slice().reverse(); };
    const ext = function (pts, len) {                                     // carry a line on beyond its portal, out to the edge of the map
      const a = pts[pts.length - 2], b = pts[pts.length - 1], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1;
      return pts.concat([[b[0] + dx / L * len, b[1] + dy / L * len]]);
    };
    const far = Math.max(W, H);
    const outer = {                                                       // from the station outwards to beyond the map
      N: ext(rev(trunk1).concat(rev(C.north).slice(1)), far), E: ext(rev(trunk1).concat(rev(C.east).slice(1)), far),
      S: ext(C.southeast, far), A: ext(C.atlantic, far)
    };
    const between = {
      'NE-LY': trunk2.concat(C.nelyon.slice(1)), 'NE-MP': trunk2.concat(C.nemont.slice(1)),
      'MP-LY': [stn.MP.at].concat(C.link, [stn.LY.at])
    };
    const seg = function (a, b) { return between[a + '-' + b] || rev(between[b + '-' + a]); };
    // lines
    const lineCls = { N: 'tt-ln', E: 'tt-ln', S: 'tt-ln', A: 'tt-ln' };
    Object.keys(outer).forEach(function (k) { svg.appendChild(s('path', { class: lineCls[k], d: dp(outer[k]) })); });
    Object.keys(between).forEach(function (k) { svg.appendChild(s('path', { class: 'tt-ln' + (k === 'MP-LY' ? ' link' : ''), d: dp(between[k]) })); });
    // place names at the edges
    const edge = function (pts, txt, anchor, dx, dy) {
      const L = pts.length, a = pts[L - 2], b = pts[L - 1];
      const t = Math.min(1, ((b[0] - a[0]) ? Math.max(((b[0] > a[0] ? W - 6 : 6) - a[0]) / (b[0] - a[0]), 0) : 1), ((b[1] - a[1]) ? Math.max(((b[1] > a[1] ? H - 6 : 6) - a[1]) / (b[1] - a[1]), 0) : 1));
      const x = a[0] + (b[0] - a[0]) * t, y = a[1] + (b[1] - a[1]) * t;
      svg.appendChild(s('text', { class: 'tt-edge', x: x + dx, y: y + dy, 'text-anchor': anchor, text: txt }));
    };
    const nm = function (k) { return narrow ? SHORT[k] : SHORT[k] + ': ' + PLACES[k]; };
    edge(outer.N, nm('N'), 'end', -8, 14); edge(outer.E, nm('E'), 'start', 8, 14);
    edge(outer.S, nm('S'), 'end', -6, -8); edge(outer.A, nm('A'), 'start', 6, -8);
    // stations: three tracks on each side
    const GAP = narrow ? 6 : 8.5, LEN = narrow ? 34 : 54;
    Object.keys(stn).forEach(function (id) {
      const x = stn[id], a = x.axis[0], b = x.axis[1], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy);
      x.u = [dx / L, dy / L]; x.n = [-x.u[1], x.u[0]];
      const g = s('g', { class: 'tt-stn' });
      const box = [-3.6, 3.6].map(function (sg) { return sg; });
      const c = x.at, hw = LEN / 2 + 5, hn = NTR * GAP + 4;
      const corner = function (p, q) { return [c[0] + x.u[0] * p + x.n[0] * q, c[1] + x.u[1] * p + x.n[1] * q]; };
      g.appendChild(s('path', { class: 'tt-box', d: dp([corner(-hw, -hn), corner(hw, -hn), corner(hw, hn), corner(-hw, hn)], true) }));
      [-1, 1].forEach(function (sg) { for (let tk = 1; tk <= NTR; tk++) { const o = sg * (tk - 0.5) * GAP; g.appendChild(s('line', { class: 'tt-track', x1: corner(-LEN / 2, o)[0], y1: corner(-LEN / 2, o)[1], x2: corner(LEN / 2, o)[0], y2: corner(LEN / 2, o)[1] })); } });
      svg.appendChild(g);
      const lbl = (narrow ? { NE: [hn + 8, 4, 'start'], LY: [0, hn + 22, 'middle'], MP: [0, hn + 22, 'middle'] } : { NE: [hn + 10, 4, 'start'], LY: [hn + 8, 18, 'start'], MP: [-hn - 8, -10, 'end'] })[id];
      svg.appendChild(s('text', { class: 'tt-sname', x: c[0] + lbl[0], y: c[1] + lbl[1], 'text-anchor': lbl[2], text: ST[id] }));
      void box;
    });
    // each train: a path through time
    const slot = function (st, side, track, toward) {                     // a train stands on its track; `toward` = the next point of its way
      const x = stn[st], sg = side === 'in' ? -1 : 1, o = sg * (track - 0.5) * GAP;
      const m = [x.at[0] + x.n[0] * o, x.at[1] + x.n[1] * o];
      const along = (toward[0] - x.at[0]) * x.u[0] + (toward[1] - x.at[1]) * x.u[1] >= 0 ? 1 : -1;
      // it stands a little before or after the middle of the platform, by turns from one track to the next, so neighbours never touch
      const i = side === 'in' ? NTR - track : NTR + track - 1, st8 = (i % 2 ? 1 : -1) * LEN * 0.12, c = [m[0] + x.u[0] * st8, m[1] + x.u[1] * st8];
      return { c: c, back: [m[0] - x.u[0] * along * LEN / 2, m[1] - x.u[1] * along * LEN / 2], front: [m[0] + x.u[0] * along * LEN / 2, m[1] + x.u[1] * along * LEN / 2] };
    };
    const poly = function (pts) {
      const cum = [0]; for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
      return { pts: pts, cum: cum, len: cum[cum.length - 1] };
    };
    const at = function (pl, f) {
      const d = Math.max(0, Math.min(1, f)) * pl.len; let i = 1; while (i < pl.cum.length - 1 && pl.cum[i] < d) i++;
      const a = pl.pts[i - 1], b = pl.pts[i], seg = (pl.cum[i] - pl.cum[i - 1]) || 1, t = (d - pl.cum[i - 1]) / seg;
      return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
    };
    const ease = function (f) { return f < 0.5 ? 2 * f * f : 1 - 2 * (1 - f) * (1 - f); };
    const APPROACH = 5;                                                   // minutes drawn from the edge of the map to the platform
    const g = s('g'); svg.appendChild(g);
    dots = trainsOf(state.sc).map(function (t) {
      const a = t.stops[0], b = t.stops[1], mid = seg(a.st, b.st);
      const inn = rev(outer[t.from]), out = outer[t.to];
      const sa = slot(a.st, a.side, a.track, mid[1]), sb = slot(b.st, b.side, b.track, out[1]);
      const legs = [
        { t0: a.arr_abs - APPROACH, t1: a.arr_abs, pl: poly(inn.slice(0, -1).concat([sa.back, sa.c])), e: function (f) { return 1 - (1 - f) * (1 - f); } },
        { t0: a.arr_abs, t1: a.dep_abs, still: sa.c },
        { t0: a.dep_abs, t1: b.arr_abs, pl: poly([sa.c, sa.front].concat(mid.slice(1, -1), [sb.back, sb.c])), e: ease },
        { t0: b.arr_abs, t1: b.dep_abs, still: sb.c },
        { t0: b.dep_abs, t1: b.dep_abs + APPROACH, pl: poly([sb.c, sb.front].concat(out.slice(1))), e: function (f) { return f * f; } }
      ];
      const el = mark(state.layer === 'all' ? 'square' : 'dot', narrow, label(t));
      el.style.setProperty('--c', t.col); PTS.tip.bind(el, tipOf(t)); g.appendChild(el);
      return { t: t, legs: legs, el: el };
    });
    if (state.layer === 'all') regional({ svg: svg, g: g, pr: pr, dp: dp, stn: stn, sl: sl, C: C, outer: outer, between: between, trunk1: trunk1, trunk2: trunk2, rev: rev, ext: ext, far: far,
      poly: poly, ease: ease, slot: slot, GAP: GAP, LEN: LEN, narrow: narrow, APPROACH: APPROACH, W: W, H: H, edge: edge });
    mapHost.appendChild(svg);
    placeDots(state.v);
  };
  // a train's mark, drawn round (0, 0) and moved with a transform: a dot (TGV alone, suburban), a square (TGV with the others), a ringed dot (regional express)
  const mark = function (shape, narrow, aria) {
    const r = narrow ? 3.2 : 4.4, el = s('g', { class: 'tt-dot tt-' + shape, tabindex: 0, role: 'img', 'aria-label': aria });
    if (shape === 'square') el.appendChild(s('rect', { x: -r, y: -r, width: 2 * r, height: 2 * r, rx: 1 }));
    else if (shape === 'ring') { el.appendChild(s('circle', { r: r + 2.2, class: 'tt-halo' })); el.appendChild(s('circle', { r: r - 0.6 })); }
    else el.appendChild(s('circle', { r: shape === 'sub' ? r - 0.8 : r }));
    return el;
  };

  // ---------------------------------------------------------------- 2b. regional express and suburban trains (the all-trains view)
  // Regional express trains (TER): the minutes of the model (model/ter_timetable.py, checked by model/table_timetable.py), in the
  // TGV tunnels between the TGVs. Suburban lines N and H: evenly spaced at the model's trains an hour, in tunnels of their own.
  const M = PTS.data.model;
  const REG = {
    TER: { c: 'var(--neutral-mark)', name: 'Regional express (TER), in the TGV tunnels', shape: 'ring' },
    N: { c: 'color-mix(in srgb, #00a092 85%, var(--ink))', name: 'RER G (today’s lines P and N)', shape: 'sub' },          // Île-de-France colours of lines N and H
    H: { c: 'color-mix(in srgb, #8d5e2a 72%, var(--ink))', name: 'RER F (today’s lines H, K and L)', shape: 'sub' }
  };
  const SUB_STOP = 1, SUB_RUN = { MP: M.TR.M - 1, SL: M.TR.SL - 1 };
  const REGT = T.table && T.table.grid && T.table.grid.regional;            // the regional express hour of each scenario
  const regionalTrains = function () {
    const out = [];
    const R_ = REGT && REGT[{ std: 'today', full: 'full', max: 'max' }[state.sc]];
    (R_ ? R_.trains : []).forEach(function (t) {
      out.push({ kind: 'TER', from: t.from, to: t.to, fwd: t.from === 'N' || t.from === 'E',
        stops: t.stops.map(function (x) { return { st: x.st, arr_abs: x.arr_abs, dep_abs: x.dep_abs, track: x.track }; }) });
    });
    const sub = function (line, n, from, to, a, b, run, off) {
      for (let i = 0; i < n; i++) {
        const d1 = off + i * 60 / n, a2 = d1 + run;
        out.push({ kind: line, from: from, to: to, stops: [{ st: a, arr_abs: d1 - SUB_STOP, dep_abs: d1 }, { st: b, arr_abs: a2, dep_abs: a2 + SUB_STOP }], track: i, fwd: from === 'N' || from === 'E' });
      }
    };
    const nN = Math.max(M.reg_platforms.n.peak.P, M.reg_platforms.n.peak.N), nH = M.reg_platforms.h.peak.H + M.reg_platforms.h.peak.K;
    sub('N', nN, 'E', 'A', 'NE', 'MP', SUB_RUN.MP, 1.5); sub('N', nN, 'A', 'E', 'MP', 'NE', SUB_RUN.MP, 4);
    sub('H', nH, 'N', 'W', 'NE', 'SL', SUB_RUN.SL, 0.5); sub('H', nH, 'W', 'N', 'SL', 'NE', SUB_RUN.SL, 1.75);
    return out;
  };
  const offsetLine = function (pts, d) {                                  // a polyline moved sideways by d pixels
    return pts.map(function (p, i) {
      const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1;
      return [p[0] - dy / L * d, p[1] + dx / L * d];
    });
  };
  const regional = function (o) {
    const svg = o.svg, dp = o.dp, rev = o.rev, OFF = o.narrow ? 5 : 7;
    const under = s('g'); svg.insertBefore(under, o.g);                     // the suburban tunnels go under the platform boxes
    // platforms of the other trains: a small box of tracks beside each TGV box, on the side where each line's tunnel runs
    // (regional express beside the TGV box; RER G beyond it, on the side of its tunnel), and Saint-Lazare
    const D = M.cost.detail, SUBT = M.sub_tracks, g2 = o.GAP * 0.55, hl = o.LEN * 0.38;
    const GROUPS = {
      NE: [['TER', D['Paris Nord-Est'].ter, -1], ['N', SUBT['Paris Nord-Est'].n, -1], ['H', SUBT['Paris Nord-Est'].h, 1]],
      MP: [['N', SUBT['Montparnasse'].n, -1], ['TER', D['Montparnasse'].ter, 1]],
      LY: [['TER', D['Gare de Lyon'].hs - 2 * NTR, -1]]                   // the fourth track each way, shared with the sixteenth south-east TGV
    };
    if (o.sl.at) { const a = o.sl.axis[0], b = o.sl.axis[1], L = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1; o.sl.u = [(b[0] - a[0]) / L, (b[1] - a[1]) / L]; o.sl.n = [-o.sl.u[1], o.sl.u[0]]; }
    const tracksAt = {}, boxAt = {}, labels = [];                                        // centre of each track: tracksAt[st][kind] = [points]; boxAt[st][kind] = the box's centre and the middles of its two ends
    const drawGroup = function (st, x, kind, n, from) {                     // n tracks from offset `from` along the station's normal
      const c = function (p, q) { return [x.at[0] + x.u[0] * p + x.n[0] * q, x.at[1] + x.u[1] * p + x.n[1] * q]; };
      const lo = from, hi = from + n * g2, gg = s('g', { class: 'tt-stn' });
      gg.appendChild(s('path', { class: 'tt-box reg', d: dp([c(-hl, lo), c(hl, lo), c(hl, hi), c(-hl, hi)], true) }));
      const pts = [];
      // a train stands a little before or after the middle of its platform, by turns from one track to the next, so neighbours never touch
      for (let k = 0; k < n; k++) { const q = lo + (k + 0.5) * g2; gg.appendChild(s('line', { class: 'tt-track', x1: c(-hl + 3, q)[0], y1: c(-hl + 3, q)[1], x2: c(hl - 3, q)[0], y2: c(hl - 3, q)[1] })); pts.push(c((k % 2 ? 1 : -1) * hl * 0.3, q)); }
      svg.insertBefore(gg, o.g);
      (tracksAt[st] = tracksAt[st] || {})[kind] = pts;
      (boxAt[st] = boxAt[st] || {})[kind] = { c: c(0, (lo + hi) / 2), ends: [c(-hl, (lo + hi) / 2), c(hl, (lo + hi) / 2)] };
      if (REG[kind] && kind !== 'TER') {                                    // the name of the RER line, just outside its box
        const p = c(hl + 9, (lo + hi) / 2);                                  // beyond the end of the box, clear of the station's name
        const t = s('text', { class: 'tt-rername', x: p[0], y: p[1] + 4, 'text-anchor': 'middle', text: kind === 'N' ? 'RER G' : 'RER F', style: 'fill: ' + REG[kind].c });
        labels.push(t);
      }
    };
    Object.keys(GROUPS).forEach(function (st) {
      const x = o.stn[st], edgeOff = NTR * o.GAP + 4 + 3, used = { '-1': edgeOff, '1': edgeOff };
      GROUPS[st].forEach(function (gp) { if (!(gp[1] > 0)) return; const sd = String(gp[2]), from = used[sd]; drawGroup(st, x, gp[0], gp[1], gp[2] > 0 ? from : -from - gp[1] * g2); used[sd] = from + gp[1] * g2 + 2; });
      // move the station's name clear of the new boxes
      const shift = Math.max(used['-1'], used['1']) - edgeOff;
      [].forEach.call(svg.querySelectorAll('text.tt-sname'), function (tx) { if (tx.textContent === ST[st]) { const anc = tx.getAttribute('text-anchor'); tx.setAttribute('x', +tx.getAttribute('x') + (anc === 'start' ? shift : anc === 'end' ? -shift : 0)); if (anc === 'middle') tx.setAttribute('y', +tx.getAttribute('y') + shift); } });
    });
    if (o.sl.at) {
      const n = SUBT['Saint-Lazare'].h; drawGroup('SL', o.sl, 'H', n, -n * g2 / 2);
      const ex = Math.abs(o.sl.u[0]) * hl + Math.abs(o.sl.n[0]) * n * g2 / 2;      // half the box's width on screen
      svg.insertBefore(s('text', { class: 'tt-sname', x: o.sl.at[0] - ex - 6, y: o.sl.at[1] + 4, 'text-anchor': 'end', text: 'Saint-Lazare' }), o.g);
    }
    // the suburban tunnels, drawn beside the TGV ones; regional express trains use the TGV tunnels themselves.
    // Near each of its stations a tunnel leaves its course and runs straight into the middle of the near end of its box, and out of the far end
    const toNE = o.trunk1.concat(o.trunk2.slice(1));
    const both = function (pts) { return rev(o.ext(rev(o.ext(pts, o.far)), o.far)); };      // carried on beyond the map at both ends
    const dist = function (p, q) { return Math.hypot(p[0] - q[0], p[1] - q[1]); };
    const into = function (pts, sts, kind) {                                // pts: the tunnel; sts: its stations in order along it
      sts.forEach(function (st) {
        const bx = boxAt[st] && boxAt[st][kind]; if (!bx) return;
        const ctr = st === 'SL' ? o.sl.at : o.stn[st].at, R = dist(ctr, bx.ends[0]) + o.LEN * 0.6;
        const cross = function (a, b) { let lo = 0, hi = 1; for (let i = 0; i < 30; i++) { const m = (lo + hi) / 2, p = [a[0] + (b[0] - a[0]) * m, a[1] + (b[1] - a[1]) * m]; if ((dist(p, ctr) < R) === (dist(a, ctr) < R)) lo = m; else hi = m; } return [a[0] + (b[0] - a[0]) * lo, a[1] + (b[1] - a[1]) * lo]; };
        let i0 = -1, i1 = -1;
        for (let i = 1; i < pts.length; i++) { const ina = dist(pts[i - 1], ctr) < R, inb = dist(pts[i], ctr) < R; if (!ina && inb && i0 < 0) i0 = i; if (ina && !inb) i1 = i; }
        if (i0 < 0 || i1 < i0) return;
        const pin = cross(pts[i0 - 1], pts[i0]), pout = cross(pts[i1 - 1], pts[i1]);
        const e = dist(pin, bx.ends[0]) <= dist(pin, bx.ends[1]) ? bx.ends : rev(bx.ends);
        const lead = function (q) { const L = dist(q, bx.c) || 1, d = o.LEN * 0.22; return [q[0] + (q[0] - bx.c[0]) / L * d, q[1] + (q[1] - bx.c[1]) / L * d]; };   // a short straight run in line with the tracks
        pts = pts.slice(0, i0).concat([pin, lead(e[0]), e[0], bx.c, e[1], lead(e[1]), pout], pts.slice(i1));
      });
      return pts;
    };
    const lineN = into(both(offsetLine(o.C.east.concat(toNE.slice(1), o.C.nemont.slice(1), o.C.atlantic.slice(1)), -OFF)), ['NE', 'MP'], 'N');
    const lineH = into(both(offsetLine(o.C.north.concat(toNE.slice(1), o.C.nesl.slice(1), o.C.slwest.slice(1)), OFF)), ['NE', 'SL'], 'H');
    [[lineN, REG.N.c], [lineH, REG.H.c]].forEach(function (q) { under.appendChild(s('path', { class: 'tt-ln sub', d: dp(q[0]), style: '--c: ' + q[1] })); });
    o.edge(lineH, 'RER F: west', 'start', 6, -6);
    const spot = function (t, j) {                                          // half the tracks for each direction: the timetable's track, or trains in turn
      const pts = tracksAt[t.stops[j].st][t.kind], half = Math.max(1, Math.floor(pts.length / 2)), k = t.stops[j].track === undefined ? t.track : t.stops[j].track;
      return pts[pts.length === 1 ? 0 : (t.fwd ? 0 : half) + (k % half)];
    };
    const near = function (pts, q) { let best = 0, bd = 1e9; pts.forEach(function (p, i) { const dd = Math.hypot(p[0] - q[0], p[1] - q[1]); if (dd < bd) { bd = dd; best = i; } }); return best; };
    const st2pt = function (st, kind) { return boxAt[st] && boxAt[st][kind] ? boxAt[st][kind].c : st === 'SL' ? o.sl.at : o.stn[st].at; };
    const route = function (t) {                                            // from the map edge, between the two stops, out to the edge
      const a = t.stops[0].st, b = t.stops[1].st;
      if (t.kind === 'TER') {                                               // at Nord-Est the TER leave the TGV tracks at the ends of the station, for their own platforms
        const mid = o.between[a + '-' + b] || rev(o.between[b + '-' + a]);
        return { inn: a === 'NE' ? rev(o.outer[t.from]).slice(0, -1) : rev(o.outer[t.from]), mid: a === 'NE' ? mid.slice(1) : b === 'NE' ? mid.slice(0, -1) : mid,
          out: b === 'NE' ? o.outer[t.to].slice(1) : o.outer[t.to] };
      }
      const full = t.kind === 'N' ? lineN : lineH, pl = (t.from === 'E' || t.from === 'N') ? full : rev(full);
      const ia = near(pl, st2pt(a, t.kind)), ib = near(pl, st2pt(b, t.kind));
      return { inn: pl.slice(0, ia + 1), mid: pl.slice(ia, ib + 1), out: pl.slice(ib) };
    };
    regionalTrains().forEach(function (t, k) {
      const a = t.stops[0], b = t.stops[1], R = REG[t.kind];
      const pa = spot(t, 0), pb = spot(t, 1);
      const rt = route(t), inn = rt.inn, out = rt.out, mid = rt.mid;
      const legs = [
        { t0: a.arr_abs - o.APPROACH, t1: a.arr_abs, pl: o.poly(inn.slice(0, -1).concat([pa])), e: function (f) { return 1 - (1 - f) * (1 - f); } },
        { t0: a.arr_abs, t1: a.dep_abs, still: pa },
        { t0: a.dep_abs, t1: b.arr_abs, pl: o.poly([pa].concat(mid.slice(1, -1), [pb])), e: o.ease },
        { t0: b.arr_abs, t1: b.dep_abs, still: pb },
        { t0: b.dep_abs, t1: b.dep_abs + o.APPROACH, pl: o.poly([pb].concat(out.slice(1))), e: function (f) { return f * f; } }
      ];
      const nm = { NE: 'Nord-Est', LY: 'Gare de Lyon', MP: 'Montparnasse', SL: 'Saint-Lazare' };
      const el = mark(R.shape, o.narrow, R.name + ', ' + nm[a.st] + ' to ' + nm[b.st]);
      el.style.setProperty('--c', R.c);
      PTS.tip.bind(el, '<b>' + R.name + '</b><br>' + nm[a.st] + ' ' + padh(a.arr_abs) + ' to ' + padh(a.dep_abs) + '<br>' + nm[b.st] + ' ' + padh(b.arr_abs) + ' to ' + padh(b.dep_abs) +
        (t.kind === 'TER' ? '' : '<br><small>Evenly spaced at the trains an hour of the model</small>'));
      o.g.appendChild(el); dots.push({ t: t, legs: legs, el: el, reg: t.kind });
    });
    labels.forEach(function (t) { svg.insertBefore(t, o.g); });            // above the lines and the boxes, under the moving trains
  };

  const placeDots = function (v) {
    dots.forEach(function (d) {
      let p = null;
      [v, v + 60, v - 60, v + 120].some(function (tt) {
        return d.legs.some(function (l) {
          if (tt < l.t0 || tt >= l.t1) return false;
          p = l.still || (function () { const f = l.e((tt - l.t0) / (l.t1 - l.t0)); const pl = l.pl; const dd = Math.max(0, Math.min(1, f)) * pl.len; let i = 1; while (i < pl.cum.length - 1 && pl.cum[i] < dd) i++; const a = pl.pts[i - 1], b = pl.pts[i], sg = (pl.cum[i] - pl.cum[i - 1]) || 1, q = (dd - pl.cum[i - 1]) / sg; return [a[0] + (b[0] - a[0]) * q, a[1] + (b[1] - a[1]) * q]; })();
          d.stopped = !!l.still; return true;
        });
      });
      if (p) { d.el.setAttribute('transform', 'translate(' + p[0].toFixed(1) + ' ' + p[1].toFixed(1) + ')' + (d.reg === 'TER' && d.stopped ? ' scale(.6)' : '')); d.el.style.display = ''; d.el.classList.toggle('stopped', d.stopped); }
      else d.el.style.display = 'none';
    });
    $('#tt-now').textContent = pad(v);
    const moving = dots.filter(function (d) { return d.el.style.display !== 'none' && !d.stopped; }).length, still = dots.filter(function (d) { return d.el.style.display !== 'none' && d.stopped; }).length;
    const vis = dots.filter(function (d) { return d.el.style.display !== 'none'; }), by = function (f) { return vis.filter(f).length; };
    $('#tt-now-read').textContent = state.layer === 'all'
      ? by(function (d) { return !d.reg; }) + ' TGVs, ' + by(function (d) { return d.reg === 'TER'; }) + ' regional express and ' + by(function (d) { return d.reg === 'N' || d.reg === 'H'; }) + ' suburban trains on the map; ' + still + ' standing at a platform, ' + moving + ' on the move'
      : still + ' trains standing at a platform, ' + moving + ' on the move';
  };
  listeners.push(placeDots);
  PTS.onResize(mapHost, function (w) { mapW = Math.min(w, 760); drawMap(); });

  // legend
  const drawLegend = function () {
    const leg = PTS.clear($('#tt-legend-map')), sq = state.layer === 'all' ? ' sq' : '';
    Object.keys(KIND).forEach(function (k) {
      leg.appendChild(h('li', null, h('i', { class: 'tt-pair' + sq }, h('b', { style: { '--c': KIND[k].c } }), h('b', { style: { '--c': 'color-mix(in srgb, ' + KIND[k].c + ' 45%, var(--surface))' } })), KIND[k].name));
    });
    if (state.layer !== 'all') return;
    Object.keys(REG).forEach(function (k) { leg.appendChild(h('li', null, h('i', { class: 'tt-pair' }, h('b', { class: k === 'TER' ? 'ring' : 'sub', style: { '--c': REG[k].c } })), REG[k].name)); });
  };

  // ---------------------------------------------------------------- 3. connections: pulse against a timetable not built for them
  const drawPairs = function () {
    const sc = state.sc;
    const key = { std: 'today', full: 'full', max: 'max' }[sc];
    const E = GR ? T.table.grid.measures[key] : TB ? T.table.measures[key] : T.cases[{ std: 'even10', full: 'even20', max: 'evenmax' }[sc]].even;
    const routes = TB ? SC[sc].trains : null;
    const count = function (a, b) { return routes ? routes.filter(function (t) { return t.from === a && t.to === b; }).length : null; };
    const NAME = { AS: 'Atlantic and south-east', AN: 'Atlantic and north', AE: 'Atlantic and east', SN: 'South-east and north', SE: 'South-east and east' };
    const rows = [];
    Object.keys(NAME).forEach(function (k) {
      const a = E.pair[k], b = E.pair[k.charAt(1) + k.charAt(0)], v = (a + b) / 2, n = count(k.charAt(0), k.charAt(1)) || 1, ideal = 30 / n;
      rows.push({ label: NAME[k] + ' <small>' + n0(n) + ' direct train' + (n === 1 ? '' : 's') + ' an hour each way</small>', value: v, mark: ideal, text: F.n(v, 1) + ' min', color: 'var(--s3)',
        tip: '<b>' + NAME[k] + '</b><br>Average wait for the next direct train: ' + F.n(a, 1) + ' and ' + F.n(b, 1) + ' minutes in the two directions<br><small>With trains exactly evenly spaced: ' + F.n(ideal, 1) + '</small>' });
    });
    PTS.chart.bars($('#tt-pairs'), { rows: rows, max: 25, fmt: function (v) { return F.n(v, 1) + ' min'; } });
    const cmp = $('#tt-compare'); if (cmp) PTS.clear(cmp);
  };

  // ---------------------------------------------------------------- 4. longer stops
  const drawStops = function () {
    const base = T.frontier[String(T.inputs.stop)] || T.frontier[T.inputs.stop];
    const rows = [];
    Object.keys(T.frontier).forEach(function (D) {
      const f = T.frontier[D];
      if (!f) { rows.push({ label: '<b>' + D + ' minutes</b>', parts: [], text: 'does not fit the tracks' }); return; }
      const cross = (f.cross - base.cross) * T.inputs.cross_trips, paris = f.held_cost * T.inputs.cross_trips;
      rows.push({ label: '<b>' + D + ' minutes</b>', parts: [
        { label: 'Passengers crossing Paris', value: Math.max(0, cross) / 60, color: 'var(--s2)' },
        { label: 'Paris passengers who stay on board through a stop', value: paris / 60, color: 'var(--s1)' }],
        text: (cross + paris) / 60 > 0.05 ? '+' + F.n((cross + paris) / 60, 1) + ' M h' : 'reference' });
    });
    PTS.chart.stack($('#tt-stops'), { rows: rows, fmt: function (v) { return F.n(v, 2) + ' million hours a year'; } });
  };

  // ---------------------------------------------------------------- controls and first draw
  const redraw = function () { drawClocks(); drawBoards(); drawMap(); drawLegend(); drawPairs(); show(); };
  PTS.seg($('#tt-layer'), [['tgv', 'High-speed trains'], ['all', 'All trains']], state.layer, function (v) { state.layer = v; setTitle(); drawMap(); drawLegend(); show(); }, 'Trains shown');
  const title0 = $('#tt-map-title').textContent;
  const setTitle = function () { $('#tt-map-title').textContent = state.layer === 'all' ? 'Every square is a TGV, every ringed dot a regional express train, every dot a suburban train; at the platforms they stand side by side, one line for each track' : title0; };
  const scen = [['std', 'About today'], ['full', 'Southern lines full'], ['max', 'Nord-Est filled too']];
  const segs = [];
  const setSc = function (v) { state.sc = v; segs.forEach(function (x) { x.set(v, true); }); redraw(); };
  segs.push(PTS.seg($('#tt-scen-2'), scen, state.sc, setSc, 'Hour shown'));
  bar($('#tt-bar-2'), true);
  drawStops(); redraw();
});
