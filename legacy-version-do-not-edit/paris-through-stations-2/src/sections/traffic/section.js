PTS.section('traffic', function (root) {
  'use strict';
  const D = PTS.data.model, B = PTS.data.finance.base, FC = PTS.data.finance.cases, own = PTS.data.traffic, F = PTS.fmt, C = PTS.chart;
  const $ = function (sel) { return root.querySelector(sel); };
  const pc = function (v) { const r = Math.round(v * 10) / 10; return F.n(r, r % 1 ? 1 : 0) + '%'; };

  // ---- suburban lines joined through a centre
  const P = D.params, avg = own.suburban.reduce(function (a, r) { return a + r.gain; }, 0) / own.suburban.length;
  C.ranges($('#tr-sub-chart'), {
    label: 'Growth in passengers on suburban lines after they were joined through a city centre', domain: [0, 40], fmt: function (v) { return F.n(v, 0) + '%'; }, axisLabel: 'Growth in passengers, %', rowH: 32,
    kinds: { gain: { label: 'Growth counted on the joined lines', color: 'var(--s1)', shape: 'dot' }, bg: { label: 'Rest of the network, same years', color: 'var(--s1)', shape: 'ring' },
      avg: { label: 'Average of the eight', color: 'var(--today)', shape: 'diamond' }, here: { label: 'Assumed in this study', color: 'var(--s2)', shape: 'diamond' } },
    rangeLabel: 'Low and high cases of this study',
    rows: own.suburban.map(function (r) {
      const tip = '<b>' + r.name + '</b><br>' + r.what + '<br><b>' + (r.gain ? '+' + pc(r.gain) : 'No gain') + '</b> ' + r.after + '<br><small>' + r.note + '</small>';
      const marks = [{ value: r.gain, kind: 'gain', over: r.gain ? '+' + pc(r.gain) : 'no gain', tip: tip }];
      if (r.bg != null) marks.unshift({ value: r.bg, kind: 'bg', tip: '<b>' + r.name + '</b><br>Rest of the network over the same years: <b>+' + pc(r.bg) + '</b>' });
      return { label: r.short, marks: marks };
    }).concat([
      { label: 'Average of the eight cases', marks: [{ value: avg, kind: 'avg', over: F.n(avg, 0) + '%', tip: '<b>Average of the eight cases</b><br>+' + F.n(avg, 0) + '%, before deducting growth that would have come anyway' }] },
      { label: 'This study: ' + pc(P.reg_uplift * 100) + ' (' + pc(P.reg_uplift_low * 100) + ' to ' + pc(P.reg_uplift_high * 100) + ')', hl: true, lo: P.reg_uplift_low * 100, hi: P.reg_uplift_high * 100,
        marks: [{ value: P.reg_uplift * 100, kind: 'here', tip: '<b>Assumed in this study</b><br>+' + pc(P.reg_uplift * 100) + ' on the five suburban lines<br><small>Low case ' + pc(P.reg_uplift_low * 100) + ', high case ' + pc(P.reg_uplift_high * 100) + '</small>' }] }])
  });

  // ---- long-distance evidence
  const K = D.connecting, up = function (c) { return F.n(c.uplift * 100, 0) + '%'; };
  const inverse = (1 / (1 - P.uplift_direct) - 1) * 100;                 // an added change loses uplift_direct; read the other way
  const longRows = own.long.map(function (r) {
    const gain = r.derive === 'inverse' ? inverse : r.gain, shown = F.n(gain, gain % 1 && r.derive !== 'inverse' ? 1 : 0) + '%';
    const what = r.what.replace('{loss}', pc(P.uplift_direct * 100)).replace('{gain}', F.n(inverse, 0) + '%');
    return { label: r.short, marks: [{ value: gain, kind: r.kind, over: '+' + shown, tip: '<b>' + r.name + '</b><br><b>+' + shown + '</b>, ' + r.after + '<br><small>' + what + '</small>' }] };
  });
  C.ranges($('#tr-long-chart'), {
    label: 'Growth in long-distance passengers in the few cases where a change of train or of station was removed', domain: [0, 200], fmt: function (v) { return F.n(v, 0) + '%'; }, axisLabel: 'Growth in passengers, %', rowH: 32,
    kinds: { obs: { label: 'Measured', color: 'var(--s1)', shape: 'dot' }, mix: { label: 'Measured, with a new line or new stations in the figure', color: 'var(--s1)', shape: 'ring' },
      der: { label: 'Derived from a measured loss', color: 'var(--s3)', shape: 'dot' }, here: { label: 'This study', color: 'var(--s2)', shape: 'diamond' } },
    rangeLabel: 'Low and high cases of this study',
    rows: longRows.concat([
      { label: 'Taken here, direct train: ' + pc(P.uplift_direct * 100) + ' (high ' + pc(P.uplift_direct_high * 100) + ')', hl: true, lo: P.uplift_direct * 100, hi: P.uplift_direct_high * 100,
        marks: [{ value: P.uplift_direct * 100, kind: 'here', tip: '<b>Taken in this study</b><br>Passengers who get a direct train across Paris: <b>+' + pc(P.uplift_direct * 100) + '</b><br><small>High case +' + pc(P.uplift_direct_high * 100) + ', as on the Paris bypass line. The low case uses the time model alone</small>' }] },
      { label: 'Result, all who cross: +' + up(K.central) + ' (' + up(K.model_only) + ' to ' + up(K.high) + ')', hl: true, lo: K.model_only.uplift * 100, hi: K.high.uplift * 100,
        marks: [{ value: K.central.uplift * 100, kind: 'here', tip: '<b>This study</b><br>All passengers who cross Paris: <b>+' + up(K.central) + '</b><br><small>Low case +' + up(K.model_only) + ', high case +' + up(K.high) + '. Those who still change train, inside one station, gain less</small>' }] }])
  });

  // ---- the estimate, with its low and high cases
  const T = B.traffic, mil = function (v) { return F.n(v, 1) + ' million'; };
  const row = function (label, key, color) {
    const lo = T.low[key], hi = T.high[key], v = T.central[key], ranged = Math.abs(hi - lo) > 1e-9, pick = Math.abs(T.pick[key] - v) > 1e-9 ? T.pick[key] : null;
    return { label: label, value: v, color: color, lo: ranged ? lo : null, hi: ranged ? hi : null, mark: pick,
      tip: '<b>' + label + '</b><br>Central: <b>' + mil(v) + '</b> more journeys a year' + (ranged ? '<br><small>Low ' + mil(lo) + ', high ' + mil(hi) + '</small>' : '<br><small>From the time model; no low or high case</small>')
        + (pick != null ? '<br><small>The tick: ' + mil(pick) + ' if passengers pick the train that calls at their best station</small>' : '') };
  };
  C.bars($('#tr-est-chart'), { fmt: mil, max: Math.ceil(T.high.new_transilien / 5) * 5, rows: [
    { group: 'High-speed trains' }, row('Starting or ending in the Paris region', 'paris_new', 'var(--s1)'), row('Crossing Paris', 'cross_new', 'var(--s1)'),
    { group: 'Suburban and regional trains' }, row('Suburban lines H, K, P, N, R', 'new_transilien', 'var(--s2)'), row('Regional express', 'new_ter', 'var(--s2)')] });

  // ---- net of the passenger charge, for the two responses of traffic to fares
  const tg = FC.central.tgv, tl = FC.resp05.tgv, FP = PTS.data.finance.params, sg = function (v) { return F.signed(v, 1) + ' million'; };
  const resp = function (v) { return 'response ' + F.n(-v, 1); };
  const lostRow = function (t, v) {
    return { label: 'Journeys lost, ' + resp(v), value: -t.lost, color: 'var(--s2)', tip: '<b>Journeys lost to the passenger charge</b><br>' + sg(-t.lost) + ' if traffic falls ' + F.n(-v, 1) + '% for 1% on the fare<br><small>' + F.n(t.lost_paris, 1) + ' million starting or ending in Paris, ' + F.n(t.lost_cross, 1) + ' million crossing</small>' };
  };
  C.bars($('#tr-net-chart'), { fmt: sg, rows: [
    { label: 'Journeys the project adds', value: tg.new_before_charge, color: 'var(--s1)' },
    lostRow(tl, FP.fare_response_low), lostRow(tg, B.fare_response),
    { sep: true },
    { label: 'Net change, ' + resp(FP.fare_response_low), value: tl.net_new, color: 'var(--today)', hl: true },
    { label: 'Net change, ' + resp(B.fare_response), value: tg.net_new, color: 'var(--today)', hl: true }] });
});
