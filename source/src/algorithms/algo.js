/* "See the algorithm used": a dialog that explains how the figures of a block are computed, shows the code of the model
   (highlighted here, cut from source/model/ at build time) and gives a runnable .py that packs the model files and inputs it needs.
   Everything is in the page (script#pts-algo), read on first use, so the page still opens from disk with no server. */
(function () {
  const h = PTS.h;
  let A = null, dlg = null, state = null;

  function data() {
    if (!A) A = JSON.parse(document.getElementById('pts-algo').textContent);
    return A;
  }

  // ---- Python, highlighted: comments, strings, numbers, keywords, builtins, the names of definitions
  const KW = new Set('and as assert break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return True try while with yield'.split(' '));
  const BI = new Set('abs all any dict enumerate float int len list max min next open print range round set sorted str sum tuple zip isinstance getattr frozenset'.split(' '));
  const TOK = /(#[^\n]*)|([rRbBfFuU]{0,2}(?:'''[\s\S]*?'''|"""[\s\S]*?"""|'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"))|(\b\d[\d_]*\.?\d*(?:[eE][-+]?\d+)?\b)|([A-Za-z_]\w*)/g;
  function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function highlight(src) {           // the lines of the source as HTML; a token over several lines (a docstring) keeps its colour on each
    const lines = ['']; let last = 0, m, prev = '';
    function put(text, c) {
      text.split('\n').forEach(function (part, i) {
        if (i) lines.push('');
        if (part) lines[lines.length - 1] += c ? '<span class="py-' + c + '">' + esc(part) + '</span>' : esc(part);
      });
    }
    TOK.lastIndex = 0;
    while ((m = TOK.exec(src))) {
      put(src.slice(last, m.index)); last = TOK.lastIndex;
      const t = m[0]; let c = null;
      if (m[1]) c = 'c'; else if (m[2]) c = 's'; else if (m[3]) c = 'n';
      else if (KW.has(t)) c = 'k'; else if (prev === 'def' || prev === 'class') c = 'f'; else if (BI.has(t)) c = 'b';
      else if (/^[A-Z][A-Z0-9_]+$/.test(t)) c = 'u';
      put(t, c);
      if (m[4]) prev = t;
    }
    put(src.slice(last));
    return lines;
  }
  function codeBlock(piece) {
    return highlight(piece.text).map(function (l, i) { return '<span class="ln">' + (piece.start + i) + '</span>' + l; }).join('\n');
  }

  // ---- the runnable script
  function pyName(id) { return 'hexagone3_' + id + '.py'; }
  function wrapText(s, width) {
    const out = []; let line = '';
    s.split(/\s+/).forEach(function (w) { if ((line + ' ' + w).trim().length > width) { out.push(line); line = w; } else line = (line + ' ' + w).trim(); });
    if (line) out.push(line);
    return out;
  }
  function plain(html) { const d = document.createElement('div'); d.innerHTML = html; return d.textContent; }
  function script(id) {
    const D = data(), al = D.algos[id], W = D.words;
    const doc = [al.title, '', ...wrapText(W.doc, 100), ''];
    al.explain.forEach(function (p) { doc.push(...wrapText(plain(p), 100), ''); });
    doc.push(W.run.replace('{file}', pyName(id)), 'CC BY 4.0, Jean-Charles Gasche, https://jcgasche.github.io/hexagone-cube/');
    const out = ['#!/usr/bin/env python3', '"""' + doc.join('\n').replace(/"""/g, "'''").replace(/\\/g, '/') + '\n"""',
      'import base64, gzip, os, sys, tempfile', '', '',
      'def run():',
      al.run.split('\n').map(function (l) { return l ? '    ' + l : ''; }).join('\n'), '', '',
      'def unpack(folder):',
      '    for path, (kind, body) in FILES.items():',
      "        full = os.path.join(folder, *path.split('/'))",
      '        os.makedirs(os.path.dirname(full), exist_ok=True)',
      "        with open(full, 'wb') as f: f.write(body.encode('utf-8') if kind == 'text' else gzip.decompress(base64.b64decode(body)))",
      '', '',
      '# the model files and inputs, as they are in source/ of the repository',
      'FILES = {'];
    al.files.forEach(function (p) {
      const f = D.files[p];
      if (f[0] === 'text') out.push("'" + p + "': ('text', r'''" + f[1] + (f[1].endsWith('\n') ? '' : '\n') + "'''),");
      else {
        const b = f[1], parts = [];
        for (let i = 0; i < b.length; i += 100) parts.push("    '" + b.slice(i, i + 100) + "'");
        out.push("'" + p + "': ('gz', (", parts.join('\n'), ')),');
      }
    });
    out.push('}', '', '',
      "if __name__ == '__main__':",
      '    with tempfile.TemporaryDirectory() as folder:',
      '        unpack(folder)',
      "        sys.path.insert(0, os.path.join(folder, 'model'))",
      '        os.chdir(folder)',
      '        run()', '');
    return out.join('\n');
  }
  function download(id) {
    const url = URL.createObjectURL(new Blob([script(id)], { type: 'text/x-python;charset=utf-8' }));
    const a = h('a', { href: url, download: pyName(id) }); document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
  }
  PTS.algoScript = script;          // for tools/check_algorithms.js

  // ---- the dialog
  function build() {
    const W = data().words;
    dlg = h('dialog', { class: 'algo-dlg', 'aria-labelledby': 'algo-title' });
    dlg.innerHTML =
      '<div class="algo-head"><div><span class="eyebrow">' + esc(W.title) + '</span><h2 id="algo-title"></h2></div>' +
      '<button type="button" class="algo-x" aria-label="' + esc(W.close) + '">×</button></div>' +
      '<div class="algo-uses"></div>' +
      '<div class="algo-tabs" role="tablist"><button type="button" role="tab" data-tab="explain">' + esc(W.explain) + '</button><button type="button" role="tab" data-tab="code">' + esc(W.code) + '</button></div>' +
      '<div class="algo-body"><div class="algo-panel" data-panel="explain" role="tabpanel"></div><div class="algo-panel" data-panel="code" role="tabpanel"></div></div>' +
      '<div class="algo-foot"><button type="button" class="algo-dl"></button><span class="note"></span></div>';
    document.body.appendChild(dlg);
    dlg.querySelector('.algo-x').onclick = function () { dlg.close(); };
    dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });       // a click on the backdrop
    dlg.querySelectorAll('[role=tab]').forEach(function (b) { b.onclick = function () { state.tab = b.dataset.tab; show(); }; });
    dlg.querySelector('.algo-dl').onclick = function () { download(state.id); };
  }
  function show() {
    const D = data(), W = D.words, al = D.algos[state.id];
    dlg.querySelector('#algo-title').textContent = al.title;
    const uses = dlg.querySelector('.algo-uses'); PTS.clear(uses);
    if (state.ids.length > 1) {
      uses.appendChild(h('span', { class: 'algo-uses-k', text: W.uses }));
      state.ids.forEach(function (x) {
        uses.appendChild(h('button', { type: 'button', class: 'algo-chip', 'aria-pressed': String(x === state.id), text: D.algos[x].title,
          onclick: function () { state.id = x; show(); } }));
      });
    }
    dlg.querySelectorAll('[role=tab]').forEach(function (b) { b.setAttribute('aria-selected', String(b.dataset.tab === state.tab)); });
    dlg.querySelectorAll('.algo-panel').forEach(function (p) { p.hidden = p.dataset.panel !== state.tab; });
    // explanation, and the figures of this block that this algorithm gives
    const ex = dlg.querySelector('[data-panel=explain]'); PTS.clear(ex);
    al.explain.forEach(function (p, i) { ex.appendChild(h('p', { html: p, class: i ? null : 'algo-goal' })); });
    const figs = (D.blocks[state.block] || []).filter(function (f) { return f[2].indexOf(state.id) >= 0; });
    if (figs.length) {
      ex.appendChild(h('h3', { text: W.figures }));
      const max = 14, tb = h('tbody');
      figs.slice(0, max).forEach(function (f) {
        const what = esc((f[3] || '').replace(/^(\u0001?)(\p{Ll})/u, function (m, b, c) { return b + c.toUpperCase(); })).replace(/\u0001/g, '<b>').replace(/\u0002/g, '</b>');       // the page's words for it, the figure in bold
        tb.appendChild(h('tr', {}, h('td', {}, h('span', { class: 'algo-what', html: what }), h('code', { text: f[0] })), h('td', { class: 'num', text: f[1] })));
      });
      ex.appendChild(h('div', { class: 'tbl-wrap' }, h('table', { class: 'tbl no-stack algo-figs' }, h('thead', {}, h('tr', {}, h('th', { text: W.expr }), h('th', { class: 'num', text: W.shown }))), tb)));
      if (figs.length > max) ex.appendChild(h('p', { class: 'note', text: W.more.replace('{n}', figs.length - max) }));
    }
    // code: the pieces of the model, then what the script runs
    const co = dlg.querySelector('[data-panel=code]'); PTS.clear(co);
    co.appendChild(h('p', { class: 'note', text: W.from }));
    let file = null;
    al.pieces.forEach(function (p) {
      if (p.file !== file) { file = p.file; co.appendChild(h('div', { class: 'algo-file', text: 'source/' + p.file })); }
      const n = p.text.split('\n').length;
      co.appendChild(h('div', { class: 'algo-lines', text: W.lines.replace('{a}', p.start).replace('{z}', p.start + n - 1) }));
      co.appendChild(h('pre', { class: 'algo-code' }, h('code', { html: codeBlock(p) })));
    });
    co.appendChild(h('div', { class: 'algo-file', text: W.what }));
    co.appendChild(h('pre', { class: 'algo-code' }, h('code', { html: codeBlock({ start: 1, text: al.run }) })));
    dlg.querySelector('.algo-dl').textContent = W.download + ' (' + pyName(state.id) + ')';
    dlg.querySelector('.algo-foot .note').textContent = W.run.replace('{file}', pyName(state.id));
  }
  function open(btn) {
    if (!dlg) build();
    const ids = btn.dataset.algos.split(' ');
    state = { ids: ids, id: ids[0], tab: 'explain', block: btn.dataset.block };
    show();
    dlg.showModal();
  }
  document.addEventListener('click', function (e) {
    const b = e.target.closest && e.target.closest('.algo-btn');
    if (b) open(b);
  });
})();
