"""Annex 'rerd': an option outside the plan. RER D gets its own pair of tracks beside the RER G tunnel between Gare du Nord and
Chatelet-Les Halles, so that RER B and D stop sharing one tunnel. This script prices the layouts at the study's unit prices
(nordest.RATE, RATE_LOW, RATE_HIGH), reads the train-by-train simulation of the section (model/rerd_trunk_sim.py ->
model/inputs/rerd_trunk_results.json) and values what each layout brings. Passengers come from the chapter 'flows'
(src/sections/flows/data.json). Nothing here enters the plan, its cost or its benefits.
Run from source/: python3 model/rerd.py   (after model/flows.py). Writes src/sections/rerd/data.json.
Everything marked ASSUMPTION is a judgement, not a measurement."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nordest import RATE, RATE_LOW, RATE_HIGH

SRC = os.path.join(HERE, '..', 'src', 'sections')
FL = json.load(open(os.path.join(SRC, 'flows', 'data.json')))
SIM = json.load(open(os.path.join(HERE, 'inputs', 'rerd_trunk_results.json')))

# ---------------------------------------------------------------- lengths and sizes
SUB_LEN = 225            # m, a suburban platform as in the study (RER D trains are about 224 m)
KM_NORD_CHATELET = 2.2   # km, Gare du Nord to Chatelet-Les Halles (the existing tunnel of RER B and D)
KM_SOUTH_LINK = 0.4      # km from the new Chatelet platforms to the existing RER D tubes towards Gare de Lyon (ASSUMPTION)
KM_NORTH_LINK = 0.5      # km from the RER D platforms of Gare du Nord into the RER G tunnel (shared layout only; ASSUMPTION)
KM_NORTH_RAMP = 1.2      # km of new tunnel from the present RER D tracks north of Gare du Nord down to Nord-Est (ASSUMPTION: 35 to 40 m deep at 35 mm per metre)
KM_CHATELET_LYON = 2.5   # km, Chatelet-Les Halles to Gare de Lyon (the RER D tunnel of 1995 is 2.5 km)
KM_SOUTH_RAMP = 1.5      # km from new platforms at Gare de Lyon up to the RER D tracks towards Villeneuve (ASSUMPTION)
R_FOLD_HARD = 0.10       # line R into the underground RER D platforms of Gare de Lyon: crossovers and platform works (ASSUMPTION)
K_FOLD_HARD = 0.10       # line K onto the RER B tracks, which it runs beside from Mitry-Claye to Gare du Nord: crossovers and platform works (ASSUMPTION)
K_PEAK, R_PEAK = 4, 5    # trains of lines K and R that reach Gare du Nord and Gare de Lyon in their busiest 60 minutes (IDFM timetable, Tuesday 3 November 2026)
B_PEAK, D_PEAK = 20, 12  # RER B and RER D trains an hour each way in the shared tunnel (timetable)


def items(layout, R):
    tun = R['tunnel_civil'] + R['tunnel_systems']
    plat = 2 * SUB_LEN * R['platform_m']                       # two platform tracks in a deep station
    tie = R['junction'] + R['portal']                          # an underground junction and the tie-in of a track pair to a line in service
    if layout == 'shared':        # RER D on the two tracks of RER G between Nord-Est and Chatelet
        return [('split', tie), ('chatelet', plat), ('tubes', tie), ('corridors', R['chatelet_links'] / 2),
                ('merges', 2 * R['junction']), ('tunnel', (KM_NORTH_LINK + KM_SOUTH_LINK) * tun), ('signals', 0.05)]
    if layout == 'own':           # its own pair beside RER G; RER D keeps its platforms at Gare du Nord
        return [('split', tie), ('chatelet', plat), ('tubes', tie), ('corridors', R['chatelet_links'] / 2),
                ('tunnel', (KM_NORD_CHATELET + KM_SOUTH_LINK) * tun)]
    if layout == 'moved':         # new RER D platforms at Nord-Est too: nothing is built under the Gare du Nord RER station
        return [('ramp', R['portal'] + KM_NORTH_RAMP * tun), ('nordest', plat), ('nordest_links', R['chatelet_links'] / 4),
                ('chatelet', plat), ('tubes', tie), ('corridors', R['chatelet_links'] / 2),
                ('tunnel', (KM_NORD_CHATELET + KM_SOUTH_LINK) * tun)]
    if layout == 'route':         # a whole new RER D route to Gare de Lyon and beyond: the kind of project studied in 2012-13
        return [('ramp', R['portal'] + KM_NORTH_RAMP * tun), ('nordest', plat), ('nordest_links', R['chatelet_links'] / 4),
                ('chatelet', plat), ('corridors', R['chatelet_links'] / 2),
                ('tunnel', (KM_NORD_CHATELET + KM_CHATELET_LYON) * tun),
                ('lyon', plat), ('lyon_links', R['chatelet_links'] / 2), ('south_ramp', R['portal'] + KM_SOUTH_RAMP * tun)]
    raise ValueError(layout)


def all_in(hard, R):
    return hard * (1 + R['design'] + R['client'] + R['land']) * (1 + R['risk'])


KM = {'shared': KM_NORTH_LINK + KM_SOUTH_LINK, 'own': KM_NORD_CHATELET + KM_SOUTH_LINK, 'moved': KM_NORTH_RAMP + KM_NORD_CHATELET + KM_SOUTH_LINK,
      'route': KM_NORTH_RAMP + KM_NORD_CHATELET + KM_CHATELET_LYON + KM_SOUTH_RAMP}
AF = 0.045 / (1 - 1.045 ** -60)        # a 60-year annuity at the State discount rate, as in the chapter on the economic return
cost = {}
for lay in ('shared', 'own', 'moved', 'route'):
    c = {lab: round(all_in(sum(v for _, v in items(lay, R)), R), 2) for lab, R in (('low', RATE_LOW), ('central', RATE), ('high', RATE_HIGH))}
    it = items(lay, RATE)
    c.update(hard=round(sum(v for _, v in it), 3), items={k: round(v, 3) for k, v in it}, km=round(KM[lay], 1),
             upkeep=round(KM[lay] * 0.0035 + 0.01, 3))                                 # tunnel upkeep at the study's high rate, plus a station's
    c['year'] = round(c['central'] * AF + c['upkeep'], 3)
    c['year_low'] = round(c['low'] * AF + c['upkeep'], 3); c['year_high'] = round(c['high'] * AF + c['upkeep'], 3)
    cost[lay] = c
cost['r_fold'] = {lab: round(all_in(R_FOLD_HARD, R), 2) for lab, R in (('low', RATE_LOW), ('central', RATE), ('high', RATE_HIGH))}
cost['k_fold'] = {lab: round(all_in(K_FOLD_HARD, R), 2) for lab, R in (('low', RATE_LOW), ('central', RATE), ('high', RATE_HIGH))}
cost['uplift'] = round((1 + RATE['design'] + RATE['client'] + RATE['land']) * (1 + RATE['risk']), 3)

# ---------------------------------------------------------------- earlier studies, for the comparison
INDEX_2013 = 1.30        # public works prices, 2013 to 2026 (ASSUMPTION: about 2% a year)
past = {'ratp03': {'value': 0.5, 'year': 2003, 'in2012': 0.7},                       # RATP 2003: a second twin-tube tunnel beside the first
        'rff13': {'low': 2.0, 'high': 3.5, 'wide_low': 1.3, 'wide_high': 3.8, 'year': 2013},    # RFF 2012-13: a new tunnel for RER D alone, four variants
        'index': INDEX_2013}
past['ratp03']['in2026'] = round(past['ratp03']['in2012'] * INDEX_2013, 1)
past['rff13'].update(low26=round(2.0 * INDEX_2013, 1), high26=round(3.5 * INDEX_2013, 1), wide_low26=round(1.3 * INDEX_2013, 1), wide_high26=round(3.8 * INDEX_2013, 1))

# ---------------------------------------------------------------- the simulation: seconds the section adds to a train
NAMES = {'plan': 'plan: B+D in the old tunnel, G alone', 'dg': 'D+G in the new tunnel, B alone in the old', 'bg': 'B+G in the new tunnel, D alone in the old',
         'half': 'mix: half the D in each tunnel', 'quarter': 'mix: a quarter of the D with the B, three quarters with the G', 'six': 'six tracks: B, D and G each alone'}
SCEN = {'today': 'today: B 20, D 12, G 12', 'growth': 'growth: B 24, D 16, G 16', 'growth_r': 'growth with line R in the D: B 24, D 20, G 16'}
k = FL['k']
RIDERS = {'B': k['line']['B'], 'D': k['line']['D'], 'G': FL['key']['pn']}      # passengers a working day (chapter 'flows'); G = lines P and N
PEAK, HIT = 0.45, 0.6        # share of journeys made in the two peaks; share of those aboard in the section or boarding after it (ASSUMPTION)
CANCEL_MIN = {'B': 4.0, 'D': 8.0, 'G': 6.0}     # minutes lost by a rider whose train is cancelled (ASSUMPTION: about half the interval of a branch)
W_LATE = (1.5, 2.0, 2.5)     # weight of a minute of lateness (ASSUMPTION)
VOT, DAYS = 15.0, 250        # euros an hour; working days a year


def delay_min(layout):
    """Minutes of delay a working day the section adds, all riders of the three lines."""
    tr = {l: 0.0 for l in RIDERS}; fq = {l: 0.0 for l in RIDERS}
    for pair in layout.values():
        for l, y in pair['lines'].items():
            tr[l] += y['freq'] * (y['added_s'] / 60 + y['cancelled_in_tunnel'] * CANCEL_MIN[l]); fq[l] += y['freq']
    return sum(RIDERS[l] * PEAK * HIT * tr[l] / fq[l] for l in RIDERS)


def pairs(layout):
    out = {}
    for name, pair in layout.items():
        out[name] = {'trains': pair['timetabled'], 'lines': {l: {'s': round(y['added_s']), 'cancelled': round(y['cancelled_in_tunnel'], 3)} for l, y in pair['lines'].items()}}
    return out


sim = {}
for sc, key in SCEN.items():
    d = SIM['scenarios'][key]; base = delay_min(d[NAMES['plan']]); sim[sc] = {}
    for lay, name in NAMES.items():
        m = delay_min(d[name]); works = all(y['cancelled_in_tunnel'] < 0.05 for p in d[name].values() for y in p['lines'].values())
        sim[sc][lay] = {'pairs': pairs(d[name]), 'delay_min': round(m, -3), 'saved_min': round(base - m, -3), 'works': works,
                        'reliability': [round((base - m) * w * VOT / 60 * DAYS / 1e9, 3) for w in W_LATE]}
ct = SIM['check_today']
sim['check'] = {'today_through': ct['old tunnel, 20 B + 12 D, today']['through'], 'nexteo_through': ct['old tunnel with NExTEO']['through'],
                'h_old': SIM['h_old_s'], 'h_new': SIM['h_new_s']}
pc = SIM['practical_capacity']; cap_rows = list(pc.values())
sim['capacity'] = {'bd': cap_rows[0], 'b_alone': cap_rows[1], 'dg': cap_rows[2], 'bg': cap_rows[3], 'one': cap_rows[4]}

# ---------------------------------------------------------------- what more trains are worth, where they can run
# With its own pair RER D can run about 16 to 20 trains an hour, and RER B alone in the old tunnel 24. Today the shared tunnel holds
# them at 20 and 12: the growth below is what the new pair makes possible, so it is counted as part of its value.
pk = {l: RIDERS[l] * PEAK for l in RIDERS}
wait = pk['B'] * 0.5 * 1.5 + pk['D'] * 1.0 * 1.5                        # minutes of waiting saved (B 3 min to 2.5 min, D 5 min to 3.75 min, half the interval), weight 1.5
crowd = pk['B'] * HIT * 20 * 0.12 + pk['D'] * HIT * 20 * 0.15           # 20 minutes aboard, crowding weight down 0.12 (B, loads -17%) and 0.15 (D, -25%) (ASSUMPTION)
g = (wait + crowd) * VOT / 60 * DAYS / 1e9
more = {'low': round(g * 0.5, 3), 'central': round(g, 3), 'high': round(g * 1.5, 3), 'wait': round(wait * VOT / 60 * DAYS / 1e9, 3)}

value = {}
for lay, cl in (('dg', 'shared'), ('six', 'own'), ('six', 'moved'), ('six', 'route')):
    rel = sim['today'][lay]['reliability']
    # with more trains: the delay of the layout at the larger service is set against the plan at today's service, the only one of the two that can run
    gained = sim['today']['plan']['delay_min'] - sim['growth'][lay]['delay_min']
    relg = [round(gained * w * VOT / 60 * DAYS / 1e9, 3) for w in W_LATE]
    c = cost[cl]
    value[cl] = {'reliability': rel[1], 'reliability_low': rel[0], 'reliability_high': rel[2],
                 'growth_reliability': relg[1], 'more_trains': more['central'],
                 'with_growth': round(relg[1] + more['central'], 3),            # delay saved at the larger service, plus the worth of the extra trains
                 'with_growth_low': round(relg[0] + more['low'], 3), 'with_growth_high': round(relg[2] + more['high'], 3),
                 'year': c['year'], 'ratio_today': round(rel[1] / c['year'], 2), 'ratio_growth': round((relg[1] + more['central']) / c['year'], 2),
                 'ratio_low': round((relg[0] + more['low']) / c['year_high'], 2), 'ratio_high': round((relg[2] + more['high']) / c['year_low'], 2)}

# ---------------------------------------------------------------- what a closure of RER D costs its riders
CUT_MIN, CUT_DAYS = 15.0, 300          # minutes lost by each rider of the section while RER D does not run through; days a year (ASSUMPTION)
cut = {'riders': k['d_bd'], 'min': CUT_MIN, 'year': round(k['d_bd'] * CUT_DAYS * CUT_MIN / 60 * VOT / 1e9, 2)}

G_PEAK = FL['k']['h']['g']
kr = {'k': K_PEAK, 'r': R_PEAK, 'b': B_PEAK, 'd': D_PEAK, 'g': G_PEAK, 'today': B_PEAK + D_PEAK, 'plan': B_PEAK + D_PEAK + G_PEAK, 'old': B_PEAK + K_PEAK, 'd_pair': D_PEAK + R_PEAK,
      'total': B_PEAK + K_PEAK + D_PEAK + R_PEAK + G_PEAK, 'added': G_PEAK + K_PEAK + R_PEAK, 'shared': D_PEAK + R_PEAK + G_PEAK}
out = {'cost': cost, 'past': past, 'sim': sim, 'more': more, 'value': value, 'cut': cut, 'kr': kr,
       'riders': RIDERS, 'params': {'peak': PEAK, 'hit': HIT, 'w_late': W_LATE[1], 'vot': VOT, 'days': DAYS, 'ramp_km': KM_NORTH_RAMP, 'south_link_km': KM_SOUTH_LINK,
                                    'nord_chatelet_km': KM_NORD_CHATELET, 'chatelet_lyon_km': KM_CHATELET_LYON, 'south_ramp_km': KM_SOUTH_RAMP, 'sub_len': SUB_LEN},
       'k': {'bd': k['bd'], 'b_bd': k['b_bd'], 'd_bd': k['d_bd'], 'g': k['g'], 'new_pairs': round(k['g'] + k['d_bd'], -3), 'd': k['line']['D'], 'b': k['line']['B'],
             'pn': round(FL['key']['pn'], -3), 'times': round(k['d_bd'] / k['g'], 1)}}
json.dump(out, open(os.path.join(SRC, 'rerd', 'data.json'), 'w'), indent=1)
for lay in ('shared', 'own', 'moved', 'route'): print(lay, cost[lay]['low'], cost[lay]['central'], cost[lay]['high'], 'hard', cost[lay]['hard'], 'year', cost[lay]['year'], value[lay])
print('past', past); print('more', more); print('cut', cut); print('k', out['k'])
for sc in ('today', 'growth', 'growth_r'): print(sc, {l: (v['delay_min'], v['works'], v['reliability'][1]) for l, v in sim[sc].items()})
print(sim['capacity'], sim['check'])
