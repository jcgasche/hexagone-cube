PTS.section('economy', function (root) {
  'use strict';
  const FIN = PTS.data.finance, P = FIN.params, F = PTS.fmt, C = PTS.chart, M = PTS.model, own = PTS.data.economy;
  const $ = function (sel) { return root.querySelector(sel); };
  const mEur = function (v) { return F.m(v); };
  const a0 = M.accounts({});

  // ---- benefits by line
  const col = function (k) { return /^Time saved/.test(k) ? 'var(--s1)' : /given up/.test(k) ? 'var(--s8)' : 'var(--s3)'; };
  C.bars($('#eco-benefits-chart'), { fmt: mEur, rows: Object.keys(a0.benefits).map(function (k) { return { label: k, value: a0.benefits[k], color: col(k) }; })
    .concat([{ sep: true }, { label: 'Total', value: a0.benefit_total, color: 'var(--neutral-mark)', hl: true }]) });

  // ---- what public budgets get back, three readings against the repayment
  const reading = function (mode, label) { const a = M.accounts({ tax_wider: mode }); return { label: label, value: a.tax_total, color: 'var(--s3)', tip: '<b>' + label + '</b><br>' + mEur(a.tax_total) + ' a year<br><small>' + F.pct(a.tax_share_of_annuity) + ' of the yearly repayment of layout A</small>' }; };
  C.bars($('#eco-tax-chart'), { fmt: mEur, rows: [reading('low', 'Nothing is new for the country'), reading('central', 'As the appraisal counts it'), reading('high', 'Every job is new and fully taxed'),
    { sep: true }, { label: 'Yearly repayment of construction, layout A', value: a0.annuity, color: 'var(--s8)', hl: true }] });

  // ---- comparison with other projects
  const f2 = function (v) { return F.n(v, 2); };
  const g = { growth: P.growth };
  const mine = [['A', 'This project, layout A', {}], ['B', 'This project, layout B', {}], ['B', 'Layout B, low prices and high traffic', { cost: 'low', traffic: 'high' }]].map(function (x) {
    const a = M.accounts(Object.assign({ layout: x[0] }, g, x[2])), flat = M.accounts(Object.assign({ layout: x[0] }, x[2])), r45 = M.accounts(Object.assign({ layout: x[0], rate: 0.045 }, g, x[2]));
    const tip = function (what, v) { return '<b>' + x[1] + '</b><br>' + what + ': <b>' + f2(v) + '</b><br><small>3% rate, benefits growing ' + F.pct(P.growth, 1) + ' a year. With wider effects: ' + f2(flat.econ_cover_all) + ' if benefits do not grow, ' + f2(r45.econ_cover_all) + ' at a 4.5% rate</small>'; };
    return { label: x[1], sub: '€' + F.n(a.capex, 0) + 'bn', hl: true, marks: [{ value: a.econ_cover_transport, kind: 'conv', tip: tip('Transport benefits', a.econ_cover_transport) }, { value: a.econ_cover_all, kind: 'wider', tip: tip('With wider effects', a.econ_cover_all) }] };
  });
  const others = own.projects.map(function (p) {
    const head = '<b>' + p.name + '</b><br>' + p.sub + '<br>';
    const marks = (p.convs || [p.conv]).map(function (v) { return { value: v, kind: 'conv', tip: head + 'Transport benefits: <b>' + (p.convs ? f2(p.convs[0]) + ' and ' + f2(p.convs[1]) : p.lo != null ? f2(p.lo) + ' to ' + f2(p.hi) : f2(v)) + '</b>' }; });
    if (p.wider != null) marks.push({ value: p.wider, kind: 'wider', tip: head + 'With wider effects: <b>' + f2(p.wider) + '</b>' });
    (p.posts || (p.post != null ? [p.post] : [])).forEach(function (v) { marks.push({ value: v, kind: 'post', tip: '<b>' + p.name + '</b><br>' + p.postnote }); });
    const lo = p.convs ? p.convs[0] : p.lo, hi = p.convs ? p.convs[1] : p.hi;
    return { label: p.name, sub: '€' + p.cost + 'bn', lo: lo, hi: hi, marks: marks };
  });
  C.ranges($('#eco-compare-chart'), { label: 'Benefits divided by costs for comparable projects and for this one', domain: [0, 3.2], fmt: function (v) { return F.n(v, 1); }, axisLabel: 'Benefits divided by costs', rowH: 32, labelWidth: 330,
    refs: [{ value: 1, label: 'Benefits equal costs' }], rangeLabel: 'Published range',
    kinds: { conv: { label: 'Transport benefits only, at approval', color: 'var(--s1)', shape: 'dot' }, wider: { label: 'With wider economic effects', color: 'var(--s1)', shape: 'ring' }, post: { label: 'Measured after opening', color: 'var(--s2)', shape: 'diamond' } },
    rows: mine.concat(others) });

  // ---- what would have to be true
  const steps = [['Central case', {}], ['and benefits grow ' + F.pct(P.growth, 1) + ' a year', { growth: P.growth }], ['and low construction prices', { growth: P.growth, cost: 'low' }],
                 ['and higher traffic', { growth: P.growth, cost: 'low', traffic: 'high' }], ['and running costs at the low end', { growth: P.growth, cost: 'low', traffic: 'high', om_scale: 'low' }]];
  const rows = [];
  [['A', 'Layout A', 'var(--s1)'], ['B', 'Layout B', 'var(--s3)']].forEach(function (L) {
    rows.push({ group: L[1] });
    steps.forEach(function (st) { const a = M.accounts(Object.assign({ layout: L[0] }, st[1])); rows.push({ label: st[0], value: a.econ_cover_all, color: L[2], mark: 1,
      tip: '<b>' + L[1] + ', ' + st[0].replace(/^and /, 'adding ') + '</b><br>Benefits ' + F.bn(a.benefit_total, 2) + ' a year against a yearly cost of ' + F.bn(a.yearly_cost, 2) + '<br><b>' + F.pct(a.econ_cover_all) + '</b>' }); });
  });
  C.bars($('#eco-ladder-chart'), { rows: rows, fmt: function (v) { return F.pct(v); }, max: 1.1 });
});
