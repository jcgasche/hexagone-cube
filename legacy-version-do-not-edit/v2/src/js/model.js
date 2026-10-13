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

  /* Cost of a layout from unit rates (bn euros of 2026). R: rates object, as base.cost_def.rates.central. */
  M.cost = function (layout, R) {
    const D = M.base().cost_def, L = D.layouts[layout];
    const networks = L.pairs + (L.tgv_extra_km ? 1 : 0), portals = D.radials * networks, junctions = 2 * networks;
    const km = D.route_km * L.pairs + L.tgv_extra_km;
    const plat = {}; let platTotal = 0;
    Object.keys(L.stations).forEach(function (n) { let m = 0; Object.keys(L.stations[n]).forEach(function (k) { m += L.stations[n][k] * D.len[k]; }); plat[n] = m; platTotal += m; });
    let halls = 0; L.halls.forEach(function (hname) { halls += R.hall[hname]; });
    const items = {
      'Tunnels, civil works': km * R.tunnel_civil, 'Tunnels, rail systems': km * R.tunnel_systems, 'Stations': platTotal * R.platform_m, 'Historic halls': halls,
      'Underground junctions': junctions * R.junction, 'Portals and links to existing lines': portals * R.portal, 'Sidings and depot links': R.sidings
    };
    let hard = 0; Object.keys(items).forEach(function (k) { hard += items[k]; });
    const soft = hard * (R.design + R.client), land = hard * R.land, risk = (hard + soft + land) * R.risk;
    return { tunnel_km: km, platform_m: plat, platform_total: platTotal, portals: portals, junctions: junctions, items: items, hard: hard, soft: soft, land: land, risk: risk, total: hard + soft + land + risk,
             systems: items['Tunnels, rail systems'] * (1 + R.design + R.client) * (1 + R.risk) };
  };

  /* The two accounts, the economic return and the public return for one set of choices. bn euros a year unless stated.
     o overrides base.defaults. o.capex and o.systems (bn) may replace the stored cost levels (used by the cost explorer).
     o.om_scale may be 'low' or 'high': the running-cost cases of that layout. */
  M.accounts = function (o) {
    const base = M.base(), d = Object.assign({}, base.defaults, o || {});
    const L = base.layouts[d.layout], T = base.traffic[d.traffic], r = d.rate, n = base.n;
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
    // high-speed passengers and the charge
    const fare = base.fare, resp = d.fare_response;
    const paris = (T.paris_base + T.paris_new) * GT, cross = (T.cross_base + T.cross_new) * GT;
    const through = cross * T.direct_share, change = cross * (1 - T.direct_share);
    const keep = function (charge) { return Math.pow(1 + charge / fare, resp); };
    const lostP = paris * (1 - keep(d.charge_end)), lostT = through * (1 - keep(d.charge_through)), lostC = change * (1 - keep(2 * d.charge_end));
    const gross = ((paris - lostP) * d.charge_end + (through - lostT) * d.charge_through + (change - lostC) * 2 * d.charge_end) / 1000;
    const lost = lostP + lostT + lostC, newTgv = (T.paris_new + T.cross_new) * GT, netTgv = newTgv - lost;
    const track = netTgv * fare * base.track_share / 1000;
    out.tgv = { paris: paris, cross: cross, through: through, change: change, lost_paris: lostP, lost_cross: lostT + lostC, lost: lost, new_before_charge: newTgv, net_new: netTgv,
                paying: paris + cross - lost, charge_gross: gross, charge_net: gross - lost * fare * base.track_share / 1000,
                gain_paris_euro: T.ben_access * 1000 / (T.paris_base + T.paris_new / 2), gain_cross_euro: T.ben_cross * 1000 / (T.cross_base + T.cross_new / 2) };
    // regional passengers
    const passHolders = T.new_transilien * GT * d.navigo_new / base.pass_trips;
    const navigo = passHolders * base.navigo_pass / 1000, ter = T.new_ter * GT * base.ter_yield / 1000, regPax = T.reg_pax * GT;
    const shops = (paris + cross - lost + regPax) * base.shop_fee * base.shop_net / 1000;
    const fee = L.fee_km * base.auth_fee;
    const fleet = (base.sets[0] + base.sets[1]) / 2 * base.set_year * d.fleet_capture;
    const supp = regPax * d.reg_supp / 1000;
    const rev = { 'Charge on high-speed passengers': gross, 'Track charges on the net change in TGV journeys': track, 'New Navigo pass holders': navigo,
                  'Fares from new regional express passengers': ter, 'Fee paid by the regional transport authority': fee, 'Shops in the new station halls': shops };
    if (fleet) rev['Share of the operators’ saving on trainsets'] = fleet;
    if (supp) rev['Supplement on regional journeys through the tunnels'] = supp;
    out.ops_rev = rev; out.ops_rev_total = sum(rev);
    out.ops_balance = out.ops_rev_total - out.ops_cost_total; out.ops_cover = out.ops_rev_total / out.ops_cost_total;
    out.ops_cover_before_renewal = out.ops_rev_total / (out.ops_cost_total - renewal);
    out.charge_cover = gross / out.ops_cost_total;
    out.pass_holders = passHolders * 1e6;
    // capital account
    const land = base.land_nominal / Math.pow(1 + r, base.land_delay) * A, payroll = d.payroll_pts / 0.1 * base.payroll_01, eu = d.eu_grant * K * A;
    out.cap_sources = { 'Surplus of the operations account': Math.max(0, out.ops_balance), 'Land released at the surface': land, 'Regional business tax package': d.levy,
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
    const dead = 0.5 * (lostP * d.charge_end + lostT * d.charge_through + lostC * 2 * d.charge_end) / 1000;
    out.benefits = { 'Time saved by TGV passengers from the Paris region': T.ben_access * G, 'Time saved by TGV passengers crossing Paris': T.ben_cross * G,
                     'Time saved by regional passengers': T.ben_regional * G, 'Comfort on relieved metro and RER lines': T.ben_comfort * G,
                     'Wider effects: urban form': T.wider_urban * G, 'Wider effects: productivity of denser job markets': T.wider_agglo * G, 'Wider effects: employment': T.wider_employment * G,
                     'Journeys given up because of the charge': -dead };
    out.benefit_total = sum(out.benefits);
    out.benefit_time = (T.ben_access + T.ben_cross + T.ben_regional) * G - dead;
    out.benefit_transport = out.benefit_time + T.ben_comfort * G;
    out.econ_cover_capital = out.benefit_total / out.annuity; out.econ_cover_all = out.benefit_total / out.yearly_cost;
    out.econ_cover_transport = out.benefit_transport / out.yearly_cost;
    // what public budgets get back: 'low' none of the added activity is new for the country; 'central' as the appraisal counts it; 'high' every job is new and fully taxed
    const X = base.tax, mode = d.tax_wider, votBiz = X.vot_business * base.vot_ld / X.vot_all;
    const hours = (T.clock_access * (T.paris_base + T.paris_new / 2) + T.clock_cross * (T.cross_base + T.cross_new / 2)) / 60;
    const workOutput = X.business_pax * hours * votBiz / 1000 * G, jobs = T.wider_employment / X.job_value;
    const ticket = (netTgv * fare + navigo * 1000 + ter * 1000 + supp * 1000) / 1000 * X.vat;
    const fuel = -Math.max(0, netTgv) * X.from_car * X.trip_km * X.litres_km / X.car_occupancy * X.fuel_duty / 1000;
    const on = mode === 'low' ? 0 : 1;
    out.tax = { 'VAT inside the net change in ticket money': ticket, 'Fuel duty lost on car trips moved to rail': fuel, 'Tax on output from working time saved': workOutput * X.gdp_share * on,
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
