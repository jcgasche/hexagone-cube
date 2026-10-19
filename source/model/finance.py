"""Financial accounts of the plan (three TGV through stations on a triangle, one tunnel for each kind of train, Saint-Lazare for line H).

Builds on nordest.py (access, traffic, cost) and adds:
- a charge on high-speed passengers who use what the project adds: 2.55 euros for boarding or leaving at a Paris station their line
  did not serve before, 5.10 for crossing Paris. The historic station of each line keeps today's price, so a Paris-region passenger pays
  only by choosing the other station, when the time it saves is worth more than the charge; passengers who cross Paris weigh the
  charge against the changes and time saved (response of traffic to fares);
- a charge on regional express passengers who use the second station (2.55) or cross Paris (5.10); none on suburban trains, which the
  Navigo pass and the regional ticket already cover;
- new Navigo pass holders on the joined suburban lines;
- station shops, the fee of the regional transport authority, half of the operators' saving on trainsets, optional sources;
- two accounts: running the project (operations) and repaying its construction (capital);
- what public budgets get back, in layers;
- a ratio of benefits to costs over 60 years, and a rate of return, to set beside other projects.

accounts(base, opts) is pure arithmetic on the `base` dictionary, so that src/js/model.js can repeat it exactly
(tools/check_model.js compares the two). Every assumption that is not sourced is marked ASSUMPTION.

Version 3.4 (14 October 2026): the charge falls only on new uses (another station than the line's own, crossing Paris), so no
journey is lost against today; crossing traffic grows as the changes of vehicle in Paris are removed, averaged over the main
destinations of the four lines (nordest.destinations); a passenger crossing Paris counts two fares in the track charges.
Version 3 (13 October 2026): one layout, the triangle; land is not sold (it becomes parks, not valued here); the regional express
charge replaces the flat supplement; the trainset saving is in the central case at half; a ratio on cost net of income is added for
comparison with British appraisals. Earlier: tunnel upkeep set between the two French benchmarks, with a low and a high case; no VAT
on the charges; public return in three readings; traffic growth applied to existing passengers too; public money shown in full.
"""
import json, os
import nordest as N
from estimate import HS_TERMINALS, FARE, VOT_LD

M = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')

# ------------------------------------------------------------------ parameters
CHARGE_END = 2.55            # euros per high-speed departure or arrival at a Paris station (price of a metro ticket in 2026)
CHARGE_THROUGH = 5.10        # euros for a passenger who crosses Paris on a direct train
REX_SECOND = 2.55            # euros per regional express passenger who gets off at the second station (the price of a metro ticket they no longer buy)
REX_THROUGH = 5.10           # euros per regional express passenger who crosses Paris without stopping
FARE_RESPONSE_LOW = -0.5     # response of traffic to fares under yield management, as suggested by the same source as the central -0.7
NAVIGO_PASS = 998.80         # euros, annual all-zone pass, 2026
PASS_TRIPS = 420             # rail journeys a year made by one regular commuter on the line (ASSUMPTION: 2 a day, 210 days)
NAVIGO_NEW = 0.30            # share of the new suburban journeys made by people who buy a pass because of the project
                             # (ASSUMPTION; share of journeys new to public transport: London 9% to 10%, Sydney 27%, East London line 28% to 32%)
TER_YIELD = 8.0              # euros per new regional express journey (ASSUMPTION)
SHOP_FEE = 0.19              # euros of shop rent per traveller in a rebuilt Paris station (Montparnasse contract, 2021, guaranteed minimum, derived)
SHOP_NET = 0.5               # share of that rent that is new, not moved from the shops of the surface halls (ASSUMPTION)
AUTH_FEE = 0.0008            # bn euros per km of line and year paid by the regional transport authority (Grand Paris Express rule)
SET_YEAR = 3.1e-3            # bn euros a year to own and maintain one high-speed trainset (2.7 to 3.5 m, derived from an old maintenance figure)
SETS = (12, 22)              # trainsets freed when trains stop turning round in Paris (derived)
FLEET_CAPTURE = 0.5          # share of that saving recovered through a higher track or station charge (ASSUMPTION, to negotiate)
STATION_LOW = 0.7            # low case for the running cost of stations: part of it is already paid for in today's terminals (ASSUMPTION)
TAX = {'gdp_share': 0.436,   # taxes and social contributions as a share of GDP, France 2025 (INSEE)
       'vat': 10 / 110,      # VAT inside a rail ticket price (10% rate)
       'business_pax': 0.30, # share of TGV passengers travelling for work (unverified press figure)
       'vot_business': 46.1, 'vot_all': 27.9,      # official values of time, long-distance rail, euros of 2015 per hour
       'job_value': 1e-5,    # bn euros a year per job in the appraisal of the Grand Paris Express: 10,000 euros of unemployment benefits saved
       'gdp_per_job': 123220e-9,                   # bn euros of output per job in Ile-de-France, 2024 (INSEE)
       'fuel_duty': 0.61,    # euros per litre of petrol (ASSUMPTION)
       'from_car': 0.25, 'trip_km': 450, 'litres_km': 0.06, 'car_occupancy': 2.2,      # ASSUMPTION
       'works_return': (0.40, 0.60)}                # share of debt-financed public investment that returns to public budgets in 5 years (OFCE)
GROWTH = 0.015               # yearly real growth of benefits used for the 60-year ratio (ASSUMPTION)
TRAFFIC_GROWTH_SHARE = 0.6   # part of that growth that is more passengers; the rest is the value of time rising with incomes (ASSUMPTION)
LEVY = 0.90                  # bn a year: a regional business tax package the size of the Grand Paris Express one, from opening
PAYROLL_01 = 0.16            # bn a year per 0.1 point of payroll transport levy in Paris and the inner ring
EU_GRANT = 1.0               # bn, paid during the works
PARK_HA = N.PARK_HA          # hectares of railway land that become parks; nothing is sold and no value is counted yet (study point I19)


def traffic(**kw):
    """Quantities of one traffic case, from nordest.py."""
    Y = N.yearly(**kw)
    w = Y['wider']; g = N.GPE; ws = g['urban'] + g['agglomeration'] + g['employment']
    reg = N.regional(kw.get('uplift', N.REG_UPLIFT), realise=kw.get('realise', 1.0))
    k = N.connecting(kw.get('c'), kw.get('evidence', N.UPLIFT_DIRECT), direct_share=kw.get('direct_share', N.DIRECT_SHARE), method=kw.get('method', 'changes'))
    ds = kw.get('direct_share', N.DIRECT_SHARE)
    clock_cross = sum(p['share'] * ((ds * (p['old_clock'] - p['direct']) + (1 - ds) * (p['old_clock'] - p['change_clock'])) if p['served'] else (p['old_clock'] - p['change_clock']))
                      for p in k['pairs'].values())
    return {'paris_base': HS_TERMINALS - 2 * Y['conn_base'], 'paris_new': Y['tgv_access_journeys'], 'cross_base': Y['conn_base'], 'cross_new': Y['tgv_conn_journeys'],
            'direct_share': Y['tgv_direct_share'], 'new_transilien': reg['new_transilien'], 'new_ter': reg['new_ter'],
            'reg_pax': (Y['reg_base'] + Y['reg_journeys']) * Y['reg_users'] / Y['reg_base'],
            'rex_second': reg['second_station_ter'], 'rex_through': reg['through_ter'], 'sub_second': reg['second_station_sub'],
            'clock_access': -N.access('clock', measure=kw.get('measure', 'station'))['all'], 'clock_cross': clock_cross, 'eq_access': -Y['tgv_access_min'], 'eq_cross': Y['tgv_conn_saving'],
            'ben_access': Y['tgv_access_benefit'], 'ben_cross': Y['tgv_conn_benefit'], 'ben_regional': Y['reg_benefit'], 'ben_comfort': Y['comfort'],
            'wider_urban': w * g['urban'] / ws, 'wider_agglo': w * g['agglomeration'] / ws, 'wider_employment': w * g['employment'] / ws,
            'measure': kw.get('measure', 'station'), 'cross_parts': [[x['q'], x['mult'], 1 if x['through'] else 0] for x in k['parts']]}


def make_base():
    levels = (('low', N.RATE_LOW), ('central', N.RATE), ('high', N.RATE_HIGH))
    f_sys = lambda R: (1 + R['design'] + R['client']) * (1 + R['risk'])
    c = {lv: N.cost(R) for lv, R in levels}; cc = c['central']
    om = lambda t, st: cc['tunnel_km'] * t + cc['platform_total'] * N.OM_STATION * st
    lay = {'capex': {lv: v['total'] for lv, v in c.items()}, 'systems': {lv: c[lv]['items']['Tunnels, rail systems'] * f_sys(R) for lv, R in levels},
                    'tunnel_km': cc['tunnel_km'], 'platform_m': cc['platform_total'], 'fee_km': N.FEE_KM,
                    'om_low': om(N.OM_TUNNEL_LOW, STATION_LOW) / om(N.OM_TUNNEL, 1.0), 'om_high': om(N.OM_TUNNEL_HIGH, 1.0) / om(N.OM_TUNNEL, 1.0),
                    'items': cc['items'], 'hard': cc['hard'], 'soft': cc['soft'], 'land': cc['land'], 'risk': cc['risk'],
                    'stations': cc['detail'], 'station_m': cc['platform_m'], 'tracks': cc['tracks']}
    tr = {'central': traffic(),
          'high': traffic(direct_share=1.0, uplift=N.REG_UPLIFT_HIGH),
          'low': traffic(method='single', uplift=N.REG_UPLIFT_LOW),
          'ride': traffic(measure='ride')}
    curves = {m: N.access_curve(measure=m) for m in ('station', 'ride')}
    cost_def = {'rates': {'low': N.RATE_LOW, 'central': N.RATE, 'high': N.RATE_HIGH}, 'link_km': N.LINK_KM, 'len': N.LEN, 'layout': N.LAYOUT,
                'corridor_km': N.CORRIDOR_KM, 'tunnels': N.TUNNELS, 'tunnel_km': N.TUNNEL_KM, 'fee_km': N.FEE_KM}
    return {'cost_def': cost_def, 'r': N.r_, 'n': N.n_, 'build_years': N.BUILD_YEARS, 'renew_year': N.RENEW_YEAR, 'fare': FARE, 'track_share': N.TRACK_SHARE, 'fare_response': N.FARE_RESPONSE,
            'layout': lay, 'om': {'tunnel': N.OM_TUNNEL, 'station': N.OM_STATION, 'trains': N.REG_TRAINKM * N.REG_TRAINKM_COST / 1000 + N.G_STOP_RUN},
            'traffic': tr, 'access_curve': curves, 'park_ha': PARK_HA, 'rex_second': REX_SECOND, 'rex_through': REX_THROUGH,
            'navigo_pass': NAVIGO_PASS, 'pass_trips': PASS_TRIPS, 'ter_yield': TER_YIELD, 'shop_fee': SHOP_FEE, 'shop_net': SHOP_NET, 'auth_fee': AUTH_FEE,
            'set_year': SET_YEAR, 'sets': SETS, 'tax': TAX, 'vot_ld': VOT_LD, 'levy': LEVY, 'payroll_01': PAYROLL_01, 'eu_grant': EU_GRANT, 'growth': GROWTH,
            'traffic_growth_share': TRAFFIC_GROWTH_SHARE,
            'defaults': {'cost': 'central', 'traffic': 'central', 'charge_end': CHARGE_END, 'charge_through': CHARGE_THROUGH, 'rex_second': REX_SECOND, 'rex_through': REX_THROUGH,
                         'fare_response': N.FARE_RESPONSE, 'navigo_new': NAVIGO_NEW, 'om_scale': 1.0, 'rate': N.r_, 'growth': 0.0, 'fleet_capture': FLEET_CAPTURE, 'shop_net': SHOP_NET, 'levy': LEVY, 'payroll_pts': 0.0,
                         'eu_grant': EU_GRANT, 'tax_wider': 'central'}}


def af(r, n): return r / (1 - (1 + r) ** -n)
def idc(r, years): return sum((1 + r) ** (k + 0.5) for k in range(years)) / years
def grow_factor(g, r, n):
    """Level yearly amount with the same present value as an amount that starts at 1 in the first year and grows g a year, over n years."""
    if abs(g) < 1e-9: return 1.0
    if abs(r - g) < 1e-9: return n / (1 + r) * af(r, n)
    q = (1 + g) / (1 + r)
    return (1 - q ** n) / (1 - q) / (1 + r) * af(r, n)


def at_charge(curve, charge):
    """Paris-region response at one level of charge, by straight lines between the tabulated levels (nordest.access_curve)."""
    rows, step = curve['rows'], curve['step']
    x = max(0.0, charge) / step; i = min(int(x), len(rows) - 2); w = x - i
    return {k: rows[i][j] + (rows[i + 1][j] - rows[i][j]) * w for j, k in enumerate(curve['cols'])}


def accounts(base, o=None):
    """The two accounts, the economic return and the public return, for one set of choices. bn euros a year unless stated."""
    d = dict(base['defaults']); d.update(o or {})
    L = base['layout']; T = base['traffic'][d['traffic']]; r, n = d['rate'], base['n']
    A = af(r, n); K = idc(r, base['build_years'])
    G = grow_factor(d['growth'], r, n)                                       # benefits: more passengers and a rising value of time
    GT = grow_factor(d['growth'] * base['traffic_growth_share'], r, n)       # passengers only
    capex = L['capex'][d['cost']]
    out = {'capex': capex, 'idc': K, 'af': A, 'grow': G, 'grow_traffic': GT, 'annuity': capex * K * A}
    # ---- operations: costs (held flat in real terms)
    om_infra = (L['tunnel_km'] * base['om']['tunnel'] + L['platform_m'] * base['om']['station']) * d['om_scale']
    renewal = L['systems'][d['cost']] / (1 + r) ** base['renew_year'] * A
    out['ops_cost'] = {'Running and maintaining tunnels and stations': om_infra, 'Extra running of regional trains': base['om']['trains'], 'Renewal of rail systems, set aside each year': renewal}
    out['ops_cost_total'] = sum(out['ops_cost'].values())
    # ---- high-speed passengers and the charge. Only new uses pay: a Paris-region passenger who boards or leaves at a station their
    #      line did not serve (the historic station keeps today's price), and a passenger who crosses Paris. No journey is lost against today.
    fare, resp = base['fare'], d['fare_response']
    P0, P = at_charge(base['access_curve'][T['measure']], 0.0), at_charge(base['access_curve'][T['measure']], d['charge_end'])
    paris = (T['paris_base'] + P['journeys']) * GT; paying_paris = paris * P['pay']
    ff = lambda charge: (1 + charge / (2 * fare)) ** resp                # a crossing trip is two TGV fares
    through = change = 0.0                                               # a plain loop, not sum(), so that src/js/model.js adds in the same way
    for q, m, t in T['cross_parts']:
        if t: through += q * m * ff(d['charge_through'])
        else: change += q * m * ff(2 * d['charge_end'])
    through *= GT; change *= GT
    cross = through + change; cross_new = cross / GT - T['cross_base']
    gross = (paying_paris * d['charge_end'] + through * d['charge_through'] + change * 2 * d['charge_end']) / 1000
    new_tgv = (P['journeys'] + cross_new) * GT
    new_before = (P0['journeys'] + T['cross_new']) * GT
    held_cross = (T['cross_new'] - cross_new) * GT
    track = (P['journeys'] + 2 * cross_new) * GT * fare * base['track_share'] / 1000          # track charges on the new journeys; a crossing trip pays two fares
    out['tgv'] = {'paris': paris, 'cross': cross, 'through': through, 'change': change, 'paying_paris': paying_paris, 'pay_share': P['pay'], 'new_before_charge': new_before,
                  'held': new_before - new_tgv, 'held_paris': (P0['journeys'] - P['journeys']) * GT, 'held_cross': held_cross, 'net_new': new_tgv, 'new_paris': P['journeys'] * GT, 'new_cross': cross_new * GT,
                  'paying': paying_paris + cross, 'charge_gross': gross, 'charge_paris': paying_paris * d['charge_end'] / 1000, 'charge_cross': gross - paying_paris * d['charge_end'] / 1000,
                  'gain_paris_euro': P['pay_gain'] * base['vot_ld'] / 60, 'gain_paris_all_euro': -P['minutes'] * base['vot_ld'] / 60,
                  'gain_cross_euro': T['ben_cross'] * 1000 / (T['cross_base'] + T['cross_new'] / 2)}
    # ---- regional passengers
    pass_holders = T['new_transilien'] * GT * d['navigo_new'] / base['pass_trips']                # million new pass holders
    navigo = pass_holders * base['navigo_pass'] / 1000
    ter = T['new_ter'] * GT * base['ter_yield'] / 1000
    reg_pax = T['reg_pax'] * GT
    shops = (paris + cross + reg_pax) * base['shop_fee'] * d['shop_net'] / 1000
    fee = L['fee_km'] * base['auth_fee']
    fleet = sum(base['sets']) / 2 * base['set_year'] * d['fleet_capture']
    rex = (T['rex_second'] * d['rex_second'] + T['rex_through'] * d['rex_through']) * GT / 1000     # no response of traffic modelled (ASSUMPTION)
    rev = {'Charge on high-speed passengers': gross, 'Track charges on new TGV journeys': track, 'New Navigo pass holders': navigo,
           'Fares from new regional express passengers': ter, 'Fee paid by the regional transport authority': fee, 'Shops in the new station halls': shops}
    if fleet: rev['Share of the operators’ saving on trainsets'] = fleet
    if rex: rev['Charge on regional express passengers'] = rex
    out['ops_rev'] = rev; out['ops_rev_total'] = sum(rev.values())
    out['ops_balance'] = out['ops_rev_total'] - out['ops_cost_total']; out['ops_cover'] = out['ops_rev_total'] / out['ops_cost_total']
    out['ops_cover_before_renewal'] = out['ops_rev_total'] / (out['ops_cost_total'] - renewal)
    out['charge_cover'] = gross / out['ops_cost_total']
    out['pass_holders'] = pass_holders * 1e6
    # ---- capital account
    payroll = d['payroll_pts'] / 0.1 * base['payroll_01']
    eu = d['eu_grant'] * K * A
    src = {'Surplus of the operations account': max(0.0, out['ops_balance']), 'Regional business tax package': d['levy'],
           'Payroll transport levy': payroll, 'European grant': eu}
    need = out['annuity'] + max(0.0, -out['ops_balance'])
    out['cap_sources'] = src; out['cap_sources_total'] = sum(src.values()); out['cap_need'] = need
    out['cap_gap'] = need - out['cap_sources_total']
    cap = lambda yearly: yearly / A / K                               # a yearly amount over 60 years as money paid during the works
    out['grant_bn'] = cap(out['cap_gap']); out['grant_share'] = out['grant_bn'] / capex
    out['shortfall_bn'] = cap(max(0.0, -out['ops_balance'])); out['levy_bn'] = cap(d['levy'] + payroll)
    out['public_bn'] = max(0.0, out['grant_bn']) + out['levy_bn'] + d['eu_grant']; out['public_share'] = out['public_bn'] / capex
    out['yearly_cost'] = out['annuity'] + out['ops_cost_total']
    # ---- economic return (benefits to society, a year)
    held_ben = held_cross * T['eq_cross'] / 120 * base['vot_ld'] / 1000                # new crossing journeys the charge holds back lose the half-gain of the rule of a half
    ben = {'Time saved by TGV passengers from the Paris region': P['benefit'] * G, 'Time saved by TGV passengers crossing Paris': T['ben_cross'] * G - held_ben * G / GT,
           'Time saved by regional passengers': T['ben_regional'] * G, 'Comfort on relieved metro and RER lines': T['ben_comfort'] * G,
           'Wider effects: urban form': T['wider_urban'] * G, 'Wider effects: productivity of denser job markets': T['wider_agglo'] * G, 'Wider effects: employment': T['wider_employment'] * G}
    out['benefits'] = ben; out['benefit_total'] = sum(ben.values())
    out['benefit_time'] = ben['Time saved by TGV passengers from the Paris region'] + ben['Time saved by TGV passengers crossing Paris'] + ben['Time saved by regional passengers']
    out['benefit_transport'] = out['benefit_time'] + T['ben_comfort'] * G
    out['econ_cover_capital'] = out['benefit_total'] / out['annuity']
    out['econ_cover_all'] = out['benefit_total'] / out['yearly_cost']
    out['econ_cover_transport'] = out['benefit_transport'] / out['yearly_cost']
    net = out['yearly_cost'] - out['ops_rev_total']                      # cost net of income, as British appraisals count it
    out['econ_cover_net'] = out['benefit_total'] / net if net > 0 else None; out['econ_cover_transport_net'] = out['benefit_transport'] / net if net > 0 else None
    # ---- what public budgets get back each year once the project is open. Three readings of how much of the added activity is new for the country:
    #      'low' none of it; 'central' as the appraisal that the ratios come from counts it; 'high' every job counted is new and pays the average rate of tax.
    X = base['tax']; mode = d['tax_wider']
    vot_biz = X['vot_business'] * base['vot_ld'] / X['vot_all']                                 # business value of time in today's money (derived)
    hours = (T['clock_access'] * (T['paris_base'] + P['journeys'] / 2) + T['clock_cross'] * (T['cross_base'] + cross_new / 2)) / 60     # million hours on the clock
    work_output = X['business_pax'] * hours * vot_biz / 1000 * G                                # output from working time saved, bn
    jobs = T['wider_employment'] / X['job_value']                                               # jobs implied by the employment line
    ticket = ((P['journeys'] + 2 * cross_new) * GT * fare + navigo * 1000 + ter * 1000) / 1000 * X['vat']      # VAT inside the new ticket money (none on the charges)
    fuel = -new_tgv * X['from_car'] * X['trip_km'] * X['litres_km'] / X['car_occupancy'] * X['fuel_duty'] / 1000
    on = 0.0 if mode == 'low' else 1.0
    tx = {'VAT inside the new ticket money': ticket, 'Fuel duty lost on car trips moved to rail': fuel,
          'Tax on output from working time saved': work_output * X['gdp_share'] * on,
          'Tax on the productivity of denser job markets': T['wider_agglo'] * G * X['gdp_share'] * on,
          'Public money saved or raised by extra employment': (jobs * X['gdp_per_job'] * X['gdp_share'] * G if mode == 'high' else T['wider_employment'] * G * on)}
    out['tax'] = tx; out['tax_total'] = sum(tx.values()); out['tax_share_of_annuity'] = out['tax_total'] / out['annuity']
    out['tax_pv'] = cap(out['tax_total'])                              # on the same footing as the grant: money during the works
    out['works_return'] = [capex * s for s in X['works_return']]
    out['jobs'] = jobs; out['work_output'] = work_output
    return out


def breakeven_charge(base, **o):
    """Charge per Paris trip end (through passengers pay double) at which operations are covered. None if above 40 euros."""
    for i in range(0, 4001):
        ch = i * 0.01
        if accounts(base, dict(o, charge_end=ch, charge_through=2 * ch))['ops_balance'] >= 0: return ch
    return None


def irr(base, **o):
    """Real rate of return of the whole project for society: construction spread evenly over the years of works, then 60 years of
    benefits (growing `growth` a year from the first year's value) less running costs, with one renewal of rail systems.
    Found by bisection; None if below -10%."""
    d = dict(base['defaults']); d.update(o)
    a = accounts(base, dict(o, growth=0.0)); L = base['layout']; yrs = base['build_years']; g = d.get('growth', 0.0)
    run = a['ops_cost']['Running and maintaining tunnels and stations'] + a['ops_cost']['Extra running of regional trains']
    def npv(r):
        v = -sum(a['capex'] / yrs * (1 + r) ** (k + 0.5) for k in range(yrs))
        v += sum((a['benefit_total'] * (1 + g) ** (t - 1) - run) / (1 + r) ** t for t in range(1, base['n'] + 1))
        return v - L['systems'][d['cost']] / (1 + r) ** base['renew_year']
    lo, hi = -0.10, 0.30
    if npv(lo) < 0: return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if npv(mid) > 0: lo = mid
        else: hi = mid
    return (lo + hi) / 2


CASES = {'central': {}, 'no_charge': dict(charge_end=0, charge_through=0, rex_second=0, rex_through=0), 'tgv_charge_only': dict(rex_second=0, rex_through=0, fleet_capture=0.0),
         'low_running': dict(om_scale='low'), 'high_running': dict(om_scale='high'),
         'shops_full': dict(shop_net=1.0), 'no_fleet': dict(fleet_capture=0.0), 'package_low_running': dict(shop_net=1.0, om_scale='low'),
         'growth': dict(growth=GROWTH), 'low_cost': dict(cost='low'), 'high_cost': dict(cost='high'), 'high_traffic': dict(traffic='high'), 'low_traffic': dict(traffic='low'),
         'ride': dict(traffic='ride'), 'best': dict(cost='low', traffic='high', growth=GROWTH), 'navigo_all': dict(navigo_new=1.0), 'navigo_low': dict(navigo_new=0.09),
         'tax_high': dict(tax_wider='high'), 'tax_low': dict(tax_wider='low'), 'rate45': dict(rate=0.045, growth=GROWTH), 'rate45_flat': dict(rate=0.045),
         'resp05': dict(fare_response=FARE_RESPONSE_LOW), 'charge_double': dict(charge_end=2 * CHARGE_END, charge_through=2 * CHARGE_THROUGH),
         'all_levers': dict(cost='low', traffic='high', growth=GROWTH, om_scale='low', shop_net=1.0)}


def resolve(base, o):
    """Named running-cost cases ('low', 'high') become the scale of the layout."""
    o = dict(o)
    if o.get('om_scale') in ('low', 'high'): o['om_scale'] = base['layout']['om_' + o['om_scale']]
    return o


if __name__ == '__main__':
    base = make_base()
    out = {'base': base, 'cases': {}, 'irr': {}}
    P = lambda x: round(x, 3) if isinstance(x, float) else x
    for name, o in CASES.items(): out['cases'][name] = accounts(base, resolve(base, o))
    out['cases']['breakeven_charge'] = breakeven_charge(base)
    out['cases']['breakeven_charge_low_running'] = breakeven_charge(base, **resolve(base, dict(om_scale='low')))
    out['cases']['breakeven_charge_high_running'] = breakeven_charge(base, **resolve(base, dict(om_scale='high')))
    out['cases']['breakeven_charge_tgv_only'] = breakeven_charge(base, rex_second=0, rex_through=0, fleet_capture=0.0)
    for name, o in {'central': {}, 'growth': dict(growth=GROWTH), 'low_cost': dict(cost='low'), 'best': dict(cost='low', traffic='high', growth=GROWTH)}.items():
        out['irr'][name] = irr(base, **o)
    out['charge_curve'] = []
    for i in range(0, 41):
        ch = i * 0.25; a = accounts(base, dict(charge_end=ch, charge_through=2 * ch))
        out['charge_curve'].append({'charge': ch, 'gross': a['tgv']['charge_gross'], 'paris': a['tgv']['charge_paris'], 'net_new': a['tgv']['net_new'], 'new_paris': a['tgv']['new_paris'],
                                    'new_cross': a['tgv']['new_cross'], 'pay_share': a['tgv']['pay_share'], 'ops_cover': a['ops_cover']})
    out['params'] = {'charge_end': CHARGE_END, 'charge_through': CHARGE_THROUGH, 'rex_second': REX_SECOND, 'rex_through': REX_THROUGH, 'fare_response_low': FARE_RESPONSE_LOW, 'navigo_new': NAVIGO_NEW,
                     'om_low': base['layout']['om_low'], 'om_high': base['layout']['om_high'], 'station_low': STATION_LOW, 'shop_net': SHOP_NET,
                     'growth': GROWTH, 'fleet_capture': FLEET_CAPTURE, 'park_ha': PARK_HA}
    os.makedirs(M, exist_ok=True); json.dump(out, open(f'{M}/finance.json', 'w'), indent=1)
    for k in ('central',):
        a = out['cases'][k]
        print('\n==', k, 'capex', P(a['capex']), 'annuity', P(a['annuity']), 'yearly', P(a['yearly_cost']))
        print(' ops cost', {x[:26]: P(v) for x, v in a['ops_cost'].items()}, P(a['ops_cost_total']))
        print(' ops rev ', {x[:26]: P(v) for x, v in a['ops_rev'].items()}, P(a['ops_rev_total']))
        print(' ops balance', P(a['ops_balance']), 'cover', P(a['ops_cover']), 'charge alone', P(a['charge_cover']), 'pass holders', round(a['pass_holders']))
        print(' tgv', {x: P(v) for x, v in a['tgv'].items()})
        print(' cap need', P(a['cap_need']), 'gap', P(a['cap_gap']), 'grant', P(a['grant_bn']), P(a['grant_share']), 'shortfall', P(a['shortfall_bn']), 'levy', P(a['levy_bn']), 'public', P(a['public_bn']), P(a['public_share']))
        print(' ben', P(a['benefit_total']), 'cover capital', P(a['econ_cover_capital']), 'all', P(a['econ_cover_all']), 'transport', P(a['econ_cover_transport']))
        print(' tax', {x[:30]: P(v) for x, v in a['tax'].items()}, P(a['tax_total']), P(a['tax_share_of_annuity']), 'pv', P(a['tax_pv']), 'jobs', round(a['jobs']), 'work', P(a['work_output']))
    print()
    for k, a in out['cases'].items():
        if isinstance(a, dict): print(k.ljust(28), 'ops', P(a['ops_cover']), 'bal', P(a['ops_balance']), '| econ', P(a['econ_cover_transport']), P(a['econ_cover_all']), '| tax', P(a['tax_total']), P(a['tax_share_of_annuity']), '| grant', P(a['grant_bn']), P(a['grant_share']), 'pub', P(a['public_share']), '| newTGV', P(a['tgv']['net_new']))
        else: print(k.ljust(28), a)
    print(out['irr']); print(out['params'])
    print('clock', {k: P(v) for k, v in base['traffic']['central'].items() if 'clock' in k or 'eq_' in k})
