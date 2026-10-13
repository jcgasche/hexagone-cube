// Compares src/js/model.js with the Python model's exported cases. Usage: node tools/check_model.js
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
global.window = { PTS_DATA: { finance: JSON.parse(fs.readFileSync(path.join(root, 'src/data/finance.json'))) } };
window.PTS = { data: window.PTS_DATA };
eval(fs.readFileSync(path.join(root, 'src/js/model.js'), 'utf8'));
const M = window.PTS.model, fin = window.PTS_DATA.finance, P = fin.params;
const opts = {
  central: {}, no_charge: { charge_end: 0, charge_through: 0, rex_second: 0, rex_through: 0 }, tgv_charge_only: { rex_second: 0, rex_through: 0, fleet_capture: 0 },
  low_running: { om_scale: 'low' }, high_running: { om_scale: 'high' }, shops_full: { shop_net: 1 }, no_fleet: { fleet_capture: 0 }, package_low_running: { shop_net: 1, om_scale: 'low' },
  growth: { growth: P.growth }, low_cost: { cost: 'low' }, high_cost: { cost: 'high' }, high_traffic: { traffic: 'high' }, low_traffic: { traffic: 'low' }, ride: { traffic: 'ride' },
  best: { cost: 'low', traffic: 'high', growth: P.growth }, navigo_all: { navigo_new: 1 }, navigo_low: { navigo_new: 0.09 }, tax_high: { tax_wider: 'high' }, tax_low: { tax_wider: 'low' },
  rate45: { rate: 0.045, growth: P.growth }, rate45_flat: { rate: 0.045 }, resp05: { fare_response: P.fare_response_low },
  charge_double: { charge_end: 2 * P.charge_end, charge_through: 2 * P.charge_through },
  all_levers: { cost: 'low', traffic: 'high', growth: P.growth, om_scale: 'low', shop_net: 1 }
};
let worst = 0, n = 0;
const cmp = (a, b, where) => {
  if (typeof a === 'number') { const e = Math.abs(a - b) / Math.max(1e-9, Math.abs(a)); worst = Math.max(worst, e); n++; if (e > 1e-9) { console.log('DIFF', where, a, b); process.exitCode = 1; } }
  else if (a && typeof a === 'object') for (const k of Object.keys(a)) { if (k === 'opts') continue; if (b[k] === undefined) { console.log('MISSING', where + '.' + k); process.exitCode = 1; } else cmp(a[k], b[k], where + '.' + k); }
};
for (const [name, o] of Object.entries(opts)) cmp(fin.cases[name], M.accounts(o), name);
cmp(fin.cases.breakeven_charge, M.breakevenCharge({}), 'breakeven');
cmp(fin.cases.breakeven_charge_tgv_only, M.breakevenCharge({ rex_second: 0, rex_through: 0, fleet_capture: 0 }), 'breakeven_tgv_only');
for (const lv of ['low', 'central', 'high']) { const c = M.cost(fin.base.cost_def.rates[lv]); cmp(fin.base.layout.capex[lv], c.total, 'cost ' + lv); cmp(fin.base.layout.systems[lv], c.systems, 'systems ' + lv); }
console.log(n + ' numbers compared, largest relative difference ' + worst.toExponential(2) + (process.exitCode ? '  FAILED' : '  OK'));
