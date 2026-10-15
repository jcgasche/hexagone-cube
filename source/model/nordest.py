"""The plan: three deep TGV through stations (Paris Nord-Est under Gare du Nord and Gare de l'Est, Gare de Lyon, Montparnasse) on a
triangle of TGV tunnels, with separate tunnels for regional express trains and suburban lines N and H, and a deep station for line H
under Saint-Lazare (version 4 below). Access, service plan, bottom-up cost, traffic, direct and indirect return.

Version 3.1 (13 October 2026): the approach tunnels come up on the existing tracks at the ring road (east: at Rosa Parks), not beyond
it; route 21.8 km instead of 33.5, so 48.6 km of twin-track tunnel instead of 72.
Version 3 (13 October 2026). Changes from version 2:
- one layout only: two tunnel pairs (TGV with regional express; suburban) plus the Montparnasse to Gare de Lyon link; no train reverses;
- TGV platforms by direction, 6 a station, 4-minute stops with a 3-minute clearing time, 65% of that cycle used (ASSUMPTION);
- regional express platforms of 350 m (trains of 270 to 330 m); no sealed pair: one switchable platform and a control hall for London;
- risk 15% central (the unit prices are final costs or contracts), 10% low, 30% high;
- access with the triangle, plus a second measure where the passenger picks a train that calls at their best station;
Version 3.2 (13 October 2026): TGV passengers' access benefit is counted at the station entrance (the ride across Paris is not held
against them); the measure that counts the ride now always assumes the passenger picks the train; regional express passengers
bound for Nord-Est trains pick the one that runs on to the station best for them;
- the Atlantic to south-east pair is direct by the link; the hub layout and the comparison layouts are removed;
- land released is not sold: it becomes parks (not valued yet).
Version 3.4 (14 October 2026): passengers who cross Paris grow as the changes of vehicle are removed (each change today keeps 63% of
potential passengers, British ticket data; a change between two trains inside one Paris station counts as half a change and keeps 79%, as for suburban trips) and as the trip gets
shorter, averaged over the main destinations of the four lines; the charge on Paris-region passengers falls only on those who choose a
station their line did not serve (access_curve); a passenger who crosses Paris pays two fares.
Version 2 (after the independent check of 12 October 2026). Changes from version 1:
- yearly cost: interest during a 12-year build, one renewal of rail systems, tunnel upkeep at the measured RER E rate,
  extra running of regional trains;
- stations sized for the capacity of the high-speed lines, by one stated rule; portals and junctions counted by one rule;
- connecting passengers: only those changing in the Paris stations; the Nord to Est pair has its own present time;
  central gain where a direct train appears is the British figure for removing a change (37%), the Paris bypass line (57%) is the high case;
- regional growth 15% on suburban lines (25% is the high case), regional express from the time model;
- boarding-time test applied to regional passengers too; comfort without the regularity part; comfort and wider effects held
  at central values in the tests on weights;
- the Pleyel layout recomputed with the same functions (free pairing, same gain, same cost rules);
- back-test extended to the first RER E section and to two French study-stage estimates.
Version 3.3 (13 October 2026): suburban lines paired north (H, K) with the Atlantic (N) and east (P) with the south-east (R);
eastern regional express trains run on to Gare de Lyon; suburb-to-suburb trips across Paris counted (cross_paris); line N traffic
corrected (30.4 M, not 27.3).
Version 3.5 (15 October 2026): the 12-minute beat of the timetable annex. A TGV stops 7 minutes and its track is held 2 more for a
late train, then stays empty 3, so a track takes 5 trains an hour; every run between two of the three stations takes 6 minutes, the
direct link included, so a ride between two Paris stops is 13 minutes and a passenger who stays on a direct train across Paris spends
20 minutes in Paris (both stops counted); regional trains take the same 6-minute run plus a 1-minute stop.
Version 4 (15 October 2026), the plan: one twin-track tunnel for each kind of train. TGVs keep the triangle (one tunnel on each side,
the four approach corridors). Regional express trains get their own tunnel from the north and east approaches through Nord-Est to
Montparnasse and out on the Atlantic side; suburban lines P and N become one line (N) in a tunnel from the east approach through
Nord-Est to Montparnasse and the Atlantic side; suburban lines H, K and L become one line (H) in a tunnel from the north approach under
Nord-Est to a new deep through station under Saint-Lazare, which comes back up on the Batignolles tracks. Nothing but TGVs runs
between Nord-Est and Gare de Lyon; regional trains of Gare de Lyon (TER Bourgogne, line R, Bercy) stay on the surface for now (open item,
not costed). 46 platform tracks, 58.4 km of twin-track tunnel. The access measure that counts the ride between Paris stops now counts
the 6-minute run only (TH_ACCESS); the crossing measure keeps the run and the stop (TH).
Version 4.1 (15 October 2026, evening): no regional express tunnel. Regional express trains run in the TGV tunnels, on a 2-minute grid
of paths (30 an hour each way): TGVs keep their 4-minute places in the 12-minute beat and regional trains take the paths in between
(condition: signalling for trains about 1.5 minutes apart, ETCS level 2 with short blocks and automatic driving in the tunnels).
Northern regional trains run through Nord-Est to Montparnasse and the Atlantic lines; eastern ones (3, plus one new) run through
Nord-Est to Gare de Lyon and on to Burgundy, so Gare de Lyon and Bercy regional trains go underground too. Gare de Lyon gets 2 more
400 m tracks (8), for the 16th south-east TGV and the regional trains. Line R stays on a small surface terminal. 44.5 km, 48 tracks.
Every assumption that is not sourced is marked ASSUMPTION.
"""
import csv, json, statistics as S, collections, math
from estimate import E, W, PSH, SH, gain, loss, VOT_LD, VOT_IDF, VOT_TER, ELAST, HS_TERMINALS, T_OLD, T_NEW, CONN_TRAIN, ACC_EGR, FARE

import os
M = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inputs')      # model inputs: access times by point and by commune
KEYS = ['Nord', 'Est', 'Lyon', 'Montparnasse']
TH = {'L': 13.0, 'M': 13.0, 'LM': 13.0}  # TGV ride between two Paris stations, stop included: a 6-minute run between any two of them and a 7-minute stop,
                                         # the 12-minute beat of the timetable annex (ASSUMPTION: the 6-minute run is a design target; 4.3 to 5.0 technically)
TH_ACCESS = {'L': 6.0, 'M': 6.0, 'LM': 6.0}   # the same ride in the access measure that counts it (version 4): the 6-minute run only, the passenger
                                             # boarding a train that is already standing at the platform (ASSUMPTION; the crossing measure keeps TH)
REVERSE = 8.0                           # minutes for the rare train that turns back at Nord-Est (ASSUMPTION; 3 to 12 in French practice)
TR = {'L': 7.0, 'M': 7.0, 'SL': 4.0}   # regional train ride between the same stations: the same 6-minute run, plus a 1-minute stop (ASSUMPTION);
                                      # SL: line H from Nord-Est to Saint-Lazare, 2.6 km, 4 minutes stop included (ASSUMPTION; RER E Magenta to Haussmann is 2.46 km)
ring = lambda d: 'Paris' if d == '75' else ('Petite couronne' if d in ('92', '93', '94') else 'Grande couronne')
DATA = {}
for tag, pf, rf in (('clock', 'points.csv', 'regional.json'), ('eq', 'points_weighted.csv', 'regional_weighted.json'), ('comfort', 'points_comfort.csv', 'regional_comfort.json')):
    DATA[tag] = ([{k: float(r['t_' + k]) for k in KEYS} for r in csv.DictReader(open(f'{M}/{pf}'))], json.load(open(f'{M}/{rf}'))['rows'])
WALKW = {'clock': 1.0, 'eq': 2.0, 'comfort': 2.0}
# Saint-Lazare (version 4). The network data are not on this machine, so the minutes from each Paris point to Saint-Lazare are DERIVED:
# for each point and each weighting, a straight line t = a + b x distance fitted on its minutes to Nord, Est and Montparnasse, applied
# to the distance to Saint-Lazare, or walking all the way when that is shorter (ASSUMPTION; to replace by a run of model.py).
XY = {'Nord': (48.880185, 2.355151), 'Est': (48.876742, 2.358424), 'Montparnasse': (48.841172, 2.320514), 'Saint-Lazare': (48.8763, 2.3254)}
WALK_MIN_PER_KM = 60 / 4.5 * 1.3                 # as in model.py: 4.5 km/h, detour factor 1.3


def hav(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0]); dl = math.radians(b[1] - a[1])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


SL_FLOOR = (6.0, 2.5)                   # the fitted line is never taken below 6 minutes plus 2.5 a km (metro at about 24 km/h with access and wait), scaled for the weighting (ASSUMPTION)


def sl_time(xy, t, walkw, scale=1.0):
    """Derived minutes from a point to the Saint-Lazare platforms: straight line on the minutes to the other three terminals (never below
    SL_FLOOR), or walking all the way when that is shorter."""
    ds = [hav(xy, XY[k]) for k in ('Nord', 'Est', 'Montparnasse')]; ts = [t[k] for k in ('Nord', 'Est', 'Montparnasse')]
    md, mt = S.mean(ds), S.mean(ts); var = sum((d - md) ** 2 for d in ds)
    b = max(0.0, sum((d - md) * (x - mt) for d, x in zip(ds, ts)) / var) if var > 1e-9 else 0.0
    d = hav(xy, XY['Saint-Lazare'])
    fit = max(mt + b * (d - md), scale * (SL_FLOOR[0] + SL_FLOOR[1] * d))
    return min(fit, walkw * (d * WALK_MIN_PER_KM + 1.0))


for tag, pf in (('clock', 'points.csv'), ('eq', 'points_weighted.csv'), ('comfort', 'points_comfort.csv')):
    sc = S.mean(sum(t.values()) for t in DATA[tag][0]) / S.mean(sum(t.values()) for t in DATA['clock'][0])
    for r, t in zip(csv.DictReader(open(f'{M}/{pf}')), DATA[tag][0]):
        t['SL'] = sl_time((float(r['lat']), float(r['lon'])), t, WALKW[tag], sc)

# passengers changing between Paris stations: 13,000 a day in the 2012-13 survey, 88% of them in the stations inside Paris,
# all kinds of train; scaled by the growth of high-speed traffic at the terminals (derived; no newer count exists)
CONN = 13000 * 0.88 * 350 / 1e6 * (112.5 / 86.9)
CONN_HIGH = E['conn_base_high']         # all 13,000, on 435 days
OLD_CLOCK = {frozenset(p): T_OLD for p in PSH}
OLD_CLOCK[frozenset(('Nord', 'Est'))] = 30.0      # the two halls are 500 m apart (ASSUMPTION: 30 minutes from train to train today)


# ------------------------------------------------------------------ 1. reaching the TGV
def tgv_times(t, deep, choice=True, measure='station', hall='both'):
    """Minutes to the train by direction in the triangle. choice=False: only the station that serves the direction today (merged Nord-Est).
    Half of each line's trains call at each of the two other stations.
    measure='station': minutes to the entrance of the nearest station where the passenger's train stops, the train being one of the two
    halves at random; the train's ride between its Paris stops is not counted. Used for the benefits of TGV passengers: on a long trip the
    minutes spent seated on the right train across Paris hardly matter to them.
    measure='ride': the train's ride between its Paris stops is counted when the passenger boards at the first one, and the passenger picks
    a train that calls at the station best for them (ASSUMPTION: enough trains an hour to choose without a longer wait).
    hall='both': Nord-Est is entered from either historic hall; 'nord': from the Gare du Nord hall only."""
    ne = min(t['Nord'], t['Est']) if hall == 'both' else t['Nord']
    if not choice:
        return {'Nord': ne + deep, 'Est': ne + deep, 'Lyon': t['Lyon'] + deep, 'Montparnasse': t['Montparnasse'] + deep}
    th = TH_ACCESS if measure == 'ride' else {'L': 0.0, 'M': 0.0, 'LM': 0.0}
    viaL, viaM = min(ne, t['Lyon'] + th['L']), min(ne, t['Montparnasse'] + th['M'])          # north and east trains come half from each southern line
    lyonNE, lyonM = min(t['Lyon'], ne + th['L']), min(t['Lyon'], t['Montparnasse'] + th['LM'])   # south-east trains: half go on to Nord-Est, half to Montparnasse by the link
    montNE, montL = min(t['Montparnasse'], ne + th['M']), min(t['Montparnasse'], t['Lyon'] + th['LM'])
    if measure == 'ride':
        north = east = min(viaL, viaM); lyon = min(lyonNE, lyonM); mont = min(montNE, montL)
    else:
        north = east = 0.5 * viaL + 0.5 * viaM; lyon = 0.5 * lyonNE + 0.5 * lyonM; mont = 0.5 * montNE + 0.5 * montL
    return {'Nord': north + deep, 'Est': east + deep, 'Lyon': lyon + deep, 'Montparnasse': mont + deep}


def access(tag='eq', deep=0.0, choice=True, measure='station', shares=SH, hall='both'):
    pts, reg = DATA[tag]; dd = deep * WALKW[tag]
    par = [sum(W[k] * (tgv_times(t, dd, choice, measure, hall)[k] - t[k]) for k in W) for t in pts]
    agg = collections.defaultdict(lambda: [0.0, 0.0])
    for r in reg:
        t = {k: r['t_' + k] for k in KEYS}; a = tgv_times(t, dd, choice, measure, hall)
        g = agg[ring(r['dep'])]; g[0] += r['pop']; g[1] += r['pop'] * sum(W[k] * (a[k] - t[k]) for k in W)
    rings = {'Paris': S.mean(par), 'Petite couronne': agg['Petite couronne'][1] / agg['Petite couronne'][0], 'Grande couronne': agg['Grande couronne'][1] / agg['Grande couronne'][0]}
    return {'rings': rings, 'all': sum(shares[k] * rings[k] for k in shares), 'paris_share_quicker': sum(x < 0 for x in par) / len(par)}


def today_mean(tag):
    return S.mean(sum(W[k] * t[k] for k in W) for t in DATA[tag][0])


def trip_eq(tag):
    ratio = today_mean(tag) / today_mean('clock')
    return (212.0 - ACC_EGR) + ACC_EGR * ratio, ACC_EGR * ratio


def access_effect(tag='eq', deep=0.0, choice=True, measure='station', c=None, shares=SH, hall='both'):
    c = CONN if c is None else c
    d = access(tag, deep, choice, measure, shares, hall)['all']
    teq, _ = trip_eq(tag)
    idf = HS_TERMINALS - 2 * c
    dj = idf * ((1 + d / teq) ** ELAST - 1)
    ben = gain(idf, dj, -d, VOT_LD) if d < 0 else -loss(idf, -dj, d, VOT_LD)
    return {'minutes': d, 'journeys': dj, 'benefit': ben, 'idf': idf}


# ------------------------------------------------------------------ 2. passengers who cross Paris
UPLIFT_DIRECT = 0.37                    # an added change of train loses 37% of passengers in the long run (British ticket data, Wheat and Wardman)
UPLIFT_DIRECT_HIGH = 0.57               # Paris bypass line against the no-project case; includes new stations and time savings (derived)
DIRECT_SHARE = 0.5                      # share of passengers on a pair served by direct trains who find one for their own trip (ASSUMPTION)
CHANGE_METRO = (20 + 20 * 2 + 17.5 * 1.5, 5 * 2 + 7.5 * 1.5)       # change weighted like a metro trip: today, and inside one station
CHANGE_KEEP = 1 - UPLIFT_DIRECT         # share of potential passengers a change of vehicle keeps (British ticket data)
STATION_KEEP = CHANGE_KEEP ** 0.5       # a change between two TGVs inside one Paris station counts as half a change, as for suburban trips (EASY_CHANGE; ASSUMPTION).
                                        # No pulse: each direction's trains are spaced evenly over the hour, which shortens the wait when a change is needed
SWISS_KEEP = 1 / 1.12                   # test only: a timed Swiss change, SBB planning 12% more passengers when a direct train replaces one
# changes of vehicle today between two Paris stations, by the route with the fewest: TGV to metro or RER, metro to metro, metro or RER to TGV
# (ASSUMPTION, read from the network map; Gare du Nord to Gare de l'Est is a walk, so one change). Each costs the share CHANGE_KEEP.
TRANSFERS = {frozenset(('Lyon', 'Nord')): 2,           # RER D
             frozenset(('Lyon', 'Est')): 2,            # RER D to Gare du Nord, then 500 m on foot
             frozenset(('Montparnasse', 'Nord')): 2,   # metro 4
             frozenset(('Montparnasse', 'Est')): 2,    # metro 4
             frozenset(('Montparnasse', 'Lyon')): 3,   # no direct line: metro 4 then 1, or 6 then 14
             frozenset(('Nord', 'Est')): 1}            # on foot
# main destinations of each line and the minutes of the fastest regular train from Paris (published timetables, unverified; to check)
DEST = {'Nord': {'Lille': 62, 'Brussels': 82, 'London': 136}, 'Est': {'Strasbourg': 106, 'Metz': 82, 'Reims': 45},
        'Lyon': {'Lyon': 116, 'Marseille': 185, 'Montpellier': 200}, 'Montparnasse': {'Bordeaux': 124, 'Nantes': 119, 'Rennes': 85}}


def pair_ride(ps):
    """Minutes a direct train takes between its two Paris stops for a pair of lines; None for north to east, which has no direct train."""
    if ps == {'Nord', 'Est'}: return None
    if ps == {'Lyon', 'Montparnasse'}: return TH['LM']
    return sum(TH['L'] if x == 'Lyon' else TH['M'] for x in ps if x in ('Lyon', 'Montparnasse'))


def city_pair(ta, tb, p, keep=STATION_KEEP):
    """One pair of cities on two lines: clock minutes from city to city today, with a direct train and with a change inside one station,
    and the growth of traffic each brings: the changes removed (each change today keeps CHANGE_KEEP of the passengers, a change inside one
    station keeps `keep`) times the time model on the door-to-door trip (ACC_EGR minutes at the two ends)."""
    ride = pair_ride(set(p)); n = TRANSFERS[frozenset(p)]
    old = ta + tb + OLD_CLOCK[frozenset(p)]
    tf = lambda new: ((new + ACC_EGR) / (old + ACC_EGR)) ** ELAST
    change = ta + tb + (ride or 0.0) + T_NEW
    out = {'today': old, 'change': change, 'transfers': n, 'mult_change': keep / CHANGE_KEEP ** n * tf(change)}
    if ride is not None:
        out['direct'] = ta + tb + ride + STOP_MIN; out['mult_direct'] = 1 / CHANGE_KEEP ** n * tf(out['direct'])
    return out


def destinations(keep=STATION_KEEP):
    """Every pair of main destinations on two different lines, and the average growth of each pair of lines."""
    rows, axis = [], {}
    for p in PSH:
        cell = []
        for ca, ta in DEST[p[0]].items():
            for cb, tb in DEST[p[1]].items():
                r = city_pair(ta, tb, p, keep); r.update({'from': ca, 'to': cb, 'pair': '-'.join(p)}); rows.append(r); cell.append(r)
        axis['-'.join(p)] = {k: S.mean(r[k] for r in cell) for k in ('today', 'change', 'mult_change', 'direct', 'mult_direct') if k in cell[0]}
        axis['-'.join(p)]['transfers'] = TRANSFERS[frozenset(p)]
    return rows, axis


def connecting(c=None, evidence=UPLIFT_DIRECT, tag='eq', direct_share=DIRECT_SHARE, weights='official', method='changes', keep=STATION_KEEP):
    """Pairs of directions in the triangle: every pair except north to east has direct trains, none of them reversing.
    The Atlantic to south-east pair runs by the direct link.
    method='changes' (central): traffic on each pair grows as the changes of vehicle are removed and the trip gets shorter, averaged
    over the main destinations of the two lines (see destinations()). method='single': the earlier estimate, `evidence` on direct
    trains (0: time model alone) and the time model for the others. Time saved is valued the official way in both."""
    c = CONN if c is None else c
    _, ae = trip_eq(tag)
    chg = 2 * T_NEW if weights == 'official' else CHANGE_METRO[1]
    _, axis = destinations(keep)
    out = {'new': 0.0, 'ben': 0.0, 'saving': 0.0, 'direct_share': 0.0, 'pairs': {}, 'parts': []}
    for p, s in PSH.items():
        ps = set(p)
        old_eq = 2 * OLD_CLOCK[frozenset(p)] if weights == 'official' else CHANGE_METRO[0] * OLD_CLOCK[frozenset(p)] / T_OLD
        old = CONN_TRAIN + old_eq + ae
        ride = pair_ride(ps); served = ride is not None
        t_direct, t_change = (ride + STOP_MIN if served else None), (ride or 0.0) + chg     # a direct train stops at both Paris stations
        parts = [(direct_share, t_direct, True), (1 - direct_share, t_change, False)] if served else [(1.0, t_change, False)]
        ax = axis['-'.join(p)]
        for sh, repl, is_direct in parts:
            q = c * s * sh; new = CONN_TRAIN + repl + ae
            if method == 'changes': up = (ax['mult_direct'] if is_direct else ax['mult_change']) - 1
            else: up = evidence if (evidence and is_direct) else (new / old) ** ELAST - 1
            out['new'] += q * up; out['saving'] += s * sh * (old - new); out['ben'] += gain(q, q * up, old - new, VOT_LD)
            out['parts'].append({'q': q, 'mult': 1 + up, 'through': is_direct, 'saving': old - new})
            if is_direct: out['direct_share'] += s * sh
        out['pairs']['-'.join(p)] = {'share': s, 'served': served, 'direct': t_direct, 'change': t_change, 'change_clock': t_change - chg + T_NEW, 'old_clock': OLD_CLOCK[frozenset(p)],
                                     'transfers': TRANSFERS[frozenset(p)], 'growth': sum(sh * ((ax['mult_direct'] if d else ax['mult_change']) - 1) for sh, _, d in parts)}
    out['uplift'] = out['new'] / c; out['base'] = c
    return out


# ------------------------------------------------------------------ 2b. the charge on Paris-region passengers who use a station their line did not serve
def tgv_choice(t, dd, measure='station', cm=0.0, hall='both'):
    """Like tgv_times, with a charge worth `cm` minutes on boarding or leaving at a station the passenger's line did not serve before
    (Gare de Lyon for the south-east, Montparnasse for the Atlantic, Nord-Est for the north and the east, by either hall).
    The historic station keeps today's price, so the passenger pays only by choosing the other one.
    Returns, by direction, (minutes, minutes plus the charge, share who pay, minutes saved against today by those who pay)."""
    ne = min(t['Nord'], t['Est']) if hall == 'both' else t['Nord']
    th = TH_ACCESS if measure == 'ride' else {'L': 0.0, 'M': 0.0, 'LM': 0.0}
    home = {'Nord': ne, 'Est': ne, 'Lyon': t['Lyon'], 'Montparnasse': t['Montparnasse']}
    other = {'Nord': [t['Lyon'] + th['L'], t['Montparnasse'] + th['M']], 'Lyon': [ne + th['L'], t['Montparnasse'] + th['LM']],
             'Montparnasse': [ne + th['M'], t['Lyon'] + th['LM']]}
    other['Est'] = other['Nord']
    out = {}
    for k in KEYS:
        sets = [[(home[k], False)] + [(x, True) for x in other[k]]] if measure == 'ride' else [[(home[k], False), (x, True)] for x in other[k]]
        w = 1.0 / len(sets); tm = gm = pay = pg = 0.0
        for opts in sets:
            tt, paid = min(opts, key=lambda o: (o[0] + (cm if o[1] else 0.0), o[1]))
            tm += w * (tt + dd); gm += w * (tt + dd + (cm if paid else 0.0))
            if paid: pay += w; pg += w * (t[k] - tt - dd)
        out[k] = (tm, gm, pay, pg)
    return out


def access_charged(tag='eq', deep=0.0, measure='station', charge=0.0, shares=SH, hall='both'):
    """Paris-region TGV passengers with the charge: average change in minutes (time only, and with the charge), share who pay, and the
    minutes saved by those who pay. The charge is turned into minutes at the long-distance value of time."""
    pts, reg = DATA[tag]; dd = deep * WALKW[tag]; cm = charge / VOT_LD * 60
    def one(t):
        a = tgv_choice(t, dd, measure, cm, hall)
        return [sum(W[k] * (a[k][0] - t[k]) for k in W), sum(W[k] * (a[k][1] - t[k]) for k in W), sum(W[k] * a[k][2] for k in W), sum(W[k] * a[k][3] for k in W)]
    par = [one(t) for t in pts]
    rings = {'Paris': [S.mean(x[i] for x in par) for i in range(4)]}
    agg = collections.defaultdict(lambda: [0.0, [0.0] * 4])
    for r in reg:
        t = {k: r['t_' + k] for k in KEYS}; v = one(t); g = agg[ring(r['dep'])]; g[0] += r['pop']
        for i in range(4): g[1][i] += r['pop'] * v[i]
    for n in ('Petite couronne', 'Grande couronne'): rings[n] = [x / agg[n][0] for x in agg[n][1]]
    allv = [sum(shares[n] * rings[n][i] for n in shares) for i in range(4)]
    return {'minutes': allv[0], 'gen': allv[1], 'pay': allv[2], 'pay_gain': allv[3] / allv[2] if allv[2] > 0 else 0.0}


CURVE_STEP, CURVE_MAX = 0.1, 40.0       # euros: the charge levels at which the Paris-region response is tabulated for the accounts


def access_curve(tag='eq', measure='station', c=None):
    """Paris-region TGV passengers by level of charge: new journeys, value of time saved, share who pay, and minutes they save."""
    c = CONN if c is None else c
    teq, _ = trip_eq(tag); idf = HS_TERMINALS - 2 * c
    rows = []
    for i in range(int(round(CURVE_MAX / CURVE_STEP)) + 1):
        a = access_charged(tag, 0.0, measure, i * CURVE_STEP)
        dj = idf * ((1 + a['gen'] / teq) ** ELAST - 1)
        rows.append([dj, gain(idf, dj, -a['minutes'], VOT_LD), a['pay'], a['pay_gain'], a['minutes']])
    return {'step': CURVE_STEP, 'cols': ['journeys', 'benefit', 'pay', 'pay_gain', 'minutes'], 'rows': rows}


# ------------------------------------------------------------------ 3. regional trains
LINES = {'H': 54.6, 'K': 4.1, 'P': 27.3, 'N': 30.4, 'R': 19.1,                    # million journeys a year (derived from daily counts, unverified; N was 27.3, a copy of P: 117,000 a day x 260)
         'L': 297000 * 260 / 1e6}                                                     # line L, Saint-Lazare: 297,000 trips a weekday (version 4; unverified)
TERM_SHARE = {'H': 119900 / 215000, 'K': 119900 / 215000, 'N': 66800 / 117000, 'P': 63900 / 105000, 'R': 33000 / 70000,
              'L': 0.5}                 # half of line L's riders start or end at Saint-Lazare (ASSUMPTION)
THROUGH_TRAINS = {'L': 0.88}            # share of a line's trains that run through the new tunnel; the rest end at the surface station (ASSUMPTION; 1 for the others)
TER_DAY = {'Nord': 69200, 'Montparnasse': 23800, 'Lyon': 14900, 'Est': 8100}        # TER and Intercites, weekday, 2012-13
TER = {k: v * 350 / 1e6 for k, v in TER_DAY.items()}
REG_UPLIFT = 0.15                       # suburban lines joined through a centre: 5% to 30% observed, middle about 17%; 15% taken as net of background growth
REG_UPLIFT_HIGH, REG_UPLIFT_LOW = 0.25, 0.05
TER_TRIP = 100.0                        # door-to-door equivalent minutes of an average regional express trip (ASSUMPTION)
NEW_MONEY = 0.30                        # share of extra suburban journeys paid by new customers (London 9%, Sydney 27%, East London line about 30%)
YIELD = {'transilien': 1.22, 'ter': 8.0}        # euros per journey (Ile-de-France average; regional express ASSUMPTION)
REG_TRAINKM = 2.0 * 0.77                # million extra train-km a year for regional trains running through (ASSUMPTION: 77% of the 2.0 M of the earlier layout, version 4)
REG_TRAINKM_COST = 27.5                 # euros per extra train-km: half the average cost per train-km paid by the region (ASSUMPTION)
SECOND_MIN = 1.0                        # a passenger uses the second station when it saves more than this, on the clock (ASSUMPTION)
TER_THROUGH_SHARE = 0.05                # share of regional express passengers who cross Paris today (ASSUMPTION; study point I15)
# version 4 (the plan): which line runs on to which station. Suburban: H and K (Gare du Nord) run under Nord-Est to Saint-Lazare and
# on as line L; P (Gare de l'Est) runs through Nord-Est to Montparnasse and on as line N; line R (Gare de Lyon) stays on the surface,
# no through running. Regional express: northern and eastern trains run through Nord-Est to Montparnasse, Atlantic trains (Montparnasse)
# run through to Nord-Est; Gare de Lyon's regional trains stay on the surface (open item).
SUB_PAIR = {'H': 'Saint-Lazare', 'K': 'Saint-Lazare', 'P': 'Montparnasse'}
TER_RUN = {'Nord': 'Montparnasse', 'Est': 'Lyon'}             # version 4.1: eastern regional trains run on to Gare de Lyon and Burgundy
SOUTH_LINE = {'N': 'Montparnasse', 'L': 'Saint-Lazare', 'R': 'Lyon'}     # the lines across Paris from H, K and P (L is west, not south, but plays the same part)
LEG = {'Lyon': 'L', 'Montparnasse': 'M', 'Saint-Lazare': 'SL'}
REG_PLATFORMS = {                       # platform rule for regional and suburban tracks (Charles, 15 October 2026; ASSUMPTION)
    'ter': {'stop': 5.0, 'gap': 2.5, 'per_track': 8, 'tracks': 4, 'peak_today': {'Nord': 11, 'Est': 3}, 'peak_planned': 15},
    'n': {'per_track': 10, 'tracks': 4, 'peak': {'P': 11, 'N': 12}, 'peak_clamart': 16},
    'h': {'per_track': 10, 'tracks': 6, 'peak': {'H': 20, 'K': 3}, 'peak_l': (24, 28)}}

# version 4.1: regional express trains in the TGV tunnels. Peak trains an hour each way (Charles, 15 October 2026; ASSUMPTION)
TER_HOUR = {'Nord': 11, 'Est': 3, 'new_east_link': 1, 'atlantic_today': 7, 'lyon_today': 4}
TER_FLOW = {'north': 11, 'east': 4, 'nemont': 11, 'nelyon': 4, 'atlantic': 11, 'southeast': 4, 'link': 0}
PATH_MIN = 2.0                          # tunnel paths on a 2-minute grid: 30 an hour each way; TGVs keep the 4-minute places of the 12-minute beat
SIGNAL_MIN = (1.5, 2.0)                 # minutes between two trains the signalling allows: 1.5 (ETCS level 2, short blocks, automatic driving) or 2
UIC_PEAK = 0.75                         # planners keep the peak-hour occupation of a line under this (UIC code 406)
TER_PLATFORM_MIN = 7.5                  # a regional express train holds its platform 5 minutes (stop and margin) plus 2.5 empty
TGV_PLATFORM_MIN = 12.0                 # a TGV holds its track 7 + 2 and leaves it empty 3: one 12-minute place
R_OPTION = {'tracks_lyon': 2, 'tracks_ne': 2, 'len': 330, 'trains': 5, 'tie_ins': 2, 'partner': 'extra line P trains towards Meaux or Provins'}   # line R through running, not built (ASSUMPTION)
SUB_PLATFORM_MIN = 6.0                  # a suburban train holds its platform 6 minutes in all: 10 trains an hour a track


def ter_paths():
    """Tunnel occupation at the peak, each way, with the full TGV service and regional express trains in the TGV tunnels; platform time
    of the tracks regional trains use; the line R option (2 more tracks at Gare de Lyon and at Nord-Est), not built."""
    sv = service(HOUR_FULL); H = HOUR_FULL
    tgv = {'north': H['North'], 'east': H['East'], 'ne_joint': H['North'] + H['East'], 'nemont': sv['legs']['Montparnasse to Nord-Est'],
           'nelyon': sv['legs']['Gare de Lyon to Nord-Est'], 'link': sv['legs']['Montparnasse to Gare de Lyon'], 'atlantic': H['Atlantic'], 'southeast': H['Southeast']}
    ter = dict(TER_FLOW, ne_joint=0)
    loads = {k: {'tgv': v, 'ter': ter[k], 'total': v + ter[k], 'occ_15': (v + ter[k]) * SIGNAL_MIN[0] / 60, 'occ_20': (v + ter[k]) * SIGNAL_MIN[1] / 60} for k, v in tgv.items()}
    lyon_extra = H['Southeast'] - TRACKS_PER_DIRECTION * PER_TRACK            # the 16th south-east TGV, on the 4th track each way
    plat = {'lyon_4th': {'used': lyon_extra * TGV_PLATFORM_MIN + TER_FLOW['nelyon'] * TER_PLATFORM_MIN, 'avail': 60.0},
            'nordest_ter': {'used': (TER_FLOW['north'] + TER_FLOW['east']) * TER_PLATFORM_MIN, 'avail': 2 * 60.0},
            'montparnasse_ter': {'used': TER_FLOW['atlantic'] * TER_PLATFORM_MIN, 'avail': 2 * 60.0}}
    for v in plat.values(): v['share'] = v['used'] / v['avail']
    r = R_OPTION['trains']
    r_hard = (R_OPTION['tracks_lyon'] + R_OPTION['tracks_ne']) * R_OPTION['len'] * RATE['platform_m'] + R_OPTION['tie_ins'] * 0.05
    f = (1 + RATE['design'] + RATE['client'] + RATE['land']) * (1 + RATE['risk'])
    ropt = dict(R_OPTION, cost=r_hard * f, lyon_4th=plat['lyon_4th']['used'] + r * SUB_PLATFORM_MIN, nordest_ter=plat['nordest_ter']['used'] + r * SUB_PLATFORM_MIN,
                southeast_load=loads['southeast']['total'] + r, southeast_occ_15=(loads['southeast']['total'] + r) * SIGNAL_MIN[0] / 60)
    atl = dict(km=CORRIDOR_KM['atlantic'], cost=CORRIDOR_KM['atlantic'] * (RATE['tunnel_civil'] + RATE['tunnel_systems']) * f + 0.15 * f)   # option if signalling only reaches 2 minutes: its own TER tunnel to Vanves
    return {'paths_per_hour': 60 / PATH_MIN, 'signal_min': SIGNAL_MIN, 'uic_peak': UIC_PEAK, 'ter_hour': TER_HOUR, 'loads': loads, 'platforms': plat,
            'ter_platform_min': TER_PLATFORM_MIN, 'tgv_platform_min': TGV_PLATFORM_MIN, 'r_option': ropt, 'atlantic_option': atl,
            'max_occ_15': max(v['occ_15'] for v in loads.values()), 'max_occ_20': max(v['occ_20'] for v in loads.values())}


# suburb to suburb across Paris (version 4): trips between H, K or P and N, L or R
TRANSIT_SHARE = 0.14                    # trips through the Paris stations between two suburban departements, only passing through Paris (OMNIL and Gares & Connexions survey, 2012-13: 145,000 a weekday, 14%)
CROSS_SHARE = 0.20                      # share of those, on these lines, bound for a suburban line on the other side of Paris (ASSUMPTION; 10% to 30% tested)
CHANGE_LOSS = 0.37                      # traffic lost for each change of train added; today's trip has two (train to metro, metro to train)
EASY_CHANGE = 0.5                       # a change between two suburban trains on the platforms of Nord-Est counts as half a change (ASSUMPTION)
CORRIDOR = {'H': (600, 200, 20), 'K': (70, 20, 30), 'P': (450, 120, 30), 'N': (650, 300, 25), 'R': (300, 110, 35),
            'L': (900, 450, 25)}        # thousands of residents and jobs near the stations, minutes to Paris (ASSUMPTION, orders of magnitude)
CROSS_DECAY = 40.0                      # minutes: trips between two corridors fall by e for every 40 minutes of travel (ASSUMPTION; 25 to infinite give the same ranking)
CROSS_TODAY = {'Montparnasse': 35.0, 'Saint-Lazare': 18.0, 'Lyon': 28.0}     # clock minutes today from a suburban train at Gare du Nord or de l'Est to one leaving the other terminal (ASSUMPTION)
CROSS_OUT = 0.5                         # share of that time spent walking, waiting and changing, counted twice at official weights (ASSUMPTION)
CROSS_CHANGE_EQ = 16.0                  # weighted minutes of a change at Nord-Est: 4 to cross the platform and 4 of waiting, counted twice (ASSUMPTION)


def cross_paris(pair=SUB_PAIR, share=CROSS_SHARE, realise=1.0):
    """Suburb-to-suburb trips across Paris between lines H, K, P and lines N, L, R. Today they change twice (train to metro, metro to
    train); with the project they stay on a direct train (H and K to L, P to N), or change once on the platforms of Nord-Est (H and K
    to N, P to L). Line R does not run through: its pairs are unchanged. Each change costs CHANGE_LOSS of the traffic. Today's trips
    are split between the nine pairs of lines in proportion to residents times jobs, discounted with time."""
    users = sum(LINES[l] * TERM_SHARE[l] for l in LINES)
    base = users * TRANSIT_SHARE * share / 2                # each trip uses two lines
    idx = {}
    for a in ('H', 'K', 'P'):
        for b, st in SOUTH_LINE.items():
            pa, ja, ta = CORRIDOR[a]; pb, jb, tb = CORRIDOR[b]
            idx[(a, b)] = (pa * jb + pb * ja) * math.exp(-(ta + TR[LEG[st]] + tb) / CROSS_DECAY)
    tot = sum(idx.values())
    out = {'today': 0.0, 'project': 0.0, 'new': 0.0, 'benefit': 0.0, 'direct_today': 0.0, 'pairs': {}}
    for (a, b), w in idx.items():
        st = SOUTH_LINE[b]; d0 = base * w / tot
        if b == 'R':                                        # no through running on line R: nothing changes
            out['today'] += d0; out['project'] += d0
            out['pairs'][a + '-' + b] = {'direct': False, 'served': False, 'today': d0, 'project': d0, 'saving_eq': 0.0, 'saving_clock': 0.0}
            continue
        direct = pair[a] == st
        changes = 0.0 if direct else EASY_CHANGE
        d1 = d0 / (1 - CHANGE_LOSS) ** (2 - changes)
        n = (d1 - d0) * realise
        s = CROSS_TODAY[st] * (1 + CROSS_OUT) - TR[LEG[st]] - (0.0 if direct else CROSS_CHANGE_EQ)
        out['benefit'] += gain(d0, n, s, VOT_IDF); out['today'] += d0; out['project'] += d0 + n; out['new'] += n
        if direct: out['direct_today'] += d0
        out['pairs'][a + '-' + b] = {'direct': direct, 'served': True, 'today': d0, 'project': d0 + n, 'saving_eq': s,
                                     'saving_clock': CROSS_TODAY[st] - TR[LEG[st]] - (0.0 if direct else 8.0)}
    out['uplift'] = out['new'] / out['today']; out['daily_today'] = out['today'] * 1e6 / 260; out['daily_project'] = out['project'] * 1e6 / 260
    return out


def _reach(hall):
    """Saving functions of a Paris point t for each service, on the pairing above (minutes from the train to the point)."""
    ne = (lambda t: min(t['Nord'], t['Est'])) if hall == 'both' else (lambda t: t['Nord'])
    on = {'Lyon': lambda t: TR['L'] + t['Lyon'], 'Montparnasse': lambda t: TR['M'] + t['Montparnasse'], 'Saint-Lazare': lambda t: TR['SL'] + t['SL']}
    def best(dest):                     # the passenger gets off at Nord-Est or at the station the train runs on to, whichever is better
        return lambda t: min(ne(t), on[dest](t))
    zero = lambda t: 0.0
    alt = {'H': lambda t: t['Nord'] - best(SUB_PAIR['H'])(t), 'K': lambda t: t['Nord'] - best(SUB_PAIR['K'])(t), 'P': lambda t: t['Est'] - best(SUB_PAIR['P'])(t),
           'N': lambda t: t['Montparnasse'] - min(t['Montparnasse'], TR['M'] + ne(t)), 'L': lambda t: t['SL'] - min(t['SL'], TR['SL'] + ne(t)),
           'R': zero}                   # line R stays on the surface at Gare de Lyon (open item)
    alt_ter = {'Nord': lambda t: t['Nord'] - best(TER_RUN['Nord'])(t), 'Est': lambda t: t['Est'] - best(TER_RUN['Est'])(t),
               'Lyon': lambda t: t['Lyon'] - min(t['Lyon'], TR['L'] + ne(t)), 'Montparnasse': alt['N']}      # Gare de Lyon and Bercy trains run through to Nord-Est (version 4.1)
    return ne, alt, alt_ter


def regional_saving(tag='eq', hall='both'):
    """Average minutes saved between the train and a Paris destination, by service, when the train runs on to a second station."""
    pts = DATA[tag][0]
    def avg(fn): return S.mean(fn(t) for t in pts)
    ne, alt, alt_ter = _reach(hall)
    sv = {l: avg(f) for l, f in alt.items()}
    sv.update({'TER ' + k: avg(f) for k, f in alt_ter.items()})
    merge = {'H': avg(lambda t: t['Nord'] - ne(t)), 'P': avg(lambda t: t['Est'] - ne(t))}      # part of the saving that comes from entering by either hall
    return sv, merge


def regional(uplift=REG_UPLIFT, tag='eq', deep=0.0, realise=1.0, hall='both', cross=CROSS_SHARE):
    sv, merge = regional_saving(tag, hall); svc, _ = regional_saving('clock', hall)
    dd = deep * WALKW[tag]
    out = {'saving_eq': sv, 'saving_clock': svc, 'merge_part': merge, 'rows': []}
    ben = new_t = new_r = base_t = base_r = users = minutes = 0.0
    def value(u, n, s, vot):                       # existing users get the whole change; new ones half of a saving
        return gain(u, n, s, vot) if s >= 0 else -loss(u, 0.0, -s, vot)
    for l, q in LINES.items():
        thr = THROUGH_TRAINS.get(l, 1.0) if sv[l] > 0 else 0.0      # riders of trains that stay on the surface see no change, not even the deeper platform
        u = q * TERM_SHARE[l]; s = sv[l] - dd
        n = q * thr * uplift * realise * (max(0.0, s / sv[l]) if sv[l] > 0 else 0.0)
        ben += value(u * thr, n, s, VOT_IDF); new_t += n; base_t += q; users += u; minutes += u * thr * svc[l]
        out['rows'].append([l, q, u, thr * svc[l], thr * sv[l]])
    for k, q in TER.items():
        if sv['TER ' + k] <= 0:                    # Gare de Lyon's regional trains stay on the surface (open item)
            base_r += q; users += q; out['rows'].append(['TER ' + k, q, q, 0.0, 0.0]); continue
        s = sv['TER ' + k] - dd
        n = q * ((1 - max(0.0, s) / TER_TRIP) ** ELAST - 1) * realise                 # time model: no observed case for regional express
        ben += value(q, n, s, VOT_TER); new_r += n; base_r += q; users += q; minutes += q * svc['TER ' + k]
        out['rows'].append(['TER ' + k, q, q, svc['TER ' + k], sv['TER ' + k]])
    x = cross_paris(share=cross, realise=realise)                 # suburb to suburb across Paris, on top of the Paris-side growth above
    out['cross'] = x; out['cross_benefit'] = x['benefit']; out['paris_benefit'] = ben
    ben += x['benefit']; new_t += x['new']
    out.update({'benefit': ben, 'new_transilien': new_t, 'new_ter': new_r, 'new': new_t + new_r, 'base': base_t + base_r, 'base_transilien': base_t, 'base_ter': base_r, 'users': users,
                'avg_clock_saving': minutes / users, 'ter_uplift': new_r / base_r,
                'fares': (new_t * NEW_MONEY * YIELD['transilien'] + new_r * YIELD['ter']) / 1000})
    out.update(second_station(hall))
    ter_thr = sum(TER.values())                                      # every regional express train runs through (version 4.1)
    out['through_ter'] = ter_thr * TER_THROUGH_SHARE * (1 + UPLIFT_DIRECT) * realise          # regional express passengers crossing Paris on a through train
    return out


def second_station(hall='both', thr=SECOND_MIN):
    """Passengers who would get off at the second station: those for whom it saves more than `thr` clock minutes, by line and for regional express."""
    pts = DATA['clock'][0]
    ne, alt, alt_ter = _reach(hall)
    share = lambda fn: sum(1 for t in pts if fn(t) > thr) / len(pts)
    sub = {l: q * TERM_SHARE[l] * THROUGH_TRAINS.get(l, 1.0) * share(alt[l]) for l, q in LINES.items()}
    ter = {k: q * share(alt_ter[k]) for k, q in TER.items()}
    return {'second_station_sub': sum(sub.values()), 'second_station_ter': sum(ter.values()), 'second_station_share': {**{l: share(alt[l]) for l in LINES}, **{'TER ' + k: share(alt_ter[k]) for k in TER}}}


# ------------------------------------------------------------------ 4. service plan and station sizes
HOUR_TODAY = {'Atlantic': 12, 'Southeast': 12, 'North': 8, 'East': 4}      # TGVs per hour and direction in a standard busy hour (ASSUMPTION)
HOUR_FULL = {'Atlantic': 15, 'Southeast': 16, 'North': 8, 'East': 4}       # southern lines at their planned capacity (sourced); north and east unchanged (ASSUMPTION)
STOP_MIN = 7.0                          # minutes a TGV stands at a through platform (ASSUMPTION, as in the timetable annex; Lyon Part-Dieu plans 6 for most TGVs)
CLEAR_MIN = 3.0                         # minutes from a departure to the next arrival on the same track (ASSUMPTION)
RESERVE_MIN = 2.0                       # minutes the track stays held after the planned departure, for a late train (ASSUMPTION, as in the timetable annex)
UTIL = (STOP_MIN + CLEAR_MIN) / (STOP_MIN + RESERVE_MIN + CLEAR_MIN)      # share of each 12-minute place used by the stop and the clearing time
PER_TRACK = 60 * UTIL / (STOP_MIN + CLEAR_MIN)                             # trains a platform track takes an hour: 5, one every 12 minutes
TRACKS_PER_DIRECTION = 3                # TGV platform tracks each way at every station (ASSUMPTION: two would do on paper, the third takes late trains)


def service(H=HOUR_TODAY):
    """One standard hour in the triangle. North and east trains pair with a southern line; the rest of the southern trains pair with
    each other by the direct link; a train left without a partner turns back at Nord-Est. No train reverses otherwise."""
    A, SE, N, Ea = H['Atlantic'], H['Southeast'], H['North'], H['East']
    through = N + Ea                                                        # trains an hour each way between a southern line and the north or east
    link = min(A - through / 2, SE - through / 2)                           # Atlantic to south-east trains an hour each way, by the link
    spare_a, spare_se = A - through / 2 - link, SE - through / 2 - link     # trains with no partner: they turn back at Nord-Est
    spare = spare_a + spare_se
    flows = {'Atlantic to north': N / 2, 'Atlantic to east': Ea / 2, 'Southeast to north': N / 2, 'Southeast to east': Ea / 2, 'Atlantic to southeast, by the direct link': link}
    rev_equiv = (REVERSE + 1.0) / STOP_MIN                                  # a turning train holds a platform as long as 2.25 stopping trains
    legs = {'Montparnasse to Nord-Est': through / 2 + spare_a, 'Gare de Lyon to Nord-Est': through / 2 + spare_se, 'Montparnasse to Gare de Lyon': link}
    stops_dir = {'Paris Nord-Est': through + spare * rev_equiv / 2, 'Gare de Lyon': SE, 'Montparnasse': A}        # stop-equivalents an hour in one direction
    out = {'hour': H, 'flows': flows, 'through_each_way': through, 'link_each_way': link, 'spare': spare, 'rev_equiv': rev_equiv, 'legs': legs,
           'per_track': PER_TRACK, 'tracks_per_direction': TRACKS_PER_DIRECTION, 'stops_direction': stops_dir}
    for n, sd in stops_dir.items():
        key = {'Paris Nord-Est': 'nordest', 'Gare de Lyon': 'lyon', 'Montparnasse': 'montparnasse'}[n]
        out[key + '_stops'] = 2 * sd                                        # both directions together
        out[key + '_tracks_calc'] = 2 * math.ceil(sd / PER_TRACK - 1e-9)   # what the rule asks for, by direction
        out[key + '_load'] = sd / TRACKS_PER_DIRECTION                      # trains an hour on each of the provided tracks
    return out


# ------------------------------------------------------------------ 5. cost, built up from unit rates of built projects (2026 euros, bn)
RATE = {'tunnel_civil': 0.130,      # per km of twin-track tunnel, with shafts (Grand Paris 0.10 to 0.13, Elizabeth line 0.14 to 0.17, Zurich 0.13 to 0.15)
        'tunnel_systems': 0.045,    # per km: track, power, signalling, ventilation (Grand Paris 0.03 to 0.06, Elizabeth line 0.10)
        'platform_m': 0.0010,       # per metre of platform track in a deep station (RER E 1999 about 0.0009 complete; RER E 2024 structures 0.0009 to 0.0014; Zurich 0.00055; London 0.0020)
        'hall': {'Nord': 0.5, 'Est': 0.3, 'Lyon': 0.5, 'Montparnasse': 0.5},        # converting each historic hall (ASSUMPTION; Montparnasse 0.19, Austerlitz 0.6, Gare du Nord 0.76 to 1.8)
        'junction': 0.25,           # per underground junction (ASSUMPTION, no published cost)
        'portal': 0.15,             # per portal and tie-in of one track pair to an existing line (ASSUMPTION)
        'sidings': 0.6,             # turnback sidings and depot links (ASSUMPTION)
        'london_hall': 0.2,         # control hall and waiting room for London trains above a switchable platform at Nord-Est (ASSUMPTION)
        'ter_links': 0.65,          # regional express trains into the TGV tunnels (version 4.1, ASSUMPTION): 6 throat tie-ins at 0.05 (Nord-Est 4, Montparnasse 2),
                                    # 2 dive-unders in the Nord-Est throats at 0.10, links at 3 TGV portal ramps (north, east, Atlantic) at 0.05
        'design': 0.12, 'client': 0.08, 'land': 0.07,
        'risk': 0.15}               # the unit prices are final costs or contracts and already hold past overruns (ASSUMPTION: 15%; 10% low, 30% high)
RATE_LOW = dict(RATE, tunnel_civil=0.100, tunnel_systems=0.035, platform_m=0.00055, risk=0.10)
RATE_HIGH = dict(RATE, tunnel_civil=0.170, tunnel_systems=0.070, platform_m=0.0014, risk=0.30)
# route km of the six corridors of the Y, read from maps (ASSUMPTION). The four approach corridors end where the tunnels come up on
# the existing surface tracks: at the ring road for the north, south-east and Atlantic lines, at Rosa Parks just inside it for the
# east. At 35 mm per metre a tunnel 35 to 40 m deep reaches the surface in 1.0 to 1.2 km, so it need not stay underground any further.
# Earlier the portals were beyond the ring road (Saint-Denis 5.0, Pantin 4.5, Maisons-Alfort 7.0, Clamart 6.0: 33.5 km in all).
CORRIDOR_KM = {'north': 2.4, 'east': 2.7, 'nelyon': 5.0, 'nemont': 6.0, 'southeast': 2.9, 'atlantic': 2.8,
               'nesl': 2.6, 'slwest': 1.2}   # version 4: Nord-Est to Saint-Lazare with the curve, and the climb back to the Batignolles tracks (ASSUMPTION; RER E Magenta to Haussmann 2.46 km)
LINK_KM = 5.0                       # the direct TGV link between the city ends of Montparnasse and Gare de Lyon (ASSUMPTION: 4.5 to 6 km)
# version 4 (the plan): one twin-track tunnel for each kind of train. Each tunnel is the list of corridors it runs along.
TUNNELS = {'tgv': ['north', 'east', 'nelyon', 'nemont', 'southeast', 'atlantic', 'link'],   # the triangle and its four approaches
           'n': ['east', 'nemont', 'atlantic'],                                               # suburban line N (formerly P and N)
           'h': ['north', 'nesl', 'slwest']}                                                  # suburban line H (formerly H, K and L)
TUNNEL_KM = {k: sum(LINK_KM if c == 'link' else CORRIDOR_KM[c] for c in v) for k, v in TUNNELS.items()}
ROUTE_KM = sum(CORRIDOR_KM.values())
TER_CORRIDORS = ['north', 'east', 'nelyon', 'nemont', 'southeast', 'atlantic']               # version 4.1: regional express trains run in the TGV tunnels, all but the link
FEE_KM = sum(v for k, v in TUNNEL_KM.items() if k != 'tgv') + sum(CORRIDOR_KM[c] for c in TER_CORRIDORS)   # km of tunnel used by regional and suburban trains (authority fee; ASSUMPTION: TGV tunnel km count when regional trains use them)
# stations: TGV tracks by direction from the service rule (3 each way); regional express and suburban tracks from the platform rule of each line (ASSUMPTION)
# junctions: TGV 4 (where north and east meet, where the two southern sides part, the two ends of the link), regional express 1 (north and east meet)
# portals and tie-ins to existing lines: TGV 4, regional express 3 (north, east, Atlantic), line N 2 (east, Atlantic), line H 2 (north, west of Saint-Lazare)
JUNCTIONS = {'tgv': 4, 'ter': 0, 'n': 0, 'h': 0}      # version 4.1: no regional express tunnel, so no junction or portal of its own
PORTALS = {'tgv': 4, 'ter': 0, 'n': 2, 'h': 2}
LAYOUT = {'tunnels': TUNNEL_KM, 'junctions': JUNCTIONS, 'portals': PORTALS, 'halls': ['Nord', 'Est', 'Lyon', 'Montparnasse'],
          'stations': {'Paris Nord-Est': {'hs': 6, 'ter': 4, 'sub': 10}, 'Gare de Lyon': {'hs': 8, 'ter': 0, 'sub': 0},
                       'Montparnasse': {'hs': 6, 'ter': 4, 'sub': 4}, 'Saint-Lazare': {'hs': 0, 'ter': 0, 'sub': 6}}}
SUB_TRACKS = {'Paris Nord-Est': {'n': 4, 'h': 6}, 'Montparnasse': {'n': 4}, 'Saint-Lazare': {'h': 6}}     # suburban tracks by line
LEN = {'hs': 400, 'ter': 350, 'sub': 225}   # platform lengths: a double TGV; regional express trains of 270 to 330 m; suburban as on RER E
STAGE_CORRIDORS = {'first': ('north', 'east', 'nelyon', 'southeast'), 'second': ('nemont', 'atlantic')}


def cost(R=RATE, L=LAYOUT):
    portals = sum(L['portals'].values()); junctions = sum(L['junctions'].values())
    km = sum(L['tunnels'].values())
    plat = {n: sum(v * LEN[k] for k, v in s.items()) for n, s in L['stations'].items()}
    items = {'Tunnels, civil works': km * R['tunnel_civil'], 'Tunnels, rail systems': km * R['tunnel_systems'],
             'Stations': sum(plat.values()) * R['platform_m'], 'Historic halls': sum(R['hall'][h] for h in L['halls']),
             'Underground junctions': junctions * R['junction'], 'Portals and links to existing lines': portals * R['portal'], 'Sidings and depot links': R['sidings'],
             'Control hall for London trains': R['london_hall'], 'TER links into the TGV tunnels': R['ter_links']}
    hard = sum(items.values())
    soft = hard * (R['design'] + R['client']); land = hard * R['land']
    risk = (hard + soft + land) * R['risk']
    return {'tunnel_km': km, 'tunnel_by_type': dict(L['tunnels']), 'link_km': LINK_KM, 'platform_m': plat, 'platform_total': sum(plat.values()), 'tracks': {n: sum(s.values()) for n, s in L['stations'].items()},
            'tracks_total': sum(sum(s.values()) for s in L['stations'].values()), 'detail': L['stations'],
            'portals': portals, 'junctions': junctions, 'portals_by_type': dict(L['portals']), 'junctions_by_type': dict(L['junctions']),
            'items': items, 'station_cost': {n: v * R['platform_m'] for n, v in plat.items()},
            'hard': hard, 'soft': soft, 'land': land, 'risk': risk, 'total': hard + soft + land + risk}


def backtest(R=RATE):
    """The same rates applied to built or priced projects (works x 1.27 for design, client and land; risk shown separately)."""
    f = 1 + R['design'] + R['client'] + R['land']
    #        name, km, platform m, other works, published cost in 2026 euros (low, high), kind, note
    cases = [('RER E first section, Paris, 1999', 4.0, 2 * 4 * 225, 0.0, 2.49, 2.49, 'built', '1,322 M of 2003, complete; two stations of 4 tracks 30 m deep and 4 km of tunnel; the index is a floor'),
             ('RER E western extension, Paris, 2024', 8.0, 900, 0.36 + 1.0, 5.83, 7.07, 'built', '5.4 bn, price base not stated: 5.8 bn if at 2023 prices, 7.1 bn if at 2012 conditions like its budget; surface line works taken at 1.0 bn'),
             ('Lyon, deep station and tunnel', 7.6, 4 * 365, 0.0, 3.84, 3.84, 'study', '3.0 bn at 2018 prices, study stage with its own contingency, before any overrun; 8.5 km of route of which 0.9 km is the station'),
             ('Marseille, deep station and tunnel', 8.3, 4 * 406, 0.0, 3.39, 3.39, 'study', '2.66 bn at 2020 prices for the whole phase, study stage with its own contingency'),
             ('Stuttgart 21', 30.0, 8 * 420, 27 * 0.03 + 0.5, 14.5, 14.5, 'building', '14.5 bn in money of each year since 2010; more in 2026 euros; includes 27 km of surface line and an airport station'),
             ('Zurich cross-city line', 4.8, 4 * 420, 0.5, 2.75, 2.75, 'built', 'CHF 2.05 bn at 2005 prices; includes two long bridges'),
             ('Munich second trunk line', 10.0, 3 * 2 * 210, 0.3, 10.9, 10.9, 'building', 'forecast 10.9 bn including future inflation; three stations about 40 m deep')]
    out = []
    for name, km, pm, other, lo, hi, kind, note in cases:
        hard = km * (R['tunnel_civil'] + R['tunnel_systems']) + pm * R['platform_m'] + other
        out.append({'name': name, 'km': km, 'platform_m': pm, 'model_no_risk': hard * f, 'model_with_risk': hard * f * (1 + R['risk']), 'actual': lo, 'actual_high': hi, 'kind': kind, 'note': note})
    return out


# ------------------------------------------------------------------ 6. yearly figures
r_, n_ = 0.03, 60
AF = r_ / (1 - (1 + r_) ** -n_)
BUILD_YEARS = 12                    # ASSUMPTION: even spending over twelve years before opening
def idc(years=BUILD_YEARS): return sum((1 + r_) ** (k + 0.5) for k in range(years)) / years      # interest during construction
RENEW_YEAR = 30                     # rail systems renewed once in the 60 years (ASSUMPTION)
TRACK_SHARE = 0.35                  # track charges as a share of high-speed ticket revenue (regulator's figures, derived)
OM_TUNNEL_HIGH = 0.0035             # bn per km of twin-track tunnel a year: first RER E section (0.0041 measured with its station structures, indexed with the public-works index)
OM_TUNNEL_LOW = 0.0010              # RATP's RER network: more than 0.5 m euros per km of track a year (regulator, 2024), so about 1.0 m per km of two-track tunnel
OM_TUNNEL = (OM_TUNNEL_HIGH + OM_TUNNEL_LOW) / 2      # ASSUMPTION: midway between the two French figures
OM_STATION = 13.2e-6                # bn per metre of platform track a year (RER E first section, measured, indexed)
GPE = {'time': 14.2, 'regularity': 4.6, 'comfort': 3.9, 'urban': 7.49, 'agglomeration': 11.3, 'employment': 19.6}
R_COMFORT = GPE['comfort'] / GPE['time']                                   # regularity left out: joined lines share their delays
R_WIDER = (GPE['urban'] + GPE['agglomeration'] + GPE['employment']) / (GPE['time'] + GPE['regularity'] + GPE['comfort'])
FARE_RESPONSE = -0.7                # response of high-speed traffic to fares (ASSUMPTION)
PARK_HA = 160                       # hectares of railway land that could become parks once the surface tracks go (estimate from maps, never measured; ASSUMPTION)


def yearly_cost(R=RATE, years=BUILD_YEARS, om_tunnel=None):
    C = cost(R); k = idc(years); om_tunnel = OM_TUNNEL if om_tunnel is None else om_tunnel
    renew = C['items']['Tunnels, rail systems'] * (1 + R['design'] + R['client']) * (1 + R['risk']) / (1 + r_) ** RENEW_YEAR * AF
    out = {'capex': C['total'], 'idc': k, 'capex_open': C['total'] * k, 'annuity': C['total'] * k * AF, 'renewal': renew,
           'om_infra': C['tunnel_km'] * om_tunnel + C['platform_total'] * OM_STATION, 'om_trains': REG_TRAINKM * REG_TRAINKM_COST / 1000}
    out['om'] = out['om_infra'] + out['om_trains']
    out['cost'] = out['annuity'] + out['renewal'] + out['om']
    return out


def wider(reg_benefit):
    comfort = reg_benefit * R_COMFORT
    return comfort, (reg_benefit + comfort) * R_WIDER


def yearly(R=RATE, deep=0.0, measure='station', evidence=UPLIFT_DIRECT, uplift=REG_UPLIFT, tag='eq', c=None, shares=SH, capacity=False,
           hall='both', weights='official', realise=1.0, years=BUILD_YEARS, scale_wider=False, om_tunnel=None, cross=CROSS_SHARE,
           method='changes', direct_share=DIRECT_SHARE, keep=STATION_KEEP):
    out = yearly_cost(R, years, om_tunnel)
    a = access_effect(tag, deep, True, measure, c, shares, hall); k = connecting(c, evidence, tag, direct_share, weights, method, keep); g = regional(uplift, tag, deep, realise, hall, cross)
    aj, kj = a['journeys'] * (realise if a['journeys'] > 0 else 1.0), k['new'] * realise
    ab = a['benefit'] - (a['journeys'] - aj) * abs(a['minutes']) / 120 * VOT_LD / 1000
    kb = k['ben'] - (k['new'] - kj) * k['saving'] / 120 * VOT_LD / 1000
    out.update({'tgv_access_min': a['minutes'], 'tgv_access_journeys': aj, 'tgv_access_benefit': ab,
                'tgv_conn_journeys': kj, 'tgv_conn_benefit': kb, 'tgv_conn_uplift': kj / k['base'], 'tgv_conn_saving': k['saving'], 'tgv_direct_share': k['direct_share'], 'conn_base': k['base'],
                'tgv_journeys': aj + kj, 'tgv_benefit': ab + kb,
                'reg_journeys': g['new'], 'reg_benefit': g['benefit'], 'reg_fares': g['fares'], 'reg_saving_clock': g['avg_clock_saving'], 'reg_users': g['users'], 'reg_base': g['base'],
                'second_station_sub': g['second_station_sub'], 'second_station_ter': g['second_station_ter'], 'through_ter': g['through_ter'],
                'reg_cross_journeys': g['cross']['new'], 'reg_cross_benefit': g['cross_benefit'], 'reg_cross_today': g['cross']['today']})
    cap = 0.10 * HS_TERMINALS if capacity else 0.0                     # scenario: 10% more trains filled once the platforms no longer cap the lines
    out['tgv_capacity_journeys'] = cap
    tgv_rev = (aj + 2 * kj + cap) * FARE / 1000                         # a passenger who crosses Paris pays two fares
    out['tgv_revenue'] = tgv_rev; out['tgv_charges'] = tgv_rev * TRACK_SHARE   # ASSUMPTION: trains are added in step with passengers and the charges reach the project
    out['direct'] = {'Track charges on new TGV journeys': out['tgv_charges'], 'Fares from new regional passengers': out['reg_fares']}
    out['direct_total'] = sum(out['direct'].values()); out['direct_cover'] = out['direct_total'] / out['cost']
    out['direct_net_of_running'] = out['direct_total'] - out['om']
    time_ben = out['tgv_benefit'] + out['reg_benefit']
    # comfort and wider effects follow the regional time saving at official weights and central boarding time, unless scale_wider
    base_reg = out['reg_benefit'] if scale_wider else regional(uplift, 'eq', 0.0, realise, hall, cross)['benefit']
    comfort, wid = wider(max(0.0, base_reg))
    out.update({'time_benefit': time_ben, 'comfort': comfort, 'wider': wid, 'benefit_total': time_ben + comfort + wid,
                'cover_time': time_ben / out['cost'], 'cover_comfort': (time_ben + comfort) / out['cost'], 'cover_all': (time_ben + comfort + wid) / out['cost']})
    return out


if __name__ == '__main__':
    out = {'TH': TH, 'TH_ACCESS': TH_ACCESS, 'TR': TR, 'conn': {'central': CONN, 'high': CONN_HIGH, 'all_13000': E['conn_base']}}
    # access
    acc = {}
    for name, kw in {'central': dict(), 'ride': dict(measure='ride'), 'no_choice': dict(choice=False), 'deep2': dict(deep=2.0), 'nord_hall': dict(hall='nord')}.items():
        acc[name] = {tag: access(tag, **kw) for tag in ('clock', 'eq', 'comfort')}
    out['access'] = acc
    out['today'] = {tag: today_mean(tag) for tag in DATA}
    out['paris'] = {'today': today_mean('clock'), 'station': today_mean('clock') + acc['central']['clock']['rings']['Paris'], 'ride': today_mean('clock') + acc['ride']['clock']['rings']['Paris'],
                    'no_choice': today_mean('clock') + acc['no_choice']['clock']['rings']['Paris'], 'nord_hall': today_mean('clock') + acc['nord_hall']['clock']['rings']['Paris']}
    pts = DATA['clock'][0]; ne_ = lambda t: min(t['Nord'], t['Est'])
    out['far_stop_share'] = {'southeast': sum(min(ne_(t) + TH_ACCESS['L'], t['Montparnasse'] + TH_ACCESS['LM']) < t['Lyon'] for t in pts) / len(pts),
                             'atlantic': sum(min(ne_(t) + TH_ACCESS['M'], t['Lyon'] + TH_ACCESS['LM']) < t['Montparnasse'] for t in pts) / len(pts),
                             'north_via_lyon': sum(t['Lyon'] + TH_ACCESS['L'] < ne_(t) for t in pts) / len(pts), 'north_via_montparnasse': sum(t['Montparnasse'] + TH_ACCESS['M'] < ne_(t) for t in pts) / len(pts)}
    out['far_stop_share_comfort'] = {'southeast': sum(min(ne_(t) + TH_ACCESS['L'], t['Montparnasse'] + TH_ACCESS['LM']) < t['Lyon'] for t in DATA['comfort'][0]) / len(pts),
                                     'atlantic': sum(min(ne_(t) + TH_ACCESS['M'], t['Lyon'] + TH_ACCESS['LM']) < t['Montparnasse'] for t in DATA['comfort'][0]) / len(pts)}
    arr = [int(float(r['arr'])) for r in csv.DictReader(open(f'{M}/points.csv'))]
    by = collections.defaultdict(list)
    for a, t in zip(arr, pts): by[a].append(sum(W[k] * (tgv_times(t, 0.0, True, 'ride')[k] - t[k]) for k in W))     # with the ride counted
    out['by_arr'] = {a: S.mean(v) for a, v in sorted(by.items())}
    rows = list(csv.DictReader(open(f'{M}/points.csv')))
    out['points'] = [{'lat': float(r['lat']), 'lon': float(r['lon']), 'd': round(sum(W[k] * (tgv_times(t, 0.0)[k] - t[k]) for k in W), 2)} for r, t in zip(rows, pts)]
    out['by_dir'] = {k: {'today': S.mean(t[k] for t in pts), 'station': S.mean(tgv_times(t, 0.0)[k] for t in pts), 'ride': S.mean(tgv_times(t, 0.0, True, 'ride')[k] for t in pts),
                         'no_choice': S.mean(tgv_times(t, 0.0, False)[k] for t in pts)} for k in KEYS}
    out['share_within1'] = sum(abs(p['d']) <= 1 for p in out['points']) / len(pts); out['share_quicker'] = sum(p['d'] < -0.05 for p in out['points']) / len(pts); out['share_slower'] = sum(p['d'] > 0.05 for p in out['points']) / len(pts)
    out['max_gain'] = min(p['d'] for p in out['points'])
    out['value_of_choice'] = {tag: access_effect(tag, 0.0, True)['benefit'] - access_effect(tag, 0.0, False)['benefit'] for tag in ('eq', 'comfort')}
    out['access_effect'] = {n: access_effect('eq', **kw) for n, kw in {'central': dict(), 'ride': dict(measure='ride'), 'no_choice': dict(choice=False), 'deep2': dict(deep=2.0), 'nord_hall': dict(hall='nord')}.items()}
    out['access_effect']['comfort'] = access_effect('comfort')
    out['connecting'] = {'central': connecting(), 'high': connecting(direct_share=1.0), 'single': connecting(method='single'), 'single_high': connecting(method='single', evidence=UPLIFT_DIRECT_HIGH),
                         'model_only': connecting(method='single', evidence=0), 'all_direct': connecting(direct_share=1.0), 'none_direct': connecting(direct_share=0.0),
                         'metro_weights': connecting(weights='metro'), 'british_change': connecting(keep=CHANGE_KEEP)}
    for v in out['connecting'].values(): v.pop('parts')
    out['destinations'], out['dest_axis'] = destinations()
    out['dest'] = DEST
    out['regional'] = regional(); out['regional_high'] = regional(REG_UPLIFT_HIGH); out['regional_low'] = regional(REG_UPLIFT_LOW); out['regional_deep2'] = regional(deep=2.0)
    out['service'] = service(); out['service_full'] = service(HOUR_FULL)
    out['cost'] = cost(); out['cost_low'] = cost(RATE_LOW)['total']; out['cost_high'] = cost(RATE_HIGH)['total']
    out['layout'] = LAYOUT; out['len'] = LEN; out['link_km'] = LINK_KM; out['tunnels'] = {'corridors': TUNNELS, 'km': TUNNEL_KM, 'fee_km': FEE_KM}
    out['ter_paths'] = ter_paths(); out['ter_corridors'] = TER_CORRIDORS
    out['sub_tracks'] = SUB_TRACKS; out['reg_platforms'] = REG_PLATFORMS; out['corridor_km'] = CORRIDOR_KM
    out['rates'] = {k: v for k, v in RATE.items()}; out['rates_low'] = {k: v for k, v in RATE_LOW.items()}; out['rates_high'] = {k: v for k, v in RATE_HIGH.items()}; out['backtest'] = backtest()
    out['AF'] = AF; out['idc'] = idc(); out['ratios'] = {'comfort': R_COMFORT, 'wider': R_WIDER}
    out['params'] = {'uplift_direct': UPLIFT_DIRECT, 'uplift_direct_high': UPLIFT_DIRECT_HIGH, 'reg_uplift': REG_UPLIFT, 'reg_uplift_high': REG_UPLIFT_HIGH, 'reg_uplift_low': REG_UPLIFT_LOW, 'new_money': NEW_MONEY,
                     'build_years': BUILD_YEARS, 'om_tunnel': OM_TUNNEL, 'om_tunnel_low': OM_TUNNEL_LOW, 'om_tunnel_high': OM_TUNNEL_HIGH, 'om_station': OM_STATION, 'reg_trainkm': REG_TRAINKM, 'reg_trainkm_cost': REG_TRAINKM_COST, 'ter_trip': TER_TRIP, 'old_ne': 30.0,
                     'stop_min': STOP_MIN, 'clear_min': CLEAR_MIN, 'util': UTIL, 'per_track': PER_TRACK, 'tracks_per_direction': TRACKS_PER_DIRECTION, 'second_min': SECOND_MIN, 'ter_through_share': TER_THROUGH_SHARE, 'park_ha': PARK_HA, 'direct_share': DIRECT_SHARE,
                     'transit_share': TRANSIT_SHARE, 'cross_share': CROSS_SHARE, 'change_loss': CHANGE_LOSS, 'easy_change': EASY_CHANGE, 'cross_today': CROSS_TODAY, 'cross_out': CROSS_OUT, 'cross_change_eq': CROSS_CHANGE_EQ, 'cross_decay': CROSS_DECAY,
                     'corridor': CORRIDOR, 'sub_pair': SUB_PAIR, 'ter_run': TER_RUN, 'south_line': SOUTH_LINE, 'through_trains': THROUGH_TRAINS, 'term_share': TERM_SHARE, 'lines': LINES, 'ter': TER,
                     'change_keep': CHANGE_KEEP, 'station_keep': STATION_KEEP, 'acc_egr': ACC_EGR, 'elast': ELAST}
    Y = yearly(); out['yearly'] = Y
    out['yearly_ride'] = yearly(measure='ride')
    tests = {'Low unit prices and 10% risk': dict(R=RATE_LOW), 'High unit prices and 30% risk': dict(R=RATE_HIGH),
             'Works take 15 years, not 12': dict(years=15),
             'Every passenger takes 2 minutes longer to board than today': dict(deep=2.0),
             'TGV passengers’ ride across Paris counted against them': dict(measure='ride'),
             'Nord-Est entered from the Gare du Nord hall only': dict(hall='nord'),
             'Crowded metro time counted 25% heavier': dict(tag='comfort'),
             'Every passenger on a served pair finds a direct train': dict(direct_share=1.0),
             'A change inside one station costs as much as a change today': dict(keep=CHANGE_KEEP),
             'A change inside one station costs 11%, as in a Swiss timed timetable': dict(keep=SWISS_KEEP),
             'Cross-Paris gain as on the Paris bypass line, 57% on direct trains': dict(method='single', evidence=UPLIFT_DIRECT_HIGH),
             'Cross-Paris gain as first estimated: 37% on direct trains': dict(method='single'),
             'Cross-Paris gain from the time model only': dict(method='single', evidence=0),
             'Today’s change of station weighted like a metro trip': dict(weights='metro'),
             'Suburban traffic grows 25%': dict(uplift=REG_UPLIFT_HIGH), 'Suburban traffic grows 5%': dict(uplift=REG_UPLIFT_LOW),
             'Tunnel upkeep as on the first RER E section': dict(om_tunnel=OM_TUNNEL_HIGH), 'Tunnel upkeep at the average of the RER network': dict(om_tunnel=OM_TUNNEL_LOW),
             'Passengers crossing Paris at the top of the survey range': dict(c=CONN_HIGH), 'Half as many passengers cross Paris': dict(c=CONN / 2),
             'Half as many suburb-to-suburb trips across Paris': dict(cross=CROSS_SHARE / 2), 'Half as many more suburb-to-suburb trips across Paris': dict(cross=CROSS_SHARE * 1.5),
             'New traffic reaches 60% of the estimate': dict(realise=0.6),
             'Platforms no longer cap the lines: 10% more TGV traffic': dict(capacity=True)}
    keep = ('capex', 'cost', 'tgv_journeys', 'tgv_benefit', 'reg_journeys', 'reg_benefit', 'reg_fares', 'direct_total', 'direct_cover', 'time_benefit', 'cover_time', 'cover_all', 'benefit_total')
    out['sens'] = {k: {x: yearly(**kw)[x] for x in keep} for k, kw in tests.items()}
    d2 = yearly(deep=2.0, scale_wider=True); out['deep2_scaled'] = {x: d2[x] for x in keep}
    # official discount rates instead of 3% (benefits held flat)
    def at_rate(r):
        global r_, AF
        r0, a0 = r_, AF
        r_ = r; AF = r / (1 - (1 + r) ** -n_)
        y = yearly(); res = {'all': y['cover_all'], 'time': y['cover_time']}
        r_, AF = r0, a0
        return res
    out['rate_tests'] = {'3.6': at_rate(0.036), '4.6': at_rate(0.046)}
    f = (1 + RATE['design'] + RATE['client'] + RATE['land']) * (1 + RATE['risk']); out['gross_up'] = f
    # staging (cost only): first the TGV axis from the north and east to the south-east, with Nord-Est, Gare de Lyon and line H to
    # Saint-Lazare; then Montparnasse with its TGV side, the link, and the regional express and line N tunnels (version 4)
    def stage(km, plat_m, halls, junc, portals, sid, london):
        hard = km * (RATE['tunnel_civil'] + RATE['tunnel_systems']) + plat_m * RATE['platform_m'] + sum(RATE['hall'][h] for h in halls) + junc * RATE['junction'] + portals * RATE['portal'] + sid + london
        return {'hard': hard, 'total': hard * f, 'km': km, 'platform_m': plat_m}
    skm = {k: sum(CORRIDOR_KM[c] for c in v) for k, v in STAGE_CORRIDORS.items()}
    km1 = skm['first'] + TUNNEL_KM['h']; km2 = skm['second'] + LINK_KM + TUNNEL_KM['n']
    pm1 = 6 * LEN['hs'] + 8 * LEN['hs'] + 2 * 6 * LEN['sub']; pm2 = cost()['platform_total'] - pm1     # stage 1: Nord-Est TGV and H, Gare de Lyon (8), Saint-Lazare
    tl1 = 0.5                       # TER links in stage 1: the Nord-Est throats and the north and east portal ramps; the rest (0.15) with Montparnasse
    out['stages'] = {'first': stage(km1, pm1, ['Nord', 'Est', 'Lyon'], JUNCTIONS['tgv'] - 2, PORTALS['tgv'] - 1 + PORTALS['h'], 0.4 + tl1, RATE['london_hall']),
                     'second': stage(km2, pm2, ['Montparnasse'], 2 + JUNCTIONS['ter'], 1 + PORTALS['ter'] + PORTALS['n'], 0.2 + RATE['ter_links'] - tl1, 0.0)}
    out['stages']['first']['route_km'] = skm['first'] + TUNNEL_KM['h']; out['stages']['second']['route_km'] = km2
    assert abs(out['stages']['first']['total'] + out['stages']['second']['total'] - cost()['total']) < 1e-9
    # things not in the central estimate
    dep = (HS_TERMINALS - 2 * CONN) / 2
    out['extras'] = {'margin_5min': dep * 5 / 60 * 1.5 * VOT_LD / 1000, 'departures': dep,
                     'fleet_sets_low': 310 * 0.5 / 13, 'fleet_sets_high': 310 * 0.5 / 7, 'capacity_revenue': 0.10 * HS_TERMINALS * FARE / 1000, 'capacity_journeys': 0.10 * HS_TERMINALS,
                     'south_growth': (HOUR_FULL['Atlantic'] + HOUR_FULL['Southeast']) / (HOUR_TODAY['Atlantic'] + HOUR_TODAY['Southeast']) - 1,
                     'hall_today': 1.0 + 200 / 1.25 / 60, 'hall_deep': 1.0 + 70 / 0.65 / 60 + 0.5 + 50 / 1.25 / 60,
                     'co2_kt': Y['tgv_journeys'] * 0.25 * 450 * 0.1, 'park_ha': PARK_HA}
    out['station_total'] = {n: v * f for n, v in out['cost']['station_cost'].items()}
    os.makedirs(f'{M}/../outputs', exist_ok=True)
    json.dump(out, open(f'{M}/../outputs/nordest.json', 'w'), indent=1, default=lambda o: sorted(o) if isinstance(o, set) else o)
    P = lambda x: round(x, 3) if isinstance(x, float) else x
    print('CONN', P(CONN), 'IDC', P(idc()))
    print('PARIS', {k: P(v) for k, v in out['paris'].items()})
    for n, v in out['access_effect'].items(): print('acc eff', n, {k: P(x) for k, x in v.items()})
    for n, v in out['connecting'].items(): print('conn', n, {k: P(x) for k, x in v.items() if k != 'pairs'})
    g = out['regional']; print('regional', {k: P(v) for k, v in g.items() if k not in ('rows', 'saving_eq', 'saving_clock', 'second_station_share')})
    print('service', {k: P(v) for k, v in out['service'].items() if k != 'hour'}); print('service full', {k: P(v) for k, v in out['service_full'].items() if k != 'hour'})
    c = out['cost']; print('COST', P(c['total']), 'low', P(out['cost_low']), 'high', P(out['cost_high']), {a: P(b) for a, b in c['items'].items()}, 'hard', P(c['hard']), c['platform_m'], c['tunnel_km'], c['portals'], c['junctions'])
    for b in out['backtest']: print('back', b['name'], P(b['model_no_risk']), P(b['model_with_risk']), b['actual'], b['actual_high'])
    print('YEARLY', {k: P(v) for k, v in Y.items() if not isinstance(v, dict)})
    print('STAGES', {k: {a: P(b) for a, b in v.items()} for k, v in out['stages'].items()})
    for k, v in out['sens'].items(): print('S', k[:58].ljust(58), P(v['cover_time']), P(v['cover_all']), '| tgv', P(v['tgv_journeys']), P(v['direct_total']))
    print('deep2 scaled', P(out['deep2_scaled']['cover_all']), 'rate tests', out['rate_tests'])
