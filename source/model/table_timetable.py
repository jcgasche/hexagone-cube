"""The hour of high-speed trains built by hand, track by track, as one would with a table (no search algorithm).

    python3 model/table_timetable.py      # -> adds 'table' to model/outputs/timetable.json and src/sections/timetable/data.json (seconds)

Run after timetable.py. The method:
1. A train holds its platform track A = A_STOP + A_RESERVE minutes (the stop, and a reserve for a late train), then the track stays
   empty B minutes before the next train can arrive. So one track takes floor(60 / (A + B)) trains in an hour that repeats.
2. Montparnasse: trains from the Atlantic line arrive on track 1 at minute 0, A + B, 2 (A + B)... until the hour is full, then on
   track 2 starting HEADWAY minutes later (two trains cannot come out of the same tunnel closer than that), and so on, until all the
   trains of the line are placed. The number of tracks used is what that side of the station needs. The same at Gare de Lyon for
   the south-east line and at Paris Nord-Est for the north and east lines, each with its own offset from the hour.
3. Each train leaves A_STOP minutes after it arrives and is sent on, in turn, to one of the two other stations, in proportion to
   the service plan (nordest.service). It arrives there after the run time and takes the first free track on that side.
4. The offsets of Gare de Lyon and Nord-Est are the ones whose trains fall into the free places left by the others: every
   combination of minutes is tried in a table, and the one that needs the fewest tracks and keeps trains furthest apart is kept.
Every figure that is not from the model or a source is marked ASSUMPTION.
"""
import json, math, os
import nordest as N
import timetable as T

HERE = os.path.dirname(os.path.abspath(__file__))
A_STOP = 7          # minutes a train stops (ASSUMPTION; Lyon Part-Dieu plans 6 for most TGVs, 10 when trains are coupled; see the annex)
A_RESERVE = 3       # minutes the track stays reserved after the planned departure, for a late train (ASSUMPTION)
B = int(T.CLEAR)         # minutes the track stays empty between a departure and the next arrival (the report's value, 3; ASSUMPTION)
H = int(T.HEADWAY)       # minutes between two trains coming out of, or going into, the same tunnel track (3; ASSUMPTION)
A = A_STOP + A_RESERVE
PER_TRACK = 60 // (A + B)                     # trains one track takes in an hour that repeats
RUN = {('MP', 'NE'): int(T.RUN['M']), ('LY', 'NE'): int(T.RUN['L']), ('MP', 'LY'): int(T.RUN['LM'])}
def run(a, b): return RUN.get((a, b)) or RUN[(b, a)]
LINE_IN = {'MP': 'A', 'LY': 'S', 'NE': 'NE*'}    # the line whose trains arrive on the 'in' side of each station

SCENARIOS = {        # trains an hour each way: from each station's own line, and where they go on (nordest.service)
    'today': {'MP': {'NE': 6, 'LY': 6}, 'LY': {'NE': 6, 'MP': 6}, 'NE': {'MP': 6, 'LY': 6}, 'east': 4},
    'full': {'MP': {'NE': 6, 'LY': 9}, 'LY': {'NE': 6, 'MP': 9}, 'NE': {'MP': 6, 'LY': 6}, 'east': 4},
    # the most a side takes with A + B = 13 minutes and trains 3 minutes apart: 4 tracks of 4 trains, 16 an hour. The southern lines
    # stay at their limits (15); Nord-Est is filled to 16 from the north and east (11 north, 5 east: ASSUMPTION)
    'max': {'MP': {'NE': 8, 'LY': 7}, 'LY': {'NE': 8, 'MP': 7}, 'NE': {'MP': 8, 'LY': 8}, 'east': 5},
}


def fill(n, offset):
    """Arrivals of n trains on one side, filling track 1, then track 2... Returns [(minute, track)], tracks used, free places."""
    out, t = [], 0
    while len(out) < n:
        for j in range(PER_TRACK):
            if len(out) == n: break
            out.append(((offset + t * H + j * (A + B)) % 60, t + 1))
        t += 1
    return out, t, t * PER_TRACK - n


def even(n, offset):
    """Arrivals of n trains spread as evenly as the whole minutes allow over the hour, from the offset."""
    return [offset + (i * 60) // n for i in range(n)]


def spread(n, k, rot=0):
    """Which of n trains in time order go to the second destination: k of them, as evenly spaced as possible (Bresenham)."""
    return [((i + rot) * k) // n != ((i + rot + 1) * k) // n for i in range(n)]


def gaps(times):
    ts = sorted(x % 60 for x in times)
    if len(ts) < 2: return [60]
    return [ts[i + 1] - ts[i] for i in range(len(ts) - 1)] + [ts[0] + 60 - ts[-1]]


def tracks_for(arrs):
    """Fewest tracks for trains each holding a track from arrival to arrival + A + B, in an hour that repeats: trains take the
    lowest-numbered free track in order of arrival, starting the hour at each train in turn, until the end of the hour meets its
    start on every track. Returns (tracks, track of each train), or (None, None) above 8 tracks."""
    n = len(arrs); m = [x % 60 for x in arrs]
    order = sorted(range(n), key=lambda i: m[i])
    for nt in range(1, 9):
        for s0 in range(n):
            seq = order[s0:] + order[:s0]; base = m[seq[0]]
            first = [None] * nt; free = [-10 ** 9] * nt; asg = {}; ok = True
            for i in seq:
                a = base + (m[i] - base) % 60
                cand = [k for k in range(nt) if free[k] <= a]
                if not cand: ok = False; break
                k = cand[0]; asg[i] = k + 1; free[k] = a + A + B
                if first[k] is None: first[k] = a
            if ok and all(first[k] is None or free[k] <= first[k] + 60 for k in range(nt)):
                return nt, asg
    return None, None


def cdist(x, y):
    d = abs(x - y) % 60
    return min(d, 60 - d)


def build(sc, off, rot):
    """All trains of the hour for one scenario, given the offsets of the three stations and the rotation of each routing.
    Arrivals from each station's own line fill its tracks as in fill(). Each train then leaves A_STOP minutes later, or up to
    A_RESERVE minutes later if that is what it takes to reach a free place at the next station (its track is held A minutes in
    any case): trains are placed one after the other in order of arrival, each taking the first departure that keeps HEADWAY
    minutes from the trains already placed, on both sides of the tunnel."""
    S = SCENARIOS[sc]; trains = []
    for st in ('MP', 'LY', 'NE'):
        dests = list(S[st].items()); n = sum(v for _, v in dests)
        arr = sorted(fill(n, off[st])[0])
        second = spread(n, dests[1][1], rot[st])
        east = spread(n, S['east'], rot[st]) if st == 'NE' else [False] * n
        for i, (a, trk) in enumerate(arr):
            trains.append({'st1': st, 'st2': dests[1][0] if second[i] else dests[0][0], 'a1': a, 'trk1': trk, 'east_in': east[i]})
    placed = {('dep', st): [] for st in ('MP', 'LY', 'NE')}
    placed.update({('arr2', st): [] for st in ('MP', 'LY', 'NE')}); placed.update({('dep2', st): [] for st in ('MP', 'LY', 'NE')})
    ok = lambda key, x: all(cdist(x, y) >= H for y in placed[key])
    for t in sorted(trains, key=lambda t: t['a1'] % 60):
        for w in range(A_RESERVE + 1):
            d = t['a1'] + A_STOP + w; a2 = d + run(t['st1'], t['st2'])
            if ok(('dep', t['st1']), d) and ok(('arr2', t['st2']), a2):
                for w2 in range(A_RESERVE + 1):
                    if ok(('dep2', t['st2']), a2 + A_STOP + w2): break
                else: continue
                t.update({'d1': d, 'a2': a2, 'd2': a2 + A_STOP + w2})
                placed[('dep', t['st1'])].append(d); placed[('arr2', t['st2'])].append(a2); placed[('dep2', t['st2'])].append(a2 + A_STOP + w2)
                break
        else:
            return None
    to_ne = sorted([t for t in trains if t['st2'] == 'NE'], key=lambda t: t['a2'] % 60)
    e_out = spread(len(to_ne), S['east'], 0)
    for t, e in zip(to_ne, e_out): t['east_out'] = e
    return trains


def check(trains):
    """Tunnel spacing and tracks on the 'out' side of each station (the 'in' sides are built to be right). Returns
    (feasible, tracks a side, smallest gap)."""
    if trains is None: return False, None, 0
    res, small = {}, 60
    for st in ('MP', 'LY', 'NE'):
        arr = [t['a2'] for t in trains if t['st2'] == st]
        dep = [t['d2'] for t in trains if t['st2'] == st]
        dep_in = [t['d1'] for t in trains if t['st1'] == st]
        g = min(gaps(arr) + gaps(dep) + gaps(dep_in))
        small = min(small, g)
        if g < H: return False, None, g
        nt, _ = tracks_for(arr)
        nt_in, _ = tracks_for([t['a1'] for t in trains if t['st1'] == st])
        if nt is None or nt_in is None: return False, None, g
        res[st] = nt; res[st + ' in'] = nt_in
    return True, res, small


def solve(sc):
    """Montparnasse at minute 0; every offset of Gare de Lyon and Nord-Est and every turn of the routings is tried."""
    best = None
    S = SCENARIOS[sc]
    n = {st: sum(S[st].values()) for st in ('MP', 'LY', 'NE')}
    for o_ly in range(60):
        for o_ne in range(60):
            for r in range(max(n.values())):
                off = {'MP': 0, 'LY': o_ly, 'NE': o_ne}; rot = {'MP': 0, 'LY': r % n['LY'], 'NE': r % n['NE']}
                ok, trk, small = check(build(sc, off, rot))
                if not ok: continue
                key = (sum(trk.values()), -small, o_ly, o_ne, r)                 # fewest tracks, then trains furthest apart
                if best is None or key < best[0]: best = (key, off, rot, trk, small)
    return best


def export(sc, best):
    """The timetable in the format of timetable.py, so that the clocks, the map and the measures read it as they read the others."""
    _, off, rot, trk_out, small = best
    trains = build(sc, off, rot)
    out_asg = {}
    for st in ('MP', 'LY', 'NE'):
        idx = [i for i, t in enumerate(trains) if t['st2'] == st]
        _, asg = tracks_for([trains[i]['a2'] for i in idx])
        for j, i in enumerate(idx): out_asg[i] = asg[j]
    route = {('MP', 'NE'): 'AN', ('NE', 'MP'): 'NA', ('LY', 'NE'): 'SN', ('NE', 'LY'): 'NS', ('MP', 'LY'): 'AS', ('LY', 'MP'): 'SA'}
    rows = []
    for i, t in enumerate(trains):
        r = route[(t['st1'], t['st2'])]
        frm = {'MP': 'A', 'LY': 'S'}.get(t['st1']) or ('E' if t['east_in'] else 'N')
        to = {'MP': 'A', 'LY': 'S'}.get(t['st2']) or ('E' if t.get('east_out') else 'N')
        rows.append({'route': r, 'from': frm, 'to': to, 'slot': i, 'rep': 0, 'london': False,
                     'stops': [{'st': t['st1'], 'side': 'in', 'arr': t['a1'] % 60, 'dep': t['d1'] % 60, 'arr_abs': t['a1'], 'dep_abs': t['d1'], 'track': t['trk1'], 'held': 0},
                               {'st': t['st2'], 'side': 'out', 'arr': t['a2'] % 60, 'dep': t['d2'] % 60, 'arr_abs': t['a2'], 'dep_abs': t['d2'], 'track': out_asg[i], 'held': 0}]})
    # London: the first train of the hour from Gare de Lyon to the north, and the first from the north to Gare de Lyon
    for r_, cond in (('SN', lambda x: x['to'] == 'N'), ('NS', lambda x: x['from'] == 'N')):
        c = sorted([x for x in rows if x['route'] == r_ and cond(x)], key=lambda x: x['stops'][0]['arr'])
        if c: c[0]['london'] = True
    rows.sort(key=lambda r: (r['stops'][0]['arr_abs'] % 60, r['route']))
    return {'name': 'table ' + sc, 'period': 60, 'trains': rows, 'offsets': off, 'smallest_gap': small}


def sides(sc, best):
    """For each side of each station: trains an hour, tracks used, places on those tracks and how many are left free."""
    S = SCENARIOS[sc]; _, off, rot, trk_out, _ = best
    out = {}
    for st in ('MP', 'LY', 'NE'):
        n = sum(S[st].values()); t_in = trk_out[st + ' in']; spare = t_in * PER_TRACK - n
        n_out = sum(S[o][st] for o in ('MP', 'LY', 'NE') if o != st and st in S[o])
        out[st] = {'in': {'trains': n, 'tracks': t_in, 'places': t_in * PER_TRACK, 'free': spare},
                   'out': {'trains': n_out, 'tracks': trk_out[st], 'places': trk_out[st] * PER_TRACK, 'free': trk_out[st] * PER_TRACK - n_out}}
    return out


class Fixed:
    """Lets the measures of timetable.py read a fixed list of trains."""
    def __init__(self, rows): self.rows = rows
    def trains(self):
        out = []
        for r in self.rows:
            s = [(x['st'], x['side'], x['arr_abs'], x['dep_abs']) for x in r['stops']]
            out.append({'r': r['route'], 'slot': r['slot'], 'rep': 0, 'from': r['from'], 'to': r['to'], 'svc': (r['slot'], r['to']),
                        'london': r['london'], 'stops': s, 'e': [0, 0]})
        return out


def main():
    path = os.path.join(HERE, 'outputs', 'timetable.json')
    data = json.load(open(path))
    table = {'params': {'a_stop': A_STOP, 'a_reserve': A_RESERVE, 'a': A, 'b': B, 'headway': H, 'per_track': PER_TRACK, 'run': {f'{a}-{b}': v for (a, b), v in RUN.items()}},
             'scenarios': SCENARIOS, 'timetables': {}, 'sides': {}, 'measures': {}}
    for sc in SCENARIOS:
        best = solve(sc)
        if best is None: table['timetables'][sc] = None; print(sc, 'no timetable'); continue
        tt = export(sc, best); table['timetables'][sc] = tt; table['sides'][sc] = sides(sc, best)
        ev = T.evenness(Fixed(tt['trains']).trains(), cs=T.CHANGE_SAME, co=T.CHANGE_OTHER)
        fx = Fixed(tt['trains']).trains()
        spare = {}
        for st in ('MP', 'LY', 'NE'):
            for side in ('in', 'out'):
                g = gaps([s_[2] for t in fx for s_ in t['stops'] if s_[0] == st and s_[1] == side])
                spare[st + ' ' + side] = sum(max(0, int(x // H) - 1) for x in g)       # more trains that fit in the gaps, HEADWAY apart
        direct = {}
        for t in tt['trains']:
            k = t['from'] + t['to']; direct.setdefault(k, t['stops'][1]['dep_abs'] - t['stops'][0]['arr_abs'])
        table['measures'][sc] = {'paris_wait': ev['paris_wait'], 'direct_wait': ev['direct_wait'], 'ne_change': ev['ne_change'], 'line': ev['line'], 'pair': ev['pair'],
                                 'spare_paths': spare, 'direct_min': min(direct.values()), 'direct_max': max(direct.values())}
        print(sc, 'offsets', tt['offsets'], 'smallest gap', tt['smallest_gap'], 'tracks', {k: (v['in']['tracks'], v['out']['tracks']) for k, v in table['sides'][sc].items()})
        print('   spare paths', table['measures'][sc]['spare_paths'], 'direct', table['measures'][sc]['direct_min'], table['measures'][sc]['direct_max'])
        print('   free places', {k: (v['in']['free'], v['out']['free']) for k, v in table['sides'][sc].items()}, 'waits', round(ev['paris_wait'], 1), round(ev['direct_wait'], 1), round(ev['ne_change'], 1))
    data['table'] = table
    json.dump(data, open(path, 'w'), indent=1)
    json.dump(data, open(os.path.join(HERE, '..', 'src', 'sections', 'timetable', 'data.json'), 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
