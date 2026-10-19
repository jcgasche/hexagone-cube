PTS.section('economy', function (root) {
  'use strict';
  const FIN = PTS.data.finance, K = FIN.cases, FR = PTS.data.french, MOD = PTS.data.model, F = PTS.fmt, C = PTS.chart, h = PTS.h, s = PTS.s, own = PTS.data.economy;
  const $ = function (sel) { return root.querySelector(sel); };
  const cen = K.central, fc = FR.cases.central, st = FR.study.central, NM = FR.names, KEY = NM.key;
  const mEur = function (v) { return F.m(v); }, bn1 = function (v) { return F.bn(v, 1); }, bn2 = function (v) { return F.bn(v, 2); };
  const signedBn = function (v) { return (v < 0 ? '-' : '+') + F.bn(Math.abs(v), 1); }, bnS = function (v) { return (v < 0 ? '-' : '') + F.bn(Math.abs(v), Math.abs(v) < 0.95 ? 2 : 1); };
  const isWider = function (k) { return NM.wider.indexOf(k) >= 0; };
  const hm = function (min) { const H = Math.floor(min / 60), M = Math.round(min - H * 60); return H + 'h' + (M < 10 ? '0' : '') + M; };

  // ---- one colour per family of benefits, used by every chart of the page
  const FAM = {
    'Passengers’ time': 'var(--s1)', 'Room for more trains in the busy hours': 'var(--s7)', 'The railway’s own gains': 'var(--s2)', 'Comfort and ease': 'var(--s3)',
    'Job access across Paris': 'var(--s4)', 'Environment': 'var(--s6)', 'Parks, land and one-off savings': 'var(--s5)', 'Carbon of the works': 'var(--s8)',
    'Construction and running costs': 'var(--s8)', 'Cost of public funds': 'var(--neutral-mark)', 'Wider effects, measured': 'var(--neutral-mark)'
  };
  const short = function (k) { return k.replace(/\s*\(.*?\)\s*$/, ''); };

  /* Donut. cfg: {slices: [{label, value, color, alpha, note}], fmt, centre: [big, small], share: true}. Values below zero are left out. */
  function donut(host, legendHost, cfg) {
    PTS.clear(host); PTS.clear(legendHost);
    const sl = cfg.slices.filter(function (x) { return x.value > 0; }), total = sl.reduce(function (a, x) { return a + x.value; }, 0);
    const fmt = cfg.fmt || mEur, R = 90, r = 56, cx = 100, cy = 100;
    const svg = s('svg', { viewBox: '0 0 200 200', role: 'img', 'aria-label': cfg.label || 'Share chart' });
    let a = -Math.PI / 2;
    sl.forEach(function (x) {
      const da = x.value / total * 2 * Math.PI, a1 = a + da, big = da > Math.PI ? 1 : 0;
      const p = function (rad, ang) { return (cx + rad * Math.cos(ang)).toFixed(2) + ' ' + (cy + rad * Math.sin(ang)).toFixed(2); };
      let d;
      if (da >= 2 * Math.PI - 1e-6) d = 'M ' + p(R, a) + ' A ' + R + ' ' + R + ' 0 1 1 ' + p(R, a + Math.PI) + ' A ' + R + ' ' + R + ' 0 1 1 ' + p(R, a) + ' M ' + p(r, a) + ' A ' + r + ' ' + r + ' 0 1 0 ' + p(r, a + Math.PI) + ' A ' + r + ' ' + r + ' 0 1 0 ' + p(r, a) + ' Z';
      else d = 'M ' + p(R, a) + ' A ' + R + ' ' + R + ' 0 ' + big + ' 1 ' + p(R, a1) + ' L ' + p(r, a1) + ' A ' + r + ' ' + r + ' 0 ' + big + ' 0 ' + p(r, a) + ' Z';
      const path = s('path', { d: d, class: 'slice', style: { fill: x.color, 'fill-opacity': x.alpha == null ? 1 : x.alpha }, tabindex: 0 });
      PTS.tip.bind(path, '<b>' + x.label + '</b><br>' + fmt(x.value) + ' <small>(' + F.pct(x.value / total) + ')</small>' + (x.note ? '<br><small>' + x.note + '</small>' : ''));
      svg.appendChild(path); a = a1;
    });
    if (cfg.centre) {
      svg.appendChild(s('text', { x: cx, y: cy - 2, 'text-anchor': 'middle', class: 'big', text: cfg.centre[0] }));
      svg.appendChild(s('text', { x: cx, y: cy + 16, 'text-anchor': 'middle', class: 'small', text: cfg.centre[1] }));
    }
    host.appendChild(svg);
    sl.forEach(function (x) {
      legendHost.appendChild(h('li', null, h('i', { style: { '--c': x.color, opacity: x.alpha == null ? 1 : x.alpha } }), h('span', { text: x.label }), h('b', { text: fmt(x.value) }), h('small', { text: F.pct(x.value / total) })));
    });
  }

  // ---- the year at a glance: the bill, who pays it, what comes back (one scale, one legend per bar)
  (function () {
    const oc = cen.ops_cost, src = cen.cap_sources, fams = st.families;
    const mix = function (c, pc) { return 'color-mix(in srgb, ' + c + ' ' + pc + '%, var(--surface))'; };
    const rows = [
      { label: 'What it costs each year', parts: [{ label: 'Repayment of construction', value: cen.annuity, color: 'var(--s8)' }, { label: 'Running tunnels and stations', value: oc['Running and maintaining tunnels and stations'], color: mix('var(--s8)', 65) },
        { label: 'Extra regional trains', value: oc['Extra running of regional trains'], color: mix('var(--s8)', 45) }, { label: 'Renewal set aside', value: oc['Renewal of rail systems, set aside each year'], color: mix('var(--s8)', 30) }], text: bn2(cen.yearly_cost) },
      { label: 'Who pays it', parts: [{ label: 'The project’s own income', value: cen.ops_rev_total, color: 'var(--s1)' }, { label: 'Regional business tax package', value: src['Regional business tax package'], color: 'var(--s2)' },
        { label: 'European grant', value: src['European grant'], color: mix('var(--s2)', 60) }, { label: 'State grant', value: cen.cap_gap, color: mix('var(--s2)', 35) }], text: bn2(cen.ops_rev_total + src['Regional business tax package'] + src['European grant'] + cen.cap_gap) },
      { label: 'What it gives back', parts: Object.keys(fams).map(function (k) { return { label: k, value: fams[k], color: FAM[k] }; }).concat([{ label: 'Wider effects, apart', value: st.wider_total, color: 'var(--neutral-mark)' }]), text: bn2(st.benefit_total) + ' + ' + mEur(st.wider_total) }
    ];
    const host = $('#eco-year-chart');
    C.stack(host, { rows: rows, fmt: bn2, legend: false });
    rows.forEach(function (r) {
      host.appendChild(h('ul', { class: 'legend eco-year-legend' }, h('li', null, h('b', { text: r.label + ':' })), r.parts.map(function (p) { return h('li', null, h('i', { style: { '--c': p.color } }), p.label + ' ', h('b', { text: p.value >= 1 ? bn2(p.value) : mEur(p.value) })); })));
    });
  })();

  // ---- the four donuts
  (function () {
    const it = MOD.cost.items, cost = MOD.cost;
    donut($('#eco-pie-build'), $('#eco-pie-build-legend'), { label: 'Construction cost by item', fmt: bn1, centre: [F.bn(cost.total, 1), 'to build'], slices: [
      { label: 'Stations and historic halls', value: it['Stations'] + it['Historic halls'], color: 'var(--s1)' },
      { label: 'Tunnels, civil works', value: it['Tunnels, civil works'], color: 'var(--s2)' },
      { label: 'Tunnels, rail systems', value: it['Tunnels, rail systems'], color: 'var(--s2)', alpha: .55 },
      { label: 'Junctions, portals, sidings, links', value: it['Underground junctions'] + it['Portals and links to existing lines'] + it['Sidings and depot links'] + it['Control hall for London trains'] + it['TER links into the TGV tunnels'], color: 'var(--s3)' },
      { label: 'Design and client costs', value: cost.soft, color: 'var(--s4)' },
      { label: 'Land', value: cost.land, color: 'var(--s5)' },
      { label: 'Risk margin', value: cost.risk, color: 'var(--neutral-mark)' }] });
    const rev = cen.ops_rev;
    donut($('#eco-pie-income'), $('#eco-pie-income-legend'), { label: 'The project’s income by source', centre: [mEur(cen.ops_rev_total), 'a year'], slices: [
      { label: 'Track charges on new TGV journeys', value: rev['Track charges on new TGV journeys'], color: 'var(--s1)' },
      { label: 'Charge on high-speed passengers', value: rev['Charge on high-speed passengers'], color: 'var(--s1)', alpha: .7 },
      { label: 'Charge on regional express passengers', value: rev['Charge on regional express passengers'], color: 'var(--s1)', alpha: .45 },
      { label: 'Fee paid by the regional transport authority', value: rev['Fee paid by the regional transport authority'], color: 'var(--s3)' },
      { label: 'Shops in the new station halls', value: rev['Shops in the new station halls'], color: 'var(--s4)' },
      { label: 'Share of the operators’ saving on trainsets', value: rev['Share of the operators’ saving on trainsets'], color: 'var(--s5)' },
      { label: 'New Navigo passes and regional express fares', value: rev['New Navigo pass holders'] + rev['Fares from new regional express passengers'], color: 'var(--s6)' }] });
    const src = cen.cap_sources;
    donut($('#eco-pie-pays'), $('#eco-pie-pays-legend'), { label: 'Who pays the yearly bill', centre: [bn2(cen.yearly_cost), 'a year'], slices: [
      { label: 'The project’s own income', value: cen.ops_rev_total, color: 'var(--s1)', note: 'It pays the running costs and leaves ' + mEur(cen.ops_balance) + ' for the repayment' },
      { label: 'Regional business tax package', value: src['Regional business tax package'], color: 'var(--s2)' },
      { label: 'European grant', value: src['European grant'], color: 'var(--s2)', alpha: .6 },
      { label: 'State grant', value: cen.cap_gap, color: 'var(--s2)', alpha: .35, note: F.bn(cen.grant_bn, 1) + ' over the works, ' + F.pct(cen.grant_share) + ' of the cost' }] });
    donut($('#eco-pie-benefits'), $('#eco-pie-benefits-legend'), { label: 'Benefits by family', centre: [bn2(st.benefit_total), 'a year'],
      slices: Object.keys(st.families).map(function (k) { return { label: k, value: st.families[k], color: FAM[k] }; }) });
  })();

  // ---- every item in today's money, with its range from the low to the high case, and what each one is
  const skip = {}; NM.costs.forEach(function (k) { skip[k] = 1; }); skip[KEY.cofp] = 1; skip[KEY.cofp_added] = 1;
  (function () {
    const lo = FR.cases.low.pv, hi = FR.cases.high.pv, pv = fc.pv;
    const rows = [];
    NM.families.forEach(function (f) {
      const ks = f[1].filter(function (k) { return pv[k] != null && !skip[k] && !(pv[k] === 0 && (lo[k] || 0) === 0 && (hi[k] || 0) === 0); });
      if (!ks.length) return;
      rows.push({ group: f[0] });
      ks.forEach(function (k) {
        const a = Math.min(lo[k] == null ? pv[k] : lo[k], hi[k] == null ? pv[k] : hi[k]), b = Math.max(lo[k] == null ? pv[k] : lo[k], hi[k] == null ? pv[k] : hi[k]);
        const ranged = Math.abs(b - a) > 1e-6;
        rows.push({ label: short(k), value: pv[k], color: FAM[f[0]], lo: ranged ? a : null, hi: ranged ? b : null,
                    tip: '<b>' + short(k) + '</b><br><small>' + NM.explain[k] + '</small><br>' + bn2(pv[k]) + ' in today’s money' + (ranged ? '<br><small>' + bnS(a) + ' to ' + bnS(b) + ' from the low to the high value</small>' : '<br><small>one value</small>') });
      });
    });
    C.bars($('#eco-pv-items-chart'), { rows: rows, fmt: bnS });
  })();

  // ---- the table of every item
  (function () {
    const t = $('#eco-items-table'), lo = FR.cases.low, hi = FR.cases.high;
    t.appendChild(h('thead', null, h('tr', null, h('th', { text: 'Item: what it is' }), h('th', { text: 'Family' }), h('th', { class: 'num', text: '€ million a year, flat' }), h('th', { class: 'num', text: '€ billion today, central' }), h('th', { class: 'num', text: 'Low' }), h('th', { class: 'num', text: 'High' }), h('th', { text: 'Confidence' }))));
    const tb = h('tbody'); t.appendChild(tb);
    const once = st.once; let sumPv = 0;
    NM.families.forEach(function (f) {
      f[1].forEach(function (k) {
        if (skip[k] || fc.pv[k] == null) return;
        if (fc.pv[k] === 0 && !(lo.pv[k] || hi.pv[k]) && !(st.benefits[k] || st.wider[k])) return;
        if (!isWider(k)) sumPv += fc.pv[k];
        const yearly = st.benefits[k] != null ? mEur(st.benefits[k]) + (k === KEY.parks ? ' once open' : '') : st.wider[k] != null ? mEur(st.wider[k]) + ' (apart)' : once[k] != null ? F.bn(once[k], 2) + ' once' : '';
        tb.appendChild(h('tr', { class: isWider(k) ? 'muted' : null }, h('th', null, h('span', { text: short(k) }), h('small', { class: 'eco-what', text: NM.explain[k] })), h('td', { text: f[0] }), h('td', { class: 'num', text: yearly }), h('td', { class: 'num', text: F.n(fc.pv[k], 2) }),
          h('td', { class: 'num', text: lo.pv[k] == null ? '' : F.n(lo.pv[k], 2) }), h('td', { class: 'num', text: hi.pv[k] == null ? '' : F.n(hi.pv[k], 2) }), h('td', { text: NM.confidence[k] || '' })));
      });
    });
    tb.appendChild(h('tr', { class: 'total' }, h('th', { text: 'Total, wider effects apart' }), h('td'), h('td', { class: 'num', text: mEur(st.benefit_total) }), h('td', { class: 'num', text: F.n(sumPv, 2) }), h('td', { class: 'num', text: '' }), h('td', { class: 'num', text: '' }), h('td')));
  })();

  // ---- across France: the city pairs, and the times written into the text
  (function () {
    const rows = FR.france.show, byPair = {};
    rows.forEach(function (r) { byPair[r.pair.join(',')] = r; byPair[r.pair.slice().reverse().join(',')] = r; });
    root.querySelectorAll('[data-pair]').forEach(function (el) { const r = byPair[el.getAttribute('data-pair')]; if (r) el.textContent = hm(el.getAttribute('data-what') === 'today' ? r.today_min : r.project_min); });
    const t = $('#eco-france-table');
    t.appendChild(h('thead', null, h('tr', null, h('th', { text: 'Between' }), h('th', { text: 'Direct trains today' }), h('th', { class: 'num', text: 'Today, with a change in Paris' }), h('th', { class: 'num', text: 'With the project, every hour' }), h('th', { class: 'num', text: 'By air, door to door' }), h('th', { class: 'num', text: 'Air passengers 2025' }), h('th', { class: 'num', text: 'Rail’s share, today to project' }))));
    const tb = h('tbody'); t.appendChild(tb);
    rows.forEach(function (r) {
      const gain = r.today_min - r.project_min;
      tb.appendChild(h('tr', null, h('th', { text: r.pair[0] + ' and ' + r.pair[1] }), h('td', { text: r.today }), h('td', { class: 'num', text: hm(r.today_min) }),
        h('td', { class: 'num', html: '<b>' + hm(r.project_min) + '</b>' + (gain > 0 ? ' <small>(' + F.n(gain, 0) + ' min less)</small>' : gain < 0 ? ' <small>(' + F.n(-gain, 0) + ' min more)</small>' : '') }),
        h('td', { class: 'num', text: hm(r.air_door_min) }), h('td', { class: 'num', text: r.air_pax ? F.n(Math.round(r.air_pax / 1000) * 1000, 0) : 'no route listed' }),
        h('td', { class: 'num', text: F.pct(r.share_today) + ' to ' + F.pct(r.share_project) })));
    });
  })();

  // ---- the largest commune pairs of the job-access measurement
  (function () {
    const t = $('#eco-pairs-table');
    t.appendChild(h('thead', null, h('tr', null, h('th', { text: 'From' }), h('th', { text: 'To' }), h('th', { class: 'num', text: 'Minutes today' }), h('th', { class: 'num', text: 'With the project' }), h('th', { class: 'num', text: 'Trips a day today' }), h('th', { class: 'num', text: 'With the project' }))));
    const tb = h('tbody'); t.appendChild(tb);
    FR.jobs.top_pairs.slice(0, 8).forEach(function (r) {
      tb.appendChild(h('tr', null, h('th', { text: r[0] }), h('td', { text: r[1] }), h('td', { class: 'num', text: F.n(r[2], 0) }), h('td', { class: 'num', text: F.n(r[3], 0) }), h('td', { class: 'num', text: F.n(r[4], 0) }), h('td', { class: 'num', text: F.n(r[5], 0) })));
    });
  })();

  // ---- the years: job access, money, value and the running total
  (function () {
    const T = FR.timeline, Y = T.years, open = FR.params.open;
    const pts = function (arr, from, to, scale) { return Y.map(function (y, i) { return [y, arr[i] * (scale || 1)]; }).filter(function (p) { return p[0] >= (from || Y[0]) && p[0] <= (to || Y[Y.length - 1]); }); };
    const yr = { fmt: function (v) { return v % 1 ? '' : String(v); }, tipLabel: function (v) { return 'In ' + v; } };
    const mFmt = function (v) { return F.n(v, 0); }, bFmt = function (v) { return F.n(v, 1); };
    C.line($('#eco-jobs-years'), { label: 'Access to jobs over the years', height: 260, x: Object.assign({ min: open, max: FR.params.last + 5 }, yr), y: { min: 0, fmt: mFmt, label: '' },
      series: [{ name: 'Commuters’ gain, central', color: 'var(--s4)', points: pts(T.jobs.users, open, null, 1000) },
               { name: 'Low case', color: 'var(--s4)', dash: true, points: pts(T.jobs_low.users, open, null, 1000) },
               { name: 'High case', color: 'var(--s3)', dash: true, points: pts(T.jobs_high.users, open, null, 1000) },
               { name: 'Wider effects, apart (central)', color: 'var(--neutral-mark)', points: pts(T.jobs.wider, open, null, 1000) }] });
    const B = FR.budget, runren = B.running.map(function (v, i) { return v + B.renewal[i]; });
    C.line($('#eco-budget-chart'), { label: 'Money spent and earned year by year', height: 280, x: Object.assign({ min: Y[0], max: 2100 }, yr), y: { min: 0, fmt: bFmt },
      vlines: [{ x: open, label: 'opening' }],
      series: [{ name: 'Construction', color: 'var(--s8)', points: pts(B.construction, null, 2100) },
               { name: 'Running, and the renewals', color: 'var(--s5)', points: pts(runren, null, 2100) },
               { name: 'The project’s own income', color: 'var(--s1)', points: pts(B.income, null, 2100) },
               { name: 'Repayment of construction, simple reading', color: 'var(--s8)', dash: true, points: pts(B.repayment, null, 2100) }] });
    C.line($('#eco-flows-chart'), { label: 'Benefits and costs year by year', height: 280, x: Object.assign({ min: Y[0], max: 2100 }, yr), y: { min: 0, fmt: bFmt },
      vlines: [{ x: open, label: 'opening' }],
      series: [{ name: 'Benefits counted', color: 'var(--s3)', points: pts(T.benefits, null, 2100) },
               { name: 'Wider effects, apart', color: 'var(--neutral-mark)', dash: true, points: pts(T.families['Wider effects, measured'], null, 2100) },
               { name: 'Costs: works, running, renewals, public funds', color: 'var(--s8)', points: pts(T.costs, null, 2100) }] });
    const firstPos = function (arr) { for (let i = 0; i < Y.length; i++) if (Y[i] > open && arr[i] >= 0) return Y[i]; return null; };
    const beLo = firstPos(T.low), beHi = firstPos(T.high);
    C.line($('#eco-cum-chart'), { label: 'Running total in today’s money', height: 300, x: Object.assign({ min: Y[0], max: Y[Y.length - 1] }, yr), y: { fmt: bFmt },
      hlines: [{ y: 0, label: 'paid back' }], vlines: [{ x: T.break_even, label: String(T.break_even) }],
      series: [{ name: 'Central case', color: 'var(--s3)', points: pts(T.cum_npv) },
               { name: 'With the wider effects', color: 'var(--neutral-mark)', dash: true, points: pts(T.cum_npv_wider) },
               { name: 'Low case' + (beLo ? ', paid back in ' + beLo : ''), color: 'var(--s8)', dash: true, points: pts(T.low) },
               { name: 'High case' + (beHi ? ', paid back in ' + beHi : ''), color: 'var(--s1)', dash: true, points: pts(T.high) }] });
  })();

  // ---- present value by family under the French rules
  (function () {
    const pf = fc.pv_families, order = NM.families.map(function (f) { return f[0]; });
    const rows = order.filter(function (k) { return pf[k] != null && k !== 'Wider effects, measured'; }).map(function (k) {
      return { label: k, value: pf[k], color: FAM[k], tip: '<b>' + k + '</b><br>' + bn2(pf[k]) + ' in today’s money' };
    });
    rows.push({ sep: true }, { label: 'Net present value', value: fc.npv, color: 'var(--neutral-mark)', hl: true, text: signedBn(fc.npv) },
      { label: 'Wider effects, reported apart', value: pf['Wider effects, measured'], color: 'var(--neutral-mark)' }, { label: 'Net value with the wider effects', value: fc.npv_wider, color: 'var(--neutral-mark)', hl: true, text: signedBn(fc.npv_wider) });
    C.bars($('#eco-pv-chart'), { rows: rows, fmt: bnS });
  })();

  // ---- what public budgets get back, three readings against the repayment
  const reading = function (mode, label) { const a = PTS.model.accounts({ tax_wider: mode }); return { label: label, value: a.tax_total, color: 'var(--s3)', tip: '<b>' + label + '</b><br>' + mEur(a.tax_total) + ' a year<br><small>' + F.pct(a.tax_share_of_annuity) + ' of the yearly repayment of construction</small>' }; };
  C.bars($('#eco-tax-chart'), { fmt: mEur, rows: [reading('low', 'Nothing is new for the country'), reading('central', 'As the appraisal counts it'), reading('high', 'Every job is new and fully taxed'),
    { sep: true }, { label: 'Yearly repayment of construction', value: cen.annuity, color: 'var(--s8)', hl: true }] });

  // ---- comparison with other projects: this project under the French rules, then the study's simple reading of the same benefits
  const f2 = function (v) { return F.n(v, 2); };
  const mine = (function () {
    const lo = FR.cases.low, hi = FR.cases.high;
    const tipFr = function (what, v) { return '<b>This project, French rules</b><br>' + what + ': <b>' + f2(v) + '</b><br><small>' + F.pct(FR.params.rate, 1) + ' rate to ' + FR.params.resid_end + '; benefits ' + bn1(fc.pv_benefits) + ' against costs ' + bn1(fc.pv_costs) + ' in today’s money. Range ' + f2(lo.ratio) + ' to ' + f2(hi.ratio) + ' from the low to the high value of the uncertain items</small>'; };
    const sl = FR.study.low, sh = FR.study.high;
    const tipSimple = function (what, v, a, b) { return '<b>This project, simple reading</b><br>' + what + ': <b>' + f2(v) + '</b><br><small>One year’s benefits at today’s traffic over one year’s bill (' + F.pct(FIN.base.r, 0) + ' rate, ' + FIN.base.n + ' years). Range ' + f2(a) + ' to ' + f2(b) + '</small>'; };
    return [{ label: 'This project, French rules', sub: '€' + F.n(fc.capex, 0) + 'bn', hl: true, lo: lo.ratio, hi: hi.ratio,
              marks: [{ value: fc.ratio, kind: 'conv', tip: tipFr('Benefits counted', fc.ratio) }, { value: fc.ratio_wider, kind: 'wider', tip: tipFr('With the wider effects', fc.ratio_wider) }] },
            { label: 'This project, simple reading', sub: F.pct(FIN.base.r, 0) + ' rate, flat', lo: sl.cover, hi: sh.cover,
              marks: [{ value: st.cover, kind: 'conv', tip: tipSimple('Benefits counted', st.cover, sl.cover, sh.cover) }, { value: st.cover_wider, kind: 'wider', tip: tipSimple('With the wider effects', st.cover_wider, sl.cover_wider, sh.cover_wider) }] }];
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
    kinds: { conv: { label: 'Benefits in the headline, at approval', color: 'var(--s1)', shape: 'dot' }, wider: { label: 'With wider economic effects', color: 'var(--s1)', shape: 'ring' }, post: { label: 'Measured after opening', color: 'var(--s2)', shape: 'diamond' } },
    rows: mine.concat(others) });

  // ---- what could change the answer: one change at a time in the official reading
  (function () {
    const c0 = fc.npv, pr = FR.params;
    const step = function (label, name, basis, color, key) {
      const a = FR.cases[name], v = a[key || 'npv'];
      return { label: label + ' <span class="tag ' + (basis === 'sourced' ? 'sourced' : 'assume') + '">' + basis + '</span>', value: v, color: color || 'var(--s1)', mark: c0, text: signedBn(v),
               tip: '<b>' + label + '</b><br>Net present value <b>' + signedBn(v) + '</b> <small>(' + signedBn(v - c0) + ' against the central case)</small><br><small>' + signedBn(a.npv_wider) + ' with the wider effects; return ' + F.pct(a.irr, 1) + '</small>' };
    };
    const rows = [
      { group: 'Price and rate' },
      step('Central case', 'central', 'sourced', 'var(--neutral-mark)'),
      step('Construction at high prices, ' + F.bn(FR.cases.high_cost.capex, 1), 'high_cost', 'sourced', 'var(--s8)'),
      step('Construction at low prices, ' + F.bn(FR.cases.low_cost.capex, 1), 'low_cost', 'sourced'),
      step('No growth of traffic or values, 4% rate: the official stress test', 'no_growth_4', 'sourced', 'var(--s8)'),
      step('Public discount rate of ' + F.pct(pr.rate_public, 1) + ' (the 2021 rate)', 'rate32', 'sourced'),
      { group: 'What is counted' },
      step('No value for the room in the busy hours', 'no_capacity', 'sourced', 'var(--s8)'),
      step('Room in the busy hours at €' + F.n(pr.cap_value * 2, 0) + ' a journey instead of €' + F.n(pr.cap_value, 0), 'capacity_40', 'assumed'),
      step('The railway’s own gains left out', 'no_producers', 'sourced', 'var(--s8)'),
      step('The regular timetable left out', 'no_timetable', 'assumed', 'var(--s8)'),
      step('The cross-France journeys left out: bypass travellers, air, their fares and carbon', 'no_france', 'assumed', 'var(--s8)'),
      step('No later arrival at through platforms', 'no_margin', 'assumed', 'var(--s8)'),
      step('The parks left out', 'no_parks', 'assumed', 'var(--s8)'),
      step('Homes and jobs do not move towards the better access', 'no_landuse', 'assumed', 'var(--s8)'),
      step('Long-distance value of time 15% lower', 'vot_ld_085', 'assumed', 'var(--s8)'),
      step('Cost of public funds at 1.25', 'cofp_125', 'sourced', 'var(--s8)'),
      step('Fares on journeys across Paris 40% higher', 'fares_14', 'assumed', 'var(--s8)'),
      step('Running costs 25% lower', 'running_075', 'sourced'),
      step('Cars not carbon-free by 2050', 'ame', 'assumed'),
      { group: 'The uncertain items together' },
      step('Every item with a range at its low value', 'low', 'assumed', 'var(--s8)'),
      step('Every item with a range at its high value', 'high', 'assumed', 'var(--s3)')
    ];
    C.bars($('#eco-sens-chart'), { rows: rows, fmt: bnS });
  })();
});
