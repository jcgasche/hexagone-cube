PTS.section('economy', function (root) {
  'use strict';
  const FIN = PTS.data.finance, P = FIN.params, K = FIN.cases, FR = PTS.data.french, MOD = PTS.data.model, F = PTS.fmt, C = PTS.chart, h = PTS.h, s = PTS.s, own = PTS.data.economy;
  const $ = function (sel) { return root.querySelector(sel); };
  const cen = K.central, fc = FR.cases.central, st = FR.study.central;
  const mEur = function (v) { return F.m(v); }, bn1 = function (v) { return F.bn(v, 1); }, bn2 = function (v) { return F.bn(v, 2); };
  const signedBn = function (v) { return (v < 0 ? '-' : '+') + F.bn(Math.abs(v), 1); }, bnS = function (v) { return (v < 0 ? '-' : '') + F.bn(Math.abs(v), Math.abs(v) < 0.95 ? 2 : 1); };

  // ---- one colour per family of benefits, used by every chart of the page
  const FAM = {
    'Passengers’ time': 'var(--s1)', 'Room for more trains in the busy hours': 'var(--s7)', 'The railway’s own gains': 'var(--s2)', 'Comfort and ease': 'var(--s3)',
    'Job access across Paris': 'var(--s4)', 'Environment': 'var(--s6)', 'Land, parks and one-off savings': 'var(--s5)', 'Costs of the works themselves': 'var(--s8)',
    'Construction and running costs': 'var(--s8)', 'Cost of public funds': 'var(--neutral-mark)', 'Wider effects, measured': 'var(--neutral-mark)'
  };
  const famOf = {}; FR.names.families.forEach(function (f) { f[1].forEach(function (k) { famOf[k] = f[0]; }); });
  const short = function (k) { return k.replace(/^(W?\d+\.|W\d\.)\s*/, '').replace(/\s*\(.*?\)\s*$/, ''); };

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

  // ---- the bridge from the first count to the complete count
  C.bars($('#eco-bridge-chart'), { fmt: mEur, rows: st.bridge.map(function (b, i) {
    const last = i === st.bridge.length - 1, first = i === 0;
    return { label: b[0], value: b[1], color: first || last ? 'var(--neutral-mark)' : b[1] < 0 ? 'var(--s8)' : (FAM[b[0]] || 'var(--s1)'), hl: first || last, text: first || last ? mEur(b[1]) : (b[1] < 0 ? '-' : '+') + mEur(Math.abs(b[1])) };
  }) });

  // ---- every item in today's money, with its range from the low to the high case
  (function () {
    const lo = FR.cases.low.pv, hi = FR.cases.high.pv, pv = fc.pv;
    const skip = { 'Construction': 1, 'Renewal of rail systems': 1, 'Running tunnels and stations': 1, 'Extra regional train running': 1, 'Cost of public funds': 1, 'Public funds on the items above': 1 };
    const rows = [];
    FR.names.families.forEach(function (f) {
      const ks = f[1].filter(function (k) { return pv[k] != null && !skip[k] && !(pv[k] === 0 && (lo[k] || 0) === 0 && (hi[k] || 0) === 0); });
      if (!ks.length) return;
      rows.push({ group: f[0] });
      ks.forEach(function (k) {
        const a = Math.min(lo[k] == null ? pv[k] : lo[k], hi[k] == null ? pv[k] : hi[k]), b = Math.max(lo[k] == null ? pv[k] : lo[k], hi[k] == null ? pv[k] : hi[k]);
        const ranged = Math.abs(b - a) > 1e-6;
        rows.push({ label: short(k), value: pv[k], color: FAM[f[0]], lo: ranged ? a : null, hi: ranged ? b : null,
                    tip: '<b>' + short(k) + '</b><br>' + bn2(pv[k]) + ' in today’s money' + (ranged ? '<br><small>' + bnS(a) + ' to ' + bnS(b) + ' from the low to the high value</small>' : '<br><small>one value, from the first count</small>') });
      });
    });
    C.bars($('#eco-pv-items-chart'), { rows: rows, fmt: bnS });
  })();

  // ---- the table of every item
  (function () {
    const t = $('#eco-items-table'), lo = FR.cases.low, hi = FR.cases.high;
    const conf = { 'TGV time: Paris region': 'Medium', 'TGV time: crossing Paris': 'Medium', 'Regional time: Paris side': 'Medium', 'TER time: crossing Paris': 'Medium', 'TGV capacity in the busy hours': 'Low',
      'Producers: margins and track charges on new TGV journeys': 'Official rule, debated', 'Trainsets freed by through running': 'Medium', 'Upkeep of surface terminals saved': 'Medium', 'Carbon': 'High', 'Road accidents, noise, pollution, congestion': 'High',
      '1. Job access: suburb-to-suburb users': 'Medium, measured', '2. Freed land (net sale value)': 'Low', '2. Parks (amenity less upkeep)': 'Low', '3. Crowding relief (replaces the borrowed comfort ratio)': 'Medium', '5. Signal boxes not renewed': 'Medium',
      '6. Reliability of the merged lines': 'Unknown, zero', '7. Noise along the closed approaches': 'Medium', '8. Shift from air: carbon': 'Medium', '8. Shift from air: travellers and operators': 'Medium', '10. Departure margin at through platforms': 'Low',
      '11. Carbon of the works': 'Medium', '11. Disruption during the works': 'Low', 'W1. Job access: agglomeration': 'Low', 'W2. Job access: people into work': 'Low', 'W3. Job access: better jobs': 'Low', 'W4. TGV links: market access': 'Low', 'W5. TGV links: imperfect competition': 'Low' };
    t.appendChild(h('thead', null, h('tr', null, h('th', { text: 'Item' }), h('th', { text: 'Family' }), h('th', { class: 'num', text: '€ million a year, flat' }), h('th', { class: 'num', text: '€ billion today, central' }), h('th', { class: 'num', text: 'Low' }), h('th', { class: 'num', text: 'High' }), h('th', { text: 'Confidence' }))));
    const tb = h('tbody'); t.appendChild(tb);
    const skip = { 'Construction': 1, 'Renewal of rail systems': 1, 'Running tunnels and stations': 1, 'Extra regional train running': 1, 'Cost of public funds': 1, 'Public funds on the items above': 1 };
    const once = st.once; let sumPv = 0;
    FR.names.families.forEach(function (f) {
      f[1].forEach(function (k) {
        if (skip[k] || fc.pv[k] == null) return;
        if (fc.pv[k] === 0 && !(lo.pv[k] || hi.pv[k]) && !(st.benefits[k] || st.wider[k])) return;
        if (!/^W/.test(k)) sumPv += fc.pv[k];
        const yearly = st.benefits[k] != null ? mEur(st.benefits[k]) : st.wider[k] != null ? mEur(st.wider[k]) + ' (apart)' : once[k] != null ? F.bn(once[k], 2) + ' once' : '';
        tb.appendChild(h('tr', { class: /^W/.test(k) ? 'muted' : null }, h('th', { text: short(k) }), h('td', { text: f[0] }), h('td', { class: 'num', text: yearly }), h('td', { class: 'num', text: F.n(fc.pv[k], 2) }),
          h('td', { class: 'num', text: lo.pv[k] == null ? '' : F.n(lo.pv[k], 2) }), h('td', { class: 'num', text: hi.pv[k] == null ? '' : F.n(hi.pv[k], 2) }), h('td', { text: conf[k] || '' })));
      });
    });
    tb.appendChild(h('tr', { class: 'total' }, h('th', { text: 'Total, wider effects apart' }), h('td'), h('td', { class: 'num', text: mEur(st.benefit_total) }), h('td', { class: 'num', text: F.n(sumPv, 2) }), h('td', { class: 'num', text: '' }), h('td', { class: 'num', text: '' }), h('td')));
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

  // ---- present value by family under the French rules
  (function () {
    const pf = fc.pv_families, order = FR.names.families.map(function (f) { return f[0]; });
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

  // ---- comparison with other projects: this project under the French rules, then the first count on the study's basis
  const f2 = function (v) { return F.n(v, 2); };
  const mine = (function () {
    const lo = FR.cases.low, hi = FR.cases.high;
    const tipFr = function (what, v) { return '<b>This project, French rules</b><br>' + what + ': <b>' + f2(v) + '</b><br><small>' + F.pct(FR.params.rate, 1) + ' rate to ' + FR.params.resid_end + '; benefits ' + bn1(fc.pv_benefits) + ' against costs ' + bn1(fc.pv_costs) + ' in today’s money. Range ' + f2(lo.ratio) + ' to ' + f2(hi.ratio) + ' from the low to the high value of the added items</small>'; };
    const g = K.growth, flat = K.central;
    const tipOld = function (what, v, vFlat) { return '<b>This project, first count, simple reading</b><br>' + what + ': <b>' + f2(v) + '</b> with benefits growing ' + F.pct(P.growth, 1) + ' a year, ' + f2(vFlat) + ' flat<br><small>' + F.pct(flat.r || 0.03, 0) + ' rate, 60 years, nothing left at the end</small>'; };
    return [{ label: 'This project, French rules', sub: '€' + F.n(fc.capex, 0) + 'bn', hl: true, lo: lo.ratio, hi: hi.ratio,
              marks: [{ value: fc.ratio, kind: 'conv', tip: tipFr('Benefits counted', fc.ratio) }, { value: fc.ratio_wider, kind: 'wider', tip: tipFr('With the wider effects', fc.ratio_wider) }] },
            { label: 'This project, first count, simple reading', sub: '3% rate', lo: flat.econ_cover_all, hi: g.econ_cover_all,
              marks: [{ value: g.econ_cover_transport, kind: 'conv', tip: tipOld('Time and comfort', g.econ_cover_transport, flat.econ_cover_transport) }, { value: g.econ_cover_all, kind: 'wider', tip: tipOld('With the borrowed wider effects', g.econ_cover_all, flat.econ_cover_all) }] }];
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
      step('Long-distance value of time 15% lower', 'vot_ld_085', 'assumed', 'var(--s8)'),
      step('Cost of public funds at 1.25', 'cofp_125', 'sourced', 'var(--s8)'),
      step('Fares on journeys across Paris 40% higher', 'fares_14', 'assumed', 'var(--s8)'),
      step('Running costs 25% lower', 'running_075', 'sourced'),
      step('Cars not carbon-free by 2050', 'ame', 'assumed'),
      { group: 'The added items together' },
      step('Every added item at its low value', 'low', 'assumed', 'var(--s8)'),
      step('Every added item at its high value', 'high', 'assumed', 'var(--s3)')
    ];
    C.bars($('#eco-sens-chart'), { rows: rows, fmt: bnS });
  })();
});
