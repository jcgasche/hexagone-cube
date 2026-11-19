/* The simulator of the annex on train spacing does in the page the calculation of model/headway.py. This checks that, with the values of
   the study, it gives the same least times as the model (src/sections/headway/data.json), for every tunnel and every pair of trains.

     node tools/check_headway_sim.js [--file ../en.html]
*/
const path = require('path');
const { chromium } = require('playwright');
const arg = (n, d) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : d; };
(async () => {
  const file = path.resolve(__dirname, arg('--file', '../../en.html'));
  const b = await chromium.launch(), p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  const errs = []; p.on('pageerror', e => errs.push(String(e)));
  await p.goto('file://' + file + '#headway'); await p.waitForTimeout(1500);
  const out = await p.evaluate(() => {
    const D = PTS.data.headway, S = PTS.headwaySim, K = D.params, res = [];
    const cases = [['central', 'auto'], ['central', 'short'], ['central', 'long'], ['cautious', 'auto'], ['cautious', 'long']];
    cases.forEach(function (cs) {
      const table = D.cases[cs[0] + '_' + cs[1]].table, sig = K.signal[cs[1]], perf = K.perf[cs[0]];
      Object.keys(table).forEach(function (key) {
        const i = key.lastIndexOf('_'), tube = key.slice(0, i), use = key.slice(i + 1), P = S.defaults(use);
        P.km = K.tubes_km[tube]; P.block = sig.block; P.tblock = sig.throat == null ? 1e9 : sig.throat; P.react = sig.react;
        P.acc_tgv = perf.tgv.acc; P.brk_tgv = perf.tgv.brk; P.acc_ter = perf.ter.acc; P.brk_ter = perf.ter.brk;
        const c = S.compute(P);
        Object.keys(table[key]).forEach(function (pair) { res.push({ where: cs.join(' ') + ' ' + key + ' ' + pair, model: table[key][pair].s, page: c.need[pair].s }); });
      });
    });
    return res;
  });
  let worst = 0; out.forEach(r => { const d = Math.abs(r.model - r.page); if (d > worst) worst = d; if (d > 0.05) console.log('differs:', r.where, r.model.toFixed(2), r.page.toFixed(2)); });
  console.log(out.length + ' least times compared, largest difference ' + worst.toFixed(4) + ' s, page errors: ' + errs.length, errs.slice(0, 3));
  await b.close();
  process.exit(worst > 0.05 || errs.length ? 1 : 0);
})();
