PTS.section('zurich', function (root) {
  'use strict';
  const D = PTS.data.zurich, M = PTS.data.model, F = PTS.fmt, h = PTS.h, s = PTS.s, C = PTS.chart;
  const $ = function (sel) { return root.querySelector(sel); };
  const calm = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  // ================================================================ 1. the station, in plan and in section
  // One drawing, 540 wide. North is on the left in both views, so a part sits in the same column in the plan and in the section.
  // Plan: 0.452 px per metre along the platforms (420 m = 190 px). Section: 7 px per metre of depth below the ground line Y0.
  const Y0 = 478, hx = function (n) { return 150 + (18 - n) * 13; };
  const svg = s('svg', { class: 'draw zh-draw', viewBox: '30 0 506 640', role: 'img',
    'aria-label': 'Zürich main station in plan and in section. From north to south: Museumstrasse through station 13.6 m down, the surface hall with 16 dead-end tracks, Löwenstrasse through station 16 m under the southern hall tracks, and the SZU terminus 11.6 m under the forecourt.' });
  const groups = {};
  const add = function (g, tag, attrs) { const e = s(tag, attrs); g.appendChild(e); return e; };
  const ln = function (g, x1, y1, x2, y2, cls) { return add(g, 'line', { x1: x1, y1: y1, x2: x2, y2: y2, class: cls }); };
  const tx = function (g, x, y, t, cls, anchor) { return add(g, 'text', { x: x, y: y, class: cls || null, 'text-anchor': anchor || null, text: t }); };
  const rc = function (g, x, y, w, hh, cls, rx) { return add(g, 'rect', { x: x, y: y, width: w, height: hh, class: cls, rx: rx || null }); };
  const G = function (id) { const g = s('g', { class: 'zh-p hot', 'data-part': id }); svg.appendChild(g); (groups[id] = groups[id] || []).push(g); return g; };
  const pill = function (g, cx, cy, t) { const w = t.length * 5.6 + 10; rc(g, cx - w / 2, cy - 10, w, 14, 'zh-pillbg', 3); tx(g, cx, cy + 1, t, 'zh-small', 'middle'); };
  const cars = function (g, xs, y, cls) { xs.forEach(function (x) { rc(g, x - 4.5, y, 9, 9, 'zh-car ' + (cls || ''), 2); }); };

  // ---- background of the section, captions
  const base = s('g'); svg.appendChild(base);
  rc(base, 52, Y0, 476, 152, 'ground');
  [5, 10, 15].forEach(function (m) { ln(base, 52, Y0 + m * 7, 528, Y0 + m * 7, 'zh-grid'); tx(base, 523, Y0 + m * 7 - 4, m + ' m', 'lbl-muted', 'end'); });
  tx(base, 49, Y0 + 4, '0', 'lbl-muted', 'end');
  tx(base, 34, 358, 'Plan, east at the top', 'zh-cap');
  tx(base, 34, 394, 'Section, looking east', 'zh-cap');
  ln(base, 34, 372, 532, 372, 'zh-sep');
  tx(base, 56, 414, 'north', 'lbl-muted'); tx(base, 526, 414, 'south', 'lbl-muted', 'end');
  ln(base, 486, 352, 522, 352, 'zh-buf'); add(base, 'polygon', { points: '486,347 477,352 486,357', class: 'zh-arrow old' }); tx(base, 504, 345, 'north', 'lbl-muted', 'middle');
  tx(base, 143, 338, 'surface lines to the west', 'lbl-muted');

  // ---- river Sihl (plan)
  let g = G('sihl');
  rc(g, 34, 206, 472, 16, 'zh-river'); tx(g, 38, 201, 'Sihl', 'zh-small'); rc(g, 34, 190, 472, 34, 'hit', 4);

  // ---- passages and shops (section)
  g = G('passage');
  rc(g, 62, Y0 + 18, 396, 26, 'zh-pass', 2); tx(g, 192, Y0 + 35, 'passages and shops', 'zh-small', 'middle');
  [[200, 0, 18], [330, 0, 18]].forEach(function (q) { ln(g, q[0], Y0 + q[1], q[0], Y0 + q[2], 'zh-stair'); });
  rc(g, 62, Y0 + 18, 396, 26, 'hit', 2);

  // ---- hall (plan and section)
  g = G('hall');
  rc(g, 143, 88, 209, 198, 'zh-area', 2); rc(g, 143, 66, 209, 18, 'struct', 2); tx(g, 200, 79, 'station building', 'zh-small', 'middle');
  for (let n = 18; n >= 3; n--) { const x = hx(n); ln(g, x, 94, x, 284, 'zh-trk'); ln(g, x - 3, 94, x + 3, 94, 'zh-buf'); ln(g, x, 284, 247.5 + (x - 247.5) * 0.3, 322, 'zh-trk zh-faint'); }
  const nums = add(g, 'g', { 'data-from': 1990 }); tx(nums, 140, 100, '18', 'zh-small', 'end'); tx(nums, 355, 100, '3', 'zh-small');
  rc(g, 143, 66, 209, 258, 'hit', 3);
  g = G('hall');
  add(g, 'path', { d: 'M143,' + Y0 + ' V' + (Y0 - 26) + ' Q247.5,' + (Y0 - 54) + ' 352,' + (Y0 - 26) + ' V' + Y0, class: 'zh-shed' });
  for (let n = 18; n >= 3; n--) rc(g, hx(n) - 4, Y0 - 11, 8, 10, 'zh-car', 2);
  tx(g, 247.5, Y0 - 47, 'hall, 16 dead-end tracks', null, 'middle');
  rc(g, 143, Y0 - 62, 209, 62, 'hit', 3);

  // ---- Museumstrasse (1990)
  const MX = [70, 86, 100, 116];
  g = G('museum');
  rc(g, 62, 100, 62, 163, 'new', 2);
  MX.forEach(function (x) { ln(g, x, 100, x, 263, 'zh-trk thru'); ln(g, x, 100, 93, 86, 'zh-trk thru'); ln(g, x, 263, 93, 277, 'zh-trk thru'); });
  ln(g, 93, 277, 93, 322, 'zh-trk thru'); pill(g, 93, 250, '41 to 44'); rc(g, 60, 86, 66, 238, 'hit', 3);
  g = G('museum');
  ln(g, 93, Y0 + 44, 93, Y0 + 52, 'zh-stair'); rc(g, 62, Y0 + 52, 62, 49, 'new', 2); rc(g, 75, Y0 + 90, 6, 5, 'zh-plat'); rc(g, 105, Y0 + 90, 6, 5, 'zh-plat'); cars(g, MX, Y0 + 86, 'thru');
  tx(g, 93, Y0 + 117, 'Museumstrasse', null, 'middle'); tx(g, 93, Y0 + 130, '41 to 44', 'zh-small', 'middle');
  ln(g, 124, Y0 + 95, 131, Y0 + 95, 'zh-buf'); tx(g, 134, Y0 + 99, '13.6 m', 'zh-small'); tx(g, 93, Y0 - 6, 'street', 'lbl-muted', 'middle');
  rc(g, 50, Y0 + 48, 122, 88, 'hit', 3);

  // ---- tunnels to the east (1990)
  g = G('east');
  add(g, 'path', { d: 'M93,86 V38 Q93,18 113,18 H512', class: 'zh-trk thru' }); add(g, 'polygon', { points: '512,13 521,18 512,23', class: 'zh-arrow' });
  tx(g, 508, 12, 'Hirschengraben tunnel to Stadelhofen', 'zh-small', 'end');
  add(g, 'path', { d: 'M93,86 V38 Q93,18 113,18 H512', class: 'hitline' });

  // ---- SZU terminus (1990)
  g = G('szu');
  rc(g, 422, 96, 36, 56, 'struct', 2);
  [430, 450].forEach(function (x) { ln(g, x, 100, x, 152, 'zh-trk'); ln(g, x - 3, 100, x + 3, 100, 'zh-buf'); ln(g, x, 152, 440, 166, 'zh-trk'); });
  add(g, 'path', { d: 'M440,166 V196 Q440,214 458,214 H516', class: 'zh-trk' }); add(g, 'polygon', { points: '516,209 525,214 516,219', class: 'zh-arrow old' });
  tx(g, 440, 90, 'forecourt', 'lbl-muted', 'middle'); tx(g, 466, 201, 'SZU tunnel', 'zh-small'); pill(g, 440, 140, '21, 22');
  rc(g, 416, 78, 110, 146, 'hit', 3);
  g = G('szu');
  rc(g, 422, Y0 + 44, 36, 43, 'struct', 2); rc(g, 435, Y0 + 76, 10, 5, 'zh-plat'); cars(g, [430, 450], Y0 + 72);
  tx(g, 440, Y0 + 103, 'SZU', null, 'middle'); tx(g, 440, Y0 + 116, '21, 22', 'zh-small', 'middle');
  ln(g, 415, Y0 + 81, 422, Y0 + 81, 'zh-buf'); tx(g, 412, Y0 + 85, '11.6 m', 'zh-small', 'end'); tx(g, 440, Y0 - 6, 'forecourt', 'lbl-muted', 'middle');
  rc(g, 376, Y0 + 44, 88, 78, 'hit', 3);

  // ---- wing station (2003 to 2014)
  const WX = [362, 373, 384, 395];
  g = G('wing');
  rc(g, 356, 236, 46, 66, 'zh-area', 2);
  WX.forEach(function (x) { ln(g, x, 241, x, 302, 'zh-trk'); ln(g, x - 3, 241, x + 3, 241, 'zh-buf'); ln(g, x, 302, 336 + (x - 378.5) * 0.3, 322, 'zh-trk zh-faint'); });
  tx(g, 408, 262, 'wing station', 'zh-small'); tx(g, 408, 275, '51 to 54', 'zh-small'); rc(g, 354, 232, 124, 92, 'hit', 3);
  g = G('wing');
  WX.forEach(function (x) { rc(g, x - 4, Y0 - 11, 8, 10, 'zh-car', 2); }); tx(g, 378.5, Y0 - 16, 'wing', 'zh-small', 'middle'); rc(g, 356, Y0 - 28, 46, 28, 'hit', 3);

  // ---- Löwenstrasse (2014; roof and walls 2002 to 2004)
  const LX = [268, 292, 307, 331];
  g = G('loewen');
  rc(g, 260, 82, 79, 190, 'new zh-over', 2);
  LX.forEach(function (x) { ln(g, x, 82, x, 272, 'zh-trk thru'); ln(g, x, 82, 299.5, 72, 'zh-trk thru'); ln(g, x, 272, 299.5, 286, 'zh-trk thru'); });
  pill(g, 299.5, 256, '31 to 34'); rc(g, 258, 72, 83, 216, 'hit', 3);
  g = G('loewen');
  ln(g, 299.5, Y0 + 44, 299.5, Y0 + 60, 'zh-stair'); rc(g, 260, Y0 + 60, 79, 58, 'new', 2); rc(g, 273, Y0 + 107, 14, 5, 'zh-plat'); rc(g, 312, Y0 + 107, 14, 5, 'zh-plat'); cars(g, LX, Y0 + 103, 'thru');
  tx(g, 299.5, Y0 + 134, 'Löwenstrasse', null, 'middle'); tx(g, 299.5, Y0 + 147, '31 to 34', 'zh-small', 'middle');
  ln(g, 339, Y0 + 112, 346, Y0 + 112, 'zh-buf'); tx(g, 349, Y0 + 116, '16 m', 'zh-small');
  rc(g, 254, Y0 + 56, 124, 94, 'hit', 3);

  // ---- Weinberg tunnel (2014)
  g = G('weinberg');
  add(g, 'path', { d: 'M299.5,72 V62 Q299.5,46 283.5,46 H101 M85,46 H48', class: 'zh-trk thru' }); add(g, 'polygon', { points: '48,41 39,46 48,51', class: 'zh-arrow' });
  tx(g, 128, 61, 'Weinberg tunnel, 4.8 km', 'zh-small'); tx(g, 87, 61, 'to Oerlikon', 'zh-small', 'end');
  add(g, 'path', { d: 'M299.5,72 V62 Q299.5,46 283.5,46 H40', class: 'hitline' });

  // ---- bridges to the west (2015)
  g = G('west');
  ln(g, 299.5, 286, 299.5, 325, 'zh-trk thru'); add(g, 'polygon', { points: '294.5,325 299.5,334 304.5,325', class: 'zh-arrow' });
  tx(g, 310, 338, 'ramp and bridges to Altstetten', 'zh-small'); rc(g, 288, 288, 190, 56, 'hit', 3);

  $('#zh-draw-host').appendChild(svg);

  // ---- interaction: part chosen, year chosen
  const partById = {}; D.parts.forEach(function (p) { partById[p.id] = p; });
  const pills = {}, pillBox = h('div', { class: 'steps', role: 'group', 'aria-label': 'Parts of the station' });
  let current = 'hall', year = 2015;
  const select = function (id) {
    current = id;
    Object.keys(groups).forEach(function (k) { groups[k].forEach(function (e) { e.classList.toggle('sel', k === id); }); });
    PTS.$$('.zh-panel', root).forEach(function (p) { p.hidden = p.dataset.panel !== id; });
    Object.keys(pills).forEach(function (k) { pills[k].setAttribute('aria-pressed', String(k === id)); });
  };
  D.parts.forEach(function (p) {
    pills[p.id] = h('button', { type: 'button', text: p.name, onclick: function () { select(p.id); } }); pillBox.appendChild(pills[p.id]);
    groups[p.id].forEach(function (e) {
      e.setAttribute('tabindex', 0); e.setAttribute('role', 'button'); e.setAttribute('aria-label', p.tip);
      e.addEventListener('click', function () { select(p.id); });
      e.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); select(p.id); } });
      PTS.tip.bind(e, '<b>' + p.name + '</b><br>' + p.tip + '<br><small>Click to read more</small>');
    });
  });
  $('#zh-pills').appendChild(pillBox);
  const setYear = function (y) {
    year = +y;
    const Y = D.years.filter(function (q) { return q.y === year; })[0];
    D.parts.forEach(function (p) {
      const on = year >= p.from && !(p.to && year >= p.to), build = !on && p.build != null && year >= p.build && year < p.from;
      groups[p.id].forEach(function (e) { e.classList.toggle('off', !(on || build)); e.classList.toggle('build', build); });
      pills[p.id].disabled = !(on || build);
    });
    PTS.$$('[data-from]', svg).forEach(function (e) { e.style.display = year >= +e.getAttribute('data-from') ? '' : 'none'; });
    if (pills[current].disabled) select('hall');
    $('#zh-year-title').textContent = Y.title; $('#zh-year-text').textContent = Y.text;
    const read = PTS.clear($('#zh-year-read'));
    [['Platform tracks', Y.tracks], ['of which through tracks', Y.through], ['of which dead-end tracks', Y.tracks - Y.through]].forEach(function (r) { read.appendChild(h('dt', { text: r[0] })); read.appendChild(h('dd', { text: String(r[1]) })); });
  };
  PTS.seg($('#zh-year-ctl'), D.years.map(function (q) { return [q.y, q.label]; }), year, setYear, 'Year');
  select('hall'); setYear(year);

  // ================================================================ 2. turning back against running through
  const turn = { pair: 1, t: 3, playing: false, raf: 0, last: 0 }, TMIN = -2, TMAX = 14, MOVE = 1.5;
  const host = $('#zh-turn-host'), playBtn = $('#zh-turn-play');
  let drawn = null;
  const ease = function (u) { return u < 0 ? 0 : u > 1 ? 1 : u * u * (3 - 2 * u); };
  const place = function () {
    if (!drawn) return;
    const P = D.turn[turn.pair], t = turn.t, Wd = drawn.W, L = drawn.L, xs = drawn.xs, off = -L - 14;
    drawn.rows.forEach(function (r) {
      const d = P[r.kind]; let x, noseRight = true, st;
      if (t < 0) { x = off + (xs - off) * ease((t + MOVE) / MOVE); st = t <= -MOVE ? 'on its way' : 'arriving'; }
      else if (t <= d.min) { x = xs; st = 'at the platform: ' + Math.floor(t) + ' of ' + d.min + ' min'; noseRight = !(r.kind === 'reverse' && t > d.min / 2); }
      else { const u = ease((t - d.min) / MOVE); x = r.kind === 'through' ? xs + (Wd + 14 - xs) * u : xs + (off - xs) * u; st = 'left after ' + d.min + ' min'; noseRight = r.kind === 'through'; }
      r.train.setAttribute('transform', 'translate(' + x.toFixed(1) + ',0)'); r.nose.setAttribute('x', noseRight ? L - 11 : 0);
      r.status.textContent = st; r.sub.textContent = d.train; r.when.textContent = 'in ' + d.in + ', out ' + d.out;
    });
  };
  PTS.onResize(host, function (Wd) {
    PTS.clear(host);
    const sv = s('svg', { class: 'draw zh-turn', width: Wd, height: 226, viewBox: '0 0 ' + Wd + ' 226', role: 'img', 'aria-label': 'Two trains stop at a platform. The one in the through station leaves forwards into the tunnel; the one in the hall leaves the way it came.' });
    const L = Math.min(170, Wd * 0.3), xs = Wd * 0.76 - L, rows = [];
    ['through', 'reverse'].forEach(function (kind, i) {
      const yb = i * 116, ty = yb + 74, gg = s('g'); sv.appendChild(gg);
      tx(gg, 0, yb + 15, kind === 'through' ? 'Runs through, under the hall' : 'Turns back, in the hall', 'zh-t1');
      const sub = tx(gg, 0, yb + 32, '', 'lbl-muted'), when = tx(gg, Wd, yb + 32, '', 'lbl-muted', 'end');
      rc(gg, Wd * 0.3, ty + 2, Wd * 0.48, 9, 'zh-plat', 2);
      ln(gg, 0, ty, kind === 'through' ? Wd : Wd * 0.78, ty, kind === 'through' ? 'zh-rail thru' : 'zh-rail');
      const train = s('g'); rc(train, 0, ty - 16, L, 14, 'zh-train ' + kind, 5); const nose = rc(train, 0, ty - 16, 11, 14, 'zh-nose', 5); gg.appendChild(train);
      if (kind === 'through') { rc(gg, Wd * 0.9, ty - 26, Wd * 0.1 + 1, 40, 'ground'); tx(gg, Wd - 2, ty + 30, 'tunnel', 'lbl-muted', 'end'); }
      else { ln(gg, Wd * 0.78, ty - 11, Wd * 0.78, ty + 3, 'zh-stop'); tx(gg, Wd * 0.78 + 8, ty - 1, 'buffers', 'lbl-muted'); }
      const status = tx(gg, Wd * 0.54, ty + 30, '', 'zh-status', 'middle');
      rows.push({ kind: kind, train: train, nose: nose, sub: sub, when: when, status: status });
    });
    host.appendChild(sv); drawn = { W: Wd, L: L, xs: xs, rows: rows }; place();
  });
  const label = function () { playBtn.textContent = calm ? 'Next minute' : turn.playing ? 'Pause' : turn.t >= TMAX ? 'Play again' : 'Play'; };
  const slider = PTS.slider($('#zh-turn-slider'), { label: 'Time', min: TMIN, max: TMAX, step: 0.25, value: turn.t,
    format: function (v) { return v < 0 ? 'before arrival' : Math.floor(v) + ' min after arrival'; } },
    function (v) { turn.playing = false; cancelAnimationFrame(turn.raf); turn.t = v; label(); place(); });
  const tick = function (now) {
    if (!turn.playing) return;
    turn.t = Math.min(TMAX, turn.t + Math.min(100, now - turn.last) / 450); turn.last = now; slider.set(turn.t, true); place();
    if (turn.t >= TMAX) { turn.playing = false; label(); } else turn.raf = requestAnimationFrame(tick);
  };
  playBtn.addEventListener('click', function () {
    if (calm) { turn.t = turn.t >= TMAX ? TMIN : Math.min(TMAX, Math.floor(turn.t) + 1); slider.set(turn.t, true); place(); return; }
    if (turn.playing) { turn.playing = false; cancelAnimationFrame(turn.raf); label(); return; }
    if (turn.t >= TMAX) turn.t = TMIN;
    turn.playing = true; turn.last = performance.now(); label(); turn.raf = requestAnimationFrame(tick);
  });
  PTS.steps($('#zh-turn-ctl'), D.turn.map(function (p, i) { return [i, p.label]; }), turn.pair, function (v) { turn.pair = +v; place(); });
  label();

  // ================================================================ 3. charts
  C.ranges($('#zh-dwell-chart'), {
    label: 'Minutes at the platform for eight trains at Zürich main station', domain: [0, 14], fmt: function (v) { return F.n(v, 0); }, axisLabel: 'minutes at the platform',
    kinds: { through: { label: 'Runs through', color: 'var(--s1)', shape: 'dot' }, reverse: { label: 'Turns back in the hall', color: 'var(--s2)', shape: 'diamond' } },
    rows: D.dwell.map(function (r) {
      return { label: r.train, marks: [{ value: r.min, kind: r.kind, over: r.min + ' min', tip: '<b>' + r.train + '</b><br>In at ' + r.in + ', out at ' + r.out + ': <b>' + r.min + ' minutes</b><br><small>' + (r.kind === 'through' ? 'Runs through on ' + r.where : 'Turns back in the hall') + '</small>' }] };
    })
  });

  const T = D.pertrack, thru = T.museum_trains + T.loewen_trains, rest = T.passenger_trains - thru, restTracks = T.all_tracks - T.through_tracks;
  const about = function (v) { return 'about ' + F.n(Math.round(v / 5) * 5, 0); };
  C.bars($('#zh-pertrack-chart'), { fmt: about, compact: true, rows: [
    { label: 'Museumstrasse, 4 through tracks (stand-in count)', value: T.museum_trains / 4, color: 'var(--s1)', tip: '<b>Museumstrasse</b><br>770 trains a day at Stadelhofen, on the same lines, over 4 tracks<br><small>unverified stand-in</small>' },
    { label: 'Löwenstrasse, 4 through tracks', value: T.loewen_trains / 4, color: 'var(--s1)', tip: '<b>Löwenstrasse</b><br>460 trains a day over 4 tracks' },
    { label: 'The other ' + restTracks + ' tracks: the hall and the SZU terminus', value: rest / restTracks, color: 'var(--neutral-mark)', tip: '<b>Hall and SZU terminus</b><br>' + F.n(rest, 0) + ' passenger trains a day over ' + restTracks + ' tracks<br><small>derived as the remainder</small>' }] });

  C.bars($('#zh-pax-chart'), { fmt: function (v) { return F.n(v, 0); }, rows: D.pax.map(function (r) {
    return { label: r.year + (r.flag ? ' (' + r.flag + ')' : ''), value: r.value, color: r.flag ? 'var(--neutral-mark)' : 'var(--s1)', tip: '<b>' + r.year + '</b><br>' + F.n(r.value, 0) + ' boardings and alightings per working day' + (r.note ? '<br><small>' + r.note + '</small>' : '') };
  }) });

  const shareCol = ['var(--s2)', 'var(--s1)', 'var(--s3)', 'var(--s5)', 'var(--neutral-mark)'];
  C.stack($('#zh-cost-chart'), { fmt: function (v) { return F.pct(v); }, rows: [{ label: '<b>Cross-city line</b><br>9.6 km, 2014 and 2015', text: 'CHF 2.24bn',
    parts: D.costshare.map(function (p, i) { return { label: p.label + (p.note ? ', ' + p.note : ''), value: p.value, color: shareCol[i] }; }) }] });

  // ================================================================ 4. the benchmark: trains an hour per platform track
  const S = M.service_full, DAY = 19.5;                                   // service day of 19 to 20 hours (derived)
  const zhPerTrack = 460 / 4 / DAY;
  const bench = function (label, v, color, tip, hl) { return { label: label, value: v, color: color, hl: !!hl, tip: '<b>' + label + '</b><br>' + F.n(v, 1) + ' trains an hour per track<br><small>' + tip + '</small>' }; };
  C.bars($('#zh-bench-chart'), { fmt: function (v) { return F.n(v, 1); }, max: 7, rows: [
    bench('Zürich, Löwenstrasse: average over the day', zhPerTrack, 'var(--today)', '460 trains a day on 4 tracks, over 19 to 20 hours of service (derived)'),
    bench('Paris: what the rule allows on one track', M.per_track, 'var(--s1)', 'stop of ' + F.n(M.stop_min, 0) + ' min, ' + F.n(M.reserve_min, 0) + ' min held for a late train, ' + F.n(M.clear_min, 0) + ' min to clear (assumptions)', true),
    bench('Paris Gare de Lyon, lines full', S.lyon_stops / M.cost.detail['Gare de Lyon'].hs, 'var(--s1)', F.n(S.lyon_stops, 0) + ' TGV stops an hour on ' + F.n(M.cost.detail['Gare de Lyon'].hs, 0) + ' tracks; the fourth track each way also takes the regional express trains'),
    bench('Paris Montparnasse, lines full', S.montparnasse_load, 'var(--s1)', F.n(S.montparnasse_stops, 0) + ' stops an hour on ' + F.n(2 * M.tracks_per_direction, 0) + ' tracks'),
    bench('Paris Nord-Est, lines full', S.nordest_load, 'var(--s1)', F.n(S.nordest_stops, 1) + ' stop equivalents an hour on ' + F.n(2 * M.tracks_per_direction, 0) + ' tracks, the one turning train counted as ' + F.n(S.rev_equiv, 2) + ' stops')] });

  // ================================================================ 5. size against the Paris stations
  const TK = M.cost.tracks, DT = M.cost.detail;
  const paris = function (k) { const d = DT[k]; return { label: k + ' (project)', value: TK[k], color: 'var(--s1)', tip: '<b>' + k + '</b><br>' + TK[k] + ' platform tracks: ' + [[d.hs, 'high-speed'], [d.ter, 'regional express'], [d.sub, 'suburban']].filter(function (x) { return x[0] > 0; }).map(function (x) { return x[0] + ' ' + x[1]; }).join(', ') }; };
  C.bars($('#zh-size-chart'), { fmt: function (v) { return F.n(v, 0); }, rows: [
    { label: 'Zürich, Museumstrasse (1990)', value: 4, color: 'var(--today)' }, { label: 'Zürich, Löwenstrasse (2014)', value: 4, color: 'var(--today)' },
    paris('Saint-Lazare'), paris('Gare de Lyon'), paris('Montparnasse'), paris('Paris Nord-Est')] });
});
