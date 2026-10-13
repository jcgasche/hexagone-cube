PTS.section('stations', function (root) {
  'use strict';
  const D = PTS.data.model, S = PTS.data.stations, F = PTS.fmt, h = PTS.h, s = PTS.s;
  const $ = function (sel) { return root.querySelector(sel); };
  const LEN = D.len, C = D.cost, COL = { hs: 'var(--s1)', ter: 'var(--s2)', sub: 'var(--s3)' };
  const state = { step: 3, depth: S.walk.depth };
  const drawings = [];                                       // every drawing registers a function that redraws it at its current width
  const redrawAll = function () { drawings.forEach(function (f) { f(); }); };
  function mount(sel, fn, maxW) {                            // draw at the real pixel width, again when the width or the layout changes
    const host = $(sel); let w = 0;
    const run = function () { if (w) { PTS.clear(host).appendChild(fn(w)); } };
    drawings.push(run);
    PTS.onResize(host, function (nw) { w = Math.min(nw, maxW || 620); run(); });
  }
  function note(el, label, tip) {                            // a mark that can be hovered or reached with the keyboard
    el.setAttribute('tabindex', '0'); el.setAttribute('role', 'img'); el.setAttribute('aria-label', label); el.classList.add('hot');
    PTS.tip.bind(el, tip);
    return el;
  }
  // platform groups of one station: TGV tracks (three each way), regional express, suburban
  function groups(name) {
    const det = C.detail[name], g = [];
    g.push({ k: 'hs', label: 'TGV', tracks: det.hs, len: LEN.hs, color: COL.hs, note: (det.hs / 2) + ' tracks each way' });
    if (det.ter) g.push({ k: 'ter', label: 'Regional express', tracks: det.ter, len: LEN.ter, color: COL.ter });
    g.push({ k: 'sub', label: 'Suburban', tracks: det.sub, len: LEN.sub, color: COL.sub });
    return g;
  }

  // ================================================================ plans: the platforms of each station, all to one scale
  const PLAN = {
    'Paris Nord-Est': { halls: ['Gare du Nord', 'Gare de l’Est'], from: ['to the north and the east', 'north, east'], to: ['to Gare de Lyon and Montparnasse', 'Lyon, Montparnasse'], magenta: true, london: S.london },
    'Gare de Lyon': { halls: ['Hall'], from: ['to Paris Nord-Est', 'Nord-Est'], to: ['to the south-east', 'south-east'], link: 'Montparnasse' },
    'Montparnasse': { halls: ['Hall'], from: ['to Paris Nord-Est', 'Nord-Est'], to: ['to the Atlantic', 'Atlantic'], link: 'Gare de Lyon' }
  };
  function plan(W, name) {
    const cfg = PLAN[name], two = cfg.halls.length === 2, narrow = W < 430, pad = narrow ? 8 : 14, sc = (W - 2 * pad) / S.halls_apart, X = function (m) { return pad + m * sc; };
    const gs = groups(name), M = S.magenta, pitch = 2 * M.width / M.tracks * sc;      // one island platform with its two tracks
    const bw = narrow ? 82 : 96, x0 = X(50), x1 = X(450), pas = [150, 350];
    let y = 96; const rowsY = [];
    gs.forEach(function (g) { g.y = y + 17; g.n = g.tracks / 2; y = g.y + g.n * pitch + 6; rowsY.push(g); });
    const fieldBottom = y, magY = fieldBottom + 44, magH = M.width * sc, H = Math.round(cfg.magenta ? magY + Math.max(magH, 50) + 34 : fieldBottom + (cfg.link ? 74 : 52));
    const svg = s('svg', { class: 'draw', viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img',
      'aria-label': 'Plan of the ' + name + ' station: ' + C.tracks[name] + ' platform tracks' + (two ? ' between the halls of Gare du Nord and Gare de l’Est, with the Magenta station drawn to the same scale' : ', entered from the hall at one end, with the junction towards the link to ' + cfg.link + ' at the city end') });
    const hall = function (x, label, tip) {
      const g = s('g', null, s('rect', { class: 'struct', x: x, y: 8, width: bw, height: 30, rx: 3 }), s('text', { class: 'st-b', x: x + bw / 2, y: 28, 'text-anchor': 'middle', text: label }));
      return note(g, label + (two ? ' hall' : ''), tip);
    };
    if (two) {
      svg.appendChild(s('path', { class: 'st-dim', d: 'M' + (pad + bw + 6) + ',23H' + (W - pad - bw - 6) + 'M' + (pad + bw + 6) + ',18v10M' + (W - pad - bw - 6) + ',18v10' }));
      svg.appendChild(s('text', { class: 'st-b', x: W / 2, y: 17, 'text-anchor': 'middle', text: S.halls_apart + ' m' }));
    }
    // passage above the platforms, with a way down to every platform at two points
    const lastOpen = rowsY[rowsY.length - 1], pasBottom = lastOpen.y + lastOpen.n * pitch - pitch * 0.3;
    const pg = s('g', null, s('path', { class: 'st-pass', d: 'M' + (pad + bw / 2) + ',38V62H' + (two ? (W - pad - bw / 2) + 'V38' : X(pas[1])) }));
    pas.forEach(function (m) { pg.appendChild(s('path', { class: 'st-pass', d: 'M' + X(m) + ',62V' + pasBottom })); });
    note(pg, two ? 'Passage linking the two halls' : 'Passage from the hall above the platforms', '<b>Passage above the platforms</b><br>' + (two ? 'Links the two halls. ' : 'Leads from the hall. ') + 'Escalators and lifts lead down from it to each platform at two points.<br><small>Assumption of this sketch</small>');
    svg.appendChild(pg);
    if (two) {
      svg.appendChild(hall(pad, cfg.halls[0], '<b>Gare du Nord hall</b><br>Kept as an entrance to the station below.'));
      svg.appendChild(hall(W - pad - bw, cfg.halls[1], '<b>Gare de l’Est hall</b><br>Kept as an entrance, ' + S.halls_apart + ' m from Gare du Nord.'));
    } else svg.appendChild(hall(pad, cfg.halls[0], '<b>The hall of ' + name + '</b><br>Kept as the entrance to the station below.'));
    svg.appendChild(s('text', { class: 'lbl-muted st-halo', x: X(250), y: 80, 'text-anchor': 'middle', text: !two ? 'Passage above the platforms' : narrow ? 'Passage linking the halls' : 'Passage above the platforms, linking the two halls' }));
    // platforms, group by group
    rowsY.forEach(function (g) {
      const a = X(250 - g.len / 2), b = X(250 + g.len / 2), grp = s('g');
      grp.appendChild(s('text', { class: 'st-lbl st-halo', x: g.k === 'sub' ? a : x0, y: g.y - 6, text: g.label + ': ' + g.tracks + ' tracks, ' + g.len + ' m' + (g.note && !narrow ? ', ' + g.note : '') }));
      for (let i = 0; i < g.n; i++) {
        const yy = g.y + i * pitch;
        grp.appendChild(s('rect', { class: 'st-plat', x: a, y: yy + pitch * 0.3, width: b - a, height: pitch * 0.4 }));
        grp.appendChild(s('line', { x1: a, x2: b, y1: yy + pitch * 0.14, y2: yy + pitch * 0.14, stroke: g.color, 'stroke-width': narrow ? 1.8 : 2.2 }));
        grp.appendChild(s('line', { x1: a, x2: b, y1: yy + pitch * 0.86, y2: yy + pitch * 0.86, stroke: g.color, 'stroke-width': narrow ? 1.8 : 2.2 }));
        pas.forEach(function (m) { grp.appendChild(s('circle', { class: 'st-way', cx: X(m), cy: yy + pitch * 0.5, r: narrow ? 2.2 : 3 })); });
      }
      grp.appendChild(s('rect', { class: 'st-hit', x: pad, y: g.y - 18, width: W - 2 * pad, height: g.n * pitch + 20 }));
      const tip = '<b>' + g.label + '</b><br>' + g.tracks + ' tracks on ' + g.n + ' island platforms, ' + g.len + ' m long<br>' + F.n(g.tracks * g.len, 0) + ' m of platform track' + (g.k === 'hs' ? '<br>Dedicated by direction: ' + g.note + ', ' + cfg.from[1] + ' on one side, ' + cfg.to[1] + ' on the other' : '');
      svg.appendChild(note(grp, g.label + ', ' + g.tracks + ' tracks of ' + g.len + ' m', tip));
    });
    if (cfg.london) {                                          // one TGV track can be closed off for each London departure; its control hall is on the Gare du Nord side
      const g0 = rowsY[0], a = X(250 - g0.len / 2), b = X(250 + g0.len / 2), yy = g0.y, lg = s('g');
      lg.appendChild(s('rect', { class: 'st-seal', x: a - 4, y: yy + pitch * 0.04, width: b - a + 8, height: pitch * 0.42, rx: 3 }));
      lg.appendChild(s('rect', { class: 'struct', x: pad + 5, y: yy + pitch * 0.06, width: x0 - pad - 12, height: pitch * 0.38, rx: 2 }));
      lg.appendChild(s('path', { class: 'st-pass thin', d: 'M' + (pad + 14) + ',38V' + (yy + pitch * 0.06) }));
      lg.appendChild(s('text', { class: 'lbl-muted st-halo', x: b + 4, y: yy - 6, 'text-anchor': 'end', text: narrow ? 'London: 1 track' : 'London: 1 track at a time' }));
      svg.appendChild(note(lg, 'One TGV track that can be closed off for London departures, with its control hall on the Gare du Nord side', '<b>London departures</b><br>Any one of the TGV tracks can be closed off for the time of a departure: passengers pass the border checks in a control hall on the Gare du Nord side and board in 10 to 15 minutes.<br><small>Assumption; Amsterdam already works this way</small>'));
    }
    svg.appendChild(s('text', { class: 'lbl-muted', x: x0, y: fieldBottom + 14, text: '← ' + cfg.from[narrow ? 1 : 0] }));
    svg.appendChild(s('text', { class: 'lbl-muted', x: x1, y: fieldBottom + 14, 'text-anchor': 'end', text: cfg.to[narrow ? 1 : 0] + ' →' }));
    if (cfg.link) {                                            // the junction towards the direct link to the other southern station, at the city end: not designed
      const g0 = rowsY[0], a = X(250 - g0.len / 2), ym = g0.y + g0.n * pitch / 2, jg = s('g');
      jg.appendChild(s('path', { class: 'st-link', d: 'M' + a + ',' + ym + 'C' + X(20) + ',' + ym + ' ' + X(20) + ',' + (fieldBottom + 22) + ' ' + X(0) + ',' + (fieldBottom + 44) }));
      jg.appendChild(s('ellipse', { class: 'st-unk', cx: a - 2, cy: ym, rx: narrow ? 8 : 11, ry: narrow ? 6 : 8 }));
      jg.appendChild(s('text', { class: 'lbl-muted st-halo', x: x0, y: fieldBottom + 36, text: narrow ? 'Junction to the link to ' + cfg.link : 'Junction towards the direct link to ' + cfg.link + ': not designed' }));
      svg.appendChild(note(jg, 'Junction at the city end towards the direct link to ' + cfg.link + ', not designed', '<b>Junction towards ' + cfg.link + '</b><br>At the city end, the TGV tracks fork: towards Paris Nord-Est, and towards the direct link to ' + cfg.link + ' (' + F.n(D.link_km, 0) + ' km). Its geometry has not been designed and is a study point.'));
    }
    if (cfg.magenta) {                                        // Magenta, to the same scale
      const mg = s('g', null, s('rect', { class: 'struct', x: x0, y: magY, width: M.length * sc, height: magH, rx: 3 }));
      for (let i = 0; i < M.tracks; i++) mg.appendChild(s('line', { class: 'st-oldtrack', x1: x0 + 4, x2: x0 + M.length * sc - 4, y1: magY + magH * (i + 0.5) / M.tracks, y2: magY + magH * (i + 0.5) / M.tracks }));
      const tx = x0 + M.length * sc + 10;
      [narrow ? 'Magenta, RER E' : 'Magenta, RER E, for scale', M.tracks + ' tracks, ' + M.length + ' m long,', M.width + ' m wide, ' + M.depth + ' m down'].forEach(function (t, i) { mg.appendChild(s('text', { class: i ? 'lbl-muted' : 'st-b', x: tx, y: magY + 12 + i * 15, text: t })); });
      svg.appendChild(note(mg, 'Magenta station of RER line E, for scale', '<b>Magenta, RER line E, opened in 1999</b><br>' + M.tracks + ' tracks in a cavern ' + M.length + ' m long and ' + M.width + ' m wide, about ' + M.depth + ' m down. It lies between the two halls.'));
    }
    svg.appendChild(s('path', { class: 'st-dim', d: 'M' + X(350) + ',' + (H - 12) + 'H' + X(450) + 'M' + X(350) + ',' + (H - 16) + 'v8M' + X(450) + ',' + (H - 16) + 'v8' }));
    svg.appendChild(s('text', { class: 'lbl-muted', x: X(400), y: H - 18, 'text-anchor': 'middle', text: '100 m' }));
    return svg;
  }
  function planRead(name, sel) {
    const dl = PTS.clear($(sel)), c = C, M = S.magenta;
    const add = function (k, v, cls) { dl.appendChild(h('dt', { class: cls || null, text: k })); dl.appendChild(h('dd', { class: cls || null, text: v })); };
    dl.appendChild(h('dt', { class: 'grp', text: name }));
    groups(name).forEach(function (g) { add(g.label + ', ' + g.len + ' m' + (g.note ? ' (' + g.note + ')' : ''), g.tracks); });
    add('Platform tracks', c.tracks[name], 'sum');
    add('Platform track', F.n(c.platform_m[name], 0) + ' m');
    if (PLAN[name].magenta) add('Magenta, for comparison', F.n(M.tracks * M.length, 0) + ' m');
    else add('Share of the platform track of Paris Nord-Est', F.pct(c.platform_m[name] / c.platform_m['Paris Nord-Est']));
    add('Width at Magenta’s width per track', 'about ' + F.n(Math.round(c.tracks[name] * M.width / M.tracks / 10) * 10, 0) + ' m');
    add('Cost with design, land and 15% risk', F.bn(D.station_total[name]));
  }
  const PLANS = [['Paris Nord-Est', '#stations-plan', '#stations-plan-read'], ['Gare de Lyon', '#stations-plan-lyon', '#stations-plan-read-lyon'], ['Montparnasse', '#stations-plan-montparnasse', '#stations-plan-read-montparnasse']];
  const planReads = function () { PLANS.forEach(function (p) { planRead(p[0], p[2]); }); };

  // ================================================================ cross-sections
  function frame(W, label) {
    const narrow = W < 430, gut = 48, top = 86, mpx = narrow ? 4.6 : 5.2, maxD = 45, H = Math.round(top + maxD * mpx);
    const fr = { W: W, H: H, narrow: narrow, x: function (f) { return gut + f * (W - gut - 4); }, y: function (d) { return top + d * mpx; } };
    const svg = fr.svg = s('svg', { class: 'draw', viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img', 'aria-label': label });
    svg.appendChild(s('rect', { class: 'ground', x: gut, y: fr.y(0), width: W - gut - 4, height: H - fr.y(0), stroke: 'none' }));
    [10, 20, 30, 40].forEach(function (d) {
      svg.appendChild(s('line', { class: 'st-grid', x1: gut, x2: W - 4, y1: fr.y(d), y2: fr.y(d) }));
      svg.appendChild(s('text', { class: 'lbl-muted', x: gut - 6, y: fr.y(d) + 4, 'text-anchor': 'end', text: d + ' m' }));
    });
    svg.appendChild(s('line', { class: 'st-street', x1: gut, x2: W - 4, y1: fr.y(0), y2: fr.y(0) }));
    svg.appendChild(s('text', { class: 'lbl-muted', x: gut - 6, y: fr.y(0) + 4, 'text-anchor': 'end', text: 'Street' }));
    return fr;
  }
  function keyed(fr, key) {                                   // links the marks of a drawing to the numbered list beside it
    const items = PTS.$$('li', key), idx = {};
    items.forEach(function (li, i) { idx[li.dataset.k] = { n: i + 1, li: li, marks: [] }; });
    const tipOf = function (k) { const c = idx[k].li.cloneNode(true); PTS.$$('sup, .tag', c).forEach(function (e) { e.remove(); }); return '<b>' + idx[k].n + '.</b> ' + c.innerHTML.replace(/<(\/?)strong>/g, '<$1b>'); };
    const api = {
      add: function (k, shapes, at) {                         // shapes: SVG elements; at: [x, y, x, y...] where the number goes
        const g = s('g', { class: 'st-item' }, shapes);
        for (let i = 0; i < at.length; i += 2) {
          g.appendChild(s('circle', { class: 'st-badge', cx: at[i], cy: at[i + 1], r: 8.5 }));
          g.appendChild(s('text', { class: 'st-badge-n', x: at[i], y: at[i + 1] + 4, 'text-anchor': 'middle', text: idx[k].n }));
        }
        note(g, idx[k].li.textContent.replace(/\s+/g, ' ').trim(), function () { return tipOf(k); });
        const on = function () { idx[k].li.classList.add('on'); }, off = function () { idx[k].li.classList.remove('on'); };
        g.addEventListener('pointerenter', on); g.addEventListener('pointerleave', off); g.addEventListener('focus', on); g.addEventListener('blur', off);
        idx[k].marks.push(g); fr.svg.appendChild(g);
        return g;
      }
    };
    items.forEach(function (li) {
      li.onpointerenter = function () { idx[li.dataset.k].marks.forEach(function (m) { m.classList.add('sel'); }); };
      li.onpointerleave = function () { idx[li.dataset.k].marks.forEach(function (m) { m.classList.remove('sel'); }); };
    });
    return api;
  }
  // shapes shared by the three cross-sections
  const P = {
    hall: function (fr, f0, f1, top, arch) {
      const a = fr.x(f0), b = fr.x(f1), y0 = fr.y(0), ye = fr.y(-top);
      return s('path', { class: 'struct', d: arch ? 'M' + a + ',' + y0 + 'V' + ye + 'Q' + (a + b) / 2 + ',' + fr.y(-top - 9) + ' ' + b + ',' + ye + 'V' + y0 + 'Z' : 'M' + a + ',' + y0 + 'V' + ye + 'H' + b + 'V' + y0 + 'Z' });
    },
    surface: function (fr, f0, f1, base) {                    // surface platforms: a low canopy with a few trains under it
      const a = fr.x(f0), b = fr.x(f1), y0 = fr.y(-(base || 0)), g = s('g', null, s('path', { class: 'st-old', d: 'M' + a + ',' + y0 + 'V' + (y0 - 22) + 'H' + b + 'V' + y0 }));
      const n = Math.max(3, Math.round((b - a) / 22));
      for (let i = 0; i < n; i++) g.appendChild(s('rect', { class: 'st-oldtrain', x: a + (b - a) * (i + 0.5) / n - 4, y: y0 - 13, width: 8, height: 11, rx: 1.5 }));
      return g;
    },
    box: function (fr, f0, f1, d0, d1, cls) { return s('rect', { class: cls, x: fr.x(f0), y: fr.y(d0), width: fr.x(f1) - fr.x(f0), height: fr.y(d1) - fr.y(d0), rx: 3 }); },
    depth: function (fr, f, d, text, anchor) { return s('text', { class: 'st-b', x: fr.x(f), y: fr.y(d) + 4, 'text-anchor': anchor || 'start', text: text }); },
    neu: function (fr, name, f0, f1) {                        // the new platforms: one mark for each track
      const d = S.walk.depth, a = fr.x(f0), b = fr.x(f1), g = s('g', null, P.box(fr, f0, f1, d - 9, d + 1, 'new')), list = [];
      groups(name).forEach(function (gr) { for (let i = 0; i < gr.tracks; i++) list.push(gr); });
      const step = Math.min(9, (b - a - 12) / list.length), w = Math.max(2.5, step * 0.62), start = (a + b) / 2 - step * list.length / 2;
      list.forEach(function (gr, i) { g.appendChild(s('rect', { x: start + i * step + (step - w) / 2, y: fr.y(d - 3.4), width: w, height: fr.y(d) - fr.y(d - 3.4), rx: 1, fill: gr.color })); });
      g.appendChild(s('text', { class: 'st-b', x: (a + b) / 2, y: fr.y(d + 1) + 15, 'text-anchor': 'middle', text: 'about ' + d + ' m: ' + C.tracks[name] + ' tracks' }));
      return g;
    },
    way: function (fr, fa, fb) {                              // two flights of escalators from the street to the new platforms
      const d = S.walk.depth - 9, xa = fr.x(fa), xb = fr.x(fb), xm = (xa + xb) / 2, y0 = fr.y(0), ym = fr.y(d / 2), y1 = fr.y(d), dir = xb > xa ? 1 : -1;
      return s('g', null, s('path', { class: 'st-wayline', d: 'M' + xa + ',' + y0 + 'L' + (xm - 5 * dir) + ',' + ym + 'H' + (xm + 5 * dir) + 'L' + xb + ',' + y1 }),
        s('path', { class: 'st-wayhead', d: 'M' + xb + ',' + (y1 + 1) + 'l' + (-9 * dir) + ',-5l' + (4.5 * dir) + ',-6z' }));
    }
  };
  const XS = {
    nordest: function (W) {
      const fr = frame(W, 'Cross-section under Gare du Nord and Gare de l’Est: metro, RER lines B and D, the Magenta station 30 m down and the new platforms about ' + S.walk.depth + ' m down'), K = keyed(fr, $('#stations-key-nordest')), M = S.magenta;
      K.add('surface', [P.surface(fr, 0.25, 0.42), P.surface(fr, 0.58, 0.75)], [fr.x(0.335), fr.y(0) - 34, fr.x(0.665), fr.y(0) - 34]);
      K.add('hall1', [P.hall(fr, 0.02, 0.24, 10, true)], [fr.x(0.13), fr.y(-8)]);
      K.add('hall2', [P.hall(fr, 0.76, 0.98, 10, true)], [fr.x(0.87), fr.y(-8)]);
      K.add('metro', [P.box(fr, 0.03, 0.14, 3, 8, 'st-unk'), P.box(fr, 0.88, 0.98, 3, 8, 'st-unk')], [fr.x(0.085), fr.y(5.5), fr.x(0.93), fr.y(5.5)]);
      K.add('rer', [P.box(fr, 0.03, 0.21, 11, 19, 'st-unk')], [fr.x(0.12), fr.y(15)]);
      K.add('magenta', [P.box(fr, 0.75, 0.87, M.depth - M.height + 1, M.depth + 1, 'struct'), s('line', { class: 'st-rail', x1: fr.x(0.76), x2: fr.x(0.86), y1: fr.y(M.depth), y2: fr.y(M.depth) }), P.depth(fr, 0.81, M.depth + 4.2, M.depth + ' m', 'middle')], [fr.x(0.81), fr.y(M.depth - 6)]);
      K.add('new', [P.neu(fr, 'Paris Nord-Est', 0.05, 0.68)], [fr.x(0.09), fr.y(S.walk.depth - 6.5)]);
      K.add('ways', [P.way(fr, 0.245, 0.34), P.way(fr, 0.755, 0.64)], [fr.x(0.31), fr.y(9), fr.x(0.69), fr.y(9)]);
      return fr.svg;
    },
    lyon: function (W) {
      const fr = frame(W, 'Cross-section under Gare de Lyon: metro line 1, RER line D 20 m down, RER line A below it, metro line 14 and the new platforms about ' + S.walk.depth + ' m down'), K = keyed(fr, $('#stations-key-lyon'));
      K.add('surface', [P.surface(fr, 0.23, 0.57)], [fr.x(0.4), fr.y(0) - 34]);
      K.add('hall1', [P.hall(fr, 0.02, 0.22, 10, true)], [fr.x(0.12), fr.y(-8)]);
      K.add('metro', [P.box(fr, 0.03, 0.15, 2.5, 7.5, 'st-unk')], [fr.x(0.09), fr.y(5)]);
      fr.svg.appendChild(P.box(fr, 0.62, 0.87, 5, 28, 'st-env'));
      K.add('rerd', [P.box(fr, 0.635, 0.855, 14, S.rerd_depth + 1, 'struct'), s('line', { class: 'st-rail', x1: fr.x(0.72), x2: fr.x(0.845), y1: fr.y(S.rerd_depth), y2: fr.y(S.rerd_depth) }), P.depth(fr, 0.845, S.rerd_depth - 2.6, S.rerd_depth + ' m', 'end')], [fr.x(0.675), fr.y(S.rerd_depth - 3)]);
      K.add('rera', [P.box(fr, 0.635, 0.855, 21.5, S.rera_depth + 1.2, 'struct'), s('line', { class: 'st-rail', x1: fr.x(0.72), x2: fr.x(0.845), y1: fr.y(S.rera_depth), y2: fr.y(S.rera_depth) }), P.depth(fr, 0.845, S.rera_depth - 2, '≈ ' + S.rera_depth + ' m', 'end')], [fr.x(0.675), fr.y(S.rera_depth - 1.75)]);
      K.add('m14', [P.box(fr, 0.9, 0.99, 10, 17, 'st-unk')], [fr.x(0.945), fr.y(13.5)]);
      K.add('new', [P.neu(fr, 'Gare de Lyon', 0.12, 0.57)], [fr.x(0.16), fr.y(S.walk.depth - 6.5)]);
      K.add('ways', [P.way(fr, 0.215, 0.3)], [fr.x(0.29), fr.y(9)]);
      return fr.svg;
    },
    montparnasse: function (W) {
      const fr = frame(W, 'Cross-section under Montparnasse: platforms one level above the street under a slab with a garden, metro lines, old quarries and the new platforms about ' + S.walk.depth + ' m down'), K = keyed(fr, $('#stations-key-montparnasse'));
      fr.svg.appendChild(P.box(fr, 0.24, 0.66, -6, 0, 'struct'));
      K.add('surface', [P.surface(fr, 0.26, 0.64, 6)], [fr.x(0.45), fr.y(-3)]);
      const trees = s('g', null, s('path', { class: 'st-slab', d: 'M' + fr.x(0.25) + ',' + fr.y(-11.4) + 'H' + fr.x(0.65) }));
      [0.3, 0.37, 0.52, 0.6].forEach(function (f) { trees.appendChild(s('circle', { class: 'st-tree', cx: fr.x(f), cy: fr.y(-13.6), r: 5 })); });
      K.add('slab', [trees], [fr.x(0.445), fr.y(-13.6)]);
      K.add('hall1', [P.hall(fr, 0.03, 0.24, 13, false)], [fr.x(0.135), fr.y(-8)]);
      K.add('metro', [P.box(fr, 0.7, 0.82, 3, 8, 'st-unk'), P.box(fr, 0.86, 0.98, 3, 8, 'st-unk')], [fr.x(0.76), fr.y(5.5), fr.x(0.92), fr.y(5.5)]);
      const q = s('g'); [[0.69, 15, 0.1], [0.82, 18, 0.08], [0.92, 14.5, 0.06]].forEach(function (e) { q.appendChild(s('ellipse', { class: 'st-unk', cx: fr.x(e[0]), cy: fr.y(e[1]), rx: e[2] * (fr.x(1) - fr.x(0)) / 2, ry: 9 })); });
      K.add('quarry', [q], [fr.x(0.82), fr.y(18)]);
      K.add('new', [P.neu(fr, 'Montparnasse', 0.12, 0.6)], [fr.x(0.16), fr.y(S.walk.depth - 6.5)]);
      K.add('ways', [P.way(fr, 0.14, 0.24)], [fr.x(0.235), fr.y(11)]);
      return fr.svg;
    }
  };

  // ================================================================ depth of comparable stations
  PTS.chart.bars($('#stations-depth-chart'), { max: 45, fmt: function (v) { return F.n(v, 0) + ' m'; }, rows: S.depths.map(function (r) {
    return { label: r.name, value: r.depth, hl: r.kind === 'here', color: r.kind === 'here' ? 'var(--s2)' : r.kind === 'built' ? 'var(--s1)' : 'var(--neutral-mark)', tip: '<b>' + r.name + '</b><br>' + r.depth + ' m<br><small>' + r.what + '</small>' };
  }) });

  // ================================================================ follow a passenger
  const WK = S.walk;
  function times() {
    const down = state.depth * WK.esc_per_m / WK.esc_speed / 60;
    return { today: [0, WK.gates, 0, WK.today_m / WK.walk_speed / 60], deep: [0, WK.gates, down + WK.landings, WK.deep_m / WK.walk_speed / 60], down: down };
  }
  function walk(W) {
    const narrow = W < 430, padL = 6, hallW = narrow ? 44 : 64, px0 = padL + hallW + 8, sc = (W - 8 - px0) / WK.platform, T = times(), st = state.step;
    const k = narrow ? 1.9 : 2.1, yT = 74, yS = 176, yP = yS + 26 + state.depth * k, H = Math.round(yS + 26 + 55 * k + 40);
    const svg = s('svg', { class: 'draw', viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img',
      'aria-label': 'Two side views: a terminal today, where the passenger walks ' + WK.today_m + ' m along the platform, and a deep through station, where the passenger goes down ' + state.depth + ' m and walks ' + WK.deep_m + ' m' });
    const train = function (y) { const g = s('g'), n = 16, w = WK.platform * sc / n; for (let i = 0; i < n; i++) g.appendChild(s('rect', { class: 'st-coach', x: px0 + i * w + 1, y: y - 15, width: w - 2, height: 12, rx: 2 })); return g; };
    const trail = function (pts, upto) { return s('path', { class: 'st-trail', d: 'M' + pts.slice(0, upto + 1).map(function (p) { return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join('L') }); };
    const chip = function (x, y, t, anchor) { return s('text', { class: 'st-chip st-halo', x: x, y: y, 'text-anchor': anchor || 'middle', text: t }); };
    const who = function (p) { return s('circle', { class: 'st-who', cx: p[0], cy: p[1], r: 6 }); };

    // ---- terminal today
    svg.appendChild(s('text', { class: 'st-b', x: padL, y: 14, text: 'Terminal today' }));
    svg.appendChild(s('rect', { class: 'struct', x: padL, y: yT - 38, width: hallW, height: 38, rx: 3 }));
    svg.appendChild(s('text', { class: 'lbl-muted', x: padL + hallW / 2, y: yT - 44, 'text-anchor': 'middle', text: 'Hall' }));
    svg.appendChild(train(yT));
    svg.appendChild(s('rect', { class: 'st-plat', x: px0, y: yT, width: WK.platform * sc, height: 6 }));
    svg.appendChild(s('rect', { class: 'st-gate', x: px0 - 5, y: yT - 16, width: 3, height: 22 }));
    const xa = px0 + WK.today_m * sc, pt = [[padL + hallW / 2, yT - 9], [px0 - 3.5, yT + 3], [px0 - 3.5, yT + 3], [xa, yT + 3]];
    svg.appendChild(s('path', { class: 'st-dim', d: 'M' + xa + ',' + (yT + 10) + 'v8' }));
    svg.appendChild(s('text', { class: 'lbl-muted', x: xa, y: yT + 31, 'text-anchor': 'middle', text: 'Average coach: ' + WK.today_m + ' m from the gates' }));
    if (st >= 1) svg.appendChild(trail(pt, st));
    if (st >= 3) svg.appendChild(chip((px0 + xa) / 2, yT - 22, '+' + F.n(T.today[3], 1) + ' min'));
    svg.appendChild(who(pt[st]));

    // ---- deep through station
    const w1 = px0 + WK.platform * 0.25 * sc, w2 = px0 + WK.platform * 0.75 * sc, run = Math.min(30, WK.platform * 0.1 * sc), x1 = px0 + WK.platform * sc;
    svg.appendChild(s('text', { class: 'st-b', x: padL, y: yS - 46, text: 'Deep through station' }));
    svg.appendChild(s('rect', { class: 'ground', x: 0, y: yS, width: W, height: H - yS, stroke: 'none' }));
    svg.appendChild(s('line', { class: 'st-street', x1: 0, x2: W, y1: yS, y2: yS }));
    svg.appendChild(s('rect', { class: 'struct', x: w1 - hallW / 2, y: yS - 30, width: hallW, height: 30, rx: 3 }));
    svg.appendChild(s('text', { class: 'lbl-muted', x: w1 + hallW / 2 + 6, y: yS - 10, text: 'Hall' }));
    svg.appendChild(s('text', { class: 'lbl-muted', x: x1, y: yS - 8, 'text-anchor': 'end', text: narrow ? 'Passage: not counted' : 'Passage to the other way down: not counted' }));
    svg.appendChild(s('rect', { class: 'new', x: px0 - 5, y: yP - 22, width: WK.platform * sc + 10, height: 34, rx: 3 }));
    svg.appendChild(train(yP));
    svg.appendChild(s('rect', { class: 'st-plat', x: px0, y: yP, width: WK.platform * sc, height: 6 }));
    svg.appendChild(s('path', { class: 'st-old', d: 'M' + w1 + ',' + (yS + 8) + 'H' + w2 }));
    [w1, w2].forEach(function (x) { svg.appendChild(s('path', { class: 'st-wayline', d: 'M' + x + ',' + (yS + 8) + 'L' + (x + run) + ',' + (yS + yP) / 2 + 'L' + x + ',' + (yP + 3) })); });
    svg.appendChild(s('rect', { class: 'st-gate', x: w1 - 9, y: yS - 14, width: 3, height: 20 }));
    const xb = w1 + WK.deep_m * sc, pd = [[w1, yS - 14], [w1, yS + 8], [w1, yP + 3], [xb, yP + 3]];
    const full = [pd[0], pd[1], [w1 + run, (yS + yP) / 2], pd[2], pd[3]];
    if (st >= 1) svg.appendChild(trail(full, st === 1 ? 1 : st === 2 ? 3 : 4));
    const xd = padL + 10;
    svg.appendChild(s('path', { class: 'st-dim', d: 'M' + xd + ',' + yS + 'V' + (yP + 6) + 'M' + (xd - 4) + ',' + (yP + 6) + 'h8' }));
    svg.appendChild(s('text', { class: 'st-b', x: xd + 7, y: (yS + yP) / 2 + 8, text: state.depth + ' m' }));
    svg.appendChild(s('text', { class: 'lbl-muted', x: x1, y: yP + 28, 'text-anchor': 'end', text: 'Average coach: ' + WK.deep_m + (narrow ? ' m away' : ' m from a way down') }));
    if (st >= 2) svg.appendChild(s('text', { class: 'st-chip', x: w1 + run + 10, y: (yS + yP) / 2 + 4, text: '+' + F.n(T.deep[2], 1) + ' min' }));
    if (st >= 3) svg.appendChild(s('text', { class: 'st-chip', x: w1 - 4, y: yP + 28, text: '+' + F.n(T.deep[3], 1) + (narrow ? '' : ' min') }));
    svg.appendChild(who(st === 0 ? pd[0] : st === 1 ? pd[1] : st === 2 ? pd[2] : pd[3]));
    return svg;
  }
  function ledger() {
    const T = times(), st = state.step, t = PTS.clear($('#stations-walk-ledger'));
    const f1 = function (v) { return F.n(v, 1); }, sum = function (a) { return a.slice(0, st + 1).reduce(function (x, y) { return x + y; }, 0); };
    const rows = [['Ticket gates', f1(T.today[1]), f1(T.deep[1])],
      ['Getting down', 'none', f1(T.deep[2]) + ' (' + state.depth + ' m)'],
      ['Along the platform', f1(T.today[3]) + ' (' + WK.today_m + ' m)', f1(T.deep[3]) + ' (' + WK.deep_m + ' m)']];
    t.appendChild(h('thead', null, h('tr', null, h('th', { text: 'Minutes' }), h('th', { class: 'num', text: 'Terminal today' }), h('th', { class: 'num', text: 'Deep station' }))));
    const body = h('tbody');
    rows.forEach(function (r, i) { body.appendChild(h('tr', { class: i + 1 > st ? 'pending' : null }, h('th', { text: r[0] }), h('td', { class: 'num', text: r[1] }), h('td', { class: 'num', text: r[2] }))); });
    body.appendChild(h('tr', { class: 'total' }, h('th', { text: st < 3 ? 'So far' : 'From hall to coach' }), h('td', { class: 'num', text: f1(sum(T.today)) }), h('td', { class: 'num', text: f1(sum(T.deep)) })));
    t.appendChild(body);
    const diff = T.deep.reduce(function (x, y) { return x + y; }, 0) - T.today.reduce(function (x, y) { return x + y; }, 0), per10 = 10 * WK.esc_per_m / WK.esc_speed;
    $('#stations-walk-title').textContent = Math.abs(diff) < 0.45 ? 'Reaching a deep platform takes about as long as walking down a terminal platform'
      : 'With platforms ' + state.depth + ' m down, reaching the coach takes ' + F.n(Math.abs(diff), 1) + ' minutes ' + (diff > 0 ? 'longer' : 'less') + ' than in a terminal today';
    $('#stations-walk-note').textContent = 'With platforms ' + state.depth + ' m down, the deep station takes ' + (Math.abs(diff) < 0.05 ? 'the same time as' : F.n(Math.abs(diff), 1) + ' minutes ' + (diff > 0 ? 'more than' : 'less than')) + ' the terminal. Each 10 m of depth adds about ' + F.n(per10, 0) + ' seconds of escalator.'
      + (state.depth === WK.depth ? '' : ' The model uses ' + WK.depth + ' m.');
  }
  const check = times();                                      // the illustration must match the totals of the model
  if (Math.abs(check.today.reduce(function (a, b) { return a + b; }, 0) - D.extras.hall_today) > 0.01 || Math.abs(check.deep.reduce(function (a, b) { return a + b; }, 0) - D.extras.hall_deep) > 0.01) console.warn('stations: walking assumptions differ from the model');

  // ================================================================ controls and first drawing
  PTS.steps($('#stations-walk-steps'), [[0, '1. In the hall'], [1, '2. Through the gates'], [2, '3. Down'], [3, '4. Along the platform']], state.step, function (v) { state.step = +v; ledger(); redrawAll(); });
  PTS.slider($('#stations-walk-depth'), { label: 'Depth of the platforms', min: 15, max: 55, step: 5, value: state.depth, format: function (v) { return v + ' m'; }, note: 'The model’s illustration uses ' + WK.depth + ' m' }, function (v) { state.depth = v; ledger(); redrawAll(); });
  planReads(); ledger();
  PLANS.forEach(function (p) { mount(p[1], function (w) { return plan(w, p[0]); }, 600); });
  mount('#stations-xs-nordest', XS.nordest, 620);
  mount('#stations-xs-lyon', XS.lyon, 620);
  mount('#stations-xs-montparnasse', XS.montparnasse, 620);
  mount('#stations-walk', walk, 640);
});
