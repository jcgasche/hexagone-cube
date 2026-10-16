/* Core of the site: section registry, router, formatting, small DOM helpers, controls, tooltip.
   Everything hangs off one global, PTS. Sections register with PTS.section(id, init); init(root) runs once, the first time the section is shown. */
(function () {
  'use strict';
  const PTS = window.PTS = window.PTS || {};
  PTS.data = window.PTS_DATA || {};
  const inits = {}, started = {};
  PTS.section = function (id, fn) { inits[id] = fn; };

  // ---------------------------------------------------------------- formatting (English, comma thousands)
  const nf = {};
  function n(x, d) { d = d || 0; if (!isFinite(x)) return 'n/a'; const k = d; nf[k] = nf[k] || new Intl.NumberFormat('en-GB', { minimumFractionDigits: d, maximumFractionDigits: d }); const s = nf[k].format(x); return /^-0(\.0+)?$/.test(s) ? s.slice(1) : s; }
  PTS.fmt = {
    n: n,
    bn: function (x, d) { return '€' + n(x, d == null ? 1 : d) + 'bn'; },            // input in bn euros
    m: function (x) { return (x < 0 ? '-' : '') + '€' + n(Math.abs(x) * 1000, 0) + 'm'; },   // input in bn euros, shown in millions
    money: function (x) { return Math.abs(x) >= 1 ? PTS.fmt.bn(x, 2) : PTS.fmt.m(x); },
    pct: function (x, d) { return n(x * 100, d || 0) + '%'; },
    eur: function (x, d) { return '€' + n(x, d == null ? 2 : d); },
    M: function (x, d) { return n(x, d == null ? 1 : d) + ' million'; },
    min: function (x, d) { return n(x, d == null ? 1 : d) + ' min'; },
    signed: function (x, d) { return (x > 0 ? '+' : '') + n(x, d == null ? 1 : d); }
  };

  // ---------------------------------------------------------------- DOM helpers
  function build(el, attrs, kids) {
    if (attrs) for (const k in attrs) {
      const v = attrs[k]; if (v == null || v === false) continue;
      if (k === 'class') el.setAttribute('class', v);
      else if (k === 'style' && typeof v === 'object') for (const p in v) el.style.setProperty(p, v[p]);
      else if (k === 'text') el.textContent = v;
      else if (k === 'html') el.innerHTML = v;
      else if (k.slice(0, 2) === 'on' && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    }
    (kids || []).forEach(function add(c) { if (c == null || c === false) return; if (Array.isArray(c)) return c.forEach(add); el.appendChild(typeof c === 'object' ? c : document.createTextNode(String(c))); });
    return el;
  }
  PTS.h = function (tag, attrs) { return build(document.createElement(tag), attrs, Array.prototype.slice.call(arguments, 2)); };
  PTS.s = function (tag, attrs) { return build(document.createElementNS('http://www.w3.org/2000/svg', tag), attrs, Array.prototype.slice.call(arguments, 2)); };
  PTS.clear = function (el) { while (el.firstChild) el.removeChild(el.firstChild); return el; };
  PTS.$ = function (sel, root) { return (root || document).querySelector(sel); };
  PTS.$$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  PTS.store = { get: function (k, d) { try { const v = localStorage.getItem('pts.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }, set: function (k, v) { try { localStorage.setItem('pts.' + k, JSON.stringify(v)); } catch (e) { /* storage is optional */ } } };
  PTS.onResize = function (el, fn) {
    let t = null, w = -1;
    const run = function () { const nw = el.clientWidth; if (nw && nw !== w) { w = nw; fn(nw); } };
    if (window.ResizeObserver) new ResizeObserver(function () { clearTimeout(t); t = setTimeout(run, 60); }).observe(el);
    else window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(run, 120); });
    run();
  };

  // ---------------------------------------------------------------- tooltip
  let tipEl = null;
  PTS.tip = {
    show: function (html, evt) {
      if (!tipEl) { tipEl = PTS.h('div', { class: 'tip', role: 'tooltip' }); document.body.appendChild(tipEl); }
      tipEl.innerHTML = html; tipEl.hidden = false;
      const r = tipEl.getBoundingClientRect(), vw = window.innerWidth, vh = window.innerHeight;
      let x = (evt.clientX || 0) + 14, y = (evt.clientY || 0) + 14;
      if (x + r.width > vw - 8) x = Math.max(8, (evt.clientX || 0) - r.width - 14);
      if (y + r.height > vh - 8) y = Math.max(8, (evt.clientY || 0) - r.height - 14);
      tipEl.style.left = x + 'px'; tipEl.style.top = y + 'px';
    },
    hide: function () { if (tipEl) tipEl.hidden = true; },
    bind: function (el, html) {
      const get = function () { return typeof html === 'function' ? html() : html; };
      el.addEventListener('pointerenter', function (e) { PTS.tip.show(get(), e); });
      el.addEventListener('pointermove', function (e) { PTS.tip.show(get(), e); });
      el.addEventListener('pointerleave', PTS.tip.hide);
      el.addEventListener('focus', function () { const r = el.getBoundingClientRect(); PTS.tip.show(get(), { clientX: r.left + r.width / 2, clientY: r.bottom }); });
      el.addEventListener('blur', PTS.tip.hide);
      return el;
    }
  };

  // ---------------------------------------------------------------- controls
  /* Segmented switch. options: [[value, label], ...]. Returns {get, set}. */
  PTS.seg = function (host, options, value, onChange, label) {
    const box = PTS.h('div', { class: 'seg', role: 'group', 'aria-label': label || '' });
    const set = function (v, silent) { value = v; PTS.$$('button', box).forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.v === String(v))); }); if (!silent && onChange) onChange(v); };
    options.forEach(function (o) { box.appendChild(PTS.h('button', { type: 'button', 'data-v': o[0], text: o[1], onclick: function () { set(o[0]); } })); });
    host.appendChild(label ? PTS.h('div', { class: 'field' }, PTS.h('span', { text: label }), box) : box);
    set(value, true);
    return { get: function () { return value; }, set: set };
  };
  /* Range slider with a live read-out. cfg: {label, min, max, step, value, format(v), note}. Returns {get, set}. */
  let uid = 0;
  PTS.slider = function (host, cfg, onChange) {
    const id = 'pts-sl-' + (++uid), fmt = cfg.format || function (v) { return String(v); };
    const out = PTS.h('output', { for: id, text: fmt(cfg.value) });
    const input = PTS.h('input', { type: 'range', id: id, min: cfg.min, max: cfg.max, step: cfg.step || 1, value: cfg.value });
    input.addEventListener('input', function () { const v = parseFloat(input.value); out.textContent = fmt(v); if (onChange) onChange(v); });
    host.appendChild(PTS.h('div', { class: 'slider' }, PTS.h('label', { for: id, text: cfg.label }), out, input, cfg.note ? PTS.h('small', { text: cfg.note }) : null));
    return { get: function () { return parseFloat(input.value); }, set: function (v, silent) { input.value = v; out.textContent = fmt(v); if (!silent && onChange) onChange(v); } };
  };
  /* Pill steps (for staged walkthroughs). options: [[value, label], ...]. */
  PTS.steps = function (host, options, value, onChange) {
    const box = PTS.h('div', { class: 'steps', role: 'group' });
    const set = function (v, silent) { value = v; PTS.$$('button', box).forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.v === String(v))); }); if (!silent && onChange) onChange(v); };
    options.forEach(function (o) { box.appendChild(PTS.h('button', { type: 'button', 'data-v': o[0], text: o[1], onclick: function () { set(o[0]); } })); });
    host.appendChild(box); set(value, true);
    return { get: function () { return value; }, set: set };
  };
  /* Table from data. cols: [{key, label, num, fmt}], rows: objects. opts: {totalKey} */
  PTS.table = function (host, cols, rows) {
    const t = PTS.h('table', { class: 'tbl' },
      PTS.h('thead', null, PTS.h('tr', null, cols.map(function (c) { return PTS.h('th', { class: c.num ? 'num' : null, text: c.label }); }))),
      PTS.h('tbody', null, rows.map(function (r) {
        return PTS.h('tr', { class: r._class || null }, cols.map(function (c, i) {
          const v = r[c.key], txt = v == null ? '' : (c.fmt ? c.fmt(v, r) : v);
          return PTS.h(i === 0 ? 'th' : 'td', { class: c.num ? 'num' : null, html: c.html ? txt : null, text: c.html ? null : txt });
        }));
      })));
    host.appendChild(PTS.h('div', { class: 'tbl-wrap' }, t));
    if (PTS.stackTables) PTS.stackTables(host);
    return t;
  };

  /* Tables of four or more columns turn into one card per row on a phone: copy the column headings into data-l. */
  PTS.stackTables = function (root) {
    PTS.$$('table.tbl', root).forEach(function (t) {
      if (t.classList.contains('stack-sm') || t.classList.contains('no-stack') || t.querySelector('[data-l]')) return;
      const heads = PTS.$$('thead th', t).map(function (th) { const c = th.cloneNode(true); PTS.$$('sup', c).forEach(function (x) { x.remove(); }); return c.textContent.trim(); });
      if (heads.length < 4) return;
      PTS.$$('tbody tr', t).forEach(function (tr) {
        let col = 0;
        Array.prototype.forEach.call(tr.children, function (c) { if (c.tagName === 'TD' && heads[col]) c.setAttribute('data-l', heads[col]); col += c.colSpan || 1; });
      });
      t.classList.add('stack-sm');
    });
  };

  // ---------------------------------------------------------------- borrowing: one section shows a figure of another
  /* The presentation shows some figures of the report as they are, with no copy: the nodes move into the presentation
     while it is shown and go back to their section when that section is shown. The lender's own lookups by id still
     find them, because its root falls back to the whole document for what it no longer holds. */
  const borrowed = [];
  PTS.ensure = function (id) {
    const page = document.getElementById(id);
    if (!page || started[id] || !inits[id]) return page;
    started[id] = true;
    const q1 = page.querySelector;
    page.querySelector = function (sel) { return q1.call(this, sel) || (/^#[\w-]+$/.test(sel) ? document.querySelector(sel) : null); };
    try { inits[id](page); } catch (e) { console.error('Section ' + id + ' failed to start', e); }
    return page;
  };
  PTS.borrow = function (hostPage, host, nodes) {
    nodes.forEach(function (el) { if (el) borrowed.push({ el: el, page: hostPage, host: host, home: el.parentNode, next: el.nextSibling }); });
    place();
  };
  function place() {
    const id = current && current.id;
    borrowed.forEach(function (b) { if (id === b.page) { if (b.el.parentNode !== b.host) b.host.appendChild(b.el); } });
    borrowed.slice().reverse().forEach(function (b) { if (id !== b.page && b.el.parentNode !== b.home) b.home.insertBefore(b.el, b.next && b.next.parentNode === b.home ? b.next : null); });
  }

  // ---------------------------------------------------------------- router: #section or #section.anchor
  let pages = [], current = null;
  function parse(hash) { const h = (hash || '').replace(/^#/, ''); const i = h.indexOf('.'); return { id: i < 0 ? h : h.slice(0, i), anchor: i < 0 ? null : h }; }
  function closeMenu() { document.body.classList.remove('menu-open'); const b = PTS.$('.menu-btn'); if (b) b.setAttribute('aria-expanded', 'false'); }
  PTS.go = function (hash, opts) {
    if (!(opts && opts.silent)) { try { history.replaceState({ y: window.scrollY }, ''); } catch (e) { /* optional */ } }     // so that Back returns to this place
    const t = parse(hash); let page = document.getElementById(t.id);
    if (!page || !page.classList.contains('page')) { page = pages[0]; t.anchor = null; }
    if (!page) return;
    if (page !== current) {
      pages.forEach(function (p) { p.hidden = p !== page; });
      current = page;
      document.body.setAttribute('data-page', page.id);
      place();
      PTS.$$('.contents a').forEach(function (a) { if (a.getAttribute('href') === '#' + page.id) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
      const here = PTS.$('.topbar .here'); if (here) here.textContent = page.dataset.title || '';
      PTS.ensure(page.id);
      PTS.stackTables(page);
    }
    closeMenu();
    if (opts && opts.restore != null) { window.scrollTo(0, opts.restore); return; }
    const target = t.anchor && document.getElementById(t.anchor);
    if (target) { if (target.tagName === 'DETAILS') target.open = true; target.scrollIntoView({ block: 'start' }); if (target.classList.contains('src-row')) { target.classList.add('flash'); setTimeout(function () { target.classList.remove('flash'); }, 2500); } }
    else if (!(opts && opts.keepScroll)) window.scrollTo(0, 0);
    if (!(opts && opts.silent)) { try { if (location.hash !== '#' + (t.anchor || page.id)) history.pushState({ y: 0 }, '', '#' + (t.anchor || page.id)); } catch (e) { /* history may be unavailable in a sandbox */ } }
  };
  PTS.current = function () { return current && current.id; };

  function start() {
    pages = PTS.$$('main > .page');
    const links = PTS.$$('.contents a');
    pages.forEach(function (p, i) {                                   // previous / next at the foot of each section
      const prev = pages[i - 1], next = pages[i + 1];
      p.appendChild(PTS.h('nav', { class: 'pager', 'aria-label': 'Previous and next section' },
        prev ? PTS.h('a', { href: '#' + prev.id, class: 'prev' }, PTS.h('span', { text: 'Previous' }), PTS.h('b', { text: prev.dataset.title })) : null,
        next ? PTS.h('a', { href: '#' + next.id, class: 'next' }, PTS.h('span', { text: 'Next' }), PTS.h('b', { text: next.dataset.title })) : null));
    });
    PTS.stackTables(document);
    document.addEventListener('click', function (e) {
      const a = e.target.closest && e.target.closest('a[href^="#"]'); if (!a) return;
      const href = a.getAttribute('href'); if (href.length < 2) return;
      e.preventDefault(); PTS.go(href);
    });
    let popped = 0;
    window.addEventListener('popstate', function (e) { popped = Date.now(); PTS.go(location.hash, { silent: true, restore: e.state && typeof e.state.y === 'number' ? e.state.y : null }); });
    window.addEventListener('hashchange', function () { if (Date.now() - popped > 200) PTS.go(location.hash, { silent: true }); });
    const btn = PTS.$('.menu-btn');
    if (btn) { btn.setAttribute('aria-expanded', 'false'); btn.addEventListener('click', function () { const open = document.body.classList.toggle('menu-open'); btn.setAttribute('aria-expanded', String(open)); }); }
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMenu(); });
    PTS.go(location.hash || (links[0] && links[0].getAttribute('href')) || '', { silent: true });
  }
  PTS.start = start;      // called once by the last script of the page, after every section has registered
})();
