"""Central-case cost and upside estimate, version 3 (after the second independent check, 11 October 2026).

Changes from version 2: one consumer-surplus rule used everywhere (rule of a half, correct sign); connecting passengers
modelled by pair of terminals, with the extra running time to the hub deducted; the Paris-region passenger count adjusts
when the connecting count changes; regional TER passengers valued at the interurban rate; hub passengers counted once;
fares lost on high-speed trains shown beside fares gained on regional trains; year 0 is opening day for every flow.
"""
import json, csv, statistics as S

import os
M = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inputs')      # model inputs: access times by point and by commune
ST = json.load(open(f'{M}/stats.json'))
RC = json.load(open(f'{M}/regional.json'))['agg']             # clock minutes
RW = json.load(open(f'{M}/regional_weighted.json'))['agg']    # equivalent minutes
from model import HS_PAX, TRAIN_DELTA
tot = sum(HS_PAX.values()); W = {k: v / tot for k, v in HS_PAX.items()}
VOT_LD, VOT_IDF, VOT_TER, ELAST = 35.0, 15.0, 31.0, -1.1
HS_TERMINALS = 112.5
ACC_EGR = 55.0                                                 # minutes of access and egress on an average trip
T_OLD, T_NEW = 57.5, 12.5                                      # change of station today, change at the hub (clock minutes)
CONN_TRAIN = 240.0                                             # minutes on trains for a typical connecting trip
FARE = 48.5


def gain(q0, new, minutes, vot):                               # value of a time saving, rule of a half for new passengers
    return (q0 * minutes / 60 + new * minutes / 120) * vot / 1000


def loss(q0, lost, minutes, vot):                              # value of a time loss; those who stop travelling lose half
    return (q0 * minutes / 60 - lost * minutes / 120) * vot / 1000


def paris(tag, col):
    R = list(csv.DictReader(open(f'{M}/points{tag}.csv')))
    today = [sum(W[k] * float(r['t_' + k]) for k in W) for r in R]
    return S.mean(float(r[col]) - t for r, t in zip(R, today)), S.mean(today)


E = {}
E['vot_ld'], E['vot_idf'], E['vot_ter'] = VOT_LD, VOT_IDF, VOT_TER

# ------------------------------------------------------------------ yearly cost (year 0 = opening day)
r, n = 0.03, 60
AF = r / (1 - (1 + r) ** -n)
E['capex'] = 33.0
E['annuity'] = E['capex'] * AF
E['track_km'] = 58 * 2 + 33.5 * 4
E['om_track'] = E['track_km'] * 1.15 / 1000
E['om_stations'] = 3 * 0.025
E['om_hub'] = 0.05
E['om'] = E['om_track'] + E['om_stations'] + E['om_hub']
E['annual_cost'] = E['annuity'] + E['om']

# ------------------------------------------------------------------ where trips start or end
pop = {k: RC[k]['pop'] for k in ('Paris', 'Petite couronne', 'Grande couronne')}
ptot = sum(pop.values())
VIS = {'Paris': 63 / 93, 'Petite couronne': 21 / 93, 'Grande couronne': 9 / 93}     # survey, visitors only
RES = {k: v / ptot for k, v in pop.items()}                                         # residents: by population (assumption)
SH = {k: 2 / 3 * VIS[k] + 1 / 3 * RES[k] for k in VIS}
E['tripend_shares'] = SH; E['tripend_visitors'] = VIS; E['tripend_residents'] = RES

d_clock_B, today_clock = paris('', 't_Pleyel_2031'); d_clock_C, _ = paris('', 't_Pleyel_prog')
d_eq_B, today_eq = paris('_weighted', 't_Pleyel_2031'); d_eq_C, _ = paris('_weighted', 't_Pleyel_prog')
E['paris_today_clock'], E['paris_today_eq'] = today_clock, today_eq
E['weight_ratio'] = today_eq / today_clock
ring = {'B': {'clock': {'Paris': d_clock_B, 'Petite couronne': RC['Petite couronne']['d1'], 'Grande couronne': RC['Grande couronne']['d1']},
              'eq': {'Paris': d_eq_B, 'Petite couronne': RW['Petite couronne']['d1'], 'Grande couronne': RW['Grande couronne']['d1']}},
        'C': {'clock': {'Paris': d_clock_C, 'Petite couronne': RC['Petite couronne']['d2'], 'Grande couronne': RC['Grande couronne']['d2']},
              'eq': {'Paris': d_eq_C, 'Petite couronne': RW['Petite couronne']['d2'], 'Grande couronne': RW['Grande couronne']['d2']}}}
E['ring'] = ring
E['train_delta'] = sum(W[k] * TRAIN_DELTA[k] for k in W)
AE_EQ = ACC_EGR * E['weight_ratio']
E['trip_eq'] = (212.0 - ACC_EGR) + AE_EQ                       # average Paris trip in equivalent minutes

# ------------------------------------------------------------------ connecting passengers, by pair of terminals
KEYS = ['Montparnasse', 'Lyon', 'Nord', 'Est']
PAIRS = [(a, b) for i, a in enumerate(KEYS) for b in KEYS[i + 1:]]
praw = {p: W[p[0]] * W[p[1]] for p in PAIRS}; psum = sum(praw.values())
PSH = {p: v / psum for p, v in praw.items()}                   # assumption: pairs in proportion to terminal traffic
E['pair_shares'] = {f'{a}-{b}': v for (a, b), v in PSH.items()}


def connecting(c, new_time, old_change_eq=2 * T_OLD):
    """c million connecting passengers; new_time(pair) = equivalent minutes replacing today's change of station."""
    out = {'new': 0.0, 'ben': 0.0, 'saving': 0.0}
    for p, s in PSH.items():
        old = CONN_TRAIN + old_change_eq + AE_EQ
        new = CONN_TRAIN + new_time(p) + AE_EQ
        up = (new / old) ** ELAST - 1
        out['new'] += c * s * up; out['saving'] += s * (old - new)
        out['ben'] += gain(c * s, c * s * up, old - new, VOT_LD)
    out['uplift'] = out['new'] / c
    return out


def hub_change(new_change_eq=2 * T_NEW):
    return lambda p: new_change_eq + TRAIN_DELTA[p[0]] + TRAIN_DELTA[p[1]]      # change at the hub plus extra running time


def hub(c, door_eq, shares=None, old_eq=2 * T_OLD, new_eq=2 * T_NEW):
    idf = HS_TERMINALS - 2 * c                                 # each connecting traveller passes two terminals
    k = connecting(c, hub_change(new_eq), old_eq)
    lost = idf * (1 - (1 + door_eq / E['trip_eq']) ** ELAST)
    cost = loss(idf, lost, door_eq, VOT_LD)
    return {'idf': idf, 'conn_new': k['new'], 'conn_ben': k['ben'], 'uplift': k['uplift'], 'saving': k['saving'], 'lost': lost, 'cost': cost,
            'net_pax': k['new'] - lost, 'net_ben': k['ben'] - cost}


def door(tag, shares=SH, kind='eq'):
    return sum(shares[k] * ring[tag][kind][k] for k in shares) + E['train_delta']


E['conn_base'] = 13000 * 350 / 1e6 * (112.5 / 86.9)
E['conn_base_high'] = 13000 * 435 / 1e6 * (112.5 / 86.9)
E['idf_tripends'] = HS_TERMINALS - 2 * E['conn_base']
E['conn_clock_saving'] = T_OLD - T_NEW
for tag in ('B', 'C'):
    E['access_clock_' + tag] = door(tag, SH, 'clock') - E['train_delta']
    E['access_eq_' + tag] = door(tag, SH, 'eq') - E['train_delta']
    E['door_clock_' + tag] = door(tag, SH, 'clock')
    E['door_eq_' + tag] = door(tag, SH, 'eq')
    h = hub(E['conn_base'], E['door_eq_' + tag])
    E['lost_' + tag], E['cost_access_' + tag] = h['lost'], h['cost']
    E['hub_net_pax_' + tag], E['hub_net_ben_' + tag] = h['net_pax'], h['net_ben']
    if tag == 'B':
        E['conn_new'], E['ben_conn'], E['conn_uplift'], E['conn_equiv_saving'] = h['conn_new'], h['conn_ben'], h['uplift'], h['saving']
E['conn_train_extra'] = sum(s * (TRAIN_DELTA[a] + TRAIN_DELTA[b]) for (a, b), s in PSH.items())
E['conn_trip_eq'] = CONN_TRAIN + 2 * T_OLD + AE_EQ
E['min_gained'] = E['conn_base'] * (E['conn_clock_saving'] - E['conn_train_extra'])
E['min_lost_B'] = E['idf_tripends'] * E['door_clock_B']
E['min_lost_C'] = E['idf_tripends'] * E['door_clock_C']
E['eqmin_gained'] = E['conn_base'] * E['conn_equiv_saving']
E['eqmin_lost_B'] = E['idf_tripends'] * E['door_eq_B']
E['eqmin_lost_C'] = E['idf_tripends'] * E['door_eq_C']


def bisect(f, lo, hi):
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) > 0: hi = mid
        else: lo = mid
    return lo


E['breakeven_eq_min'] = bisect(lambda d: -hub(E['conn_base'], d)['net_ben'], 0.0, 20.0)
E['breakeven_conn'] = bisect(lambda c: hub(c, E['door_eq_B'])['net_ben'], 1.0, 20.0)
E['pulse_upside'] = 21.9 * 0.6 * (156 / 117.2) * 0.125

# ------------------------------------------------------------------ regional through network
lines = {'H': 54.6, 'K': 4.1, 'P': 27.3, 'N': 27.3, 'R': 19.1}
E['reg_base_transilien'] = sum(lines.values())
E['reg_base_ter'] = (69200 + 23800 + 14900 + 8100) * 350 / 1e6
E['reg_base'] = E['reg_base_transilien'] + E['reg_base_ter']
E['reg_terminal_share'] = (119900 + 66800 + 63900 + 33000) / (215000 + 117000 + 105000 + 70000)   # terminal counts over line ridership
E['reg_benef_transilien'] = E['reg_base_transilien'] * E['reg_terminal_share']
E['reg_beneficiaries'] = E['reg_benef_transilien'] + E['reg_base_ter']
E['reg_uplift'] = 0.10
E['reg_new'] = E['reg_base'] * E['reg_uplift']
E['reg_min_saved'] = 5.0


def regional(minutes=5.0, uplift=0.10):
    return (gain(E['reg_benef_transilien'], E['reg_base_transilien'] * uplift, minutes, VOT_IDF)
            + gain(E['reg_base_ter'], E['reg_base_ter'] * uplift, minutes, VOT_TER))


E['ben_reg'] = regional()
E['rev_reg'] = (E['reg_base_transilien'] * E['reg_uplift'] * 1.39 + E['reg_base_ter'] * E['reg_uplift'] * 9.0) / 1000
GPE = {'time': 14.2, 'regularity': 4.6, 'comfort': 3.9, 'urban': 7.49, 'agglomeration': 11.3, 'employment': 19.6}
E['ratio_comfort'] = (GPE['regularity'] + GPE['comfort']) / GPE['time']
E['ratio_wider'] = (GPE['urban'] + GPE['agglomeration'] + GPE['employment']) / (GPE['time'] + GPE['regularity'] + GPE['comfort'])
E['ben_reg_comfort'] = E['ben_reg'] * E['ratio_comfort']       # scaled from the regional network's time savings only
E['ben_wider'] = (E['ben_reg'] + E['ben_reg_comfort']) * E['ratio_wider']

# ------------------------------------------------------------------ land and cash
E['land_gross_ha'], E['land_released_ha'], E['land_sold_ha'] = 200, 160, 80
E['land_price'] = 650 / 16
E['land_price_low'] = 650 / 26
E['land_nominal'] = E['land_sold_ha'] * E['land_price'] / 1000
E['land_year'] = 7                                             # years after opening
E['land_pv'] = E['land_nominal'] / (1 + r) ** E['land_year']
E['land_annual'] = E['land_pv'] * AF
E['land_nominal_low'] = E['land_sold_ha'] * E['land_price_low'] / 1000
E['land_annual_low'] = E['land_nominal_low'] / (1 + r) ** E['land_year'] * AF
E['hub_pax'] = E['idf_tripends'] - E['lost_B'] + E['conn_base'] + E['conn_new']       # each passenger counted once
E['fee'] = 33.5 * 0.8 / 1000
E['hs_fares_lost'] = -E['hub_net_pax_B'] * FARE / 1000
E['own_cash_gross'] = E['land_annual'] + E['rev_reg']
E['own_cash'] = E['own_cash_gross'] - E['hs_fares_lost']
E['own_cash_cover'] = E['own_cash'] / E['annual_cost']
E['own_cash_gross_cover'] = E['own_cash_gross'] / E['annual_cost']

# ------------------------------------------------------------------ benefit cover
E['user_ben_B'] = E['hub_net_ben_B'] + E['ben_reg']
E['cover_user'] = E['user_ben_B'] / E['annual_cost']
E['cover_comfort'] = (E['user_ben_B'] + E['ben_reg_comfort']) / E['annual_cost']
E['cover_wider'] = (E['user_ben_B'] + E['ben_reg_comfort'] + E['ben_wider']) / E['annual_cost']
E['cover_wider_on_net'] = E['user_ben_B'] * (1 + E['ratio_comfort']) * (1 + E['ratio_wider']) / E['annual_cost']
E['reg_cost'] = 13.4 / 33 * E['annuity'] + 134 * 1.15 / 1000 + E['om_stations']
E['hub_cost'] = 19.6 / 33 * E['annuity'] + 116 * 1.15 / 1000 + E['om_hub']
E['reg_cover_time'] = E['ben_reg'] / E['reg_cost']
E['reg_cover_wider'] = (E['ben_reg'] + E['ben_reg_comfort'] + E['ben_wider']) / E['reg_cost']

# ------------------------------------------------------------------ funding plan (yearly, bn)
stack = [('Regional business levy', 0.90, 'charge'), ('Hub charge, 2 euros per high-speed passenger', E['hub_pax'] * 2 / 1000, 'charge'),
         ('Operator fee for the regional tunnels', E['fee'], 'charge'), ('Land sales', E['land_annual'], 'own'),
         ('Fares from added regional journeys', E['rev_reg'], 'own'), ('European grant, 0.5 bn', 0.5 * AF, 'grant')]
E['stack'] = stack
E['stack_total'] = sum(v for _, v, _ in stack)
E['stack_cover'] = E['stack_total'] / E['annual_cost']
E['gap'] = E['annual_cost'] - E['stack_total']
E['gap_capital'] = E['gap'] / AF
E['levy_for_100'] = 0.90 + E['gap']

# ------------------------------------------------------------------ what would change the answer
mk = lambda rate, yrs: 33.0 * rate / (1 - (1 + rate) ** -yrs)
c0, d0 = E['conn_base'], E['door_eq_B']
pick = lambda h: {'hub_net_ben': h['net_ben'], 'hub_net_pax': h['net_pax']}
s = {}
s['cost_plus_50'] = {'annual_cost': E['annuity'] * 1.5 + E['om'], 'stack_cover': E['stack_total'] / (E['annuity'] * 1.5 + E['om'])}
s['regional_x3'] = {'capex': 33.0 + 2 * 13.4, 'annual_cost': (33.0 + 2 * 13.4) * AF + E['om'], 'reg_cover_time': E['ben_reg'] / ((3 * 13.4) * AF + 134 * 1.15 / 1000 + E['om_stations'])}
s['conn_half'] = pick(hub(c0 / 2, d0))
s['conn_high'] = pick(hub(E['conn_base_high'], d0))
s['conn_double'] = pick(hub(2 * c0, d0))
s['regional_stop'] = {'hub_net_ben': E['hub_net_ben_C'], 'hub_net_pax': E['hub_net_pax_C']}
s['res_by_pop'] = pick(hub(c0, door('B', RES)))               # every trip spread like the population
s['res_as_visitors'] = pick(hub(c0, door('B', VIS)))          # every trip spread like visitors' trips
# the change of station counted with the access model's own weights: 20 min in the metro, 20 walking, 17.5 waiting today; 5 walking, 7.5 waiting at the hub
s['change_low'] = pick(hub(c0, d0, old_eq=20 + 20 * 2 + 17.5 * 1.5, new_eq=5 * 2 + 7.5 * 1.5))
s['change_low']['saving'] = (20 + 40 + 26.25) - (10 + 11.25)
s['change_high'] = pick(hub(c0, d0, old_eq=120 + 2 * T_NEW))    # the bypass line review: two hours per avoided change
# clock minutes only, no weights anywhere
E_trip_clock = 212.0
def hub_clock():
    idf = HS_TERMINALS - 2 * c0; new = ben = 0.0
    for p, sh in PSH.items():
        old = CONN_TRAIN + T_OLD + ACC_EGR; nw = CONN_TRAIN + T_NEW + TRAIN_DELTA[p[0]] + TRAIN_DELTA[p[1]] + ACC_EGR
        up = (nw / old) ** ELAST - 1; new += c0 * sh * up; ben += gain(c0 * sh, c0 * sh * up, old - nw, VOT_LD)
    lost = idf * (1 - (1 + E['door_clock_B'] / E_trip_clock) ** ELAST)
    return {'hub_net_ben': ben - loss(idf, lost, E['door_clock_B'], VOT_LD), 'hub_net_pax': new - lost}
s['unweighted'] = hub_clock()
s['hub_deep_2min'] = pick(hub(c0, d0 + 4.0))                  # two more minutes of walking to deep platforms at the hub
s['reg_8min'] = {'ben_reg': regional(8.0)}
s['reg_15pct'] = {'reg_new': E['reg_base'] * 0.15, 'rev': (E['reg_base_transilien'] * 0.15 * 1.39 + E['reg_base_ter'] * 0.15 * 9.0) / 1000}
s['reg_ter_idf_rate'] = {'ben_reg': gain(E['reg_benef_transilien'], E['reg_base_transilien'] * 0.1, 5, VOT_IDF) + gain(E['reg_base_ter'], E['reg_base_ter'] * 0.1, 5, VOT_IDF)}
s['market_rate'] = {'service_57_40': mk(0.057, 40), 'service_35_40': mk(0.035, 40), 'real_3_40': mk(0.03, 40)}
s['hub_charge'] = {'fare_rise': 2 / FARE, 'lost': E['hub_pax'] * (1 - (1 + 2 / FARE) ** -0.7)}
s['hub_minute'] = {'per_minute': hub(c0, d0 + 2.0)['cost'] - hub(c0, d0)['cost']}      # one more minute of walking at the hub, counted double
s['land_low'] = {'nominal': E['land_nominal_low'], 'annual': E['land_annual_low']}
E['sens'] = s
os.makedirs(f'{M}/../outputs', exist_ok=True); json.dump(E, open(f'{M}/../outputs/estimate.json', 'w'), indent=1)
if __name__ == '__main__':
    for k, v in E.items():
        if isinstance(v, float): print(f'{k:22s} {v:10.3f}')
    print(json.dumps(E['pair_shares'])); print(json.dumps({k: {a: round(b, 3) for a, b in v.items()} for k, v in s.items()}, indent=0))
