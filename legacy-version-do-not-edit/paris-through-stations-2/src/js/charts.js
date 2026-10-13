/* Chart helpers. Bars and stacks are plain HTML (they reflow by themselves); line and range charts are SVG drawn at the
   real pixel width and redrawn when the width changes. Colours are CSS variables, so both themes work without redrawing.
   Rules followed here (see CONTRIBUTING.md): one axis, thin marks, a legend for two or more series, hover on every mark,
   text in text colours and never in series colours. */
(function () {
  'use strict';
  const PTS = window.PTS, h = PTS.h, s = PTS.s, F = PTS.fmt;
  const C = PTS.chart = {};
  C.colors = ['var(--s1)', 'var(--s2)', 'var(--s3)', 'var(--s4)', 'var(--s5)', 'var(--s6)', 'var(--s7)', 'var(--s8)'];

  /* Horizontal bars.
     cfg: {rows: [{label, value, color, lo, hi, mark, hl, tip, text, group, sep}], fmt, max, min, compact}
     compact: true puts each label on its own line (for narrow cards).
     lo/hi draw a range line over the bar; mark draws a tick; text overrides the printed value. */
  C.bars = function (host, cfg) {
    PTS.clear(host);
    const rows = cfg.rows.filter(function (r) { return !r.group && !r.sep; });
    const fmt = cfg.fmt || function (v) { return F.n(v, 1); };
    const hiV = Math.max.apply(null, rows.map(function (r) { return Math.max(r.value || 0, r.hi || 0, r.mark || 0); }).concat([cfg.max || 0, 0]));
    const loV = Math.min.apply(null, rows.map(function (r) { return Math.min(r.value || 0, r.lo || 0); }).concat([cfg.min || 0, 0]));
    const span = (hiV - loV) || 1, pos = function (v) { return (v - loV) / span * 100; };
    const box = h('div', { class: 'bars' + (cfg.compact ? ' compact' : '') });
    cfg.rows.forEach(function (r) {
      if (r.group) { box.appendChild(h('div', { class: 'grp', text: r.group })); return; }
      if (r.sep) { box.appendChild(h('div', { class: 'sep' })); return; }
      const v = r.value || 0, a = pos(Math.min(0, v)), b = pos(Math.max(0, v));
      const track = h('div', { class: 'track' },
        h('div', { class: 'bar' + (v < 0 ? ' neg' : ''), style: { left: a + '%', width: Math.max(0, b - a) + '%', '--c': r.color || 'var(--s1)' } }),
        loV < 0 ? h('div', { class: 'zero', style: { left: pos(0) + '%' } }) : null,
        r.lo != null && r.hi != null ? h('div', { class: 'rng', style: { left: pos(r.lo) + '%', width: (pos(r.hi) - pos(r.lo)) + '%' } }) : null,
        r.mark != null ? h('div', { class: 'mark', style: { left: pos(r.mark) + '%' } }) : null);
      const tip = r.tip || ('<b>' + r.label + '</b><br>' + (r.text || fmt(v)) + (r.lo != null && r.hi != null ? '<br><small>range ' + fmt(r.lo) + ' to ' + fmt(r.hi) + '</small>' : ''));
      PTS.tip.bind(track, tip); track.tabIndex = 0;
      const wrap = r.hl ? 'row-hl' : null;
      const lab = h('div', { class: 'lab', html: r.label }), val = h('div', { class: 'val', text: r.text || fmt(v) });
      if (wrap) { [lab, track, val].forEach(function (e) { e.classList.add('hl'); }); lab.style.fontWeight = 600; lab.style.color = 'var(--ink)'; }
      box.appendChild(lab); box.appendChild(track); box.appendChild(val);
    });
    host.appendChild(box);
    return box;
  };

  /* Stacked horizontal bars on one shared scale.
     cfg: {rows: [{label, parts: [{label, value, color}], text}], fmt, max, legend: [{label, color}] or true} */
  C.stack = function (host, cfg) {
    PTS.clear(host);
    const outer = host; host = h('div', { class: 'stack' }); outer.appendChild(host);
    const fmt = cfg.fmt || function (v) { return F.n(v, 2); };
    const totals = cfg.rows.map(function (r) { return r.parts.reduce(function (a, p) { return a + Math.max(0, p.value); }, 0); });
    const max = cfg.max || Math.max.apply(null, totals) || 1;
    const seen = {}, leg = [];
    cfg.rows.forEach(function (r, i) {
      const bar = h('div', { class: 'stackbar', style: { width: (totals[i] / max * 100) + '%' } });
      r.parts.forEach(function (p) {
        if (!(p.value > 0)) return;
        const seg = h('i', { style: { '--c': p.color, flex: p.value + ' 0 0' }, tabindex: 0 });
        PTS.tip.bind(seg, '<b>' + p.label + '</b><br>' + fmt(p.value) + (totals[i] ? ' <small>(' + F.pct(p.value / totals[i]) + ' of this bar)</small>' : ''));
        bar.appendChild(seg);
        if (!seen[p.label]) { seen[p.label] = 1; leg.push(p); }
      });
      host.appendChild(h('div', { class: 'stackrow' }, h('div', { class: 'lab', html: r.label }), h('div', { style: { 'min-width': 0 } }, bar), h('div', { class: 'val', text: r.text || fmt(totals[i]) })));
    });
    if (cfg.legend !== false) host.appendChild(h('ul', { class: 'legend' }, (Array.isArray(cfg.legend) ? cfg.legend : leg).map(function (p) { return h('li', null, h('i', { style: { '--c': p.color } }), p.label); })));
  };

  function ticks(lo, hi, count) {
    const span = hi - lo, step0 = Math.pow(10, Math.floor(Math.log10(span / count))), err = span / count / step0;
    const step = step0 * (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1), out = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-6; v += step) out.push(Math.round(v / step) * step);
    return out;
  }
  C.ticks = ticks;

  /* Line chart with a crosshair read-out.
     cfg: {series: [{name, color, points: [[x, y], ...], dash}], x: {label, fmt, min, max}, y: {label, fmt, min, max}, height,
           vlines: [{x, label}], hlines: [{y, label}], onHover(x)} */
  C.line = function (host, cfg) {
    PTS.clear(host);
    const wrap = h('div', { style: { position: 'relative' } }); host.appendChild(wrap);
    const fx = (cfg.x && cfg.x.fmt) || function (v) { return F.n(v, 1); }, fy = (cfg.y && cfg.y.fmt) || function (v) { return F.n(v, 1); };
    const all = [].concat.apply([], cfg.series.map(function (q) { return q.points; }));
    const x0 = cfg.x && cfg.x.min != null ? cfg.x.min : Math.min.apply(null, all.map(function (p) { return p[0]; }));
    const x1 = cfg.x && cfg.x.max != null ? cfg.x.max : Math.max.apply(null, all.map(function (p) { return p[0]; }));
    let y0 = cfg.y && cfg.y.min != null ? cfg.y.min : Math.min.apply(null, all.map(function (p) { return p[1]; }).concat([0]));
    let y1 = cfg.y && cfg.y.max != null ? cfg.y.max : Math.max.apply(null, all.map(function (p) { return p[1]; }));
    if (y1 === y0) y1 = y0 + 1;
    const H = cfg.height || 260, m = { l: 52, r: 16, t: 14, b: 40 };
    PTS.onResize(wrap, function (W) {
      PTS.clear(wrap);
      const iw = W - m.l - m.r, ih = H - m.t - m.b;
      const X = function (v) { return m.l + (v - x0) / (x1 - x0) * iw; }, Y = function (v) { return m.t + ih - (v - y0) / (y1 - y0) * ih; };
      const svg = s('svg', { width: W, height: H, viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': cfg.label || 'Line chart' });
      const g = s('g', { class: 'grid' }), ax = s('g', { class: 'axis' });
      ticks(y0, y1, 5).forEach(function (t) { g.appendChild(s('line', { x1: m.l, x2: W - m.r, y1: Y(t), y2: Y(t) })); ax.appendChild(s('text', { x: m.l - 8, y: Y(t) + 4, 'text-anchor': 'end', text: fy(t) })); });
      ticks(x0, x1, Math.max(3, Math.floor(iw / 90))).forEach(function (t) { ax.appendChild(s('text', { x: X(t), y: H - m.b + 18, 'text-anchor': 'middle', text: fx(t) })); });
      if (cfg.x && cfg.x.label) ax.appendChild(s('text', { x: m.l + iw / 2, y: H - 4, 'text-anchor': 'middle', text: cfg.x.label }));
      if (y0 < 0) ax.appendChild(s('line', { x1: m.l, x2: W - m.r, y1: Y(0), y2: Y(0), style: 'stroke: var(--muted)' }));
      svg.appendChild(g); svg.appendChild(ax);
      (cfg.hlines || []).forEach(function (l) { svg.appendChild(s('line', { x1: m.l, x2: W - m.r, y1: Y(l.y), y2: Y(l.y), style: 'stroke: var(--ink); stroke-dasharray: 5 4; stroke-width: 1' })); svg.appendChild(s('text', { x: W - m.r, y: Y(l.y) - 5, 'text-anchor': 'end', style: 'fill: var(--ink); font-size: 12px', text: l.label })); });
      (cfg.vlines || []).forEach(function (l) { svg.appendChild(s('line', { x1: X(l.x), x2: X(l.x), y1: m.t, y2: m.t + ih, style: 'stroke: var(--ink); stroke-dasharray: 5 4; stroke-width: 1' })); svg.appendChild(s('text', { x: X(l.x) + 5, y: m.t + 11, style: 'fill: var(--ink); font-size: 12px', text: l.label })); });
      cfg.series.forEach(function (q, i) {
        const d = q.points.map(function (p, k) { return (k ? 'L' : 'M') + X(p[0]).toFixed(1) + ' ' + Y(p[1]).toFixed(1); }).join(' ');
        svg.appendChild(s('path', { d: d, fill: 'none', style: 'stroke: ' + (q.color || C.colors[i]) + '; stroke-width: 2' + (q.dash ? '; stroke-dasharray: 6 4' : '') }));
      });
      const cross = s('line', { y1: m.t, y2: m.t + ih, style: 'stroke: var(--muted); stroke-width: 1', visibility: 'hidden' }); svg.appendChild(cross);
      const dots = cfg.series.map(function (q, i) { const c = s('circle', { r: 4.5, style: 'fill: ' + (q.color || C.colors[i]) + '; stroke: var(--surface); stroke-width: 2', visibility: 'hidden' }); svg.appendChild(c); return c; });
      const hit = s('rect', { x: m.l, y: m.t, width: iw, height: ih, fill: 'transparent' }); svg.appendChild(hit);
      const move = function (e) {
        const r = svg.getBoundingClientRect(), xv = x0 + (e.clientX - r.left - m.l) / iw * (x1 - x0);
        let html = '', xs = null;
        cfg.series.forEach(function (q, i) {
          let best = q.points[0]; q.points.forEach(function (p) { if (Math.abs(p[0] - xv) < Math.abs(best[0] - xv)) best = p; });
          xs = best[0]; dots[i].setAttribute('cx', X(best[0])); dots[i].setAttribute('cy', Y(best[1])); dots[i].setAttribute('visibility', 'visible');
          html += '<br><span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:' + (q.color || C.colors[i]) + ';margin-right:6px"></span>' + q.name + ': <b>' + fy(best[1]) + '</b>';
        });
        cross.setAttribute('x1', X(xs)); cross.setAttribute('x2', X(xs)); cross.setAttribute('visibility', 'visible');
        PTS.tip.show('<b>' + ((cfg.x && cfg.x.tipLabel) ? cfg.x.tipLabel(xs) : fx(xs)) + '</b>' + html, e);
        if (cfg.onHover) cfg.onHover(xs);
      };
      hit.addEventListener('pointermove', move); hit.addEventListener('pointerdown', move);
      hit.addEventListener('pointerleave', function () { PTS.tip.hide(); cross.setAttribute('visibility', 'hidden'); dots.forEach(function (c) { c.setAttribute('visibility', 'hidden'); }); });
      wrap.appendChild(svg);
    });
    if (cfg.series.length > 1) host.appendChild(h('ul', { class: 'legend' }, cfg.series.map(function (q, i) { return h('li', null, h('i', { style: { '--c': q.color || C.colors[i] } }), q.name); })));
  };

  /* Range and dot chart: one row per item, marks of several kinds on one shared scale.
     cfg: {rows: [{label, sub, hl, lo, hi, marks: [{value, kind, tip}], note}], domain: [min, max], fmt,
           kinds: {key: {label, color, shape: 'dot' | 'ring' | 'diamond'}}, refs: [{value, label}], axisLabel} */
  C.ranges = function (host, cfg) {
    PTS.clear(host);
    const wrap = h('div'); host.appendChild(wrap);
    const fmt = cfg.fmt || function (v) { return F.n(v, 1); }, d0 = cfg.domain[0], d1 = cfg.domain[1], rowH = cfg.rowH || 30;
    PTS.onResize(wrap, function (W) {
      PTS.clear(wrap);
      const narrow = W < 560, labW = narrow ? 0 : Math.min(cfg.labelWidth || 300, W * 0.42), m = { l: labW + 10, r: 18, t: 30, b: 34 };
      const lineH = narrow ? rowH + 18 : rowH, H = m.t + cfg.rows.length * lineH + m.b, iw = W - m.l - m.r;
      const X = function (v) { return m.l + (Math.max(d0, Math.min(d1, v)) - d0) / (d1 - d0) * iw; };
      const svg = s('svg', { width: W, height: H, viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': cfg.label || 'Comparison chart' });
      const ax = s('g', { class: 'axis' }), grid = s('g', { class: 'grid' });
      ticks(d0, d1, Math.max(3, Math.floor(iw / 80))).forEach(function (t) { grid.appendChild(s('line', { x1: X(t), x2: X(t), y1: m.t - 6, y2: H - m.b })); ax.appendChild(s('text', { x: X(t), y: H - m.b + 16, 'text-anchor': 'middle', text: fmt(t) })); });
      if (cfg.axisLabel) ax.appendChild(s('text', { x: m.l + iw / 2, y: H - 2, 'text-anchor': 'middle', text: cfg.axisLabel }));
      svg.appendChild(grid); svg.appendChild(ax);
      (cfg.refs || []).forEach(function (r) {
        if (narrow) cfg.rows.forEach(function (row, i) { const top = m.t + i * lineH + 20; svg.appendChild(s('line', { x1: X(r.value), x2: X(r.value), y1: top, y2: top + rowH - 4, style: 'stroke: var(--ink); stroke-width: 1.2' })); });
        else svg.appendChild(s('line', { x1: X(r.value), x2: X(r.value), y1: m.t - 8, y2: H - m.b, style: 'stroke: var(--ink); stroke-width: 1.2' }));
        const right = X(r.value) > W * 0.6;
        svg.appendChild(s('text', { x: X(r.value) + (right ? -5 : 5), y: m.t - 12, 'text-anchor': right ? 'end' : 'start', style: 'fill: var(--ink); font-size: 12px; font-weight: 600', text: r.label }));
      });
      cfg.rows.forEach(function (r, i) {
        const top = m.t + i * lineH, cy = top + (narrow ? 18 + rowH / 2 : rowH / 2);
        if (r.hl) svg.appendChild(s('rect', { x: 0, y: top + 1, width: W, height: lineH - 2, rx: 4, style: 'fill: var(--accent-soft)' }));
        const lab = s('text', { x: narrow ? 4 : labW, y: narrow ? top + 15 : cy + 4, 'text-anchor': narrow ? 'start' : 'end', style: 'fill: var(--ink); font-size: 13px' + (r.hl ? '; font-weight: 600' : ''), text: r.label });
        if (r.sub) lab.appendChild(s('tspan', { style: 'fill: var(--muted); font-weight: 400', text: '  ' + r.sub }));
        svg.appendChild(lab);
        if (r.lo != null && r.hi != null) svg.appendChild(s('line', { x1: X(r.lo), x2: X(r.hi), y1: cy, y2: cy, style: 'stroke: var(--neutral-mark); stroke-width: 6; stroke-linecap: round; opacity: .55' }));
        (r.marks || []).forEach(function (k) {
          const kind = cfg.kinds[k.kind] || {}, x = X(k.value), col = kind.color || 'var(--s1)';
          let el;
          if (kind.shape === 'diamond') el = s('rect', { x: x - 5.5, y: cy - 5.5, width: 11, height: 11, transform: 'rotate(45 ' + x + ' ' + cy + ')', style: 'fill: ' + col + '; stroke: var(--surface); stroke-width: 1.5' });
          else if (kind.shape === 'ring') el = s('circle', { cx: x, cy: cy, r: 5.5, style: 'fill: var(--surface); stroke: ' + col + '; stroke-width: 2.6' });
          else el = s('circle', { cx: x, cy: cy, r: 6.5, style: 'fill: ' + col + '; stroke: var(--surface); stroke-width: 1.5' });
          el.setAttribute('tabindex', 0);
          PTS.tip.bind(el, k.tip || ('<b>' + r.label + '</b><br>' + (kind.label || '') + ': <b>' + fmt(k.value) + '</b>' + (k.note ? '<br><small>' + k.note + '</small>' : '')));
          svg.appendChild(el);
          if (k.over) svg.appendChild(s('text', { x: x + 10, y: cy + 4, style: 'fill: var(--muted); font-size: 12px', text: k.over }));
        });
        if (r.note) svg.appendChild(s('text', { x: W - m.r, y: narrow ? top + 15 : cy + 4, 'text-anchor': 'end', style: 'fill: var(--muted); font-size: 12px', text: r.note }));
      });
      wrap.appendChild(svg);
    });
    const keys = Object.keys(cfg.kinds);
    host.appendChild(h('ul', { class: 'legend' }, keys.map(function (k) {
      const kind = cfg.kinds[k], st = kind.shape === 'ring' ? { '--c': 'var(--surface)', border: '2.5px solid ' + kind.color, 'border-radius': '50%' } : kind.shape === 'diamond' ? { '--c': kind.color, transform: 'rotate(45deg) scale(.85)', 'border-radius': '1px' } : { '--c': kind.color, 'border-radius': '50%' };
      return h('li', null, h('i', { style: st }), kind.label);
    }).concat(cfg.rangeLabel ? [h('li', null, h('i', { style: { '--c': 'var(--neutral-mark)', height: '6px', width: '22px', opacity: .55 } }), cfg.rangeLabel)] : [])));
  };
})();
