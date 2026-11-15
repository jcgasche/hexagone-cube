"""Annex 'lc': a variant outside the plan. In place of RER F (Nord-Est to Saint-Lazare), line L runs under Paris to Chatelet-Les Halles
and Gare d'Austerlitz and takes the southern branches of RER C; the western branches of RER C turn north at Saint-Michel, stop at
Chatelet and run to Nord-Est, where they take line H. This script counts the trains on each pair of tracks, prices what the variant
builds and no longer builds at the study's unit prices (nordest.RATE, RATE_LOW, RATE_HIGH), and sets its cost beside the time it
saves. Travel times and passengers come from the chapter 'times' (model/regiontimes.py -> src/sections/times/data.json), the trains
that a pair of tracks can take from the annex 'rerd'. Nothing here enters the plan, its cost or its benefits.
Run from source/: python3 model/variantc.py   (after model/regiontimes.py export and model/rerd.py). Writes src/sections/lc/data.json.
Everything marked ASSUMPTION is a judgement, not a measurement."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from nordest import RATE, RATE_LOW, RATE_HIGH, CORRIDOR_KM

SRC = os.path.join(HERE, '..', 'src', 'sections')
TM = json.load(open(os.path.join(SRC, 'times', 'data.json')))
RD = json.load(open(os.path.join(SRC, 'rerd', 'data.json')))

# ---------------------------------------------------------------- trains in the busiest 60 minutes, each way (IDFM timetable, Tuesday 3 November 2026)
PEAK = {'B': 20, 'D': 12, 'G': RD['kr']['g'], 'K': RD['kr']['k'], 'R': RD['kr']['r'],
        'H': 20,                 # line H into Gare du Nord (the study's count)
        'L': 23,                 # line L into Saint-Lazare (the study's count)
        'C_south': 23,           # RER C from the south into Gare d'Austerlitz, 7:30 to 8:30 (20 of them run on to Saint-Michel today)
        'C_west': 20}            # RER C through Saint-Michel towards the west, 7:30 to 8:30 (16 the other way)
LIMIT_TWO_LINES = RD['sim']['capacity']['dg']['90 s']      # trains an hour on a pair that two lines share, with under a minute of added delay (annex 'rerd')
LIMIT_ONE_LINE = RD['sim']['capacity']['one']['90 s']      # one line alone on one platform track each way
ch = PEAK['C_west']                                        # the joined line RER C west + H runs the trains of the smaller side one for one
trains = {'peak': PEAK, 'limit_two': LIMIT_TWO_LINES, 'limit_one': LIMIT_ONE_LINE, 'ch': ch, 'lc': PEAK['L'],
          'two_pairs': {'old': PEAK['B'] + PEAK['D'], 'new': PEAK['G'] + ch},
          'three_pairs': {'old': PEAK['B'] + PEAK['D'], 'g': PEAK['G'], 'ch': ch},
          'with_kr': {'old': PEAK['B'] + PEAK['K'], 'd': PEAK['D'] + PEAK['R'], 'g': PEAK['G'], 'ch': ch, 'dg': PEAK['D'] + PEAK['R'] + PEAK['G']}}
for k in ('two_pairs', 'three_pairs', 'with_kr'): trains[k]['all'] = sum(v for a, v in trains[k].items() if a != 'dg')
trains['today'] = PEAK['B'] + PEAK['D']

# ---------------------------------------------------------------- what is built in place of the RER F tunnel (lengths read from maps; ASSUMPTION)
SUB_LEN = 225                    # m, a suburban platform as in the study
KM = {'sl_chatelet': 2.5,        # Saint-Lazare to Chatelet-Les Halles (2.3 km in a straight line)
      'chatelet_austerlitz': 2.8,     # Chatelet-Les Halles to the RER C tracks at Gare d'Austerlitz (2.6 km in a straight line, under the Seine)
      'chatelet_saint_michel': 1.0,   # Chatelet-Les Halles to the RER C tracks at Saint-Michel Notre-Dame (0.9 km in a straight line, under the Seine and the Ile de la Cite)
      'nord_chatelet': 2.2}           # a second new pair between Nord-Est and Chatelet-Les Halles, beside RER G
KM_NOT_BUILT = CORRIDOR_KM['nesl']    # the RER F tunnel between Nord-Est and Saint-Lazare
TRACKS_CHATELET = {'lc': 4, 'ch': 2}  # platform tracks at Chatelet: two each way for 23 trains an hour, one each way for 20 (the plan's rule: 20 trains an hour a track)


def items(R):
    tun = R['tunnel_civil'] + R['tunnel_systems']; tie = R['junction'] + R['portal']
    return [('sl_chatelet', KM['sl_chatelet'] * tun), ('chatelet_austerlitz', KM['chatelet_austerlitz'] * tun), ('chatelet_saint_michel', KM['chatelet_saint_michel'] * tun),
            ('nord_chatelet', KM['nord_chatelet'] * tun), ('chatelet_lc', TRACKS_CHATELET['lc'] * SUB_LEN * R['platform_m']), ('chatelet_ch', TRACKS_CHATELET['ch'] * SUB_LEN * R['platform_m']),
            ('chatelet_links', R['chatelet_links']), ('tie_austerlitz', tie), ('tie_saint_michel', tie), ('rer_f_tunnel', -KM_NOT_BUILT * tun)]


def all_in(hard, R):
    return hard * (1 + R['design'] + R['client'] + R['land']) * (1 + R['risk'])


AF = 0.045 / (1 - 1.045 ** -60)        # a 60-year annuity at the State discount rate, as in the chapter on the economic return
km_more = sum(KM.values()) - KM_NOT_BUILT
cost = {lab: round(all_in(sum(v for _, v in items(R)), R), 1) for lab, R in (('low', RATE_LOW), ('central', RATE), ('high', RATE_HIGH))}
cost.update(items={k: round(v, 3) for k, v in items(RATE)}, hard=round(sum(v for _, v in items(RATE)), 2), km_new=round(sum(KM.values()), 1), km_not_built=KM_NOT_BUILT, km_more=round(km_more, 1),
            uplift=round((1 + RATE['design'] + RATE['client'] + RATE['land']) * (1 + RATE['risk']), 3), upkeep=round(km_more * 0.0035 + 0.01, 3),
            tracks_chatelet=sum(TRACKS_CHATELET.values()), tracks_chatelet_all=sum(TRACKS_CHATELET.values()) + 2 + 2,      # with the two of RER G and the two of RER D (annex 'rerd')
            d_pair=RD['cost']['own']['with_g']['central'], d_shared=RD['cost']['shared']['with_g']['central'], kr=round(RD['cost']['r_fold']['central'] + RD['cost']['k_fold']['central'], 2))
cost['year'] = round(cost['central'] * AF + cost['upkeep'], 3); cost['year_low'] = round(cost['low'] * AF + cost['upkeep'], 3); cost['year_high'] = round(cost['high'] * AF + cost['upkeep'], 3)
cost['with_d'] = round(cost['central'] + cost['d_pair'] + cost['kr'], 1)

# ---------------------------------------------------------------- the time it saves, in euros (rough, as in the annex 'rerd')
VOT, DAYS = 15.0, 250                  # euros an hour; working days a year
ALL_TRIPS = TM['k']['factor'] / 2      # hours of all passengers for an hour of the commuters, both ways: a morning commuter stands for 'factor' passengers a day (chapter 'flows')
x = TM['x']['c_kb']; v = TM['v']
euro = lambda hours_day: round(hours_day * ALL_TRIPS * DAYS * VOT / 1e9, 3)
value = {'hours_more': x['hours_day'], 'hours_gained': x['hours_gained'], 'hours_lost': x['hours_lost'], 'year': euro(x['hours_day']), 'year_gained': euro(x['hours_gained']),
         'share_of_cost': round(euro(x['hours_day']) / cost['year'], 2), 'all_trips': round(ALL_TRIPS, 2), 'vot': VOT, 'days': DAYS,
         'more_than_plan': round(v['variant_c']['hours_day'] / v['plan']['hours_day'] - 1, 3), 'more_than_plan_kr': round(v['variant_c']['hours_day'] / v['plan_kb_rd']['hours_day'] - 1, 3)}

# ---------------------------------------------------------------- who rides through the centre (commuters one morning, and passengers a day)
t = TM['tun']; f = TM['k']['factor']; th = lambda n: int(round(n, -3))
bd = {k: t[k]['b'] + t[k]['d'] for k in ('future', 'plan', 'plan_kb_rd', 'variant_c')}
load = {'bd': bd, 'bd_relief': round(1 - bd['variant_c'] / bd['future'], 3), 'bd_relief_plan': round(1 - bd['plan'] / bd['future'], 3),
        'day': {k: th(t['variant_c'][k] * f) for k in ('c_sl_ch', 'c_ch_aus', 'c_sm_ch', 'c_ch_ne', 'g_n', 'g_s')}, 'c_today': t['future']['c'], 'c_today_day': th(t['future']['c'] * f)}

# ---------------------------------------------------------------- examples: minutes before the project, with the plan, with the variant
EX = {'sl_aus': ('Gare Saint-Lazare', "Gare d'Austerlitz"), 'enghien_javel': ('Enghien-les-Bains', 'Javel'), 'bretigny_sl': ('Brétigny', 'Gare Saint-Lazare'), 'becon_chatelet': ('Bécon les Bruyères', 'Châtelet - Les Halles'),
      'sl_juvisy': ('Gare Saint-Lazare', 'Juvisy'), 'juvisy_chatelet': ('Juvisy', 'Châtelet - Les Halles'), 'epinay_sm': ('Épinay - Villetaneuse', 'Saint-Michel Notre-Dame'),
      'clichy_bfm': ('Clichy - Levallois', 'Bibliothèque François Mitterrand'), 'stcloud_aus': ('Saint-Cloud', "Gare d'Austerlitz"), 'invalides_nord': ('Invalides', 'Gare du Nord'),
      'ermont_invalides': ('Ermont - Eaubonne', 'Invalides'), 'nord_sl': ('Gare du Nord', 'Gare Saint-Lazare'), 'epinay_sl': ('Épinay - Villetaneuse', 'Gare Saint-Lazare'),
      'becon_nord': ('Bécon les Bruyères', 'Gare du Nord'), 'juvisy_invalides': ('Juvisy', 'Invalides'), 'bfm_orsay': ('Bibliothèque François Mitterrand', "Musée d'Orsay"),
      'versailles_aus': ('Versailles Château Rive Gauche', "Gare d'Austerlitz")}
ex = {k: TM['exv'][a + '>' + b] for k, (a, b) in EX.items()}
short = lambda o: dict(o, **{'from': o['from'].replace(' Arrondissement', ''), 'to': o['to'].replace(' Arrondissement', ''), 'saved': o['base'] - o['variant']})
od = {'gain': [short(o) for o in x['od_gain']], 'loss': [short(o) for o in x['od_loss']]}

# ---------------------------------------------------------------- how many trains of the morning find a train to become on the other side
import numpy as np
LOG = [j for j in json.loads(str(np.load(os.path.join(HERE, 'inputs', 'regiontimes', 'variant_c.npz'))['log'])) if 'joined' in j]
pick = lambda name, a: next({'arrivals': j['arrivals'], 'joined': j['joined'], 'wait': j['mean_wait_min']} for j in LOG if j['name'] == name and j['from'] == a)
joins = {'l_c': pick('Line L to RER C south', 'L'), 'c_l': pick('Line L to RER C south', 'C'), 'c_h': pick('RER C west to line H', 'C'), 'h_c': pick('RER C west to line H', 'H')}

out = {'joins': joins, 'ex': ex, 'od': od, 'trains': trains, 'km': KM, 'cost': cost, 'value': value, 'load': load, 'params': {'sub_len': SUB_LEN, 'tracks': TRACKS_CHATELET}}
json.dump(out, open(os.path.join(SRC, 'lc', 'data.json'), 'w'), indent=1)
print('trains', trains); print('cost', cost); print('value', value); print('load', load)
