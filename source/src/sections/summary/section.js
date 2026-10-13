PTS.section('summary', function (root) {
  'use strict';
  const F = PTS.fmt, C = PTS.chart, M = PTS.model;
  const A = M.accounts(), mEur = function (v) { return F.m(v); };     // the central case: the triangle with the income package
  const rev = A.ops_rev, revRows = Object.keys(rev).map(function (k) { return { label: k, value: rev[k], color: 'var(--s1)' }; });
  C.bars(root.querySelector('#sum-ops'), { fmt: mEur, rows: [
    { label: 'Running costs', value: A.ops_cost_total, color: 'var(--s8)', hl: true },
    { label: 'Income', value: A.ops_rev_total, color: 'var(--s1)', hl: true, text: mEur(A.ops_rev_total) + ' (' + F.pct(A.ops_cover) + ')' },
    { group: 'Income, line by line' }].concat(revRows) });
  C.bars(root.querySelector('#sum-cap'), { fmt: mEur, rows: [
    { label: 'Repayment of construction', value: A.annuity, color: 'var(--s8)' },
    { label: 'Benefits to the country', value: A.benefit_total, color: 'var(--s3)', text: mEur(A.benefit_total) + ' (' + F.pct(A.econ_cover_capital) + ')' },
    { label: 'Returned to public budgets, middle reading', value: A.tax_total, color: 'var(--s4)' }] });
});
