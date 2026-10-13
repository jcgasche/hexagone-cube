// Compares src/js/model.js with the Python model's exported cases. Usage: node tools/check_model.js
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
global.window = { PTS_DATA: { finance: JSON.parse(fs.readFileSync(path.join(root, 'src/data/finance.json'))) } };
window.PTS = { data: window.PTS_DATA };
eval(fs.readFileSync(path.join(root, 'src/js/model.js'), 'utf8'));
const M = window.PTS.model, fin = window.PTS_DATA.finance, P = fin.params;
const opts = {
  central: {}, no_charge: { charge_end: 0, charge_through: 0 }, low_running: { om_scale: 'low' }, high_running: { om_scale: 'high' }, with_options: { fleet_capture: P.fleet_capture, reg_supp: P.reg_supp },
  with_options_low_running: { fleet_capture: P.fleet_capture, reg_supp: P.reg_supp, om_scale: 'low' },
  growth: { growth: P.growth }, low_cost: { cost: 'low' }, high_cost: { cost: 'high' }, high_traffic: { traffic: 'high' }, low_traffic: { traffic: 'low' },
  best: { cost: 'low', traffic: 'high', growth: P.growth }, navigo_all: { navigo_new: 1 }, tax_high: { tax_wider: 'high' }, tax_low: { tax_wider: 'low' }, rate45: { rate: 0.045, growth: P.growth },
  resp05: { fare_response: P.fare_response_low }, charge_matched: { charge_end: P.charge_alt[0], charge_through: P.charge_alt[1] },
  all_levers: { cost: 'low', traffic: 'high', growth: P.growth, om_scale: 'low', fleet_capture: P.fleet_capture, reg_supp: P.reg_supp }
};
let worst = 0, n = 0;
const cmp = (a, b, where) => {
  if (typeof a === 'number') { const e = Math.abs(a - b) / Math.max(1e-9, Math.abs(a)); worst = Math.max(worst, e); n++; if (e > 1e-9) { console.log('DIFF', where, a, b); process.exitCode = 1; } }
  else if (a && typeof a === 'object') for (const k of Object.keys(a)) { if (k === 'opts') continue; if (b[k] === undefined) { console.log('MISSING', where + '.' + k); process.exitCode = 1; } else cmp(a[k], b[k], where + '.' + k); }
};
for (const lay of ['A', 'B']) {
  for (const [name, o] of Object.entries(opts)) cmp(fin.cases[lay + '_' + name], M.accounts(Object.assign({ layout: lay }, o)), lay + '_' + name);
  cmp(fin.cases[lay + '_breakeven_charge'], M.breakevenCharge({ layout: lay }), lay + '_breakeven');
  for (const lv of ['low', 'central', 'high']) { const c = M.cost(lay, fin.base.cost_def.rates[lv]); cmp(fin.base.layouts[lay].capex[lv], c.total, lay + ' cost ' + lv); cmp(fin.base.layouts[lay].systems[lv], c.systems, lay + ' systems ' + lv); }
}
console.log(n + ' numbers compared, largest relative difference ' + worst.toExponential(2) + (process.exitCode ? '  FAILED' : '  OK'));
