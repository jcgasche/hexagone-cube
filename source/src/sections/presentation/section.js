PTS.section('presentation', function (root) {
  'use strict';
  const D = PTS.data, F = PTS.fmt, h = PTS.h, s = PTS.s;
  const $ = function (sel) { return root.querySelector(sel); };
  const calm = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const add = function (g, tag, attrs) { const e = s(tag, attrs); g.appendChild(e); return e; };
  const pz = $('.pz'); pz.classList.add('pz-js');
  const hm = function (m) { m = Math.round(m); return Math.floor(m / 60) + 'h' + String(m % 60).padStart(2, '0'); };
  const SHOW = D.french.france.show;
  const pairOf = function (a, b) { return SHOW.filter(function (p) { return (p.pair[0] === a && p.pair[1] === b) || (p.pair[0] === b && p.pair[1] === a); })[0]; };

  // ---------------------------------------------------------------- journey times written into the text
  PTS.$$('[data-pair]', root).forEach(function (el) {
    const q = el.getAttribute('data-pair').split(','), p = pairOf(q[0], q[1]); if (!p) return;
    el.textContent = hm(el.getAttribute('data-what') === 'today' ? p.today_min : p.project_min);
  });

  // ---------------------------------------------------------------- counters and reveal on scroll
  const count = function (el) {
    const to = parseFloat(el.getAttribute('data-count')), d = +el.getAttribute('data-d') || 0, pre = el.getAttribute('data-pre') || '', post = el.getAttribute('data-post') || '';
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

  const defs = function (svg) {
    const d = add(svg, 'defs', {});
    const f = add(d, 'filter', { id: svg.id + '-glow', x: '-50%', y: '-50%', width: '200%', height: '200%' });
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

  // ---------------------------------------------------------------- hero: the triangle with trains running through
  (function () {
    const svg = $('#pz-hero-svg'); svg.setAttribute('viewBox', '0 0 1200 800'); svg.setAttribute('preserveAspectRatio', 'xMaxYMid slice');
    const glow = defs(svg), g = add(svg, 'g', { transform: 'translate(520 40)' });
    const NE = [470, 110], LY = [590, 300], MP = [330, 320];
    const pt = function (p) { return p[0] + ' ' + p[1]; };
    const ends = { N: [420, -60], E: [760, -20], S: [760, 560], A: [80, 620] };
    // the lines coming in, and the triangle
    [[ends.N, NE], [ends.E, NE], [ends.S, LY], [ends.A, MP]].forEach(function (q) { add(g, 'path', { d: 'M' + pt(q[0]) + ' L' + pt(q[1]), stroke: 'rgba(143,192,255,.22)', 'stroke-width': 2, fill: 'none' }); });
    [[NE, LY], [LY, MP], [MP, NE]].forEach(function (q) { add(g, 'path', { d: 'M' + pt(q[0]) + ' L' + pt(q[1]), stroke: 'url(#pz-hero-grad)', 'stroke-width': 5, fill: 'none', filter: glow, opacity: .85 }); });
    const lg = add(svg.querySelector('defs'), 'linearGradient', { id: 'pz-hero-grad', x1: 0, y1: 0, x2: 1, y2: 1 });
    add(lg, 'stop', { offset: '0', 'stop-color': '#5aa2ff' }); add(lg, 'stop', { offset: '1', 'stop-color': '#3fe0a5' });
    // trains: in from one line, two stops, out on another
    const routes = [
      [ends.N, NE, LY, ends.S, '#ff7a59'], [ends.S, LY, NE, ends.N, '#ffb199'], [ends.A, MP, NE, ends.E, '#a48bff'], [ends.E, NE, MP, ends.A, '#cbbcff'],
      [ends.A, MP, LY, ends.S, '#3fe0a5'], [ends.S, LY, MP, ends.A, '#9cf0d0'], [ends.N, NE, MP, ends.A, '#5aa2ff'], [ends.E, NE, LY, ends.S, '#ffc24b']
    ];
    routes.forEach(function (r, i) { ride(g, 'M' + pt(r[0]) + ' L' + pt(r[1]) + ' L' + pt(r[2]) + ' L' + pt(r[3]), { c: r[4], glow: glow, r: 5, dur: 9, begin: -i * 1.1 }); });
    [NE, LY, MP].forEach(function (q) {
      add(g, 'circle', { cx: q[0], cy: q[1], r: 24, fill: 'rgba(68,215,255,.12)', stroke: 'rgba(68,215,255,.6)', 'stroke-width': 1.5 });
      add(g, 'circle', { cx: q[0], cy: q[1], r: 8, fill: '#fff', filter: glow });
    });
  })();

  // ---------------------------------------------------------------- the idea, in three steps
  (function () {
    const svg = $('#pz-idea-svg'), glow = defs(svg);
    add(svg, 'ellipse', { cx: 260, cy: 205, rx: 175, ry: 135, fill: 'rgba(255,255,255,.035)', stroke: 'rgba(255,255,255,.14)', 'stroke-dasharray': '4 6' });
    add(svg, 'text', { x: 260, y: 345, 'text-anchor': 'middle', class: 'dim', text: 'Paris, inside the ring road' });
    const P = { NO: [246, 100], ES: [292, 112], NE: [270, 112], LY: [345, 268], MP: [182, 275], SL: [196, 130] };
    const E = { N: [215, -10], E: [530, 40], S: [530, 410], A: [-10, 410], W: [-10, 95], SW: [60, 410], NW: [150, -10] };
    const L = function (pts) { return 'M' + pts.map(function (p) { return p[0] + ' ' + p[1]; }).join(' L'); };
    const layer = function (cls) { return add(svg, 'g', { class: 'pz-l ' + cls }); };
    const today = layer('l0'), tri = layer('l1'), reg = layer('l2');
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
    // the triangle: lines that go through
    const tlines = [[E.N, P.NE, P.LY, E.S], [E.E, P.NE, P.MP, E.A], [E.A, P.MP, P.LY, E.S]];
    tlines.forEach(function (r) { add(tri, 'path', { d: L(r), stroke: 'rgba(143,192,255,.25)', 'stroke-width': 3, fill: 'none' }); });
    [[P.NE, P.LY], [P.LY, P.MP], [P.MP, P.NE]].forEach(function (q) { add(tri, 'path', { d: L(q), stroke: '#44d7ff', 'stroke-width': 6, fill: 'none', filter: glow }); });
    const trips = [[E.N, P.NE, P.LY, E.S, '#ff7a59'], [E.S, P.LY, P.NE, E.N, '#ffb199'], [E.E, P.NE, P.MP, E.A, '#a48bff'], [E.A, P.MP, P.NE, E.E, '#cbbcff'], [E.A, P.MP, P.LY, E.S, '#3fe0a5'], [E.S, P.LY, P.MP, E.A, '#9cf0d0']];
    trips.forEach(function (r, i) { ride(tri, L(r.slice(0, 4)), { c: r[4], glow: glow, r: 5, dur: 7, begin: -i * 1.15 }); });
    [['Paris Nord-Est', P.NE, 0, -18, 'middle'], ['Gare de Lyon', P.LY, 16, 4, 'start'], ['Montparnasse', P.MP, -16, 4, 'end']].forEach(function (q) {
      add(tri, 'circle', { cx: q[1][0], cy: q[1][1], r: 10, fill: '#fff', filter: glow });
      add(tri, 'text', { x: q[1][0] + q[2], y: q[1][1] + q[3], 'text-anchor': q[4], class: 'big', text: q[0] });
    });
    add(tri, 'text', { x: 262, y: 222, 'text-anchor': 'middle', class: 'big', text: D.model.run_min + ' min', style: 'fill: #44d7ff' });
    add(tri, 'text', { x: 262, y: 238, 'text-anchor': 'middle', class: 'dim', text: 'between any two stations' });
    // regional: line N, line H, regional express trains in the TGV tunnels
    const off = function (pts, dx, dy) { return pts.map(function (p) { return [p[0] + dx, p[1] + dy]; }); };
    const lnN = [E.E, [300, 128], off([P.NE], 4, 10)[0], off([P.MP], 8, 8)[0], E.SW], lnH = [E.NW, [262, 120], [214, 136], P.SL, E.W];
    add(reg, 'path', { d: L(lnN), stroke: '#ffc24b', 'stroke-width': 4, fill: 'none', 'stroke-linejoin': 'round' });
    add(reg, 'path', { d: L(lnH), stroke: '#ff6fb1', 'stroke-width': 4, fill: 'none', 'stroke-linejoin': 'round' });
    add(reg, 'path', { d: L(off([E.N, P.NE, P.MP, E.A], -7, 0)), stroke: '#a48bff', 'stroke-width': 2, 'stroke-dasharray': '6 5', fill: 'none' });
    ride(reg, L(lnN), { c: '#ffc24b', glow: glow, r: 4, dur: 8 }); ride(reg, L(lnN), { c: '#ffc24b', glow: glow, r: 4, dur: 8, begin: -4 });
    ride(reg, L(lnH), { c: '#ff6fb1', glow: glow, r: 4, dur: 7 }); ride(reg, L(lnH), { c: '#ff6fb1', glow: glow, r: 4, dur: 7, begin: -3.5 });
    add(reg, 'rect', { x: P.SL[0] - 6, y: P.SL[1] - 6, width: 12, height: 12, rx: 3, fill: '#ff6fb1' });
    add(reg, 'text', { x: P.SL[0] - 12, y: P.SL[1] - 10, 'text-anchor': 'end', class: 'big', text: 'Saint-Lazare' });
    [['N', 70, 380, '#ffc24b'], ['H', 30, 84, '#ff6fb1'], ['TER', 30, 330, '#a48bff']].forEach(function (q) {
      add(reg, 'rect', { x: q[1] - 4, y: q[2] - 14, width: q[0].length * 10 + 10, height: 20, rx: 5, fill: q[3] });
      add(reg, 'text', { x: q[1] + 1, y: q[2] + 1, class: 'big', text: q[0], style: 'fill: #06101f; font-size: 14px' });
    });
    const steps = PTS.$$('.pz-step', $('#presentation\\.idea'));
    let cur = 0, timer = null;
    const set = function (v) {
      cur = +v; svg.setAttribute('data-step', cur);
      today.style.opacity = cur === 0 ? 1 : 0; tri.style.opacity = cur >= 1 ? 1 : 0; reg.style.opacity = cur >= 2 ? 1 : 0;
      steps.forEach(function (st) { st.hidden = +st.getAttribute('data-step') !== cur; });
    };
    [today, tri, reg].forEach(function (g) { g.style.transition = 'opacity .7s ease'; });
    const ctl = PTS.steps($('#pz-idea-steps'), [['0', 'Today'], ['1', 'The TGV triangle'], ['2', 'Regional trains too']], '0', function (v) { clearInterval(timer); set(v); });
    set(0);
    whenShown(svg, function () { if (calm || timer) return; timer = setInterval(function () { const v = (cur + 1) % 3; ctl.set(String(v), true); set(v); if (v === 2) clearInterval(timer); }, 5000); });
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
    [-3, -6].forEach(function (z) { line(soil, [G.x1, G.y0, z], [G.x1, G.y1, z], { stroke: 'rgba(255,255,255,.06)' }); line(soil, [G.x0, G.y1, z], [G.x1, G.y1, z], { stroke: 'rgba(255,255,255,.06)' }); });

    // after: the deep station and its tunnel, seen through the ground
    const deep = add(svg, 'g', { class: 'pz-after' });
    const DZ0 = -8.5, DZ1 = -5.5, DX0 = 8, DX1 = 18, DY0 = 12, DY1 = 42;
    add(deep, 'path', { d: 'M' + P(11, G.y0, -7)[0] + ' ' + P(11, G.y0, -7)[1] + ' L' + P(11, DY0, -7)[0] + ' ' + P(11, DY0, -7)[1], stroke: 'rgba(68,215,255,.55)', 'stroke-width': 14 * k / 8.6, 'stroke-linecap': 'round', fill: 'none' });
    add(deep, 'path', { d: 'M' + P(15, G.y0, -7)[0] + ' ' + P(15, G.y0, -7)[1] + ' L' + P(15, DY0, -7)[0] + ' ' + P(15, DY0, -7)[1], stroke: 'rgba(68,215,255,.55)', 'stroke-width': 14 * k / 8.6, 'stroke-linecap': 'round', fill: 'none' });
    box(deep, DX0, DX1, DY0, DY1, DZ0, DZ1, ['rgba(68,215,255,.10)', 'rgba(68,215,255,.22)', 'rgba(68,215,255,.30)']);
    for (let i = 0; i < 6; i++) {                                        // six TGV tracks, a train on four of them
      const x = DX0 + 0.9 + i * 1.45;
      line(deep, [x, DY0 + 1, DZ0], [x, DY1 - 1, DZ0], { stroke: 'rgba(255,255,255,.35)', 'stroke-width': 1 });
      if (i % 3 === 2) continue;
      const tg = add(deep, 'g', { class: 'pz-deeptrain' });
      box(tg, x - 0.45, x + 0.45, DY0 + 3 + (i % 2) * 4, DY0 + 21 + (i % 2) * 4, DZ0, DZ0 + 1.2, ['#e9f6ff', '#7cc8f0', '#a9dcf5']);
      if (!calm) { const v = P(0, -8, 0), o = P(0, 0, 0); tg.style.setProperty('--dx', (v[0] - o[0]) + 'px'); tg.style.setProperty('--dy', (v[1] - o[1]) + 'px'); tg.style.animation = 'pz-train ' + (7 + i) + 's ease-in-out ' + (-i * 1.7) + 's infinite alternate'; }
    }
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
    [[2, 18], [5, 22], [7.5, 16], [10, 20]].forEach(function (q, i) {   // trains standing in the hall and on the approach
      const x = HX0 + (HX1 - HX0) * (([1, 5, 9, 14][i] + 0.5) / 17);
      const tg = add(before, 'g', {});
      box(tg, x - 0.3, x + 0.3, q[1], q[1] + 20, 0.03, 1.1, ['#f0e7da', '#a2958a', '#c9bcae']);
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
    let timer = null;
    const set = function (v) {
      const a = v === 'after';
      PTS.$$('.pz-before', svg).forEach(function (g) { g.style.opacity = a ? 0 : 1; });
      PTS.$$('.pz-after', svg).forEach(function (g) { g.style.opacity = a ? 1 : 0; });
      groundTop.setAttribute('fill', a ? 'rgba(27,35,51,.4)' : '#1b2333');
      svg.classList.toggle('is-after', a);
      textSteps.forEach(function (st) { st.hidden = (st.getAttribute('data-step') === '1') !== a; });
    };
    PTS.$$('.pz-before, .pz-after', svg).forEach(function (g) { g.style.transition = 'opacity .9s ease'; });
    const tg = PTS.steps($('#pz-nord-toggle'), [['before', 'Today'], ['after', 'With the project']], 'before', function (v) { clearTimeout(timer); set(v); });
    set('before');
    whenShown(svg, function () { if (calm || timer) return; timer = setTimeout(function () { tg.set('after'); }, 2600); });
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

  // ---------------------------------------------------------------- across France
  (function () {
    const CITY = { Lille: [3.06, 50.63], Bordeaux: [-0.58, 44.84], Strasbourg: [7.75, 48.58], Lyon: [4.84, 45.76], Marseille: [5.37, 43.3], Rennes: [-1.68, 48.11], Nantes: [-1.55, 47.22], Dijon: [5.04, 47.32], Paris: [2.35, 48.86] };
    const svg = $('#pz-fr-map'), glow = defs(svg), kx = Math.cos(47 * Math.PI / 180);
    const pr = function (c) { return [40 + (c[0] + 2.2) * kx * 46, 30 + (51.2 - c[1]) * 58]; };
    const P0 = pr(CITY.Paris);
    const pairs = SHOW.filter(function (p) { return CITY[p.pair[0]] && CITY[p.pair[1]]; }).map(function (p) { return Object.assign({ gain: p.today_min - p.project_min }, p); }).sort(function (a, b) { return b.gain - a.gain; });
    const g = add(svg, 'g', {});
    const arcs = pairs.map(function (p) {
      const a = pr(CITY[p.pair[0]]), b = pr(CITY[p.pair[1]]);
      const bend = function (u, v, sg) { return [(u[0] + v[0]) / 2 + sg * (v[1] - u[1]) * 0.12, (u[1] + v[1]) / 2 - sg * (v[0] - u[0]) * 0.12]; };
      const c1 = bend(a, P0, 1), c2 = bend(P0, b, 1);
      const d = 'M' + a[0] + ' ' + a[1] + ' Q' + c1[0] + ' ' + c1[1] + ' ' + P0[0] + ' ' + P0[1] + ' Q' + c2[0] + ' ' + c2[1] + ' ' + b[0] + ' ' + b[1];
      return { p: p, el: add(g, 'path', { d: d, fill: 'none', 'stroke-width': 2.5, 'stroke-linecap': 'round' }) };
    });
    add(svg, 'circle', { cx: P0[0], cy: P0[1], r: 12, fill: 'rgba(68,215,255,.2)', stroke: '#44d7ff' });
    add(svg, 'text', { x: P0[0] + 16, y: P0[1] - 10, class: 'big', text: 'Paris' });
    Object.keys(CITY).forEach(function (c) { if (c === 'Paris') return; const q = pr(CITY[c]); add(svg, 'circle', { cx: q[0], cy: q[1], r: 5, fill: '#fff' }); add(svg, 'text', { x: q[0] + (q[0] < P0[0] ? -9 : 9), y: q[1] + 4, 'text-anchor': q[0] < P0[0] ? 'end' : 'start', text: c, style: 'fill: #fff' }); });
    const host = $('#pz-fr-bars'), max = Math.max.apply(0, pairs.map(function (p) { return Math.max(p.today_min, p.project_min); }));
    host.appendChild(h('div', { class: 'pz-key' }, h('span', null, h('i', { style: 'background: rgba(255,122,89,.75)' }), 'Today, best way'), h('span', null, h('i', { style: 'background: linear-gradient(90deg,#44d7ff,#3fe0a5)' }), 'Through train, every hour')));
    const rows = pairs.map(function (p, i) {
      const t = h('i', { class: 't' }), q = h('i', { class: 'p' }), b = h('b');
      const row = h('div', { class: 'pz-bar', title: 'Today: ' + p.today + ' (' + hm(p.today_min) + ')' }, h('span', { text: p.pair[0] + ' to ' + p.pair[1] }), h('div', { class: 'pz-track' }, t, q), b);
      row.addEventListener('pointerenter', function () { hi(i); }); row.addEventListener('pointerleave', function () { hi(-1); });
      host.appendChild(row);
      return { row: row, t: t, q: q, b: b, p: p };
    });
    const hi = function (i) { arcs.forEach(function (a, k) { a.el.style.opacity = i < 0 || k === i ? 1 : 0.15; }); rows.forEach(function (r, k) { r.row.classList.toggle('hi', k === i); }); };
    let mode = 'today';
    const set = function (v) {
      mode = v;
      arcs.forEach(function (a) { a.el.setAttribute('stroke', v === 'today' ? (a.p.today.indexOf('change') >= 0 ? '#ff7a59' : 'rgba(255,170,140,.55)') : '#44d7ff'); a.el.setAttribute('filter', v === 'today' ? '' : glow); a.el.setAttribute('stroke-dasharray', v === 'today' && a.p.today.indexOf('change') >= 0 ? '5 6' : ''); });
      rows.forEach(function (r) {
        r.t.style.width = (r.p.today_min / max * 100) + '%';
        r.q.style.width = v === 'today' ? '0%' : (r.p.project_min / max * 100) + '%';
        r.b.textContent = hm(v === 'today' ? r.p.today_min : r.p.project_min);
        r.b.style.color = v === 'today' ? '#fff' : (r.p.project_min < r.p.today_min ? '#3fe0a5' : '#fff');
      });
    };
    let timer = null;
    const tg = PTS.steps($('#pz-fr-toggle'), [['today', 'Today'], ['project', 'With the project']], 'today', function (v) { clearTimeout(timer); set(v); });
    set('today');
    whenShown(svg, function () { if (timer) return; timer = setTimeout(function () { tg.set('project'); }, calm ? 0 : 1800); });
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
    add(be, 'text', { x: X(yrs[last]) - 4, y: Y(v[last]) - 12, 'text-anchor': 'end', class: 'big', text: '+€' + F.n(D.french.cases.central.npv, 1) + 'bn', style: 'fill: #3fe0a5' });
    if (!calm) { const L = line.getTotalLength(); line.style.strokeDasharray = L + ' ' + L; line.style.strokeDashoffset = L; line.style.transition = 'stroke-dashoffset 2s cubic-bezier(.3,.6,.2,1)'; }
    whenShown(svg, function () { line.style.strokeDashoffset = 0; be.setAttribute('opacity', 1); });
  })();

  // ---------------------------------------------------------------- figures of the report, shown here as they are
  const lend = function (section, host, pick) {
    const page = PTS.ensure(section); if (!page) return [];
    const nodes = pick(page).filter(Boolean);
    PTS.borrow('presentation', host, nodes);
    return nodes;
  };
  const kids = function (id, skip) { const b = document.getElementById(id); return b ? Array.prototype.filter.call(b.children, function (c) { return !c.matches(skip); }) : []; };
  lend('timetable', $('#pz-hour-host'), function () { return kids('timetable.map', 'h2, h3, p, .tt-boards'); });
  lend('access', $('#pz-access-host'), function () { return kids('access.map', 'h2, h3, p'); });
  lend('access', $('#pz-access-host-2'), function () { const c = document.getElementById('access-arr-chart'); return [c && c.closest('figure')]; });
  lend('works', $('#pz-works-host'), function () { const c = document.getElementById('works-ba'); return [c && c.closest('figure')]; });
  // the hour plays by itself the first time it comes into view
  whenShown($('#pz-hour-host'), function () {
    if (calm) return;
    const b = PTS.$$('button', $('#pz-hour-host')).filter(function (x) { return x.textContent.trim() === 'Play'; })[0];
    if (b) b.click();
  });
  // the works step through today, the works and after, once
  whenShown($('#pz-works-host'), function () {
    const bs = PTS.$$('#works-ba-controls button', root.ownerDocument);
    if (calm || bs.length < 2) return;
    bs.slice(1).forEach(function (b, i) { setTimeout(function () { if (PTS.current() === 'presentation') b.click(); }, 2200 * (i + 1)); });
  });
});
