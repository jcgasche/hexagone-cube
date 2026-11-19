PTS.section('headway', function (root) {
  'use strict';
  const D = PTS.data.headway, F = PTS.fmt, h = PTS.h;
  const $ = function (sel) { return root.querySelector(sel); };
  const state = { hour: 'full', sig: 'auto', perf: 'central' };
  const APPROACH = { north: 'North approach', east: 'East approach', southeast: 'South-east approach', atlantic: 'Atlantic approach' };
  const STATION = { NE: 'Nord-Est', MP: 'Montparnasse', LY: 'Gare de Lyon' };
  const PAIR = { tgv_tgv: 'TGV behind a TGV', ter_tgv: 'TGV behind a TER', tgv_ter: 'TER behind a TGV', ter_ter: 'TER behind a TER' };
  const order = ['north', 'east', 'southeast', 'atlantic'];

  function name(r) {
    if (r.use === 'tun') { const w = r.way.split(' '); return STATION[w[0]] + ' to ' + STATION[w[1]]; }
    return APPROACH[r.tube] + (r.use === 'in' ? ', arriving' : ', leaving');
  }
  function line(r) {
    const w = r.worst, cls = (r.short ? 'hw-bad ' : '') + (r.taken > D.params.uic_peak ? 'hw-over' : '');
    return h('tr', { class: cls || null },
      h('th', { text: name(r) }),
      h('td', { class: 'num', text: F.n(r.trains) + ' (' + F.n(r.tgv) + ' + ' + F.n(r.ter) + ')' }),
      h('td', { class: 'hw-pair', text: PAIR[w.first + '_' + w.second] }),
      h('td', { class: 'num', text: F.n(w.gap) }),
      h('td', { class: 'num', text: F.n(w.need) }),
      h('td', { class: 'num hw-spare', text: F.n(w.spare) }),
      h('td', { class: 'num', text: F.n(r.short) }),
      h('td', { class: 'num hw-taken' },
        h('span', { class: 'hw-bar', 'aria-hidden': 'true' }, h('i', { style: { width: Math.min(100, r.taken * 100) + '%' } }), h('b', { style: { left: D.params.uic_peak * 100 + '%' } })),
        F.pct(r.taken)));
  }
  function draw() {
    const c = D.cases[state.perf + '_' + state.sig].hours[state.hour], rows = c.rows, host = $('#hw-table');
    const group = function (label, list) { return [h('tr', { class: 'hw-group' }, h('th', { colspan: 8, text: label }))].concat(list.map(line)); };
    const inn = rows.filter(function (r) { return r.use === 'in'; }).sort(function (a, b) { return order.indexOf(a.tube) - order.indexOf(b.tube); });
    const out = rows.filter(function (r) { return r.use === 'out'; }).sort(function (a, b) { return order.indexOf(a.tube) - order.indexOf(b.tube); });
    const tri = rows.filter(function (r) { return r.use === 'tun'; });
    PTS.clear(host);
    host.appendChild(h('div', { class: 'tbl-wrap' }, h('table', { class: 'tbl hw-rows' },
      h('thead', null, h('tr', null,
        h('th', { text: 'Track' }),
        h('th', { class: 'num', text: 'Trains an hour (TGVs + TER)' }),
        h('th', { text: 'Closest pair' }),
        h('th', { class: 'num', text: 'Time the timetable gives it (s)' }),
        h('th', { class: 'num', text: 'Least time it needs (s)' }),
        h('th', { class: 'num', text: 'In hand (s)' }),
        h('th', { class: 'num', text: 'Pairs too close' }),
        h('th', { class: 'num', text: 'Share of the hour taken' }))),
      h('tbody', null, group('Approach tunnels, towards the station', inn), group('The triangle', tri), group('Approach tunnels, away from the station', out)))));
    const s = c.sum, sum = $('#hw-sum');
    PTS.clear(sum);
    sum.appendChild(h('span', { text: F.n(s.short) + ' of ' + F.n(s.pairs) + ' pairs of trains closer than they need.' }));
    sum.appendChild(document.createTextNode(' '));
    sum.appendChild(h('span', { text: 'The mark on each bar is the limit planners keep in the busiest hour.' }));
  }
  const ctl = $('#hw-ctl');
  PTS.seg(ctl, [['today', 'About today'], ['full', 'Southern lines full'], ['max', 'Nord-Est filled too']], state.hour, function (v) { state.hour = v; draw(); }, 'Hour shown');
  PTS.seg(ctl, [['auto', 'Short blocks, automatic driving'], ['short', 'Short blocks, a driver'], ['long', 'Blocks of 400 m, a driver']], state.sig, function (v) { state.sig = v; draw(); }, 'Signalling');
  PTS.seg(ctl, [['central', 'Central trains'], ['cautious', 'Cautious trains']], state.perf, function (v) { state.perf = v; draw(); }, 'Trains');
  draw();
});
