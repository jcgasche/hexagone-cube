PTS.section('works', function (root) {
  'use strict';
  const D = PTS.data.model, S = PTS.data.works, F = PTS.fmt, h = PTS.h, s = PTS.s;
  const $ = function (sel) { return root.querySelector(sel); };
  const YEARS = D.params.build_years, AFTER = YEARS + 1;
  const state = { ba: 'today', year: 6 };
  const drawings = [];
  function mount(sel, fn, maxW) {                            // draw at the real pixel width, again when the width or the state changes
    const host = $(sel); let w = 0;
    const run = function () { if (w) PTS.clear(host).appendChild(fn(w)); };
    drawings.push(run);
    PTS.onResize(host, function (nw) { w = Math.min(nw, maxW || 640); run(); });
  }
  const redraw = function () { drawings.forEach(function (f) { f(); }); };
  function note(el, label, tip) {
    el.setAttribute('tabindex', '0'); el.setAttribute('role', 'img'); el.setAttribute('aria-label', label); el.classList.add('hot');
    PTS.tip.bind(el, tip);
    return el;
  }

  // ================================================================ one terminal: today, during the works, after
  const BA = {
    today: 'Trains end at the platforms behind the hall. The approach tracks cut through the city as far as the ring road and beyond.',
    works: 'The station is dug under the platforms and the tunnels are bored from shafts. Trains keep running above. A few platforms at a time are closed over the works.',
    after: 'Trains run through below, and the hall is the entrance. The platforms and the approach tracks inside Paris are no longer needed: cleared, they become a park. Beyond the ring road the tunnels come up through a portal and join the existing line; the depot is reached through it.'
  };
  function ba(W) {
    const st = state.ba, narrow = W < 520, yS = narrow ? 90 : 78, H = yS + 138, X = function (f) { return Math.round(f * W); };
    const svg = s('svg', { class: 'draw', viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img', 'aria-label': 'Side view of a terminal, ' + (st === 'today' ? 'today' : st === 'works' ? 'during the works' : 'after the works') + '. ' + BA[st] });
    const lab = function (f, tier, text, cls) { svg.appendChild(s('text', { class: cls || 'lbl-muted', x: X(f), y: !narrow ? 14 : tier === 1 ? 13 : 28, 'text-anchor': 'middle', text: text })); };
    const under = function (f, dy, text, anchor, dx) { svg.appendChild(s('text', { class: 'wk-under', x: X(f) + (dx || 0), y: yS + dy, 'text-anchor': anchor || 'middle', text: text })); };
    const yT = yS + 84, bx0 = X(0.08), bx1 = X(0.42), tunnel = 'M' + bx1 + ',' + yT + 'H' + X(0.74) + 'L' + X(0.84) + ',' + (yS - 2);
    svg.appendChild(s('rect', { class: 'ground', x: 0, y: yS, width: W, height: H - yS, stroke: 'none' }));
    // the ring road, a bridge over the tracks
    svg.appendChild(s('path', { class: 'wk-ring', d: 'M' + (X(0.74) - 16) + ',' + (yS - 26) + 'h32M' + (X(0.74) - 10) + ',' + (yS - 26) + 'v26M' + (X(0.74) + 10) + ',' + (yS - 26) + 'v26' }));
    lab(0.74, 1, 'Ring road');
    // what lies beyond the ring road stays in every state
    svg.appendChild(s('rect', { class: 'struct', x: X(0.87), y: yS - 20, width: X(0.97) - X(0.87), height: 20, rx: 2 }));
    lab(0.92, 2, 'Depot');
    if (st !== 'after') {
      svg.appendChild(s('line', { class: 'oldline', x1: X(0.15), x2: W, y1: yS - 2, y2: yS - 2 }));
      svg.appendChild(s('path', { class: 'wk-canopy', d: 'M' + X(0.15) + ',' + (yS - 2) + 'V' + (yS - 26) + 'H' + X(0.37) + 'V' + (yS - 2) }));
      [0.18, 0.25, 0.32, 0.5, 0.63].forEach(function (f) { svg.appendChild(s('rect', { class: 'wk-train', x: X(f), y: yS - 14, width: narrow ? 14 : 22, height: 10, rx: 2 })); });
      lab(0.26, 1, 'Platforms'); lab(0.55, 2, 'Approach tracks');
    } else {
      svg.appendChild(s('line', { class: 'oldline', x1: X(0.84), x2: W, y1: yS - 2, y2: yS - 2 }));
      svg.appendChild(s('rect', { class: 'wk-freed', x: X(0.15), y: yS - 9, width: X(0.72) - X(0.15), height: 9, rx: 2 }));
      [0.2, 0.3, 0.4, 0.5, 0.6, 0.68].forEach(function (f) { svg.appendChild(s('circle', { class: 'wk-tree', cx: X(f), cy: yS - 15, r: 5 })); });
      lab(0.43, 1, narrow ? 'Park' : 'Park on the site of the tracks', 'wk-b');
    }
    svg.appendChild(s('line', { class: 'wk-street', x1: 0, x2: W, y1: yS, y2: yS }));
    svg.appendChild(s('path', { class: 'struct', d: 'M' + X(0.03) + ',' + yS + 'V' + (yS - 30) + 'Q' + X(0.085) + ',' + (yS - 56) + ' ' + X(0.14) + ',' + (yS - 30) + 'V' + yS + 'Z' }));
    svg.appendChild(s('text', { class: st === 'after' ? 'wk-b' : 'lbl-muted', x: narrow ? 2 : X(0.085), y: narrow ? 28 : 14, 'text-anchor': narrow ? 'start' : 'middle', text: st === 'after' ? 'Entrance' : 'Hall' }));
    if (st === 'works') {
      [0.28, 0.6].forEach(function (f) { svg.appendChild(s('rect', { class: 'wk-site', x: X(f) - 6, y: yS - 2, width: 12, height: yT - yS - 10 })); });
      svg.appendChild(s('rect', { class: 'wk-closed', x: X(0.27), y: yS - 26, width: X(0.1), height: 24 }));
      svg.appendChild(s('rect', { class: 'wk-doing', x: bx0, y: yT - 18, width: bx1 - bx0, height: 36, rx: 3 }));
      svg.appendChild(s('path', { class: 'wk-doing line', d: 'M' + bx1 + ',' + yT + 'H' + X(0.66) }));
      svg.appendChild(s('rect', { class: 'wk-tbm', x: X(0.66) - 4, y: yT - 7, width: 16, height: 14, rx: 2 }));
      under(0.25, 118, 'Station being dug'); under(0.6, 40, narrow ? 'Shaft' : 'Shaft and work site', 'start', 12);
      under(0.47, 104, 'Tunnel being bored', 'start');
    }
    if (st === 'after') {
      svg.appendChild(s('path', { class: 'newline', d: tunnel }));
      svg.appendChild(s('rect', { class: 'new', x: bx0, y: yT - 18, width: bx1 - bx0, height: 36, rx: 3 }));
      svg.appendChild(s('rect', { class: 'wk-newtrain', x: bx0 + 14, y: yT - 7, width: (bx1 - bx0) * 0.6, height: 12, rx: 3 }));
      svg.appendChild(s('path', { class: 'wk-way', d: 'M' + X(0.1) + ',' + yS + 'L' + X(0.15) + ',' + (yT - 18) }));
      svg.appendChild(s('path', { class: 'wk-node', d: 'M' + X(0.84) + ',' + (yS + 5) + 'l7,11h-14z' }));
      under(0.25, 118, 'New station'); under(0.58, 76, 'Tunnels'); under(0.84, 22, 'Portal', 'start', 13);
    }
    return svg;
  }
  PTS.seg($('#works-ba-controls'), [['today', 'Today'], ['works', 'During the works'], ['after', 'After']], state.ba, function (v) { state.ba = v; $('#works-ba-text').textContent = BA[v]; redraw(); }, 'One terminal');
  $('#works-ba-text').textContent = BA[state.ba];
  mount('#works-ba', ba, 760);

  // ================================================================ timeline
  const statusOf = function (e, y) { return y < e.start ? 'none' : y < e.open ? 'works' : 'open'; };
  const WORD = { none: 'not started', works: 'under construction', open: 'open' };
  const yearName = function (y) { return y === 0 ? 'Before the works' : y > YEARS ? 'After year ' + YEARS : 'Year ' + y; };
  const NODE = { nordest: [0.5, 0.36], lyon: [0.76, 0.66], montparnasse: [0.24, 0.66] };
  const LINE = { north: [[0.28, 0.07], 'nordest', 'Saint-Denis'], east: [[0.72, 0.07], 'nordest', 'Pantin'], nelyon: ['nordest', 'lyon'], nemont: ['nordest', 'montparnasse'], southeast: ['lyon', [0.94, 0.93], 'Maisons-Alfort'], atlantic: ['montparnasse', [0.06, 0.93], 'Clamart'], link: ['montparnasse', 'lyon'] };
  const NCOR = S.elements.filter(function (e) { return e.kind === 'corridor'; }).length;
  function surfaceWord(e, y) {
    const two = e.id === 'nordest';
    if (y < e.open) return two ? 'Two terminals in use above' : 'Terminal in use above';
    if (y < e.open + 2 && y <= YEARS) return 'Surface platforms closing';
    return two ? 'Two halls as entrances' : 'Hall as entrance';
  }
  function net(W) {
    const y = state.year, narrow = W < 430, H = Math.round(Math.max(270, W * 0.66)), nw = narrow ? 104 : 124, nh = 30;
    const P = function (p) { const q = typeof p === 'string' ? NODE[p] : p; return [q[0] * W, q[1] * H]; };
    const svg = s('svg', { class: 'draw', viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img', 'aria-label': 'Diagram of the network in ' + yearName(y).toLowerCase() + ': ' + S.elements.map(function (e) { return e.name + ' ' + WORD[statusOf(e, y)]; }).join(', ') });
    const span = function (e) { return e.start === 1 ? 'Works from the first year' : 'Works from year ' + e.start; };
    S.elements.filter(function (e) { return e.kind === 'corridor'; }).forEach(function (e) {
      const L = LINE[e.id], a = P(L[0]), b = P(L[1]), stt = statusOf(e, y);
      const g = s('g', null, s('line', { class: 'wk-line ' + stt + (e.id === 'link' ? ' single' : ''), x1: a[0], y1: a[1], x2: b[0], y2: b[1] }), s('line', { class: 'wk-hit', x1: a[0], y1: a[1], x2: b[0], y2: b[1] }));
      const what = e.id === 'link' ? e.name + ', one pair of tracks, with its junction caverns at both ends' : e.name + ' corridor';
      svg.appendChild(note(g, what + ', ' + WORD[stt], '<b>' + what + '</b><br>' + WORD[stt].charAt(0).toUpperCase() + WORD[stt].slice(1) + ' in ' + yearName(y).toLowerCase() + '<br><small>' + span(e) + '; opens after year ' + (e.open - 1) + ' (assumed)</small>'));
      if (L[2]) {
        const p = typeof L[0] === 'string' ? b : a, up = p[1] < H / 2;
        svg.appendChild(s('path', { class: 'wk-node ' + stt, d: 'M' + p[0] + ',' + (p[1] - 7) + 'l7,12h-14z' }));
        svg.appendChild(s('text', { class: 'lbl-muted', x: p[0] + (p[0] < W / 2 ? 12 : -12), y: p[1] + (up ? 2 : 6), 'text-anchor': p[0] < W / 2 ? 'start' : 'end', text: L[2] }));
      }
    });
    S.elements.filter(function (e) { return e.kind === 'station'; }).forEach(function (e) {
      const p = P(e.id), stt = statusOf(e, y);
      const g = s('g', null, s('rect', { class: 'wk-st ' + stt, x: p[0] - nw / 2, y: p[1] - nh / 2, width: nw, height: nh, rx: 6 }),
        s('text', { class: 'wk-b', x: p[0], y: p[1] + 4, 'text-anchor': 'middle', text: e.name }),
        s('text', { class: 'lbl-muted wk-halo', x: p[0], y: p[1] + nh / 2 + 14, 'text-anchor': 'middle', text: surfaceWord(e, y) }));
      svg.appendChild(note(g, e.name + ', ' + WORD[stt], '<b>' + e.name + '</b><br>Deep station ' + WORD[stt] + ' in ' + yearName(y).toLowerCase() + '<br>' + surfaceWord(e, y) + '<br><small>' + span(e) + '; opens after year ' + (e.open - 1) + ' (assumed)</small>'));
    });
    return svg;
  }
  function readout() {
    const y = state.year, total = D.cost.total, names = function (stt) { const l = S.elements.filter(function (e) { return e.kind === 'station' && statusOf(e, y) === stt; }).map(function (e) { return e.name; }); return l.length ? l.join(', ') : 'none'; };
    const km = function (stt) { return S.elements.filter(function (e) { return e.kind === 'corridor' && statusOf(e, y) === stt; }).length; };
    $('#works-tl-title').textContent = yearName(y);
    const dl = PTS.clear($('#works-tl-read'));
    [['Stations under construction', names('works')], ['Stations open', names('open')], ['Tunnel corridors, the link counted as one', km('works') + ' under construction, ' + km('open') + ' open, of ' + NCOR],
      ['Spent by the end of the year, if spending is even', F.bn(total * Math.min(y, YEARS) / YEARS, 0) + ' of ' + F.bn(total, 0)]].forEach(function (r) { dl.appendChild(h('dt', { text: r[0] })); dl.appendChild(h('dd', { text: r[1] })); });
    $('#works-tl-network').textContent = S.network.filter(function (n) { return y <= n.to; })[0].text;
  }
  function gantt() {
    const y = state.year, box = h('div', { class: 'works-gantt' });
    const cells = function (head) { const t = h('div', { class: 'wg-track' + (head ? ' head' : '') }); for (let i = 1; i <= YEARS; i++) t.appendChild(h('span', { class: 'wg-cell' + (i === y ? ' cur' : ''), text: head ? i : null })); return t; };
    box.appendChild(h('div', { class: 'wg-lab head', text: 'Year' })); box.appendChild(cells(true));
    S.tasks.forEach(function (t) {
      if (t.group) { box.appendChild(h('div', { class: 'wg-grp', text: t.group })); return; }
      const track = cells(false), bar = h('i', { class: 'wg-bar ' + t.kind, style: { left: (t.from - 1) / YEARS * 100 + '%', width: (t.to - t.from + 1) / YEARS * 100 + '%' }, tabindex: 0 });
      PTS.tip.bind(bar, '<b>' + t.label + '</b><br>' + (t.from === t.to ? 'Year ' + t.from : 'Years ' + t.from + ' to ' + t.to) + ' (assumed)');
      track.appendChild(bar);
      box.appendChild(h('div', { class: 'wg-lab' + (y >= t.from && y <= t.to ? ' now' : ''), text: t.label })); box.appendChild(track);
      if (t.opens) {
        const tr = cells(false), m = h('i', { class: 'wg-open', style: { left: t.to / YEARS * 100 + '%' }, tabindex: 0 });
        PTS.tip.bind(m, '<b>' + t.opens + '</b><br>After year ' + t.to + ' (assumed)');
        tr.appendChild(m);
        box.appendChild(h('div', { class: 'wg-lab strong' + (y > t.to ? ' now' : ''), text: t.opens + ', after year ' + t.to })); box.appendChild(tr);
      }
    });
    PTS.clear($('#works-tl-gantt')).appendChild(box);
  }
  function seen() {
    const y = state.year, host = PTS.clear($('#works-tl-seen'));
    S.seen.forEach(function (st) {
      const ph = st.phases.filter(function (p) { return y <= p.to; })[0], cls = /Open|Finished/.test(ph.state) ? ' open' : /Works|Tests/.test(ph.state) ? ' doing' : '';
      host.appendChild(h('div', { class: 'card' }, h('h4', { text: st.name }), h('span', { class: 'works-chip' + cls, text: ph.state }), h('p', { text: ph.text })));
    });
  }
  const legend = $('#works-tl-legend');
  [['none', 'Not started'], ['works', 'Under construction'], ['open', 'Open']].forEach(function (l) {
    legend.appendChild(h('li', null, s('svg', { class: 'draw', viewBox: '0 0 30 12', width: 30, height: 12, 'aria-hidden': 'true' }, s('line', { class: 'wk-line ' + l[0], x1: 2, x2: 28, y1: 6, y2: 6 })), l[1]));
  });
  [['civil', 'Structures and tunnels'], ['fit', 'Track, power and signalling'], ['test', 'Tests'], ['surface', 'Halls and surface']].forEach(function (l) { legend.appendChild(h('li', null, h('i', { class: 'wg-key ' + l[0] }), l[1])); });

  const setYear = function (v) { state.year = v; readout(); gantt(); seen(); redraw(); };
  const slider = PTS.slider($('#works-tl-slider'), { label: 'Year of the works', min: 0, max: AFTER, step: 1, value: state.year, format: yearName, note: 'Year 0 is today; the last step is after the works' }, function (v) { setYear(v); });
  const jump = h('div', { class: 'steps', role: 'group', 'aria-label': 'Jump to a year' });
  [[0, 'Today'], [2, 'Year 2'], [6, 'Year 6'], [S.open.first, 'Year ' + S.open.first + ': first stage open'], [AFTER, 'All open']].forEach(function (j) { jump.appendChild(h('button', { type: 'button', text: j[1], onclick: function () { slider.set(j[0]); } })); });
  $('#works-tl-jump').appendChild(jump);
  mount('#works-tl-net', net, 560);
  readout(); gantt(); seen();

  // ================================================================ how long comparable works took
  PTS.chart.bars($('#works-durations'), { max: 24, rows: S.durations.map(function (r) {
    return { label: r.name, value: r.years, hl: r.kind === 'here', color: r.kind === 'here' ? 'var(--s2)' : r.kind === 'built' ? 'var(--s1)' : 'var(--neutral-mark)', text: F.n(r.years, r.years % 1 ? 1 : 0) + ' years',
      tip: '<b>' + r.name + '</b><br>' + r.what + '<br>' + r.span };
  }) });
});
