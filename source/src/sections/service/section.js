PTS.section('service', function (root) {
  'use strict';
  const D = PTS.data.model, F = PTS.fmt, h = PTS.h, s = PTS.s;
  const $ = function (sel) { return root.querySelector(sel); };
  const n0 = function (v) { return F.n(v, v % 1 ? 1 : 0); };
  const r1 = function (v) { return Math.round(v * 10 + 1e-9) / 10; };                 // one decimal, half up, as the build and Intl do
  const t1 = function (v) { return n0(r1(v)); };
  const SCEN = [['today', 'Standard busy hour'], ['full', 'Southern lines full']];
  const state = { scen: 'today', stop: D.stop_min, clear: D.clear_min, util: D.util };
  const hourOf = function (scen) { return scen === 'full' ? D.hour_full : D.hour_today; };
  const perTrack = function (st) { return 60 * st.util / (st.stop + st.clear); };    // trains one platform track takes an hour
  const ST = ['Paris Nord-Est', 'Gare de Lyon', 'Montparnasse'];
  const PROV = function (n) { return D.cost.detail[n].hs; };                         // high-speed platform tracks provided at a station, both directions

  /* The model's service plan (model/nordest.py, section 4), repeated here so that the controls can move its settings.
     North and east trains pair with a southern line, half each; the rest of the southern trains pair with each other by the link;
     a train left without a partner turns back at Nord-Est. */
  const plan = function (H, st) {
    const A = H.Atlantic, SE = H.Southeast, N = H.North, E = H.East, through = N + E;
    const link = Math.min(A - through / 2, SE - through / 2);
    const spareA = A - through / 2 - link, spareSE = SE - through / 2 - link, spare = spareA + spareSE;
    const revEq = (D.reverse + 1) / st.stop;                                        // a turning train holds a platform as long as revEq stopping trains
    const legs = { 'Montparnasse to Nord-Est': through / 2 + spareA, 'Gare de Lyon to Nord-Est': through / 2 + spareSE, 'Montparnasse to Gare de Lyon': link };
    const stopsDir = { 'Paris Nord-Est': through + spare * revEq / 2, 'Gare de Lyon': SE, 'Montparnasse': A };   // stop-equivalents an hour in one direction
    const pt = perTrack(st), tracks = {}, load = {};
    ST.forEach(function (n) { tracks[n] = 2 * stopsDir[n] / pt; load[n] = stopsDir[n] / (PROV(n) / 2); });
    return { A: A, SE: SE, N: N, E: E, through: through, link: link, spareA: spareA, spareSE: spareSE, spare: spare, revEq: revEq, legs: legs, stopsDir: stopsDir, perTrack: pt, tracks: tracks, load: load };
  };

  // ---------------------------------------------------------------- flow diagram of one hour: the triangle
  const KIND = {
    north: { color: 'var(--s1)', label: 'To or from the north' },
    east: { color: 'var(--s2)', label: 'To or from the east' },
    link: { color: 'var(--s3)', label: 'Atlantic to south-east, by the direct link' },
    back: { color: 'var(--neutral-mark)', label: 'Turns back at Nord-Est, no partner' }
  };
  /* A band is a polyline with its own lateral offset on each segment (positive = left of travel); the corners are where the
     offset lines of two neighbouring segments meet. */
  const band = function (pts, offs) {
    const segs = [];
    for (let i = 0; i < pts.length - 1; i++) {
      const p = pts[i], q = pts[i + 1], dx = q[0] - p[0], dy = q[1] - p[1], L = Math.hypot(dx, dy) || 1;
      const nx = dy / L, ny = -dx / L, d = offs[i] || 0;                                // left normal on a screen (y down)
      segs.push({ p: [p[0] + nx * d, p[1] + ny * d], q: [q[0] + nx * d, q[1] + ny * d] });
    }
    const out = [segs[0].p];
    for (let i = 0; i < segs.length - 1; i++) {
      const a = segs[i], b = segs[i + 1];
      const r = [a.q[0] - a.p[0], a.q[1] - a.p[1]], u = [b.q[0] - b.p[0], b.q[1] - b.p[1]], den = r[0] * u[1] - r[1] * u[0];
      if (Math.abs(den) < 1e-6) out.push(a.q);
      else { const t = ((b.p[0] - a.p[0]) * u[1] - (b.p[1] - a.p[1]) * u[0]) / den; out.push([a.p[0] + r[0] * t, a.p[1] + r[1] * t]); }
    }
    out.push(segs[segs.length - 1].q);
    return out.map(function (p, i) { return (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1); }).join(' ');
  };
  const flowHost = $('#svc-flows'), wrap = h('div'); flowHost.appendChild(wrap);
  let lastW = 0;
  const drawFlows = function (full) {
    lastW = full; PTS.clear(wrap);
    const W = Math.min(full, 640), narrow = W < 480;
    const p = plan(hourOf(state.scen), state);
    const u = Math.max(2.6, Math.min(5, W / 128));                                      // pixels per train
    const y0 = 78, yT = y0 + 64, yS = yT + 190, yB = yS + 60, H = yB + 56;
    const NE = [W / 2, yT], M = [W * 0.24, yS], L = [W * 0.76, yS], NEnd = [W / 2 - W * 0.26, y0], EEnd = [W / 2 + W * 0.26, y0], AEnd = [M[0], yB], SEnd = [L[0], yB];
    const svg = s('svg', { class: 'draw', width: W, height: H, viewBox: '0 0 ' + W + ' ' + H, role: 'img',
      'aria-label': 'Flow diagram of high-speed trains in one hour on the triangle of three stations. From the Atlantic line through Montparnasse and from the south-east line through Gare de Lyon, ' +
        n0(p.through) + ' trains an hour each way reach Paris Nord-Est and run on to the north or east; ' + n0(p.link) + ' an hour each way run between Montparnasse and Gare de Lyon by the direct link' +
        (p.spare > 0 ? '; ' + n0(p.spare) + ' turns back at Nord-Est' : '') + '.' });
    const aN = p.N / 2, aE = p.E / 2, sN = p.N / 2, sE = p.E / 2;
    const TA = p.A * u, TS = p.SE * u;                                                   // width of the Atlantic and south-east approaches
    const hM = (aN + aE + p.spareA) * u / 2, hL = (sN + sE + p.spareSE) * u / 2, hN = (aN + sN) * u / 2, hE = (aE + sE) * u / 2;   // half-widths of the legs and exits
    const past = function (a, b, len) { const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1; return [b[0] + dx / L * len, b[1] + dy / L * len]; };
    // offsets: on each segment the bands are laid side by side so that the bundle is centred on the line
    const flows = [
      { kind: 'north', n: aN, name: 'Atlantic and north', stops: 'Stops in Paris: Montparnasse and Paris Nord-Est',
        pts: [AEnd, M, NE, NEnd], offs: [TA / 2 - aN * u / 2, hM - aN * u / 2, hN - aN * u / 2] },
      { kind: 'east', n: aE, name: 'Atlantic and east', stops: 'Stops in Paris: Montparnasse and Paris Nord-Est',
        pts: [AEnd, M, NE, EEnd], offs: [TA / 2 - aN * u - aE * u / 2, hM - aN * u - aE * u / 2, hE - aE * u / 2] },
      { kind: 'north', n: sN, name: 'South-east and north', stops: 'Stops in Paris: Gare de Lyon and Paris Nord-Est',
        pts: [SEnd, L, NE, NEnd], offs: [TS / 2 - p.link * u - sN * u / 2, hL - sN * u / 2, -hN + sN * u / 2] },
      { kind: 'east', n: sE, name: 'South-east and east', stops: 'Stops in Paris: Gare de Lyon and Paris Nord-Est',
        pts: [SEnd, L, NE, EEnd], offs: [TS / 2 - p.link * u - sN * u - sE * u / 2, hL - sN * u - sE * u / 2, -hE + sE * u / 2] },
      { kind: 'link', n: p.link, name: 'Atlantic and south-east', stops: 'Stops in Paris: Montparnasse and Gare de Lyon, by the direct link',
        pts: [AEnd, M, L, SEnd], offs: [-TA / 2 + p.link * u / 2, 0, TS / 2 - p.link * u / 2] }
    ];
    if (p.spareSE > 0) flows.push({ kind: 'back', n: p.spareSE, cap: true, name: 'South-east line, no partner', stops: 'Stops at Gare de Lyon, turns back at Paris Nord-Est',
      pts: [SEnd, L, past(L, NE, 38)], offs: [TS / 2 - p.link * u - sN * u - sE * u - p.spareSE * u / 2, hL - sN * u - sE * u - p.spareSE * u / 2] });
    if (p.spareA > 0) flows.push({ kind: 'back', n: p.spareA, cap: true, name: 'Atlantic line, no partner', stops: 'Stops at Montparnasse, turns back at Paris Nord-Est',
      pts: [AEnd, M, past(M, NE, 38)], offs: [TA / 2 - aN * u - aE * u - p.spareA * u / 2, hM - aN * u - aE * u - p.spareA * u / 2] });
    const paths = [];
    flows.forEach(function (f) {
      if (!(f.n > 0)) return;
      const w = f.n * u, d = band(f.pts, f.offs);
      svg.appendChild(s('path', { class: 'svc-case', d: d, 'stroke-width': w + 1.5, 'stroke-linejoin': 'round' }));
      const el = s('path', { class: 'svc-flow', d: d, 'stroke-width': Math.max(1.5, w - 1.2), 'stroke-linecap': f.cap ? 'round' : 'butt', 'stroke-linejoin': 'round', style: '--c: ' + KIND[f.kind].color, tabindex: 0, role: 'img',
        'aria-label': f.name + ': ' + n0(f.n) + (f.kind === 'back' ? ' train an hour. ' : ' trains an hour each way. ') + f.stops });
      PTS.tip.bind(el, '<b>' + f.name + '</b><br>' + n0(f.n) + (f.n === 1 ? ' train' : ' trains') + ' an hour ' + (f.kind === 'back' ? '' : 'each way') + '<br><small>' + f.stops + '</small>');
      const on = function () { svg.classList.add('hovering'); el.classList.add('on'); }, off = function () { svg.classList.remove('hovering'); el.classList.remove('on'); };
      el.addEventListener('pointerenter', on); el.addEventListener('pointerleave', off); el.addEventListener('focus', on); el.addEventListener('blur', off);
      paths.push(el);
    });
    paths.forEach(function (el) { svg.appendChild(el); });
    // trains an hour each way on each leg, beside the leg
    const legLbl = function (x, y, anchor, n) {
      svg.appendChild(s('text', { class: 'lbl-muted svc-halo', x: x, y: y, 'text-anchor': anchor, text: n0(n) + (narrow ? ' each way' : ' trains an hour each way') }));
    };
    legLbl((M[0] + NE[0]) / 2 - 4 * u - 10, (M[1] + NE[1]) / 2 + 4, 'end', p.legs['Montparnasse to Nord-Est']);
    legLbl((L[0] + NE[0]) / 2 + 4 * u + 10, (L[1] + NE[1]) / 2 + 4, 'start', p.legs['Gare de Lyon to Nord-Est']);
    legLbl(W / 2, yS - p.link * u / 2 - 8, 'middle', p.legs['Montparnasse to Gare de Lyon']);
    // station name plates on the lines
    const chip = function (cx, cy, txt) {
      const w = txt.length * 7.3 + 18;
      svg.appendChild(s('rect', { class: 'svc-chip', x: cx - w / 2, y: cy - 12, width: w, height: 24, rx: 12 }));
      svg.appendChild(s('text', { x: cx, y: cy + 4.5, 'text-anchor': 'middle', style: 'font-weight: 600; font-size: 13px', text: txt }));
    };
    chip(NE[0], NE[1], 'Paris Nord-Est'); chip(M[0], M[1], 'Montparnasse'); chip(L[0], L[1], 'Gare de Lyon');
    // the four line ends: name, trains an hour, places served
    const end = function (cx, y, name, n, places) {
      const t = s('text', { class: 'svc-end', x: cx, y: y, 'text-anchor': 'middle' },
        s('tspan', { class: 'nm', x: cx, text: name }), s('tspan', { x: cx, dy: 16, text: n0(n) + (narrow ? ' an hour' : ' an hour each way') }), s('tspan', { class: 'lbl-muted', x: cx, dy: 15, text: places }));
      svg.appendChild(t);
    };
    end(NEnd[0], 14, 'North', p.N, 'Lille, London, Brussels'); end(EEnd[0], 14, 'East', p.E, 'Reims, Strasbourg');
    end(AEnd[0], yB + 18, 'Atlantic', p.A, 'Bordeaux, Rennes, Nantes'); end(SEnd[0], yB + 18, 'South-east', p.SE, 'Lyon, Marseille');
    wrap.appendChild(svg);
    const south = p.A + p.SE;
    $('#svc-flow-title').textContent = (state.scen === 'full' ? 'With the southern lines full, ' : 'In the standard hour, ') + n0(p.through) + ' of the ' + n0(south) + ' trains an hour from the south run on to the north or east through Nord-Est; ' +
      n0(p.link) + ' cross from one southern station to the other by the link' + (p.spare > 0 ? ' and ' + n0(p.spare) + (p.spare === 1 ? ' turns back' : ' turn back') : '');
    // legend with the numbers
    const leg = PTS.clear($('#svc-flow-legend'));
    [['north', p.N], ['east', p.E], ['link', p.link], ['back', p.spare]].forEach(function (r) {
      if (!(r[1] > 0)) return;
      leg.appendChild(h('li', null, h('i', { style: { '--c': KIND[r[0]].color } }), KIND[r[0]].label + ': ', h('b', { text: n0(r[1]) + (r[0] === 'back' ? ' an hour' : ' an hour each way') })));
    });
  };
  PTS.onResize(wrap, drawFlows);

  // ---------------------------------------------------------------- platform calculator
  const drawHour = function (p) {
    const host = PTS.clear($('#svc-hour'));
    const busiest = ST.reduce(function (a, n) { return p.load[n] > p.load[a] ? n : a; }, ST[0]);
    const n = p.load[busiest], slot = 60 / n, stop = state.stop, clear = state.clear;
    for (let k = 0; k * slot < 60; k++) {
      const a = k * slot + (slot - stop - clear) / 2;
      host.appendChild(h('i', { class: 'stop', style: { left: (a / 60 * 100) + '%', width: (Math.min(60 - a, stop) / 60 * 100) + '%' } }));
      if (a + stop < 60) host.appendChild(h('i', { class: 'clear', style: { left: ((a + stop) / 60 * 100) + '%', width: (Math.min(60 - a - stop, clear) / 60 * 100) + '%' } }));
    }
    $('#svc-hour-title').textContent = 'One hour on one platform track at ' + busiest + ': ' + t1(n) + ' trains, one every ' + t1(slot) + ' minutes';
    $('#svc-hour-sub').textContent = n0(stop) + ' minutes stopped, ' + n0(clear) + ' to clear, ' + t1(Math.max(0, slot - stop - clear)) + ' free before the next train; the rule allows up to ' + t1(p.perTrack) + ' an hour on a track';
    host.setAttribute('aria-label', 'One hour on one platform track at ' + busiest + ': ' + t1(n) + ' trains an hour, each stopped ' + n0(stop) + ' minutes with ' + n0(clear) + ' minutes to clear the track');
  };
  const drawCalc = function () {
    const p = plan(hourOf(state.scen), state);
    const read = PTS.clear($('#svc-calc-read')), ne = p.tracks['Paris Nord-Est'], whole = 2 * Math.ceil(ne / 2 - 1e-9);
    const rows = [['Trains running through to the north or east, each way', n0(p.through)]];
    if (p.spare > 0) rows.push(['Trains turning back, no partner', n0(p.spare) + ', counted as ' + F.n(p.revEq, 2) + ' stops each']);
    rows.push(['Stops an hour in each direction', t1(p.stopsDir['Paris Nord-Est'])], ['One track takes, an hour', t1(p.perTrack) + ' trains'],
      ['Tracks each way by the rule', t1(ne / 2) + ', so ' + n0(whole / 2)], ['Tracks each way provided', n0(D.tracks_per_direction)],
      ['Trains an hour on each track provided', t1(p.load['Paris Nord-Est']), 'sum']);
    rows.forEach(function (r) { read.appendChild(h('dt', { class: r[2] || null, text: r[0] })); read.appendChild(h('dd', { class: r[2] || null, text: r[1] })); });
    const worst = ST.reduce(function (a, n) { return p.tracks[n] > p.tracks[a] ? n : a; }, ST[0]), need = p.tracks[worst];
    const short = ST.filter(function (n) { return p.tracks[n] > PROV(n) + 0.05; });
    $('#svc-calc-title').textContent = (state.scen === 'full' ? 'Southern lines full: ' : 'Standard busy hour: ') + (!short.length
      ? 'the rule asks for at most ' + t1(need) + ' tracks, at ' + worst + '; every station has as many as it needs'
      : 'the rule asks for ' + t1(p.tracks[short[0]]) + ' tracks at ' + short[0] + ', more than the ' + PROV(short[0]) + ' provided');
    const host = PTS.clear($('#svc-calc-tracks'));
    ST.forEach(function (name) {
      const PROVIDED = PROV(name), need = p.tracks[name], full = Math.floor(need + 1e-9), part = need - full;
      const pips = h('div', { class: 'svc-pips', role: 'img', 'aria-label': name + ': ' + t1(need) + ' tracks needed, ' + PROVIDED + ' provided' });
      const total = Math.max(PROVIDED, Math.ceil(need - 1e-9));
      for (let i = 0; i < total; i++) {
        const used = i < full ? 'full' : (i === full && part > 0.01 ? 'part' : null), cls = i >= PROVIDED ? 'short' : (used || 'free');
        pips.appendChild(h('i', { class: 'svc-pip ' + cls + ((i + 1) % (PROVIDED / 2) === 0 ? ' dir-end' : ''), style: cls === 'part' ? { '--f': Math.round(part * 100) + '%' } : null }));
      }
      const margin = PROVIDED - r1(need);
      const verdict = margin >= 0.05 ? h('span', null, t1(need) + ' needed, ' + PROVIDED + ' provided: ', h('span', { class: 'ok', text: t1(margin) + ' spare' }))
        : margin > -0.05 ? h('span', null, t1(need) + ' needed, ' + PROVIDED + ' provided: ', h('span', { class: 'ko', text: 'no margin' }))
        : h('span', null, t1(need) + ' needed, ' + PROVIDED + ' provided: ', h('span', { class: 'ko', text: t1(-margin) + ' short' }));
      if (PROVIDED > 2 * D.tracks_per_direction) verdict.appendChild(h('span', { text: '; the fourth track each way also takes the TER' }));
      host.appendChild(h('div', { class: 'svc-st' }, h('div', { class: 'lab' }, h('b', { text: name }), verdict), pips));
    });
    drawHour(p);
  };

  // ---------------------------------------------------------------- controls (the two switches move together)
  let segFlow = null, segCalc = null;
  const setScen = function (v) { state.scen = v; segFlow.set(v, true); segCalc.set(v, true); if (lastW) drawFlows(lastW); drawCalc(); };
  segFlow = PTS.seg($('#svc-flow-ctl'), SCEN, state.scen, setScen, 'Hour shown');
  segCalc = PTS.seg($('#svc-calc-ctl'), SCEN, state.scen, setScen, 'Hour');
  const sl = $('#svc-calc-sliders');
  PTS.slider(sl, { label: 'Minutes a train stops at the platform', min: 2, max: 10, step: 0.5, value: state.stop, format: function (v) { return n0(v) + ' min'; },
    note: 'A TGV stop takes 3 minutes, 6 at Lyon Part-Dieu for most trains. Used in this study, as in the timetable annex: ' + n0(D.stop_min) }, function (v) { state.stop = v; drawCalc(); });
  PTS.slider(sl, { label: 'Minutes to clear the track after a departure', min: 1, max: 5, step: 0.5, value: state.clear, format: function (v) { return n0(v) + ' min'; },
    note: 'From one train leaving to the next pulling in. Used in this study: ' + n0(D.clear_min) }, function (v) { state.clear = v; drawCalc(); });
  PTS.slider(sl, { label: 'Share of the hour a timetable can use', min: 50, max: 85, step: 5, value: Math.round(state.util * 100), format: function (v) { return n0(v) + '%'; },
    note: 'The rest is held for late trains: in this study ' + n0(D.reserve_min) + ' minutes of each ' + n0(D.stop_min + D.reserve_min + D.clear_min) + '-minute place, so ' + F.pct(D.util) }, function (v) { state.util = v / 100; drawCalc(); });
  drawCalc();
});
