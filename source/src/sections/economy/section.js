PTS.section('economy', function (root) {
  'use strict';
  const FIN = PTS.data.finance, P = FIN.params, K = FIN.cases, F = PTS.fmt, C = PTS.chart, M = PTS.model, own = PTS.data.economy;
  const $ = function (sel) { return root.querySelector(sel); };
  const mEur = function (v) { return F.m(v); };
  const a0 = M.accounts({});

  // ---- benefits by line (central case, recomputed in the browser; the same figures as the finance case 'central')
  const col = function (k) { return /^Time saved/.test(k) ? 'var(--s1)' : /given up/.test(k) ? 'var(--s8)' : 'var(--s3)'; };
  C.bars($('#eco-benefits-chart'), { fmt: mEur, rows: Object.keys(a0.benefits).map(function (k) { return { label: k, value: a0.benefits[k], color: col(k) }; })
    .concat([{ sep: true }, { label: 'Total', value: a0.benefit_total, color: 'var(--neutral-mark)', hl: true }]) });

  // ---- what public budgets get back, three readings against the repayment
  const reading = function (mode, label) { const a = M.accounts({ tax_wider: mode }); return { label: label, value: a.tax_total, color: 'var(--s3)', tip: '<b>' + label + '</b><br>' + mEur(a.tax_total) + ' a year<br><small>' + F.pct(a.tax_share_of_annuity) + ' of the yearly repayment of construction</small>' }; };
  C.bars($('#eco-tax-chart'), { fmt: mEur, rows: [reading('low', 'Nothing is new for the country'), reading('central', 'As the appraisal counts it'), reading('high', 'Every job is new and fully taxed'),
    { sep: true }, { label: 'Yearly repayment of construction', value: a0.annuity, color: 'var(--s8)', hl: true }] });

  // ---- comparison with other projects: one row for the triangle, drawn with growth (the basis nearest to the others), the band from the flat case
  const f2 = function (v) { return F.n(v, 2); };
  const mine = (function () {
    const g = K.growth, flat = K.central, r45 = K.rate45, r45f = K.rate45_flat;
    const tip = function (what, v, vFlat) { return '<b>This project, the triangle</b><br>' + what + ': <b>' + f2(v) + '</b> with benefits growing ' + F.pct(P.growth, 1) + ' a year, ' + f2(vFlat) + ' flat<br><small>3% rate. At 4.5%: ' + f2(r45.econ_cover_all) + ' with growth, ' + f2(r45f.econ_cover_all) + ' flat, on all benefits. On cost net of income: ' + f2(g.econ_cover_net) + ' with growth, ' + f2(flat.econ_cover_net) + ' flat</small>'; };
    return [{ label: 'This project', sub: '€' + F.n(g.capex, 0) + 'bn, 3% rate', hl: true, lo: flat.econ_cover_all, hi: g.econ_cover_all,
              marks: [{ value: g.econ_cover_transport, kind: 'conv', tip: tip('Transport benefits', g.econ_cover_transport, flat.econ_cover_transport) }, { value: g.econ_cover_all, kind: 'wider', tip: tip('With wider effects', g.econ_cover_all, flat.econ_cover_all) }] }];
  })();
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

  // ---- what would have to be true: each lever on its own against the central case, then the combined cases (all read from the finance cases)
  const c0 = K.central.econ_cover_all;
  const step = function (label, name, basis, color) {
    const a = K[name], d = a.econ_cover_all - c0;
    return { label: label + ' <span class="tag ' + (basis === 'sourced' ? 'sourced' : 'assume') + '">' + basis + '</span>', value: a.econ_cover_all, color: color || 'var(--s1)', mark: c0,
             tip: '<b>' + label + '</b><br>Benefits ' + F.bn(a.benefit_total, 2) + ' a year against a yearly cost of ' + F.bn(a.yearly_cost, 2) + '<br><b>' + F.pct(a.econ_cover_all) + '</b> <small>(' + F.signed(d * 100, 1) + ' points against the central case)</small>' };
  };
  const rows = [
    { group: 'One lever at a time' },
    step('Central case', 'central', 'sourced', 'var(--neutral-mark)'),
    step('Benefits grow ' + F.pct(P.growth, 1) + ' a year', 'growth', 'assumed'),
    step('Low construction prices and 10% risk', 'low_cost', 'sourced'),
    step('TGV passengers’ ride across Paris counted against them', 'ride', 'assumed'),
    step('Higher traffic: the top of the evidence on direct trains and joined lines', 'high_traffic', 'sourced'),
    step('Running costs at the low end of the records', 'low_running', 'sourced'),
    { group: 'Levers combined' },
    step('Low prices, higher traffic and growth', 'best', 'assumed', 'var(--s3)'),
    step('The same with low running costs and shops at full yield', 'all_levers', 'assumed', 'var(--s3)')
  ];
  C.bars($('#eco-ladder-chart'), { rows: rows, fmt: function (v) { return F.pct(v); }, max: 1.0 });
});
