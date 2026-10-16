"""The minutes of the regional express trains (TER) that run in the TGV tunnels, fitted around the TGV hour of the timetable.

    python3 -m pip install ortools        # once: the constraint solver this script needs (not needed to build the site)
    python3 model/ter_timetable.py        # -> model/inputs/ter_timetable.json (about a minute for each of the three hours)

Its result is kept in model/inputs/, so the site builds without ortools; model/table_timetable.py reads it, checks every rule again
and exports it with its measures. Rerun this script only when the TGV hour or the regional trains change.

The TGVs keep their places (model/table_timetable.py: a train every 4 minutes on each side of each station). The TER take the times
between them, in half-minutes, under the rules of the plan (nordest.REG_PLATFORMS, TER_HOUR):
- each line's TER an hour each way: 11 between the north and the Atlantic, through Nord-Est and Montparnasse; 4 between the east and
  the south-east, through Nord-Est and Gare de Lyon (3 today and the new hourly link);
- a TER stops 5 minutes (stop and margin) and its platform track then stays empty 2.5 minutes; it may stand longer, up to 8 minutes,
  to wait for its path; two platform tracks each way at Nord-Est and at Montparnasse, one each way at Gare de Lyon (its fourth track);
- every train takes the same 6 minutes between two stations, so two trains keep their spacing all along a tunnel;
- on every track they share with other trains (the approach tunnels and the tunnels between the stations, each way) a TER keeps
  2 minutes from the train ahead and the train behind, TGV or TER, wherever the hour allows it, and never less than the 1.5 minutes
  the signalling of the plan allows (nordest.SIGNAL_MIN); the solver keeps the closer spacings as few as it can;
- where the tracks of two lines meet at the ends of Nord-Est, trains on them pass at least 1 minute apart wherever the hour allows;
- each line's TER are spread over the hour, within 3 minutes (north and Atlantic) or 7 minutes (east and south-east) of even spacing.
Every figure that is not from the model or a source is marked ASSUMPTION.
"""
import json, os, sys, time
import nordest as N
import table_timetable as TT

HERE = os.path.dirname(os.path.abspath(__file__))
U = 2                                         # the times are counted in half-minutes
P = 60 * U
RUN = TT.G_RUN * U                            # 6 minutes between two stations
STOP = int(N.REG_PLATFORMS['ter']['stop'] * U)
GAP = int(N.REG_PLATFORMS['ter']['gap'] * U)
STOP_MAX = 8 * U                              # longest stop allowed, waiting for a path (ASSUMPTION)
SEP = int(N.PATH_MIN * U)                     # 2 minutes, the paths between the TGV places
FLOOR = int(N.SIGNAL_MIN[0] * U)              # 1.5 minutes, the least the signalling allows
MEET = 1 * U                                  # trains of two lines where their tracks meet (ASSUMPTION)
TOL = {'NA': 3 * U, 'AN': 3 * U, 'ES': 7 * U, 'SE': 7 * U}     # spread over the hour (ASSUMPTION)
TRACKS = {'NE': 2, 'MP': 2, 'LY': 1}         # TER platform tracks each way (nordest: 4 at Nord-Est and Montparnasse; the 4th TGV track each way at Lyon)
NA = N.TER_HOUR['Nord']; ES = N.TER_HOUR['Est'] + N.TER_HOUR['new_east_link']
LINES = {'NA': ('N', 'A', 'NE', 'MP', NA), 'ES': ('E', 'S', 'NE', 'LY', ES), 'AN': ('A', 'N', 'MP', 'NE', NA), 'SE': ('S', 'E', 'LY', 'NE', ES)}
GROUPS = (('south', ('NA', 'ES')), ('north', ('AN', 'SE')))    # trains that share the Nord-Est platforms of one direction
END = {'NE': {'N': 'n', 'E': 'n', 'MP': 's', 'LY': 's'}, 'MP': {'A': 'sw', 'NE': 'ne', 'LY': 'ne'}, 'LY': {'S': 'se', 'NE': 'nw', 'MP': 'nw'}}


def cd(a, b):
    d = (a - b) % P
    return min(d, P - d)


def tgv_events(tt):
    """Times (half-minutes in the hour) at which TGVs use each track: into a station from a line, into a tunnel, out to a line, and
    through each end of each station."""
    ev = {}
    def put(k, t): ev.setdefault(k, []).append(int(round(t * U)) % P)
    for t in tt['trains']:
        a, b = t['stops']; s1, s2 = a['st'], b['st']
        put(('in', s1, t['from']), a['arr_abs']); put(('tun', s1, s2), a['dep_abs']); put(('out', s2, t['to']), b['dep_abs'])
        put(('end', s1, END[s1][t['from']], 'in'), a['arr_abs']); put(('end', s1, END[s1][s2], 'out'), a['dep_abs'])
        put(('end', s2, END[s2][s1], 'in'), b['arr_abs']); put(('end', s2, END[s2][t['to']], 'out'), b['dep_abs'])
    return ev


def events(key, t1, w1, w2):
    """A TER of line `key` arriving at its first station at t1, stopping w1 there and w2 at the second: the tracks it uses, and when."""
    fr, to, a, b, _ = LINES[key]; d1 = t1 + w1; t2 = d1 + RUN; d2 = t2 + w2
    track = [(('in', a, fr), t1), (('tun', a, b), d1), (('out', b, to), d2)]
    ends = [(('end', a, END[a][fr], 'in'), t1), (('end', a, END[a][b], 'out'), d1), (('end', b, END[b][a], 'in'), t2), (('end', b, END[b][to], 'out'), d2)]
    return track, [e for e in ends if e[0][1] == 'NE']


def solve(ev, keys, seconds=60):
    from ortools.sat.python import cp_model
    m = cp_model.CpModel(); trains = []; cost = []
    def modv(expr):
        x = m.NewIntVar(-4 * P, 4 * P, ''); m.Add(x == expr)
        r = m.NewIntVar(0, P - 1, ''); m.AddModuloEquality(r, x + 4 * P, P); return r
    for key in keys:
        n = LINES[key][4]; ideal = P / n; lo, hi = int(ideal - TOL[key]), int(ideal + TOL[key] + 0.999)
        us = [m.NewIntVar(0, 2 * P, '') for _ in range(n)]
        m.Add(us[0] <= P - 1)
        for a, b in zip(us, us[1:]): m.Add(b - a >= lo); m.Add(b - a <= hi)
        m.Add(us[0] + P - us[-1] >= lo); m.Add(us[0] + P - us[-1] <= hi)
        for u in us: trains.append({'key': key, 'u': u, 'w1': m.NewIntVar(STOP, STOP_MAX, ''), 'w2': m.NewIntVar(STOP, STOP_MAX, '')})
    for t in trains:                         # u: arrival at Nord-Est, the station both lines of a group share
        fr, to, a, b, _ = LINES[t['key']]
        if a == 'NE': t1 = t['u']; d1 = t1 + t['w1']; t2 = d1 + RUN; d2 = t2 + t['w2']
        else: t2 = t['u']; d1 = t2 - RUN; t1 = d1 - t['w1']; d2 = t2 + t['w2']
        T1, D1, T2, D2 = modv(t1), modv(d1), modv(t2), modv(d2)
        t['track'] = [(('in', a, fr), T1), (('tun', a, b), D1), (('out', b, to), D2)]
        t['ends'] = [e for e in [(('end', a, END[a][fr], 'in'), T1), (('end', a, END[a][b], 'out'), D1), (('end', b, END[b][a], 'in'), T2),
                                 (('end', b, END[b][to], 'out'), D2)] if e[0][1] == 'NE']
        for k, x in t['track']:                                    # against the TGVs on the same track
            dist = [min([cd(v, y) for y in ev.get(k, [])] or [P]) for v in range(P)]
            close = m.NewBoolVar('')
            m.AddAllowedAssignments([x, close], [(v, int(dist[v] < SEP)) for v in range(P) if dist[v] >= FLOOR])
            cost.append(1000 * close)
        for k, x in t['ends']:                                     # against the TGVs of the other lines where the tracks meet
            dist = [min([cd(v, y) for y in ev.get(k, [])] or [P]) for v in range(P)]
            close = m.NewBoolVar('')
            m.AddAllowedAssignments([x, close], [(v, int(dist[v] < MEET)) for v in range(P)])
            cost.append(30 * close)
        d = 'S' if fr in 'NE' else 'N'
        t['plat'] = [((a, d), T1, t['w1']), ((b, d), T2, t['w2'])]
        t['k'] = {}
        for g, s, w in t['plat']:
            bs = [m.NewBoolVar('') for _ in range(TRACKS[g[0]])]; m.AddExactlyOne(bs); t['k'][g] = bs
        cost.append(t['w1'] + t['w2'] - 2 * STOP)
    for i, a in enumerate(trains):
        for b in trains[i + 1:]:
            if a['key'] == b['key']:                                 # two TER of one line share all their tracks
                for (k, x), (_, y) in zip(a['track'], b['track']):
                    r = modv(x - y); m.Add(r >= FLOOR); m.Add(r <= P - FLOOR)
                    close = m.NewBoolVar(''); m.Add(r >= SEP).OnlyEnforceIf(close.Not()); m.Add(r <= P - SEP).OnlyEnforceIf(close.Not())
                    cost.append(1000 * close)
            else:
                be = dict(b['ends'])
                for k, x in a['ends']:
                    if k in be:
                        r = modv(x - be[k]); close = m.NewBoolVar('')
                        m.Add(r >= MEET).OnlyEnforceIf(close.Not()); m.Add(r <= P - MEET).OnlyEnforceIf(close.Not()); cost.append(30 * close)
            for g, s1, w1 in a['plat']:
                for g2, s2, w2 in b['plat']:
                    if g != g2: continue
                    r = modv(s2 - s1)
                    for ka, kb in zip(a['k'][g], b['k'][g]):
                        same = m.NewBoolVar(''); m.AddBoolAnd([ka, kb]).OnlyEnforceIf(same); m.AddBoolOr([ka.Not(), kb.Not()]).OnlyEnforceIf(same.Not())
                        m.Add(r >= w1 + GAP).OnlyEnforceIf(same); m.Add(r <= P - w2 - GAP).OnlyEnforceIf(same)
    m.Minimize(sum(cost))
    sv = cp_model.CpSolver(); sv.parameters.max_time_in_seconds = seconds; sv.parameters.num_workers = 8; sv.parameters.random_seed = 1
    st = sv.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): return sv.StatusName(st), None
    out = []
    for t in trains:
        fr, to, a, b, _ = LINES[t['key']]; u, w1, w2 = sv.Value(t['u']), sv.Value(t['w1']), sv.Value(t['w2'])
        t1 = u if a == 'NE' else u - RUN - w1
        t1 %= P; d1 = t1 + w1; t2 = d1 + RUN; d2 = t2 + w2
        k = {g[0]: [sv.Value(x) for x in bs].index(1) for g, bs in t['k'].items()}
        out.append({'line': t['key'], 'from': fr, 'to': to,
                    'stops': [{'st': a, 'arr_abs': t1 / U, 'dep_abs': d1 / U, 'track': k[a]}, {'st': b, 'arr_abs': t2 / U, 'dep_abs': d2 / U, 'track': k[b]}]})
    out.sort(key=lambda r: (r['stops'][0]['arr_abs'], r['line']))
    return sv.StatusName(st), out


def main():
    res = {'_note': 'Written by model/ter_timetable.py (needs ortools); read and checked by model/table_timetable.py. Minutes in the hour; '
                    'tracks counted from 0 among the TER platform tracks of one direction.',
           'params': {'stop': STOP / U, 'gap': GAP / U, 'stop_max': STOP_MAX / U, 'sep': SEP / U, 'floor': FLOOR / U, 'meet': MEET / U,
                      'tol': {k: v / U for k, v in TOL.items()}, 'tracks': TRACKS, 'trains': {k: v[4] for k, v in LINES.items()}},
           'hours': {}}
    for sc in TT.GRID:
        ev = tgv_events(TT.grid_export(sc)); trains = []; status = []
        for name, keys in GROUPS:
            t0 = time.time(); st, tr = solve(ev, keys, float(sys.argv[1]) if len(sys.argv) > 1 else 60)
            print(sc, name, st, round(time.time() - t0, 1), 's', flush=True)
            if tr is None: raise SystemExit(f'{sc} {name}: no hour fits the rules ({st})')
            trains += tr; status.append(st)
        res['hours'][sc] = {'status': status, 'trains': trains}
    json.dump(res, open(os.path.join(HERE, 'inputs', 'ter_timetable.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
