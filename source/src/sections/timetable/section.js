PTS.section('timetable', function (root) {
  'use strict';
  const T = PTS.data.timetable, P = PTS.data.project, G = PTS.data.paris_geo, F = PTS.fmt, h = PTS.h, s = PTS.s;
  const $ = function (sel) { return root.querySelector(sel); };
  const calm = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const pad = function (m) { m = ((Math.floor(m) % 60) + 60) % 60; return ':' + (m < 10 ? '0' : '') + m; };
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
    AS: { c: 'var(--s3)', name: 'Atlantic and south-east, by the link' }
  };
  const kindOf = function (t) {
    const ends = [t.from, t.to], has = function (x) { return ends.indexOf(x) >= 0; };
    const k = has('A') && has('S') ? 'AS' : (has('A') ? 'A' : 'S') + (has('N') ? 'N' : 'E');
    const dark = t.to === 'N' || t.to === 'E' || (t.from === 'A' && t.to === 'S');
    return { k: k, dark: dark };
  };
  const SC = { full: T.chosen, std: T.standard, max: T.maximum };
  const trainsOf = function (sc) {
    if (SC[sc]._t) return SC[sc]._t;
    SC[sc]._t = SC[sc].trains.map(function (t, i) {
      const k = kindOf(t);
      return Object.assign({ id: i, kind: k.k, dark: k.dark, col: k.dark ? KIND[k.k].c : 'color-mix(in srgb, ' + KIND[k.k].c + ' 45%, var(--surface))' }, t);
    });
    return SC[sc]._t;
  };
  const label = function (t) { return 'From ' + LINE[t.from] + ' to ' + LINE[t.to]; };
  const tipOf = function (t) {
    const a = t.stops[0], b = t.stops[1];
    return '<b>' + SHORT[t.from] + ' to ' + SHORT[t.to].toLowerCase() + '</b><br>' + ST[a.st] + ' ' + pad(a.arr) + ' to ' + pad(a.dep) + ', track ' + a.track +
      '<br>' + ST[b.st] + ' ' + pad(b.arr) + ' to ' + pad(b.dep) + ', track ' + b.track + '<br><small>' + (a.dep_abs - a.arr_abs + b.dep_abs - b.arr_abs) + ' minutes stopped in Paris, ' +
      (b.dep_abs - a.arr_abs) + ' from the first arrival to the last departure</small>';
  };

  // ---------------------------------------------------------------- shared clock: one minute for the clocks and the map
  const state = { sc: 'std', v: 0, playing: false, raf: 0, last: 0, speed: 1 };
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
  const CX = 190, CY = 190, RD = 74, R0 = RD + 16, RW = 12, GAPG = 7;
  const pt = function (m, r) { const a = m / 60 * 2 * Math.PI; return [CX + r * Math.sin(a), CY - r * Math.cos(a)]; };
  const ringR = function (side, track) { return R0 + (side === 'in' ? track - 1 : 3 + track - 1) * RW + (side === 'in' ? 0 : GAPG); };
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
      const svg = s('svg', { class: 'draw tt-clock', viewBox: '0 0 380 380', role: 'img', 'aria-label': ST[st] + ': ' + n + ' high-speed trains an hour stop here, on six platform tracks drawn as six rings; each coloured arc is a train standing at its track.' });
      add(svg, 'circle', { cx: CX, cy: CY, r: RD, class: 'tt-face' });
      for (let m = 0; m < 60; m++) { const a = pt(m, RD), b = pt(m, RD - (m % 5 ? 4 : 9)); add(svg, 'line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: m % 5 ? 'tt-tick' : 'tt-tick five' }); }
      [[0, ':00'], [15, ':15'], [30, ':30'], [45, ':45']].forEach(function (q) { const p = pt(q[0], RD - 21); add(svg, 'text', { x: p[0], y: p[1] + 4.5, 'text-anchor': 'middle', class: 'tt-num', text: q[1] }); });
      ['in', 'out'].forEach(function (side) { for (let k = 1; k <= 3; k++) add(svg, 'circle', { cx: CX, cy: CY, r: ringR(side, k), class: 'tt-ring' }); });
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
      const hand = add(svg, 'line', { x1: CX, y1: CY, x2: CX, y2: CY - (R0 + 6 * RW + GAPG + 2), class: 'tt-handline' }); add(svg, 'circle', { cx: CX, cy: CY, r: 4.5, class: 'tt-hub' });
      const now = h('span', { class: 'tt-cap-now' });
      const box = h('div', { class: 'tt-clockbox' }, h('h4', { text: ST[st] }), svg,
        h('p', { class: 'tt-cap' }, h('span', { text: n + ' trains an hour' }), now));
      host.appendChild(box);
      clocks.push({ hand: hand, stays: stays, now: now, st: st });
    });
    const leg = $('#tt-ringnote');
    if (leg) leg.textContent = 'Inner three rings: tracks a, for trains coming in from the station\u2019s own line; outer three rings: tracks b, for trains going out to it. Each arc is a train at its platform, from arrival to departure.';
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
          h('td', null, h('i', { class: 'tt-sw', style: { '--c': r.t.col } }), SHORT[r.t.from] + ' to ' + SHORT[r.t.to].toLowerCase()),
          h('td', { text: (r.j === 0 ? 'next ' : 'from ') + ST[other.st] + ' ' + pad(r.j === 0 ? other.arr : other.dep) })));
      });
      host.appendChild(h('details', { class: 'tt-board' }, h('summary', null, h('strong', { text: ST[st] }), ': the ' + Pd + ' minutes that repeat, ' + rows.length + ' trains'),
        h('div', { class: 'tbl-wrap' }, h('table', { class: 'tbl no-stack' },
          h('thead', null, h('tr', null, h('th', { class: 'num', text: 'In' }), h('th', { class: 'num', text: 'Out' }), h('th', { class: 'num', text: 'Track' }), h('th', { text: 'Train' }), h('th', { text: 'Other Paris stop' }))), tb)),
        h('p', { class: 'note', text: 'The same minutes come back ' + (60 / Pd) + ' times an hour: a train at :0' + (rows.length ? Math.floor(rows[0].x.arr) % 10 : 0) + ' is also at ' + reps(rows.length ? rows[0].x.arr : 0).split(' ').slice(1).join(' and ') + '. Tracks a are for trains coming from ' + (st === 'NE' ? 'the north and east' : st === 'LY' ? 'the south-east' : 'the Atlantic') + ', tracks b for trains going there.' })));
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
      'aria-label': 'Animated schematic map of the three stations and their tunnels. Each dot is a high-speed train; dots stand side by side at the platforms of each station and move along the tunnels at the minutes of the timetable.' });
    svg.appendChild(s('path', { class: 'tt-land', d: G.outline.map(function (r) { return dp(r.map(pr), true); }).join('') }));
    svg.appendChild(s('path', { class: 'tt-seine', d: dp(P.seine.map(pr)) }));
    // routes, in screen points
    const C = {}; P.corridors.forEach(function (c) { C[c.id] = c.path.map(pr); });
    const stn = {}; P.stations.forEach(function (x) { stn[{ 'Paris Nord-Est': 'NE', 'Gare de Lyon': 'LY', 'Montparnasse': 'MP' }[x.name]] = { at: pr(x.at), axis: x.axis.map(pr) }; });
    const trunk1 = P.trunks[0].map(pr), trunk2 = P.trunks[1].map(pr);
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
    const GAP = narrow ? 7 : 10, LEN = narrow ? 34 : 54;
    Object.keys(stn).forEach(function (id) {
      const x = stn[id], a = x.axis[0], b = x.axis[1], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy);
      x.u = [dx / L, dy / L]; x.n = [-x.u[1], x.u[0]];
      const g = s('g', { class: 'tt-stn' });
      const box = [-3.6, 3.6].map(function (sg) { return sg; });
      const c = x.at, hw = LEN / 2 + 5, hn = 3 * GAP + 4;
      const corner = function (p, q) { return [c[0] + x.u[0] * p + x.n[0] * q, c[1] + x.u[1] * p + x.n[1] * q]; };
      g.appendChild(s('path', { class: 'tt-box', d: dp([corner(-hw, -hn), corner(hw, -hn), corner(hw, hn), corner(-hw, hn)], true) }));
      [-1, 1].forEach(function (sg) { for (let tk = 1; tk <= 3; tk++) { const o = sg * (tk - 0.5) * GAP; g.appendChild(s('line', { class: 'tt-track', x1: corner(-LEN / 2, o)[0], y1: corner(-LEN / 2, o)[1], x2: corner(LEN / 2, o)[0], y2: corner(LEN / 2, o)[1] })); } });
      svg.appendChild(g);
      const lbl = (narrow ? { NE: [hn + 8, 4, 'start'], LY: [0, hn + 22, 'middle'], MP: [0, hn + 22, 'middle'] } : { NE: [hn + 10, 4, 'start'], LY: [hn + 8, 18, 'start'], MP: [-hn - 8, -10, 'end'] })[id];
      svg.appendChild(s('text', { class: 'tt-sname', x: c[0] + lbl[0], y: c[1] + lbl[1], 'text-anchor': lbl[2], text: ST[id] }));
      void box;
    });
    // each train: a path through time
    const slot = function (st, side, track, toward) {                     // a train stands on its track; `toward` = the next point of its way
      const x = stn[st], sg = side === 'in' ? -1 : 1, o = sg * (track - 0.5) * GAP;
      const c = [x.at[0] + x.n[0] * o, x.at[1] + x.n[1] * o];
      const along = (toward[0] - x.at[0]) * x.u[0] + (toward[1] - x.at[1]) * x.u[1] >= 0 ? 1 : -1;
      return { c: c, back: [c[0] - x.u[0] * along * LEN / 2, c[1] - x.u[1] * along * LEN / 2], front: [c[0] + x.u[0] * along * LEN / 2, c[1] + x.u[1] * along * LEN / 2] };
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
      const el = s('circle', { r: narrow ? 3.2 : 4.4, class: 'tt-dot', tabindex: 0, role: 'img', 'aria-label': label(t) });
      el.style.setProperty('--c', t.col); PTS.tip.bind(el, tipOf(t)); g.appendChild(el);
      return { t: t, legs: legs, el: el };
    });
    mapHost.appendChild(svg);
    placeDots(state.v);
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
      if (p) { d.el.setAttribute('cx', p[0].toFixed(1)); d.el.setAttribute('cy', p[1].toFixed(1)); d.el.style.display = ''; d.el.classList.toggle('stopped', d.stopped); }
      else d.el.style.display = 'none';
    });
    $('#tt-now').textContent = pad(v);
    const moving = dots.filter(function (d) { return d.el.style.display !== 'none' && !d.stopped; }).length, still = dots.filter(function (d) { return d.el.style.display !== 'none' && d.stopped; }).length;
    $('#tt-now-read').textContent = still + ' trains standing at a platform, ' + moving + ' on the move';
  };
  listeners.push(placeDots);
  PTS.onResize(mapHost, function (w) { mapW = Math.min(w, 760); drawMap(); });

  // legend
  ['#tt-legend-map'].forEach(function (sel) { const leg = $(sel); Object.keys(KIND).forEach(function (k) {
    leg.appendChild(h('li', null, h('i', { class: 'tt-pair' }, h('b', { style: { '--c': KIND[k].c } }), h('b', { style: { '--c': 'color-mix(in srgb, ' + KIND[k].c + ' 45%, var(--surface))' } })), KIND[k].name));
  }); });

  // ---------------------------------------------------------------- 3. connections: pulse against a timetable not built for them
  const drawPairs = function () {
    const sc = state.sc, full = sc !== 'std', E = T.cases[{ std: 'even10', full: 'even20', max: 'evenmax' }[sc]];
    const Pu = sc === 'max' ? null : full ? T.cases.pulse20 : T.cases.pulse10, R = sc === 'max' ? null : full ? T.cases.random20 : T.cases.random10;
    const ev = E.even, hour = sc === 'full' ? T.inputs.hour : sc === 'max' ? T.max_hour : { AN: 6, SN: 6, AS: 6 };
    const NAME = { AS: 'Atlantic and south-east', AN: 'Atlantic and north', AE: 'Atlantic and east', SN: 'South-east and north', SE: 'South-east and east' };
    const n = { AS: hour.AS, AN: hour.AN * 2 / 3, AE: hour.AN / 3, SN: hour.SN * 2 / 3, SE: hour.SN / 3 };
    const rows = [];
    Object.keys(NAME).forEach(function (k) {
      const a = ev.pair[k], b = ev.pair[k.charAt(1) + k.charAt(0)], v = (a + b) / 2, ideal = 30 / n[k];
      rows.push({ label: NAME[k] + ' <small>' + n0(n[k]) + ' direct trains an hour each way</small>', value: v, mark: ideal, text: F.n(v, 1) + ' min', color: 'var(--s3)',
        tip: '<b>' + NAME[k] + '</b><br>Average wait for the next direct train: ' + F.n(a, 1) + ' and ' + F.n(b, 1) + ' minutes in the two directions<br><small>With trains exactly evenly spaced: ' + F.n(ideal, 1) + '</small>' });
    });
    PTS.chart.bars($('#tt-pairs'), { rows: rows, max: 16, fmt: function (v) { return F.n(v, 1) + ' min'; } });
    const host = PTS.clear($('#tt-compare')), m1 = function (v) { return F.n(v, 1); };
    const lines = [
      ['Wait for the next train to or from one\u2019s line (Paris passengers)', 'paris_wait'],
      ['Wait for the next direct train (passengers crossing Paris)', 'direct_wait'],
      ['North to east: minutes in Paris, with the change', 'ne_change'],
      ['A passenger who changes to one service: minutes in Paris', 'change_avg']];
    const tb = h('tbody');
    lines.forEach(function (r) { tb.appendChild(h('tr', { class: r[1] === 'paris_wait' ? 'hl' : null }, h('th', { text: r[0] }), h('td', { class: 'num', text: m1(E[r[1]]) }), h('td', { class: 'num', text: Pu ? m1(Pu[r[1]]) : 'not run' }), h('td', { class: 'num', text: R ? m1(R[r[1]]) : 'not run' }))); });
    host.appendChild(h('div', { class: 'tbl-wrap' }, h('table', { class: 'tbl no-stack' }, h('thead', null, h('tr', null, h('th', { text: 'Average minutes' }), h('th', { class: 'num', text: 'Even' }), h('th', { class: 'num', text: 'Timed for changes' }), h('th', { class: 'num', text: 'Untimed' }))), tb)));
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
  const redraw = function () { drawClocks(); drawBoards(); drawMap(); drawPairs(); show(); };
  const scen = [['std', 'About today'], ['full', 'Southern lines full'], ['max', 'Most the stations take']];
  const segs = [];
  const setSc = function (v) { state.sc = v; segs.forEach(function (x) { x.set(v, true); }); redraw(); };
  segs.push(PTS.seg($('#tt-scen-2'), scen, state.sc, setSc, 'Hour shown'));
  bar($('#tt-bar-2'), true);
  drawStops(); redraw();
});
