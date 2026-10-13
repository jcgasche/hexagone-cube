PTS.section('why', function (root) {
  'use strict';
  const D = PTS.data.model, own = PTS.data.why, F = PTS.fmt, h = PTS.h;
  const $ = function (sel) { return root.querySelector(sel); };
  const mins = function (v) { return F.n(v, v % 1 ? 1 : 0); };
  const cap = function (t) { return t.charAt(0).toUpperCase() + t.slice(1); };

  // ---- one platform track, one hour. The rule is the one the model uses for its own stations (model/nordest.py, section 4):
  //      after each train the track needs clearMin minutes, and a timetable uses at most util of the hour,
  //      so a track takes 60 * util / (standing + clearMin) trains an hour.
  const stopMin = D.stop_min, clearMin = D.clear_min, util = D.util;
  const cases = own.platform_cases.map(function (c) {
    return Object.assign({}, c, { min: c.from === 'model_stop' ? stopMin : c.min, note: c.note.replace('{stop}', mins(stopMin)) });
  });
  const hour = $('#why-plat-hour');
  let pills = null, slider = null;
  const drawHour = function (min, c) {
    const n = 60 * util / (min + clearMin), slot = 60 / n;
    PTS.clear(hour);
    for (let k = 0; k * slot + (slot - min) / 2 < 60; k++) {
      const a = k * slot + (slot - min) / 2, b = Math.min(60, a + min);
      hour.appendChild(h('i', { style: { left: (a / 60 * 100) + '%', width: ((b - a) / 60 * 100) + '%' } }));
    }
    $('#why-plat-n').textContent = F.n(n, Math.abs(n - Math.round(n)) < 0.05 ? 0 : 1) + (Math.abs(n - 1) < 0.05 ? ' train an hour' : ' trains an hour');
    $('#why-plat-txt').textContent = 'on one platform track, when each train stands ' + mins(min) + ' minutes, with ' + mins(clearMin) + ' to clear the track and ' + F.pct(util) + ' of the hour used at most';
    hour.setAttribute('aria-label', 'One hour on one platform track: ' + F.n(n, 1) + ' trains an hour when each stands ' + mins(min) + ' minutes');
    $('#why-plat-note').textContent = c ? c.note : 'Pick one of the four cases above to see where its standing time comes from.';
  };
  pills = PTS.steps($('#why-plat-cases'), cases.map(function (c) { return [c.id, c.label + ', ' + mins(c.min) + ' min']; }), 'turn', function (id) {
    const c = cases.filter(function (x) { return x.id === id; })[0]; if (!c) return;
    slider.set(c.min, true); drawHour(c.min, c);
  });
  slider = PTS.slider($('#why-plat-slider'), { label: 'Minutes a train stands at the platform', min: 2, max: 40, step: 1, value: 20, format: function (v) { return mins(v) + ' min'; } }, function (v) {
    const c = cases.filter(function (x) { return x.min === v; })[0];
    pills.set(c ? c.id : '', true); drawHour(v, c);
  });
  drawHour(20, cases.filter(function (x) { return x.id === 'turn'; })[0]);

  // ---- Lille to Lyon (and Bordeaux to Marseille by the link): four passengers followed minute by minute
  const P = D.connecting.central.pairs['Lyon-Nord'], PL = D.connecting.central.pairs['Montparnasse-Lyon'], T = 60;
  const KIND = { tgv: ['On the TGV', 'var(--s1)'], walk: ['Walking', 'var(--s2)'], metro: ['Metro or RER', 'var(--s3)'], wait: ['Waiting', 'var(--s4)'] };
  const fit = function (segs, total) {                     // the section's minutes are rescaled to the model's total
    const s = segs.reduce(function (a, x) { return a + x.min; }, 0);
    return segs.map(function (x) { return Object.assign({}, x, { min: x.min * total / s }); });
  };
  const ride = function (min, doing, what) { return { kind: 'tgv', min: min, what: what, doing: doing }; };
  const rows = [
    { name: 'Today, Lille to Lyon: change of station', dest: 'Lyon', segs: fit(own.today, P.old_clock) },
    { name: 'With the project, Lille to Lyon: same train', dest: 'Lyon', segs: [ride(P.direct, 'on the same train, between Nord-Est and Gare de Lyon', 'On the same train from Paris Nord-Est to Gare de Lyon, stop included')] },
    { name: 'With the project, Lille to Lyon: change at Nord-Est', dest: 'Lyon', segs: fit(own.change, P.change_clock - P.direct).concat([ride(P.direct, 'on the connecting train, between Nord-Est and Gare de Lyon', 'On the connecting train from Paris Nord-Est to Gare de Lyon, stop included')]) },
    { name: 'With the project, Bordeaux to Marseille: same train, by the direct link', dest: 'Marseille', segs: [ride(PL.direct, 'on the same train, between Montparnasse and Gare de Lyon by the direct link', 'On the same train from Montparnasse to Gare de Lyon by the direct link, stop included')] }
  ];
  const host = $('#why-trip');
  rows.forEach(function (r) {
    r.total = r.segs.reduce(function (a, x) { return a + x.min; }, 0);
    const strip = h('div', { class: 'why-strip' });
    let acc = 0;
    r.segs.forEach(function (x) {
      const seg = h('i', { tabindex: 0, role: 'img', 'aria-label': KIND[x.kind][0] + ', ' + mins(x.min) + ' minutes. ' + x.what, style: { left: (acc / T * 100) + '%', width: (x.min / T * 100) + '%', '--c': KIND[x.kind][1] } });
      PTS.tip.bind(seg, '<b>' + KIND[x.kind][0] + ', ' + mins(x.min) + ' min</b><br>' + x.what);
      strip.appendChild(seg); acc += x.min;
    });
    if (acc < T) {
      const gone = h('i', { class: 'gone', tabindex: 0, role: 'img', 'aria-label': 'Out of Paris, on the train to ' + r.dest + ', ' + mins(r.total) + ' minutes after arriving', style: { left: (acc / T * 100) + '%', width: ((T - acc) / T * 100) + '%' } });
      PTS.tip.bind(gone, '<b>Out of Paris</b><br>On the train to ' + r.dest + ', ' + mins(r.total) + ' minutes after arriving');
      strip.appendChild(gone);
    }
    r.cur = h('div', { class: 'cur' }); strip.appendChild(r.cur);
    r.status = h('span');
    host.appendChild(h('div', { class: 'why-trip-row' }, h('div', { class: 'lab' }, h('b', { text: r.name }), r.status), strip, h('div', { class: 'val', text: mins(r.total) + ' min' })));
  });
  host.appendChild(h('div', { class: 'why-trip-row', 'aria-hidden': 'true' }, h('div', { class: 'lab' }),
    h('div', { class: 'why-trip-axis' }, [0, 15, 30, 45, 60].map(function (t) { return h('span', { style: { left: (t / T * 100) + '%' }, text: t === 60 ? '60 min' : String(t) }); })), h('div', { class: 'val' })));
  const at = function (t) {
    rows.forEach(function (r) {
      let acc = 0, txt = null;
      r.segs.forEach(function (x) { if (txt == null && t < acc + x.min) txt = cap(x.doing); acc += x.min; });
      r.status.textContent = txt != null ? txt : (t - r.total < 0.01 ? 'Leaving Paris for ' + r.dest + ' now' : 'Left Paris ' + mins(t - r.total) + ' min ago, on the way to ' + r.dest);
      r.cur.style.left = (t / T * 100) + '%';
    });
  };
  PTS.slider($('#why-trip-slider'), { label: 'Minutes since the train arrived in Paris', min: 0, max: T, step: 2.5, value: 25, format: function (v) { return mins(v) + ' min'; } }, at);
  at(25);
  const leg = $('#why-trip-legend');
  ['tgv', 'walk', 'metro', 'wait'].forEach(function (k) { leg.appendChild(h('li', null, h('i', { style: { '--c': KIND[k][1] } }), KIND[k][0])); });
  leg.appendChild(h('li', null, h('i', { style: { '--c': 'color-mix(in srgb, var(--s1) 22%, transparent)' } }), 'Out of Paris, on the way to the next city'));
});
