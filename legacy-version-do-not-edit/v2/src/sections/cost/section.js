PTS.section('cost', function (root) {
  'use strict';
  const D = PTS.data.model, B = PTS.data.finance.base, F = PTS.fmt, h = PTS.h, C = PTS.chart, own = PTS.data.cost;
  const $ = function (sel) { return root.querySelector(sel); };
  const ITEMS = [['Tunnels, civil works', 'var(--s1)'], ['Tunnels, rail systems', 'var(--s7)'], ['Stations', 'var(--s2)'], ['Historic halls', 'var(--s4)'],
                 ['Underground junctions', 'var(--s3)'], ['Portals and links to existing lines', 'var(--s5)'], ['Sidings and depot links', 'var(--s6)']];
  const parts = function (c) {
    const p = ITEMS.map(function (it) { return { label: it[0], value: c.items[it[0]], color: it[1] }; });
    p.push({ label: 'Design, client costs and land', value: c.soft + c.land, color: 'var(--neutral-mark)' });
    p.push({ label: 'Risk', value: c.risk, color: 'var(--s8)' });
    return p;
  };

  // ---- build-up of the two layouts
  C.stack($('#cost-buildup'), { fmt: F.bn, rows: [
    { label: '<b>Layout A</b><br>three pairs of tracks', parts: parts(D.cost.A) },
    { label: '<b>Layout B</b><br>two pairs of tracks', parts: parts(D.cost.B) }] });

  // ---- deep stations per metre of platform track
  C.ranges($('#cost-stations-chart'), {
    label: 'Cost of deep stations per metre of platform track', domain: [0, 2.2], fmt: function (v) { return F.n(v, 1); }, axisLabel: '€ million per metre of platform track',
    refs: [{ value: D.rates.platform_m * 1000, label: 'Used here: €' + F.n(D.rates.platform_m * 1000, 1) + 'm' }],
    kinds: { complete: { label: 'Complete station', color: 'var(--s1)', shape: 'dot' }, structure: { label: 'Contract for the structure only', color: 'var(--s1)', shape: 'ring' } },
    rangeLabel: 'Range given by the source',
    rows: own.stations.map(function (r) {
      return { label: r.name, lo: r.lo, hi: r.hi, marks: [{ value: r.value, kind: r.kind, tip: '<b>' + r.name + '</b><br>' + r.what + '<br>€' + (r.lo ? F.n(r.lo, 2) + 'm to €' + F.n(r.hi, 2) : F.n(r.value, 2)) + 'm per metre' + (r.note ? '<br><small>' + r.note + '</small>' : '') }] };
    })
  });

  // ---- explorer
  const R0 = B.cost_def.rates, state = { layout: 'A', tunnel_civil: R0.central.tunnel_civil, tunnel_systems: R0.central.tunnel_systems, platform_m: R0.central.platform_m, risk: R0.central.risk };
  const sliders = {};
  const draw = function () {
    const R = Object.assign({}, R0.central, { tunnel_civil: state.tunnel_civil, tunnel_systems: state.tunnel_systems, platform_m: state.platform_m, risk: state.risk });
    const c = PTS.model.cost(state.layout, R), ref = D.cost[state.layout].total;
    const a = PTS.model.accounts({ layout: state.layout, capex: c.total, systems: c.systems });
    const read = PTS.clear($('#cost-ex-read'));
    [['Construction cost', F.bn(c.total)], ['Against the central estimate', Math.abs(c.total - ref) < 0.05 ? 'same' : F.signed(c.total - ref, 1) + 'bn'], ['Yearly repayment over 60 years', F.bn(a.annuity, 2)], ['Stations, share of works', F.pct(c.items.Stations / c.hard)]]
      .forEach(function (r) { read.appendChild(h('dt', { text: r[0] })); read.appendChild(h('dd', { text: r[1] })); });
    C.bars($('#cost-ex-bars'), { fmt: F.bn, max: 40, compact: true, rows: [
      { label: 'Tunnels', value: c.items['Tunnels, civil works'] + c.items['Tunnels, rail systems'], color: 'var(--s1)' },
      { label: 'Stations', value: c.items.Stations, color: 'var(--s2)' },
      { label: 'Halls, junctions, portals, sidings', value: c.hard - c.items['Tunnels, civil works'] - c.items['Tunnels, rail systems'] - c.items.Stations, color: 'var(--s3)' },
      { label: 'Design, client costs, land', value: c.soft + c.land, color: 'var(--neutral-mark)' },
      { label: 'Risk', value: c.risk, color: 'var(--s8)' }] });
  };
  PTS.seg($('#cost-ex-top'), [['A', 'Layout A'], ['B', 'Layout B']], state.layout, function (v) { state.layout = v; draw(); }, 'Layout');
  const host = $('#cost-ex-sliders');
  const mk = function (key, cfg) { sliders[key] = PTS.slider(host, Object.assign({ value: state[key] }, cfg), function (v) { state[key] = v; draw(); }); };
  mk('platform_m', { label: 'Deep station, per metre of platform track', min: 0.0005, max: 0.0021, step: 0.00005, format: function (v) { return '€' + F.n(v * 1000, 2) + 'm'; }, note: 'Zürich 0.55, Paris 0.9 to 1.4, London 2.0' });
  mk('tunnel_civil', { label: 'Tunnel, civil works, per km', min: 0.08, max: 0.18, step: 0.005, format: function (v) { return '€' + F.n(v * 1000, 0) + 'm'; }, note: 'Grand Paris 100 to 130, London 140 to 170' });
  mk('tunnel_systems', { label: 'Track, power, signalling, per km', min: 0.03, max: 0.105, step: 0.005, format: function (v) { return '€' + F.n(v * 1000, 0) + 'm'; }, note: 'Grand Paris 31 to 58, London 104' });
  mk('risk', { label: 'Risk allowance', min: 0.1, max: 0.6, step: 0.01, format: function (v) { return F.pct(v); }, note: 'Grand Paris 24% to 32%; average overrun of rail projects 45%' });
  const preset = function (name) {
    const R = name === 'zurich' ? Object.assign({}, R0.central, { platform_m: 0.00055 }) : name === 'london' ? Object.assign({}, R0.central, { platform_m: 0.002 }) : R0[name];
    ['platform_m', 'tunnel_civil', 'tunnel_systems', 'risk'].forEach(function (k) { state[k] = R[k]; sliders[k].set(R[k], true); });
    draw();
  };
  PTS.steps($('#cost-ex-presets'), [['central', 'Central'], ['low', 'Low prices'], ['high', 'High prices'], ['zurich', 'Stations at Zürich price'], ['london', 'Stations at London price']], 'central', preset);
  draw();

  // ---- back-test
  const bt = D.backtest, top = Math.max.apply(null, bt.map(function (b) { return Math.max(b.model_with_risk, b.actual_high); }));
  C.ranges($('#cost-backtest-chart'), {
    label: 'This study’s prices applied to seven projects, against their published cost', domain: [0, Math.ceil(top / 2) * 2], fmt: function (v) { return F.n(v, 0); }, axisLabel: '€ billion, 2026 prices', rowH: 34,
    kinds: { model: { label: 'This study’s prices, before risk', color: 'var(--s1)', shape: 'dot' }, risk: { label: 'With 30% risk', color: 'var(--s1)', shape: 'ring' }, actual: { label: 'Published cost', color: 'var(--s2)', shape: 'diamond' } },
    rows: bt.map(function (b) {
      const name = b.name.replace('Zurich', 'Zürich'), f1 = function (v) { return '€' + F.n(v, 1) + 'bn'; };
      return { label: name, sub: b.kind === 'study' ? '(study)' : b.kind === 'building' ? '(building)' : '', lo: b.actual_high > b.actual ? b.actual : null, hi: b.actual_high > b.actual ? b.actual_high : null,
        marks: [{ value: b.model_no_risk, kind: 'model', tip: '<b>' + name + '</b><br>This study’s prices, before risk: <b>' + f1(b.model_no_risk) + '</b>' },
                { value: b.model_with_risk, kind: 'risk', tip: '<b>' + name + '</b><br>With 30% risk: <b>' + f1(b.model_with_risk) + '</b>' },
                { value: b.actual, kind: 'actual', tip: '<b>' + name + '</b><br>Published cost: <b>' + f1(b.actual) + (b.actual_high > b.actual ? ' to ' + f1(b.actual_high) : '') + '</b><br><small>' + b.note + '</small>' }] };
    })
  });
  const cap = function (t) { return t.charAt(0).toUpperCase() + t.slice(1).replace(/ bn/g, 'bn').replace(/ M /g, 'm '); };
  PTS.table($('#cost-backtest-table'), [
    { key: 'name', label: 'Project', fmt: function (v) { return v.replace('Zurich', 'Zürich'); } }, { key: 'km', label: 'Tunnel, km', num: true, fmt: function (v) { return F.n(v, v % 1 ? 1 : 0); } },
    { key: 'platform_m', label: 'Platform track, m', num: true, fmt: function (v) { return F.n(v, 0); } }, { key: 'model_no_risk', label: 'Our prices, no risk', num: true, fmt: function (v) { return F.n(v, 1); } },
    { key: 'model_with_risk', label: 'With 30% risk', num: true, fmt: function (v) { return F.n(v, 1); } },
    { key: 'actual', label: 'Published cost', num: true, fmt: function (v, r) { return r.actual_high > v ? F.n(v, 1) + ' to ' + F.n(r.actual_high, 1) : F.n(v, 1); } }, { key: 'note', label: 'Note', fmt: cap }], bt);
});
