PTS.section('crossing', function (root) {
  'use strict';
  const D = PTS.data.model, own = PTS.data.crossing, F = PTS.fmt, h = PTS.h, s = PTS.s, C = PTS.chart;
  const $ = function (sel) { return root.querySelector(sel); };
  const n0 = function (v) { return F.n(v, v % 1 ? 1 : 0); };
  const K = D.connecting.central, LN = own.lines, ORDER = ['N', 'E', 'SE', 'A'];

  // ---------------------------------------------------------------- pair selector
  const state = { from: 'A', to: 'N' };
  const pairOf = function (a, b) { return K.pairs[LN[a].key + '-' + LN[b].key] || K.pairs[LN[b].key + '-' + LN[a].key]; };
  const south = function (k) { return k === 'A' || k === 'SE'; };
  const lc = function (k) { return k === 'A' ? 'the Atlantic' : LN[k].name.toLowerCase(); };       // 'Atlantic' keeps its capital
  const rideOf = function (k) { return k === 'A' ? D.TH.M : k === 'SE' ? D.TH.L : 0; };          // TGV minutes between that line's own station and Nord-Est

  // schematic of the network: line ends, the three stations
  const PT = { N: [112, 16], E: [304, 62], hub: [164, 96], M: [116, 164], L: [220, 154], A: [34, 238], SE: [300, 238] };
  const ROUTE = { N: ['N', 'hub'], E: ['E', 'hub'], SE: ['SE', 'L', 'hub'], A: ['A', 'M', 'hub'] };
  const pathOf = function (keys) { return keys.map(function (k, i) { return (i ? 'L' : 'M') + PT[k][0] + ' ' + PT[k][1]; }).join(' '); };
  const drawMap = function (pair) {
    const a = state.from, b = state.to, host = PTS.clear($('#cx-map'));
    const svg = s('svg', { class: 'draw', viewBox: '0 0 320 258', role: 'img', 'aria-label': 'Sketch of the route across Paris from ' + (a === 'A' ? 'the Atlantic' : 'the ' + lc(a)) + ' line to ' + (b === 'A' ? 'the Atlantic' : 'the ' + lc(b)) + ' line, through ' + LN[a].stops.concat(LN[b].stops).filter(function (x, i, arr) { return arr.indexOf(x) === i; }).join(' and ') + '.' });
    ORDER.forEach(function (k) { svg.appendChild(s('path', { class: 'net', d: pathOf(ROUTE[k]) })); });
    const route = ROUTE[a].concat(ROUTE[b].slice().reverse().slice(1));
    svg.appendChild(s('path', { class: 'sel', d: pathOf(route) }));
    // today's change of station, as a dotted hop between the two terminals
    const term = function (k) { return k === 'A' ? 'M' : k === 'SE' ? 'L' : 'hub'; }, ta = term(a), tb = term(b);
    if (ta !== tb) {
      const p = PT[ta], q = PT[tb], both = south(a) && south(b), viaM = ta === 'M' || tb === 'M';
      const cx = (p[0] + q[0]) / 2 + (both ? 0 : viaM ? -26 : 28), cy = (p[1] + q[1]) / 2 + (both ? 24 : -8);
      svg.appendChild(s('path', { class: 'hop', d: 'M' + p[0] + ' ' + p[1] + ' Q' + cx + ' ' + cy + ' ' + q[0] + ' ' + q[1] }));
      svg.appendChild(s('text', { class: 'lbl-muted halo', x: both ? cx : viaM ? cx + 6 : cx - 2, y: both ? cy + 8 : viaM ? cy - 6 : cy + 12, 'text-anchor': both ? 'middle' : viaM ? 'end' : 'start', text: 'today, by metro' }));
    }
    const used = { hub: true, M: a === 'A' || b === 'A', L: a === 'SE' || b === 'SE' };
    svg.appendChild(s('rect', { class: 'new', x: PT.hub[0] - 17, y: PT.hub[1] - 10, width: 34, height: 20, rx: 10 }));
    svg.appendChild(s('circle', { class: used.M ? 'new' : 'struct', cx: PT.M[0], cy: PT.M[1], r: 7 }));
    svg.appendChild(s('circle', { class: used.L ? 'new' : 'struct', cx: PT.L[0], cy: PT.L[1], r: 7 }));
    svg.appendChild(s('text', { class: 'halo on', x: 188, y: 110, text: 'Paris Nord-Est' }));
    svg.appendChild(s('text', { class: 'halo ' + (used.M ? 'on' : 'off'), x: 104, y: 160, 'text-anchor': 'end', text: 'Montparnasse' }));
    svg.appendChild(s('text', { class: 'halo ' + (used.L ? 'on' : 'off'), x: 232, y: 150, text: 'Gare de Lyon' }));
    [['N', 124, 20, 'start'], ['E', 304, 50, 'end'], ['A', 46, 252, 'start'], ['SE', 290, 252, 'end']].forEach(function (e) {
      svg.appendChild(s('text', { class: e[0] === a || e[0] === b ? 'on' : 'off', x: e[1], y: e[2], 'text-anchor': e[3], text: LN[e[0]].name }));
    });
    host.appendChild(svg);
  };

  const draw = function () {
    const a = state.from, b = state.to, A = LN[a], B = LN[b], pair = pairOf(a, b);
    const direct = pair.served && pair.direct != null, both = south(a) && south(b), ride = rideOf(a) + rideOf(b), changeMin = pair.change_clock - ride;
    $('#cx-title').textContent = A.name + ' to ' + lc(b);
    $('#cx-sub').textContent = 'For example ' + A.city + ' to ' + B.city;
    const today = !south(a) && !south(b) ? 'Walk between ' + A.terminal + ' and ' + B.terminal + ', 500 m apart, and wait for the next train'
      : 'Leave the train at ' + A.terminal + ', cross Paris by metro or RER, board again at ' + B.terminal;
    const directTxt = !direct ? 'Not in the plan: the train would have to reverse at Nord-Est'
      : both ? 'Stay on board: ' + A.stops[0] + ', a reversal at Paris Nord-Est, then ' + B.stops[0]
      : 'Stay on board: the train stops at ' + (south(a) ? A.stops[0] + ', then Paris Nord-Est' : 'Paris Nord-Est, then ' + B.stops[0]);
    const changeTxt = n0(changeMin) + ' minutes from train to train on the platforms of Nord-Est' + (ride ? ', and ' + n0(ride) + ' on the trains inside Paris' : '');
    C.bars($('#cx-bars'), { max: 60, fmt: function (v) { return n0(v) + ' min'; }, rows: [
      { label: '<b>Today</b><br><small>' + today + '</small>', value: pair.old_clock, color: 'var(--today)', tip: '<b>Today: ' + n0(pair.old_clock) + ' min</b><br>' + today },
      { label: '<b>Direct train</b><br><small>' + directTxt + '</small>', value: direct ? pair.direct : 0, color: 'var(--s1)', text: direct ? null : 'none', tip: '<b>Direct train' + (direct ? ': ' + n0(pair.direct) + ' min' : '') + '</b><br>' + directTxt },
      { label: '<b>Change inside Nord-Est</b><br><small>' + changeTxt + '</small>', value: pair.change_clock, color: 'var(--s2)', tip: '<b>Change inside Nord-Est: ' + n0(pair.change_clock) + ' min</b><br>' + changeTxt }] });
    const read = PTS.clear($('#cx-read'));
    [['Share of the passengers who cross Paris', F.pct(pair.share)], ['Passengers a year on this pair, both ways', F.M(pair.share * K.base, 1)],
     ['Saved on a direct train', direct ? n0(pair.old_clock - pair.direct) + ' min' : 'no direct train'], ['Saved with a change inside Nord-Est', n0(pair.old_clock - pair.change_clock) + ' min']]
      .forEach(function (r) { read.appendChild(h('dt', { text: r[0] })); read.appendChild(h('dd', { text: r[1] })); });
    drawMap(pair);
  };
  const opts = ORDER.map(function (k) { return [k, LN[k].name]; });
  const ctl = $('#cx-ctl');
  // a line cannot be paired with itself: the choice made on one side is switched off on the other
  const lock = function () {
    PTS.$$('.field', ctl).forEach(function (f, i) {
      const other = i === 0 ? state.to : state.from;
      PTS.$$('button', f).forEach(function (bt) { bt.disabled = bt.dataset.v === other; bt.title = bt.disabled ? 'Already chosen on the other side' : ''; });
    });
  };
  PTS.seg(ctl, opts, state.from, function (v) { state.from = v; lock(); draw(); }, 'Coming from');
  PTS.seg(ctl, opts, state.to, function (v) { state.to = v; lock(); draw(); }, 'Going to');
  lock(); draw();

  // ---------------------------------------------------------------- regional and suburban services
  const G = D.regional;
  const nameOf = function (k) { return own.ter_names[k] || 'Line ' + k; };
  const MEASURE = {
    min: { label: 'Minutes saved', sub: 'Minutes saved on the clock by an average passenger, by service, with the second station each one runs on to', fmt: function (v) { return F.n(v, 1) + ' min'; }, get: function (r) { return r[3]; } },
    users: { label: 'Journeys concerned', sub: 'Million journeys a year to or from the Paris terminal, by service', fmt: function (v) { return F.n(v, 1) + ' million'; }, get: function (r) { return r[2]; } },
    hours: { label: 'Hours saved a year', sub: 'Million hours saved a year (journeys multiplied by minutes saved), by service', fmt: function (v) { return F.n(v, 2) + ' million h'; }, get: function (r) { return r[2] * r[3] / 60; } }
  };
  const drawReg = function (key) {
    const M = MEASURE[key];
    const row = function (r) {
      return { label: nameOf(r[0]) + '<br><small>on to ' + own.second_stop[r[0]] + '</small>', value: M.get(r), color: 'var(--s1)',
        tip: '<b>' + nameOf(r[0]) + '</b><br>' + F.n(r[2], 1) + ' million journeys a year through its Paris terminal<br>' + F.n(r[3], 1) + ' minutes saved on average<br>' + F.n(r[2] * r[3] / 60, 2) + ' million hours a year' };
    };
    const sub = G.rows.filter(function (r) { return r[0].indexOf('TER') !== 0; }), ter = G.rows.filter(function (r) { return r[0].indexOf('TER') === 0; });
    C.bars($('#cx-reg-chart'), { fmt: M.fmt, rows: [{ group: 'Suburban lines' }].concat(sub.map(row), [{ group: 'Regional express trains' }], ter.map(row)) });
    $('#cx-reg-sub').textContent = M.sub;
  };
  PTS.seg($('#cx-reg-ctl'), Object.keys(MEASURE).map(function (k) { return [k, MEASURE[k].label]; }), 'min', drawReg, 'Show');
  drawReg('min');
  const f1 = function (v) { return F.n(v, 1); };
  PTS.table($('#cx-reg-table'), [
    { key: 'name', label: 'Service' }, { key: 'q', label: 'Journeys a year', num: true, fmt: f1 }, { key: 'u', label: 'Of which through the Paris terminal', num: true, fmt: f1 },
    { key: 'stop', label: 'Second stop' }, { key: 'm', label: 'Minutes saved, average', num: true, fmt: f1 }],
    G.rows.map(function (r) { return { name: nameOf(r[0]), q: r[1], u: r[2], stop: own.second_stop[r[0]], m: r[3] }; })
      .concat([{ name: 'Total', q: G.base, u: G.users, stop: '', m: G.avg_clock_saving, _class: 'total' }]));
});
