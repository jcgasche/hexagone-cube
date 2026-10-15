PTS.section('cost', function (root) {
  'use strict';
  const D = PTS.data.model, B = PTS.data.finance.base, F = PTS.fmt, h = PTS.h, C = PTS.chart, own = PTS.data.cost;
  const $ = function (sel) { return root.querySelector(sel); };
  const ITEMS = [['Tunnels, civil works', 'var(--s1)'], ['Tunnels, rail systems', 'var(--s7)'], ['Stations', 'var(--s2)'], ['Historic halls', 'var(--s4)'],
                 ['Underground junctions', 'var(--s3)'], ['Portals and links to existing lines', 'var(--s5)'], ['Sidings and depot links', 'var(--s6)'],
                 ['Control hall for London trains', 'var(--today)'], ['TER links into the TGV tunnels', 'var(--new)']];
  const pctRisk = function (R) { return F.pct(R.risk); };
  const parts = function (c, R) {
    const p = ITEMS.map(function (it) { return { label: it[0], value: c.items[it[0]], color: it[1] }; });
    p.push({ label: 'Design, client costs and land bought', value: c.soft + c.land, color: 'var(--neutral-mark)' });
    p.push({ label: 'Risk, ' + pctRisk(R), value: c.risk, color: 'var(--s8)' });
    return p;
  };

  // ---- build-up of the cost
  C.stack($('#cost-buildup'), { fmt: F.bn, rows: [{ label: '<b>The triangle</b><br>four deep stations, a tunnel for each kind of train (the regional express in the TGV one), the direct link', parts: parts(D.cost, D.rates) }] });

  // ---- deep stations per metre of platform track
  C.ranges($('#cost-stations-chart'), {
    label: 'Cost of deep stations per metre of platform track', domain: [0, 2.2], fmt: function (v) { return F.n(v, 1); }, axisLabel: '€ million per metre of platform track',
    refs: [{ value: D.rates.platform_m * 1000, label: 'Used here: €' + F.n(D.rates.platform_m * 1000, 1) + 'm' }],
    kinds: { final: { label: 'Final cost of a complete station', color: 'var(--s1)', shape: 'diamond' }, complete: { label: 'Complete station, budget or forecast', color: 'var(--s1)', shape: 'dot' }, structure: { label: 'Contract for the structure only', color: 'var(--s1)', shape: 'ring' } },
    rangeLabel: 'Range given by the source',
    rows: own.stations.map(function (r) {
      return { label: r.name, lo: r.lo, hi: r.hi, marks: [{ value: r.value, kind: r.kind, tip: '<b>' + r.name + '</b><br>' + r.what + '<br>€' + (r.lo ? F.n(r.lo, 2) + 'm to €' + F.n(r.hi, 2) : F.n(r.value, 2)) + 'm per metre' + (r.note ? '<br><small>' + r.note + '</small>' : '') }] };
    })
  });

  // ---- explorer: one layout, the triangle; prices, risk and the number of TGV tracks per station can move
  const R0 = B.cost_def.rates, L0 = B.cost_def.layout, hs0 = L0.stations['Paris Nord-Est'].hs;
  const state = { tunnel_civil: R0.central.tunnel_civil, tunnel_systems: R0.central.tunnel_systems, platform_m: R0.central.platform_m, risk: R0.central.risk, hs: hs0 };
  const sliders = {};
  const layoutWith = function (hs) {
    // the slider moves every station that has TGV tracks by the same number from its own base (Gare de Lyon keeps its two extra
    // tracks for the regional express trains and the 16th south-east TGV); Saint-Lazare (suburban only) keeps none
    const st = {}, dh = hs - hs0;
    Object.keys(L0.stations).forEach(function (n) { st[n] = Object.assign({}, L0.stations[n], L0.stations[n].hs > 0 ? { hs: L0.stations[n].hs + dh } : {}); });
    return Object.assign({}, L0, { stations: st });
  };
  const draw = function () {
    const R = Object.assign({}, R0.central, { tunnel_civil: state.tunnel_civil, tunnel_systems: state.tunnel_systems, platform_m: state.platform_m, risk: state.risk });
    const c = PTS.model.cost(R, layoutWith(state.hs)), ref = D.cost.total;
    const a = PTS.model.accounts({ capex: c.total, systems: c.systems });
    const read = PTS.clear($('#cost-ex-read'));
    [['Construction cost', F.bn(c.total)], ['Against the central estimate', Math.abs(c.total - ref) < 0.05 ? 'same' : F.signed(c.total - ref, 1) + 'bn'], ['Yearly repayment over 60 years', F.bn(a.annuity, 2)],
     ['Stations, share of works', F.pct(c.items.Stations / c.hard)], ['Platform track', F.n(c.platform_total, 0) + ' m']]
      .forEach(function (r) { read.appendChild(h('dt', { text: r[0] })); read.appendChild(h('dd', { text: r[1] })); });
    C.bars($('#cost-ex-bars'), { fmt: F.bn, max: 35, compact: true, rows: [
      { label: 'Tunnels', value: c.items['Tunnels, civil works'] + c.items['Tunnels, rail systems'], color: 'var(--s1)' },
      { label: 'Stations', value: c.items.Stations, color: 'var(--s2)' },
      { label: 'Halls, junctions, portals, sidings, London hall, regional express links', value: c.hard - c.items['Tunnels, civil works'] - c.items['Tunnels, rail systems'] - c.items.Stations, color: 'var(--s3)' },
      { label: 'Design, client costs, land bought', value: c.soft + c.land, color: 'var(--neutral-mark)' },
      { label: 'Risk, ' + pctRisk(R), value: c.risk, color: 'var(--s8)' }] });
  };
  const host = $('#cost-ex-sliders');
  const mk = function (key, cfg) { sliders[key] = PTS.slider(host, Object.assign({ value: state[key] }, cfg), function (v) { state[key] = v; draw(); }); };
  mk('platform_m', { label: 'Deep station, per metre of platform track', min: 0.0005, max: 0.0021, step: 0.00005, format: function (v) { return '€' + F.n(v * 1000, 2) + 'm'; }, note: 'Zürich 0.55, Paris 0.9 to 1.4, London 2.0' });
  mk('tunnel_civil', { label: 'Tunnel, civil works, per km', min: 0.08, max: 0.18, step: 0.005, format: function (v) { return '€' + F.n(v * 1000, 0) + 'm'; }, note: 'Grand Paris 100 to 130, London 140 to 170' });
  mk('tunnel_systems', { label: 'Track, power, signalling, per km', min: 0.03, max: 0.105, step: 0.005, format: function (v) { return '€' + F.n(v * 1000, 0) + 'm'; }, note: 'Grand Paris 31 to 58, London 104' });
  mk('risk', { label: 'Risk allowance, on top of everything', min: 0.05, max: 0.6, step: 0.01, format: function (v) { return F.pct(v); }, note: F.pct(R0.central.risk) + ' here, on final costs and contracts; Grand Paris 24% to 32% on estimates; average overrun of rail projects 45%' });
  mk('hs', { label: 'TGV platform tracks in each station', min: 4, max: 8, step: 1, format: function (v) { return F.n(v, 0) + ' tracks'; }, note: hs0 + ' here, three each way, at Nord-Est and Montparnasse; Gare de Lyon has ' + L0.stations['Gare de Lyon'].hs + ' and moves with them; four were ruled out as too tight' });
  const preset = function (name) {
    const R = name === 'zurich' ? Object.assign({}, R0.central, { platform_m: 0.00055 }) : name === 'london' ? Object.assign({}, R0.central, { platform_m: 0.002 }) : R0[name];
    ['platform_m', 'tunnel_civil', 'tunnel_systems', 'risk'].forEach(function (k) { state[k] = R[k]; sliders[k].set(R[k], true); });
    state.hs = hs0; sliders.hs.set(hs0, true);
    draw();
  };
  PTS.steps($('#cost-ex-presets'), [['central', 'Central'], ['low', 'Low prices, ' + F.pct(R0.low.risk) + ' risk'], ['high', 'High prices, ' + F.pct(R0.high.risk) + ' risk'], ['zurich', 'Stations at Zürich price'], ['london', 'Stations at London price']], 'central', preset);
  draw();

  // ---- back-test
  const bt = D.backtest, riskLab = 'With ' + F.pct(D.rates.risk) + ' risk', top = Math.max.apply(null, bt.map(function (b) { return Math.max(b.model_with_risk, b.actual_high); }));
  C.ranges($('#cost-backtest-chart'), {
    label: 'This study’s prices applied to seven projects, against their published cost', domain: [0, Math.ceil(top / 2) * 2], fmt: function (v) { return F.n(v, 0); }, axisLabel: '€ billion, 2026 prices', rowH: 34,
    kinds: { model: { label: 'This study’s prices, before risk', color: 'var(--s1)', shape: 'dot' }, risk: { label: riskLab, color: 'var(--s1)', shape: 'ring' }, actual: { label: 'Published cost', color: 'var(--s2)', shape: 'diamond' } },
    rows: bt.map(function (b) {
      const name = b.name.replace('Zurich', 'Zürich'), f1 = function (v) { return '€' + F.n(v, 1) + 'bn'; };
      return { label: name, sub: b.kind === 'study' ? '(study)' : b.kind === 'building' ? '(building)' : '', lo: b.actual_high > b.actual ? b.actual : null, hi: b.actual_high > b.actual ? b.actual_high : null,
        marks: [{ value: b.model_no_risk, kind: 'model', tip: '<b>' + name + '</b><br>This study’s prices, before risk: <b>' + f1(b.model_no_risk) + '</b>' },
                { value: b.model_with_risk, kind: 'risk', tip: '<b>' + name + '</b><br>' + riskLab + ': <b>' + f1(b.model_with_risk) + '</b>' },
                { value: b.actual, kind: 'actual', tip: '<b>' + name + '</b><br>Published cost: <b>' + f1(b.actual) + (b.actual_high > b.actual ? ' to ' + f1(b.actual_high) : '') + '</b><br><small>' + b.note + '</small>' }] };
    })
  });
  const cap = function (t) { return t.charAt(0).toUpperCase() + t.slice(1).replace(/ bn/g, 'bn').replace(/ M /g, 'm '); };
  PTS.table($('#cost-backtest-table'), [
    { key: 'name', label: 'Project', fmt: function (v) { return v.replace('Zurich', 'Zürich'); } }, { key: 'km', label: 'Tunnel, km', num: true, fmt: function (v) { return F.n(v, v % 1 ? 1 : 0); } },
    { key: 'platform_m', label: 'Platform track, m', num: true, fmt: function (v) { return F.n(v, 0); } }, { key: 'model_no_risk', label: 'Our prices, no risk', num: true, fmt: function (v) { return F.n(v, 1); } },
    { key: 'model_with_risk', label: riskLab, num: true, fmt: function (v) { return F.n(v, 1); } },
    { key: 'actual', label: 'Published cost', num: true, fmt: function (v, r) { return r.actual_high > v ? F.n(v, 1) + ' to ' + F.n(r.actual_high, 1) : F.n(v, 1); } }, { key: 'note', label: 'Note', fmt: cap }], bt);
});
