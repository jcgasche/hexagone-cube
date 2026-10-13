PTS.section('service', function (root) {
  'use strict';
  const D = PTS.data.model, F = PTS.fmt, h = PTS.h, s = PTS.s;
  const $ = function (sel) { return root.querySelector(sel); };
  const n0 = function (v) { return F.n(v, v % 1 ? 1 : 0); };
  const r1 = function (v) { return Math.round(v * 10 + 1e-9) / 10; };                 // one decimal, half up, as the build and Intl do
  const t1 = function (v) { return F.n(r1(v), 1); };
  const n2 = function (v) { return String(Math.round(v * 100) / 100); };
  const SCEN = [['today', 'Standard busy hour'], ['full', 'Southern lines full']];
  const state = { scen: 'today', perTrack: D.per_track, reverse: D.reverse };
  const stopMin = (D.reverse + 1) / D.service.rev_equiv;             // minutes of one stop in the model's rule
  const hourOf = function (scen) { return scen === 'full' ? D.hour_full : D.hour_today; };

  /* The model's service plan (model/nordest.py, section 4), repeated here so that the sliders can move its two settings. */
  const plan = function (H, perTrack, reverse) {
    const A = H.Atlantic, SE = H.Southeast, N = H.North, E = H.East, through = N + E;
    const rev = Math.min(A - through / 2, SE - through / 2);
    const spareA = A - through / 2 - rev, spareSE = SE - through / 2 - rev, spare = spareA + spareSE;
    const revEq = (reverse + 1) / stopMin, stops = 2 * through + (2 * rev + spare) * revEq;
    return { A: A, SE: SE, N: N, E: E, through: through, rev: rev, spareA: spareA, spareSE: spareSE, spare: spare, revEq: revEq, stops: stops,
      tracks: { 'Paris Nord-Est': stops / perTrack, 'Gare de Lyon': 2 * SE / perTrack, 'Montparnasse': 2 * A / perTrack } };
  };

  // ---------------------------------------------------------------- flow diagram of one hour
  const KIND = {
    north: { color: 'var(--s1)', label: 'Runs through to the north' },
    east: { color: 'var(--s2)', label: 'Runs through to the east' },
    rev: { color: 'var(--s3)', label: 'Reverses at Nord-Est, Atlantic to southeast' },
    back: { color: 'var(--neutral-mark)', label: 'Turns back at Nord-Est, no partner' }
  };
  const flowHost = $('#svc-flows'), wrap = h('div'); flowHost.appendChild(wrap);
  let lastW = 0;
  const drawFlows = function (full) {
    lastW = full; PTS.clear(wrap);
    const W = Math.min(full, 640), narrow = W < 480;
    const p = plan(hourOf(state.scen), D.per_track, D.reverse);
    const aN = p.N / 2, aE = p.E / 2, sN = p.N / 2, sE = p.E / 2;
    const u = Math.max(3, Math.min(6, W / 115));
    const xM = W * 0.3, xL = W * 0.7, xN = W * 0.27, xE = W * 0.73;
    const revW = Math.max(p.rev * u, 2), y0 = 62, yh0 = 166, ym = yh0 + 26 + revW / 2, yh1 = ym + revW / 2 + 16, yS = yh1 + 58, yB = yS + 60, H = yB + 62;
    const svg = s('svg', { class: 'draw', width: W, height: H, viewBox: '0 0 ' + W + ' ' + H, role: 'img',
      'aria-label': 'Flow diagram of high-speed trains in one hour. From the Atlantic line through Montparnasse and from the southeast line through Gare de Lyon, trains reach Paris Nord-Est. ' +
        n0(p.through) + ' an hour each way run through to the north and east; ' + n0(p.rev) + ' an hour each way reverse at Nord-Est between the two southern lines.' });
    // lane centres, left to right
    const mL = xM - p.A * u / 2, lL = xL - p.SE * u / 2, nL = xN - p.N * u / 2, eL = xE - p.E * u / 2;
    const x = {
      aN: mL + aN * u / 2, aE: mL + aN * u + aE * u / 2, aBack: mL + (aN + aE) * u + p.spareA * u / 2, aRev: mL + (aN + aE + p.spareA) * u + p.rev * u / 2,
      sRev: lL + p.rev * u / 2, sBack: lL + p.rev * u + p.spareSE * u / 2, sN: lL + (p.rev + p.spareSE) * u + sN * u / 2, sE: lL + (p.rev + p.spareSE + sN) * u + sE * u / 2,
      aNt: nL + aN * u / 2, sNt: nL + aN * u + sN * u / 2, aEt: eL + aE * u / 2, sEt: eL + aE * u + sE * u / 2
    };
    // station boxes under the bands
    svg.appendChild(s('rect', { class: 'svc-hub', x: mL - 16, y: yh0, width: (lL + p.SE * u + 16) - (mL - 16), height: yh1 - yh0, rx: 10 }));
    const bend = 46, R = revW / 2 + 7;
    const thru = function (xa, xt) { return 'M' + xa + ' ' + yB + ' L' + xa + ' ' + yh0 + ' C' + xa + ' ' + (yh0 - bend) + ' ' + xt + ' ' + (y0 + bend) + ' ' + xt + ' ' + y0; };
    const flows = [
      { kind: 'north', n: aN, d: thru(x.aN, x.aNt), name: 'Atlantic and north', stops: 'Stops in Paris: Montparnasse and Paris Nord-Est' },
      { kind: 'north', n: sN, d: thru(x.sN, x.sNt), name: 'Southeast and north', stops: 'Stops in Paris: Gare de Lyon and Paris Nord-Est' },
      { kind: 'east', n: sE, d: thru(x.sE, x.sEt), name: 'Southeast and east', stops: 'Stops in Paris: Gare de Lyon and Paris Nord-Est' },
      { kind: 'east', n: aE, d: thru(x.aE, x.aEt), name: 'Atlantic and east', stops: 'Stops in Paris: Montparnasse and Paris Nord-Est' },
      { kind: 'rev', n: p.rev, name: 'Atlantic and southeast', stops: 'Stops in Paris: Montparnasse, Paris Nord-Est (' + n0(D.reverse) + ' minutes to change direction) and Gare de Lyon',
        d: 'M' + x.aRev + ' ' + yB + ' L' + x.aRev + ' ' + (ym + R) + ' Q' + x.aRev + ' ' + ym + ' ' + (x.aRev + R) + ' ' + ym + ' L' + (x.sRev - R) + ' ' + ym + ' Q' + x.sRev + ' ' + ym + ' ' + x.sRev + ' ' + (ym + R) + ' L' + x.sRev + ' ' + yB }
    ];
    if (p.spareA > 0) flows.push({ kind: 'back', n: p.spareA, cap: true, d: 'M' + x.aBack + ' ' + yB + ' L' + x.aBack + ' ' + (ym + 2), name: 'Atlantic line, no partner', stops: 'Stops at Montparnasse, turns back at Paris Nord-Est' });
    if (p.spareSE > 0) flows.push({ kind: 'back', n: p.spareSE, cap: true, d: 'M' + x.sBack + ' ' + yB + ' L' + x.sBack + ' ' + (ym + 2), name: 'Southeast line, no partner', stops: 'Stops at Gare de Lyon, turns back at Paris Nord-Est' });
    const paths = [];
    flows.forEach(function (f) {
      if (!(f.n > 0)) return;
      const w = f.n * u;
      svg.appendChild(s('path', { class: 'svc-case', d: f.d, 'stroke-width': w + 1.5 }));
      const el = s('path', { class: 'svc-flow', d: f.d, 'stroke-width': Math.max(1.5, w - 1.2), 'stroke-linecap': f.cap ? 'round' : 'butt', style: '--c: ' + KIND[f.kind].color, tabindex: 0, role: 'img',
        'aria-label': f.name + ': ' + n0(f.n) + ' trains an hour each way. ' + f.stops });
      PTS.tip.bind(el, '<b>' + f.name + '</b><br>' + n0(f.n) + (f.n === 1 ? ' train' : ' trains') + ' an hour ' + (f.kind === 'back' ? '' : 'each way') + '<br><small>' + f.stops + '</small>');
      const on = function () { svg.classList.add('hovering'); el.classList.add('on'); }, off = function () { svg.classList.remove('hovering'); el.classList.remove('on'); };
      el.addEventListener('pointerenter', on); el.addEventListener('pointerleave', off); el.addEventListener('focus', on); el.addEventListener('blur', off);
      paths.push(el);
    });
    paths.forEach(function (el) { svg.appendChild(el); });
    // station name plates on the lines
    const chip = function (cx, cy, txt) {
      const w = txt.length * 7.3 + 18;
      svg.appendChild(s('rect', { class: 'svc-chip', x: cx - w / 2, y: cy - 12, width: w, height: 24, rx: 12 }));
      svg.appendChild(s('text', { x: cx, y: cy + 4.5, 'text-anchor': 'middle', style: 'font-weight: 600; font-size: 13px', text: txt }));
    };
    chip(W / 2, yh0, 'Paris Nord-Est'); chip(xM, yS, 'Montparnasse'); chip(xL, yS, 'Gare de Lyon');
    // the four line ends: name, trains an hour, places served
    const end = function (cx, y, name, n, places) {
      const t = s('text', { class: 'svc-end', x: cx, y: y, 'text-anchor': 'middle' },
        s('tspan', { class: 'nm', x: cx, text: name }), s('tspan', { x: cx, dy: 16, text: n0(n) + (narrow ? ' an hour' : ' an hour each way') }), s('tspan', { class: 'lbl-muted', x: cx, dy: 15, text: places }));
      svg.appendChild(t);
    };
    end(xN, 14, 'North', p.N, 'Lille, London, Brussels'); end(xE, 14, 'East', p.E, 'Reims, Strasbourg');
    end(xM, yB + 18, 'Atlantic', p.A, 'Bordeaux, Rennes, Nantes'); end(xL, yB + 18, 'Southeast', p.SE, 'Lyon, Marseille');
    wrap.appendChild(svg);
    const south = p.A + p.SE, swap = 2 * p.rev;
    $('#svc-flow-title').textContent = (state.scen === 'full' ? 'With the southern lines full, ' : 'In the standard hour, ') + n0(p.through) + ' of the ' + n0(south) + ' trains an hour from the south run on to the north or east; ' +
      n0(swap) + ' swap southern lines at Nord-Est' + (p.spare > 0 ? ' and ' + n0(p.spare) + (p.spare === 1 ? ' turns back' : ' turn back') : '');
    // legend with the numbers
    const leg = PTS.clear($('#svc-flow-legend'));
    [['north', p.N], ['east', p.E], ['rev', p.rev], ['back', p.spare]].forEach(function (r) {
      if (!(r[1] > 0)) return;
      leg.appendChild(h('li', null, h('i', { style: { '--c': KIND[r[0]].color } }), KIND[r[0]].label + ': ', h('b', { text: n0(r[1]) + (r[0] === 'back' ? ' an hour' : ' an hour each way') })));
    });
  };
  PTS.onResize(wrap, drawFlows);

  // ---------------------------------------------------------------- platform calculator
  const provided = D.cost.A.detail, SEALED = 2;
  const drawCalc = function () {
    const p = plan(hourOf(state.scen), state.perTrack, state.reverse);
    const read = PTS.clear($('#svc-calc-read')), ne = p.tracks['Paris Nord-Est'], whole = Math.ceil(ne / 2 - 1e-9) * 2, have = provided['Paris Nord-Est'].hs - SEALED;
    const rows = [['Trains running through, each way', n0(p.through)], ['Trains reversing, each way', n0(p.rev)]];
    if (p.spare > 0) rows.push(['Trains turning back, no partner', n0(p.spare)]);
    rows.push(['Stops an hour, both directions', n0(2 * p.through)], ['Reversals an hour', n0(2 * p.rev + p.spare)], ['One reversal counts as', F.n(p.revEq, 2) + ' stops'],
      ['Platform time, in stops an hour', n2(p.stops), 'sum'], ['Tracks by the rule', t1(ne)], ['In whole platforms of two tracks', n0(whole)],
      ['Provided in layout A', n0(have) + ', plus ' + SEALED + ' sealed']);
    rows.forEach(function (r) { read.appendChild(h('dt', { class: r[2] || null, text: r[0] })); read.appendChild(h('dd', { class: r[2] || null, text: r[1] })); });
    const gap = have - r1(ne);
    $('#svc-calc-title').textContent = (state.scen === 'full' ? 'Southern lines full: ' : 'Standard busy hour: ') + 'Nord-Est needs ' + t1(ne) + ' high-speed tracks by this rule; layout A provides ' + n0(have) + ', plus ' + SEALED + ' for London trains' +
      (gap < -0.05 ? ', so ' + t1(-gap) + ' are missing' : '');
    const host = PTS.clear($('#svc-calc-tracks'));
    ['Paris Nord-Est', 'Gare de Lyon', 'Montparnasse'].forEach(function (name) {
      const need = p.tracks[name], sealed = name === 'Paris Nord-Est' ? SEALED : 0, got = provided[name].hs - sealed, full = Math.floor(need + 1e-9), part = need - full;
      const pips = h('div', { class: 'svc-pips', role: 'img', 'aria-label': name + ': ' + t1(need) + ' tracks needed, ' + got + ' provided' + (sealed ? ', plus ' + sealed + ' sealed for London trains' : '') });
      const total = Math.max(got, Math.ceil(need - 1e-9));
      for (let i = 0; i < total; i++) {
        const used = i < full ? 'full' : (i === full && part > 0.01 ? 'part' : null), cls = i >= got ? 'short' : (used || 'free');
        pips.appendChild(h('i', { class: 'svc-pip ' + cls, style: cls === 'part' ? { '--f': Math.round(part * 100) + '%' } : null }));
      }
      for (let i = 0; i < sealed; i++) pips.appendChild(h('i', { class: 'svc-pip sealed' }));
      const margin = got - r1(need);
      const verdict = margin >= 0.05 ? h('span', null, t1(need) + ' needed, ' + got + ' provided' + (sealed ? ' plus ' + sealed + ' sealed' : '') + ': ', h('span', { class: 'ok', text: t1(margin) + ' spare' }))
        : margin > -0.05 ? h('span', null, t1(need) + ' needed, ' + got + ' provided: ', h('span', { class: 'ko', text: 'no margin' }))
        : h('span', null, t1(need) + ' needed, ' + got + ' provided' + (sealed ? ' plus ' + sealed + ' sealed' : '') + ': ', h('span', { class: 'ko', text: t1(-margin) + ' short' }));
      host.appendChild(h('div', { class: 'svc-st' }, h('div', { class: 'lab' }, h('b', { text: name }), verdict), pips));
    });
  };

  // ---------------------------------------------------------------- controls (the two switches move together)
  let segFlow = null, segCalc = null;
  const setScen = function (v) { state.scen = v; segFlow.set(v, true); segCalc.set(v, true); if (lastW) drawFlows(lastW); drawCalc(); };
  segFlow = PTS.seg($('#svc-flow-ctl'), SCEN, state.scen, setScen, 'Hour shown');
  segCalc = PTS.seg($('#svc-calc-ctl'), SCEN, state.scen, setScen, 'Hour');
  const sl = $('#svc-calc-sliders');
  PTS.slider(sl, { label: 'Stops an hour on one platform track', min: 4, max: 6, step: 0.5, value: state.perTrack, format: function (v) { return n0(v) + ' an hour'; },
    note: 'Through stations are planned for 4 to 6. Used in this study: ' + n0(D.per_track) }, function (v) { state.perTrack = v; drawCalc(); });
  PTS.slider(sl, { label: 'Minutes for a train to change direction', min: 3, max: 12, step: 1, value: state.reverse, format: function (v) { return n0(v) + ' min'; },
    note: 'French practice: 10 to 12, or about 3 with a second driver. Used in this study: ' + n0(D.reverse) }, function (v) { state.reverse = v; drawCalc(); });
  drawCalc();
});
