"""The junctions of the three TGV stations: do the trains of the timetable get in each other's way between the tunnels and the platform tracks?

    python3 model/throat.py        # -> src/data/throat.json (about two minutes)

model/headway.py checks two trains that follow each other on one tunnel track. This script looks at what that leaves out: at each end
of a station the tunnel tracks fan out to the platform tracks, and where two tunnels arrive at the same end (the two other stations of the
triangle; the north and east approaches at Nord-Est) the paths of some trains cross the paths of others.

Each station is run in two halves, one for each direction, as the timetable does (model/table_timetable.py: the 'in' side takes the trains
that come from outside Paris, the 'out' side those that come from the triangle). Each half has its own platform tracks: three for TGVs,
and those of the regional express trains (TER) of that direction. So at one end of a station there are:
- the arrivals, which come from one or two tunnel tracks and spread over the platform tracks of one half;
- the departures, which leave the platform tracks of the other half and join one or two tunnel tracks.

Three kinds of crossing can exist at an end where two tunnels meet, if everything is on one level:
1. 'across': an arrival from one tunnel cuts the path of a departure to the other tunnel (the two tracks of a tunnel lie side by side,
   so one arriving track is always on the wrong side of one departing track);
2. 'arrivals': two arrivals from the two tunnels, bound for platform tracks whose order is the reverse of the order of the tunnels;
3. 'departures': the same for two departures.
A crossing is a short piece of track that only one train may hold at a time. Each train holds it from the moment it must know it free
(its braking point less the time to react; for a departure, the time to set the route) to the moment the signalling gives it back behind
its tail: the blocking time of model/headway.py. Two trains whose times overlap are in conflict: one of them is held.

The script replays the three hours of the timetable, every TGV and every TER on its platform track, and counts the conflicts and the
least time in hand, for each kind of crossing. It tries every order of the platform tracks and keeps the best. Nothing here is a track
layout: it says which crossings can stay on one level and which need one track to pass under another.
"""
import contextlib, io, itertools, json, os
with contextlib.redirect_stdout(io.StringIO()):
    import headway as H

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'src', 'data', 'throat.json')

ZONE = 100.0                    # m of track a crossing takes (ASSUMPTION: the length of a block in the fan of points)
ROUTE = H.T_SYS + H.T_POINTS    # s to set and lock a route before a train may leave
OTHER = {'NE': ('MP', 'LY'), 'MP': ('NE', 'LY'), 'LY': ('NE', 'MP')}
OUTER = {'NE': ('N', 'E'), 'MP': ('A',), 'LY': ('S',)}
NAME = {'N': 'north', 'E': 'east', 'S': 'southeast', 'A': 'atlantic'}


# What the track owner's own timetable rules ask today, with today's signalling (SNCF Reseau, 'Norme de trace horaire sur les lignes
# nationales', service 2019, document AR30136, line from Paris-Est): minutes.
NORMS = {'line': 3.0,                 # two trains one behind the other at 120 km/h or more, automatic block signals
         'hsl_platform': 3.5,         # Haussmann-Saint-Lazare (underground through station of RER E): between two trains on one platform track
         'hsl_diverge': 2.5, 'hsl_converge': 2.0, 'hsl_cross': 3.5,       # the same station: routes that part, that join, that cross
         'magenta': 3.5,              # Magenta: a departure and the next arrival on the same track
         'est_dep': 3.0, 'est_arr': 4.0}                                    # Paris-Est: departures in a row, arrivals in a row
# Points (turnouts) of the French network, by the tangent of their angle: speed on the turning track (km/h) and length (m). From a
# railwayman's published course, not from the track owner: unverified. A forum of railway staff gives 60 km/h for 0.085 and 90 for 0.05.
POINTS = {'0.085': {'tan': 0.085, 'kmh': 70, 'kmh_low': 60, 'm': 40.0}, '0.05': {'tan': 0.05, 'kmh': 100, 'kmh_low': 90, 'm': 63.0}}
TRACK_GAP = 9.0                 # m between two platform tracks on average: a platform every other gap (ASSUMPTION)
TUNNEL_GAP = 4.0                # m between the two tracks to be linked where two tunnels meet (ASSUMPTION)


def fan(tracks, tan, length):
    """Metres of points needed to spread one tunnel track over the platform tracks of one half of a station (the outer track is half
    the width of the half away from the middle), and the same with a link between the tracks of two tunnels ahead of it."""
    one = (tracks - 1) / 2.0 * TRACK_GAP / tan + length
    return {'one': one, 'two': one + TUNNEL_GAP / tan + length}


def km_of(st, stem):
    return H.TUBES[H.SIDE[stem]] if stem in H.SIDE else H.TUBES[H.BETWEEN[frozenset((st, stem))]]


_cache = {}
def hold(move, st, stem, kind, perf, sig, vt, u0, u1):
    """Seconds, counted from the stop (arrival) or from the start (departure), during which a train holds the piece of track from u0 to
    u1 metres beyond the end of the platforms."""
    key = (move, st, stem, kind, perf, sig, vt, u0, u1)
    if key in _cache: return _cache[key]
    km = km_of(st, stem); L = H.LEN[kind]; react = H.SIGNAL[sig]['react']
    if move == 'arr':
        p = H.arriving(kind, km, perf, vt) if stem in H.SIDE else H.between(kind, km, perf, vt)[0]
        xd = km * 1000.0 - H.LEN['tgv'] - H.STOP_CLEAR; end = p['t'][-1]
        out = (H.needs(p, xd - u1) - react - end, H.at(p, xd - u0 + L) - end + H.T_SYS)
    else:
        p = H.leaving(kind, km, perf, vt) if stem in H.SIDE else H.between(kind, km, perf, vt)[0]
        out = (-ROUTE, H.at(p, u1 + L) + H.T_SYS)
    _cache[key] = out
    return out


def movements(hour):
    """Every arrival and departure of one hour: (station, end) -> {'arr': [...], 'dep': [...]}, each (seconds, kind, tunnel, platform track).
    Platform tracks are named by half of the station ('in' or 'out'), kind and number."""
    ev = {}
    def put(st, end, move, t, kind, stem, plat): ev.setdefault((st, end), {'arr': [], 'dep': []})[move].append((round(t * 60.0) % 3600, kind, stem, plat))
    for kind, trains in hour.items():
        for t in trains:
            a, b = t['stops']; s1, s2 = a['st'], b['st']
            put(s1, 'outer', 'arr', a['arr_abs'], kind, t['from'], ('in', kind, a['track']))
            put(s1, 'tri', 'dep', a['dep_abs'], kind, s2, ('in', kind, a['track']))
            put(s2, 'tri', 'arr', b['arr_abs'], kind, s1, ('out', kind, b['track']))
            put(s2, 'outer', 'dep', b['dep_abs'], kind, t['to'], ('out', kind, b['track']))
    return ev


def clash(a, b):
    """Seconds in hand between two blocking times in an hour that repeats (negative: they overlap)."""
    best = 1e9
    for k in (-3600, 0, 3600):
        lo1, hi1 = a; lo2, hi2 = b[0] + k, b[1] + k
        best = min(best, max(lo2 - hi1, lo1 - hi2))
    return best


def tally(pairs):
    """pairs: [(seconds in hand, what)] -> count, conflicts, least in hand."""
    if not pairs: return {'pairs': 0, 'conflicts': 0, 'least': None, 'worst': None}
    w = min(pairs, key=lambda x: x[0])
    return {'pairs': len(pairs), 'conflicts': sum(1 for x in pairs if x[0] < -1e-6), 'least': w[0], 'worst': w[1]}


def end_study(st, end, mv, perf, sig, vt):
    """One end of one station in one hour: the three kinds of crossing, on one level."""
    th = H.THROAT[vt]; stems = OTHER[st] if end == 'tri' else OUTER[st]
    span = lambda move, m, u0, u1: tuple(m[0] + x for x in hold(move, st, m[2], m[1], perf, sig, vt, u0, u1))
    out = {'station': st, 'end': end, 'tunnels': list(stems), 'n_arr': len(mv['arr']), 'n_dep': len(mv['dep']),
           'by_tunnel': {s: {'arr': sum(1 for m in mv['arr'] if m[2] == s), 'dep': sum(1 for m in mv['dep'] if m[2] == s)} for s in stems}}
    if len(stems) < 2: return out
    X, Y = stems
    # 1. across: arrivals from one tunnel against departures to the other, at the tunnel end of the fan of points. Which of the two
    # pairs crosses depends on which side the arrivals' half of the station lies: both are tried.
    across = {}
    for a, d in ((X, Y), (Y, X)):
        pairs = [(clash(span('arr', m, th - ZONE, th), span('dep', n, th - ZONE, th)), {'arr': m[0] / 60.0, 'dep': n[0] / 60.0, 'kinds': m[1] + '_' + n[1]})
                 for m in mv['arr'] if m[2] == a for n in mv['dep'] if n[2] == d]
        # share of the hour the crossing is held, if nothing overlapped: what a timetable built around it would have to fit
        load = (sum(hold('arr', st, m[2], m[1], perf, sig, vt, th - ZONE, th)[1] - hold('arr', st, m[2], m[1], perf, sig, vt, th - ZONE, th)[0] for m in mv['arr'] if m[2] == a)
                + sum(hold('dep', st, n[2], n[1], perf, sig, vt, th - ZONE, th)[1] - hold('dep', st, n[2], n[1], perf, sig, vt, th - ZONE, th)[0] for n in mv['dep'] if n[2] == d)) / 3600.0
        across[a + '_' + d] = dict(tally(pairs), arr_from=a, dep_to=d, load=load, arr=sum(1 for m in mv['arr'] if m[2] == a), dep=sum(1 for n in mv['dep'] if n[2] == d))
    out['across'] = min(across.values(), key=lambda r: (r['conflicts'], -(r['least'] or 0))); out['across_other'] = max(across.values(), key=lambda r: (r['conflicts'], -(r['least'] or 0)))
    # 2 and 3. within one half: two trains of the two tunnels cross when the order of their platform tracks is the reverse of the order
    # of the tunnels. Every order of the platform tracks is tried; the crossing is in the middle of the fan of points.
    for move, name in (('arr', 'arrivals'), ('dep', 'departures')):
        plats = sorted({m[3] for m in mv[move]}); best = None
        if not any(m[2] == X for m in mv[move]) or not any(m[2] == Y for m in mv[move]): out[name] = dict(tally([]), order=[list(p) for p in plats]); continue
        gaps = {}
        for m in mv[move]:
            for n in mv[move]:
                if m[2] == X and n[2] == Y and m[3] != n[3]:
                    gaps.setdefault((m[3], n[3]), []).append((clash(span(move, m, th / 2 - ZONE / 2, th / 2 + ZONE / 2), span(move, n, th / 2 - ZONE / 2, th / 2 + ZONE / 2)), {'x': m[0] / 60.0, 'y': n[0] / 60.0, 'kinds': m[1] + '_' + n[1]}))
        for order in itertools.permutations(plats):
            pos = {p: i for i, p in enumerate(order)}
            pairs = [g for (px, py), lst in gaps.items() if pos[px] > pos[py] for g in lst]      # X is on the left: X to a track right of Y's track crosses
            r = tally(pairs); key = (r['conflicts'], -(r['least'] if r['least'] is not None else 1e9), r['pairs'])
            if best is None or key < best[0]: best = (key, r, order)
        out[name] = dict(best[1], order=[list(p) for p in best[2]])
        # the tracks each tunnel uses: can the platform tracks be split between the two tunnels?
        out[name]['tracks_by_tunnel'] = {s: sorted({list(m[3])[2] if False else '%s %s' % (m[3][1], m[3][2]) for m in mv[move] if m[2] == s}) for s in stems}
    return out


def study(H_, perf, sig, vt):
    res = {}
    for sc, hour in H_.items():
        ev = movements(hour); rows = [end_study(st, end, ev[(st, end)], perf, sig, vt) for st in ('NE', 'MP', 'LY') for end in ('outer', 'tri')]
        two = [r for r in rows if len(r['tunnels']) == 2]
        res[sc] = {'ends': rows, 'by_end': {r['station'] + '_' + r['end']: r for r in rows}, 'sum': {k: {'pairs': sum(r[k]['pairs'] for r in two), 'conflicts': sum(r[k]['conflicts'] for r in two),
                                           'least': min((r[k]['least'] for r in two if r[k]['least'] is not None), default=None)} for k in ('across', 'arrivals', 'departures')}}
    return res


def main():
    Hh = H.hours()
    out = {'params': {'zone': ZONE, 'route_s': ROUTE, 'throat': H.THROAT[H.V_THROAT], 'v_throat': H.V_THROAT},
           'holds': {}, 'cases': {}, 'norms': NORMS, 'points': POINTS, 'track_gap': TRACK_GAP, 'tunnel_gap': TUNNEL_GAP,
           'fan': {k: {'t4': fan(4, v['tan'], v['m']), 't5': fan(5, v['tan'], v['m'])} for k, v in (('p085', POINTS['0.085']), ('p05', POINTS['0.05']))}}
    # the plan against those rules: minutes
    import table_timetable as TT
    ter = json.load(open(os.path.join(HERE, 'inputs', 'ter_timetable.json')))['params']
    out['plan'] = {'line': H.N.PATH_MIN, 'tgv_platform': TT.G_RESERVE + TT.G_B if hasattr(TT, 'G_B') else None, 'ter_platform': ter['gap'], 'tgv_line': H.T.HEADWAY}
    for perf, sig in (('central', 'auto'), ('central', 'long'), ('rule', 'rule')):
        out['cases'][perf + '_' + sig] = study(Hh, perf, sig, H.V_THROAT)
    # how long one train holds a crossing, for the page
    th = H.THROAT[H.V_THROAT]
    for kind in ('tgv', 'ter'):
        a = hold('arr', 'MP', 'NE', kind, 'central', 'auto', H.V_THROAT, th - ZONE, th); d = hold('dep', 'MP', 'NE', kind, 'central', 'auto', H.V_THROAT, th - ZONE, th)
        out['holds'][kind] = {'arr': a[1] - a[0], 'dep': d[1] - d[0], 'arr_before_stop': -a[0], 'dep_after_start': d[1]}
    # what the length of the blocks and of the fan of points do to the least time between two trains (model/headway.py, one value changed)
    out['sweep'] = {'block': [], 'throat': []}
    keep = (dict(H.SIGNAL['auto']), dict(H.SIGNAL['rule']), dict(H.THROAT))
    brief = lambda c: {'tgv_second': c['need']['tgv_second'], 'ter_second': c['need']['ter_second'], 'cycle': c['need']['cycle'], 'spare': c['hours']['full']['sum']['spare_min'],
                       'short': c['hours']['full']['sum']['short'], 'taken': c['hours']['full']['sum']['taken_max']}
    for b in (100.0, 200.0, 300.0, 400.0, 600.0, 800.0):
        for k in ('auto', 'rule'): H.SIGNAL[k]['block'] = b; H.SIGNAL[k]['throat'] = min(b, 100.0)
        out['sweep']['block'].append({'block': b, 'central': brief(H.case(Hh, 'central', 'auto', H.V_THROAT, rows=False)), 'rule': brief(H.case(Hh, 'rule', 'rule', H.V_THROAT, rows=False))})
    H.SIGNAL['auto'].update(keep[0]); H.SIGNAL['rule'].update(keep[1])
    for t in (200.0, 300.0, 400.0, 500.0, 600.0):
        H.THROAT[H.V_THROAT] = t
        out['sweep']['throat'].append({'throat': t, 'central': brief(H.case(Hh, 'central', 'auto', H.V_THROAT, rows=False)), 'rule': brief(H.case(Hh, 'rule', 'rule', H.V_THROAT, rows=False))})
    H.THROAT.update(keep[2])
    out['sweep']['by_block'] = {'b%d' % r['block']: r for r in out['sweep']['block']}; out['sweep']['by_throat'] = {'t%d' % r['throat']: r for r in out['sweep']['throat']}
    # platform tracks of each half of each station, and the trains they take
    out['halves'] = {}
    for sc, hour in Hh.items():
        ev = movements(hour); hv = {}
        for (st, end), mv in ev.items():
            for move in ('arr', 'dep'):
                for m in mv[move]:
                    if (move == 'arr') != ((end == 'outer') == (m[3][0] == 'in')): continue        # count each stop once: by its arrival
                    h = hv.setdefault(st, {}).setdefault(m[3][0], {'tgv_tracks': set(), 'ter_tracks': set(), 'tgv': 0, 'ter': 0})
                    h[m[1] + '_tracks'].add(m[3][2]); h[m[1]] += 1
        out['halves'][sc] = {st: {half: {'tgv_tracks': len(v['tgv_tracks']), 'ter_tracks': len(v['ter_tracks']), 'tgv': v['tgv'], 'ter': v['ter']} for half, v in d.items()} for st, d in hv.items()}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w'), indent=1)
    for case, res in out['cases'].items():
        for sc, r in res.items():
            print(case, sc, {k: (v['conflicts'], v['pairs'], None if v['least'] is None else round(v['least'])) for k, v in r['sum'].items()})
            if case == 'central_auto':
                for e in r['ends']:
                    if len(e['tunnels']) == 2:
                        print('   ', e['station'], e['end'], e['by_tunnel'], 'across', e['across']['conflicts'], '/', e['across']['pairs'], round(e['across']['least']), '(other side', e['across_other']['conflicts'], ')',
                              'arr', e['arrivals']['conflicts'], '/', e['arrivals']['pairs'], e['arrivals']['least'] and round(e['arrivals']['least']), 'dep', e['departures']['conflicts'], '/', e['departures']['pairs'], e['departures']['least'] and round(e['departures']['least']))
    for k in ('block', 'throat'):
        rows = out['sweep'][k]
        for r in rows: print('sweep', k, r[k], {c: (round(r[c]['tgv_second']), round(r[c]['spare']), r[c]['short'], round(100 * r[c]['taken'])) for c in ('central', 'rule')})
    print('across load full', [(e['station'], e['end'], round(e['across']['load'], 2), round(e['across_other']['load'], 2)) for e in out['cases']['central_auto']['full']['ends'] if len(e['tunnels']) == 2])
    print('holds', out['holds']); print('halves full', out['halves']['full'])


if __name__ == '__main__':
    main()
