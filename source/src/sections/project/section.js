PTS.section('project', function (root) {
  'use strict';
  const D = PTS.data.model, G = PTS.data.paris_geo, P = PTS.data.project, F = PTS.fmt, h = PTS.h, s = PTS.s;
  const $ = function (sel) { return root.querySelector(sel); };
  // one twin-track tunnel for each kind of train: TGV, line N, line H (c.tunnels, as model.tunnels.corridors). The regional express trains
  // have no tunnel of their own (version 4.1): they ride in the TGV tunnel of the corridors marked c.ter (as model.ter_corridors), drawn as a thin line inside it
  const NET = { tgv: { k: 'tgv', label: 'TGV', long: 'TGV', color: 'var(--s1)', plat: 'hs' },
    n: { k: 'n', label: 'RER G', long: 'RER G', color: 'var(--s3)', plat: 'sub' },
    h: { k: 'h', label: 'RER F', long: 'RER F', color: 'var(--s4)', plat: 'sub' } };
  const NETS = [NET.tgv, NET.n, NET.h];
  const TER = { k: 'ter', label: 'Regional express', long: 'regional express', color: 'var(--s2)', plat: 'ter' };   // platforms of their own, no tunnel
  const TP = D.ter_paths, LOADS = TP.loads;
  const LEN = D.len, C = D.cost, R = D.rates, TC = D.tunnels.corridors;
  const on = function (k) { return state.layers[k]; };
  const netsOf = function (c) { return NETS.filter(function (n) { return c.tunnels.indexOf(n.k) >= 0; }); };
  const shown = function (c) { return netsOf(c).filter(function (n) { return on(n.k); }); };
  const words = function (list) { return list.length < 2 ? list.join('') : list.slice(0, -1).join(', ') + ' and ' + list[list.length - 1]; };
  const tunnelWords = function (nets) { return words(nets.map(function (n) { return n.long; })) + (nets.length === 1 ? ' tunnel' : ' tunnels'); };
  const stageOf = function (c, n) { return n.k === 'n' ? 2 : c.stage; };     // the line N tunnel is all stage 2
  // the tunnels of each corridor must be the model's
  P.corridors.forEach(function (c) { const want = Object.keys(TC).filter(function (t) { return TC[t].indexOf(c.id) >= 0; }); if (want.sort().join() !== c.tunnels.slice().sort().join()) console.warn('project: corridor ' + c.id + ' tunnels differ from the model', want, c.tunnels); });
  const terWant = (D.ter_corridors || []).slice().sort().join(), terHave = P.corridors.filter(function (c) { return c.ter; }).map(function (c) { return c.id; }).sort().join();
  if (terWant !== terHave) console.warn('project: corridors with regional express trains differ from the model', terWant, terHave);
  P.corridors.forEach(function (c) { if (c.ter && !LOADS[c.ter]) console.warn('project: no tunnel load in the model for ' + c.id); });
  P.portals.forEach(function (po) { po.tunnels = P.corridors.filter(function (c) { return c.id === po.corridor; })[0].tunnels; });
  const LAYERS = [['tgv', 'TGV tunnels'], ['ter', 'Regional express, in the TGV tunnels'], ['n', 'RER G'], ['h', 'RER F'], ['stations', 'Stations'], ['nodes', 'Portals and junctions'], ['surface', 'Today’s surface tracks']];
  // the stations stand where today's terminals are (positions from paris_geo); Paris Nord-Est lies between Gare du Nord and Gare de l'Est
  const T = G.term, mid = [(T.Nord[0] + T.Est[0]) / 2, (T.Nord[1] + T.Est[1]) / 2];
  const AT = { 'Paris Nord-Est': mid, 'Gare de Lyon': T.Lyon, 'Montparnasse': T.Montparnasse, 'Gare du Nord': T.Nord, 'Gare de l’Est': T.Est };
  P.stations.forEach(function (st) { if (AT[st.name]) st.at = AT[st.name]; });       // Saint-Lazare keeps its own position from data.json
  P.lines.forEach(function (l) { if (AT[l.name]) l.path[0] = AT[l.name]; });
  const state = { layers: { tgv: true, ter: true, n: true, h: true, stations: true, nodes: true, surface: true }, sel: { kind: 'station', id: 'Paris Nord-Est' }, width: 0 };

  // ---------------------------------------------------------------- geometry helpers
  function spline(pts, n) {                                  // Catmull-Rom through the points, n samples per span
    const out = [];
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
      for (let j = 0; j < n; j++) {
        const t = j / n, t2 = t * t, t3 = t2 * t;
        out.push([0, 1].map(function (a) { return 0.5 * (2 * p1[a] + (p2[a] - p0[a]) * t + (2 * p0[a] - 5 * p1[a] + 4 * p2[a] - p3[a]) * t2 + (3 * p1[a] - p0[a] - 3 * p2[a] + p3[a]) * t3); }));
      }
    }
    out.push(pts[pts.length - 1]);
    return out;
  }
  function offset(poly, d) {
    return poly.map(function (p, i) {
      const a = poly[Math.max(0, i - 1)], b = poly[Math.min(poly.length - 1, i + 1)], nx = a[1] - b[1], ny = b[0] - a[0], l = Math.sqrt(nx * nx + ny * ny) || 1;
      return [p[0] + nx / l * d, p[1] + ny / l * d];
    });
  }
  function dpath(poly, close) { return 'M' + poly.map(function (p) { return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join('L') + (close ? 'Z' : ''); }
  function hot(el, label, tip, pick) {                        // hover, focus and click on a mark of the drawing
    el.setAttribute('tabindex', '0'); el.setAttribute('role', 'button'); el.setAttribute('aria-label', label); el.classList.add('hot');
    PTS.tip.bind(el, tip);
    el.addEventListener('click', pick);
    el.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } });
    return el;
  }
  const isSel = function (kind, id) { return state.sel.kind === kind && state.sel.id === id; };
  const select = function (kind, id) { state.sel = { kind: kind, id: id }; drawMap(); drawPanel(); };

  // ---------------------------------------------------------------- the map
  function drawMap() {
    const host = $('#project-map'), W = state.width; if (!W) return;
    const narrow = W < 430, view = P.view[narrow ? 'narrow' : 'wide'], k = Math.cos(48.86 * Math.PI / 180);
    const sc = W / ((view.lon[1] - view.lon[0]) * k), H = Math.round((view.lat[1] - view.lat[0]) * sc);
    const pr = function (ll) { return [(ll[0] - view.lon[0]) * k * sc, (view.lat[1] - ll[1]) * sc]; };
    const line = function (pts, n) { return spline(pts.map(pr), n || 10); };
    const gap = narrow ? 3.4 : 3.8, on = state.layers, anyNet = NETS.some(function (n) { return on[n.k]; });
    const svg = s('svg', { class: 'draw', viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img',
      'aria-label': 'Schematic map of Paris with the four deep stations, the tunnel corridors of the TGV, RER G and RER F tunnels, the regional express trains running in the TGV tunnels, the direct link between Montparnasse and Gare de Lyon, the five portal sites and the four junction sites' });
    const clipId = 'project-clip-paris';
    svg.appendChild(s('defs', null, s('clipPath', { id: clipId }, s('path', { d: G.outline.map(function (r) { return dpath(r.map(pr), true); }).join('') }))));

    // existing lines, drawn first so that only the part outside Paris shows
    if (on.surface) P.lines.forEach(function (l) { svg.appendChild(s('path', { class: 'pm-kept', d: dpath(line(l.path)) })); });
    svg.appendChild(s('path', { class: 'pm-land', d: G.outline.map(function (r) { return dpath(r.map(pr), true); }).join('') }));
    G.bois.forEach(function (b) { svg.appendChild(s('path', { class: 'pm-park', d: b.r.map(function (r) { return dpath(r.map(pr), true); }).join('') })); });
    G.arr.forEach(function (a) { svg.appendChild(s('path', { class: 'pm-arr', d: a.r.map(function (r) { return dpath(r.map(pr), true); }).join('') })); });
    svg.appendChild(s('path', { class: 'pm-seine', d: dpath(line(P.seine, 6)) }));
    const sl = pr(P.seine_label); svg.appendChild(s('text', { class: 'pm-sub', x: sl[0], y: sl[1], 'text-anchor': 'middle', text: 'Seine' }));

    // surface tracks inside Paris that would no longer be needed
    if (on.surface) {
      const g = s('g', { 'clip-path': 'url(#' + clipId + ')' });
      P.lines.forEach(function (l) { const fr = l.freed || l.path; if (fr.length > 1) g.appendChild(s('path', { class: 'pm-freed', d: dpath(line(fr)) })); });
      // tracks inside Paris that stay in use: beyond a portal inside Paris (Rosa Parks), Gare de Lyon for now (open item), Saint-Lazare's surface station
      P.lines.forEach(function (l) { if (l.kept_inside) g.appendChild(s('path', { class: 'pm-kept' + (l.freed && l.freed.length ? ' few' : ''), d: dpath(line(l.kept_inside)) })); });
      svg.appendChild(g);
      P.others.forEach(function (o) {
        const p = pr(o.at), m = s('circle', { class: 'pm-other', cx: p[0], cy: p[1], r: 4 });
        PTS.tip.bind(m, '<b>' + o.name + '</b><br>' + o.tip); m.setAttribute('tabindex', '0'); m.setAttribute('role', 'img'); m.setAttribute('aria-label', o.name + ' station: ' + o.tip.charAt(0).toLowerCase() + o.tip.slice(1));
        if (o.freed) m.classList.add('freed');
        svg.appendChild(m);
        if (!narrow) svg.appendChild(s('text', { class: 'pm-sub', x: p[0] + o.lbl[0], y: p[1] + o.lbl[1], 'text-anchor': o.lbl[2], text: o.name }));
      });
    }

    // tunnels: one line for each twin-track tunnel, side by side, only those of the layers switched on
    if (anyNet) {
      const band = function (poly, g, nets, ter) { nets.forEach(function (n, i) {
        const d = dpath(offset(poly, (i - (nets.length - 1) / 2) * gap));
        g.appendChild(s('path', { class: 'pm-net', d: d, stroke: n.color }));
        if (n.k === 'tgv' && ter && on.ter) g.appendChild(s('path', { class: 'pm-ter', d: d, stroke: TER.color }));      // regional express trains inside the TGV tunnel
      }); };
      const trunks = s('g'); P.trunks.forEach(function (t) { band(line(t.path, 8), trunks, shown(t), true); }); svg.appendChild(trunks);
      P.corridors.forEach(function (c) {
        const nets = shown(c); if (!nets.length) return;
        const poly = line(c.path, 12), g = s('g', { class: isSel('corridor', c.id) ? 'sel' : null }), all = netsOf(c);
        g.appendChild(s('path', { class: 'pm-halo', d: dpath(poly) }));
        band(poly, g, nets, !!c.ter);
        g.appendChild(s('path', { class: 'pm-hit', d: dpath(poly) }));
        hot(g, 'Corridor ' + c.name + ', ' + F.n(c.km, 1) + ' km', '<b>' + c.name + (c.id === 'link' ? '' : ' corridor') + '</b><br>' + c.from + ' to ' + c.to + '<br>' + F.n(c.km, 1) + ' km of route: ' + 'the ' + tunnelWords(all) + (all.length > 1 ? ', side by side' : '') + (c.ter ? '<br>Regional express trains share the TGV tunnel: ' + loadWords(c.ter) : '') + '<br><small>Select for details</small>', function () { select('corridor', c.id); });
        svg.appendChild(g);
        if (!narrow) { const mid = poly[Math.round(poly.length / 2)]; svg.appendChild(s('text', { class: 'pm-sub', x: mid[0] + c.lbl[0], y: mid[1] + c.lbl[1], 'text-anchor': c.lbl[2], text: F.n(c.km, 1) + ' km' })); }
      });
    }

    // junctions and portals
    if (on.nodes) {
      P.junctions.forEach(function (j) {
        const p = pr(j.at), r = 6.5, g = s('g', { class: isSel('junction', j.id) ? 'sel' : null }, s('path', { class: 'pm-node', d: 'M' + p[0] + ',' + (p[1] - r) + 'L' + (p[0] + r) + ',' + p[1] + 'L' + p[0] + ',' + (p[1] + r) + 'L' + (p[0] - r) + ',' + p[1] + 'Z' }));
        hot(g, j.name, '<b>' + j.name + '</b><br>' + j.what + '<br>' + j.tunnels.length + (j.tunnels.length === 1 ? ' cavern: ' : ' caverns: ') + words(j.tunnels.map(function (k) { return NET[k].long; })), function () { select('junction', j.id); });
        svg.appendChild(g);
      });
      P.portals.forEach(function (o) {
        const p = pr(o.at), r = 7, g = s('g', { class: isSel('portal', o.name) ? 'sel' : null }, s('path', { class: 'pm-node', d: 'M' + p[0] + ',' + (p[1] - r) + 'L' + (p[0] + r) + ',' + (p[1] + r * 0.8) + 'L' + (p[0] - r) + ',' + (p[1] + r * 0.8) + 'Z' }));
        hot(g, (o.tunnels.length === 1 ? 'Portal at ' : 'Portals at ') + o.name, '<b>' + (o.tunnels.length === 1 ? 'Portal at ' : 'Portals at ') + o.name + '</b><br>Where the ' + tunnelWords(o.tunnels.map(function (k) { return NET[k]; })) + ' come' + (o.tunnels.length === 1 ? 's' : '') + ' up to join ' + o.line + '.' + (o.ter ? '<br>' + o.ter : ''), function () { select('portal', o.name); });
        svg.appendChild(g);
        svg.appendChild(s('text', { class: 'pm-sub out', x: p[0] + o.lbl[0], y: p[1] + o.lbl[1], 'text-anchor': o.lbl[2], text: o.name }));
      });
    }

    // the four deep stations
    if (on.stations) P.stations.forEach(function (st) {
      const p = pr(st.at), a = pr(st.axis[0]), b = pr(st.axis[1]), ang = Math.atan2(b[1] - a[1], b[0] - a[0]) * 180 / Math.PI, bw = narrow ? 26 : 30, bh = narrow ? 13 : 15;
      const g = s('g', { class: isSel('station', st.name) ? 'sel' : null },
        s('rect', { class: 'pm-station', x: p[0] - bw / 2, y: p[1] - bh / 2, width: bw, height: bh, rx: 3, transform: 'rotate(' + ang.toFixed(1) + ' ' + p[0].toFixed(1) + ' ' + p[1].toFixed(1) + ')' }));
      hot(g, 'Station ' + st.name, '<b>' + st.name + '</b><br>' + C.tracks[st.name] + ' platform tracks: ' + trackWords(st.name) + '<br><small>Select for details</small>', function () { select('station', st.name); });
      svg.appendChild(g);
      svg.appendChild(s('text', { class: 'pm-lbl', x: p[0] + st.lbl[0], y: p[1] + st.lbl[1], 'text-anchor': st.lbl[2], text: st.name }));
      if (!narrow && st.under) svg.appendChild(s('text', { class: 'pm-sub', x: p[0] + st.lbl[0], y: p[1] + st.lbl[1] + 14, 'text-anchor': st.lbl[2], text: st.under }));
    });

    const focus = document.activeElement && host.contains(document.activeElement) ? document.activeElement.getAttribute('aria-label') : null;
    PTS.clear(host).appendChild(svg);
    if (focus) { const again = PTS.$$('[aria-label]', svg).filter(function (e) { const l = e.getAttribute('aria-label'); return l === focus || PTS.tr(l) === focus; })[0]; if (again) again.focus(); }
  }

  // ---------------------------------------------------------------- the side panel
  function rows(dl, list) {
    list.forEach(function (r) {
      if (r.length === 1) { dl.appendChild(h('dt', { class: 'grp', text: r[0] })); return; }
      dl.appendChild(h('dt', { class: r[2] || null, text: r[0] })); dl.appendChild(h('dd', { class: r[2] || null, text: r[1] }));
    });
    return dl;
  }
  function tracksOf(name) {                                   // platform tracks of a station by type of train: TGV, regional express, line N, line H
    const det = C.detail[name], sub = D.sub_tracks[name] || {};
    return { tgv: det.hs, ter: det.ter, n: sub.n || 0, h: sub.h || 0 };
  }
  const PLATS = [NET.tgv, TER, NET.n, NET.h];                 // kinds of platform track: the regional express trains have their own, but no tunnel
  function loadWords(key) {                                   // trains an hour each way in a TGV tunnel at the peak, and the share of its paths they take
    const l = LOADS[key];
    return F.n(l.tgv, 0) + ' TGVs and ' + F.n(l.ter, 0) + ' regional express trains an hour each way, ' + F.pct(l.occ_15) + ' of the tunnel’s capacity with trains ' + F.n(TP.signal_min[0], 1) + ' minutes apart (' + F.pct(l.occ_20) + ' at ' + F.n(TP.signal_min[1], 0) + ' minutes)';
  }
  function trackWords(name) {
    const t = tracksOf(name);
    return words(PLATS.filter(function (n) { return t[n.k]; }).map(function (n) { return t[n.k] + ' ' + n.long; }));
  }
  function strip(st) {                                        // one line for each platform track, to scale in length
    const tr = tracksOf(st.name), W = 240, step = 5, list = [];
    PLATS.forEach(function (n) { for (let i = 0; i < tr[n.k]; i++) list.push({ k: n.plat, color: n.color, london: n.k === 'tgv' && i < (st.london || 0) }); });
    const svg = s('svg', { class: 'project-strip', viewBox: '0 0 ' + W + ' ' + (list.length * step + 2), role: 'img', 'aria-label': list.length + ' platform tracks drawn as lines, ' + LEN.hs + ', ' + LEN.ter + ' or ' + LEN.sub + ' m long' });
    list.forEach(function (t, i) {
      const len = LEN[t.k] / LEN.hs * W, x0 = (W - len) / 2;
      svg.appendChild(s('line', { x1: x0, x2: x0 + len, y1: i * step + 2.5, y2: i * step + 2.5, stroke: t.color, 'stroke-width': 2, 'stroke-dasharray': t.london ? '7 3' : null }));
    });
    return svg;
  }
  function drawPanel() {
    const box = PTS.clear($('#project-panel')), sel = state.sel;
    if (sel.kind === 'station') {
      const st = P.stations.filter(function (x) { return x.name === sel.id; })[0], tr = tracksOf(st.name);
      const list = [['Platform tracks']];
      PLATS.forEach(function (n) { if (tr[n.k]) list.push([n.label + ', ' + LEN[n.plat] + ' m' + (n.k === 'tgv' && st.london ? ' (' + st.london + ' can be closed off for London departures)' : '') + (n.k === 'tgv' && st.tgv_note ? ' (' + st.tgv_note + ')' : ''), tr[n.k]]); });
      list.push(['All platform tracks', C.tracks[st.name], 'sum'], ['Platform track, metres', F.n(C.platform_m[st.name], 0)]);
      list.push(
        ['Cost'], ['Works at €' + F.n(R.platform_m * 1000, 1) + 'm per metre', F.bn(C.station_cost[st.name])], ['With design, land and 15% risk', F.bn(D.station_total[st.name])]);
      box.appendChild(h('h4', { text: 'Station, stage ' + st.stage }));
      box.appendChild(h('h3', { text: st.name }));
      box.appendChild(h('p', { text: st.where }));
      box.appendChild(strip(st));
      box.appendChild(rows(h('dl', { class: 'read' }), list));
      box.appendChild(h('p', { class: 'note', text: st.calls + (st.name === 'Saint-Lazare' ? ' The ride from Nord-Est takes ' + F.n(D.TR.SL, 0) + ' minutes.' : '') + ' ' + st.surface + (st.stage_note ? ' ' + st.stage_note : '') }));
    } else if (sel.kind === 'corridor') {
      const co = P.corridors.filter(function (x) { return x.id === sel.id; })[0], nets = netsOf(co), count = nets.length, km = co.km * count, works = km * (R.tunnel_civil + R.tunnel_systems);
      const stages = nets.map(function (n) { return stageOf(co, n); }).filter(function (v, i, a) { return a.indexOf(v) === i; }).sort();
      box.appendChild(h('h4', { text: (co.id === 'link' ? 'Direct link' : 'Corridor') + ', stage' + (stages.length > 1 ? 's ' : ' ') + stages.join(' and ') }));
      box.appendChild(h('h3', { text: co.name }));
      box.appendChild(h('p', { text: co.from + ' to ' + co.to + '.' }));
      box.appendChild(rows(h('dl', { class: 'read' }), [['Length'], ['Route, planning estimate', F.n(co.km, 1) + ' km'], ['Tunnels side by side', count], ['Two-track tunnel', F.n(km, 1) + ' km', 'sum'],
        ['Cost'], ['Tunnels and rail systems, works', F.bn(works)], ['With design, land and 15% risk', F.bn(works * D.gross_up)]]));
      const ul = h('ul', { class: 'project-carries' });
      const lc = function (t) { return /^.[a-z]/.test(t) ? t.charAt(0).toLowerCase() + t.slice(1) : t; };
      nets.forEach(function (n) {
        ul.appendChild(h('li', null, h('i', { style: { '--c': n.color } }), n.label + ' tunnel: ' + lc(co.carries[n.k]) + (stages.length > 1 ? ' (stage ' + stageOf(co, n) + ')' : '')));
        if (n.k === 'tgv' && co.ter) ul.appendChild(h('li', { class: 'project-in' }, h('i', { style: { '--c': TER.color } }), 'In the same TGV tunnel: ' + lc(co.carries.ter)));
      });
      box.appendChild(h('h4', { text: count === 1 ? 'One tunnel, for' : count + ' tunnels side by side' }));
      box.appendChild(ul);
      if (co.ter) box.appendChild(h('p', { class: 'note', text: 'At the peak: ' + loadWords(co.ter) + '. Planners keep the peak under ' + F.pct(TP.uic_peak) + '.' }));
      if (co.note) box.appendChild(h('p', { class: 'note', text: co.note }));
      if (co.id === 'link') box.appendChild(h('p', { class: 'note', text: 'The link leaves each station at its city end, so that a train from the Atlantic enters Gare de Lyon facing the south-east. Its length is taken as ' + F.n(co.km, 0) + ' km (4.5 to 6 km); its geometry is a study point.' }));
    } else if (sel.kind === 'portal') {
      const po = P.portals.filter(function (x) { return x.name === sel.id; })[0];
      const pn = po.tunnels.map(function (k) { return NET[k]; });
      box.appendChild(h('h4', { text: pn.length === 1 ? 'Portal' : 'Portals' }));
      box.appendChild(h('h3', { text: po.name }));
      box.appendChild(h('p', { text: 'Where the ' + tunnelWords(pn) + ' come' + (pn.length === 1 ? 's' : '') + ' up on the existing tracks to join ' + po.line + '. The place is a planning assumption.' + (po.ter ? ' ' + po.ter : '') }));
      const ul = h('ul', { class: 'project-carries' });
      pn.forEach(function (n) { ul.appendChild(h('li', null, h('i', { style: { '--c': n.color } }), n.label)); });
      box.appendChild(ul);
      box.appendChild(rows(h('dl', { class: 'read' }), [['Portals here, one for each tunnel', pn.length], ['Portals in all', C.portals], ['Price used for each, works', F.m(R.portal)]]));
      box.appendChild(h('p', { class: 'note', text: 'The price is an assumption: no built project publishes the cost of a portal and its link to the existing line.' }));
    } else {
      const j = P.junctions.filter(function (x) { return x.id === sel.id; })[0];
      box.appendChild(h('h4', { text: 'Underground junction' }));
      box.appendChild(h('h3', { text: j.name }));
      box.appendChild(h('p', { text: j.what + ' Each tunnel that splits needs its own cavern.' }));
      const ul = h('ul', { class: 'project-carries' });
      j.tunnels.forEach(function (k) { ul.appendChild(h('li', null, h('i', { style: { '--c': NET[k].color } }), NET[k].label + ' tunnel')); });
      box.appendChild(ul);
      box.appendChild(rows(h('dl', { class: 'read' }), [['Caverns here, one for each tunnel', j.tunnels.length], ['Junction caverns in all', C.junctions], ['Price used for each, works', F.m(R.junction)]]));
      box.appendChild(h('p', { class: 'note', text: 'The price is an assumption: no project publishes the cost of a junction cavern.' }));
    }
  }

  // ---------------------------------------------------------------- legend
  function sample(kind, color) {
    const g = s('svg', { viewBox: '0 0 24 12', width: 24, height: 12, 'aria-hidden': 'true', class: 'draw' });
    if (kind === 'net') g.appendChild(s('line', { x1: 1, x2: 23, y1: 6, y2: 6, stroke: color, 'stroke-width': 2.6 }));
    if (kind === 'ter') { g.appendChild(s('line', { x1: 1, x2: 23, y1: 6, y2: 6, stroke: NET.tgv.color, 'stroke-width': 2.6 })); g.appendChild(s('line', { class: 'pm-ter', x1: 1, x2: 23, y1: 6, y2: 6, stroke: color })); }
    if (kind === 'freed') g.appendChild(s('line', { class: 'pm-freed', x1: 2, x2: 23, y1: 6, y2: 6 }));
    if (kind === 'kept') g.appendChild(s('line', { class: 'pm-kept', x1: 1, x2: 23, y1: 6, y2: 6 }));
    if (kind === 'few') g.appendChild(s('line', { class: 'pm-kept few', x1: 1, x2: 23, y1: 6, y2: 6 }));
    if (kind === 'station') g.appendChild(s('rect', { class: 'pm-station', x: 3, y: 1.5, width: 18, height: 9, rx: 2 }));
    if (kind === 'portal') g.appendChild(s('path', { class: 'pm-node', d: 'M12,1L18,11L6,11Z' }));
    if (kind === 'junction') g.appendChild(s('path', { class: 'pm-node', d: 'M12,1L17,6L12,11L7,6Z' }));
    if (kind === 'other') g.appendChild(s('circle', { class: 'pm-other', cx: 12, cy: 6, r: 4 }));
    return g;
  }
  function drawLegend() {
    const ul = PTS.clear($('#project-legend')), on = state.layers;
    const add = function (kind, text, color) { ul.appendChild(h('li', null, sample(kind, color), text)); };
    const legendText = { tgv: 'TGV tunnel (two tracks)', n: 'RER G tunnel (today’s lines P and N)', h: 'RER F tunnel (today’s lines H, K and L)' };
    NETS.forEach(function (n) { if (on[n.k]) add('net', legendText[n.k], n.color); });
    if (on.ter && on.tgv) add('ter', 'TGV tunnel also used by regional express trains', TER.color);
    if (on.stations) add('station', 'Deep through station');
    if (on.nodes) { add('portal', 'Portals'); add('junction', 'Underground junction'); }
    if (on.surface) { add('freed', 'Surface tracks no longer needed: parks'); add('kept', 'Surface tracks kept in use'); add('few', 'A few tracks kept, for line R'); add('other', 'Other terminals: Austerlitz left as it is, Bercy freed'); }
  }

  // ---------------------------------------------------------------- controls
  const controls = $('#project-controls');
  const pills = h('div', { class: 'steps', role: 'group', 'aria-label': 'Layers shown on the map' });
  LAYERS.forEach(function (l) {
    const b = h('button', { type: 'button', 'aria-pressed': 'true', text: l[1] });
    b.addEventListener('click', function () { state.layers[l[0]] = !state.layers[l[0]]; b.setAttribute('aria-pressed', String(state.layers[l[0]])); drawMap(); drawLegend(); });
    pills.appendChild(b);
  });
  controls.appendChild(h('div', { class: 'field' }, h('span', { text: 'Layers' }), pills));

  PTS.onResize($('#project-map'), function (w) { state.width = Math.min(w, 640); drawMap(); });
  drawPanel(); drawLegend();
});
