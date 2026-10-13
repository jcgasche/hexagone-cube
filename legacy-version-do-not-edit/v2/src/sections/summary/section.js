PTS.section('summary', function (root) {
  'use strict';
  const F = PTS.fmt, C = PTS.chart, M = PTS.model;
  const A = M.accounts({ layout: 'A' }), B = M.accounts({ layout: 'B' }), mEur = function (v) { return F.m(v); };
  C.bars(root.querySelector('#sum-ops'), { fmt: mEur, rows: [
    { group: 'Layout A' }, { label: 'Running costs', value: A.ops_cost_total, color: 'var(--s8)' }, { label: 'Income', value: A.ops_rev_total, color: 'var(--s1)', text: mEur(A.ops_rev_total) + ' (' + F.pct(A.ops_cover) + ')' },
    { group: 'Layout B' }, { label: 'Running costs', value: B.ops_cost_total, color: 'var(--s8)' }, { label: 'Income', value: B.ops_rev_total, color: 'var(--s1)', text: mEur(B.ops_rev_total) + ' (' + F.pct(B.ops_cover) + ')' }] });
  C.bars(root.querySelector('#sum-cap'), { fmt: mEur, rows: [
    { group: 'Layout A' }, { label: 'Repayment of construction', value: A.annuity, color: 'var(--s8)' }, { label: 'Benefits to the country', value: A.benefit_total, color: 'var(--s3)', text: mEur(A.benefit_total) + ' (' + F.pct(A.econ_cover_capital) + ')' },
    { label: 'Returned to public budgets, middle reading', value: A.tax_total, color: 'var(--s4)' },
    { group: 'Layout B' }, { label: 'Repayment of construction', value: B.annuity, color: 'var(--s8)' }, { label: 'Benefits to the country', value: B.benefit_total, color: 'var(--s3)', text: mEur(B.benefit_total) + ' (' + F.pct(B.econ_cover_capital) + ')' },
    { label: 'Returned to public budgets, middle reading', value: B.tax_total, color: 'var(--s4)' }] });
});
