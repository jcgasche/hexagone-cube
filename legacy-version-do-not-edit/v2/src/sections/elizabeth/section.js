PTS.section('elizabeth', function (root) {
  'use strict';
  const D = PTS.data.elizabeth, M = PTS.data.model, B = PTS.data.finance.base, F = PTS.fmt, h = PTS.h, s = PTS.s, C = PTS.chart;
  const $ = function (sel) { return root.querySelector(sel); };
  const key = function (e, fn) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fn(); } };

  // ================================================================ 1. the line: diagram, depth profile, station notes
  const ST = D.stations, names = {}, item = {};
  ST.concat(D.branches).forEach(function (x) { names[x.id] = x.name; item[x.id] = x; });
  const lineHost = $('#el-line'), scroller = $('#el-line-scroll'), pick = $('#el-pick');
  let sel = 'lst', hot = {}, drops = {};
  const step = function (d) { const i = D.order.indexOf(sel); select(D.order[(i + d + D.order.length) % D.order.length], true); };

  function applySel() {
    Object.keys(hot).forEach(function (id) { hot[id].forEach(function (el) { el.classList.toggle('sel', id === sel); el.setAttribute('aria-pressed', String(id === sel)); }); });
    Object.keys(drops).forEach(function (id) { drops[id].classList.toggle('sel', id === sel); });
  }
  function select(id, reveal) {
    sel = id;
    const x = item[id], focusNav = pick.contains(document.activeElement) ? document.activeElement.dataset.d : null;
    PTS.clear(pick);
    pick.appendChild(h('div', { class: 'el-pick-head' },
      h('h3', null, x.name + ' ', h('span', { class: 'tag', text: x.kind })),
      h('div', { class: 'el-nav' },
        h('button', { class: 'btn', type: 'button', 'data-d': '-1', 'aria-label': 'Previous station', text: '←', onclick: function () { step(-1); } }),
        h('span', { text: (D.order.indexOf(id) + 1) + ' of ' + D.order.length }),
        h('button', { class: 'btn', type: 'button', 'data-d': '1', 'aria-label': 'Next station', text: '→', onclick: function () { step(1); } }))));
    pick.appendChild(h('dl', { class: 'el-facts' }, x.facts.map(function (f) { return h('div', null, h('dt', { text: f[0] }), h('dd', { text: f[1] })); })));
    if (focusNav) { const b = pick.querySelector('button[data-d="' + focusNav + '"]'); if (b) b.focus(); }
    applySel();
    if (reveal && hot[id] && scroller.scrollWidth > scroller.clientWidth) {          // on a phone the drawing scrolls sideways: bring the chosen station into view
      const r = hot[id][0].getBoundingClientRect(), q = scroller.getBoundingClientRect();
      scroller.scrollLeft += (r.left + r.width / 2) - (q.left + q.width / 2);
    }
  }

  function drawLine(W) {
    PTS.clear(lineHost); hot = {}; drops = {};
    const VW = Math.max(W, 800), padL = 128, padR = 40, dx = (VW - padL - padR) / 9;
    const X = function (i) { return padL + i * dx; };
    const yUp = 40, yM = 94, yG = 204, sc = 3.2, gH = 44 * sc, H = Math.ceil(yG + gH + 6), gx0 = 58, gx1 = VW - 8;
    const Y = function (d) { return yG + d * sc; };
    const svg = s('svg', { class: 'draw el-map' + (dx < 78 ? ' el-tight' : ''), width: VW, height: H, viewBox: '0 0 ' + VW + ' ' + H, role: 'img',
      'aria-label': 'Diagram of the Elizabeth line, with its ten new stations and its three older branches, above a profile of the depth of the stations' });
    const add = function (el) { svg.appendChild(el); return el; };
    const mkHot = function (id, tip, kids, twin) {             // twin: a second mark for the same station, left out of the keyboard order
      const g = s('g', { class: 'hot el-hot', tabindex: twin ? -1 : 0, role: 'button', 'aria-label': names[id] + ': show details' }, kids);
      g.addEventListener('click', function () { select(id); });
      g.addEventListener('keydown', function (e) { key(e, function () { select(id); }); });
      PTS.tip.bind(g, tip);
      (hot[id] = hot[id] || []).push(g);
      return g;
    };
    const hit = function (x, y, w, hh) { return s('rect', { class: 'el-hit', x: x, y: y, width: w, height: hh, rx: 5 }); };
    const hitLine = function (d) { return s('path', { d: d, fill: 'none', stroke: 'transparent', 'stroke-width': 18 }); };
    const text = function (cls, x, y, t, anchor) { return s('text', { class: cls, x: x, y: y, 'text-anchor': anchor || 'middle', text: t }); };
    const branchTip = function (b) { return '<b>' + b.name + '</b><br>' + b.tip + '<br><small>Click for details</small>'; };
    const br = {}; D.branches.forEach(function (b) { br[b.id] = b; });

    // ---- depth profile: ground, scale, light drop lines from each station on the diagram to its place in the ground
    add(s('rect', { class: 'ground', x: gx0, y: yG, width: gx1 - gx0, height: gH }));
    [10, 20, 30, 40].forEach(function (d) {
      add(s('line', { class: 'el-gridline', x1: gx0, x2: gx1, y1: Y(d), y2: Y(d) }));
      add(text('lbl-muted', gx0 - 7, Y(d) + 4, d + ' m', 'end'));
    });
    add(text('lbl-muted', gx0 - 7, yG + 4, '0', 'end'));
    add(text('lbl-muted', gx0 + 6, yG - 8, 'street level', 'start'));
    add(text('lbl-muted', (X(7) + X(8)) / 2 + 2, yG - 8, 'Thames'));
    ST.forEach(function (st, i) {
      drops[st.id] = add(s('line', { class: 'el-drop', x1: X(i), x2: X(i), y1: yM + 50, y2: st.surface ? yG - 11 : Y(st.depth) - 6 }));
    });

    // ---- diagram: older branches in the west
    const xR = 22;
    add(mkHot('reading', branchTip(br.reading), [hit(8, yM - 30, 98, 38),
      s('path', { class: 'oldline', d: 'M' + xR + ' ' + yM + ' L' + X(0) + ' ' + yM }),
      s('circle', { class: 'el-end', cx: xR, cy: yM, r: 5 }), text('el-name', xR - 6, yM - 12, 'Reading', 'start')]));
    add(mkHot('heathrow', branchTip(br.heathrow), [hit(8, yM + 10, 98, 44),
      s('path', { class: 'oldline', d: 'M' + (xR + 54) + ' ' + yM + ' L' + (xR + 26) + ' ' + (yM + 28) + ' L' + xR + ' ' + (yM + 28) }),
      s('circle', { class: 'el-end', cx: xR, cy: yM + 28, r: 5 }), text('el-name', xR - 6, yM + 47, 'Heathrow', 'start')]));

    // ---- diagram: north-eastern branch (new tunnel as far as Stratford, then the existing line)
    const xJ = X(5) + 0.62 * dx, rise = yM - yUp, xSt = xJ + rise + 0.42 * dx, xSh = X(8) + 0.25 * dx;
    const dNew = 'M' + xJ + ' ' + yM + ' L' + (xJ + rise) + ' ' + yUp + ' L' + (xSt - 14) + ' ' + yUp, dOld = 'M' + (xSt - 14) + ' ' + yUp + ' L' + xSh + ' ' + yUp;
    add(mkHot('shenfield', branchTip(br.shenfield), [hit(xJ + rise - 8, yUp - 28, xSh - xJ - rise + 44, 40), hitLine(dNew),
      s('path', { class: 'newline', d: dNew }), s('path', { class: 'oldline', d: dOld }),
      s('circle', { class: 'el-end', cx: xSt, cy: yUp, r: 4 }), s('circle', { class: 'el-end', cx: xSh, cy: yUp, r: 5 }),
      text('el-name', xSt, yUp - 12, 'Stratford'), text('el-name', xSh, yUp - 12, 'Shenfield')]));

    // ---- diagram: the new railway and its stations
    add(s('path', { class: 'newline', d: 'M' + X(0) + ' ' + yM + ' L' + X(9) + ' ' + yM }));
    ST.forEach(function (st, i) {
      if (i) add(text('lbl-muted', i === 6 ? X(5) + 0.3 * dx : (X(i - 1) + X(i)) / 2, yM - 9, st.min + ' min'));
      const tip = '<b>' + st.name + '</b><br>' + st.kind + '<br>Depth: ' + st.depthText + (i ? '<br>' + st.cum + ' minutes from Paddington' : '') + '<br><small>Click for details</small>';
      add(mkHot(st.id, tip, [hit(X(i) - dx / 2 + 3, yM - 13, dx - 6, 60), s('circle', { class: 'el-dot', cx: X(i), cy: yM, r: 7 })]
        .concat(st.label.map(function (t, k) { return text('el-name', X(i), yM + 27 + k * 15, t); }))));
    });
    add(mkHot('junction', branchTip(br.junction), [hit(xJ - 10, yM - 10, 20, 20),
      s('rect', { class: 'el-dot', x: xJ - 4.5, y: yM - 4.5, width: 9, height: 9, transform: 'rotate(45 ' + xJ + ' ' + yM + ')' })]));

    // ---- profile: the existing line at street level, then the new railway down through the stations and back up
    const pW = X(0) - 0.5 * dx;
    add(s('path', { class: 'oldline', d: 'M' + gx0 + ' ' + yG + ' L' + pW + ' ' + yG }));
    const pts = [[pW, 0], [X(0) - 14, 21], [X(0) + 14, 21], [X(1) - 14, 28], [X(1) + 14, 28], [X(3) - 14, 29.5], [X(3) + 14, 29.5], [X(4) - 14, 34], [X(4) + 14, 34],
      [X(5) - 14, 30], [X(5) + 14, 30], [X(6) - 14, 28], [X(6) + 14, 28], [X(7) - 0.45 * dx, 0], [X(7) + 0.3 * dx, 0], [X(8) - 14, 14.5], [X(8) + 14, 14.5], [X(9) - 0.4 * dx, 0], [X(9) + 14, 0]];
    add(s('path', { class: 'newline', 'stroke-linejoin': 'round', d: pts.map(function (p, k) { return (k ? 'L' : 'M') + p[0].toFixed(1) + ' ' + Y(p[1]).toFixed(1); }).join(' ') }));
    ST.forEach(function (st, i) {
      const cy = st.surface ? yG - 5 : Y(st.depth), above = st.concourse, ly = st.surface ? yG + 17 : above ? cy - 12 : cy + 20;
      const tip = '<b>' + st.name + '</b><br>' + st.kind + '<br>Depth: ' + st.depthText + '<br><small>Click for details</small>';
      add(mkHot(st.id, tip, [hit(X(i) - 30, Math.min(cy - 8, ly - 13), 60, Math.abs(ly - cy) + 22),
        s('rect', { class: 'el-box' + (st.concourse ? ' el-open' : ''), x: X(i) - 14, y: cy - 5, width: 28, height: 10, rx: 2 }),
        text('el-depth', X(i), ly, st.depthText)], true));
    });
    lineHost.appendChild(svg);
    $('#el-swipe').hidden = VW <= W;
    applySel();
  }
  if (lineHost.clientWidth && lineHost.clientWidth < 800) sel = 'pad';      // on a phone the drawing scrolls sideways: start at its visible end
  PTS.onResize(lineHost, drawLine);
  select(sel);

  // ================================================================ 2. journey times before and after
  const P = D.pairs, KIND = D.kinds;
  const findPair = function (a, b) { return P.filter(function (p) { return (p.a === a && p.b === b) || (p.a === b && p.b === a); })[0]; };
  const partners = function (a) { return D.places.filter(function (b) { return b !== a && findPair(a, b); }); };
  const mins = function (v) { return F.n(v, v % 1 ? 1 : 0); };
  let from = 'Paddington', to = 'Abbey Wood';
  const selA = h('select', { id: 'el-from' }, D.places.map(function (p) { return h('option', { value: p, text: p }); }));
  const selB = h('select', { id: 'el-to' });
  $('#el-times-controls').appendChild(h('div', { class: 'field' }, h('label', { for: 'el-from', text: 'From' }), selA));
  $('#el-times-controls').appendChild(h('div', { class: 'field' }, h('label', { for: 'el-to', text: 'To' }), selB));
  const fillTo = function () {
    const opts = partners(from); if (opts.indexOf(to) < 0) to = opts[0];
    PTS.clear(selB); opts.forEach(function (p) { selB.appendChild(h('option', { value: p, text: p })); });
    selA.value = from; selB.value = to;
  };

  function showResult() {
    const p = findPair(from, to), host = PTS.clear($('#el-times-result')), both = p.before != null && p.after != null;
    let big, sub;
    if (both) {
      const d = p.before - p.after;
      big = d === 0 ? 'no time saved' : mins(d) + ' minutes saved' + (p.beforeOpen ? ', or more' : '');
      sub = d === 0 || p.beforeOpen ? '' : F.pct(d / p.before) + ' of the time before';
    } else { big = mins(p.saving) + ' minutes saved'; sub = ''; }
    const left = host.appendChild(h('div', { class: 'el-res-side' })), right = host.appendChild(h('div'));
    left.appendChild(h('h3', { text: from + ' to ' + to + ': ' + big }));
    if (sub) left.appendChild(h('p', { class: 'el-res-note', text: sub.charAt(0).toUpperCase() + sub.slice(1) + '.' }));
    left.appendChild(h('p', { class: 'el-res-note' }, h('b', { text: KIND[p.kind] + '. ' }), p.note || ''));
    if (p.measured) left.appendChild(h('p', { class: 'el-res-note', text: 'Journeys counted at peak between the two areas rose from ' + F.n(p.measured.n0) + ' to ' + F.n(p.measured.n1) + '.' }));
    const rows = [];
    if (p.measured) rows.push({ group: 'Platform to platform' });
    if (p.before != null) rows.push({ label: 'Before', value: p.before, color: 'var(--neutral-mark)', text: (p.beforeOpen ? 'more than ' : '') + mins(p.before) + ' min' });
    if (p.after != null) rows.push({ label: 'With the Elizabeth line', value: p.after, color: 'var(--s1)', text: mins(p.after) + ' min' });
    if (p.measured) rows.push({ group: 'Door to door, measured at peak' },
      { label: 'October 2019', value: p.measured.before, color: 'var(--neutral-mark)', text: mins(p.measured.before) + ' min' },
      { label: 'October 2023', value: p.measured.after, color: 'var(--s1)', text: mins(p.measured.after) + ' min' });
    if (rows.length) C.bars(right, { rows: rows, max: 80, compact: true, fmt: function (v) { return mins(v) + ' min'; } });
  }

  const MAXMIN = 70, pos = function (v) { return Math.min(100, v / MAXMIN * 100) + '%'; };
  function drawPairs() {
    const host = PTS.clear($('#el-pairs')), box = h('div', { class: 'bars el-db' }), cur = findPair(from, to);
    box.appendChild(h('div', { class: 'lab' }));
    box.appendChild(h('div', { class: 'track el-ax', 'aria-hidden': 'true' }, [0, 20, 40, 60].map(function (t) { return h('span', { style: { left: pos(t) }, text: t ? String(t) : '0 min' }); })));
    box.appendChild(h('div', { class: 'el-axval', text: 'Saved' }));
    D.groups.forEach(function (g) {
      box.appendChild(h('div', { class: 'grp', text: g[1] }));
      P.filter(function (p) { return p.g === g[0] && p.before != null && p.after != null; })
        .sort(function (a, b) { return (b.before - b.after) - (a.before - a.after); })
        .forEach(function (p) {
          const d = p.before - p.after, hl = p === cur ? ' hl' : '', pick = function () { from = p.a; to = p.b; fillTo(); showResult(); drawPairs(); };
          const lab = h('div', { class: 'lab' + hl, onclick: pick }, p.a + ' to ' + p.b);
          const track = h('button', { class: 'track' + hl, type: 'button', 'aria-label': p.a + ' to ' + p.b + ': ' + mins(p.before) + ' minutes before, ' + mins(p.after) + ' with the line. Show above', onclick: pick },
            h('i', { class: 'el-rng', style: { left: pos(p.after), width: (Math.min(MAXMIN, p.before) - p.after) / MAXMIN * 100 + '%' } }),
            h('i', { class: 'el-b', style: { left: pos(p.before) } }), h('i', { class: 'el-a', style: { left: pos(p.after) } }));
          PTS.tip.bind(track, '<b>' + p.a + ' to ' + p.b + '</b><br>Before: <b>' + (p.beforeOpen ? 'more than ' : '') + mins(p.before) + ' min</b><br>With the line: <b>' + mins(p.after) + ' min</b><br><small>' + KIND[p.kind] + '</small>');
          box.appendChild(lab); box.appendChild(track);
          box.appendChild(h('div', { class: 'val', text: mins(d) + (p.beforeOpen ? '+' : '') + ' min' }));
        });
    });
    host.appendChild(box);
  }
  selA.addEventListener('change', function () { from = selA.value; fillTo(); showResult(); drawPairs(); });
  selB.addEventListener('change', function () { to = selB.value; showResult(); drawPairs(); });
  fillTo(); showResult(); drawPairs();

  // ================================================================ 3. traffic: stages, daily trips, where passengers came from
  const SG = D.stages, stageHost = $('#el-stage-draw');
  let stage = 's3', stageW = 0;
  function drawStage(W) {
    stageW = W; PTS.clear(stageHost);
    const k = SG.map(function (g) { return g.id; }).indexOf(stage), g = SG[k], H = 150, y1 = 56, y2 = 104;
    const x0 = 12, xE = W - 12, xP = Math.max(0.36 * W, 118), xL = Math.max(0.56 * W, xP + 66), xJ = xL + 0.07 * W, xS = xJ + Math.max(0.09 * W, 30);
    const svg = s('svg', { class: 'draw el-stage', width: W, height: H, viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': g.title + '. ' + g.text });
    const add = function (el) { svg.appendChild(el); return el; };
    const text = function (cls, x, y, t, anchor) { return add(s('text', { class: cls, x: x, y: y, 'text-anchor': anchor || 'middle', text: t })); };
    const path = function (cls, d) { return add(s('path', { class: cls, d: d })); };
    text(null, x0, 26, 'Reading,', 'start'); text(null, x0, 41, 'Heathrow', 'start');
    text(null, xP, 41, 'Paddington'); text(null, xL, 26, 'Liverpool'); text(null, xL, 41, 'Street');
    text(null, xE, 41, 'Shenfield', 'end'); text(null, xE, y2 + 21, 'Abbey Wood', 'end');
    if (k < 2) {                                         // the older services still end at the two terminals
      path('oldline', 'M' + x0 + ' ' + y1 + ' L' + (xP - 3) + ' ' + y1); path('oldline', 'M' + xE + ' ' + y1 + ' L' + (xL + 3) + ' ' + y1);
      add(s('line', { class: 'el-buffer', x1: xP, x2: xP, y1: y1 - 7, y2: y1 + 7 })); add(s('line', { class: 'el-buffer', x1: xL, x2: xL, y1: y1 - 7, y2: y1 + 7 }));
    }
    if (k === 0) { path('el-plan', 'M' + xP + ' ' + y2 + ' L' + xE + ' ' + y2); text('lbl-muted', (xP + xL) / 2, y2 + 21, 'tunnel being built'); }
    if (k === 1) {
      path('newline', 'M' + xP + ' ' + y2 + ' L' + xE + ' ' + y2);
      [xP, xL].forEach(function (x) { path('el-change', 'M' + x + ' ' + (y1 + 13) + ' L' + x + ' ' + (y2 - 12) + ' M' + (x - 4) + ' ' + (y1 + 18) + ' L' + x + ' ' + (y1 + 13) + ' L' + (x + 4) + ' ' + (y1 + 18) + ' M' + (x - 4) + ' ' + (y2 - 17) + ' L' + x + ' ' + (y2 - 12) + ' L' + (x + 4) + ' ' + (y2 - 17)); text('el-changelbl', x + 8, (y1 + y2) / 2 + 4, 'change', 'start'); });
    }
    if (k >= 2) {                                        // trains dive into the tunnel and run through
      path('el-stub', 'M' + (xP - 40) + ' ' + y1 + ' L' + (xP - 3) + ' ' + y1); path('el-stub', 'M' + xS + ' ' + y1 + ' L' + (xL + 3) + ' ' + y1);
      add(s('line', { class: 'el-buffer', x1: xP, x2: xP, y1: y1 - 7, y2: y1 + 7 })); add(s('line', { class: 'el-buffer', x1: xL, x2: xL, y1: y1 - 7, y2: y1 + 7 }));
      path('oldline', 'M' + x0 + ' ' + y1 + ' L' + (xP - 40) + ' ' + y1); path('oldline', 'M' + xE + ' ' + y1 + ' L' + xS + ' ' + y1);
      path('newline', 'M' + (xP - 40) + ' ' + y1 + ' L' + (xP - 12) + ' ' + y2 + ' L' + xE + ' ' + y2); path('newline', 'M' + xS + ' ' + y1 + ' L' + xJ + ' ' + y2);
    }
    if (k >= 1) {
      add(s('circle', { class: 'el-dot', cx: xP, cy: y2, r: 5.5 })); add(s('circle', { class: 'el-dot', cx: xL, cy: y2, r: 5.5 }));
      text('lbl-muted', (xP + xL) / 2, y2 + 21, (k === 1 ? '' : 'up to ') + g.tph + ' trains an hour');
    }
    stageHost.appendChild(svg);
  }
  function showStage(id) {
    stage = id;
    const g = SG.filter(function (x) { return x.id === id; })[0];
    if (stageW) drawStage(stageW);
    $('#el-stage-title').textContent = g.title;
    $('#el-stage-text').textContent = g.text;
    const read = PTS.clear($('#el-stage-read'));
    [['Trains an hour through the centre, busiest times', g.tph == null ? 'none' : (g.id === 's1' ? '' : 'up to ') + g.tph],
     ['Places each way in an hour', g.cap == null ? 'none' : F.n(g.cap)],
     ['Trips a day', 'about ' + F.n(g.daily)]].forEach(function (r) { read.appendChild(h('dt', { text: r[0] })); read.appendChild(h('dd', { text: r[1] })); });
    C.bars($('#el-daily'), { compact: true, fmt: function (v) { return F.n(v); }, max: 800000, rows: D.daily.map(function (r) {
      return { label: r.label, value: r.value, color: r.stage === 'before' ? 'var(--neutral-mark)' : 'var(--s1)', hl: r.stage === id, tip: '<b>' + r.label + '</b><br>About ' + F.n(r.value) + ' trips a day' };
    }) });
  }
  PTS.steps($('#el-stage-steps'), SG.map(function (g) { return [g.id, g.step]; }), stage, showStage);
  PTS.onResize(stageHost, drawStage);
  showStage(stage);

  const pctFmt = function (v) { return F.n(v, 0) + '%'; };
  const rail = D.origin.slice(0, 4), onRail = rail.reduce(function (a, r) { return a + r.value; }, 0);
  C.bars($('#el-origin'), { compact: true, fmt: pctFmt, max: 62, rows: rail.map(function (r) { return { label: r.label, value: r.value, color: 'var(--s1)' }; })
    .concat([{ label: 'Already on rail, in all', value: onRail, color: 'var(--s1)', hl: true }, { sep: true },
             { label: D.origin[4].label, value: D.origin[4].value, color: 'var(--s2)', hl: true }]) });
  C.bars($('#el-otherwise'), { compact: true, fmt: pctFmt, max: 100, rows: D.otherwise.map(function (r) { return { label: r.label, value: r.value, color: 'var(--s1)' }; }) });

  // ================================================================ 4. money
  const gbp = function (v) { return '£' + F.n(v, 1) + 'bn'; }, gbm = function (v) { return '£' + F.n(v, 0) + 'm'; };
  C.stack($('#el-funding'), { fmt: gbp, rows: [{ label: '<b>Funding agreed in 2010</b><br>before the overrun', parts: D.funding.map(function (p, i) { return { label: p.label, value: p.value, color: C.colors[i] }; }), text: '£14.8bn' }] });
  const acc = [];
  D.opacc.forEach(function (y) {
    acc.push({ group: y.year + ', ' + y.journeys + ' million journeys' },
      { label: 'Fares', value: y.income, color: 'var(--s1)' }, { label: 'Operating cost', value: y.cost, color: 'var(--neutral-mark)' });
  });
  C.bars($('#el-opacc'), { fmt: gbm, max: 800, rows: acc });

  const ratio = function (v) { return F.n(v, 2); }, RMAX = 4, rpos = function (v) { return (v / RMAX * 100) + '%'; };
  const BCR = [
    { label: 'At approval', sub: '2011', range: [3.09, 3.53], text: '1.97; 3.09 to 3.53', marks: [
      [1.97, 'el-a', 'Transport benefits only: <b>1.97</b>'],
      [3.09, 'el-w', 'With wider benefits: <b>3.09 to 3.53</b>'], [3.53, 'el-w', 'With wider benefits: <b>3.09 to 3.53</b>']] },
    { label: 'After the cost rise', sub: '2020', text: '1.37; 1.88', marks: [
      [1.37, 'el-a', 'Transport benefits only: <b>1.37</b>'], [1.88, 'el-w', 'With wider benefits: <b>1.88</b>']] },
    { label: 'With the traffic measured since 2022', text: 'not published', marks: [] }];
  const bcr = h('div', { class: 'bars el-db el-bcr' });
  bcr.appendChild(h('div', { class: 'lab' }));
  bcr.appendChild(h('div', { class: 'track el-ax', 'aria-hidden': 'true' }, [0, 1, 2, 3, 4].map(function (v) { return h('span', { style: { left: rpos(v) }, text: String(v) }); })));
  bcr.appendChild(h('div', { class: 'el-axval', text: 'Ratio' }));
  BCR.forEach(function (r) {
    const track = h('div', { class: 'track' }, h('i', { class: 'el-ref' }),
      r.range ? h('i', { class: 'el-rng', style: { left: rpos(r.range[0]), width: rpos(r.range[1] - r.range[0]) } }) : null);
    r.marks.forEach(function (m) {
      const dot = h('i', { class: m[1], style: { left: rpos(m[0]) }, tabindex: 0, role: 'img', 'aria-label': r.label + ': ' + ratio(m[0]) });
      PTS.tip.bind(dot, '<b>' + r.label + (r.sub ? ', ' + r.sub : '') + '</b><br>' + m[2]);
      track.appendChild(dot);
    });
    bcr.appendChild(h('div', { class: 'lab' }, r.label, r.sub ? h('small', { text: ' ' + r.sub }) : null));
    bcr.appendChild(track);
    bcr.appendChild(h('div', { class: 'val', text: r.text }));
  });
  $('#el-bcr').appendChild(bcr);

  // ================================================================ 5. scale against Paris
  const L = D.london, cA = M.cost.A, cB = M.cost.B, LON = 'var(--s2)', PAR = 'var(--s1)';
  const three = function (sel, fmt, lon, a, b, extra) {
    C.bars($(sel), Object.assign({ compact: true, fmt: fmt, rows: [
      Object.assign({ label: 'Elizabeth line', value: lon, color: LON }, (extra && extra.lon) || {}),
      Object.assign({ label: 'Paris, layout A', value: a, color: PAR }, (extra && extra.a) || {}),
      Object.assign({ label: 'Paris, layout B', value: b, color: PAR }, (extra && extra.b) || {})] }));
  };
  three('#el-scale-tunnel', function (v) { return F.n(v, v % 1 ? 1 : 0) + ' km'; }, L.tunnel_km, cA.tunnel_km, cB.tunnel_km);
  three('#el-scale-platform', function (v) { return F.n(v) + ' m'; }, L.platform_m, cA.platform_total, cB.platform_total);
  three('#el-scale-cost', function (v) { return F.bn(v, v % 1 ? 1 : 0); }, L.cost_eur, cA.total, cB.total, { lon: { text: 'about €' + L.cost_eur + 'bn' },
    a: { lo: M.cost_low.A, hi: M.cost_high.A }, b: { lo: M.cost_low.B, hi: M.cost_high.B } });

  const len = B.cost_def.len, ne = B.cost_def.layouts.A.stations['Paris Nord-Est'], size = h('div', { class: 'el-size' });
  const sizeRow = function (title, sub, n, metres, cls) {
    const lines = h('div', { class: 'lines' + (cls ? ' ' + cls : ''), tabindex: 0 });
    for (let i = 0; i < n; i++) lines.appendChild(h('i', { style: { '--w': (metres / 400 * 100) + '%' } }));
    PTS.tip.bind(lines, '<b>' + title + '</b><br>' + sub + '<br><small>' + F.n(n * metres) + ' m of platform track</small>');
    size.appendChild(h('div', { class: 'lab' }, h('b', { text: title }), h('span', { text: sub })));
    size.appendChild(lines);
  };
  sizeRow('London, one Elizabeth line station', L.tracks + ' tracks of about ' + L.platform_len + ' m, for trains of ' + L.train_len + ' m', L.tracks, L.platform_len, 'old');
  size.appendChild(h('div', { class: 'sep' }));
  sizeRow('Paris Nord-Est, high-speed trains', ne.hs + ' tracks of ' + len.hs + ' m', ne.hs, len.hs);
  sizeRow('Paris Nord-Est, regional express trains', ne.ter + ' tracks of ' + len.ter + ' m', ne.ter, len.ter);
  sizeRow('Paris Nord-Est, suburban trains', ne.sub + ' tracks of ' + len.sub + ' m', ne.sub, len.sub);
  size.appendChild(h('div', { class: 'lab ruler-lab' }, h('span', { text: 'Scale' })));
  size.appendChild(h('div', { class: 'ruler', 'aria-hidden': 'true' }, [0, 100, 200, 300, 400].map(function (v) { return h('span', { style: { left: (v / 4) + '%' }, text: v ? v + ' m' : '0' }); })));
  $('#el-size').appendChild(size);
});
