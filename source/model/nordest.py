"""The triangle: three deep through stations (Paris Nord-Est under Gare du Nord and Gare de l'Est, Gare de Lyon, Montparnasse),
joined by two pairs of tunnels on a Y and a direct TGV link between the two southern stations. Access, service plan, bottom-up cost,
traffic, direct and indirect return.

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
Every assumption that is not sourced is marked ASSUMPTION.
"""
import csv, json, statistics as S, collections, math
from estimate import E, W, PSH, SH, gain, loss, VOT_LD, VOT_IDF, VOT_TER, ELAST, HS_TERMINALS, T_OLD, T_NEW, CONN_TRAIN, ACC_EGR, FARE

import os
M = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inputs')      # model inputs: access times by point and by commune
KEYS = ['Nord', 'Est', 'Lyon', 'Montparnasse']
TH = {'L': 10.0, 'M': 11.0, 'LM': 6.0}  # TGV ride between Nord-Est and Lyon / Montparnasse, and Montparnasse to Lyon by the link, stop included (ASSUMPTION)
REVERSE = 8.0                           # minutes for the rare train that turns back at Nord-Est (ASSUMPTION; 3 to 12 in French practice)
TR = {'L': 6.0, 'M': 7.0}              # regional train ride between the same stations (ASSUMPTION: 5 to 6 km at 60 km/h plus a stop)
ring = lambda d: 'Paris' if d == '75' else ('Petite couronne' if d in ('92', '93', '94') else 'Grande couronne')
DATA = {}
for tag, pf, rf in (('clock', 'points.csv', 'regional.json'), ('eq', 'points_weighted.csv', 'regional_weighted.json'), ('comfort', 'points_comfort.csv', 'regional_comfort.json')):
    DATA[tag] = ([{k: float(r['t_' + k]) for k in KEYS} for r in csv.DictReader(open(f'{M}/{pf}'))], json.load(open(f'{M}/{rf}'))['rows'])
WALKW = {'clock': 1.0, 'eq': 2.0, 'comfort': 2.0}

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
    th = TH if measure == 'ride' else {'L': 0.0, 'M': 0.0, 'LM': 0.0}
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
UPLIFT_DIRECT = 0.37                    # traffic gained when a change of train is removed (British ticket data, Wheat and Wardman)
UPLIFT_DIRECT_HIGH = 0.57               # Paris bypass line against the no-project case; includes new stations and time savings (derived)
DIRECT_SHARE = 0.5                      # share of passengers on a pair served by direct trains who find one for their own trip (ASSUMPTION)
CHANGE_METRO = (20 + 20 * 2 + 17.5 * 1.5, 5 * 2 + 7.5 * 1.5)       # change weighted like a metro trip: today, and inside one station


def connecting(c=None, evidence=UPLIFT_DIRECT, tag='eq', direct_share=DIRECT_SHARE, weights='official'):
    """Pairs of directions in the triangle: every pair except north to east has direct trains, none of them reversing.
    The Atlantic to south-east pair runs by the direct link."""
    c = CONN if c is None else c
    _, ae = trip_eq(tag)
    chg = 2 * T_NEW if weights == 'official' else CHANGE_METRO[1]
    out = {'new': 0.0, 'ben': 0.0, 'saving': 0.0, 'direct_share': 0.0, 'pairs': {}}
    for p, s in PSH.items():
        ps = set(p)
        old_eq = 2 * OLD_CLOCK[frozenset(p)] if weights == 'official' else CHANGE_METRO[0] * OLD_CLOCK[frozenset(p)] / T_OLD
        old = CONN_TRAIN + old_eq + ae
        if ps == {'Nord', 'Est'}:
            served, t_direct, t_change = False, None, chg
        elif ps == {'Lyon', 'Montparnasse'}:
            served, t_direct, t_change = True, TH['LM'], TH['LM'] + chg
        else:
            ride = sum(TH['L'] if x == 'Lyon' else TH['M'] for x in ps if x in ('Lyon', 'Montparnasse'))    # riding between the Paris stops
            served, t_direct, t_change = True, ride, ride + chg
        parts = [(direct_share, t_direct, True), (1 - direct_share, t_change, False)] if served else [(1.0, t_change, False)]
        for sh, repl, is_direct in parts:
            q = c * s * sh; new = CONN_TRAIN + repl + ae
            up = evidence if (evidence and is_direct) else (new / old) ** ELAST - 1
            out['new'] += q * up; out['saving'] += s * sh * (old - new); out['ben'] += gain(q, q * up, old - new, VOT_LD)
            if is_direct: out['direct_share'] += s * sh
        out['pairs']['-'.join(p)] = {'share': s, 'served': served, 'direct': t_direct, 'change': t_change, 'change_clock': t_change - chg + T_NEW, 'old_clock': OLD_CLOCK[frozenset(p)]}
    out['uplift'] = out['new'] / c; out['base'] = c
    return out


# ------------------------------------------------------------------ 3. regional trains
LINES = {'H': 54.6, 'K': 4.1, 'P': 27.3, 'N': 27.3, 'R': 19.1}                     # million journeys a year (derived from daily counts, unverified)
TERM_SHARE = {'H': 119900 / 215000, 'K': 119900 / 215000, 'N': 66800 / 117000, 'P': 63900 / 105000, 'R': 33000 / 70000}
TER_DAY = {'Nord': 69200, 'Montparnasse': 23800, 'Lyon': 14900, 'Est': 8100}        # TER and Intercites, weekday, 2012-13
TER = {k: v * 350 / 1e6 for k, v in TER_DAY.items()}
REG_UPLIFT = 0.15                       # suburban lines joined through a centre: 5% to 30% observed, middle about 17%; 15% taken as net of background growth
REG_UPLIFT_HIGH, REG_UPLIFT_LOW = 0.25, 0.05
TER_TRIP = 100.0                        # door-to-door equivalent minutes of an average regional express trip (ASSUMPTION)
NEW_MONEY = 0.30                        # share of extra suburban journeys paid by new customers (London 9%, Sydney 27%, East London line about 30%)
YIELD = {'transilien': 1.22, 'ter': 8.0}        # euros per journey (Ile-de-France average; regional express ASSUMPTION)
REG_TRAINKM = 2.0                       # million extra train-km a year for regional trains running on to the second station (ASSUMPTION from 1,166 trains a weekday)
REG_TRAINKM_COST = 27.5                 # euros per extra train-km: half the average cost per train-km paid by the region (ASSUMPTION)
SECOND_MIN = 1.0                        # a passenger uses the second station when it saves more than this, on the clock (ASSUMPTION)
TER_THROUGH_SHARE = 0.05                # share of regional express passengers who cross Paris today (ASSUMPTION; study point I15)


def regional_saving(tag='eq', hall='both'):
    """Average minutes saved between the train and a Paris destination, by service, when the train runs on to a second station."""
    pts = DATA[tag][0]
    def avg(fn): return S.mean(fn(t) for t in pts)
    ne = (lambda t: min(t['Nord'], t['Est'])) if hall == 'both' else (lambda t: t['Nord'])
    sv = {'H': avg(lambda t: t['Nord'] - min(ne(t), TR['L'] + t['Lyon'])), 'P': avg(lambda t: t['Est'] - min(ne(t), TR['M'] + t['Montparnasse'])),
          'N': avg(lambda t: t['Montparnasse'] - min(t['Montparnasse'], TR['M'] + ne(t))), 'R': avg(lambda t: t['Lyon'] - min(t['Lyon'], TR['L'] + ne(t)))}
    sv['K'] = sv['H']
    half = lambda t: min(ne(t), TR['L'] + t['Lyon'], TR['M'] + t['Montparnasse'])        # the passenger picks the train that runs on to the best station
    sv['TER Nord'] = avg(lambda t: t['Nord'] - half(t)); sv['TER Est'] = avg(lambda t: t['Est'] - half(t))
    sv['TER Lyon'] = sv['R']; sv['TER Montparnasse'] = sv['N']
    merge = {'H': avg(lambda t: t['Nord'] - ne(t)), 'P': avg(lambda t: t['Est'] - ne(t))}      # part of the saving that comes from entering by either hall
    return sv, merge


def regional(uplift=REG_UPLIFT, tag='eq', deep=0.0, realise=1.0, hall='both'):
    sv, merge = regional_saving(tag, hall); svc, _ = regional_saving('clock', hall)
    dd = deep * WALKW[tag]
    out = {'saving_eq': sv, 'saving_clock': svc, 'merge_part': merge, 'rows': []}
    ben = new_t = new_r = base_t = base_r = users = minutes = 0.0
    def value(u, n, s, vot):                       # existing users get the whole change; new ones half of a saving
        return gain(u, n, s, vot) if s >= 0 else -loss(u, 0.0, -s, vot)
    for l, q in LINES.items():
        u = q * TERM_SHARE[l]; s = sv[l] - dd
        n = q * uplift * realise * (max(0.0, s / sv[l]) if sv[l] > 0 else 0.0)
        ben += value(u, n, s, VOT_IDF); new_t += n; base_t += q; users += u; minutes += u * svc[l]
        out['rows'].append([l, q, u, svc[l], sv[l]])
    for k, q in TER.items():
        s = sv['TER ' + k] - dd
        n = q * ((1 - max(0.0, s) / TER_TRIP) ** ELAST - 1) * realise                 # time model: no observed case for regional express
        ben += value(q, n, s, VOT_TER); new_r += n; base_r += q; users += q; minutes += q * svc['TER ' + k]
        out['rows'].append(['TER ' + k, q, q, svc['TER ' + k], sv['TER ' + k]])
    out.update({'benefit': ben, 'new_transilien': new_t, 'new_ter': new_r, 'new': new_t + new_r, 'base': base_t + base_r, 'base_transilien': base_t, 'base_ter': base_r, 'users': users,
                'avg_clock_saving': minutes / users, 'ter_uplift': new_r / base_r,
                'fares': (new_t * NEW_MONEY * YIELD['transilien'] + new_r * YIELD['ter']) / 1000})
    out.update(second_station(hall))
    out['through_ter'] = base_r * TER_THROUGH_SHARE * (1 + UPLIFT_DIRECT) * realise          # regional express passengers crossing Paris on a through train
    return out


def second_station(hall='both', thr=SECOND_MIN):
    """Passengers who would get off at the second station: those for whom it saves more than `thr` clock minutes, by line and for regional express."""
    pts = DATA['clock'][0]
    ne = (lambda t: min(t['Nord'], t['Est'])) if hall == 'both' else (lambda t: t['Nord'])
    alt = {'H': lambda t: t['Nord'] - min(ne(t), TR['L'] + t['Lyon']), 'P': lambda t: t['Est'] - min(ne(t), TR['M'] + t['Montparnasse']),
           'N': lambda t: t['Montparnasse'] - min(t['Montparnasse'], TR['M'] + ne(t)), 'R': lambda t: t['Lyon'] - min(t['Lyon'], TR['L'] + ne(t))}
    alt['K'] = alt['H']
    half = lambda t: min(ne(t), TR['L'] + t['Lyon'], TR['M'] + t['Montparnasse'])
    alt_ter = {'Nord': lambda t: t['Nord'] - half(t), 'Est': lambda t: t['Est'] - half(t), 'Lyon': alt['R'], 'Montparnasse': alt['N']}
    share = lambda fn: sum(1 for t in pts if fn(t) > thr) / len(pts)
    sub = {l: q * TERM_SHARE[l] * share(alt[l]) for l, q in LINES.items()}
    ter = {k: q * share(alt_ter[k]) for k, q in TER.items()}
    return {'second_station_sub': sum(sub.values()), 'second_station_ter': sum(ter.values()), 'second_station_share': {**{l: share(alt[l]) for l in LINES}, **{'TER ' + k: share(alt_ter[k]) for k in TER}}}


# ------------------------------------------------------------------ 4. service plan and station sizes
HOUR_TODAY = {'Atlantic': 12, 'Southeast': 12, 'North': 8, 'East': 4}      # TGVs per hour and direction in a standard busy hour (ASSUMPTION)
HOUR_FULL = {'Atlantic': 15, 'Southeast': 16, 'North': 8, 'East': 4}       # southern lines at their planned capacity (sourced); north and east unchanged (ASSUMPTION)
STOP_MIN = 4.0                          # minutes a TGV stands at a through platform (ASSUMPTION; 3 is the TGV norm, 4 to 5 at the largest hubs)
CLEAR_MIN = 3.0                         # minutes from a departure to the next arrival on the same track (ASSUMPTION)
UTIL = 0.65                             # share of that cycle a timetable can use and still absorb late trains (ASSUMPTION; 60 to 75% in practice)
PER_TRACK = 60 * UTIL / (STOP_MIN + CLEAR_MIN)                             # trains a platform track takes an hour: about 5.6
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
        'design': 0.12, 'client': 0.08, 'land': 0.07,
        'risk': 0.15}               # the unit prices are final costs or contracts and already hold past overruns (ASSUMPTION: 15%; 10% low, 30% high)
RATE_LOW = dict(RATE, tunnel_civil=0.100, tunnel_systems=0.035, platform_m=0.00055, risk=0.10)
RATE_HIGH = dict(RATE, tunnel_civil=0.170, tunnel_systems=0.070, platform_m=0.0014, risk=0.30)
# route km of the six corridors of the Y, read from maps (ASSUMPTION). The four approach corridors end where the tunnels come up on
# the existing surface tracks: at the ring road for the north, south-east and Atlantic lines, at Rosa Parks just inside it for the
# east. At 35 mm per metre a tunnel 35 to 40 m deep reaches the surface in 1.0 to 1.2 km, so it need not stay underground any further.
# Earlier the portals were beyond the ring road (Saint-Denis 5.0, Pantin 4.5, Maisons-Alfort 7.0, Clamart 6.0: 33.5 km in all).
CORRIDOR_KM = {'north': 2.4, 'east': 2.7, 'nelyon': 5.0, 'nemont': 6.0, 'southeast': 2.9, 'atlantic': 2.8}
ROUTE_KM = sum(CORRIDOR_KM.values())
STAGE_CORRIDORS = {'first': ('north', 'east', 'nelyon', 'southeast'), 'second': ('nemont', 'atlantic')}
LINK_KM = 5.0                       # the direct TGV link between the city ends of Montparnasse and Gare de Lyon (ASSUMPTION: 4.5 to 6 km)
RADIALS = 4                         # corridors that come to the surface: north, east, southeast, Atlantic
# stations: TGV tracks by direction from the service rule (3 each way); regional express and suburban tracks as in the reference case (ASSUMPTION)
LAYOUT = {'pairs': 2, 'halls': ['Nord', 'Est', 'Lyon', 'Montparnasse'],
          'stations': {'Paris Nord-Est': {'hs': 6, 'ter': 6, 'sub': 4}, 'Gare de Lyon': {'hs': 6, 'ter': 4, 'sub': 2}, 'Montparnasse': {'hs': 6, 'ter': 4, 'sub': 2}}}
LEN = {'hs': 400, 'ter': 350, 'sub': 225}   # platform lengths: a double TGV; regional express trains of 270 to 330 m; suburban as on RER E


def cost(R=RATE, L=LAYOUT):
    portals = RADIALS * L['pairs']                                         # one portal and tie-in per pair of tracks and per radial
    junctions = 2 * L['pairs'] + 2                                         # per pair: where north and east meet, where the two southern corridors part; two more where the link joins
    km = ROUTE_KM * L['pairs'] + LINK_KM
    plat = {n: sum(v * LEN[k] for k, v in s.items()) for n, s in L['stations'].items()}
    items = {'Tunnels, civil works': km * R['tunnel_civil'], 'Tunnels, rail systems': km * R['tunnel_systems'],
             'Stations': sum(plat.values()) * R['platform_m'], 'Historic halls': sum(R['hall'][h] for h in L['halls']),
             'Underground junctions': junctions * R['junction'], 'Portals and links to existing lines': portals * R['portal'], 'Sidings and depot links': R['sidings'],
             'Control hall for London trains': R['london_hall']}
    hard = sum(items.values())
    soft = hard * (R['design'] + R['client']); land = hard * R['land']
    risk = (hard + soft + land) * R['risk']
    return {'tunnel_km': km, 'link_km': LINK_KM, 'platform_m': plat, 'platform_total': sum(plat.values()), 'tracks': {n: sum(s.values()) for n, s in L['stations'].items()}, 'detail': L['stations'],
            'portals': portals, 'junctions': junctions, 'items': items, 'station_cost': {n: v * R['platform_m'] for n, v in plat.items()},
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
           hall='both', weights='official', realise=1.0, years=BUILD_YEARS, scale_wider=False, om_tunnel=None):
    out = yearly_cost(R, years, om_tunnel)
    a = access_effect(tag, deep, True, measure, c, shares, hall); k = connecting(c, evidence, tag, weights=weights); g = regional(uplift, tag, deep, realise, hall)
    aj, kj = a['journeys'] * (realise if a['journeys'] > 0 else 1.0), k['new'] * realise
    ab = a['benefit'] - (a['journeys'] - aj) * abs(a['minutes']) / 120 * VOT_LD / 1000
    kb = k['ben'] - (k['new'] - kj) * k['saving'] / 120 * VOT_LD / 1000
    out.update({'tgv_access_min': a['minutes'], 'tgv_access_journeys': aj, 'tgv_access_benefit': ab,
                'tgv_conn_journeys': kj, 'tgv_conn_benefit': kb, 'tgv_conn_uplift': kj / k['base'], 'tgv_conn_saving': k['saving'], 'tgv_direct_share': k['direct_share'], 'conn_base': k['base'],
                'tgv_journeys': aj + kj, 'tgv_benefit': ab + kb,
                'reg_journeys': g['new'], 'reg_benefit': g['benefit'], 'reg_fares': g['fares'], 'reg_saving_clock': g['avg_clock_saving'], 'reg_users': g['users'], 'reg_base': g['base'],
                'second_station_sub': g['second_station_sub'], 'second_station_ter': g['second_station_ter'], 'through_ter': g['through_ter']})
    cap = 0.10 * HS_TERMINALS if capacity else 0.0                     # scenario: 10% more trains filled once the platforms no longer cap the lines
    out['tgv_capacity_journeys'] = cap
    tgv_rev = (out['tgv_journeys'] + cap) * FARE / 1000
    out['tgv_revenue'] = tgv_rev; out['tgv_charges'] = tgv_rev * TRACK_SHARE   # ASSUMPTION: trains are added in step with passengers and the charges reach the project
    out['direct'] = {'Track charges on new TGV journeys': out['tgv_charges'], 'Fares from new regional passengers': out['reg_fares']}
    out['direct_total'] = sum(out['direct'].values()); out['direct_cover'] = out['direct_total'] / out['cost']
    out['direct_net_of_running'] = out['direct_total'] - out['om']
    time_ben = out['tgv_benefit'] + out['reg_benefit']
    # comfort and wider effects follow the regional time saving at official weights and central boarding time, unless scale_wider
    base_reg = out['reg_benefit'] if scale_wider else regional(uplift, 'eq', 0.0, realise, hall)['benefit']
    comfort, wid = wider(max(0.0, base_reg))
    out.update({'time_benefit': time_ben, 'comfort': comfort, 'wider': wid, 'benefit_total': time_ben + comfort + wid,
                'cover_time': time_ben / out['cost'], 'cover_comfort': (time_ben + comfort) / out['cost'], 'cover_all': (time_ben + comfort + wid) / out['cost']})
    return out


if __name__ == '__main__':
    out = {'TH': TH, 'TR': TR, 'conn': {'central': CONN, 'high': CONN_HIGH, 'all_13000': E['conn_base']}}
    # access
    acc = {}
    for name, kw in {'central': dict(), 'ride': dict(measure='ride'), 'no_choice': dict(choice=False), 'deep2': dict(deep=2.0), 'nord_hall': dict(hall='nord')}.items():
        acc[name] = {tag: access(tag, **kw) for tag in ('clock', 'eq', 'comfort')}
    out['access'] = acc
    out['today'] = {tag: today_mean(tag) for tag in DATA}
    out['paris'] = {'today': today_mean('clock'), 'station': today_mean('clock') + acc['central']['clock']['rings']['Paris'], 'ride': today_mean('clock') + acc['ride']['clock']['rings']['Paris'],
                    'no_choice': today_mean('clock') + acc['no_choice']['clock']['rings']['Paris'], 'nord_hall': today_mean('clock') + acc['nord_hall']['clock']['rings']['Paris']}
    pts = DATA['clock'][0]; ne_ = lambda t: min(t['Nord'], t['Est'])
    out['far_stop_share'] = {'southeast': sum(min(ne_(t) + TH['L'], t['Montparnasse'] + TH['LM']) < t['Lyon'] for t in pts) / len(pts),
                             'atlantic': sum(min(ne_(t) + TH['M'], t['Lyon'] + TH['LM']) < t['Montparnasse'] for t in pts) / len(pts),
                             'north_via_lyon': sum(t['Lyon'] + TH['L'] < ne_(t) for t in pts) / len(pts), 'north_via_montparnasse': sum(t['Montparnasse'] + TH['M'] < ne_(t) for t in pts) / len(pts)}
    out['far_stop_share_comfort'] = {'southeast': sum(min(ne_(t) + TH['L'], t['Montparnasse'] + TH['LM']) < t['Lyon'] for t in DATA['comfort'][0]) / len(pts),
                                     'atlantic': sum(min(ne_(t) + TH['M'], t['Lyon'] + TH['LM']) < t['Montparnasse'] for t in DATA['comfort'][0]) / len(pts)}
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
    out['connecting'] = {'central': connecting(), 'high': connecting(evidence=UPLIFT_DIRECT_HIGH), 'model_only': connecting(evidence=0),
                         'all_direct': connecting(direct_share=1.0), 'none_direct': connecting(direct_share=0.0), 'metro_weights': connecting(weights='metro')}
    out['regional'] = regional(); out['regional_high'] = regional(REG_UPLIFT_HIGH); out['regional_low'] = regional(REG_UPLIFT_LOW); out['regional_deep2'] = regional(deep=2.0)
    out['service'] = service(); out['service_full'] = service(HOUR_FULL)
    out['cost'] = cost(); out['cost_low'] = cost(RATE_LOW)['total']; out['cost_high'] = cost(RATE_HIGH)['total']
    out['layout'] = LAYOUT; out['len'] = LEN; out['link_km'] = LINK_KM
    out['rates'] = {k: v for k, v in RATE.items()}; out['rates_low'] = {k: v for k, v in RATE_LOW.items()}; out['rates_high'] = {k: v for k, v in RATE_HIGH.items()}; out['backtest'] = backtest()
    out['AF'] = AF; out['idc'] = idc(); out['ratios'] = {'comfort': R_COMFORT, 'wider': R_WIDER}
    out['params'] = {'uplift_direct': UPLIFT_DIRECT, 'uplift_direct_high': UPLIFT_DIRECT_HIGH, 'reg_uplift': REG_UPLIFT, 'reg_uplift_high': REG_UPLIFT_HIGH, 'reg_uplift_low': REG_UPLIFT_LOW, 'new_money': NEW_MONEY,
                     'build_years': BUILD_YEARS, 'om_tunnel': OM_TUNNEL, 'om_tunnel_low': OM_TUNNEL_LOW, 'om_tunnel_high': OM_TUNNEL_HIGH, 'om_station': OM_STATION, 'reg_trainkm': REG_TRAINKM, 'reg_trainkm_cost': REG_TRAINKM_COST, 'ter_trip': TER_TRIP, 'old_ne': 30.0,
                     'stop_min': STOP_MIN, 'clear_min': CLEAR_MIN, 'util': UTIL, 'per_track': PER_TRACK, 'tracks_per_direction': TRACKS_PER_DIRECTION, 'second_min': SECOND_MIN, 'ter_through_share': TER_THROUGH_SHARE, 'park_ha': PARK_HA, 'direct_share': DIRECT_SHARE}
    Y = yearly(); out['yearly'] = Y
    out['yearly_ride'] = yearly(measure='ride')
    tests = {'Low unit prices and 10% risk': dict(R=RATE_LOW), 'High unit prices and 30% risk': dict(R=RATE_HIGH),
             'Works take 15 years, not 12': dict(years=15),
             'Every passenger takes 2 minutes longer to board than today': dict(deep=2.0),
             'TGV passengers’ ride across Paris counted against them': dict(measure='ride'),
             'Nord-Est entered from the Gare du Nord hall only': dict(hall='nord'),
             'Crowded metro time counted 25% heavier': dict(tag='comfort'),
             'Direct trains gain 57%, as on the Paris bypass line': dict(evidence=UPLIFT_DIRECT_HIGH),
             'Cross-Paris gain from the time model only': dict(evidence=0),
             'Today’s change of station weighted like a metro trip': dict(weights='metro'),
             'Suburban traffic grows 25%': dict(uplift=REG_UPLIFT_HIGH), 'Suburban traffic grows 5%': dict(uplift=REG_UPLIFT_LOW),
             'Tunnel upkeep as on the first RER E section': dict(om_tunnel=OM_TUNNEL_HIGH), 'Tunnel upkeep at the average of the RER network': dict(om_tunnel=OM_TUNNEL_LOW),
             'Passengers crossing Paris at the top of the survey range': dict(c=CONN_HIGH), 'Half as many passengers cross Paris': dict(c=CONN / 2),
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
    # staging (cost only): first the north to south-east axis with Nord-Est and Gare de Lyon, then Montparnasse with the link
    def stage(km, stations, halls, junc, portals, sid, london):
        c = cost(); hard = km * (RATE['tunnel_civil'] + RATE['tunnel_systems']) + sum(c['station_cost'][n] for n in stations) + sum(RATE['hall'][h] for h in halls) + junc * RATE['junction'] + portals * RATE['portal'] + sid + london
        return {'hard': hard, 'total': hard * f, 'km': km}
    skm = {k: sum(CORRIDOR_KM[c] for c in v) for k, v in STAGE_CORRIDORS.items()}
    out['stages'] = {'first': stage(skm['first'] * LAYOUT['pairs'], ['Paris Nord-Est', 'Gare de Lyon'], ['Nord', 'Est', 'Lyon'], 4, 6, 0.4, RATE['london_hall']),
                     'second': stage(skm['second'] * LAYOUT['pairs'] + LINK_KM, ['Montparnasse'], ['Montparnasse'], 2, 2, 0.2, 0.0)}
    for k in skm: out['stages'][k]['route_km'] = skm[k] + (LINK_KM if k == 'second' else 0.0)
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
