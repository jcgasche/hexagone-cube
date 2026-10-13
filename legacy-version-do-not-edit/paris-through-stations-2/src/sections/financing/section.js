PTS.section('financing', function (root) {
  'use strict';
  const FIN = PTS.data.finance, B = FIN.base, P = FIN.params, F = PTS.fmt, h = PTS.h, C = PTS.chart, M = PTS.model;
  const $ = function (sel) { return root.querySelector(sel); };
  const mEur = function (v) { return F.m(v); }, bn2 = function (v) { return F.bn(v, 2); };

  // colours by line, fixed so that a line keeps its colour in every chart of the section
  const COST = { 'Running and maintaining tunnels and stations': 'var(--s8)', 'Renewal of rail systems, set aside each year': 'var(--s7)', 'Extra running of regional trains': 'var(--neutral-mark)' };
  const REV = { 'Charge on high-speed passengers': 'var(--s1)', 'Track charges on the net change in TGV journeys': 'var(--s2)', 'New Navigo pass holders': 'var(--s3)', 'Fares from new regional express passengers': 'var(--s6)',
                'Fee paid by the regional transport authority': 'var(--s4)', 'Shops in the new station halls': 'var(--s5)', 'Share of the operators’ saving on trainsets': 'var(--s7)', 'Charge on regional express passengers': 'var(--s8)' };
  const CAP = { 'Surplus of the operations account': 'var(--s1)', 'Regional business tax package': 'var(--s2)', 'Payroll transport levy': 'var(--s5)', 'European grant': 'var(--s3)' };
  const SHORT = { 'Renewal of rail systems, set aside each year': 'Renewal of rail systems', 'Regional business tax package': 'Tax on businesses in the region', 'Track charges on the net change in TGV journeys': 'Track charges on new TGV journeys',
                  'Share of the operators’ saving on trainsets': 'Operators’ saving on trainsets, share', 'Charge on regional express passengers': 'Charge on regional express passengers' };
  const lab = function (k) { return SHORT[k] || k; };
  const parts = function (obj, colors) { return Object.keys(obj).map(function (k) { return { label: lab(k), value: obj[k], color: colors[k] || 'var(--neutral-mark)' }; }); };

  function opsChart(host, a, fmt) {
    const neg = Object.keys(a.ops_rev).filter(function (k) { return a.ops_rev[k] < 0; });
    C.stack(host, { fmt: fmt, max: Math.max(a.ops_cost_total, a.ops_rev_total, 0.01) * 1.02, rows: [
      { label: 'Running costs', parts: parts(a.ops_cost, COST), text: fmt(a.ops_cost_total) },
      { label: 'Income' + (neg.length ? '<br><small style="color:var(--muted)">after ' + fmt(-neg.reduce(function (t, k) { return t + a.ops_rev[k]; }, 0)) + ' of track charges lost</small>' : ''), parts: parts(a.ops_rev, REV), text: fmt(a.ops_rev_total) }] });
  }
  function capChart(host, a, fmt) {
    const need = [{ label: 'Repayment of construction', value: a.annuity, color: 'var(--s8)' }, { label: 'Shortfall of operations', value: Math.max(0, -a.ops_balance), color: 'var(--s7)' }];
    const src = parts(a.cap_sources, CAP).concat([{ label: 'Grants from the State, the Region and the City', value: Math.max(0, a.cap_gap), color: 'var(--neutral-mark)' }]);
    C.stack(host, { fmt: fmt, max: Math.max(a.cap_need, a.cap_sources_total) * 1.02, rows: [{ label: 'To find each year', parts: need, text: fmt(a.cap_need) }, { label: 'Where it comes from', parts: src, text: a.cap_gap > 0 ? fmt(a.cap_need) : fmt(a.cap_sources_total) }] });
  }

  // ---- overview of the two accounts, central case
  (function () {
    const a = M.accounts({});
    opsChart($('#fin-ops-chart'), a, mEur); capChart($('#fin-cap-chart'), a, bn2);
    $('#fin-ops-title').textContent = 'Operations: income covers ' + F.pct(a.ops_cover, 1) + ' of the running costs';
    $('#fin-cap-title').textContent = 'Capital: after a new tax on businesses, grants of ' + F.bn(a.grant_bn, 0) + ' remain to be found';
  })();

  // ---- cases of the operations account (the same cases as the exported finance file)
  const cases = [['high', 'Running costs as on the first RER E section', { om_scale: 'high' }], ['central', 'Central case, with the income package', {}], ['low', 'Running costs at the low end', { om_scale: 'low' }],
                 ['shops', 'Shops at full yield', { shop_net: 1 }], ['tgv', 'TGV charge alone: no regional express charge, no trainset share', { rex_second: 0, rex_through: 0, fleet_capture: 0 }],
                 ['none', 'No charge on any passenger', { charge_end: 0, charge_through: 0, rex_second: 0, rex_through: 0 }]];
  C.bars($('#fin-ops-cases'), { fmt: function (v) { return F.pct(v, 1); }, max: 1.5, rows: cases.map(function (c) {
    const a = M.accounts(c[2]);
    return { label: c[1], value: a.ops_cover, color: c[0] === 'central' ? 'var(--s1)' : 'var(--s3)', mark: 1, hl: c[0] === 'central', tip: '<b>' + c[1] + '</b><br>Income ' + mEur(a.ops_rev_total) + ' against running costs ' + mEur(a.ops_cost_total) + '<br>Covered: <b>' + F.pct(a.ops_cover, 1) + '</b>' };
  }) });

  // ---- gain against charge, two groups on their own scales
  const t = M.accounts({}).tgv, gain = PTS.clear($('#fin-gain-chart'));
  [['Passenger from the Paris region', t.gain_paris_euro, P.charge_end], ['Passenger crossing Paris', t.gain_cross_euro, P.charge_through]].forEach(function (g) {
    const box = h('div', { style: { 'margin-bottom': '10px' } }); gain.appendChild(box);
    C.bars(box, { fmt: function (v) { return F.eur(v, 2); }, rows: [{ group: g[0] }, { label: 'Average gain in time', value: g[1], color: 'var(--s3)' }, { label: 'Charge', value: g[2], color: 'var(--s1)' }] });
  });

  // ---- charge curves
  const curve = FIN.charge_curve;
  const euro = function (v) { return '€' + F.n(v, 2); };
  C.line($('#fin-curve-money'), { label: 'Money from the charge by level of charge', height: 250,
    x: { label: 'Charge per departure or arrival, euros', fmt: function (v) { return F.n(v, 0); }, tipLabel: function (v) { return 'Charge of ' + euro(v); }, min: 0, max: 10 },
    y: { fmt: function (v) { return F.n(v, 0); }, min: 0 },
    vlines: [{ x: P.charge_end, label: euro(P.charge_end) }],
    series: [{ name: 'Collected', points: curve.map(function (c) { return [c.charge, c.gross * 1000]; }) },
             { name: 'After lost track charges', points: curve.map(function (c) { return [c.charge, c.net * 1000]; }), dash: true }] });
  C.line($('#fin-curve-traffic'), { label: 'Change in high-speed journeys by level of charge', height: 250,
    x: { label: 'Charge per departure or arrival, euros', fmt: function (v) { return F.n(v, 0); }, tipLabel: function (v) { return 'Charge of ' + euro(v); }, min: 0, max: 10 },
    y: { fmt: function (v) { return F.signed(v, 0); } },
    vlines: [{ x: P.charge_end, label: euro(P.charge_end) }], hlines: [{ y: 0, label: 'Today’s traffic' }],
    series: [{ name: 'Traffic falls 0.7% for 1% on fares', points: curve.map(function (c) { return [c.charge, c.net_new]; }) },
             { name: 'Traffic falls 0.5%', points: curve.map(function (c) { return [c.charge, c.net_new_low]; }), dash: true }] });

  // ---- Navigo
  C.bars($('#fin-navigo-chart'), { fmt: function (v) { return '€' + F.n(v * 1000, 0) + 'm'; }, rows: [[0.09, '9%, as measured in London'], [0.27, '27%, as in Sydney'], [P.navigo_new, F.pct(P.navigo_new) + ', used here'], [0.5, '50%'], [1, '100%, upper bound']].map(function (r) {
    const a = M.accounts({ navigo_new: r[0] });
    return { label: r[1], value: a.ops_rev['New Navigo pass holders'], color: 'var(--s3)', hl: r[0] === P.navigo_new, tip: '<b>' + r[1] + '</b><br>' + F.n(a.pass_holders, 0) + ' new passes<br><b>€' + F.n(a.ops_rev['New Navigo pass holders'] * 1000, 0) + 'm a year</b><br>Running costs covered: ' + F.pct(a.ops_cover, 1) };
  }) });

  // ---- calculator
  const st = Object.assign({}, B.defaults), ctl = {};
  const tile = function (n, k, d, tc) { return h('div', { class: 'tile', style: tc ? { '--tc': tc } : null }, h('span', { class: 'n', html: n }), h('span', { class: 'k', text: k }), h('span', { class: 'd', text: d })); };
  const render = function () {
    const a = M.accounts(st);
    const tiles = PTS.clear($('#fin-o-tiles'));
    tiles.appendChild(tile(F.pct(a.ops_cover, 1), 'of running costs covered', a.ops_balance >= 0 ? 'Surplus of ' + mEur(a.ops_balance) + ' a year' : 'Shortfall of ' + mEur(-a.ops_balance) + ' a year', a.ops_balance >= 0 ? 'var(--good)' : 'var(--alt)'));
    tiles.appendChild(tile(a.cap_gap > 0 ? '€' + F.n(a.grant_bn, 1) + '<small>bn</small>' : 'None', 'of grants needed',
      a.cap_gap > 0 ? 'Against a construction cost of ' + F.bn(a.capex) + (a.shortfall_bn > 0.05 ? '; ' + F.bn(a.shortfall_bn) + ' of it covers the shortfall of operations' : '') + '. Public money in all: ' + F.pct(a.public_share) + ' of the cost'
                    : 'The sources chosen exceed the need by ' + bn2(-a.cap_gap) + ' a year', 'var(--today)'));
    tiles.appendChild(tile(F.pct(a.econ_cover_all), 'share of benefits', 'Yearly benefits ' + bn2(a.benefit_total) + ' against a yearly cost of ' + bn2(a.yearly_cost), 'var(--s3)'));
    const list = function (obj, color) { return Object.keys(obj).filter(function (k) { return Math.abs(obj[k]) > 1e-9; }).map(function (k) { return { label: lab(k), value: obj[k], color: color }; }); };
    C.bars($('#fin-o-ops'), { compact: true, fmt: mEur, rows: [{ group: 'Running costs' }].concat(list(a.ops_cost, 'var(--s8)'), [{ label: 'Total running costs', value: a.ops_cost_total, color: 'var(--s8)', hl: true }, { group: 'Income' }],
      list(a.ops_rev, 'var(--s1)'), [{ label: 'Total income', value: a.ops_rev_total, color: 'var(--s1)', hl: true }]) });
    C.bars($('#fin-o-cap'), { compact: true, fmt: bn2, rows: [{ group: 'To find each year' }, { label: 'Repayment of construction', value: a.annuity, color: 'var(--s8)' }].concat(
      a.ops_balance < 0 ? [{ label: 'Shortfall of operations', value: -a.ops_balance, color: 'var(--s8)' }] : [], [{ group: 'Where it comes from' }], list(a.cap_sources, 'var(--s2)'),
      [{ label: a.cap_gap >= 0 ? 'Grants from the State, the Region and the City' : 'More than needed', value: Math.abs(a.cap_gap), color: 'var(--neutral-mark)', hl: true }]) });
    const r = a.ops_rev, pos = function (v) { return Math.max(0, v || 0); };
    const who = [
      { label: 'High-speed passengers, net of track charges lost', value: pos(r['Charge on high-speed passengers'] + Math.min(0, r['Track charges on the net change in TGV journeys'])), color: 'var(--s1)' },
      { label: 'Regional passengers and their transport authority', value: pos(r['Charge on regional express passengers']) + pos(r['New Navigo pass holders']) + pos(r['Fares from new regional express passengers']) + pos(r['Fee paid by the regional transport authority']), color: 'var(--s3)' },
      { label: 'Train operators', value: pos(r['Track charges on the net change in TGV journeys']) + pos(r['Share of the operators’ saving on trainsets']), color: 'var(--s7)' },
      { label: 'Shops', value: pos(r['Shops in the new station halls']), color: 'var(--s4)' },
      { label: 'Businesses of the region, through taxes', value: a.cap_sources['Regional business tax package'] + a.cap_sources['Payroll transport levy'], color: 'var(--s2)' },
      { label: 'Europe', value: a.cap_sources['European grant'], color: 'var(--s6)' },
      { label: 'Taxpayers, through grants', value: pos(a.cap_gap), color: 'var(--neutral-mark)' }];
    const total = who.reduce(function (s, p) { return s + p.value; }, 0);
    C.stack($('#fin-o-who'), { fmt: bn2, rows: [{ label: 'Yearly cost of both accounts', parts: who, text: bn2(total) }] });
    $('#fin-o-who-note').textContent = 'Users, operators and shops carry ' + F.pct((who[0].value + who[1].value + who[2].value + who[3].value) / total) + ', taxes on businesses ' + F.pct(who[4].value / total) + ', grants ' + F.pct((who[5].value + who[6].value) / total) + '.';
    const d = PTS.clear($('#fin-o-tgv'));
    [['Journeys added by the project', F.signed(a.tgv.new_before_charge, 1) + ' million'], ['Journeys given up because of the charge', F.signed(-a.tgv.lost, 1) + ' million'], ['Change against today', F.signed(a.tgv.net_new, 1) + ' million'],
     ['Money collected by the TGV charge', mEur(a.tgv.charge_gross)], ['Money collected by the regional express charge', mEur(a.ops_rev['Charge on regional express passengers'] || 0)], ['New Navigo passes', F.n(a.pass_holders, 0)]].forEach(function (x, i) { d.appendChild(h('dt', { class: i === 2 ? 'sum' : null, text: x[0] })); d.appendChild(h('dd', { class: i === 2 ? 'sum' : null, text: x[1] })); });
  };
  const set = function (k) { return function (v) { st[k] = v; render(); }; };
  ctl.cost = PTS.seg($('#fin-c-project'), [['low', 'Low'], ['central', 'Central'], ['high', 'High']], st.cost, set('cost'), 'Construction cost');
  ctl.traffic = PTS.seg($('#fin-c-project'), [['low', 'Low'], ['central', 'Central'], ['high', 'High']], st.traffic, set('traffic'), 'New traffic');
  const sl = function (host, key, cfg) { ctl[key] = PTS.slider($(host), Object.assign({ value: st[key] }, cfg), set(key)); };
  sl('#fin-c-growth', 'growth', { label: 'Growth of traffic and benefits each year', min: 0, max: 0.02, step: 0.0025, format: function (v) { return F.pct(v, 2); }, note: 'Zero in the central case; 1.5% is the high test' });
  sl('#fin-c-charge', 'charge_end', { label: 'Charge per departure or arrival in Paris', min: 0, max: 10, step: 0.05, format: euro, note: 'A metro ticket costs €2.55; the air solidarity tax is €7.40' });
  sl('#fin-c-charge', 'charge_through', { label: 'Charge for crossing Paris on a direct train', min: 0, max: 30, step: 0.1, format: euro, note: 'The time gained is counted at about €' + F.n(t.gain_cross_euro, 0) + '; only ' + F.n(t.through, 1) + ' million passengers pay it' });
  sl('#fin-c-charge', 'fare_response', { label: 'Fall in traffic when fares rise 1%', min: -1.2, max: -0.2, step: 0.05, format: function (v) { return F.n(-v, 2) + '%'; }, note: 'French experts use 0.7; perhaps 0.5 where prices vary with demand or the charge is billed to operators' });
  sl('#fin-c-rex', 'rex_second', { label: 'Charge for getting off at the second station', min: 0, max: 10, step: 0.05, format: euro, note: F.n(B.traffic.central.rex_second, 1) + ' million passengers a year; no loss of traffic modelled' });
  sl('#fin-c-rex', 'rex_through', { label: 'Charge for crossing Paris on a regional express train', min: 0, max: 20, step: 0.1, format: euro, note: F.n(B.traffic.central.rex_through, 1) + ' million passengers a year, an assumption' });
  sl('#fin-c-other', 'om_scale', { label: 'Running cost of tunnels and stations', min: 0.5, max: 1.3, step: 0.01, format: function (v) { return F.pct(v) + ' of the central rate'; }, note: 'About ' + F.pct(P.om_low) + ': tunnels as on the RER network; about ' + F.pct(P.om_high) + ': everything as on the first RER E section' });
  sl('#fin-c-other', 'navigo_new', { label: 'New suburban journeys made by new pass holders', min: 0, max: 1, step: 0.01, format: function (v) { return F.pct(v); } });
  sl('#fin-c-other', 'fleet_capture', { label: 'Share of operators’ trainset saving recovered', min: 0, max: 1, step: 0.1, format: function (v) { return F.pct(v); }, note: 'Half in the central case' });
  sl('#fin-c-other', 'shop_net', { label: 'Share of shop rents counted as new', min: 0, max: 1, step: 0.1, format: function (v) { return F.pct(v); }, note: 'Half in the central case; 100% is the full yield' });
  sl('#fin-c-capital', 'levy', { label: 'Tax on businesses in the region, a year', min: 0, max: 1.5, step: 0.05, format: bn2, note: 'The Grand Paris Express receives €0.90bn a year' });
  sl('#fin-c-capital', 'payroll_pts', { label: 'Rise in the payroll transport levy', min: 0, max: 0.5, step: 0.05, format: function (v) { return F.n(v, 2) + ' point'; }, note: 'About €160m a year per 0.1 point in Paris and the inner ring' });
  sl('#fin-c-capital', 'eu_grant', { label: 'European grant', min: 0, max: 5, step: 0.5, format: function (v) { return F.bn(v, 1); } });
  sl('#fin-c-capital', 'rate', { label: 'Interest rate above inflation', min: 0.02, max: 0.05, step: 0.0025, format: function (v) { return F.pct(v, 2); }, note: 'Official discount rates run from 3.2% to 4.6%' });
  const apply = function (o) { Object.assign(st, B.defaults, o); Object.keys(ctl).forEach(function (k) { ctl[k].set(st[k], true); }); render(); };
  const presets = {
    central: function () { return {}; },
    none: function () { return { charge_end: 0, charge_through: 0, rex_second: 0, rex_through: 0 }; },
    tgv: function () { return { rex_second: 0, rex_through: 0, fleet_capture: 0 }; },
    even: function () { const ch = M.breakevenCharge({}); return { charge_end: Math.min(10, ch), charge_through: Math.min(30, 2 * ch) }; },
    best: function () { return { cost: 'low', traffic: 'high', growth: P.growth, om_scale: Math.round(P.om_low * 100) / 100, shop_net: 1 }; }
  };
  PTS.steps($('#fin-presets'), [['central', 'Central case'], ['none', 'No charge on any passenger'], ['tgv', 'TGV charge alone'], ['even', 'TGV charge that balances operations'], ['best', 'Everything favourable']], 'central', function (k) { apply(presets[k]()); });
  render();
});
