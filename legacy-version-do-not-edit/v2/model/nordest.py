"""Paris Nord-Est configuration: no Pleyel hub; one deep hub under Gare du Nord and Gare de l'Est, deep through
stations under Gare de Lyon and Montparnasse. Access, service plan, bottom-up cost, traffic, direct and indirect return.

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
import estimate as EST
from estimate import E, W, PSH, SH, gain, loss, VOT_LD, VOT_IDF, VOT_TER, ELAST, HS_TERMINALS, T_OLD, T_NEW, CONN_TRAIN, ACC_EGR, FARE
from model import TRAIN_DELTA

import os
M = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inputs')      # model inputs: access times by point and by commune
KEYS = ['Nord', 'Est', 'Lyon', 'Montparnasse']
TH = {'L': 10.0, 'M': 11.0}            # TGV ride between Nord-Est and Lyon / Montparnasse, stop included (ASSUMPTION)
REVERSE = 8.0                           # minutes for a train to change direction at a platform (ASSUMPTION; 3 to 12 in French practice)
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
def tgv_times(t, deep, choice=True, pairing='free', hall='both'):
    """Minutes to the train by direction. choice=False: only the station that serves the direction today (merged Nord-Est).
    hall='both': Nord-Est is entered from either historic hall; 'nord': from the Gare du Nord hall only."""
    ne = min(t['Nord'], t['Est']) if hall == 'both' else t['Nord']
    if not choice:
        return {'Nord': ne + deep, 'Est': ne + deep, 'Lyon': t['Lyon'] + deep, 'Montparnasse': t['Montparnasse'] + deep}
    viaL, viaM = min(ne, t['Lyon'] + TH['L']), min(ne, t['Montparnasse'] + TH['M'])
    if pairing == 'free':                      # trains to the north and to the east come half from each southern corridor
        north = east = 0.5 * viaL + 0.5 * viaM
    else:                                      # fixed corridors: north with southeast, east with Atlantic
        north, east = viaL, viaM
    lyon, mont = min(t['Lyon'], ne + TH['L']), min(t['Montparnasse'], ne + TH['M'])
    if pairing == 'free':                      # half of the southern trains come from the other southern branch, reversing at Nord-Est
        loop = TH['L'] + REVERSE + TH['M']
        lyon = 0.5 * lyon + 0.5 * min(lyon, t['Montparnasse'] + loop); mont = 0.5 * mont + 0.5 * min(mont, t['Lyon'] + loop)
    return {'Nord': north + deep, 'Est': east + deep, 'Lyon': lyon + deep, 'Montparnasse': mont + deep}


def access(tag='eq', deep=0.0, choice=True, pairing='free', shares=SH, hall='both'):
    pts, reg = DATA[tag]; dd = deep * WALKW[tag]
    par = [sum(W[k] * (tgv_times(t, dd, choice, pairing, hall)[k] - t[k]) for k in W) for t in pts]
    agg = collections.defaultdict(lambda: [0.0, 0.0])
    for r in reg:
        t = {k: r['t_' + k] for k in KEYS}; a = tgv_times(t, dd, choice, pairing, hall)
        g = agg[ring(r['dep'])]; g[0] += r['pop']; g[1] += r['pop'] * sum(W[k] * (a[k] - t[k]) for k in W)
    rings = {'Paris': S.mean(par), 'Petite couronne': agg['Petite couronne'][1] / agg['Petite couronne'][0], 'Grande couronne': agg['Grande couronne'][1] / agg['Grande couronne'][0]}
    return {'rings': rings, 'all': sum(shares[k] * rings[k] for k in shares), 'paris_share_quicker': sum(x < 0 for x in par) / len(par)}


def today_mean(tag):
    return S.mean(sum(W[k] * t[k] for k in W) for t in DATA[tag][0])


def trip_eq(tag):
    ratio = today_mean(tag) / today_mean('clock')
    return (212.0 - ACC_EGR) + ACC_EGR * ratio, ACC_EGR * ratio


def access_effect(tag='eq', deep=0.0, choice=True, pairing='free', c=None, shares=SH, hall='both'):
    c = CONN if c is None else c
    d = access(tag, deep, choice, pairing, shares, hall)['all']
    teq, _ = trip_eq(tag)
    idf = HS_TERMINALS - 2 * c
    dj = idf * ((1 + d / teq) ** ELAST - 1)
    ben = gain(idf, dj, -d, VOT_LD) if d < 0 else -loss(idf, -dj, d, VOT_LD)
    return {'minutes': d, 'journeys': dj, 'benefit': ben, 'idf': idf}


# ------------------------------------------------------------------ 2. passengers who cross Paris
DIRECT_CORR = [{'Lyon', 'Nord'}, {'Montparnasse', 'Est'}]
UPLIFT_DIRECT = 0.37                    # traffic gained when a change of train is removed (British ticket data, Wheat and Wardman)
UPLIFT_DIRECT_HIGH = 0.57               # Paris bypass line against the no-project case; includes new stations and time savings (derived)
DIRECT_SHARE = 0.5                      # share of passengers on a pair served by direct trains who find one for their own trip (ASSUMPTION)
CHANGE_METRO = (20 + 20 * 2 + 17.5 * 1.5, 5 * 2 + 7.5 * 1.5)       # change weighted like a metro trip: today, and inside one station


def connecting(c=None, pairing='free', evidence=UPLIFT_DIRECT, tag='eq', direct_share=DIRECT_SHARE, layout='nordest', weights='official'):
    """Pairs of directions. Free pairing with reversal: every pair except north-east has direct trains.
    layout='pleyel': the same rules at a hub north of Paris, with the extra running time to reach it."""
    c = CONN if c is None else c
    _, ae = trip_eq(tag)
    chg = 2 * T_NEW if weights == 'official' else CHANGE_METRO[1]
    out = {'new': 0.0, 'ben': 0.0, 'saving': 0.0, 'direct_share': 0.0, 'pairs': {}}
    for p, s in PSH.items():
        ps = set(p)
        old_eq = 2 * OLD_CLOCK[frozenset(p)] if weights == 'official' else CHANGE_METRO[0] * OLD_CLOCK[frozenset(p)] / T_OLD
        old = CONN_TRAIN + old_eq + ae
        if layout == 'nordest':
            ride = sum(TH['L'] if x == 'Lyon' else TH['M'] for x in ps if x in ('Lyon', 'Montparnasse'))    # riding between the Paris stops
        else:
            ride = TRAIN_DELTA[p[0]] + TRAIN_DELTA[p[1]]                                                    # extra running to and from the hub
        if ps == {'Nord', 'Est'}:
            served, t_direct, t_change = False, None, ride + chg
        elif ps == {'Lyon', 'Montparnasse'}:
            served, t_direct, t_change = pairing == 'free', ride + REVERSE, ride + chg
        else:
            served = pairing == 'free' or ps in DIRECT_CORR
            t_direct, t_change = ride, ride + chg
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


def regional_saving(tag='eq', hall='both'):
    """Average minutes saved between the train and a Paris destination, by service, when the train runs on to a second station."""
    pts = DATA[tag][0]
    def avg(fn): return S.mean(fn(t) for t in pts)
    ne = (lambda t: min(t['Nord'], t['Est'])) if hall == 'both' else (lambda t: t['Nord'])
    sv = {'H': avg(lambda t: t['Nord'] - min(ne(t), TR['L'] + t['Lyon'])), 'P': avg(lambda t: t['Est'] - min(ne(t), TR['M'] + t['Montparnasse'])),
          'N': avg(lambda t: t['Montparnasse'] - min(t['Montparnasse'], TR['M'] + ne(t))), 'R': avg(lambda t: t['Lyon'] - min(t['Lyon'], TR['L'] + ne(t)))}
    sv['K'] = sv['H']
    half = lambda t: 0.5 * min(ne(t), TR['L'] + t['Lyon']) + 0.5 * min(ne(t), TR['M'] + t['Montparnasse'])
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
    return out


# ------------------------------------------------------------------ 4. service plan and station sizes
HOUR_TODAY = {'Atlantic': 12, 'Southeast': 12, 'North': 8, 'East': 4}      # TGVs per hour and direction in a standard busy hour (ASSUMPTION)
HOUR_FULL = {'Atlantic': 15, 'Southeast': 16, 'North': 8, 'East': 4}       # southern lines at their planned capacity (sourced); north and east unchanged (ASSUMPTION)
PER_TRACK = 5.0                                                            # stops of 4 minutes an hour on one through platform track (built stations: 4 to 6)
STOP_MIN = 4.0
def service(H=HOUR_TODAY):
    A, SE, N, Ea = H['Atlantic'], H['Southeast'], H['North'], H['East']
    flows = {'Atlantic to north': N / 2, 'Atlantic to east': Ea / 2, 'Southeast to north': N / 2, 'Southeast to east': Ea / 2}
    through = N + Ea
    rev = min(A - through / 2, SE - through / 2)                           # trains that pair with the other southern line, reversing at Nord-Est
    spare = (A - through / 2 - rev) + (SE - through / 2 - rev)             # trains left with no partner: they turn back at Nord-Est too
    flows['Atlantic to southeast, reversing at Nord-Est'] = rev
    rev_equiv = (REVERSE + 1.0) / STOP_MIN                                 # a reversing train holds a platform as long as 2.25 stopping trains
    stops = 2 * through + (2 * rev + spare) * rev_equiv                    # stop-equivalents an hour, both directions
    return {'hour': H, 'flows': flows, 'through_each_way': through, 'reversing_each_way': rev, 'spare': spare, 'rev_equiv': rev_equiv,
            'nordest_stops': stops, 'nordest_tracks_calc': stops / PER_TRACK, 'lyon_tracks_calc': 2 * SE / PER_TRACK, 'montparnasse_tracks_calc': 2 * A / PER_TRACK}


# ------------------------------------------------------------------ 5. cost, built up from unit rates of built projects (2026 euros, bn)
RATE = {'tunnel_civil': 0.130,      # per km of twin-track tunnel, with shafts (Grand Paris 0.10 to 0.13, Elizabeth line 0.14 to 0.17, Zurich 0.13 to 0.15)
        'tunnel_systems': 0.045,    # per km: track, power, signalling, ventilation (Grand Paris 0.03 to 0.06, Elizabeth line 0.10)
        'platform_m': 0.0010,       # per metre of platform track in a deep station (RER E 1999 about 0.0009 complete; RER E 2024 structures 0.0009 to 0.0014; Zurich 0.00055; London 0.0020)
        'hall': {'Nord': 0.5, 'Est': 0.3, 'Lyon': 0.5, 'Montparnasse': 0.5},        # converting each historic hall (ASSUMPTION; Montparnasse 0.19, Austerlitz 0.6, Gare du Nord 0.76 to 1.8)
        'junction': 0.25,           # per underground junction (ASSUMPTION, no published cost)
        'portal': 0.15,             # per portal and tie-in of one track pair to an existing line (ASSUMPTION)
        'sidings': 0.6,             # turnback sidings and depot links (ASSUMPTION)
        'design': 0.12, 'client': 0.08, 'land': 0.07, 'risk': 0.30}
RATE_LOW = dict(RATE, tunnel_civil=0.100, tunnel_systems=0.035, platform_m=0.00055, risk=0.20)
RATE_HIGH = dict(RATE, tunnel_civil=0.170, tunnel_systems=0.070, platform_m=0.0014, risk=0.45)
ROUTE_KM = 33.5                     # six corridors of the reference case
RADIALS = 4                         # corridors that come to the surface: north, east, southeast, Atlantic
# stations: high-speed tracks from the service rule at full line capacity, rounded up to whole island platforms, plus a sealed pair for London trains at the hub;
# regional express (ter) and suburban (sub) tracks as in the reference case; layout B pools high-speed and regional express and saves 2 tracks a station (ASSUMPTION)
LAYOUTS = {
    'nordest': {'pairs': 3, 'tgv_extra_km': 0.0, 'halls': ['Nord', 'Est', 'Lyon', 'Montparnasse'],
                'stations': {'Paris Nord-Est': {'hs': 16, 'ter': 6, 'sub': 4}, 'Gare de Lyon': {'hs': 8, 'ter': 4, 'sub': 2}, 'Montparnasse': {'hs': 6, 'ter': 4, 'sub': 2}}},
    'nordest_lean': {'pairs': 2, 'tgv_extra_km': 0.0, 'halls': ['Nord', 'Est', 'Lyon', 'Montparnasse'],
                     'stations': {'Paris Nord-Est': {'hs': 20, 'ter': 0, 'sub': 4}, 'Gare de Lyon': {'hs': 10, 'ter': 0, 'sub': 2}, 'Montparnasse': {'hs': 8, 'ter': 0, 'sub': 2}}},
    'pleyel': {'pairs': 2, 'tgv_extra_km': 58.0, 'halls': ['Nord', 'Est', 'Lyon', 'Montparnasse'],
               'stations': {'Saint-Denis-Pleyel': {'hs': 16, 'ter': 0, 'sub': 0}, 'Paris Nord': {'hs': 0, 'ter': 6, 'sub': 4}, 'Gare de Lyon': {'hs': 0, 'ter': 4, 'sub': 2}, 'Montparnasse': {'hs': 0, 'ter': 4, 'sub': 2}}},
}
LEN = {'hs': 400, 'ter': 400, 'sub': 225}


def cost(layout, R=RATE):
    L = LAYOUTS[layout]
    networks = L['pairs'] + (1 if L['tgv_extra_km'] else 0)                 # separate pairs of tracks that reach the surface on each radial
    portals = RADIALS * networks                                           # one portal and tie-in per pair of tracks and per radial
    junctions = 2 * networks                                               # per network: where north and east meet, and where the two southern corridors part
    km = ROUTE_KM * L['pairs'] + L['tgv_extra_km']
    plat = {n: sum(v * LEN[k] for k, v in s.items()) for n, s in L['stations'].items()}
    items = {'Tunnels, civil works': km * R['tunnel_civil'], 'Tunnels, rail systems': km * R['tunnel_systems'],
             'Stations': sum(plat.values()) * R['platform_m'], 'Historic halls': sum(R['hall'][h] for h in L['halls']),
             'Underground junctions': junctions * R['junction'], 'Portals and links to existing lines': portals * R['portal'], 'Sidings and depot links': R['sidings']}
    hard = sum(items.values())
    soft = hard * (R['design'] + R['client']); land = hard * R['land']
    risk = (hard + soft + land) * R['risk']
    return {'tunnel_km': km, 'platform_m': plat, 'platform_total': sum(plat.values()), 'tracks': {n: sum(s.values()) for n, s in L['stations'].items()}, 'detail': L['stations'],
            'portals': portals, 'junctions': junctions, 'items': items, 'station_cost': {n: v * R['platform_m'] for n, v in plat.items()},
            'hard': hard, 'soft': soft, 'land': land, 'risk': risk, 'total': hard + soft + land + risk}


def backtest():
    """The same rates applied to built or priced projects (works x 1.27 for design, client and land; risk shown separately)."""
    R = RATE; f = 1 + R['design'] + R['client'] + R['land']
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


def yearly_cost(layout, R=RATE, years=BUILD_YEARS, om_tunnel=None):
    C = cost(layout, R); k = idc(years); om_tunnel = OM_TUNNEL if om_tunnel is None else om_tunnel
    renew = C['items']['Tunnels, rail systems'] * (1 + R['design'] + R['client']) * (1 + R['risk']) / (1 + r_) ** RENEW_YEAR * AF
    out = {'capex': C['total'], 'idc': k, 'capex_open': C['total'] * k, 'annuity': C['total'] * k * AF, 'renewal': renew,
           'om_infra': C['tunnel_km'] * om_tunnel + C['platform_total'] * OM_STATION, 'om_trains': REG_TRAINKM * REG_TRAINKM_COST / 1000}
    out['om'] = out['om_infra'] + out['om_trains']
    out['cost'] = out['annuity'] + out['renewal'] + out['om']
    return out


def wider(reg_benefit):
    comfort = reg_benefit * R_COMFORT
    return comfort, (reg_benefit + comfort) * R_WIDER


def yearly(layout='nordest', R=RATE, deep=0.0, pairing='free', evidence=UPLIFT_DIRECT, uplift=REG_UPLIFT, tag='eq', c=None, shares=SH, capacity=False, land_price=650 / 16,
           hall='both', weights='official', realise=1.0, years=BUILD_YEARS, scale_wider=False, om_tunnel=None):
    out = yearly_cost(layout, R, years, om_tunnel)
    a = access_effect(tag, deep, True, pairing, c, shares, hall); k = connecting(c, pairing, evidence, tag, weights=weights); g = regional(uplift, tag, deep, realise, hall)
    aj, kj = a['journeys'] * (realise if a['journeys'] > 0 else 1.0), k['new'] * realise
    ab = a['benefit'] - (a['journeys'] - aj) * abs(a['minutes']) / 120 * VOT_LD / 1000
    kb = k['ben'] - (k['new'] - kj) * k['saving'] / 120 * VOT_LD / 1000
    out.update({'tgv_access_min': a['minutes'], 'tgv_access_journeys': aj, 'tgv_access_benefit': ab,
                'tgv_conn_journeys': kj, 'tgv_conn_benefit': kb, 'tgv_conn_uplift': kj / k['base'], 'tgv_conn_saving': k['saving'], 'tgv_direct_share': k['direct_share'], 'conn_base': k['base'],
                'tgv_journeys': aj + kj, 'tgv_benefit': ab + kb,
                'reg_journeys': g['new'], 'reg_benefit': g['benefit'], 'reg_fares': g['fares'], 'reg_saving_clock': g['avg_clock_saving'], 'reg_users': g['users'], 'reg_base': g['base']})
    cap = 0.10 * HS_TERMINALS if capacity else 0.0                     # scenario: 10% more trains filled once the terminals are full
    out['tgv_capacity_journeys'] = cap
    tgv_rev = (out['tgv_journeys'] + cap) * FARE / 1000
    out['tgv_revenue'] = tgv_rev; out['tgv_charges'] = tgv_rev * TRACK_SHARE   # ASSUMPTION: trains are added in step with passengers and the charges reach the project
    land_nom = 80 * land_price / 1000; land_pv = land_nom / (1 + r_) ** 7
    out['land_nominal'] = land_nom; out['land_annual'] = land_pv * AF
    out['direct'] = {'Track charges on new TGV journeys': out['tgv_charges'], 'Fares from new regional passengers': out['reg_fares'], 'Land sales': out['land_annual']}
    out['direct_total'] = sum(out['direct'].values()); out['direct_cover'] = out['direct_total'] / out['cost']
    out['direct_net_of_running'] = out['direct_total'] - out['om']
    time_ben = out['tgv_benefit'] + out['reg_benefit']
    # comfort and wider effects follow the regional time saving at official weights and central boarding time, unless scale_wider
    base_reg = out['reg_benefit'] if scale_wider else regional(uplift, 'eq', 0.0, realise, hall)['benefit']
    comfort, wid = wider(max(0.0, base_reg))
    out.update({'time_benefit': time_ben, 'comfort': comfort, 'wider': wid, 'benefit_total': time_ben + comfort + wid,
                'cover_time': time_ben / out['cost'], 'cover_comfort': (time_ben + comfort) / out['cost'], 'cover_all': (time_ben + comfort + wid) / out['cost']})
    return out


def funding(Y):
    hs_pax = HS_TERMINALS - Y['conn_base'] + Y['tgv_journeys']                     # each passenger once
    lost = hs_pax * (1 - (1 + 2 / FARE) ** FARE_RESPONSE)                          # journeys lost to a 2 euro charge
    hs_net = (hs_pax - lost) * 2 / 1000 - lost * FARE * TRACK_SHARE / 1000         # charge on the journeys that remain, less the track charges of those lost
    reg_pax = (Y['reg_base'] + Y['reg_journeys']) * Y['reg_users'] / Y['reg_base']  # journeys that reach a Paris station, so use the tunnels
    stack = [('Regional business levy, the size of the Grand Paris Express levy', 0.90, 'levy'), ('Charge of 2 euros per high-speed passenger, net', hs_net, 'charge'),
             ('Supplement of 0.50 euro per regional journey through the tunnels', reg_pax * 0.5 / 1000, 'charge'), ('Fee paid by the regional transport authority', 2 * ROUTE_KM * 0.8 / 1000, 'charge'),
             ('Track charges on new TGV journeys', Y['tgv_charges'], 'own'), ('Fares from new regional passengers', Y['reg_fares'], 'own'), ('Land sales', Y['land_annual'], 'own'),
             ('European grant of 1 billion', 1.0 * Y['idc'] * AF, 'grant')]
    tot = sum(v for _, v, _ in stack); gap = Y['cost'] - tot
    by = collections.defaultdict(float)
    for _, v, kind in stack: by[kind] += v
    grant = gap / AF / Y['idc']                                                    # grant paid during the works, 2026 euros
    return {'stack': stack, 'total': tot, 'cover': tot / Y['cost'], 'gap': gap, 'gap_capital': grant, 'gap_share_of_capex': grant / Y['capex'], 'hs_pax': hs_pax, 'hs_lost': lost,
            'hs_gross': (hs_pax - lost) * 2 / 1000, 'reg_pax': reg_pax, 'by_kind': dict(by), 'share_passengers': by['charge'] / Y['cost'], 'share_own': by['own'] / Y['cost'],
            'share_tax': (by['levy'] + by['grant'] + gap) / Y['cost'], 'levy_alone': (0.90 + gap) / 0.90}


def pleyel(c=None, evidence=UPLIFT_DIRECT, direct_share=DIRECT_SHARE):
    """The hub layout of the reference case on the same rules: free pairing and direct trains at the hub, same gain, same costs."""
    c = CONN if c is None else c
    h = EST.hub(c, E['door_eq_B'])                                                  # access: every Paris-region passenger goes to the hub
    k = connecting(c, 'free', evidence, 'eq', direct_share, layout='pleyel')
    g = regional()
    out = yearly_cost('pleyel')
    out.update({'tgv_access_journeys': -h['lost'], 'tgv_access_benefit': -h['cost'], 'tgv_conn_journeys': k['new'], 'tgv_conn_benefit': k['ben'], 'tgv_direct_share': k['direct_share'],
                'tgv_journeys': k['new'] - h['lost'], 'tgv_benefit': k['ben'] - h['cost'], 'reg_benefit': g['benefit']})
    out['time_benefit'] = out['tgv_benefit'] + out['reg_benefit']; out['comfort'], out['wider'] = wider(g['benefit'])
    out['benefit_total'] = out['time_benefit'] + out['comfort'] + out['wider']
    out['cover_time'] = out['time_benefit'] / out['cost']; out['cover_all'] = out['benefit_total'] / out['cost']
    return out


if __name__ == '__main__':
    out = {'TH': TH, 'TR': TR, 'conn': {'central': CONN, 'high': CONN_HIGH, 'all_13000': E['conn_base']}}
    # access
    acc = {}
    for name, kw in {'central': dict(), 'no_choice': dict(choice=False), 'corridor': dict(pairing='corridor'), 'deep2': dict(deep=2.0), 'nord_hall': dict(hall='nord')}.items():
        acc[name] = {tag: access(tag, **kw) for tag in ('clock', 'eq', 'comfort')}
    out['access'] = acc
    out['today'] = {tag: today_mean(tag) for tag in DATA}
    out['paris'] = {'today': today_mean('clock'), 'nordest': today_mean('clock') + acc['central']['clock']['rings']['Paris'], 'no_choice': today_mean('clock') + acc['no_choice']['clock']['rings']['Paris'],
                    'nord_hall': today_mean('clock') + acc['nord_hall']['clock']['rings']['Paris'], 'hub': today_mean('clock') + E['ring']['B']['clock']['Paris']}
    pts = DATA['clock'][0]; ne_ = lambda t: min(t['Nord'], t['Est'])
    out['far_stop_share'] = {'southeast': sum(ne_(t) + TH['L'] < t['Lyon'] for t in pts) / len(pts), 'atlantic': sum(ne_(t) + TH['M'] < t['Montparnasse'] for t in pts) / len(pts),
                             'north_via_lyon': sum(t['Lyon'] + TH['L'] < ne_(t) for t in pts) / len(pts), 'north_via_montparnasse': sum(t['Montparnasse'] + TH['M'] < ne_(t) for t in pts) / len(pts)}
    out['far_stop_share_comfort'] = {'southeast': sum(ne_(t) + TH['L'] < t['Lyon'] for t in DATA['comfort'][0]) / len(pts),
                                     'atlantic': sum(ne_(t) + TH['M'] < t['Montparnasse'] for t in DATA['comfort'][0]) / len(pts)}
    arr = [int(float(r['arr'])) for r in csv.DictReader(open(f'{M}/points.csv'))]
    by = collections.defaultdict(list)
    for a, t in zip(arr, pts): by[a].append(sum(W[k] * (tgv_times(t, 0.0)[k] - t[k]) for k in W))
    out['by_arr'] = {a: S.mean(v) for a, v in sorted(by.items())}
    rows = list(csv.DictReader(open(f'{M}/points.csv')))
    out['points'] = [{'lat': float(r['lat']), 'lon': float(r['lon']), 'd': round(sum(W[k] * (tgv_times(t, 0.0)[k] - t[k]) for k in W), 2)} for r, t in zip(rows, pts)]
    out['by_dir'] = {k: {'today': S.mean(t[k] for t in pts), 'nordest': S.mean(tgv_times(t, 0.0)[k] for t in pts), 'no_choice': S.mean(tgv_times(t, 0.0, False)[k] for t in pts)} for k in KEYS}
    out['share_within1'] = sum(abs(p['d']) <= 1 for p in out['points']) / len(pts); out['share_quicker'] = sum(p['d'] < -0.05 for p in out['points']) / len(pts); out['share_slower'] = sum(p['d'] > 0.05 for p in out['points']) / len(pts)
    out['max_gain'] = min(p['d'] for p in out['points'])
    out['value_of_choice'] = {tag: access_effect(tag, 0.0, True)['benefit'] - access_effect(tag, 0.0, False)['benefit'] for tag in ('eq', 'comfort')}
    out['access_effect'] = {n: access_effect('eq', **kw) for n, kw in {'central': dict(), 'no_choice': dict(choice=False), 'deep2': dict(deep=2.0), 'corridor': dict(pairing='corridor'), 'nord_hall': dict(hall='nord')}.items()}
    out['access_effect']['comfort'] = access_effect('comfort')
    out['connecting'] = {'central': connecting(), 'high': connecting(evidence=UPLIFT_DIRECT_HIGH), 'model_only': connecting(evidence=0), 'corridor': connecting(pairing='corridor'),
                         'all_direct': connecting(direct_share=1.0), 'none_direct': connecting(direct_share=0.0), 'metro_weights': connecting(weights='metro')}
    out['regional'] = regional(); out['regional_high'] = regional(REG_UPLIFT_HIGH); out['regional_low'] = regional(REG_UPLIFT_LOW); out['regional_deep2'] = regional(deep=2.0)
    out['service'] = service(); out['service_full'] = service(HOUR_FULL)
    out['cost'] = {k: cost(k) for k in LAYOUTS}
    out['cost_low'] = {k: cost(k, RATE_LOW)['total'] for k in LAYOUTS}; out['cost_high'] = {k: cost(k, RATE_HIGH)['total'] for k in LAYOUTS}
    out['rates'] = {k: v for k, v in RATE.items()}; out['backtest'] = backtest()
    out['AF'] = AF; out['idc'] = idc(); out['ratios'] = {'comfort': R_COMFORT, 'wider': R_WIDER}
    out['params'] = {'uplift_direct': UPLIFT_DIRECT, 'uplift_direct_high': UPLIFT_DIRECT_HIGH, 'reg_uplift': REG_UPLIFT, 'reg_uplift_high': REG_UPLIFT_HIGH, 'reg_uplift_low': REG_UPLIFT_LOW, 'new_money': NEW_MONEY,
                     'build_years': BUILD_YEARS, 'om_tunnel': OM_TUNNEL, 'om_tunnel_low': OM_TUNNEL_LOW, 'om_tunnel_high': OM_TUNNEL_HIGH, 'om_station': OM_STATION, 'reg_trainkm': REG_TRAINKM, 'reg_trainkm_cost': REG_TRAINKM_COST, 'ter_trip': TER_TRIP, 'old_ne': 30.0}
    Y = yearly(); out['yearly'] = Y; out['funding'] = funding(Y)
    YL = yearly('nordest_lean'); out['yearly_lean'] = YL; out['funding_lean'] = funding(YL)
    tests = {'Low unit prices and 20% risk': dict(R=RATE_LOW), 'High unit prices and 45% risk': dict(R=RATE_HIGH),
             'Works take 15 years, not 12': dict(years=15),
             'Every passenger takes 2 minutes longer to board than today': dict(deep=2.0),
             'Nord-Est entered from the Gare du Nord hall only': dict(hall='nord'),
             'Crowded metro time counted 25% heavier': dict(tag='comfort'),
             'Trains keep to fixed pairs of lines, none reverse': dict(pairing='corridor'),
             'Direct trains gain 57%, as on the Paris bypass line': dict(evidence=UPLIFT_DIRECT_HIGH),
             'Cross-Paris gain from the time model only': dict(evidence=0),
             'Today’s change of station weighted like a metro trip': dict(weights='metro'),
             'Suburban traffic grows 25%': dict(uplift=REG_UPLIFT_HIGH), 'Suburban traffic grows 5%': dict(uplift=REG_UPLIFT_LOW),
             'Tunnel upkeep as on the first RER E section': dict(om_tunnel=OM_TUNNEL_HIGH), 'Tunnel upkeep at the average of the RER network': dict(om_tunnel=OM_TUNNEL_LOW),
             'Passengers crossing Paris at the top of the survey range': dict(c=CONN_HIGH), 'Half as many passengers cross Paris': dict(c=CONN / 2),
             'New traffic reaches 60% of the estimate': dict(realise=0.6),
             'Terminals full: 10% more TGV traffic made possible': dict(capacity=True), 'Land at 25 million euros a hectare': dict(land_price=25.0)}
    keep = ('capex', 'cost', 'tgv_journeys', 'tgv_benefit', 'reg_journeys', 'reg_benefit', 'reg_fares', 'direct_total', 'direct_cover', 'time_benefit', 'cover_time', 'cover_all', 'benefit_total')
    out['sens'] = {k: {x: yearly(**kw)[x] for x in keep} for k, kw in tests.items()}
    out['lean_sens'] = {k: {x: yearly('nordest_lean', **kw)[x] for x in keep} for k, kw in tests.items()}
    d2 = yearly(deep=2.0, scale_wider=True); out['deep2_scaled'] = {x: d2[x] for x in keep}
    d2l = yearly('nordest_lean', deep=2.0, scale_wider=True); out['deep2_scaled_lean'] = {x: d2l[x] for x in keep}
    # official discount rates instead of 3% (benefits held flat)
    def at_rate(r):
        global r_, AF
        r0, a0 = r_, AF
        r_ = r; AF = r / (1 - (1 + r) ** -n_)
        ya, yb = yearly(), yearly('nordest_lean'); res = {'A': ya['cover_all'], 'B': yb['cover_all'], 'A_time': ya['cover_time'], 'B_time': yb['cover_time']}
        r_, AF = r0, a0
        return res
    out['rate_tests'] = {'3.6': at_rate(0.036), '4.6': at_rate(0.046)}
    # the Pleyel layout on the same rules
    out['yearly_pleyel'] = pleyel(); out['pleyel_old_method'] = {'journeys': E['hub_net_pax_B'], 'benefit': E['hub_net_ben_B']}
    out['hub'] = {'access_eq': E['access_eq_B'], 'access_clock': E['access_clock_B']}
    f = (1 + RATE['design'] + RATE['client'] + RATE['land']) * (1 + RATE['risk']); out['gross_up'] = f
    # staging: what a first stage on the north to southeast axis would contain (cost only, layout A)
    def stage(km, stations, halls, junc, portals, sid):
        c = cost('nordest'); hard = km * 3 * (RATE['tunnel_civil'] + RATE['tunnel_systems']) + sum(c['station_cost'][n] for n in stations) + sum(RATE['hall'][h] for h in halls) + junc * RATE['junction'] + portals * RATE['portal'] + sid
        return {'hard': hard, 'total': hard * f}
    out['stages'] = {'first': stage(21.5, ['Paris Nord-Est', 'Gare de Lyon'], ['Nord', 'Est', 'Lyon'], 3, 9, 0.4), 'second': stage(12.0, ['Montparnasse'], ['Montparnasse'], 3, 3, 0.2)}
    # things not in the central estimate
    dep = (HS_TERMINALS - 2 * CONN) / 2
    out['extras'] = {'margin_5min': dep * 5 / 60 * 1.5 * VOT_LD / 1000, 'departures': dep,
                     'fleet_sets_low': 310 * 0.5 / 13, 'fleet_sets_high': 310 * 0.5 / 7, 'capacity_revenue': 0.10 * HS_TERMINALS * FARE / 1000, 'capacity_journeys': 0.10 * HS_TERMINALS,
                     'south_growth': (HOUR_FULL['Atlantic'] + HOUR_FULL['Southeast']) / (HOUR_TODAY['Atlantic'] + HOUR_TODAY['Southeast']) - 1,
                     'hall_today': 1.0 + 200 / 1.25 / 60, 'hall_deep': 1.0 + 70 / 0.65 / 60 + 0.5 + 50 / 1.25 / 60,
                     'co2_kt': Y['tgv_journeys'] * 0.25 * 450 * 0.1, 'lost_charge_journeys': out['funding']['hs_lost']}
    out['station_total'] = {n: v * f for n, v in out['cost']['nordest']['station_cost'].items()}
    out['station_total_lean'] = {n: v * f for n, v in out['cost']['nordest_lean']['station_cost'].items()}
    os.makedirs(f'{M}/../outputs', exist_ok=True)
    json.dump(out, open(f'{M}/../outputs/nordest.json', 'w'), indent=1, default=lambda o: sorted(o) if isinstance(o, set) else o)
    P = lambda x: round(x, 3) if isinstance(x, float) else x
    print('CONN', P(CONN), 'IDC', P(idc()))
    print('PARIS', {k: P(v) for k, v in out['paris'].items()})
    for n, v in out['access_effect'].items(): print('acc eff', n, {k: P(x) for k, x in v.items()})
    for n, v in out['connecting'].items(): print('conn', n, {k: P(x) for k, x in v.items() if k != 'pairs'})
    g = out['regional']; print('regional', {k: P(v) for k, v in g.items() if k not in ('rows', 'saving_eq', 'saving_clock')})
    print('deep2 regional', P(out['regional_deep2']['benefit']))
    print('service', {k: P(v) for k, v in out['service'].items() if k != 'hour'}); print('service full', {k: P(v) for k, v in out['service_full'].items() if k != 'hour'})
    for k, c in out['cost'].items(): print('COST', k, P(c['total']), 'low', P(out['cost_low'][k]), 'high', P(out['cost_high'][k]), {a: P(b) for a, b in c['items'].items()}, 'hard', P(c['hard']), c['platform_m'], c['tunnel_km'], c['portals'], c['junctions'])
    for b in out['backtest']: print('back', b['name'], P(b['model_no_risk']), P(b['model_with_risk']), b['actual'], b['actual_high'])
    print('YEARLY', {k: P(v) for k, v in Y.items() if not isinstance(v, dict)})
    print('FUND', [(a[:28], P(b)) for a, b, _ in out['funding']['stack']], {k: P(v) for k, v in out['funding'].items() if k not in ('stack', 'by_kind')})
    print('LEAN', {k: P(v) for k, v in YL.items() if k in ('capex', 'cost', 'annuity', 'om', 'renewal', 'direct_cover', 'cover_time', 'cover_all')}, {k: P(v) for k, v in out['funding_lean'].items() if k in ('cover', 'gap_capital', 'gap_share_of_capex', 'levy_alone')})
    print('PLEYEL', {k: P(v) for k, v in out['yearly_pleyel'].items()})
    for k, v in out['sens'].items(): print('S', k[:55].ljust(55), P(v['cover_time']), P(v['cover_all']), '| B', P(out['lean_sens'][k]['cover_time']), P(out['lean_sens'][k]['cover_all']), '| tgv', P(v['tgv_journeys']), P(v['direct_total']))
    print('deep2 scaled', P(out['deep2_scaled']['cover_all']), P(out['deep2_scaled_lean']['cover_all']))
