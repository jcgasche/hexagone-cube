PTS.section('pulse', function (root) {
  'use strict';
  const D = PTS.data.pulse, M = PTS.data.model, F = PTS.fmt, h = PTS.h, s = PTS.s, C = PTS.chart;
  const $ = function (sel) { return root.querySelector(sel); };
  const calm = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const pad = function (m) { return ':' + (m < 10 ? '0' : '') + m; };
  const add = function (g, tag, attrs) { const e = s(tag, attrs); g.appendChild(e); return e; };
  const key = function (el, fn) { el.addEventListener('click', fn); el.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); fn(); } }); };

  // ================================================================ 1. one hour at Zürich, on a clock
  const W = D.wave, START = 40;                                   // the scrubber runs from :40 to :39
  const off = function (m) { return (m - START + 60) % 60; };     // minutes after :40
  const events = [];
  [['arr', 'arr', true], ['dep', 'dep', true], ['half_arr', 'arr', false], ['half_dep', 'dep', false]].forEach(function (q) {
    W[q[0]].forEach(function (e) { events.push(Object.assign({ kind: q[1], full: q[2] }, e)); });
  });
  const stackAt = {};
  events.forEach(function (e) { e.k = stackAt[e.m] = (stackAt[e.m] == null ? 0 : stackAt[e.m] + 1); });
  const CX = 190, CY = 190, RD = 112;
  const pt = function (m, r) { const a = m / 60 * 2 * Math.PI; return [CX + r * Math.sin(a), CY - r * Math.cos(a)]; };
  const arc = function (m1, m2, r) { const a = pt(m1, r), b = pt(m2, r); return 'M' + a[0].toFixed(1) + ',' + a[1].toFixed(1) + ' A' + r + ',' + r + ' 0 0 1 ' + b[0].toFixed(1) + ',' + b[1].toFixed(1); };
  const clock = s('svg', { class: 'draw pu-clock', viewBox: '0 0 380 380', role: 'img', 'aria-label': 'A clock face showing when long-distance trains arrive at and leave Zürich main station in one hour: twelve arrivals between :48 and :58, twelve departures between :01 and :11, and a smaller wave around the half hour.' });
  add(clock, 'circle', { cx: CX, cy: CY, r: RD, class: 'pu-face' });
  for (let m = 0; m < 60; m++) { const a = pt(m, RD), b = pt(m, RD - (m % 5 ? 5 : 10)); add(clock, 'line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: m % 5 ? 'pu-tick' : 'pu-tick five' }); }
  [[0, ':00'], [15, ':15'], [30, ':30'], [45, ':45']].forEach(function (q) { const p = pt(q[0], RD - 26); add(clock, 'text', { x: p[0], y: p[1] + 5, 'text-anchor': 'middle', class: 'pu-num', text: q[1] }); });
  add(clock, 'path', { d: arc(48, 58, RD + 9), class: 'pu-arc arr' }); add(clock, 'path', { d: arc(1, 11, RD + 9), class: 'pu-arc dep' });
  add(clock, 'path', { d: arc(22, 28, RD + 9), class: 'pu-arc arr half' }); add(clock, 'path', { d: arc(28, 38, RD + 9), class: 'pu-arc dep half' });
  const hand = add(clock, 'line', { x1: CX, y1: CY, x2: CX, y2: CY - RD + 8, class: 'pu-handline' }); add(clock, 'circle', { cx: CX, cy: CY, r: 5, class: 'pu-hub' });
  events.forEach(function (e) {
    const p = pt(e.m, RD + 24 + e.k * 13.5);
    e.el = e.kind === 'arr' ? add(clock, 'circle', { cx: p[0], cy: p[1], r: 5.5, class: 'pu-ev arr' }) : add(clock, 'rect', { x: p[0] - 5, y: p[1] - 5, width: 10, height: 10, rx: 1.5, class: 'pu-ev dep' });
    e.el.setAttribute('tabindex', 0);
    PTS.tip.bind(e.el, '<b>' + pad(e.m) + ' ' + e.train + '</b><br>' + (e.kind === 'arr' ? 'arrives from ' : 'leaves for ') + e.place + (e.track ? '<br><small>track ' + e.track + '</small>' : ''));
  });
  $('#pu-clock').appendChild(clock);
  const lists = { arr: $('#pu-arr'), dep: $('#pu-dep') };
  events.filter(function (e) { return e.full; }).forEach(function (e) {
    e.li = h('li', null, h('b', { text: pad(e.m) }), h('span', { text: e.train + (e.kind === 'arr' ? ' from ' : ' to ') + e.place }), h('i', { text: e.track }));
    lists[e.kind].appendChild(e.li);
  });
  const st = { v: 20, playing: false, raf: 0, last: 0 }, playBtn = $('#pu-play');
  const phase = function (m, a, d) {
    if (m >= 48 && m <= 58) return 'The wave arrives: ' + a + ' of 12 long-distance trains are in.';
    if (m === 59 || m === 0) return 'The last train of the wave is in and the first leaves at :01. This is the moment to change.';
    if (m >= 1 && m <= 11) return 'The wave leaves: ' + d + ' of 12 trains have gone.';
    if (m >= 12 && m <= 21) return 'Quiet. The next trains are those of the smaller wave around the half hour.';
    if (m >= 22 && m <= 27) return 'The half-hour wave arrives.';
    if (m >= 28 && m <= 38) return 'The half-hour wave leaves.';
    return 'Quiet. The next wave arrives from :48.';
  };
  const show = function () {
    const vi = Math.floor(st.v + 1e-6), m = (START + vi) % 60, ang = ((START + (calm ? vi : st.v)) % 60) * 6;
    hand.setAttribute('transform', 'rotate(' + ang.toFixed(2) + ' ' + CX + ' ' + CY + ')');
    let a = 0, d = 0;
    events.forEach(function (e) {
      const done = off(e.m) <= vi; e.el.classList.toggle('done', done);
      if (e.li) e.li.classList.toggle('done', done);
      if (e.full && done) { if (e.kind === 'arr') a++; else d++; }
    });
    $('#pu-min').textContent = pad(m); $('#pu-phase').textContent = phase(m, a, d);
    const read = PTS.clear($('#pu-read'));
    [['Arrived since :48', a + ' of 12'], ['Left since :01', d + ' of 12']].forEach(function (r) { read.appendChild(h('dt', { text: r[0] })); read.appendChild(h('dd', { text: r[1] })); });
  };
  const label = function () { playBtn.textContent = calm ? 'Next minute' : st.playing ? 'Pause' : st.v >= 59 ? 'Play again' : 'Play'; };
  const scrub = PTS.slider($('#pu-scrub'), { label: 'Minute', min: 0, max: 59, step: 1, value: st.v, format: function (v) { return pad((START + Math.floor(v)) % 60); } },
    function (v) { st.playing = false; cancelAnimationFrame(st.raf); st.v = v; label(); show(); });
  const tick = function (now) {
    if (!st.playing) return;
    st.v = Math.min(59, st.v + Math.min(100, now - st.last) / 400); st.last = now; scrub.set(Math.floor(st.v), true); show();
    if (st.v >= 59) { st.playing = false; label(); } else st.raf = requestAnimationFrame(tick);
  };
  playBtn.addEventListener('click', function () {
    if (calm) { st.v = st.v >= 59 ? 0 : Math.floor(st.v) + 1; scrub.set(st.v, true); show(); return; }
    if (st.playing) { st.playing = false; cancelAnimationFrame(st.raf); st.v = Math.floor(st.v); label(); show(); return; }
    if (st.v >= 59) st.v = 0;
    st.playing = true; st.last = performance.now(); label(); st.raf = requestAnimationFrame(tick);
  });
  label(); show();

  // ---- from one arrival to every departure in another direction
  const sel = $('#pu-from');
  W.arr.forEach(function (a, i) { sel.appendChild(h('option', { value: i, text: a.place + ', ' + a.train + ', in at ' + pad(a.m) + ' on track ' + a.track })); });
  const waits = function () {
    const a = W.arr[+sel.value], rows = [];
    W.dep.forEach(function (d) {
      const same = W.same.some(function (p) { return p[0] === a.place && p[1] === d.place; }) && a.track === d.track;
      if (!same && a.dir.some(function (x) { return d.dir.indexOf(x) >= 0; })) return;
      const w = (d.m - a.m + 60) % 60;
      rows.push({ label: 'to ' + d.place + ' at ' + pad(d.m) + ', ' + d.train + ', track ' + d.track, value: w, text: w + ' min', color: same ? 'var(--s3)' : w < W.min_change ? 'var(--s4)' : 'var(--s1)',
        tip: '<b>' + a.place + ' to ' + d.place + '</b><br>In at ' + pad(a.m) + ' on track ' + a.track + ', out at ' + pad(d.m) + ' on track ' + d.track + ': <b>' + w + ' minutes</b><br><small>' + (same ? 'the same train carries on' : w < W.min_change ? 'under the standard 7 minutes' : 'a standard change') + '</small>' });
    });
    C.bars($('#pu-waits'), { rows: rows, max: 25, fmt: function (v) { return v + ' min'; } });
  };
  sel.value = String(W.arr.length - 2); sel.addEventListener('change', waits); waits();

  // ================================================================ 2. the nodes and the runs between them
  const N = {}; D.nodes.forEach(function (n) { N[n.id] = n; });
  const net = s('svg', { class: 'draw pu-net', viewBox: '0 0 640 420', role: 'img', 'aria-label': 'Schematic map of the main Swiss rail nodes with the minutes between them. Zürich, Bern and Basel beat at 00 and 30; Lausanne and Biel at 15 and 45.' });
  const view = { mode: 'now', pick: 'n:zh' };
  const planHour = function (e) { return e.plan === '<60' || (+e.plan >= 50 && +e.plan <= 61); };
  D.edges.forEach(function (e) {
    const a = N[e.a], b = N[e.b], x = a.x + (b.x - a.x) * e.t, y = a.y + (b.y - a.y) * e.t;
    e.g = add(net, 'g', { class: 'pu-e hot', tabindex: 0, role: 'button' });
    e.line = add(e.g, 'line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y, class: 'pu-edge' });
    add(e.g, 'line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y, class: 'pu-ehit' });
    e.bg = add(e.g, 'rect', { y: y - 10, height: 19, rx: 4, class: 'pu-ebg' }); e.txt = add(e.g, 'text', { x: x, y: y + 4, 'text-anchor': 'middle', class: 'pu-etxt' }); e.x = x;
    key(e.g, function () { pick('e:' + e.a + e.b); });
    PTS.tip.bind(e.g, function () { return '<b>' + a.name + ' to ' + b.name + '</b><br>2026: ' + e.nowText + (e.plan ? '<br>Planned: ' + e.planText : '') + '<br><small>Click to read more</small>'; });
  });
  D.nodes.forEach(function (n) {
    n.g = add(net, 'g', { class: 'pu-n hot', tabindex: 0, role: 'button' });
    n.c = add(n.g, 'circle', { cx: n.x, cy: n.y, r: 15 }); n.hand = add(n.g, 'line', { class: 'pu-hand' });
    add(n.g, 'text', { x: n.x + n.lx, y: n.y + n.ly, 'text-anchor': n.anchor || 'start', class: 'pu-name', text: n.name });
    n.min = add(n.g, 'text', { x: n.x + n.lx, y: n.y + n.ly + 14, 'text-anchor': n.anchor || 'start', class: 'pu-minute' });
    add(n.g, 'circle', { cx: n.x, cy: n.y, r: 21, class: 'pu-nhit' });
    key(n.g, function () { pick('n:' + n.id); });
    PTS.tip.bind(n.g, function () { const k = view.mode === 'now' ? n.obs : n.plan; return '<b>' + n.name + '</b><br>' + (k === '00' ? 'Node at 00 and 30' : k === '15' ? 'Node at 15 and 45' : 'Not a named node') + '<br><small>Click to read more</small>'; });
  });
  $('#pu-net').appendChild(net);
  setTimeout(function () {                                         // on a narrow screen, start with Bern and Zürich in view
    const box = $('#pu-net'), k = net.getBoundingClientRect().width / 640;
    if (box.scrollWidth > box.clientWidth + 4) box.scrollLeft = Math.max(0, (N.be.x + N.zh.x) / 2 * k - box.clientWidth / 2);
  }, 0);
  const row = function (dl, k, v) { if (!v) return; dl.appendChild(h('dt', { text: k })); dl.appendChild(h('dd', { text: v })); };
  const panel = function () {
    const box = PTS.clear($('#pu-net-panel')), dl = h('dl', { class: 'pu-facts' });
    if (view.pick.charAt(0) === 'n') {
      const n = N[view.pick.slice(2)];
      box.appendChild(h('h3', { text: n.name }));
      row(dl, 'Plan of 1994', n.planText); row(dl, 'Arrivals in 2026', n.arr); row(dl, 'Departures in 2026', n.dep);
      row(dl, 'Passengers per working day, 2023', n.pax ? F.n(n.pax, 0) : ''); box.appendChild(dl);
      if (n.note) box.appendChild(h('p', { text: n.note }));
      const ul = h('ul', { class: 'pu-runs' });
      D.edges.forEach(function (e) { if (e.a !== n.id && e.b !== n.id) return; const o = N[e.a === n.id ? e.b : e.a]; ul.appendChild(h('li', null, h('button', { type: 'button', class: 'pu-link', text: o.name, onclick: function () { pick('e:' + e.a + e.b); } }), h('span', { text: e.now === '113' ? '1 h 53' : e.now + ' min' }))); });
      box.appendChild(h('h4', { text: 'Runs from here in 2026' })); box.appendChild(ul);
    } else {
      const e = D.edges.filter(function (q) { return 'e:' + q.a + q.b === view.pick; })[0];
      box.appendChild(h('h3', { text: N[e.a].name + ' to ' + N[e.b].name }));
      row(dl, 'In 2026', e.nowText); row(dl, 'Planned', e.planText); row(dl, 'Before', e.before); row(dl, 'What bought it', e.bought); box.appendChild(dl);
      box.appendChild(h('p', { class: 'note', text: e.hour ? 'A run of about one hour: both ends can be nodes at the same minute.' : 'Not a run of one hour: the two ends beat at different minutes, or the run fits another multiple of half an hour.' }));
    }
  };
  const paint = function () {
    const now = view.mode === 'now';
    D.nodes.forEach(function (n) {
      const k = now ? n.obs : n.plan, cls = k === '00' ? 'n00' : k === '15' ? 'n15' : 'nx';
      n.c.setAttribute('class', 'pu-node ' + cls); n.c.setAttribute('r', k ? 15 : 7);
      n.hand.setAttribute('x1', k === '15' ? n.x - 10 : n.x); n.hand.setAttribute('x2', k === '15' ? n.x + 10 : n.x);
      n.hand.setAttribute('y1', k === '00' ? n.y - 10 : n.y); n.hand.setAttribute('y2', k === '00' ? n.y + 10 : n.y);
      n.hand.style.display = k ? '' : 'none';
      n.min.textContent = k === '00' ? '00 and 30' : k === '15' ? '15 and 45' : '';
      n.g.classList.toggle('sel', view.pick === 'n:' + n.id);
    });
    D.edges.forEach(function (e) {
      const t = now ? (e.now === '113' ? '1 h 53' : e.now) : e.plan, w = t.length * 6.6 + 10;
      e.txt.textContent = t; e.bg.setAttribute('x', e.x - w / 2); e.bg.setAttribute('width', w); e.bg.style.display = t ? '' : 'none';
      e.line.setAttribute('class', 'pu-edge' + ((now ? e.hour : planHour(e)) ? ' hour' : '') + (t ? '' : ' none'));
      e.g.classList.toggle('sel', view.pick === 'e:' + e.a + e.b);
    });
    $('#pu-net-title').textContent = now ? 'In 2026 Luzern beats with the hour, and the western runs take longer than planned' : 'The plan: seven nodes, four at 00 and 30, three at 15 and 45';
    panel();
  };
  const pick = function (id) { view.pick = id; paint(); };
  PTS.seg($('#pu-view'), [['plan', 'The plan of 1994'], ['now', 'The 2026 timetable']], view.mode, function (v) { view.mode = v; paint(); }, 'Show');
  paint();

  // ================================================================ 3. one run, and the hour it has to fit
  const E = D.edge, es = { T: E.now };
  const half = function (v) { return F.n(v, v % 1 ? 1 : 0); };
  const edgeHost = $('#pu-edge-draw');
  let edgeW = 0;
  const drawEdge = function () {
    const T = es.T, Wd = edgeW; if (!Wd) return;
    PTS.clear(edgeHost);
    const H = 244, m = { l: 54, r: 10, t: 34, b: 42 }, x0 = -8, x1 = 106, yZ = m.t + 18, yB = H - m.b - 18;
    const X = function (v) { return m.l + (v - x0) / (x1 - x0) * (Wd - m.l - m.r); };
    const sv = s('svg', { class: 'draw pu-run', width: Wd, height: H, viewBox: '0 0 ' + Wd + ' ' + H, role: 'img', 'aria-label': 'Time and distance diagram of trains between Zürich and Bern with a journey time of ' + T + ' minutes.' });
    const fits = T < 60, slack = 60 - T, d0 = fits ? slack / 2 : 0;
    [0, 30, 60, 90].forEach(function (c, i) {
      if (fits && i % 2 === 0) add(sv, 'rect', { x: X(c - d0), y: m.t, width: X(c + d0) - X(c - d0), height: H - m.t - m.b, rx: 3, class: 'pu-band' });
      else add(sv, 'line', { x1: X(c), x2: X(c), y1: m.t, y2: H - m.b, class: 'pu-hr' + (i % 2 ? ' half' : '') });
      add(sv, 'text', { x: X(c), y: m.t - 12, 'text-anchor': 'middle', class: i % 2 ? 'lbl-muted' : 'pu-hrlbl', text: i % 2 ? ':30' : ':00' });
    });
    [[yZ, 'Zürich'], [yB, 'Bern']].forEach(function (q) { add(sv, 'line', { x1: m.l - 6, x2: Wd - m.r, y1: q[0], y2: q[0], class: 'pu-st' }); add(sv, 'text', { x: 0, y: q[0] + 4, class: 'pu-stn', text: q[1] }); });
    const seg = function (a, ya, b, yb, cls) {                              // one train, cut at the edges of the drawing
      let A = a, YA = ya, B = b, YB = yb;
      if (B < x0 || A > x1) return;
      if (A < x0) { YA = ya + (yb - ya) * (x0 - a) / (b - a); A = x0; }
      if (B > x1) { YB = ya + (yb - ya) * (x1 - a) / (b - a); B = x1; }
      add(sv, 'line', { x1: X(A), y1: YA, x2: X(B), y2: YB, class: cls });
    };
    [-60, 60].forEach(function (k) { seg(k + d0, yZ, k + d0 + T, yB, 'pu-train faint'); seg(k + d0, yB, k + d0 + T, yZ, 'pu-train faint'); });
    seg(d0, yB, d0 + T, yZ, 'pu-train back'); seg(d0, yZ, d0 + T, yB, 'pu-train main');
    const mark = fits ? (slack >= 4 ? 'good' : 'warn') : 'bad';
    [[yB, 1], [yZ, -1]].forEach(function (q) {
      const y = q[0], dir = q[1];
      if (!fits) [-1, 0, 1].forEach(function (j) { add(sv, 'line', { x1: X(60), y1: y, x2: X(60) + 10 + j * 6, y2: y + dir * 13, class: 'pu-other' }); });
      if (T > 60) add(sv, 'line', { x1: X(T), x2: X(90), y1: y, y2: y, class: 'pu-wait' });
      add(sv, 'circle', { cx: X(d0), cy: dir > 0 ? yZ : yB, r: 4, class: 'pu-start' });
      add(sv, 'circle', { cx: X(d0 + T), cy: y, r: 5.5, class: 'pu-mark ' + mark });
    });
    add(sv, 'text', { x: X(60), y: H - m.b + 16, 'text-anchor': 'middle', class: 'pu-waitlbl', text: fits ? slack + (slack === 1 ? ' minute' : ' minutes') + ' together' : 'the other trains leave at the hour' });
    add(sv, 'text', { x: X(60), y: H - m.b + 31, 'text-anchor': 'middle', class: 'lbl-muted', text: fits ? 'all trains are in both stations' : T > 60 ? 'the passenger waits ' + (90 - T) + ' minutes for the next' : 'no time to change' });
    edgeHost.appendChild(sv);
    $('#pu-edge-title').textContent = fits ? (slack >= 4 ? 'Zürich to Bern in ' + T + ' minutes: the train is in before the others leave'
      : 'Zürich to Bern in ' + T + ' minutes: in time, with only ' + slack + (slack === 1 ? ' minute' : ' minutes') + ' to change')
      : T === 60 ? 'Zürich to Bern in 60 minutes: the trains only pass each other at the hour, nobody can change'
      : 'Zürich to Bern in ' + T + ' minutes: ' + (T - 60) + ' minutes too late for the node';
    const read = PTS.clear($('#pu-edge-read'));
    [['Leaves Zürich', fits ? half(d0) + ' min after the hour' : 'at the hour'],
     ['Arrives in Bern', fits ? half(d0) + ' min before the hour' : T === 60 ? 'at the hour' : (T - 60) + ' min after the hour'],
     ['Time in the station with the other trains', fits ? slack + ' min' : 'none'],
     ['A passenger who changes leaves Bern', fits ? 'just after the hour' : 'half an hour later'],
     ['From leaving Zürich to leaving Bern', fits ? '60 min' : '90 min']]
      .forEach(function (r) { read.appendChild(h('dt', { text: r[0] })); read.appendChild(h('dd', { text: r[1] })); });
  };
  const steps = PTS.steps($('#pu-edge-steps'), E.marks, es.T, function (v) { edgeSlider.set(+v); });
  const edgeSlider = PTS.slider($('#pu-edge-slider'), { label: 'Journey time, Zürich to Bern', min: E.min, max: E.max, step: 1, value: es.T, format: function (v) { return v + ' min'; } },
    function (v) { es.T = v; steps.set(v, true); drawEdge(); });
  PTS.onResize(edgeHost, function (w) { edgeW = w; drawEdge(); });

  // ================================================================ 4. results, and Paris
  const P = D.punct, pts = function (a) { return P.years.map(function (y, i) { return [y, a[i]]; }).filter(function (p) { return p[1] != null; }); };
  C.line($('#pu-punct'), { label: 'Punctuality of SBB passenger trains and share of connections made, 2020 to 2025', height: 240,
    x: { fmt: function (v) { return v % 1 ? '' : String(v); }, tipLabel: function (v) { return String(v); } }, y: { min: 88, max: 100, fmt: function (v) { return F.n(v, 1) + '%'; } },
    series: [{ name: 'Connections made', color: 'var(--s3)', points: pts(P.conn) }, { name: 'All passenger trains on time', color: 'var(--s1)', points: pts(P.all) }, { name: 'Long-distance trains on time', color: 'var(--s2)', points: pts(P.long) }] });
  C.bars($('#pu-rules'), { compact: true, max: 45, rows: D.rules.map(function (r) {
    const t = r.lo === r.hi ? '+' + r.lo + '%' : '+' + r.lo + '% to ' + r.hi + '%';
    return { label: r.label, value: r.hi, lo: r.lo === r.hi ? null : r.lo, hi: r.lo === r.hi ? null : r.hi, text: t, color: 'var(--s1)', tip: '<b>' + r.label + '</b><br>' + t + ' passengers' };
  }) });

  const pr = M.connecting.central.pairs, mins = function (v) { return F.n(v, v % 1 ? 1 : 0) + ' min'; };
  C.bars($('#pu-paris'), { fmt: mins, max: 60, rows: [
    { label: 'Paris today: between two stations', value: pr['Lyon-Nord'].old_clock, color: 'var(--today)', tip: '<b>Paris today</b><br>' + mins(pr['Lyon-Nord'].old_clock) + ' from train to train between two terminals<br><small>value of the model</small>' },
    { label: 'Paris Nord-Est: inside one station (assumed)', value: pr['Nord-Est'].change_clock, color: 'var(--s1)', hl: true, tip: '<b>Paris Nord-Est</b><br>' + mins(pr['Nord-Est'].change_clock) + ' from train to train<br><small>assumption of the model</small>' },
    { label: 'Zürich: standard minimum', value: W.min_change, color: 'var(--neutral-mark)' },
    { label: 'Zürich: across one platform', value: 4, color: 'var(--neutral-mark)' }] });
});
