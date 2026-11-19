"""How close two trains can follow each other in the TGV tunnels: the triangle and its four approaches.

    python3 model/headway.py        # -> src/sections/headway/data.json (about a minute)

The timetable (model/table_timetable.py, model/ter_timetable.py) places the trains of the busiest hour on rules stated in minutes: 3 minutes
between two TGVs on a tunnel track, 2 minutes around a regional express train (TER), 1.5 on a few places of the fullest hour. This script
checks those minutes from the physics of the trains and of the signalling, with the method planners use (blocking times, UIC code 406):

- a train may only run towards a stretch of track (a block) that the train ahead has left, with its whole length, plus a safety
  distance; it must be told so before the point where it would otherwise have to start braking; so the least time between two trains is
  set, block by block, by the braking distance of the second train, the length of the block, the length of the first train, and the
  times the signalling needs to see the block free, to move the points and to tell the train;
- in a tunnel at steady speed that gives the well-known formula; at the two ends of a tunnel the trains leave from, and arrive on, different
  platform tracks through the points of the station throat, at low speed, and a 400 m train takes long to clear them: these are the tight places;
- every train takes the same 6 minutes between two stations (the design target of the plan): the script finds the speed each kind of train
  holds in each tunnel to do so, and says where 6 minutes do not hold.

Then the three hours of the timetable are replayed: on each tunnel track, each way, every pair of trains that follow each other is given the
least time it needs, and the time the timetable gives it. The sum of the least times over the hour is the share of the hour the track
is taken (UIC 406 keeps it under 75% in the busiest hour).

Nothing here is a signalling design. Every figure that is not from the model or a source is marked ASSUMPTION; the two sets of train
performances (central and cautious) and the three signalling cases bracket what a design would fix.
"""
import contextlib, io, json, math, os
with contextlib.redirect_stdout(io.StringIO()):
    import nordest as N
    import timetable as T
    import table_timetable as TT

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'src', 'sections', 'headway', 'data.json')

# --- the trains ---------------------------------------------------------------------------------------------------------------------
LEN = {'tgv': 400.0, 'ter': 330.0}      # m: two TGV sets coupled (the platforms of the plan); three regional sets coupled (nordest.R_OPTION, unverified)
# (acceleration, braking) in m/s2, means over the speeds of the tunnels (ASSUMPTION). 'central' is what model/timetable.py already uses for
# the TGV (0.4 and 0.5); 'cautious' takes 0.3 for both, a low value for a loaded double set. The braking value is used twice: for the stop
# the train makes, and for the distance the signalling keeps free ahead of it.
PERF = {'central': {'tgv': (T.ACC, T.BRK), 'ter': (0.6, 0.7)},
        'cautious': {'tgv': (0.3, 0.3), 'ter': (0.5, 0.5)},
        'rule': {'tgv': (T.ACC, 0.6), 'ter': (0.6, 0.7)}}      # the TGV braking at the least value the European rule asks of a high-speed train (RULE below)
# What the rules say of the braking of a high-speed train, on level track (high-speed rolling stock TSI, decision 2008/232/EC, clause 4.2.4):
# service braking at least 0.6 m/s2 under 230 km/h, felt 2 s after it is asked; emergency braking at least 0.9 m/s2 under 170 km/h with wet
# rails and part of the brakes out of use (case B), felt after 3 s. And the times the European signalling leaves a driver in the examples
# of the EU Agency for Railways (Introduction to ETCS braking curves): 9 s from the indication to the permitted speed, 4 s more before the
# system brakes by itself.
RULE = {'service': 0.6, 'service_s': 2.0, 'emergency': 0.9, 'emergency_s': 3.0, 'driver_s': 9.0, 'system_s': 4.0}
V_LINE = T.V                            # 100 km/h, the most a train runs in the tunnels (model/timetable.py)
V_APPROACH = 80                         # km/h in the approach tunnels, between the ring road and the station (ASSUMPTION); 100 is tested
DEPTH = 35.0                            # m the platforms lie under the rails at the tunnel mouths (the depth drawn in the stations chapter; ASSUMPTION)
G = 9.81
RUN = TT.G_RUN * 60.0                   # 6 minutes from start to stop between two stations
MARGIN = T.MARGIN                       # 7% kept between the fastest run and the timetable (model/timetable.py)

# --- the stations -------------------------------------------------------------------------------------------------------------------
STOP_CLEAR = 30.0                       # m between the tail of a 400 m train at rest and the last points behind it (ASSUMPTION)
THROAT = {60: 300.0, 80: 450.0}         # m of points between the tunnel track and the platform tracks, by the speed over the points in km/h (ASSUMPTION)
V_THROAT = 60                           # km/h over the points, central case (ASSUMPTION); 80 is tested

# --- the signalling -----------------------------------------------------------------------------------------------------------------
OVERLAP = 50.0                          # m kept free behind a train beyond the block it has left (ASSUMPTION)
T_SYS = 10.0                            # s to see a block free, lock the route and tell the next train by radio (ASSUMPTION: ETCS level 2)
T_POINTS = 8.0                          # s more where points must move between the two trains (ASSUMPTION)
SIGNAL = {                              # block: m in the tunnel; throat: m in the station throat (None: one route across the whole throat); react: s before the braking point
    'long':  {'block': 400.0, 'throat': None,  'react': 8.0},     # ETCS level 2 on blocks as long as a train, a driver
    'short': {'block': 200.0, 'throat': 100.0, 'react': 8.0},     # short blocks, the throat released piece by piece, a driver
    'auto':  {'block': 200.0, 'throat': 100.0, 'react': 2.0},     # the same with automatic driving (ATO over ETCS)
    'rule':  {'block': 200.0, 'throat': 100.0, 'react': RULE['driver_s'] + RULE['service_s']},   # short blocks, a driver given the times of RULE
}
UIC_PEAK = N.UIC_PEAK                   # 75% of the hour at most (UIC code 406)

TUBES = {                               # km (nordest.CORRIDOR_KM, LINK_KM: read from maps, ASSUMPTION)
    'north': N.CORRIDOR_KM['north'], 'east': N.CORRIDOR_KM['east'], 'southeast': N.CORRIDOR_KM['southeast'], 'atlantic': N.CORRIDOR_KM['atlantic'],
    'nemont': N.CORRIDOR_KM['nemont'], 'nelyon': N.CORRIDOR_KM['nelyon'], 'link': N.LINK_KM}
SIDE = {'N': 'north', 'E': 'east', 'S': 'southeast', 'A': 'atlantic'}
BETWEEN = {frozenset(('MP', 'NE')): 'nemont', frozenset(('LY', 'NE')): 'nelyon', frozenset(('MP', 'LY')): 'link'}
DX = 1.0                                # m, step of the speed profiles


# --- speed profiles -----------------------------------------------------------------------------------------------------------------
def profile(dist, acc, brk, v0, v1, caps, slope=()):
    """Speed and time of the head of a train every metre from 0 to dist: never above the caps [(from m, to m, m/s)], never gaining
    more than acc nor losing more than brk, starting at v0 and ending at v1. slope: [(from m, to m, rise in m per m)], positive when the
    train climbs: gravity then takes from the acceleration and adds to the braking, and the reverse going down."""
    n = int(round(dist / DX)); cap = [1e9] * (n + 1); A = [acc] * (n + 1); B = [brk] * (n + 1)
    for a, b, v in caps:
        for i in range(max(0, int(math.floor(a / DX))), min(n, int(math.ceil(b / DX))) + 1): cap[i] = min(cap[i], v)
    for a, b, g in slope:
        for i in range(max(0, int(math.floor(a / DX))), min(n, int(math.ceil(b / DX))) + 1): A[i] = max(0.05, acc - G * g); B[i] = max(0.05, brk + G * g)
    v = [0.0] * (n + 1); v[0] = min(v0, cap[0])
    for i in range(n): v[i + 1] = min(cap[i + 1], math.sqrt(v[i] ** 2 + 2 * A[i] * DX))
    v[n] = min(v[n], v1)
    for i in range(n - 1, -1, -1): v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * B[i] * DX))
    t = [0.0] * (n + 1)
    for i in range(n): t[i + 1] = t[i] + 2 * DX / (v[i] + v[i + 1])
    return {'v': v, 't': t, 'n': n, 'brk': B}


def at(p, x):
    """Time at which the head is x metres along (beyond the end: at the last speed)."""
    if x <= 0: return p['t'][0]
    i = x / DX
    if i >= p['n']: return p['t'][-1] + (x - p['n'] * DX) / max(p['v'][-1], 0.1)
    k = int(i); f = i - k
    return p['t'][k] + f * (p['t'][k + 1] - p['t'][k])


def needs(p, s):
    """Time at which the head reaches the point where it must be told that the track is free as far as s: the first point from which it
    could no longer stop before s (with the braking it has at that point, slope included)."""
    for i in range(p['n'] + 1):
        if i * DX + p['v'][i] ** 2 / (2 * p['brk'][i]) >= s: return p['t'][i]
    return p['t'][-1]


def between(kind, km, perf, vt, vmax=None):
    """A run from a stop to a stop: slow over the points until the tail has left them, then the tunnel, then slow from the points of the
    next station to the stop. vmax None: the speed that makes the run last 6 minutes, if the train can do it."""
    acc, brk = PERF[perf][kind]; L = LEN[kind]; D = km * 1000.0; th = THROAT[vt]; v = vt / 3.6
    caps = lambda top: [(0, th + L, v), (D - LEN['tgv'] - STOP_CLEAR - th, D, v), (0, D, top)]
    fast = profile(D, acc, brk, 0.0, 0.0, caps(V_LINE))
    if vmax is not None: return profile(D, acc, brk, 0.0, 0.0, caps(vmax)), fast['t'][-1]
    if fast['t'][-1] >= RUN: return fast, fast['t'][-1]
    lo, hi = 20 / 3.6, V_LINE
    for _ in range(40):
        mid = (lo + hi) / 2
        if profile(D, acc, brk, 0.0, 0.0, caps(mid))['t'][-1] > RUN: lo = mid
        else: hi = mid
    p = profile(D, acc, brk, 0.0, 0.0, caps(hi)); p['cruise'] = hi
    return p, fast['t'][-1]


def ramp(km, vt):
    """Metres of an approach tunnel on the slope (from its mouth to the points of the station, which are level with the platforms), and the slope."""
    r = km * 1000.0 - LEN['tgv'] - STOP_CLEAR - THROAT[vt]
    return r, DEPTH / r


def arriving(kind, km, perf, vt, va=None):
    """From the mouth of an approach tunnel, going down to the station, to the stop."""
    acc, brk = PERF[perf][kind]; D = km * 1000.0; r, g = ramp(km, vt); va = (va or V_APPROACH) / 3.6
    return profile(D, acc, brk, va, 0.0, [(r, D, vt / 3.6), (0, D, va)], [(0, r, -g)])


def leaving(kind, km, perf, vt, va=None):
    """From the stop up to the mouth of an approach tunnel."""
    acc, brk = PERF[perf][kind]; D = km * 1000.0; r, g = ramp(km, vt); va = (va or V_APPROACH) / 3.6
    return profile(D, acc, brk, 0.0, va, [(0, THROAT[vt] + LEN[kind], vt / 3.6), (0, D, va)], [(D - r, D, g)])


# --- blocks -------------------------------------------------------------------------------------------------------------------------
def cut(a, b, size):
    n = max(1, int(math.ceil((b - a) / size - 1e-9)))
    return [(a + (b - a) * i / n, a + (b - a) * (i + 1) / n) for i in range(n)]


def blocks(km, sig, vt, start, end):
    """The blocks two trains share on one tunnel track, as (from, to, safety distance, seconds for the points). start / end: is there a
    station throat at that end. The two trains use different platform tracks: at the start they meet at the last points of the throat,
    at the end they part at the last points before the platforms (the worst case for both)."""
    S = SIGNAL[sig]; D = km * 1000.0; th = THROAT[vt]; out = []
    a = 0.0; b = D
    if start:
        out.append((0.0 if S['throat'] is None else th - S['throat'], th, OVERLAP, T_POINTS)); a = th
    if end:
        xd = D - LEN['tgv'] - STOP_CLEAR; b = xd - th
    out += [(x, y, OVERLAP, 0.0) for x, y in cut(a, b, S['block'])]
    if end:
        if S['throat'] is None: out.append((b, xd, 0.0, T_POINTS))
        else:
            tb = cut(b, xd, S['throat'])
            out += [(x, y, OVERLAP, 0.0) for x, y in tb[:-1]] + [(tb[-1][0], tb[-1][1], 0.0, T_POINTS)]
    return out


def least(lead, follow, kinds, perf, sig, bl, ref):
    """Least seconds between the two trains (at their start if ref is 'start', at their stop if 'stop'), and the block that sets it."""
    S = SIGNAL[sig]; Ll = LEN[kinds[0]]
    o1 = lead['t'][-1] if ref == 'stop' else 0.0; o2 = follow['t'][-1] if ref == 'stop' else 0.0
    best = (-1e9, None)
    for (s, e, ov, pts) in bl:
        free = at(lead, e + ov + Ll) - o1 + T_SYS + pts
        need = needs(follow, s) - o2 - S['react']
        if free - need > best[0]: best = (free - need, (s, e))
    return best


def steady(kind_lead, kind_follow, perf, sig, v):
    """The textbook formula in a tunnel at steady speed v (m/s)."""
    S = SIGNAL[sig]; brk = PERF[perf][kind_follow][1]
    return (v * v / (2 * brk) + S['block'] + OVERLAP + LEN[kind_lead]) / v + T_SYS + S['react']


def rule_stop(v, g):
    """Metres ahead of a train at v m/s, going down a slope g, that the signalling must hold free by the rules of RULE: the longer of the
    stop with the service brake (driver's time, then the brake's) and of the stop the system makes by itself with the emergency brake."""
    drop = G * g
    service = v * (RULE['driver_s'] + RULE['service_s']) + v * v / (2 * (RULE['service'] - drop))
    emergency = v * (RULE['driver_s'] + RULE['system_s'] + RULE['emergency_s']) + v * v / (2 * (RULE['emergency'] - drop))
    return {'service': service, 'emergency': emergency, 'most': max(service, emergency), 'service_left': RULE['service'] - drop, 'emergency_left': RULE['emergency'] - drop}


# --- the least times, tube by tube --------------------------------------------------------------------------------------------------
def tube_table(perf, sig, vt):
    """For each tube and each way of using it, the least seconds between two trains, by kind of the first and of the second."""
    out = {}
    for tube, km in TUBES.items():
        mid = tube in ('nemont', 'nelyon', 'link')
        for use in (['tun'] if mid else ['in', 'out']):
            row = {}
            for a in ('tgv', 'ter'):
                for b in ('tgv', 'ter'):
                    if use == 'tun':
                        pa, _ = between(a, km, perf, vt); pb, _ = between(b, km, perf, vt)
                        h, where = least(pa, pb, (a, b), perf, sig, blocks(km, sig, vt, True, True), 'start')
                        place = 'start' if where[1] <= THROAT[vt] + 1 else ('end' if where[1] > km * 1000 - LEN['tgv'] - STOP_CLEAR - THROAT[vt] - 1 else 'tunnel')
                    elif use == 'in':
                        pa = arriving(a, km, perf, vt); pb = arriving(b, km, perf, vt)
                        h, where = least(pa, pb, (a, b), perf, sig, blocks(km, sig, vt, False, True), 'stop')
                        place = 'end' if where[1] > km * 1000 - LEN['tgv'] - STOP_CLEAR - THROAT[vt] - 1 else 'tunnel'
                    else:
                        pa = leaving(a, km, perf, vt); pb = leaving(b, km, perf, vt)
                        h, where = least(pa, pb, (a, b), perf, sig, blocks(km, sig, vt, True, False), 'start')
                        place = 'start' if where[1] <= THROAT[vt] + 1 else 'tunnel'
                    row[a + '_' + b] = {'s': h, 'place': place}
            out[tube + '_' + use] = row
    return out


def runs(perf, vt):
    """Does each kind of train hold 6 minutes in each tunnel of the triangle, and at what speed."""
    out = {}
    for tube in ('nemont', 'nelyon', 'link'):
        out[tube] = {}
        for k in ('tgv', 'ter'):
            p, fast = between(k, TUBES[tube], perf, vt)
            out[tube][k] = {'fastest': fast, 'with_margin': fast * MARGIN, 'holds': fast * MARGIN <= RUN + 1e-6, 'holds_bare': fast <= RUN + 1e-6,
                            'cruise_kmh': p.get('cruise', V_LINE) * 3.6, 'spare': RUN - fast}
    return out


# --- the hours of the timetable, replayed -------------------------------------------------------------------------------------------
def hours():
    """The three hours of the timetable: the TGVs of model/table_timetable.py and the regional trains of model/ter_timetable.py."""
    ter = json.load(open(os.path.join(HERE, 'inputs', 'ter_timetable.json')))
    return {sc: {'tgv': TT.grid_export(sc)['trains'], 'ter': ter['hours'][sc]['trains']} for sc in TT.GRID}


def events(hour):
    """The trains of one hour on each tunnel track, each way: (tube_use, direction) -> [(seconds in the hour, kind)]."""
    ev = {}
    def put(k, t, kind): ev.setdefault(k, []).append((round(t * 60.0) % 3600, kind))
    for kind, trains in hour.items():
        for t in trains:
            a, b = t['stops']; s1, s2 = a['st'], b['st']
            put((SIDE[t['from']] + '_in', t['from'] + ' ' + s1), a['arr_abs'], kind)
            put((BETWEEN[frozenset((s1, s2))] + '_tun', s1 + ' ' + s2), a['dep_abs'], kind)
            put((SIDE[t['to']] + '_out', s2 + ' ' + t['to']), b['dep_abs'], kind)
    return ev


def replay(hour, table):
    """Each tunnel track of one hour: its trains, the closest pair, the least time that pair needs, the share of the hour taken."""
    rows = []
    for (key, way), lst in sorted(events(hour).items()):
        lst = sorted(lst); n = len(lst); taken = 0.0; worst = None; short = 0; gap_min = 1e9; close = 0; close_short = 0
        for i in range(n):
            (t1, k1), (t2, k2) = lst[i], lst[(i + 1) % n]
            gap = (t2 - t1) % 3600 or 3600.0
            need = table[key][k1 + '_' + k2]['s']; taken += need; gap_min = min(gap_min, gap)
            if gap < need - 1e-6: short += 1
            if gap < N.PATH_MIN * 60 - 1e-6:
                close += 1
                if gap < need - 1e-6: close_short += 1
            if worst is None or gap - need < worst['spare']: worst = {'gap': gap, 'need': need, 'spare': gap - need, 'first': k1, 'second': k2, 'minute': t1 / 60.0, 'place': table[key][k1 + '_' + k2]['place']}
        tube, use = key.rsplit('_', 1)
        rows.append({'tube': tube, 'use': use, 'way': way, 'trains': n, 'tgv': sum(1 for _, k in lst if k == 'tgv'), 'ter': sum(1 for _, k in lst if k == 'ter'),
                     'gap_min': gap_min, 'taken': taken / 3600.0, 'short': short, 'close': close, 'close_short': close_short, 'worst': worst, 'most': 3600.0 * n / taken})
    return rows


def summary(rows):
    w = min(rows, key=lambda r: r['worst']['spare']); f = max(rows, key=lambda r: r['taken'])
    return {'short': sum(r['short'] for r in rows), 'pairs': sum(r['trains'] for r in rows), 'tracks': len(rows),
            'close': sum(r['close'] for r in rows), 'close_short': sum(r['close_short'] for r in rows),
            'tracks_short': sum(1 for r in rows if r['short']), 'tracks_over': sum(1 for r in rows if r['taken'] > UIC_PEAK + 1e-9),
            'spare_min': w['worst']['spare'], 'spare_share': w['worst']['need'] / w['worst']['gap'], 'spare_at': dict(w['worst'], tube=w['tube'], use=w['use'], way=w['way']),
            'taken_max': f['taken'], 'taken_at': {'tube': f['tube'], 'use': f['use'], 'way': f['way'], 'trains': f['trains']}}


def case(H, perf, sig, vt, rows=True):
    """One set of assumptions: the least times, tube by tube, and the three hours replayed on them."""
    table = tube_table(perf, sig, vt); c = {'table': table, 'hours': {}}
    pick = lambda pair, use: max(row[pair]['s'] for k, row in table.items() if k.endswith(use))
    c['need'] = {name: {pair: pick(pair, '_' + use) for pair in ('tgv_tgv', 'tgv_ter', 'ter_tgv', 'ter_ter')} for name, use in (('arrive', 'in'), ('leave', 'out'), ('between', 'tun'))}
    vals = [x['s'] for row in table.values() for x in row.values()]
    c['need']['min'] = min(vals); c['need']['max'] = max(vals)
    c['need']['tgv_second'] = max(row[p]['s'] for row in table.values() for p in ('tgv_tgv', 'ter_tgv'))
    c['need']['ter_second'] = max(row[p]['s'] for row in table.values() for p in ('tgv_ter', 'ter_ter'))
    c['need']['at_peak'] = {k: c['need'][k] / UIC_PEAK for k in ('tgv_second', 'ter_second')}      # spacing that leaves the reserve of UIC code 406 on that pair alone
    c['need']['cycle'] = max(row['tgv_ter']['s'] + row['ter_tgv']['s'] for row in table.values())     # a TGV, a regional train, a TGV: seconds needed of the 240 between two TGVs
    for sc, hour in H.items():
        r = replay(hour, table); c['hours'][sc] = {'sum': summary(r)}
        if rows: c['hours'][sc]['rows'] = r
    return c


def main():
    global V_APPROACH, DEPTH, OVERLAP, T_SYS
    H = hours()
    out = {'params': {'len': LEN, 'perf': {p: {k: {'acc': a, 'brk': b} for k, (a, b) in v.items()} for p, v in PERF.items()}, 'v_line_kmh': V_LINE * 3.6, 'v_approach': V_APPROACH,
                      'depth': DEPTH, 'run_min': RUN / 60, 'margin': MARGIN, 'stop_clear': STOP_CLEAR, 'throat': {'v' + str(k): v for k, v in THROAT.items()}, 'v_throat': V_THROAT,
                      'overlap': OVERLAP, 't_sys': T_SYS, 't_points': T_POINTS, 'signal': SIGNAL, 'uic_peak': UIC_PEAK, 'tubes_km': TUBES,
                      'slope': {k: ramp(TUBES[k], V_THROAT)[1] for k in SIDE.values()},
                      'plan': {'tgv': T.HEADWAY * 60.0, 'path': N.PATH_MIN * 60.0, 'floor': N.SIGNAL_MIN[0] * 60.0, 'step': TT.G_STEP * 60.0}},
           'cases': {}, 'runs': {}, 'steady': {}, 'sens': {}}
    for perf in ('central', 'cautious'):
        out['runs'][perf] = runs(perf, V_THROAT)
        for sig in ('long', 'short', 'auto'):
            out['steady'][f'{perf}_{sig}'] = {'v' + str(v): {a + '_' + b: steady(a, b, perf, sig, v / 3.6) for a in LEN for b in LEN} for v in (60, 80, 100)}
            out['cases'][f'{perf}_{sig}'] = case(H, perf, sig, V_THROAT)
    # what moves the result: one assumption changed at a time, on the central trains, for the plan's signalling and for long blocks
    for sig in ('auto', 'long'):
        S = {}
        for perf in ('central', 'cautious'): S['base_' + perf] = case(H, perf, sig, V_THROAT, rows=False)
        S['points80'] = case(H, 'central', sig, 80, rows=False)
        keep = (V_APPROACH, DEPTH, OVERLAP, T_SYS)
        V_APPROACH = 100; S['approach100'] = case(H, 'central', sig, V_THROAT, rows=False); V_APPROACH = keep[0]
        V_APPROACH = 60; S['approach60'] = case(H, 'central', sig, V_THROAT, rows=False); S['approach60_cautious'] = case(H, 'cautious', sig, V_THROAT, rows=False); V_APPROACH = keep[0]
        DEPTH = 0.0; S['flat'] = case(H, 'central', sig, V_THROAT, rows=False); S['flat_cautious'] = case(H, 'cautious', sig, V_THROAT, rows=False); DEPTH = keep[1]
        OVERLAP = 100.0; S['overlap100'] = case(H, 'central', sig, V_THROAT, rows=False); OVERLAP = keep[2]
        T_SYS = 20.0; S['sys20'] = case(H, 'central', sig, V_THROAT, rows=False); T_SYS = keep[3]
        out['sens'][sig] = {k: {'need': v['need'], 'hours': v['hours']} for k, v in S.items()}
    # the braking the rules ask of a high-speed train, with the times the signalling gives a driver
    steep = max(ramp(TUBES[k], V_THROAT)[1] for k in SIDE.values()); va = V_APPROACH / 3.6
    mine = lambda perf, react: va * react + va * va / (2 * (PERF[perf]['tgv'][1] - G * steep))
    out['rule'] = {'asked': RULE, 'slope': steep, 'drop': G * steep, 'stop': rule_stop(va, steep), 'stop_level': rule_stop(va, 0.0),
                   'model': {'auto': mine('central', SIGNAL['auto']['react']), 'short': mine('central', SIGNAL['short']['react']), 'cautious': mine('cautious', SIGNAL['auto']['react']),
                             'left_central': PERF['central']['tgv'][1] - G * steep, 'left_cautious': PERF['cautious']['tgv'][1] - G * steep},
                   'case': case(H, 'rule', 'rule', V_THROAT, rows=False)}
    out['load'] = {}                                        # the busiest approach track and the busiest track of the triangle, each hour
    for sc in H:
        rows = out['cases']['central_auto']['hours'][sc]['rows']
        top = lambda uses: max((r for r in rows if r['use'] in uses), key=lambda r: r['trains'])
        a, t = top(('in', 'out')), top(('tun',))
        out['load'][sc] = {'approach': dict({k: a[k] for k in ('tube', 'way', 'trains', 'tgv', 'ter')}, flat_share=a['trains'] * N.PATH_MIN / 60.0),   # flat_share: every train counted for 2 minutes
                           'triangle': {k: t[k] for k in ('tube', 'way', 'trains', 'tgv', 'ter')},
                           'trains': sum(len(v) for v in H[sc].values()), 'tgv': len(H[sc]['tgv']), 'ter': len(H[sc]['ter'])}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w'), indent=1)
    line = lambda c: f"need {round(c['need']['min'])} to {round(c['need']['max'])} s, TGV second {round(c['need']['tgv_second'])}, cycle {round(c['need']['cycle'])}; " + ' | '.join(
        f"{sc}: short {c['hours'][sc]['sum']['short']}/{c['hours'][sc]['sum']['pairs']} (close {c['hours'][sc]['sum']['close_short']}/{c['hours'][sc]['sum']['close']}), spare {round(c['hours'][sc]['sum']['spare_min'])} s, taken {round(100 * c['hours'][sc]['sum']['taken_max'])}%" for sc in c['hours'])
    for name, c in out['cases'].items(): print(name.ljust(16), line(c))
    for sig, S in out['sens'].items():
        for name, c in S.items(): print('sens', sig, name.ljust(20), line(c))
    print('rule'.ljust(16), line(out['rule']['case']), {k: round(v, 3) for k, v in out['rule']['stop'].items()}, {k: round(v, 3) for k, v in out['rule']['model'].items()})
    for name, r in out['runs'].items():
        print('run', name, {t: {k: (round(x['fastest']), round(x['with_margin']), round(x['cruise_kmh'])) for k, x in v.items()} for t, v in r.items()})


if __name__ == '__main__':
    main()
