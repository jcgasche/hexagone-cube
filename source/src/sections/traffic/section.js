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
        marks: [{ value: P.reg_uplift * 100, kind: 'here', tip: '<b>Assumed in this study</b><br>+' + pc(P.reg_uplift * 100) + ' on the five suburban lines that run through (H, K, P, N, L)<br><small>Low case ' + pc(P.reg_uplift_low * 100) + ', high case ' + pc(P.reg_uplift_high * 100) + '</small>' }] }])
  });

  // ---- long-distance evidence
  const K = D.connecting, up = function (c) { return F.n(c.uplift * 100, 0) + '%'; };
  const inverse = (1 / (1 - P.uplift_direct) - 1) * 100;                 // an added change loses uplift_direct; read the other way
  const longRows = own.long.map(function (r) {
    const gain = r.derive === 'inverse' ? inverse : r.gain, shown = F.n(gain, gain % 1 && r.derive !== 'inverse' ? 1 : 0) + '%';
    const what = r.what.replace('{loss}', pc(P.uplift_direct * 100)).replace('{gain}', F.n(inverse, 0) + '%');
    return { label: r.short, marks: [{ value: gain, kind: r.kind, over: '+' + shown, tip: '<b>' + r.name + '</b><br><b>+' + shown + '</b>, ' + r.after + '<br><small>' + what + '</small>' }] };
  });
  const served = Object.keys(K.central.pairs).filter(function (k) { return K.central.pairs[k].served; });
  const shareServed = served.reduce(function (t, k) { return t + K.central.pairs[k].share; }, 0);
  const directUp = served.reduce(function (t, k) { return t + K.central.pairs[k].share * (D.dest_axis[k].mult_direct - 1); }, 0) / shareServed * 100;
  const longMax = Math.ceil(Math.max(K.high.uplift * 100, directUp, 200) / 50) * 50;
  C.ranges($('#tr-long-chart'), {
    label: 'Growth in long-distance passengers in the few cases where a change of train or of station was removed', domain: [0, longMax], fmt: function (v) { return F.n(v, 0) + '%'; }, axisLabel: 'Growth in passengers, %', rowH: 32,
    kinds: { obs: { label: 'Measured', color: 'var(--s1)', shape: 'dot' }, mix: { label: 'Measured, with a new line or new stations in the figure', color: 'var(--s1)', shape: 'ring' },
      der: { label: 'Derived from a measured loss', color: 'var(--s3)', shape: 'dot' }, here: { label: 'This study', color: 'var(--s2)', shape: 'diamond' } },
    rangeLabel: 'Low and high cases of this study',
    rows: longRows.concat([
      { label: 'This study, direct train: +' + pc(directUp) + ', two or three changes removed', hl: true,
        marks: [{ value: directUp, kind: 'here', tip: '<b>Taken in this study</b><br>Passengers who get a direct train across Paris: <b>+' + pc(directUp) + '</b><br><small>Each change of vehicle today keeps ' + F.pct(P.change_keep) + ' of the potential traffic; the shorter trip adds the time model. Average of the five pairs of lines with direct trains</small>' }] },
      { label: 'Result, all who cross: +' + up(K.central) + ' (' + up(K.single) + ' to ' + up(K.high) + ')', hl: true, lo: K.single.uplift * 100, hi: K.high.uplift * 100,
        marks: [{ value: K.central.uplift * 100, kind: 'here', tip: '<b>This study</b><br>All passengers who cross Paris: <b>+' + up(K.central) + '</b><br><small>Those who still change do so across one platform, counted as half a change, which keeps ' + F.pct(P.station_keep) + ' of them. Low case +' + up(K.single) + ', the first estimate of this study; high case +' + up(K.high) + ', every passenger of a served pair on a direct train</small>' }] }])
  });

  // ---- destination by destination
  const NAMES = { 'Montparnasse-Lyon': 'Atlantic and south-east', 'Montparnasse-Nord': 'Atlantic and north', 'Lyon-Nord': 'South-east and north', 'Montparnasse-Est': 'Atlantic and east', 'Lyon-Est': 'South-east and east', 'Nord-Est': 'North and east' };
  const hm = function (v) { const r = Math.round(v); return Math.floor(r / 60) + 'h' + String(r % 60).padStart(2, '0'); };
  const times = function (v) { return F.n(v, 1) + ' times'; };
  C.bars($('#tr-dest-chart'), { fmt: times, min: 0, rows: Object.keys(NAMES).map(function (k) {
    const a = D.dest_axis[k], pr = K.central.pairs[k], v = 1 + pr.growth;
    return { label: NAMES[k], value: v, color: 'var(--s1)', lo: a.mult_direct != null ? a.mult_change : null, hi: a.mult_direct != null ? a.mult_direct : null,
      tip: '<b>' + NAMES[k] + '</b><br>Traffic <b>' + times(v) + '</b> today’s<br><small>' + a.transfers + (a.transfers > 1 ? ' changes' : ' change') + ' of vehicle in Paris today; ' + hm(a.today) + ' from city to city on average, '
        + (a.direct != null ? hm(a.direct) + ' on a direct train (' + times(a.mult_direct) + '), ' : 'no direct train, ') + hm(a.change) + ' with a change in one station (' + times(a.mult_change) + ')</small>' };
  }) });
  PTS.table($('#tr-dest-table'), [
    { key: 'from', label: 'From' }, { key: 'to', label: 'To' }, { key: 'transfers', label: 'Changes today', num: true },
    { key: 'today', label: 'Today', num: true, fmt: hm }, { key: 'direct', label: 'Direct train', num: true, fmt: hm }, { key: 'change', label: 'Change in one station', num: true, fmt: hm },
    { key: 'saved', label: 'Minutes saved', num: true, fmt: function (v) { return F.n(v, 0); } },
    { key: 'mult', label: 'Traffic, times today', num: true, fmt: function (v) { return F.n(v, 1); } }],
    D.destinations.map(function (r) {
      const best = r.direct != null ? r.direct : r.change, ds = r.direct != null ? P.direct_share : 0;
      return { from: r.from, to: r.to, transfers: r.transfers, today: r.today, direct: r.direct, change: r.change, saved: r.today - best, mult: ds * (r.mult_direct || 0) + (1 - ds) * r.mult_change };
    }));

  // ---- the estimate, with its low and high cases
  const T = B.traffic, mil = function (v) { return F.n(v, 1) + ' million'; };
  const row = function (label, key, color) {
    const lo = T.low[key], hi = T.high[key], v = T.central[key], ranged = Math.abs(hi - lo) > 1e-9, pick = Math.abs(T.ride[key] - v) > 1e-9 ? T.ride[key] : null;
    return { label: label, value: v, color: color, lo: ranged ? lo : null, hi: ranged ? hi : null, mark: pick,
      tip: '<b>' + label + '</b><br>Central: <b>' + mil(v) + '</b> more journeys a year' + (ranged ? '<br><small>Low ' + mil(lo) + ', high ' + mil(hi) + '</small>' : '<br><small>From the time model; no low or high case</small>')
        + (pick != null ? '<br><small>The tick: ' + mil(pick) + ' if the ride across Paris is counted against the passenger</small>' : '') };
  };
  C.bars($('#tr-est-chart'), { fmt: mil, max: Math.ceil(T.high.new_transilien / 5) * 5, rows: [
    { group: 'High-speed trains' }, row('Starting or ending in the Paris region', 'paris_new', 'var(--s1)'), row('Crossing Paris', 'cross_new', 'var(--s1)'),
    { group: 'Suburban and regional trains' }, row('Suburban lines H, K, L, P, N, R', 'new_transilien', 'var(--s2)'), row('Regional express', 'new_ter', 'var(--s2)')] });

  // ---- new journeys before and with the charge on new uses
  const tg = FC.central.tgv, FP = PTS.data.finance.params, mi = function (v) { return F.n(v, 1) + ' million'; };
  C.bars($('#tr-net-chart'), { fmt: mi, rows: [
    { group: 'Before any charge' },
    { label: 'Starting or ending in the Paris region', value: T.central.paris_new, color: 'var(--s1)' },
    { label: 'Crossing Paris', value: T.central.cross_new, color: 'var(--s1)' },
    { group: 'With the charge on new uses' },
    { label: 'Starting or ending in the Paris region', value: tg.new_paris, color: 'var(--s2)', tip: '<b>Paris region, with the charge</b><br>' + mi(tg.new_paris) + ' more journeys a year<br><small>' + F.pct(tg.pay_share) + ' of these passengers choose a station their line did not serve and pay €' + F.n(FP.charge_end, 2) + '; the others pay nothing more</small>' },
    { label: 'Crossing Paris', value: tg.new_cross, color: 'var(--s2)', tip: '<b>Crossing Paris, with the charge</b><br>' + mi(tg.new_cross) + ' more journeys a year<br><small>€' + F.n(FP.charge_through, 2) + ' on a direct train or with a change in one station</small>' },
    { sep: true },
    { label: 'Added with the charge', value: tg.net_new, color: 'var(--today)', hl: true, tip: '<b>Added with the charge</b><br>' + mi(tg.net_new) + ' a year<br><small>' + mi(tg.held) + ' held back by the charge; none lost against today</small>' }] });
});
