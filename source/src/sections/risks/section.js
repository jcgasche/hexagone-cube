PTS.section('risks', function (root) {
  'use strict';
  const D = PTS.data.model, F = PTS.fmt, C = PTS.chart, h = PTS.h;
  const $ = function (sel) { return root.querySelector(sel); };

  // ---- one assumption at a time (the triangle; tests that change only the project's income are left out of the chart)
  const S = D.sens, Y = D.yearly;
  const rows = Object.keys(S).filter(function (k) { return !/^Platforms no longer cap/.test(k); }).map(function (k) { return { label: k, value: S[k].cover_all }; });
  rows.push({ label: 'Time savings only, no comfort or wider effects', value: Y.cover_time });
  rows.push({ label: 'Official discount rate for regional projects, 3.6%', value: D.rate_tests['3.6'].all });
  rows.push({ label: 'Official discount rate for long-distance projects, 4.6%', value: D.rate_tests['4.6'].all });
  rows.push({ label: 'Benefits grow 1.5% a year with incomes and traffic', value: PTS.model.accounts({ growth: PTS.data.finance.params.growth, charge_end: 0, charge_through: 0, rex_second: 0, rex_through: 0 }).econ_cover_all });
  rows.sort(function (a, b) { return b.value - a.value; });
  const c = Y.cover_all;
  C.bars($('#risk-sens-chart'), { fmt: function (v) { return F.pct(v); }, max: 0.55, rows: rows.map(function (r) {
    const d = r.value - c;
    return { label: r.label, value: r.value, mark: c, color: Math.abs(d) < 0.005 ? 'var(--neutral-mark)' : d > 0 ? 'var(--s3)' : 'var(--s2)',
             tip: '<b>' + r.label + '</b><br>Benefits cover <b>' + F.pct(r.value, 1) + '</b> of the yearly cost<br><small>' + F.signed(d * 100, 1) + ' points against the central case of ' + F.pct(c, 1) + '</small>' };
  }) });
  $('#risk-sens-title').textContent = 'Benefits cover from ' + F.pct(rows[rows.length - 1].value) + ' to ' + F.pct(rows[0].value) + ' of the yearly cost, around a central case of ' + F.pct(c);

  // ---- filter of the study points (status, and subject from the row's data-t letter)
  const trs = PTS.$$('#risk-points tbody tr', root), count = $('#risk-count');
  const state = { s: 'all', t: 'all' };
  const apply = function () {
    let n = 0, open = 0;
    trs.forEach(function (tr) { const ok = (state.s === 'all' || tr.dataset.s === state.s) && (state.t === 'all' || tr.dataset.t === state.t); tr.hidden = !ok; if (ok) { n++; if (/^I\d+$/.test(tr.firstElementChild.textContent.trim())) open++; } });
    const tot = function (s) { return trs.filter(function (tr) { return tr.dataset.s === s; }).length; };
    count.textContent = n + ' of ' + trs.length + ' points shown, ' + open + ' of them study points of the brief. In all: ' + tot('Estimated') + ' estimated, ' + tot('Assumed') + ' assumed, ' + tot('Open') + ' open.';
  };
  PTS.seg($('#risk-filter'), [['all', 'All'], ['Estimated', 'Estimated'], ['Assumed', 'Assumed'], ['Open', 'Open']], 'all', function (v) { state.s = v; apply(); }, 'Status');
  PTS.seg($('#risk-filter'), [['all', 'All'], ['A', 'Operation'], ['B', 'Cost'], ['C', 'Passengers'], ['D', 'Money'], ['E', 'City']], 'all', function (v) { state.t = v; apply(); }, 'Subject');
  trs.forEach(function (tr) { const td = tr.children[3]; if (td) { td.innerHTML = ''; td.appendChild(h('span', { class: 'tag ' + (tr.dataset.s === 'Estimated' ? 'sourced' : tr.dataset.s === 'Assumed' ? 'assume' : 'sketch'), text: tr.dataset.s })); } });
  apply();
});
