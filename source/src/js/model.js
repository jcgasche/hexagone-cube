/* The yearly accounts and the cost build-up, in the browser. This file repeats model/finance.py (accounts) and
   model/nordest.py (cost) line for line, on the numbers exported in data/finance.json ("base").
   tools/check_model.js compares the two; run it after any change here or in the Python model. */
(function () {
  'use strict';
  const PTS = window.PTS = window.PTS || {};
  const M = PTS.model = {};
  M.base = function () { return PTS.data.finance.base; };

  M.af = function (r, n) { return r / (1 - Math.pow(1 + r, -n)); };
  M.idc = function (r, years) { let t = 0; for (let k = 0; k < years; k++) t += Math.pow(1 + r, k + 0.5); return t / years; };
  M.growFactor = function (g, r, n) {
    if (Math.abs(g) < 1e-9) return 1;
    if (Math.abs(r - g) < 1e-9) return n / (1 + r) * M.af(r, n);
    const q = (1 + g) / (1 + r);
    return (1 - Math.pow(q, n)) / (1 - q) / (1 + r) * M.af(r, n);
  };

  /* Cost of the triangle from unit rates (bn euros of 2026). R: rates object, as base.cost_def.rates.central; L: a layout like base.cost_def.layout. */
  M.cost = function (R, L) {
    const D = M.base().cost_def; L = L || D.layout;
    const total = function (o) { let t = 0; Object.keys(o).forEach(function (k) { t += o[k]; }); return t; };
    const portals = total(L.portals), junctions = total(L.junctions);
    const km = total(L.tunnels);
    const plat = {}; let platTotal = 0;
    Object.keys(L.stations).forEach(function (n) { let m = 0; Object.keys(L.stations[n]).forEach(function (k) { m += L.stations[n][k] * D.len[k]; }); plat[n] = m; platTotal += m; });
    let halls = 0; L.halls.forEach(function (hname) { halls += R.hall[hname]; });
    const items = {
      'Tunnels, civil works': km * R.tunnel_civil, 'Tunnels, rail systems': km * R.tunnel_systems, 'Stations': platTotal * R.platform_m, 'Historic halls': halls,
      'Underground junctions': junctions * R.junction, 'Portals and links to existing lines': portals * R.portal, 'Sidings and depot links': R.sidings,
      'Control hall for London trains': R.london_hall
    };
    let hard = 0; Object.keys(items).forEach(function (k) { hard += items[k]; });
    const soft = hard * (R.design + R.client), land = hard * R.land, risk = (hard + soft + land) * R.risk;
    return { tunnel_km: km, tunnel_by_type: L.tunnels, link_km: D.link_km, platform_m: plat, platform_total: platTotal, portals: portals, junctions: junctions, items: items, hard: hard, soft: soft, land: land, risk: risk, total: hard + soft + land + risk,
             systems: items['Tunnels, rail systems'] * (1 + R.design + R.client) * (1 + R.risk) };
  };

  /* Paris-region response at one level of charge, by straight lines between the levels tabulated by the Python model. */
  M.atCharge = function (curve, charge) {
    const rows = curve.rows, x = Math.max(0, charge) / curve.step, i = Math.min(Math.floor(x), rows.length - 2), w = x - i, out = {};
    curve.cols.forEach(function (k, j) { out[k] = rows[i][j] + (rows[i + 1][j] - rows[i][j]) * w; });
    return out;
  };

  /* The two accounts, the economic return and the public return for one set of choices. bn euros a year unless stated.
     o overrides base.defaults. o.capex and o.systems (bn) may replace the stored cost levels (used by the cost explorer).
     o.om_scale may be 'low' or 'high': the running-cost cases of the layout. */
  M.accounts = function (o) {
    const base = M.base(), d = Object.assign({}, base.defaults, o || {});
    const L = base.layout, T = base.traffic[d.traffic], r = d.rate, n = base.n;
    if (d.om_scale === 'low' || d.om_scale === 'high') d.om_scale = L['om_' + d.om_scale];
    const A = M.af(r, n), K = M.idc(r, base.build_years), G = M.growFactor(d.growth, r, n), GT = M.growFactor(d.growth * base.traffic_growth_share, r, n);
    const capex = d.capex != null ? d.capex : L.capex[d.cost], systems = d.systems != null ? d.systems : L.systems[d.cost];
    const out = { capex: capex, idc: K, af: A, grow: G, grow_traffic: GT, annuity: capex * K * A, opts: d };
    const sum = function (obj) { let t = 0; Object.keys(obj).forEach(function (k) { t += obj[k]; }); return t; };
    // operations: costs
    const omInfra = (L.tunnel_km * base.om.tunnel + L.platform_m * base.om.station) * d.om_scale;
    const renewal = systems / Math.pow(1 + r, base.renew_year) * A;
    out.ops_cost = { 'Running and maintaining tunnels and stations': omInfra, 'Extra running of regional trains': base.om.trains, 'Renewal of rail systems, set aside each year': renewal };
    out.ops_cost_total = sum(out.ops_cost);
    // high-speed passengers and the charge: only new uses pay (another station than the line's own, crossing Paris); no journey is lost against today
    const fare = base.fare, resp = d.fare_response, curve = base.access_curve[T.measure];
    const P0 = M.atCharge(curve, 0), P = M.atCharge(curve, d.charge_end);
    const paris = (T.paris_base + P.journeys) * GT, payingParis = paris * P.pay;
    const ff = function (charge) { return Math.pow(1 + charge / (2 * fare), resp); };
    let through = 0, change = 0;
    T.cross_parts.forEach(function (x) { if (x[2]) through += x[0] * x[1] * ff(d.charge_through); else change += x[0] * x[1] * ff(2 * d.charge_end); });
    through *= GT; change *= GT;
    const cross = through + change, crossNew = cross / GT - T.cross_base;
    const gross = (payingParis * d.charge_end + through * d.charge_through + change * 2 * d.charge_end) / 1000;
    const newTgv = (P.journeys + crossNew) * GT, newBefore = (P0.journeys + T.cross_new) * GT, heldCross = (T.cross_new - crossNew) * GT;
    const track = (P.journeys + 2 * crossNew) * GT * fare * base.track_share / 1000;
    out.tgv = { paris: paris, cross: cross, through: through, change: change, paying_paris: payingParis, pay_share: P.pay, new_before_charge: newBefore,
                held: newBefore - newTgv, held_paris: (P0.journeys - P.journeys) * GT, held_cross: heldCross, net_new: newTgv, new_paris: P.journeys * GT, new_cross: crossNew * GT,
                paying: payingParis + cross, charge_gross: gross, charge_paris: payingParis * d.charge_end / 1000, charge_cross: gross - payingParis * d.charge_end / 1000,
                gain_paris_euro: P.pay_gain * base.vot_ld / 60, gain_paris_all_euro: -P.minutes * base.vot_ld / 60,
                gain_cross_euro: T.ben_cross * 1000 / (T.cross_base + T.cross_new / 2) };
    // regional passengers
    const passHolders = T.new_transilien * GT * d.navigo_new / base.pass_trips;
    const navigo = passHolders * base.navigo_pass / 1000, ter = T.new_ter * GT * base.ter_yield / 1000, regPax = T.reg_pax * GT;
    const shops = (paris + cross + regPax) * base.shop_fee * d.shop_net / 1000;
    const fee = L.fee_km * base.auth_fee;
    const fleet = (base.sets[0] + base.sets[1]) / 2 * base.set_year * d.fleet_capture;
    const rex = (T.rex_second * d.rex_second + T.rex_through * d.rex_through) * GT / 1000;
    const rev = { 'Charge on high-speed passengers': gross, 'Track charges on new TGV journeys': track, 'New Navigo pass holders': navigo,
                  'Fares from new regional express passengers': ter, 'Fee paid by the regional transport authority': fee, 'Shops in the new station halls': shops };
    if (fleet) rev['Share of the operators’ saving on trainsets'] = fleet;
    if (rex) rev['Charge on regional express passengers'] = rex;
    out.ops_rev = rev; out.ops_rev_total = sum(rev);
    out.ops_balance = out.ops_rev_total - out.ops_cost_total; out.ops_cover = out.ops_rev_total / out.ops_cost_total;
    out.ops_cover_before_renewal = out.ops_rev_total / (out.ops_cost_total - renewal);
    out.charge_cover = gross / out.ops_cost_total;
    out.pass_holders = passHolders * 1e6;
    // capital account
    const payroll = d.payroll_pts / 0.1 * base.payroll_01, eu = d.eu_grant * K * A;
    out.cap_sources = { 'Surplus of the operations account': Math.max(0, out.ops_balance), 'Regional business tax package': d.levy,
                        'Payroll transport levy': payroll, 'European grant': eu };
    out.cap_sources_total = sum(out.cap_sources);
    out.cap_need = out.annuity + Math.max(0, -out.ops_balance);
    out.cap_gap = out.cap_need - out.cap_sources_total;
    const cap = function (yearly) { return yearly / A / K; };          // a yearly amount over 60 years as money paid during the works
    out.grant_bn = cap(out.cap_gap); out.grant_share = out.grant_bn / capex;
    out.shortfall_bn = cap(Math.max(0, -out.ops_balance)); out.levy_bn = cap(d.levy + payroll);
    out.public_bn = Math.max(0, out.grant_bn) + out.levy_bn + d.eu_grant; out.public_share = out.public_bn / capex;
    out.yearly_cost = out.annuity + out.ops_cost_total;
    // economic return
    const heldBen = heldCross * T.eq_cross / 120 * base.vot_ld / 1000;
    out.benefits = { 'Time saved by TGV passengers from the Paris region': P.benefit * G, 'Time saved by TGV passengers crossing Paris': T.ben_cross * G - heldBen * G / GT,
                     'Time saved by regional passengers': T.ben_regional * G, 'Comfort on relieved metro and RER lines': T.ben_comfort * G,
                     'Wider effects: urban form': T.wider_urban * G, 'Wider effects: productivity of denser job markets': T.wider_agglo * G, 'Wider effects: employment': T.wider_employment * G };
    out.benefit_total = sum(out.benefits);
    out.benefit_time = out.benefits['Time saved by TGV passengers from the Paris region'] + out.benefits['Time saved by TGV passengers crossing Paris'] + out.benefits['Time saved by regional passengers'];
    out.benefit_transport = out.benefit_time + T.ben_comfort * G;
    out.econ_cover_capital = out.benefit_total / out.annuity; out.econ_cover_all = out.benefit_total / out.yearly_cost;
    out.econ_cover_transport = out.benefit_transport / out.yearly_cost;
    const net = out.yearly_cost - out.ops_rev_total;          // cost net of income, as British appraisals count it
    out.econ_cover_net = net > 0 ? out.benefit_total / net : null; out.econ_cover_transport_net = net > 0 ? out.benefit_transport / net : null;
    // what public budgets get back: 'low' none of the added activity is new for the country; 'central' as the appraisal counts it; 'high' every job is new and fully taxed
    const X = base.tax, mode = d.tax_wider, votBiz = X.vot_business * base.vot_ld / X.vot_all;
    const hours = (T.clock_access * (T.paris_base + P.journeys / 2) + T.clock_cross * (T.cross_base + crossNew / 2)) / 60;
    const workOutput = X.business_pax * hours * votBiz / 1000 * G, jobs = T.wider_employment / X.job_value;
    const ticket = ((P.journeys + 2 * crossNew) * GT * fare + navigo * 1000 + ter * 1000) / 1000 * X.vat;
    const fuel = -newTgv * X.from_car * X.trip_km * X.litres_km / X.car_occupancy * X.fuel_duty / 1000;
    const on = mode === 'low' ? 0 : 1;
    out.tax = { 'VAT inside the new ticket money': ticket, 'Fuel duty lost on car trips moved to rail': fuel, 'Tax on output from working time saved': workOutput * X.gdp_share * on,
                'Tax on the productivity of denser job markets': T.wider_agglo * G * X.gdp_share * on,
                'Public money saved or raised by extra employment': mode === 'high' ? jobs * X.gdp_per_job * X.gdp_share * G : T.wider_employment * G * on };
    out.tax_total = sum(out.tax); out.tax_share_of_annuity = out.tax_total / out.annuity; out.tax_pv = cap(out.tax_total);
    out.works_return = X.works_return.map(function (sh) { return capex * sh; });
    out.jobs = jobs; out.work_output = workOutput;
    return out;
  };

  /* Lowest charge per Paris trip end (through passengers pay double) at which operations are covered; null if above 40 euros. */
  M.breakevenCharge = function (o) {
    for (let i = 0; i <= 4000; i++) { const ch = i * 0.01; if (M.accounts(Object.assign({}, o, { charge_end: ch, charge_through: 2 * ch })).ops_balance >= 0) return ch; }
    return null;
  };
})();
