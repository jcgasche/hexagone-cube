// Writes the runnable .py of every algorithm as the page builds it (src/algorithms/algo.js, reading the data of a built page), then runs
// each with python3 in an empty folder and reports what fails. No packages needed.
//   node tools/check_algorithms.js                      # reads ../en.html, writes to dist/algorithms/
//   node tools/check_algorithms.js --page ../index.html --only cost,accounts --out /tmp/algo
const fs = require('fs'), path = require('path'), vm = require('vm'), { execFileSync } = require('child_process');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const ROOT = path.join(__dirname, '..');
const page = fs.readFileSync(path.resolve(ROOT, arg('page', '../en.html')), 'utf8');
const json = page.match(/<script type="application\/json" id="pts-algo">([\s\S]*?)<\/script>/)[1];
const out = path.resolve(ROOT, arg('out', 'dist/algorithms')); fs.mkdirSync(out, { recursive: true });
const only = arg('only', '') ? arg('only', '').split(',') : null;

// just enough of a page for algo.js: its data, and an element that turns HTML into text
const el = () => ({ set innerHTML(v) { this._t = v.replace(/<[^>]+>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'); }, get textContent() { return this._t; } });
const sandbox = { PTS: { h: () => null }, document: { getElementById: () => ({ textContent: json }), createElement: el, addEventListener: () => {} } };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(ROOT, 'src', 'algorithms', 'algo.js'), 'utf8'), sandbox);

const ids = Object.keys(JSON.parse(json).algos).filter(id => !only || only.includes(id));
let bad = 0;
for (const id of ids) {
  const file = path.join(out, 'hexagone3_' + id + '.py');
  fs.writeFileSync(file, sandbox.PTS.algoScript(id));
  const t0 = Date.now();
  try {
    const res = execFileSync('python3', ['-I', file], { cwd: out, encoding: 'utf8', timeout: 600000, stdio: ['ignore', 'pipe', 'pipe'] });
    console.log(`ok   ${id} (${((Date.now() - t0) / 1000).toFixed(0)} s, ${(fs.statSync(file).size / 1024).toFixed(0)} KB)\n` + res.split('\n').slice(0, 4).map(l => '     ' + l).join('\n'));
  } catch (e) {
    bad++; console.log(`FAIL ${id}\n` + String(e.stderr || e.message).split('\n').slice(-8).join('\n'));
  }
}
process.exit(bad ? 1 : 0);
