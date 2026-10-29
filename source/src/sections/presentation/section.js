PTS.section('presentation', function (root) {
  'use strict';
  const D = PTS.data, F = PTS.fmt, h = PTS.h, s = PTS.s;
  const $ = function (sel) { return root.querySelector(sel); };
  const calm = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const add = function (g, tag, attrs) { const e = s(tag, attrs); g.appendChild(e); return e; };
  const pz = $('.pz'); pz.classList.add('pz-js');
  const hm = function (m) { m = Math.round(m); return Math.floor(m / 60) + 'h' + String(m % 60).padStart(2, '0'); };
  const SHOW = D.french.france.show, FP = D.french.params;
  /* Today's time with a change of station in Paris: the model's own estimate where today's way is that change, otherwise the
     through train's time with the model's change of station (x_today minutes from train to train) in place of its two stops (x_proj). */
  const num = function (v) { return parseFloat(String(v).replace(/[\s\u202f\u00a0]/g, '').replace(',', '.')); };     // a number the build wrote, in English or French
  const viaParis = function (p) { return p.today_min; };          // today with a change of station in Paris, from SNCF's timetable (model/paris_crossing.py)

  // ---------------------------------------------------------------- counters and reveal on scroll
  const count = function (el) {
    const to = num(el.getAttribute('data-count')), d = +el.getAttribute('data-d') || 0, pre = el.getAttribute('data-pre') || '', post = el.getAttribute('data-post') || '';
    if (!isFinite(to)) return;
    if (calm) { el.textContent = pre + F.n(to, d) + post; return; }
    const t0 = performance.now(), dur = 1400;
    const step = function (now) { const f = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - f, 3); el.textContent = pre + F.n(to * e, d) + post; if (f < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  };
  const onShow = [];
  const reveal = function (box) {
    if (box.classList.contains('on')) return;
    box.classList.add('on');
    PTS.$$('[data-count]', box).forEach(count);
    onShow.forEach(function (o) { if (box.contains(o.el)) o.fn(); });
  };
  const slides = PTS.$$('.pz-slide', root);
  const dots = $('#pz-dots');
  slides.forEach(function (sl) { dots.appendChild(h('a', { href: '#' + sl.id, 'aria-label': sl.getAttribute('data-dot') }, h('span', { text: sl.getAttribute('data-dot') }))); });
  const dotLinks = PTS.$$('a', dots);
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) reveal(e.target); }); }, { threshold: 0.12 });
    PTS.$$('.pz-in', root).forEach(function (b) { io.observe(b); });
    const io2 = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { const i = slides.indexOf(e.target); dotLinks.forEach(function (a, k) { a.classList.toggle('on', k === i); }); } });
    }, { rootMargin: '-45% 0px -50% 0px' });
    slides.forEach(function (sl) { io2.observe(sl); });
  } else PTS.$$('.pz-in', root).forEach(reveal);
  const whenShown = function (el, fn) { onShow.push({ el: el, fn: fn }); if (el.closest('.pz-in.on')) fn(); };

  /* A row of steps that moves on by itself every `ms`, with a thin bar filling up to the next move, until someone picks a step.
     options: [[value, label], ...]; set(value) draws that step. */
  const auto = function (host, options, ms, set) {
    let i = 0, timer = null, stopped = calm;
    const ctl = PTS.steps(host, options, options[0][0], function (v) { stop(); set(v); });
    const bar = h('i'); host.appendChild(h('span', { class: 'pz-timer', 'aria-hidden': 'true' }, bar));
    const stop = function () { stopped = true; clearTimeout(timer); host.classList.add('stopped'); };
    const arm = function () {
      if (stopped) return;
      bar.style.transition = 'none'; bar.style.width = '0%'; void bar.offsetWidth;
      bar.style.transition = 'width ' + ms + 'ms linear'; bar.style.width = '100%';
      timer = setTimeout(function () {
        if (PTS.current() === 'presentation' && !document.hidden) { i = (i + 1) % options.length; ctl.set(options[i][0], true); set(options[i][0]); }
        arm();
      }, ms);
    };
    set(options[0][0]);
    if (calm) host.classList.add('stopped');
    whenShown(host, arm);
    return { stop: stop, set: function (v) { i = options.map(function (o) { return o[0]; }).indexOf(v); ctl.set(v, true); set(v); } };
  };

  /* A block whose content changes by itself keeps the height of its tallest state, so the page never moves: draw each state once,
     measure, keep the largest as the minimum height, and draw the first state again. Measured again when the width changes. */
  const lockHeight = function (el, states) {
    if (!el) return;
    let w = 0, hmax = 0;
    const grow = function () { const hh = el.offsetHeight; if (hh > hmax) { hmax = hh; el.style.minHeight = hmax + 'px'; } };
    const measure = function () {                         // on a new width, start again from the content's own heights
      el.style.minHeight = ''; hmax = 0;
      states.forEach(function (fn) { fn(); grow(); });
      states[0](); grow();
    };
    const again = function () { if (el.offsetWidth && window.innerWidth !== w) { w = window.innerWidth; measure(); } };     // the window's width, not the block's, which its own content may nudge
    if (window.ResizeObserver) {
      window.addEventListener('resize', function () { clearTimeout(el._lk); el._lk = setTimeout(again, 150); });
      new ResizeObserver(grow).observe(el);              // a state drawn later and taller raises the floor; nothing lowers it
    }
    again(); setTimeout(function () { w = 0; again(); }, 1500);       // measured early, while the block is still off screen
    whenShown(el, function () { if (!w) again(); });
  };

  const defs = function (svg) {
    const d = add(svg, 'defs', {});
    const f = add(d, 'filter', { id: svg.id + '-glow', filterUnits: 'userSpaceOnUse', x: '-10%', y: '-10%', width: '120%', height: '120%' });     // the drawing's own space, so that a level line keeps its glow
    add(f, 'feGaussianBlur', { stdDeviation: 3, result: 'b' });
    const m = add(f, 'feMerge', {}); add(m, 'feMergeNode', { in: 'b' }); add(m, 'feMergeNode', { in: 'SourceGraphic' });
    return 'url(#' + svg.id + '-glow)';
  };
  const ride = function (g, d, o) {                                     // a dot that runs along a path, forever
    const c = add(g, 'circle', { r: o.r || 4, fill: o.c, filter: o.glow, opacity: calm ? 0 : 1 });
    if (calm) return c;
    const am = add(c, 'animateMotion', { dur: o.dur + 's', repeatCount: 'indefinite', begin: (o.begin || 0) + 's', path: d, rotate: 'auto' });
    if (o.back) { am.setAttribute('keyPoints', '0;1;1;0;0'); am.setAttribute('keyTimes', '0;0.4;0.5;0.9;1'); am.setAttribute('calcMode', 'linear'); }
    return c;
  };

  // ---------------------------------------------------------------- journeys across France, under the opening figures
  (function () {
    const host = $('#pz-trips');
    const rows = SHOW.map(function (p) { return { p: p, a: viaParis(p), b: p.project_min }; }).sort(function (x, y) { return (y.a - y.b) - (x.a - x.b) || x.b - y.b; }).slice(0, 4);
    host.appendChild(h('span', { class: 'pz-trips-k', text: 'No change in Paris' }));
    rows.forEach(function (r) {
      host.appendChild(h('div', { class: 'pz-trip' }, h('span', { class: 'pz-trip-n', text: r.p.pair[0] + ' → ' + r.p.pair[1] }),
        h('span', { class: 'pz-trip-t' }, h('s', { text: hm(r.a) }), ' ', h('b', { text: hm(r.b) }))));
    });
  })();
  // ---------------------------------------------------------------- hero: the hexagon of France, joined through the triangle at its centre
  (function () {
    const svg = $('#pz-hero-svg'); svg.setAttribute('viewBox', '0 0 1200 800'); svg.setAttribute('preserveAspectRatio', 'xMaxYMid slice');
    const glow = defs(svg), g = add(svg, 'g', {});
    const C = [905, 268], R = 222, pt = function (p) { return p[0].toFixed(1) + ' ' + p[1].toFixed(1); };
    const V = [-90, -30, 30, 90, 150, 210].map(function (a) { a = a * Math.PI / 180; return [C[0] + R * Math.cos(a), C[1] + R * Math.sin(a)]; });
    const CITY = { Lille: V[0], Strasbourg: V[1], Marseille: V[2], Bordeaux: V[4], Rennes: V[5] };
    const NE = [905, 216], LY = [952, 298], MP = [858, 298];
    add(g, 'path', { d: 'M' + V.map(pt).join(' L') + ' Z', fill: 'rgba(90,162,255,.035)', stroke: 'rgba(143,192,255,.28)', 'stroke-width': 1.5, 'stroke-dasharray': '6 8' });
    const lg = add(svg.querySelector('defs'), 'linearGradient', { id: 'pz-hero-grad', gradientUnits: 'userSpaceOnUse', x1: MP[0], y1: NE[1], x2: LY[0], y2: LY[1] });
    add(lg, 'stop', { offset: '0', 'stop-color': '#5aa2ff' }); add(lg, 'stop', { offset: '1', 'stop-color': '#3fe0a5' });
    // the lines from each corner of the country to its station, and the triangle
    [['Lille', NE], ['Strasbourg', NE], ['Marseille', LY], ['Bordeaux', MP], ['Rennes', MP]].forEach(function (q) { add(g, 'path', { d: 'M' + pt(CITY[q[0]]) + ' L' + pt(q[1]), stroke: 'rgba(143,192,255,.22)', 'stroke-width': 2, fill: 'none' }); });
    [[NE, LY], [LY, MP], [MP, NE]].forEach(function (q) { add(g, 'path', { d: 'M' + pt(q[0]) + ' L' + pt(q[1]), stroke: 'url(#pz-hero-grad)', 'stroke-width': 5, fill: 'none', filter: glow, opacity: .9 }); });
    // trains: from one region to another, through two stations in Paris
    const routes = [
      ['Lille', NE, LY, 'Marseille', '#ff7a59'], ['Marseille', LY, NE, 'Lille', '#ffb199'], ['Rennes', MP, NE, 'Strasbourg', '#a48bff'], ['Strasbourg', NE, MP, 'Bordeaux', '#cbbcff'],
      ['Bordeaux', MP, LY, 'Marseille', '#3fe0a5'], ['Bordeaux', MP, NE, 'Lille', '#5aa2ff'], ['Marseille', LY, MP, 'Rennes', '#9cf0d0'], ['Strasbourg', NE, LY, 'Marseille', '#ffc24b']
    ];
    routes.forEach(function (r, i) { ride(g, 'M' + pt(CITY[r[0]]) + ' L' + pt(r[1]) + ' L' + pt(r[2]) + ' L' + pt(CITY[r[3]]), { c: r[4], glow: glow, r: 5, dur: 8, begin: -i * 1.0 }); });
    [NE, LY, MP].forEach(function (q) {
      add(g, 'circle', { cx: q[0], cy: q[1], r: 20, fill: 'rgba(68,215,255,.12)', stroke: 'rgba(68,215,255,.6)', 'stroke-width': 1.5 });
      add(g, 'circle', { cx: q[0], cy: q[1], r: 7, fill: '#fff', filter: glow });
    });
    Object.keys(CITY).forEach(function (c) {
      const p = CITY[c], right = p[0] > C[0] + 1, left = p[0] < C[0] - 1;
      add(g, 'circle', { cx: p[0], cy: p[1], r: 6, fill: '#cfe6ff' });
      if (p[1] > C[1]) return;                                         // the cities of the lower half would sit under the figures: dots only
      add(g, 'text', { x: p[0] + (right ? 12 : left ? -12 : 0), y: p[1] + (right || left ? 5 : p[1] < C[1] ? -14 : 24), 'text-anchor': right ? 'start' : left ? 'end' : 'middle', class: 'dim', text: c, style: 'font-size: 15px; fill: rgba(207,230,255,.7)' });
    });
  })();


  // ---------------------------------------------------------------- the idea, in three steps
  (function () {
    const svg = $('#pz-idea-svg'), glow = defs(svg);
    add(svg, 'ellipse', { cx: 260, cy: 205, rx: 175, ry: 135, fill: 'rgba(255,255,255,.035)', stroke: 'rgba(255,255,255,.14)', 'stroke-dasharray': '4 6' });
    add(svg, 'text', { x: 260, y: 352, 'text-anchor': 'middle', class: 'dim', text: 'Paris, inside the ring road' });
    const P = { NO: [246, 100], ES: [292, 112], NE: [270, 112], LY: [345, 268], MP: [182, 275], SL: [196, 136], LD: [44, 150], CH: [222, 224] };
    const E = { N: [215, -10], E: [530, 40], S: [530, 410], A: [-10, 410], W: [-10, 120], SW: [60, 410], NW: [160, -10] };
    const L = function (pts) { return 'M' + pts.map(function (p) { return p[0] + ' ' + p[1]; }).join(' L'); };
    const layer = function (cls) { return add(svg, 'g', { class: 'pz-l ' + cls }); };
    const today = layer('l0'), reg = layer('l2'), tri = layer('l1');
    // today: four lines that end
    [[E.N, P.NO, '#ff7a59'], [E.E, P.ES, '#a48bff'], [E.S, P.LY, '#ffc24b'], [E.A, P.MP, '#3fe0a5']].forEach(function (q, i) {
      add(today, 'path', { d: L([q[0], q[1]]), stroke: 'rgba(255,255,255,.3)', 'stroke-width': 3, fill: 'none' });
      ride(today, L([q[0], q[1]]), { c: q[2], glow: glow, r: 5, dur: 5, begin: -i * 1.3, back: true });
    });
    [['Gare du Nord', P.NO, -10, -10, 'end'], ["Gare de l'Est", P.ES, 12, -8, 'start'], ['Gare de Lyon', P.LY, 14, 4, 'start'], ['Montparnasse', P.MP, -14, 4, 'end']].forEach(function (q) {
      add(today, 'rect', { x: q[1][0] - 7, y: q[1][1] - 7, width: 14, height: 14, rx: 3, fill: '#ff7a59' });
      add(today, 'text', { x: q[1][0] + q[2], y: q[1][1] + q[3], 'text-anchor': q[4], class: 'big', text: q[0] });
    });
    add(today, 'text', { x: 260, y: 210, 'text-anchor': 'middle', class: 'dim', text: 'Trains go in, wait, and come back out' });
    // regional: RER G, RER F to La Défense, TER in the TGV tunnels (drawn under the triangle)
    const off = function (pts, dx, dy) { return pts.map(function (p) { return [p[0] + dx, p[1] + dy]; }); };
    const lnG = [E.E, [300, 128], [274, 124], P.CH, [190, 285], E.SW];
    const lnF = [E.NW, [262, 122], [214, 140], P.SL, [150, 112], [96, 108], P.LD, E.W];
    add(reg, 'path', { d: L(lnG), stroke: '#ffc24b', 'stroke-width': 4, fill: 'none', 'stroke-linejoin': 'round' });
    add(reg, 'path', { d: L(lnF), stroke: '#ff6fb1', 'stroke-width': 4, fill: 'none', 'stroke-linejoin': 'round' });
    add(reg, 'path', { d: L(off([E.N, P.NE, P.MP, E.A], -8, 0)), stroke: '#a48bff', 'stroke-width': 2, 'stroke-dasharray': '6 5', fill: 'none' });
    add(reg, 'path', { d: L(off([E.E, P.NE, P.LY, E.S], 8, 0)), stroke: '#a48bff', 'stroke-width': 2, 'stroke-dasharray': '6 5', fill: 'none' });
    ride(reg, L(lnG), { c: '#ffc24b', glow: glow, r: 4, dur: 8 }); ride(reg, L(lnG), { c: '#ffc24b', glow: glow, r: 4, dur: 8, begin: -4 });
    ride(reg, L(lnF), { c: '#ff6fb1', glow: glow, r: 4, dur: 8 }); ride(reg, L(lnF), { c: '#ff6fb1', glow: glow, r: 4, dur: 8, begin: -4 });
    ride(reg, L(off([E.N, P.NE, P.MP, E.A], -8, 0)), { c: '#a48bff', glow: glow, r: 3.5, dur: 7, begin: -2 });
    [[P.SL, 'Saint-Lazare', -10, -12, 'end', '#ff6fb1'], [P.LD, 'La Défense', 0, 22, 'middle', '#ff6fb1'], [P.CH, 'Châtelet', 12, 5, 'start', '#ffc24b']].forEach(function (q) {
      add(reg, 'rect', { x: q[0][0] - 6, y: q[0][1] - 6, width: 12, height: 12, rx: 3, fill: q[5] });
      add(reg, 'text', { x: q[0][0] + q[2], y: q[0][1] + q[3], 'text-anchor': q[4], class: 'big', text: q[1] });
    });
    const badge = function (x, y, txt, c) {
      const w = txt.length * 8.2 + 14;
      add(reg, 'rect', { x: x, y: y - 15, width: w, height: 22, rx: 6, fill: c });
      add(reg, 'text', { x: x + w / 2, y: y + 1, 'text-anchor': 'middle', class: 'big', text: txt, style: 'fill: #06101f; font-size: 14px' });
    };
    badge(120, 30, 'L · H · K → F', '#ff6fb1'); badge(404, 116, 'P · N → G', '#ffc24b'); badge(22, 330, 'TER', '#a48bff');
    // the triangle: lines that go through, 6 minutes a side
    const tlines = [[E.N, P.NE, P.LY, E.S], [E.E, P.NE, P.MP, E.A], [E.A, P.MP, P.LY, E.S]];
    tlines.forEach(function (r) { add(tri, 'path', { d: L(r), stroke: 'rgba(143,192,255,.25)', 'stroke-width': 3, fill: 'none' }); });
    [[P.NE, P.LY], [P.LY, P.MP], [P.MP, P.NE]].forEach(function (q) { add(tri, 'path', { d: L(q), stroke: '#44d7ff', 'stroke-width': 6, fill: 'none', filter: glow }); });
    const trips = [[E.N, P.NE, P.LY, E.S, '#ff7a59'], [E.S, P.LY, P.NE, E.N, '#ffb199'], [E.E, P.NE, P.MP, E.A, '#a48bff'], [E.A, P.MP, P.NE, E.E, '#cbbcff'], [E.A, P.MP, P.LY, E.S, '#3fe0a5'], [E.S, P.LY, P.MP, E.A, '#9cf0d0']];
    trips.forEach(function (r, i) { ride(tri, L(r.slice(0, 4)), { c: r[4], glow: glow, r: 5, dur: 7, begin: -i * 1.15 }); });
    [['Paris Nord-Est', P.NE, 0, -18, 'middle'], ['Gare de Lyon', P.LY, 16, 4, 'start'], ['Montparnasse', P.MP, -16, 4, 'end']].forEach(function (q) {
      add(tri, 'circle', { cx: q[1][0], cy: q[1][1], r: 10, fill: '#fff', filter: glow });
      add(tri, 'text', { x: q[1][0] + q[2], y: q[1][1] + q[3], 'text-anchor': q[4], class: 'big', text: q[0] });
    });
    [[P.NE, P.LY, 14, 0], [P.LY, P.MP, 0, 18], [P.MP, P.NE, -14, 0]].forEach(function (q) {    // the ride on each side
      const x = (q[0][0] + q[1][0]) / 2 + q[2], y = (q[0][1] + q[1][1]) / 2 + q[3], txt = D.model.run_min + ' min';
      add(tri, 'rect', { x: x - 24, y: y - 12, width: 48, height: 22, rx: 11, fill: '#06101f', stroke: '#44d7ff' });
      add(tri, 'text', { x: x, y: y + 4, 'text-anchor': 'middle', class: 'big', text: txt, style: 'fill: #44d7ff; font-size: 13px' });
    });
    const steps = PTS.$$('.pz-step', $('#presentation\\.idea'));
    [today, tri, reg].forEach(function (g) { g.style.transition = 'opacity .7s ease'; });
    auto($('#pz-idea-steps'), [['0', 'Today'], ['1', 'The TGV triangle'], ['2', 'With TER + Transilien']], 4000, function (v) {
      const cur = +v; svg.setAttribute('data-step', cur);
      today.style.opacity = cur === 0 ? 1 : 0; tri.style.opacity = cur >= 1 ? 1 : 0; reg.style.opacity = cur >= 2 ? 1 : 0;
      steps.forEach(function (st) { st.hidden = +st.getAttribute('data-step') !== cur; });
    });
  })();

  // ---------------------------------------------------------------- Gare du Nord, before and after, seen from above at an angle
  (function () {
    const svg = $('#pz-nord-svg'), glow = defs(svg);
    const C = Math.cos(Math.PI / 6), S = 0.5;
    let k = 8.6, ox = 0, oy = 0;
    const P = function (x, y, z) { return [ox + (x - y) * C * k, oy + (x + y) * S * k - (z || 0) * k]; };
    const pts = function (a) { return a.map(function (p) { const q = P(p[0], p[1], p[2]); return q[0].toFixed(1) + ',' + q[1].toFixed(1); }).join(' '); };
    // fit the ground block to the drawing
    const G = { x0: -8, x1: 22, y0: -6, y1: 50, d: 10 };
    (function () {
      const c = [[G.x0, G.y0, 7], [G.x1, G.y0, 0], [G.x0, G.y1, 0], [G.x1, G.y1, -G.d], [G.x0, G.y1, -G.d], [G.x1, G.y0, -G.d]].map(function (p) { return P(p[0], p[1], p[2]); });
      const xs = c.map(function (p) { return p[0]; }), ys = c.map(function (p) { return p[1]; });
      const sc = Math.min(740 / (Math.max.apply(0, xs) - Math.min.apply(0, xs)), 500 / (Math.max.apply(0, ys) - Math.min.apply(0, ys)));
      k = k * sc; const c2 = c.map(function (p) { return [p[0] * sc, p[1] * sc]; });
      ox = 10 - Math.min.apply(0, c2.map(function (p) { return p[0]; })); oy = 10 - Math.min.apply(0, c2.map(function (p) { return p[1]; }));
    })();
    const poly = function (g, a, attrs) { attrs.points = pts(a); return add(g, 'polygon', attrs); };
    const cp = add(svg.querySelector('defs'), 'clipPath', { id: 'pz-nord-clip' });      // trains show only inside the block of ground
    poly(cp, [[G.x0, G.y0, 0], [G.x1, G.y0, 0], [G.x1, G.y0, -G.d], [G.x1, G.y1, -G.d], [G.x0, G.y1, -G.d], [G.x0, G.y1, 9]], {});
    const clip = function (g) { g.setAttribute('clip-path', 'url(#pz-nord-clip)'); return g; };
    const U = (function () { const a = P(0, 1, 0), o = P(0, 0, 0); return [a[0] - o[0], a[1] - o[1]]; })();     // one unit along the tracks, on the drawing
    const box = function (g, x0, x1, y0, y1, z0, z1, col) {             // the three faces one sees: top, +x side, +y side
      poly(g, [[x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1]], { fill: col[1] });
      poly(g, [[x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1]], { fill: col[2] });
      poly(g, [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], { fill: col[0] });
    };
    const lab = function (g, x, y, z, txt, cls, dx, dy) { const p = P(x, y, z); const t = add(g, 'text', { x: p[0] + (dx || 0), y: p[1] + (dy || 0), class: cls || 'big', 'text-anchor': 'middle', text: txt }); return t; };
    const line = function (g, a, b, attrs) { const p = P(a[0], a[1], a[2]), q = P(b[0], b[1], b[2]); attrs.x1 = p[0]; attrs.y1 = p[1]; attrs.x2 = q[0]; attrs.y2 = q[1]; return add(g, 'line', attrs); };
    let seed = 7; const rnd = function () { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };

    const HX0 = 0, HX1 = 11, HY0 = 30, HY1 = 45;                       // the hall: 17 tracks wide, 150 m deep, the front on the street
    const fanX = function (y, t) { const f = Math.max(0, Math.min(1, (HY0 - y) / (HY0 - G.y0))); return HX0 - 5 * f + (HX1 - HX0 + 12 * f) * t; };   // the fan of tracks widens away from the hall

    // the ground, cut open on the two near sides
    const soil = add(svg, 'g', {});
    poly(soil, [[G.x1, G.y0, 0], [G.x1, G.y1, 0], [G.x1, G.y1, -G.d], [G.x1, G.y0, -G.d]], { fill: '#2a2620' });
    poly(soil, [[G.x0, G.y1, 0], [G.x1, G.y1, 0], [G.x1, G.y1, -G.d], [G.x0, G.y1, -G.d]], { fill: '#352f27' });
    [11, 15].forEach(function (x) { const ring = []; for (let a = 0; a <= 24; a++) { const t = a / 24 * 2 * Math.PI; ring.push([x + 1.5 * Math.cos(t), G.y1, -7 + 1.5 * Math.sin(t)]); } poly(soil, ring, { fill: '#0a1222', stroke: 'rgba(68,215,255,.6)', class: 'pz-after' }); });
    [-3, -6].forEach(function (z) { line(soil, [G.x1, G.y0, z], [G.x1, G.y1, z], { stroke: 'rgba(255,255,255,.06)' }); line(soil, [G.x0, G.y1, z], [G.x1, G.y1, z], { stroke: 'rgba(255,255,255,.06)' }); });

    // after: the deep station and its tunnel, seen through the ground
    const deep = add(svg, 'g', { class: 'pz-after' });
    const DZ0 = -8.5, DZ1 = -5.5, DX0 = 8, DX1 = 18, DY0 = 12, DY1 = 42;
    [11, 15].forEach(function (x) {                                     // the tunnels, out to the ring road behind and on under Paris in front
      add(deep, 'path', { d: 'M' + P(x, G.y0, -7)[0] + ' ' + P(x, G.y0, -7)[1] + ' L' + P(x, G.y1, -7)[0] + ' ' + P(x, G.y1, -7)[1], stroke: 'rgba(68,215,255,.4)', 'stroke-width': 14 * k / 8.6, fill: 'none' });
    });
    box(deep, DX0, DX1, DY0, DY1, DZ0, DZ1, ['rgba(68,215,255,.10)', 'rgba(68,215,255,.22)', 'rgba(68,215,255,.30)']);
    for (let i = 0; i < 6; i++) {                                        // six TGV tracks, a train on four of them
      const x = DX0 + 0.9 + i * 1.45;
      line(deep, [x, DY0 + 1, DZ0], [x, DY1 - 1, DZ0], { stroke: 'rgba(255,255,255,.35)', 'stroke-width': 1 });
    }
    const runs = clip(add(deep, 'g', {}));
    [0, 1, 3, 4, 2, 5].forEach(function (i, n) {                        // trains run in, stop and run on through: one way on the even tracks, the other way on the odd ones
      const x = DX0 + 0.9 + i * 1.45, back = i % 2 === 0;
      const tg = add(runs, 'g', { class: 'pz-thru' });
      box(tg, x - 0.45, x + 0.45, DY0 + 6, DY0 + 24, DZ0, DZ0 + 1.2, n % 3 === 2 ? ['#efe2ff', '#a48bff', '#c7b6ff'] : ['#e9f6ff', '#7cc8f0', '#a9dcf5']);
      tg.style.setProperty('--ux', U[0] + 'px'); tg.style.setProperty('--uy', U[1] + 'px');
      tg.style.setProperty('--a', back ? 34 : -44); tg.style.setProperty('--b', back ? -44 : 34);
      if (calm) return;
      tg.style.animation = 'pz-thru 6s cubic-bezier(.45,.05,.55,.95) ' + (-n * 1.05) + 's infinite';
    });
    [[8.6, 33], [9.6, 38], [8.6, 42]].forEach(function (q) {             // the ways down from the hall
      line(deep, [q[0], q[1], 0], [q[0] + 2, q[1] - 3, DZ1], { stroke: '#44d7ff', 'stroke-width': 3, filter: glow, 'stroke-dasharray': '3 3' });
    });

    // the ground's top: town and ballast today, see-through with the project
    const top = add(svg, 'g', {});
    const groundTop = poly(top, [[G.x0, G.y0, 0], [G.x1, G.y0, 0], [G.x1, G.y1, 0], [G.x0, G.y1, 0]], { fill: '#1b2333' });
    poly(top, [[G.x0, HY1 + 0.5, 0.01], [G.x1, HY1 + 0.5, 0.01], [G.x1, G.y1, 0.01], [G.x0, G.y1, 0.01]], { fill: '#2b3447' });   // the street in front
    lab(top, 18, 48, 0, 'Rue de Dunkerque', 'dim', 0, 4);

    // the track field: before
    const before = add(svg, 'g', { class: 'pz-before' });
    poly(before, [[fanX(G.y0, 0), G.y0, 0.02], [fanX(G.y0, 1), G.y0, 0.02], [HX1, HY0, 0.02], [HX1, HY1 - 3, 0.02], [HX0, HY1 - 3, 0.02], [HX0, HY0, 0.02]], { fill: '#3a3530' });
    for (let t = 0; t < 17; t++) {
      const f = (t + 0.5) / 17, a = [fanX(G.y0, f), G.y0, 0.03], b = [fanX(HY0, f), HY0, 0.03], c = [HX0 + (HX1 - HX0) * f, HY1 - 3, 0.03];
      add(before, 'polyline', { points: pts([a, b, c]), stroke: 'rgba(200,190,170,.55)', 'stroke-width': 1.1, fill: 'none' });
    }
    const moving = clip(add(before, 'g', {}));
    [[1, 0], [5, 1], [9, 0], [12, 1], [15, 0]].forEach(function (q, i) {   // trains come in to the buffers, wait, and go back out the way they came
      const t = q[0], f = (t + 0.5) / 17, x = HX0 + (HX1 - HX0) * f, home = [x, HY1 - 3.4, 0.03];
      const tg = add(moving, 'g', {});
      box(tg, x - 0.3, x + 0.3, home[1] - 18, home[1], 0.03, 1.1, ['#f0e7da', '#a2958a', '#c9bcae']);
      if (q[1] || calm) return;                                        // two of them stand at the platform
      const o = P(home[0], home[1], 0), off = function (a) { const p = P(a[0], a[1], 0); return (p[0] - o[0]).toFixed(1) + ' ' + (p[1] - o[1]).toFixed(1); };
      const far = [fanX(G.y0, f), G.y0 - 1], mid = [fanX(HY0, f), HY0];
      add(tg, 'animateMotion', { dur: '8s', begin: (-i * 2.2) + 's', repeatCount: 'indefinite', path: 'M' + off(far) + ' L' + off(mid) + ' L0 0',
        keyPoints: '0;1;1;0;0', keyTimes: '0;0.35;0.55;0.9;1', calcMode: 'spline', keySplines: '.2 .6 .4 1; 0 0 1 1; .6 0 .8 .4; 0 0 1 1' });
    });
    for (let i = 0; i < 70; i++) { const p = P(HX0 + rnd() * (HX1 - HX0), HY1 - 2.6 + rnd() * 2.4, 0.05); add(before, 'circle', { cx: p[0], cy: p[1], r: 1.6, fill: '#ffd2b8' }); }

    // the park and the open hall: after
    const after = add(svg, 'g', { class: 'pz-after' });
    poly(after, [[fanX(G.y0, 0), G.y0, 0.02], [fanX(G.y0, 1), G.y0, 0.02], [HX1, HY0, 0.02], [HX0, HY0, 0.02]], { fill: 'rgba(31,92,64,.82)' });
    add(after, 'path', { d: (function () { let d = ''; for (let i = 0; i <= 20; i++) { const y = HY0 - i * (HY0 - G.y0) / 20, x = fanX(y, 0.5 + 0.28 * Math.sin(i / 2.6)); const p = P(x, y, 0.03); d += (i ? ' L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1); } return d; })(), stroke: '#d9c9a3', 'stroke-width': 2.4, fill: 'none', opacity: .8 });
    poly(after, [[fanX(4, 0.15), 4, 0.03], [fanX(4, 0.4), 4, 0.03], [fanX(12, 0.4), 12, 0.03], [fanX(12, 0.15), 12, 0.03]], { fill: '#3e8fd8', opacity: .75 });   // a pond
    const trees = [];
    for (let i = 0; i < 46; i++) { const y = G.y0 + 1 + rnd() * (HY0 - G.y0 - 2), x = fanX(y, 0.04 + rnd() * 0.92); trees.push([x, y]); }
    trees.sort(function (a, b) { return (a[0] + a[1]) - (b[0] + b[1]); }).forEach(function (q, i) {
      const tg = add(after, 'g', { class: 'pz-tree', style: '--d: ' + (i * 18) + 'ms' });
      const b = P(q[0], q[1], 0), t = P(q[0], q[1], 1.6);
      add(tg, 'line', { x1: b[0], y1: b[1], x2: t[0], y2: t[1], stroke: '#5b4630', 'stroke-width': 2 });
      add(tg, 'circle', { cx: t[0], cy: t[1] - 4, r: 6 + (i % 3) * 2, fill: ['#3fe0a5', '#2fbf87', '#7fe8b8'][i % 3], opacity: .92 });
    });
    poly(after, [[HX0, HY0, 0.04], [HX1, HY0, 0.04], [HX1, HY1, 0.04], [HX0, HY1, 0.04]], { fill: 'rgba(42,53,80,.85)' });      // the hall floor, free for people
    [[8.6, 33], [9.6, 38], [8.6, 42]].forEach(function (q) { poly(after, [[q[0] - 0.8, q[1] - 2.5, 0.05], [q[0] + 0.8, q[1] - 2.5, 0.05], [q[0] + 0.8, q[1], 0.05], [q[0] - 0.8, q[1], 0.05]], { fill: '#0a1222', stroke: '#44d7ff', 'stroke-width': 1.2 }); });
    for (let i = 0; i < 120; i++) { const p = P(HX0 + 0.4 + rnd() * (HX1 - HX0 - 0.8), HY0 + 0.4 + rnd() * (HY1 - HY0 - 0.8), 0.06); add(after, 'circle', { cx: p[0], cy: p[1], r: 1.6, fill: ['#ffd2b8', '#bcd8ff', '#ffe08a', '#f5f5f5'][i % 4], class: 'pz-person', style: '--d: ' + (i % 9) * 0.4 + 's' }); }

    // a few town blocks for scale, then the hall itself: side wall, a glazed front with its arch, a glass roof
    [[-7, -2, 33, 44, 5], [-7, -2, 20, 31, 6]].forEach(function (q) { box(svg, q[0], q[1], q[2], q[3], 0, q[4], ['#3a4660', '#2b3549', '#323d54']); });
    const hall = add(svg, 'g', {});
    poly(hall, [[HX1, HY0, 0], [HX1, HY1, 0], [HX1, HY1, 3.2], [HX1, HY0, 3.2]], { fill: 'rgba(215,205,185,.32)', stroke: 'rgba(240,230,210,.5)' });
    const front = [[HX0, HY1, 0], [HX1, HY1, 0], [HX1, HY1, 3.2]];
    for (let i = 0; i <= 16; i++) { const a = Math.PI * i / 16; front.push([HX0 + (HX1 - HX0) * (0.5 + 0.5 * Math.cos(a)), HY1, 3.2 + 3.2 * Math.sin(a)]); }
    front.push([HX0, HY1, 3.2]);
    poly(hall, front, { fill: 'rgba(225,214,192,.88)', stroke: '#f3e9d6' });
    const arch = []; for (let i = 0; i <= 16; i++) { const a = Math.PI * i / 16; arch.push([HX0 + (HX1 - HX0) * (0.5 + 0.38 * Math.cos(a)), HY1, 2.4 + 2.9 * Math.sin(a)]); }
    poly(hall, arch, { fill: 'rgba(120,180,230,.45)', stroke: '#f3e9d6' });
    for (let i = 0; i <= 8; i++) {                                     // the arched roof, rib by rib, along the hall
      const y = HY0 + (HY1 - HY0) * i / 8, rib = [];
      for (let j = 0; j <= 12; j++) { const a = Math.PI * j / 12; rib.push([HX0 + (HX1 - HX0) * (0.5 + 0.5 * Math.cos(a)), y, 3.2 + 3.2 * Math.sin(a)]); }
      add(hall, 'polyline', { points: pts(rib), fill: 'none', stroke: 'rgba(200,225,255,.45)', 'stroke-width': 1 });
    }
    const ridge = function (t) { const a = Math.PI * t; return [HX0 + (HX1 - HX0) * (0.5 + 0.5 * Math.cos(a)), 3.2 + 3.2 * Math.sin(a)]; };
    for (let j = 0; j <= 12; j += 3) { const r = ridge(j / 12); line(hall, [r[0], HY0, r[1]], [r[0], HY1, r[1]], { stroke: 'rgba(200,225,255,.35)' }); }
    const glass = []; for (let j = 0; j <= 12; j++) { const r = ridge(j / 12); glass.push([r[0], HY0, r[1]]); } for (let j = 12; j >= 0; j--) { const r = ridge(j / 12); glass.push([r[0], HY1, r[1]]); }
    poly(hall, glass, { fill: 'rgba(160,200,240,.12)' });
    // a few town blocks for scale

    // labels
    const lb = add(svg, 'g', { class: 'pz-before' }), la = add(svg, 'g', { class: 'pz-after' });
    lab(lb, 5.5, HY1, 7.6, 'Tracks run into the hall', 'big', 0, -6);
    lab(lb, fanX(5, 0.5), 5, 0, 'Kilometres of tracks', 'big', 0, -10);
    lab(la, 5.5, HY1, 7.6, 'A welcome hall', 'big', 0, -6);
    lab(la, fanX(2, 0.5), 2, 2, 'Parc du Nord', 'big', 0, -18);
    const dl = P(DX1, (DY0 + DY1) / 2, DZ0); add(la, 'text', { x: dl[0] + 12, y: dl[1] + 24, class: 'big', text: 'Deep platforms, Paris Nord-Est', style: 'fill: #9fe6ff' });
    const tl = P(5.5, -6, -7); add(la, 'text', { x: tl[0] + 24, y: tl[1] + 28, class: 'dim', text: 'Tunnels to the ring road', style: 'fill: #9fe6ff' });

    const textSteps = PTS.$$('.pz-step', $('#pz-nord-text'));
    const set = function (v) {
      const a = v === 'after';
      PTS.$$('.pz-before', svg).forEach(function (g) { g.style.opacity = a ? 0 : 1; });
      PTS.$$('.pz-after', svg).forEach(function (g) { g.style.opacity = a ? 1 : 0; });
      groundTop.setAttribute('fill', a ? 'rgba(27,35,51,.4)' : '#1b2333');
      svg.classList.toggle('is-after', a);
      textSteps.forEach(function (st) { st.hidden = (st.getAttribute('data-step') === '1') !== a; });
    };
    PTS.$$('.pz-before, .pz-after', svg).forEach(function (g) { g.style.transition = 'opacity .9s ease'; });
    auto($('#pz-nord-toggle'), [['before', 'Today'], ['after', 'With the project']], 10000, set);     // time to read both texts
  })();
  // ---------------------------------------------------------------- two tunnels side by side, cut open, in the same drawing style
  (function () {
    const svg = $('#pz-tube-svg'), glow = defs(svg);
    const C = Math.cos(Math.PI / 6), S = 0.5, G = { x0: 0, x1: 34, y0: 0, y1: 56, d: 13 };
    let k = 1, ox = 0, oy = 0;
    const P = function (x, y, z) { return [ox + (x - y) * C * k, oy + (x + y) * S * k - (z || 0) * k]; };
    (function () {                                                        // fit the block of ground to the drawing
      const c = [[G.x0, G.y0, 6], [G.x1, G.y0, 0], [G.x0, G.y1, 0], [G.x1, G.y1, -G.d], [G.x0, G.y1, -G.d], [G.x1, G.y0, -G.d]].map(function (p) { return P(p[0], p[1], p[2]); });
      const xs = c.map(function (p) { return p[0]; }), ys = c.map(function (p) { return p[1]; });
      k = Math.min(740 / (Math.max.apply(0, xs) - Math.min.apply(0, xs)), 400 / (Math.max.apply(0, ys) - Math.min.apply(0, ys)));
      const c2 = c.map(function (p) { return [p[0] * k, p[1] * k]; });
      ox = 10 - Math.min.apply(0, c2.map(function (p) { return p[0]; })); oy = 10 - Math.min.apply(0, c2.map(function (p) { return p[1]; }));
    })();
    const pts = function (a) { return a.map(function (p) { const q = P(p[0], p[1], p[2]); return q[0].toFixed(1) + ',' + q[1].toFixed(1); }).join(' '); };
    const poly = function (g, a, attrs) { attrs.points = pts(a); return add(g, 'polygon', attrs); };
    const box = function (g, x0, x1, y0, y1, z0, z1, col) {
      poly(g, [[x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1]], { fill: col[1] });
      poly(g, [[x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1]], { fill: col[2] });
      poly(g, [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], { fill: col[0] });
    };
    const U = (function () { const a = P(0, 1, 0), o = P(0, 0, 0); return [a[0] - o[0], a[1] - o[1]]; })();
    const cp = add(svg.querySelector('defs'), 'clipPath', { id: 'pz-tube-clip' });
    poly(cp, [[G.x0, G.y0, 4], [G.x1, G.y0, 4], [G.x1, G.y0, -G.d], [G.x1, G.y1, -G.d], [G.x0, G.y1, -G.d], [G.x0, G.y1, 4]], {});
    const R = 3.3, ZC = -7;
    const TUBES = [{ x: 10, name: 'TGV + TER', c: '#44d7ff' }, { x: 24, name: 'RER G', c: '#ffc24b' }];
    const ring = function (x, y, r) { const a = []; for (let i = 0; i <= 32; i++) { const t = i / 32 * 2 * Math.PI; a.push([x + r * Math.cos(t), y, ZC + r * Math.sin(t)]); } return a; };

    // the tunnels, seen through the ground
    const n = (function () { const l = Math.hypot(U[0], U[1]); return [-U[1] / l, U[0] / l]; })();
    TUBES.forEach(function (t) {
      const r0 = ring(t.x, G.y0, R).map(function (p) { return P(p[0], p[1], p[2]); });
      let lo = r0[0], hi = r0[0]; r0.forEach(function (p) { const d = p[0] * n[0] + p[1] * n[1]; if (d < lo[0] * n[0] + lo[1] * n[1]) lo = p; if (d > hi[0] * n[0] + hi[1] * n[1]) hi = p; });
      const L = G.y1 - G.y0, sh = function (p) { return (p[0] + U[0] * L).toFixed(1) + ',' + (p[1] + U[1] * L).toFixed(1); };
      add(svg, 'polygon', { points: [lo[0].toFixed(1) + ',' + lo[1].toFixed(1), hi[0].toFixed(1) + ',' + hi[1].toFixed(1), sh(hi), sh(lo)].join(' '), fill: t.c, opacity: .1 });
      for (let y = G.y0; y < G.y1; y += 4) add(svg, 'polyline', { points: pts(ring(t.x, y, R)), fill: 'none', stroke: t.c, 'stroke-opacity': .16 });
      [-1.15, 1.15].forEach(function (dx) { add(svg, 'polyline', { points: pts([[t.x + dx, G.y0, ZC - 2.4], [t.x + dx, G.y1, ZC - 2.4]]), fill: 'none', stroke: 'rgba(255,255,255,.35)' }); });
    });
    // trains: one track each way in each tunnel
    const runs = add(svg, 'g', { 'clip-path': 'url(#pz-tube-clip)' });
    const kinds = { TGV: { len: 17, col: ['#e9f6ff', '#7cc8f0', '#a9dcf5'], dur: 5.2 }, TER: { len: 11, col: ['#efe2ff', '#a48bff', '#c7b6ff'], dur: 6.2 }, RER: { len: 12, col: ['#fff1cf', '#e0a636', '#f2c86a'], dur: 4.6 } };
    [[0, 1, ['TGV', 'TER']], [0, -1, ['TER', 'TGV']], [1, 1, ['RER', 'RER']], [1, -1, ['RER', 'RER']]].forEach(function (q, j) {
      const t = TUBES[q[0]], x = t.x + q[1] * 1.15, away = q[1] > 0;
      q[2].forEach(function (kd, m) {
        const K = kinds[kd], tg = add(runs, 'g', { class: 'pz-run' });
        box(tg, x - 0.6, x + 0.6, 20, 20 + K.len, ZC - 2.4, ZC - 0.6, K.col);
        tg.style.setProperty('--ux', U[0] + 'px'); tg.style.setProperty('--uy', U[1] + 'px');
        tg.style.setProperty('--a', away ? 44 : -46); tg.style.setProperty('--b', away ? -46 : 44);
        if (!calm) tg.style.animation = 'pz-run ' + K.dur + 's linear ' + (-(m * K.dur / 2) - j * 0.7) + 's infinite';
      });
    });
    // the soil, cut open, with the two tunnels in the front face
    poly(svg, [[G.x1, G.y0, 0], [G.x1, G.y1, 0], [G.x1, G.y1, -G.d], [G.x1, G.y0, -G.d]], { fill: '#2a2620', 'fill-opacity': .8 });
    poly(svg, [[G.x0, G.y1, 0], [G.x1, G.y1, 0], [G.x1, G.y1, -G.d], [G.x0, G.y1, -G.d]], { fill: '#352f27', 'fill-opacity': .8 });
    [-4, -9].forEach(function (z) { add(svg, 'polyline', { points: pts([[G.x0, G.y1, z], [G.x1, G.y1, z], [G.x1, G.y0, z]]), fill: 'none', stroke: 'rgba(255,255,255,.06)' }); });
    // the street above: a see-through ground, a few blocks and trees
    poly(svg, [[G.x0, G.y0, 0], [G.x1, G.y0, 0], [G.x1, G.y1, 0], [G.x0, G.y1, 0]], { fill: 'rgba(27,35,51,.55)', stroke: 'rgba(255,255,255,.12)' });
    poly(svg, [[14, G.y0, 0.01], [20, G.y0, 0.01], [20, G.y1, 0.01], [14, G.y1, 0.01]], { fill: 'rgba(60,72,98,.55)' });
    [[0, 6, 2, 12, 4], [0, 6, 16, 26, 5], [28, 34, 2, 10, 4.5], [28, 34, 14, 22, 3.5]].forEach(function (b) { box(svg, b[0], b[1], b[2], b[3], 0, b[4], ['#3a4660', '#2b3549', '#323d54']); });
    let seed = 11; const rnd = function () { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
    for (let i = 0; i < 14; i++) { const x = rnd() < 0.5 ? 12 + rnd() * 1.5 : 21 + rnd() * 1.5, y = 4 + i * 3.6, b = P(x, y, 0), tp = P(x, y, 1.5); add(svg, 'line', { x1: b[0], y1: b[1], x2: tp[0], y2: tp[1], stroke: '#5b4630', 'stroke-width': 2 }); add(svg, 'circle', { cx: tp[0], cy: tp[1] - 3, r: 5 + (i % 3), fill: ['#3fe0a5', '#2fbf87', '#7fe8b8'][i % 3], opacity: .9 }); }
    // the cut faces of the tunnels, and their names
    TUBES.forEach(function (t) {
      poly(svg, ring(t.x, G.y1, R), { fill: 'rgba(6,16,31,.85)', stroke: t.c, 'stroke-width': 2.5, filter: glow });
      [-1.15, 1.15].forEach(function (dx) { const p = P(t.x + dx, G.y1, ZC - 2.4); add(svg, 'rect', { x: p[0] - 5, y: p[1] - 9, width: 10, height: 9, rx: 2, fill: t.c, opacity: .9 }); });
      const p = P(t.x, G.y1, ZC - R - 1.6);
      add(svg, 'text', { x: p[0], y: p[1] + 16, 'text-anchor': 'middle', class: 'big', text: t.name, style: 'fill: ' + t.c });
    });
    const p = P(G.x1, G.y1, -G.d); add(svg, 'text', { x: p[0] + 8, y: p[1] - 6, class: 'dim', text: 'Two tracks in each, one each way' });
  })();

  // ---------------------------------------------------------------- the four parks on the map
  (function () {
    const svg = $('#pz-parks-svg'), glow = defs(svg), G = D.paris_geo, PJ = D.project, V = PJ.view.wide;
    const W = 600, kx = Math.cos(48.86 * Math.PI / 180), sc = W / ((V.lon[1] - V.lon[0]) * kx), H = (V.lat[1] - V.lat[0]) * sc;
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H.toFixed(0));
    const pr = function (ll) { return [(ll[0] - V.lon[0]) * kx * sc, (V.lat[1] - ll[1]) * sc]; };
    const dp = function (a, close) { return a.map(function (p, i) { const q = pr(p); return (i ? 'L' : 'M') + q[0].toFixed(1) + ' ' + q[1].toFixed(1); }).join(' ') + (close ? 'Z' : ''); };
    add(svg, 'path', { d: G.outline.map(function (r) { return dp(r, true); }).join(''), fill: 'rgba(255,255,255,.04)', stroke: 'rgba(255,255,255,.25)', 'stroke-width': 1.2 });
    G.bois.forEach(function (b) { add(svg, 'path', { d: b.r.map(function (r) { return dp(r, true); }).join(''), fill: 'rgba(63,224,165,.10)' }); });
    add(svg, 'path', { d: dp(PJ.seine), fill: 'none', stroke: 'rgba(90,162,255,.45)', 'stroke-width': 5, 'stroke-linecap': 'round' });
    const portal = { 'Gare du Nord': 'Porte de la Chapelle', 'Gare de l’Est': 'Rosa Parks', 'Gare de Lyon': 'Porte de Charenton', 'Montparnasse': 'Porte de Vanves' };
    const NAMES = { 'Gare du Nord': ['Parc du Nord', -1], 'Gare de l’Est': ["Parc de l'Est", 1], 'Gare de Lyon': ['Parc de Lyon', 1], 'Montparnasse': ['Parc Montparnasse', -1] };
    const parks = [];
    PJ.lines.forEach(function (l) {
      if (!portal[l.name]) { add(svg, 'path', { d: dp(l.path), fill: 'none', stroke: 'rgba(255,255,255,.18)', 'stroke-width': 2 }); return; }
      const po = PJ.portals.filter(function (p) { return p.name === portal[l.name]; })[0];
      let best = 0, bd = 1e9; l.path.forEach(function (p, i) { const d = Math.hypot(p[0] - po.at[0], p[1] - po.at[1]); if (d < bd) { bd = d; best = i; } });
      const freed = l.path.slice(0, best).concat([po.at]), rest = [po.at].concat(l.path.slice(best + 1));
      add(svg, 'path', { d: dp(rest), fill: 'none', stroke: 'rgba(255,255,255,.18)', 'stroke-width': 2 });
      const glowp = add(svg, 'path', { d: dp(freed), fill: 'none', stroke: '#3fe0a5', 'stroke-width': 16, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', opacity: .35, filter: glow });
      const core = add(svg, 'path', { d: dp(freed), fill: 'none', stroke: '#3fe0a5', 'stroke-width': 7, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
      parks.push(glowp, core);
      const mid = pr(freed[Math.floor(freed.length / 2)] || freed[0]), side = NAMES[l.name][1];
      add(svg, 'text', { x: mid[0] + side * 18, y: mid[1] - (l.name === 'Gare du Nord' ? 22 : -4), 'text-anchor': side > 0 ? 'start' : 'end', class: 'big', text: NAMES[l.name][0], style: 'fill: #9cf0d0' });
    });
    PJ.stations.forEach(function (st) { const p = pr(st.at), w = st.name === 'Saint-Lazare'; add(svg, 'circle', { cx: p[0], cy: p[1], r: 6, fill: '#fff', filter: glow }); add(svg, 'text', { x: p[0] + (w ? -10 : 10), y: p[1] + (w ? 16 : -8), 'text-anchor': w ? 'end' : 'start', class: 'dim', text: st.short || st.name, style: 'fill: #fff' }); });
    parks.forEach(function (p) { const L = p.getTotalLength ? p.getTotalLength() : 0; if (!L || calm) return; p.style.strokeDasharray = L + ' ' + L; p.style.strokeDashoffset = L; p.style.transition = 'stroke-dashoffset 2.2s cubic-bezier(.2,.7,.2,1)'; });
    whenShown(svg, function () { parks.forEach(function (p) { p.style.strokeDashoffset = 0; }); });
  })();

  // ---------------------------------------------------------------- the parks against the Buttes-Chaumont, side by side
  (function () {
    const host = $('#pz-bc-row'), n = num(host.getAttribute('data-n'));
    // a drawing of the park's outline, its lake and the island with the Sibyl's temple
    const shape = 'M6 30 C4 20 10 12 20 10 C28 3 40 4 46 10 C54 12 60 18 57 26 C60 34 52 40 44 39 C36 44 24 43 18 38 C10 39 5 36 6 30 Z';
    for (let i = 0; i < Math.ceil(n); i++) {
      const part = Math.min(1, n - i), svg = add(host, 'svg', { viewBox: '0 0 64 48', class: 'pz-bc-i', style: '--d: ' + (i * 160) + 'ms; width: ' + (part * 64) + 'px', preserveAspectRatio: 'xMinYMid slice' });
      add(svg, 'path', { d: shape, fill: '#2fbf87', stroke: '#3fe0a5', 'stroke-width': 1.5 });
      add(svg, 'path', { d: 'M24 26 C26 20 36 19 40 24 C43 29 36 33 30 32 C26 32 23 30 24 26 Z', fill: '#3e8fd8', opacity: .8 });
      add(svg, 'circle', { cx: 34, cy: 25, r: 3, fill: '#e9f6ff' });
    }
  })();

  // ---------------------------------------------------------------- across France: with a change of station in Paris, and through
  (function () {
    const CITY = { Lille: [3.06, 50.63], Bordeaux: [-0.58, 44.84], Strasbourg: [7.75, 48.58], Lyon: [4.84, 45.76], Marseille: [5.37, 43.3], Rennes: [-1.68, 48.11], Nantes: [-1.55, 47.22], Dijon: [5.04, 47.32], Paris: [2.35, 48.86] };
    const svg = $('#pz-fr-map'), glow = defs(svg), kx = Math.cos(47 * Math.PI / 180);
    const pr = function (c) { return [40 + (c[0] + 2.2) * kx * 46, 30 + (51.2 - c[1]) * 58]; };
    const P0 = pr(CITY.Paris);
    const pairs = SHOW.filter(function (p) { return CITY[p.pair[0]] && CITY[p.pair[1]]; }).map(function (p) { return Object.assign({ via: viaParis(p) }, p); }).sort(function (a, b) { return (b.via - b.project_min) - (a.via - a.project_min) || a.project_min - b.project_min; });
    const g = add(svg, 'g', {});
    const arcs = pairs.map(function (p) {
      const a = pr(CITY[p.pair[0]]), b = pr(CITY[p.pair[1]]);
      const bend = function (u, v) { return [(u[0] + v[0]) / 2 + (v[1] - u[1]) * 0.12, (u[1] + v[1]) / 2 - (v[0] - u[0]) * 0.12]; };
      const c1 = bend(a, P0), c2 = bend(P0, b);
      return { p: p, el: add(g, 'path', { d: 'M' + a[0] + ' ' + a[1] + ' Q' + c1[0] + ' ' + c1[1] + ' ' + P0[0] + ' ' + P0[1] + ' Q' + c2[0] + ' ' + c2[1] + ' ' + b[0] + ' ' + b[1], fill: 'none', 'stroke-width': 2.5, 'stroke-linecap': 'round' }) };
    });
    const hub = add(svg, 'circle', { cx: P0[0], cy: P0[1], r: 12, fill: 'rgba(68,215,255,.2)', stroke: '#44d7ff' });
    const hubX = add(svg, 'text', { x: P0[0], y: P0[1] + 5, 'text-anchor': 'middle', class: 'big', text: '⇄', style: 'fill: #ff7a59; font-size: 15px' });
    add(svg, 'text', { x: P0[0] + 16, y: P0[1] - 12, class: 'big', text: 'Paris' });
    Object.keys(CITY).forEach(function (c) { if (c === 'Paris') return; const q = pr(CITY[c]); add(svg, 'circle', { cx: q[0], cy: q[1], r: 5, fill: '#fff' }); add(svg, 'text', { x: q[0] + (q[0] < P0[0] ? -9 : 9), y: q[1] + 4, 'text-anchor': q[0] < P0[0] ? 'end' : 'start', text: c, style: 'fill: #fff' }); });
    const host = $('#pz-fr-bars'), max = Math.max.apply(0, pairs.map(function (p) { return p.via; }));
    const withDirect = pairs.filter(function (p) { return p.direct_day >= 0.5; }).map(function (p) { return p.project_direct_day / p.direct_day; }).sort(function (a, b) { return a - b; });
    const mid = withDirect.length % 2 ? withDirect[(withDirect.length - 1) / 2] : (withDirect[withDirect.length / 2 - 1] + withDirect[withDirect.length / 2]) / 2;
    const MT = D.french.more_trains;
    const fresh = pairs.filter(function (p) { return p.direct_day < 0.5 && p.project_direct_day >= 0.5; }).length;
    const saved = pairs.map(function (p) { return p.via - p.project_min; });
    $('#pz-fr-cards').append(h('div', { class: 'pz-frq-in' },
      h('div', null, h('b', { text: '×' + F.n(mid, 1) }), h('span', { text: 'direct trains between these cities, with the same number of trains as today' })),
      h('div', null, h('b', { text: F.n(fresh, 0) }), h('span', { text: 'new direct links, with no more trains' })),
      h('div', { class: 'more' }, h('b', { text: '1 direct an hour' }), h('span', { text: 'possible between every TGV city in France, by buying more trainsets. The limit is no longer the infrastructure.' })),
      h('div', null, h('b', { text: F.n(Math.min.apply(0, saved), 0) + ' to ' + F.n(Math.max.apply(0, saved), 0) + ' min' }), h('span', { text: 'less on each journey, no change in Paris' }))));
    host.appendChild(h('div', { class: 'pz-key' }, h('span', null, h('i', { style: 'background: rgba(255,122,89,.75)' }), 'Today, with a change of station in Paris'), h('span', null, h('i', { style: 'background: linear-gradient(90deg,#44d7ff,#3fe0a5)' }), 'Through train')));
    const head = h('b', { text: 'Today, with a change' });
    host.appendChild(h('div', { class: 'pz-bar pz-bar-h' }, h('span'), h('span'), head, h('em', { text: 'Direct trains a day' })));
    const rows = pairs.map(function (p, i) {
      const t = h('i', { class: 't' }), q = h('i', { class: 'p' }), b = h('b'), f = h('em');
      const row = h('div', { class: 'pz-bar' }, h('span', { text: p.pair[0] + ' → ' + p.pair[1] }), h('div', { class: 'pz-track' }, t, q), b, f);
      row.addEventListener('pointerenter', function () { hi(i); }); row.addEventListener('pointerleave', function () { hi(-1); });
      host.appendChild(row);
      return { row: row, t: t, q: q, b: b, f: f, p: p };
    });
    const hi = function (i) { arcs.forEach(function (a, k) { a.el.style.opacity = i < 0 || k === i ? 1 : 0.15; }); rows.forEach(function (r, k) { r.row.classList.toggle('hi', k === i); }); };
    const frSet = function (v) {
      const now = v === 'today', more = v === 'more';
      arcs.forEach(function (a) { a.el.setAttribute('stroke', now ? '#ff7a59' : more ? '#3fe0a5' : '#44d7ff'); a.el.setAttribute('stroke-width', more ? 4 : 2.5); a.el.setAttribute('filter', now ? '' : glow); a.el.setAttribute('stroke-dasharray', now ? '5 6' : ''); });
      hub.setAttribute('fill', now ? 'rgba(255,122,89,.25)' : 'rgba(68,215,255,.2)'); hub.setAttribute('stroke', now ? '#ff7a59' : '#44d7ff'); hubX.style.opacity = now ? 1 : 0;
      rows.forEach(function (r) {
        r.t.style.width = (r.p.via / max * 100) + '%';
        r.q.style.width = now ? '0%' : (r.p.project_min / max * 100) + '%';
        r.b.innerHTML = now ? hm(r.p.via) : hm(r.p.project_min) + ' <small>-' + F.n(r.p.via - r.p.project_min, 0) + ' min</small>';
        r.b.style.color = now ? '#fff' : '#3fe0a5';
        const n = more ? r.p.more_direct_day : r.p.project_direct_day;
        r.f.innerHTML = now ? '<b class="today">' + F.n(r.p.direct_day, 0) + '</b>' : '<s>' + F.n(r.p.direct_day, 0) + '</s> <b>' + F.n(n, 0) + '</b> <small>(+' + F.n(n - r.p.direct_day, 0) + ')</small>';
        head.textContent = now ? 'Today, with a change' : 'With the project';
      });
    };
    auto($('#pz-fr-toggle'), [['today', 'Today'], ['project', 'With the project'], ['more', 'With the project and more trains']], 5000, frSet);
    lockHeight($('#pz-fr-bars'), [function () { frSet('today'); }, function () { frSet('project'); }, function () { frSet('more'); }]);
  })();

  // ---------------------------------------------------------------- the whole region: TER to both airports and to the TGVs, today and through
  (function () {
    const A = D.airports, G = D.paris_geo, PJ = D.project, svg = $('#pz-rg-map'), glow = defs(svg);
    const V = { lon: [2.06, 2.73], lat: [48.68, 49.06] }, W = 520, kx = Math.cos(48.86 * Math.PI / 180), sc = W / ((V.lon[1] - V.lon[0]) * kx);
    const pr = function (ll) { return [(ll[0] - V.lon[0]) * kx * sc, (V.lat[1] - ll[1]) * sc]; };
    const L = function (a) { return a.map(function (p, i) { const q = pr(p); return (i ? 'L' : 'M') + q[0].toFixed(1) + ' ' + q[1].toFixed(1); }).join(' '); };
    const st = {}; PJ.stations.forEach(function (x) { st[x.short || x.name] = x.at; });
    const NE = st['Nord-Est'], LY = st['Gare de Lyon'], MP = st['Montparnasse'];
    const T = { Nord: [2.3551, 48.8802], Est: [2.3584, 48.8767], Lyon: [2.3735, 48.8449], Bercy: [2.3813, 48.839], Montparnasse: [2.3205, 48.8412] };
    const CDG = [2.5699, 49.004], ORLY = [2.3611, 48.7289];
    const EDGE = { north: [2.40, 49.06], east: [2.73, 48.94], burgundy: [2.73, 48.72], atlantic: [2.06, 48.71] };
    const NAME_AT = { north: [2.40, 49.06], east: [2.71, 48.905], burgundy: [2.66, 48.705], atlantic: [2.06, 48.71] };     // where each direction's name sits, inside the map
    const portal = {}; PJ.portals.forEach(function (x) { portal[x.name] = x.at; });
    const WAY = {                                                           // each direction: from the edge of the map to today's terminal, and on through the plan's two stations
      north: { out: [EDGE.north, portal['Porte de la Chapelle']], today: T.Nord, plan: [NE, MP] },
      east: { out: [EDGE.east, portal['Rosa Parks']], today: T.Est, plan: [NE, LY] },
      burgundy: { out: [EDGE.burgundy, portal['Porte de Charenton']], today: T.Bercy, plan: [LY, NE] },
      atlantic: { out: [EDGE.atlantic, portal['Porte de Vanves']], today: T.Montparnasse, plan: [MP, NE] }
    };
    add(svg, 'path', { d: G.outline.map(function (r) { return L(r) + 'Z'; }).join(''), fill: 'rgba(255,255,255,.05)', stroke: 'rgba(255,255,255,.25)', 'stroke-width': 1 });
    add(svg, 'path', { d: L(PJ.seine), fill: 'none', stroke: 'rgba(90,162,255,.4)', 'stroke-width': 3, 'stroke-linecap': 'round' });
    // the two airport lines, the same in both views
    const lines = [[NE, [2.39, 48.92], [2.50, 48.97], CDG], [LY, [2.37, 48.80], ORLY]];
    add(svg, 'path', { d: L(lines[0]), fill: 'none', stroke: '#5aa2ff', 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
    add(svg, 'path', { d: L(lines[1]), fill: 'none', stroke: '#ffc24b', 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
    ride(svg, L(lines[0]), { c: '#5aa2ff', glow: glow, r: 4, dur: 7 }); ride(svg, L(lines[1]), { c: '#ffc24b', glow: glow, r: 4, dur: 6, begin: -2 });
    const today = add(svg, 'g', { style: 'transition: opacity .6s' }), plan = add(svg, 'g', { style: 'transition: opacity .6s' });
    Object.keys(WAY).forEach(function (k, i) {                               // the TER lines from outside: grey to the portal in both views
      const w = WAY[k];
      add(svg, 'path', { d: L(w.out), fill: 'none', stroke: 'rgba(164,139,255,.5)', 'stroke-width': 3, 'stroke-linecap': 'round' });
      const dt = L(w.out.concat([w.today])), dp = L(w.out.concat(w.plan));
      add(today, 'path', { d: dt, fill: 'none', stroke: '#a48bff', 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
      add(plan, 'path', { d: dp, fill: 'none', stroke: '#a48bff', 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', filter: glow });
      ride(today, dt, { c: '#a48bff', glow: glow, r: 4.5, dur: 6, begin: -i * 1.5, back: true });
      ride(plan, dp, { c: '#a48bff', glow: glow, r: 4.5, dur: 7, begin: -i * 1.7 }); ride(plan, dp, { c: '#a48bff', glow: glow, r: 4.5, dur: 7, begin: -i * 1.7 - 3.5 });
    });
    // today: the metro across Paris between the terminals and the two airport lines
    [[T.Montparnasse, T.Nord], [T.Montparnasse, T.Lyon], [T.Bercy, T.Nord], [T.Est, T.Lyon]].forEach(function (q) {
      add(today, 'path', { d: L(q), fill: 'none', stroke: '#ff7a59', 'stroke-width': 2, 'stroke-dasharray': '4 5', opacity: .9 });
    });
    [T.Nord, T.Est, T.Lyon, T.Bercy, T.Montparnasse].forEach(function (q) { const c = pr(q); add(today, 'circle', { cx: c[0], cy: c[1], r: 4.5, fill: '#fff' }); });
    const tl = pr([2.245, 48.868]); add(today, 'text', { x: tl[0], y: tl[1], 'text-anchor': 'end', class: 'dim', text: 'Metro across Paris', style: 'fill: #ff9b80; font-size: 11px' });
    // the plan: the triangle lit
    [[NE, LY], [LY, MP], [MP, NE]].forEach(function (q) { add(plan, 'path', { d: L(q), stroke: '#44d7ff', 'stroke-width': 4, fill: 'none', filter: glow }); });
    [NE, LY, MP].forEach(function (q) { const c = pr(q); add(plan, 'circle', { cx: c[0], cy: c[1], r: 7, fill: 'rgba(68,215,255,.15)', stroke: 'rgba(68,215,255,.7)' }); add(plan, 'circle', { cx: c[0], cy: c[1], r: 3.5, fill: '#fff', filter: glow }); });
    // names
    const label = function (ll, text, dx, dy, anchor, cls, style) { const c = pr(ll); add(svg, 'text', { x: c[0] + dx, y: c[1] + dy, 'text-anchor': anchor || 'start', class: cls || 'dim', text: text, style: style || '' }); };
    [[CDG, 'Roissy-CDG', 'end', -10, -8], [ORLY, 'Orly', 'start', 10, 4]].forEach(function (q) { const c = pr(q[0]); add(svg, 'circle', { cx: c[0], cy: c[1], r: 7, fill: '#fff', filter: glow }); add(svg, 'path', { d: 'M' + (c[0] - 4) + ' ' + c[1] + ' l4 -3 l4 3 l-4 1 z', fill: '#0b1530' }); label(q[0], q[1], q[3], q[4], q[2], 'big'); });
    label(NE, 'Nord-Est', 8, -6, 'start', 'dim', 'fill: #fff'); label(LY, 'Gare de Lyon', 10, 12, 'start', 'dim', 'fill: #fff'); label(MP, 'Montparnasse', -8, 12, 'end', 'dim', 'fill: #fff');
    label([2.46, 48.955], 'RER B', 8, 0, 'start', 'dim', 'fill: #5aa2ff'); label([2.37, 48.79], 'Line 14', 8, 0, 'start', 'dim', 'fill: #ffc24b');
    A.rows.forEach(function (r) {                                           // the towns, at the edge each direction comes from
      const e = NAME_AT[r.id], c = pr(e), top = e[1] > 49, right = e[0] > 2.5;
      add(svg, 'text', { x: c[0] + (top ? 8 : right ? -6 : 6), y: c[1] + (top ? 14 : right ? -4 : -10), 'text-anchor': top ? 'start' : right ? 'end' : 'start', class: 'big', text: r.name, style: 'fill: #cbbcff' });
      add(svg, 'text', { x: c[0] + (top ? 8 : right ? -6 : 6), y: c[1] + (top ? 28 : right ? 10 : 4), 'text-anchor': top ? 'start' : right ? 'end' : 'start', class: 'dim', text: r.towns, style: 'font-size: 11px' });
    });
    // the bars: each direction to each airport
    const host = $('#pz-rg-bars'), AP = { cdg: 'Roissy', orly: 'Orly' };
    host.appendChild(h('div', { class: 'pz-key' }, h('span', null, h('i', { style: 'background: rgba(255,122,89,.75)' }), 'Today, from the TER’s first Paris station'), h('span', null, h('i', { style: 'background: linear-gradient(90deg,#44d7ff,#3fe0a5)' }), 'With the project, from the same station')));
    const head = h('b', { text: 'Today, at the terminal' });
    host.appendChild(h('div', { class: 'pz-bar pz-bar-h' }, h('span'), h('span'), head));
    const rows = [];
    ['cdg', 'orly'].forEach(function (ap) {
      A.rows.forEach(function (r) {
        const t = h('i', { class: 't' }), q = h('i', { class: 'p' }), b = h('b');
        host.appendChild(h('div', { class: 'pz-bar' }, h('span', { text: r.name + ' → ' + AP[ap] }), h('div', { class: 'pz-track' }, t, q), b));
        rows.push({ t: t, q: q, b: b, x: r[ap] });
      });
    });
    const max = Math.max.apply(0, rows.map(function (r) { return r.x.today; }));
    const set = function (v) {
      const now = v === 'today';
      today.style.opacity = now ? 1 : 0; plan.style.opacity = now ? 0 : 1;
      rows.forEach(function (r) {
        r.t.style.width = (r.x.today / max * 100) + '%'; r.q.style.width = now ? '0%' : (r.x.plan / max * 100) + '%';
        r.b.innerHTML = now ? F.n(r.x.today, 0) : F.n(r.x.plan, 0) + ' <small>-' + F.n(r.x.today - r.x.plan, 0) + ' min</small>';
        r.b.style.color = now ? '#fff' : '#3fe0a5';
      });
      head.textContent = now ? 'Today, at the terminal' : 'With the project, through';
    };
    auto($('#pz-rg-toggle'), [['today', 'Today'], ['project', 'With the project']], 5000, set);
    lockHeight(host, [function () { set('today'); }, function () { set('project'); }]);
  })();

  // ---------------------------------------------------------------- the running total, in today's money
  (function () {
    const svg = $('#pz-curve-svg'), T = D.french.timeline, W = 520, H = 300, m = { l: 44, r: 14, t: 40, b: 28 };
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    const yrs = T.years, v = T.cum_npv, last = yrs.length - 1;
    const lo = Math.min.apply(0, v), hi = Math.max.apply(0, v);
    const X = function (y) { return m.l + (y - yrs[0]) / (yrs[last] - yrs[0]) * (W - m.l - m.r); }, Y = function (x) { return m.t + (hi - x) / (hi - lo) * (H - m.t - m.b); };
    const glow = defs(svg);
    const lg = add(svg.querySelector('defs'), 'linearGradient', { id: 'pz-curve-grad', x1: 0, y1: 0, x2: 1, y2: 0 });
    add(lg, 'stop', { offset: '0', 'stop-color': '#ff7a59' }); add(lg, 'stop', { offset: ((T.break_even - yrs[0]) / (yrs[last] - yrs[0])).toFixed(3), 'stop-color': '#ffc24b' }); add(lg, 'stop', { offset: '1', 'stop-color': '#3fe0a5' });
    const step = Math.ceil((hi - lo) / 4 / 10) * 10;
    for (let t = Math.ceil(lo / step) * step; t <= hi; t += step) { add(svg, 'line', { x1: m.l, x2: W - m.r, y1: Y(t), y2: Y(t), stroke: t === 0 ? 'rgba(255,255,255,.45)' : 'rgba(255,255,255,.08)' }); add(svg, 'text', { x: m.l - 6, y: Y(t) + 4, 'text-anchor': 'end', class: 'dim', text: (t > 0 ? '+' : '') + t }); }
    [yrs[0], 2050, 2075, 2100, 2125, yrs[last]].filter(function (y, i, a) { return a.indexOf(y) === i && y <= yrs[last]; }).forEach(function (y) { add(svg, 'text', { x: X(y), y: H - 8, 'text-anchor': 'middle', class: 'dim', text: y }); });
    const d = yrs.map(function (y, i) { return (i ? 'L' : 'M') + X(y).toFixed(1) + ' ' + Y(v[i]).toFixed(1); }).join(' ');
    add(svg, 'path', { d: d + ' L' + X(yrs[last]) + ' ' + Y(0) + ' L' + X(yrs[0]) + ' ' + Y(0) + 'Z', fill: 'rgba(68,215,255,.07)' });
    const line = add(svg, 'path', { d: d, fill: 'none', stroke: 'url(#pz-curve-grad)', 'stroke-width': 3.5, filter: glow, 'stroke-linejoin': 'round' });
    const be = add(svg, 'g', { opacity: calm ? 1 : 0, style: 'transition: opacity .6s ease 1.6s' });
    add(be, 'circle', { cx: X(T.break_even), cy: Y(0), r: 6, fill: '#ffc24b', filter: glow });
    add(be, 'text', { x: X(T.break_even), y: Y(0) - 14, 'text-anchor': 'middle', class: 'big', text: 'Paid back, ' + T.break_even });
    add(be, 'text', { x: X(yrs[last]) - 4, y: Y(v[last]) - 12, 'text-anchor': 'end', class: 'big', text: '+' + F.bn(D.french.cases.central.npv, 1), style: 'fill: #3fe0a5' });
    if (!calm) { const L = line.getTotalLength(); line.style.strokeDasharray = L + ' ' + L; line.style.strokeDashoffset = L; line.style.transition = 'stroke-dashoffset 2s cubic-bezier(.3,.6,.2,1)'; }
    whenShown(svg, function () { line.style.strokeDashoffset = 0; be.setAttribute('opacity', 1); });
  })();

  // ---------------------------------------------------------------- figures of the report, shown here as they are
  const lend = function (section, host, nodes) {
    if (!PTS.ensure(section)) return [];
    nodes = nodes.filter(Boolean);
    PTS.borrow('presentation', host, nodes);
    return nodes;
  };
  const byId = function (id) { return document.getElementById(id); };
  const kids = function (id, skip) { const b = byId(id); return b ? Array.prototype.filter.call(b.children, function (c) { return !c.matches(skip); }) : []; };

  // the hour: the timetable's own map, clocks, legend and controls, laid out for this page
  (function () {
    if (!PTS.ensure('timetable')) return;
    const bar = byId('tt-bar-2'), parts = bar ? Array.prototype.slice.call(bar.children) : [];
    const play = parts.filter(function (x) { return x.tagName === 'BUTTON'; })[0], speed = parts.filter(function (x) { return x.classList.contains('tt-speed'); })[0];
    const scrub = parts.filter(function (x) { return x !== play && x !== speed; })[0];
    lend('timetable', $('#pz-tt-scrub'), [scrub]);
    lend('timetable', $('#pz-tt-legend'), [byId('tt-legend-map')]);
    lend('timetable', $('#pz-tt-ctl'), [play, byId('tt-layer'), speed]);
    lend('timetable', $('#pz-tt-map'), [byId('tt-map')]);
    lend('timetable', $('#pz-tt-clocks'), [byId('tt-clocks')]);
    const host = $('#pz-hour-host');
    if (play) {                                                           // play and pause as one symbol
      const mark = function () { host.classList.toggle('is-playing', /pause/i.test(play.textContent)); play.setAttribute('aria-label', play.textContent.trim()); };
      new MutationObserver(mark).observe(play, { childList: true, characterData: true, subtree: true }); mark();
    }
    whenShown(host, function () {
      const full = byId('tt-scen-2') && byId('tt-scen-2').querySelector('button[data-v="max"]');   // the most the stations can take
      if (full && full.getAttribute('aria-pressed') !== 'true') full.click();
      if (!calm && play && !/pause/i.test(play.textContent)) play.click();     // 'Pause' is the same word in French
    });
  })();

  // reaching the station: the map and the chart by arrondissement; the map moves on by itself from today to the project
  (function () {
    lend('access', $('#pz-access-host'), kids('access.map', 'h2, h3, p'));
    const c = byId('access-arr-chart'); lend('access', $('#pz-access-host-2'), [c && c.closest('figure')]);
    const tiles = ['today', 'project', 'saved'].map(function (v) { return byId('access-t-' + v); });
    const host = $('#pz-acc-toggle'); if (!tiles[0] || calm) return;
    const bar = h('i'); host.appendChild(h('span', { class: 'pz-timer', 'aria-hidden': 'true' }, bar));
    let i = 0, timer = null, stopped = false;
    const stop = function () { stopped = true; clearTimeout(timer); host.classList.add('stopped'); };
    tiles.forEach(function (t) { t.addEventListener('click', function (e) { if (e.isTrusted) stop(); }); });
    const arm = function () {
      if (stopped) return;
      bar.style.transition = 'none'; bar.style.width = '0%'; void bar.offsetWidth; bar.style.transition = 'width 4000ms linear'; bar.style.width = '100%';
      timer = setTimeout(function () { if (PTS.current() === 'presentation' && !document.hidden) { i = (i + 1) % tiles.length; tiles[i].click(); } arm(); }, 4000);
    };
    lockHeight($('#pz-access-host'), tiles.map(function (t) { return function () { t.click(); }; }));
    whenShown(host, function () { tiles[0].click(); arm(); });
  })();

  // the works: the timeline's first figure, today, during the works and after
  lend('works', $('#pz-works-host'), [(function () { const c = byId('works-ba'); return c && c.closest('figure'); })()]);
  lockHeight($('#pz-works-host'), PTS.$$('#works-ba-controls button', document).map(function (b) { return function () { b.click(); }; }));
  whenShown($('#pz-works-host'), function () {
    const bs = PTS.$$('#works-ba-controls button', document);
    if (calm || bs.length < 2) return;
    bs.slice(1).forEach(function (b, i) { setTimeout(function () { if (PTS.current() === 'presentation') b.click(); }, 2200 * (i + 1)); });
  });
});
