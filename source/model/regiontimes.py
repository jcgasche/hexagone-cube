#!/usr/bin/env python3
"""Travel times from every station to every other station of the Paris region, for any version of the network (chapter 'times').

A set of reusable steps. Each version of the network is a small JSON file (model/inputs/networks/*.json) that says how it differs
from the published timetable; the same commands run on any of them, and 'compare' sets two versions side by side.

    python3 model/regiontimes.py run <network.json> --gtfs <IDFM GTFS folder>      -> model/inputs/regiontimes/<name>.npz
    python3 model/regiontimes.py weights --communes <communes.json> --mobpro <mobpro_flows.csv.gz>
                                                                                    -> model/inputs/regiontimes/weights.npz
    python3 model/regiontimes.py compare <base name> <variant name>                 (prints the gains of the variant over the base)
    python3 model/regiontimes.py gpe --gtfs <IDFM GTFS folder>                      -> model/inputs/networks/gpe.json (metro lines 15 to 18)
    python3 model/regiontimes.py riders [names]                                     -> model/inputs/regiontimes/riders.json (people through the watched sections)
    python3 model/regiontimes.py validate                                           (today's times beside a public journey planner)
    python3 model/regiontimes.py export                                             -> src/sections/times/data.json

WHAT IS MEASURED. The time, on the clock, from the platforms of one station to the platforms of another, in the morning peak of one
Tuesday, read from the real timetable train by train (metro, RER, Transilien, tram and the TER trains that the Ile-de-France timetable
holds; no TGV). A traveller reaches the first platform at a time taken every 3 minutes between 7:30 and 8:30, takes the trains that
get there soonest, and changes with the walking times that Ile-de-France Mobilites publishes between platforms. The time of a pair of
stations is the average over those starting times. Only the first wait is capped, at FIRST_WAIT_CAP minutes: where trains are few,
riders come for their train (ASSUMPTION).

HOW. A connection scan (Dibbelt, Pajor, Strasser, Wagner, 2013): every hop of every train between two stops, sorted by departure,
is read once; a hop can be taken if the traveller is already on the train or stands at its stop when it leaves. All origins and all
starting times are carried together in arrays, so one pass of the timetable gives a whole block of the station-to-station table.

A NETWORK FILE holds:
  "name", "label", "about"   what the version is;
  "new_stops"   platforms that do not exist today: {"id", "name", "lon", "lat", "member_of": [stations they belong to],
                "like": [existing stops whose walking times to the other platforms they take], "to_like_min": minutes to those stops};
  "walks"       [stop, stop, minutes] between new platforms;
  "through"     lines joined end to end: {"name", "a": {"lines", "terminal"}, "b": {"lines", "terminal"}, "path": [[stop, minute], ...],
                "dwell_min", "max_wait_min"}. Every train of the lines of side a that ends at a's terminal runs on along the path
                (minute = arrival at each stop, counted from its arrival at the first) and then becomes the next train of side b to
                leave b's terminal, if one leaves within max_wait_min: it waits at the last stop of the path until that train's time.
                The same the other way. A train with no partner ends at the last stop of the path; a departure with no partner starts
                from its end of the path.
  "matched_timetable": true   the timetable is rewritten for the joined lines: the onward train leaves as soon as the train from the
                other side is ready, so nobody waits at the join, and its whole onward run is that much earlier.
Nothing else of the timetable is touched: on both sides every train keeps its times, its stops and its branch, so no connection that
exists today is lost. The wait at the last stop of the path is the price of that caution; a timetable drawn for the joined lines
would remove most of it, so the gains are on the low side.

Everything marked ASSUMPTION is a judgement, listed in the chapter."""
import json, os, sys, math, csv, collections, time

HERE = os.path.dirname(os.path.abspath(__file__))
NETS = os.path.join(HERE, 'inputs', 'networks')
RES = os.path.join(HERE, 'inputs', 'regiontimes')
RAW = os.path.join(HERE, 'inputs', 'traffic', 'raw')
OUT = os.path.join(HERE, '..', 'src', 'sections', 'times', 'data.json')

DAY = '20261103'                       # the Tuesday read from the timetable
T0, T1, STEP = 7.5 * 3600, 8.5 * 3600, 180       # starting times: every 3 minutes from 7:30 to 8:30
LOOK = 3600                            # a traveller may let trains go for up to an hour to catch a better one (matters only where trains are hourly)
FIRST_WAIT_CAP = 600                   # seconds of the first wait that are counted (ASSUMPTION)
T_END = 12 * 3600                      # trains read until noon: journeys of up to two and a half hours
SAME_STOP = 180                        # seconds to change between two lines at the platforms of one railway station, where the timetable file gives no time (ASSUMPTION)
SAME_STOP_FAR = 300                    # the same between the underground and the surface platforms of Gare du Nord and Gare de Lyon (ASSUMPTION)
FAR = {'IDFM:monomodalStopPlace:462394': ({'B', 'D'}, {'H', 'K', 'TER'}), 'IDFM:monomodalStopPlace:470195': ({'A', 'D'}, {'R', 'TER'})}
CLOSE_S = 900                          # walks are chained (platform to platform to platform) up to 15 minutes
BIG = 10 ** 9
NOTRE_DAME = (2.3488, 48.8534)


def hav(lon1, lat1, lon2, lat2):
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


# ====================================================================== the timetable
def load_timetable(gtfs):
    """The trains of the day: a list of trips, each {'line', 'kind', 'stops': [[stop, arrival s, departure s, may board, may alight, line], ...]},
    the stops {id: (name, lon, lat, station id)} and the published walking times [(stop, stop, seconds)]."""
    import pandas as pd
    tsec = lambda x: int(x[:-6]) * 3600 + int(x[-5:-3]) * 60 + int(x[-2:])
    stops = pd.read_csv(f'{gtfs}/stops.txt', dtype=str); routes = pd.read_csv(f'{gtfs}/routes.txt', dtype=str)
    trips = pd.read_csv(f'{gtfs}/trips.txt', dtype=str); cal = pd.read_csv(f'{gtfs}/calendar.txt', dtype=str); cd = pd.read_csv(f'{gtfs}/calendar_dates.txt', dtype=str)
    wd = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][__import__('datetime').date(int(DAY[:4]), int(DAY[4:6]), int(DAY[6:])).weekday()]
    act = set(cal[(cal[wd] == '1') & (cal.start_date <= DAY) & (cal.end_date >= DAY)].service_id) | set(cd[(cd.date == DAY) & (cd.exception_type == '1')].service_id)
    act -= set(cd[(cd.date == DAY) & (cd.exception_type == '2')].service_id)
    trips = trips[trips.service_id.isin(act)].merge(routes[['route_id', 'route_short_name', 'route_type']], on='route_id')
    st = pd.read_csv(f'{gtfs}/stop_times.txt', dtype=str, usecols=['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence', 'pickup_type', 'drop_off_type'])
    st = st[st.trip_id.isin(set(trips.trip_id))].copy()
    st['arr'] = st.arrival_time.map(tsec); st['dep'] = st.departure_time.map(tsec); st['seq'] = st.stop_sequence.astype(int)
    st = st.sort_values(['trip_id', 'seq'])
    line = dict(zip(trips.trip_id, trips.route_short_name)); kind = dict(zip(trips.trip_id, trips.route_type.astype(int)))
    out = []; cur = None
    for tid, s, a, d, pu, do in zip(st.trip_id, st.stop_id, st.arr, st.dep, st.pickup_type, st.drop_off_type):
        if cur is None or cur['id'] != tid:
            cur = {'id': tid, 'line': line[tid], 'kind': kind[tid], 'stops': []}; out.append(cur)
        cur['stops'].append([s, int(a), int(d), pu != '1', do != '1', cur['line']])
    out = [t for t in out if len(t['stops']) > 1 and t['stops'][-1][1] >= T0 - 3600 and t['stops'][0][2] <= T_END]
    S = {r.stop_id: (r.stop_name, float(r.stop_lon), float(r.stop_lat), r.parent_station if isinstance(r.parent_station, str) else r.stop_id) for r in stops.itertuples()}
    tr = pd.read_csv(f'{gtfs}/transfers.txt', dtype=str)
    walks = [(r.from_stop_id, r.to_stop_id, int(float(r.min_transfer_time or 120))) for r in tr.itertuples() if r.from_stop_id != r.to_stop_id]
    return out, S, walks


# ====================================================================== a version of the network
OPS = ('new_stops', 'walks', 'new_lines', 'split', 'extend', 'through', 'watch')


def read_network(path):
    """A network file, with the files it includes read first (their steps come before its own)."""
    net = json.load(open(path)); steps = {k: [] for k in OPS}
    for inc in net.get('include', []):
        sub = read_network(os.path.join(os.path.dirname(path), inc + '.json'))
        for k in OPS: steps[k] += sub[k]
    for k in OPS: steps[k] += net.get(k, [])
    net.update(steps); return net


def _clock(x):
    h, m = x.split(':'); return int(h) * 3600 + int(m) * 60


def apply_network(trips, S, walks, net):
    """The timetable of a version: new platforms and their walks, new lines, lines cut in two, lines run on along existing tracks, and
    lines joined end to end. Returns (trips, S, walks, members, log): members = {new stop: [stations it belongs to]}; log = what was joined."""
    S = dict(S); walks = list(walks); members = {}; log = []
    for ns in net.get('new_stops', []):
        S[ns['id']] = (ns['name'], ns['lon'], ns['lat'], ns['id']); members[ns['id']] = ns.get('member_of') or [ns['id']]
        for like in ns.get('like', []):
            for a, b, s in list(walks):
                if a == like: walks.append((ns['id'], b, s))
                if b == like: walks.append((a, ns['id'], s))
            w = int(ns.get('to_like_min', 5) * 60); walks += [(ns['id'], like, w), (like, ns['id'], w)]
    for a, b, m in net.get('walks', []):
        walks += [(a, b, int(m * 60)), (b, a, int(m * 60))]
    par = lambda s: S[s][3]
    # ---- new lines: a train every 'headway_min' each way, stops = [[stop, minutes from the first stop, arrival], ...]
    for nl in net.get('new_lines', []):
        hw = nl['headway_min'] * 60.0; dw = int(nl.get('dwell_s', 30)); st = nl['stops']; total = st[-1][1]
        t = float(_clock(nl.get('from', '05:30'))); end = _clock(nl.get('to', '12:30')); k = 0
        while t <= end:
            for way, seq in ((0, st), (1, [[q[0], total - q[1]] for q in reversed(st)])):
                t0 = t + (hw / 2 if way else 0)
                trips.append({'id': 'new:%s:%d:%d' % (nl['line'], way, k), 'line': nl['line'], 'kind': nl.get('kind', 1),
                              'stops': [[q[0], int(t0 + q[1] * 60), int(t0 + q[1] * 60) + dw, True, True, nl['line']] for q in seq]})
            t += hw; k += 1
        log.append({'name': 'new line ' + nl['line'], 'trains': 2 * k, 'stops': len(st), 'minutes': total, 'headway_min': nl['headway_min']})
    # ---- lines cut in two between two stops that follow each other: each part becomes a train of its own
    for sp in net.get('split', []):
        pair = set(sp['at']); out = []; cut = 0
        for t in trips:
            st = t['stops']; i = next((i for i in range(len(st) - 1) if t['line'] in sp['lines'] and {st[i][0], st[i + 1][0]} == pair), None)
            if i is None: out.append(t); continue
            cut += 1
            for part, seg in (('a', st[:i + 1]), ('b', st[i + 1:])):
                if len(seg) > 1: out.append({'id': t['id'] + ':' + part, 'line': t['line'], 'kind': t['kind'], 'stops': seg})
        trips = out; log.append({'name': 'cut ' + '+'.join(sp['lines']), 'trains': cut})
    # ---- lines run on along tracks that exist: path = [[stop, minutes from the terminal, line whose platform it is], ...]
    for ex in net.get('extend', []):
        dwell = int(ex.get('dwell_min', 0.7) * 60); pth = ex['path']; n_in = n_out = 0
        via, not_via = set(ex.get('via', [])), set(ex.get('not_via', []))            # only the trains that call (or do not call) at these stations: one branch of a line
        for t in trips:
            last, first = t['stops'][-1], t['stops'][0]
            if via or not_via:
                called = {par(q[0]) for q in t['stops']} | {q[0] for q in t['stops']}
                if (via and not called & via) or (not_via and called & not_via): continue
            if last[5] in ex['lines'] and par(last[0]) == ex['terminal'] and not t.get('ext'):
                t0 = last[1]; lab = lambda q: q[2] if len(q) > 2 else last[5]
                t['stops'][-1] = [pth[0][0], t0, t0 + dwell, True, True, lab(pth[0])]
                for q in pth[1:]:
                    a = t0 + int(q[1] * 60); t['stops'].append([q[0], a, a + dwell, True, True, lab(q)])
                t['ext'] = True; n_in += 1
            elif first[5] in ex['lines'] and par(first[0]) == ex['terminal'] and not t.get('ext'):
                d0 = first[2]; lab = lambda q: q[2] if len(q) > 2 else first[5]
                pre = [[q[0], d0 - int(q[1] * 60) - dwell, d0 - int(q[1] * 60), True, True, lab(q)] for q in reversed(pth)]
                t['stops'] = pre + t['stops'][1:]; t['ext'] = True; n_out += 1
        log.append({'name': ex['name'], 'arrivals': n_in, 'departures': n_out})
    for sp in net.get('through', []):
        dwell = int(sp['dwell_min'] * 60); maxw = int(sp['max_wait_min'] * 60); path = sp['path']; total = path[-1][1]
        for A, B, pth in ((sp['a'], sp['b'], path), (sp['b'], sp['a'], [[q[0], total - q[1]] + q[2:] for q in reversed(path)])):
            inbound = sorted((t for t in trips if t['stops'][-1][5] in A['lines'] and par(t['stops'][-1][0]) == A['terminal'] and not t.get('ext')), key=lambda t: t['stops'][-1][1])
            outbound = sorted((t for t in trips if t['stops'][0][5] in B['lines'] and par(t['stops'][0][0]) == B['terminal'] and not t.get('joined') and not t.get('ext')), key=lambda t: t['stops'][0][2])
            ready = []
            for t in inbound:                                           # every arriving train runs on along the path
                t0 = t['stops'][-1][1]; ln = t['stops'][-1][5]; lab = lambda q: q[2] if len(q) > 2 else ln
                t['stops'][-1] = [pth[0][0], t0, t0 + dwell, True, True, lab(pth[0])]
                for q in pth[1:]:
                    a = t0 + int(q[1] * 60); t['stops'].append([q[0], a, a + dwell, True, True, lab(q)])
                t['joined'] = True; ready.append(t['stops'][-1][2])
            j = 0; done = 0; waits = []
            for i, t in enumerate(inbound):                             # ... waits for the next departure of the other side, and becomes that train
                while j < len(outbound) and outbound[j]['stops'][0][2] < ready[i]: j += 1
                if j >= len(outbound): break
                d = outbound[j]['stops'][0][2]
                if d - ready[i] > maxw: continue
                nxt_alone = i + 1 < len(inbound) and ready[i + 1] <= d and not (j + 1 < len(outbound) and outbound[j + 1]['stops'][0][2] - ready[i + 1] <= maxw)
                if nxt_alone: continue                                  # the next train is closer to this departure and has no other: it takes it
                o = outbound[j]; j += 1; waits.append((d - ready[i]) / 60.0)
                if net.get('matched_timetable'):                        # a timetable written for the joined line: the onward train leaves as soon as this one is ready
                    sh = d - ready[i]; t['stops'] += [[x[0], x[1] - sh, x[2] - sh] + list(x[3:]) for x in o['stops'][1:]]
                else:
                    t['stops'][-1][2] = d
                    t['stops'] += [list(x) for x in o['stops'][1:]]
                o['gone'] = True; done += 1
            for o in outbound:                                          # a departure with no partner starts from its own end of the path
                if not o.get('gone'):
                    s0 = o['stops'][0]; q = pth[-1]; o['stops'][0] = [q[0], s0[1], s0[2], True, True, q[2] if len(q) > 2 else s0[5]]; o['joined'] = True
            log.append({'name': sp['name'], 'from': '+'.join(A['lines']), 'to': '+'.join(B['lines']), 'arrivals': len(inbound), 'departures': len(outbound), 'joined': done,
                        'mean_wait_min': round(sum(waits) / len(waits), 1) if waits else None})
            trips = [t for t in trips if not t.get('gone')]
    # ---- sections watched: which hops count for each (to know how many travellers ride through a tunnel or reach a terminal on a line)
    watch = net.get('watch', [])
    def bits(a, b):
        m = 0
        for i, w in enumerate(watch):
            if 'pairs' in w: hit = any({a[0], b[0]} == set(p) for p in w['pairs'])
            else: hit = (a[0] in w['at'] or b[0] in w['at']) and (a[5] in w['lines'] or b[5] in w['lines']) and not ({a[0], b[0]} & set(w.get('except', [])))
            if hit: m |= 1 << i
        return m
    if watch:
        near = set(x for w in watch for p in w.get('pairs', []) for x in p) | set(x for w in watch for x in w.get('at', []))
        for t in trips:
            st = t['stops']; t['watch'] = [bits(st[k], st[k + 1]) if (st[k][0] in near or st[k + 1][0] in near) else 0 for k in range(len(st) - 1)]
    return trips, S, walks, members, log


# ====================================================================== the lines of the Grand Paris Express, not yet in the timetable
GPE_HEADWAY = {'15': 2.5, '16': 4.0, '17': 4.0, '18': 4.0}     # minutes between trains at the peak: 2 to 3 published for line 15; lines 16, 17, 18 ASSUMPTION
GPE_WALK = (3.0, 70.0)                 # minutes to change between a new platform and a platform that exists: 3, plus the distance at 70 m a minute (ASSUMPTION)
GPE_NEAR_M = 350                       # a platform that exists within 350 m is a connection
GPE_MIN_PER_KM = 36.9 / 28.8           # where no run time is published (line 15 east): the minutes per straight-line km of line 15 south
GPE_18_MIN = 30.0                      # line 18 end to end, as published in 2019 (the 2015 run times add up to 33.5 with a station since dropped)


def make_gpe(gtfs):
    """networks/gpe.json: lines 15, 16, 17 and 18 as new lines, from inputs/traffic/raw/gpe_lines.json (stations, run times) and the stops of the timetable."""
    import re, unicodedata, pickle
    cache = os.path.join(gtfs, '..', 'timetable_%s.pkl' % DAY)
    trips, S, walks = pickle.load(open(cache, 'rb')) if os.path.exists(cache) else load_timetable(gtfs)
    kind = {}
    for t in trips:
        for q in t['stops']: kind.setdefault(q[0], set()).add(t['kind'])
    G = json.load(open(os.path.join(RAW, 'gpe_lines.json')))
    slug = lambda x: re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', x).encode('ascii', 'ignore').decode().lower()).strip('-')
    stops = {}; wk = []; seq = {}
    for L in G['lines']:
        ids = []
        for st in L['stations']:
            sid = 'GPE:' + slug(st['name']); ids.append(sid)
            if sid in stops: continue
            near = sorted((hav(st['lon'], st['lat'], S[q][1], S[q][2]) * 1000, q) for q in kind if hav(st['lon'], st['lat'], S[q][1], S[q][2]) * 1000 <= GPE_NEAR_M)
            rail = [q for d, q in near if kind[q] & {1, 2}]
            stops[sid] = {'id': sid, 'name': st['name'], 'lon': st['lon'], 'lat': st['lat'], 'member_of': [S[rail[0]][3]] if rail else []}
            for d, q in near: wk.append([sid, q, round(GPE_WALK[0] + d / GPE_WALK[1], 1)])
        mins = [0.0]
        for seg, a, b in zip(L['between_stations'], L['stations'], L['stations'][1:]):
            mins.append(mins[-1] + (seg['run_time_s'] / 60.0 if seg.get('run_time_s') else hav(a['lon'], a['lat'], b['lon'], b['lat']) * GPE_MIN_PER_KM))
        if L['section'] == '18': mins = [m * GPE_18_MIN / mins[-1] for m in mins]
        seq[L['section']] = (ids, mins)
    def chain(*parts):                                                  # sections end to end; (name, True) = run backwards
        out = []; t = 0.0
        for name, back in parts:
            ids, mins = seq[name]
            if back: ids = ids[::-1]; mins = [mins[-1] - m for m in mins[::-1]]
            for k, (i, m) in enumerate(zip(ids, mins)):
                if k == 0 and out: continue
                out.append([i, round(t + m, 2)])
            t += mins[-1]
        return out
    lines = [{'line': '15', 'kind': 1, 'headway_min': GPE_HEADWAY['15'], 'stops': chain(('15 Sud', True), ('15 Ouest', False), ('15 Est', False))},
             {'line': '16', 'kind': 1, 'headway_min': GPE_HEADWAY['16'], 'stops': chain(('16', False))},
             {'line': '17', 'kind': 1, 'headway_min': GPE_HEADWAY['17'], 'stops': chain(('17', False))},
             {'line': '18', 'kind': 1, 'headway_min': GPE_HEADWAY['18'], 'stops': chain(('18', False))}]
    net = {'name': 'gpe', 'label': 'Lines 15, 16, 17 and 18',
           'about': 'The lines of the Grand Paris Express that are not in the timetable yet, complete, as they are planned to be when the project opens: line 15 as one line from Noisy-Champs '
                    'round by Pont de Sevres and Saint-Denis Pleyel to Champigny Centre, lines 16, 17 and 18. Run times between stations as published by the Societe des grands projets (2015), '
                    'line 18 brought to the 30 minutes published in 2019; line 15 east from its length (ASSUMPTION). A train every 2.5 minutes on line 15 (2 to 3 published), every 4 minutes on '
                    'lines 16, 17 and 18 (ASSUMPTION). A change to a platform that exists within 350 m takes 3 minutes plus the distance at 70 m a minute (ASSUMPTION); the lines of the Grand Paris '
                    'Express share one platform group where they meet.',
           'new_stops': list(stops.values()), 'walks': wk, 'new_lines': lines}
    json.dump(net, open(os.path.join(NETS, 'gpe.json'), 'w'), ensure_ascii=False, indent=1)
    for l in lines: print('  line', l['line'], len(l['stops']), 'stops', l['stops'][-1][1], 'min')
    print('  ', len(stops), 'stations,', sum(1 for v in stops.values() if v['member_of']), 'at a station that exists,', len(wk), 'walks')
    for v in stops.values(): print('    ', v['name'], '->', [S[w[1]][0] + ' %.1f' % w[2] for w in wk if w[0] == v['id']][:4], '| station', v['member_of'])


# ====================================================================== the scan
def build(trips, S, walks, members):
    """Nodes (a metro or tram stop; a railway stop once per line, so that changing line there takes time; a new platform), walks between
    nodes, and the hops sorted by departure."""
    import numpy as np
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    node = {}; names = []; lines_at = collections.defaultdict(set); kinds = collections.defaultdict(set)
    def nid(stop, line, kind):
        key = (stop, line) if (kind == 2 and stop not in members) else (stop, None)
        if key not in node: node[key] = len(names); names.append(key)
        lines_at[stop].add(line); kinds[stop].add(kind)
        return node[key]
    hops = []
    for ti, t in enumerate(trips):
        st = t['stops']
        for k in range(len(st) - 1):
            a, b = st[k], st[k + 1]
            if a[2] > T_END or b[1] < T0 - 1800: continue
            hops.append((a[2], k, nid(a[0], a[5], t['kind']), nid(b[0], b[5], t['kind']), max(b[1], a[2]), ti, a[3], b[4], t['watch'][k] if 'watch' in t else 0))
    hops.sort(key=lambda h: (h[0], h[5], h[1]))
    by_stop = collections.defaultdict(list)
    for (stop, line), i in node.items(): by_stop[stop].append((line, i))
    W = {}
    def add(i, j, s):
        if i != j and s < W.get((i, j), BIG): W[(i, j)] = s
    for a, b, s in walks:
        for _, i in by_stop.get(a, []):
            for _, j in by_stop.get(b, []): add(i, j, s)
    for stop, lst in by_stop.items():                                   # two lines at the platforms of one railway station
        for la, i in lst:
            for lb, j in lst:
                if i == j: continue
                far = FAR.get(stop); s = SAME_STOP_FAR if far and ((la in far[0] and lb in far[1]) or (la in far[1] and lb in far[0])) else SAME_STOP
                add(i, j, s)
    n = len(names)
    if W:
        ij = np.array(list(W.keys())); G = csr_matrix((np.array(list(W.values()), float), (ij[:, 0], ij[:, 1])), shape=(n, n))
        D = dijkstra(G, directed=True, limit=CLOSE_S)                   # walks chained, up to 15 minutes
        foot = [[] for _ in range(n)]
        for i, j in zip(*np.where(np.isfinite(D) & (D > 0))): foot[i].append((int(j), int(D[i, j])))
    else: foot = [[] for _ in range(n)]
    station = collections.defaultdict(list)                             # station -> its nodes (a new platform belongs to the stations it is given)
    for (stop, line), i in node.items():
        for p in (members[stop] if stop in members else [S[stop][3]]): station[p].append(i)
    return {'names': names, 'hops': hops, 'foot': foot, 'station': station, 'lines_at': lines_at, 'kinds': kinds, 'n': n}


def scan(net, origins, verbose=True, nwatch=0):
    """Minutes from each station of 'origins' to every station: the average over the starting times, the first wait capped.
    With sections watched, also the share of those starting times whose quickest journey rides through each section (0 to 100)."""
    import numpy as np
    stations = sorted(net['station']); spos = {s: i for i, s in enumerate(stations)}
    taus = np.arange(T0, T1 + LOOK + 1, STEP).astype(np.int32); K = len(taus); KE = int((T1 - T0) // STEP) + 1
    hops = net['hops']; nh = len(hops); foot = net['foot']
    ntr = max(h[5] for h in hops) + 1
    out = np.full((len(origins), len(stations)), np.nan, np.float32)
    use = np.zeros((nwatch, len(origins), len(stations)), np.uint8) if nwatch else None
    batch = max(1, (4500 if nwatch else 9000) // K)
    members = [np.array(net['station'][s]) for s in stations]; cols = np.arange(K); win = int(LOOK // STEP) + 1
    for b0 in range(0, len(origins), batch):
        ob = origins[b0:b0 + batch]; R = len(ob) * K
        A = np.full((net['n'], R), BIG, np.int32); F = np.zeros((ntr, R), bool)
        if nwatch: U = np.zeros((net['n'], R), np.uint16); UT = np.zeros((ntr, R), np.uint16)      # sections ridden: to reach each platform, aboard each train
        for oi, o in enumerate(ob):
            sl = slice(oi * K, (oi + 1) * K)
            for i in net['station'][o]:
                A[i, sl] = np.minimum(A[i, sl], taus)
                for j, w in foot[i]: A[j, sl] = np.minimum(A[j, sl], taus + w)
        for dep, _, a, b, arr, tr, pick, drop, wbit in hops:
            f = F[tr]
            if pick:
                can = A[a] <= dep
                if nwatch:
                    fresh = can & ~f
                    if fresh.any(): np.copyto(UT[tr], U[a], where=fresh)
                np.logical_or(f, can, out=f)
            if not f.any(): continue
            if wbit: np.bitwise_or(UT[tr], np.uint16(wbit), out=UT[tr], where=f)
            if not drop: continue
            new = np.where(f, np.int32(arr), np.int32(BIG))
            better = new < A[b]
            if not better.any(): continue
            np.minimum(A[b], new, out=A[b])
            if nwatch:
                np.copyto(U[b], UT[tr], where=better)
                for j, w in foot[b]:
                    nw = new + np.int32(w); bj = nw < A[j]
                    if bj.any(): np.copyto(U[j], UT[tr], where=bj); np.minimum(A[j], nw, out=A[j])
            else:
                for j, w in foot[b]: np.minimum(A[j], new + np.int32(w), out=A[j])
        # arrival at each station = the first of its platforms reached
        for oi, o in enumerate(ob):
            sl = slice(oi * K, (oi + 1) * K)
            if nwatch:
                arr = np.empty((len(stations), K), np.int32); flg = np.empty((len(stations), K), np.uint16)
                for si, m in enumerate(members):
                    sub = A[m, sl]; am = sub.argmin(axis=0); arr[si] = sub[am, cols]; flg[si] = U[m, sl][am, cols]
            else: arr = np.stack([A[m, sl].min(axis=0) for m in members])                             # stations x starting times
            jour = np.where(arr < BIG, arr - taus[None, :], BIG).astype(np.float64)                   # seconds from each starting time
            best = np.full((len(stations), KE), np.inf); pickk = np.zeros((len(stations), KE), np.int64)
            for k in range(KE):
                m1 = min(K, k + win)
                wait = np.minimum(taus[k:m1] - taus[k], FIRST_WAIT_CAP)[None, :]
                cand = np.where(jour[:, k:m1] < BIG, jour[:, k:m1] + wait, np.inf)
                best[:, k] = cand.min(axis=1)
                if nwatch: pickk[:, k] = k + cand.argmin(axis=1)
            ok = np.isfinite(best).all(axis=1)
            out[b0 + oi, ok] = (best[ok].mean(axis=1) / 60.0).astype(np.float32)
            out[b0 + oi, spos[o]] = 0.0
            if nwatch:
                fl = np.take_along_axis(flg, pickk, axis=1)                                            # the sections ridden by the journey chosen at each starting time
                for w in range(nwatch): use[w, b0 + oi, ok] = np.round(((fl[ok] >> w) & 1).mean(axis=1) * 100).astype(np.uint8)
        if verbose: print(f'  scanned {min(b0 + batch, len(origins))}/{len(origins)} origins', flush=True)
    return stations, out, use


def run(net_file, gtfs):
    import numpy as np, pickle
    net = read_network(net_file); t0 = time.time()
    cache = os.path.join(gtfs, '..', 'timetable_%s.pkl' % DAY)                    # the day's trains, read once from the timetable folder
    if os.path.exists(cache): trips, S, walks = pickle.load(open(cache, 'rb'))
    else:
        trips, S, walks = load_timetable(gtfs)
        try: pickle.dump((trips, S, walks), open(cache, 'wb'))
        except OSError: pass
    trips, S, walks, members, log = apply_network(trips, S, walks, net)
    for l in log: print('  ', l)
    N = build(trips, S, walks, members)
    # the stations of the table: those a metro or a train serves (tram stops are used on the way, not listed)
    serves = collections.defaultdict(set); kinds = collections.defaultdict(set)
    for stop in N['lines_at']:
        for p in (members[stop] if stop in members else [S[stop][3]]):
            serves[p] |= N['lines_at'][stop]; kinds[p] |= N['kinds'][stop]
    origins = sorted(s for s in N['station'] if kinds[s] & {1, 2})
    print(f"  {len(trips)} trains, {len(N['hops'])} hops, {N['n']} platforms, {len(origins)} stations of {len(N['station'])}", flush=True)
    watch = [w['name'] for w in net.get('watch', [])]
    stations, M, use = scan(N, origins, nwatch=len(watch))
    keep = [stations.index(s) for s in origins]; M = M[:, keep]
    os.makedirs(RES, exist_ok=True); out = os.path.join(RES, net['name'] + '.npz')
    extra = {'watch': np.array(watch), 'usage': use[:, :, keep]} if watch else {}
    np.savez_compressed(out, minutes=np.round(M, 2).astype(np.float32), ids=np.array(origins), names=np.array([S[s][0] for s in origins]),
                        lon=np.array([S[s][1] for s in origins]), lat=np.array([S[s][2] for s in origins]),
                        lines=np.array(['|'.join(sorted(serves[s])) for s in origins]), kinds=np.array(['|'.join(str(k) for k in sorted(kinds[s])) for s in origins]),
                        log=json.dumps(log), label=net.get('label', net['name']), **extra)
    print(f'  {out}  {M.shape}  {time.time() - t0:.0f} s', flush=True)


# ====================================================================== who is concerned: entries at the stations, journeys to work
# station numbers of the validation file that differ from the timetable's: numbers that changed during the year, and the RER platforms of
# Chatelet-Les Halles, counted by the RATP under the metro station Chatelet
ENTRY_ALIAS = {('810', '71264'): '474151', '74000': '478733', '63650': '463850', '74371': '463843', '63278': '63284'}


def station_entries():
    """Entries on an average working day at each station, all networks together (IDFM validations, twelve months to June 2026)."""
    tot = collections.Counter()
    with open(os.path.join(RAW, 'idfm_validations_ferre_par_station.csv'), encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter=';'):
            z = ENTRY_ALIAS.get((r['code_stif_trns'], r['id_zdc'])) or ENTRY_ALIAS.get(r['id_zdc']) or r['id_zdc']
            try: tot['IDFM:' + z] += float(r['nb_vald_12m_lun_ven']) / float(r['nb_jours_12m_lun_ven'])
            except (ValueError, ZeroDivisionError): pass
    return tot


def line_boardings():
    """Boardings a working day at each station of each RER and Transilien line (the counts fitted for the chapter 'flows')."""
    f = os.path.join(HERE, 'inputs', 'flows_network.json'); out = {}
    if os.path.exists(f):
        for line, L in json.load(open(f))['lines'].items():
            out[line] = {s: v['count'] for s, v in L.get('stations', {}).items() if v.get('count')}
    return out


ACCESS_N, ACCESS_KM = 5, 8.0           # a commune is tied to the five nearest stations of today, within 8 km, and to any new station as near
ACCESS_STORE = 12                      # nearest stations kept on file, new ones included


def access_min(d_km, ha):
    """Minutes on the clock from a commune to a station d km from its centre: part of the commune lives closer, so 0.6 x d plus a term
    for its size; on foot, or by a feeder bus (5 minutes of wait, 18 km/h, 3 minutes of walk) when that is quicker (ASSUMPTION, as in
    the job-access model of the study, without its weights)."""
    r = math.sqrt(ha / 100.0 / math.pi) if ha else 1.0; e = max(0.3, 0.6 * d_km + 0.25 * r)
    return min(e * 1.3 / 4.5 * 60, 5 + e * 1.3 / 18 * 60 + 3)


def make_weights(communes, mobpro):
    """The census journeys to work by public transport (INSEE, 2022), commune to commune, and the stations each commune uses."""
    import numpy as np, pandas as pd
    base = np.load(os.path.join(RES, ('future' if os.path.exists(os.path.join(RES, 'future.npz')) else 'today') + '.npz')); ids = list(base['ids']); lon = base['lon']; lat = base['lat']
    C = json.load(open(communes)); Z = []; seen = set()
    for r in C['communes'] + C['paris_arrondissements']:
        if r['code'] == '75056' or r['code'] in seen or not r['code'].startswith(('75', '77', '78', '91', '92', '93', '94', '95')) or 'centre' not in r: continue
        seen.add(r['code']); Z.append((r['code'], r['nom'], r['centre']['coordinates'][0], r['centre']['coordinates'][1], r.get('surface', 0)))
    pos = {z[0]: i for i, z in enumerate(Z)}; near = np.full((len(Z), ACCESS_STORE), -1, np.int32); acc = np.full((len(Z), ACCESS_STORE), np.nan, np.float32)
    now = set(np.load(os.path.join(RES, 'today.npz'))['ids']); old = np.array([s in now for s in ids])
    for k, (code, nom, zlon, zlat, ha) in enumerate(Z):
        d = np.array([hav(zlon, zlat, lo, la) for lo, la in zip(lon, lat)]); o = np.argsort(d)[:ACCESS_STORE]
        for q, j in enumerate(o):
            if d[j] <= ACCESS_KM: near[k, q] = j; acc[k, q] = access_min(float(d[j]), ha)
    df = pd.read_csv(mobpro, dtype={'COMMUNE': str, 'DCLT': str}); df = df[df.TRANS == 6]; total = float(df.SUM_IPONDI.sum())
    df['i'] = df.COMMUNE.map(pos); df['j'] = df.DCLT.map(pos); df = df.dropna(subset=['i', 'j']); df = df[df.i != df.j]
    g = df.groupby(['i', 'j']).SUM_IPONDI.sum().reset_index()
    np.savez_compressed(os.path.join(RES, 'weights.npz'), zone=np.array([z[0] for z in Z]), zname=np.array([z[1] for z in Z]), zlon=np.array([z[2] for z in Z]), zlat=np.array([z[3] for z in Z]),
                        near=near, acc=acc, near_ids=np.array(ids), old=old, i=g.i.values.astype(np.int32), j=g.j.values.astype(np.int32), t=g.SUM_IPONDI.values.astype(np.float32),
                        all_pt=np.float32(total))
    print(f'  {len(Z)} communes, {len(g)} pairs, {g.SUM_IPONDI.sum():,.0f} commuters between two communes of the region (of {total:,.0f} in the file)')


# ====================================================================== comparing two versions
CLASSES = [(-1e9, -1.0, 'slower by more than 1 min'), (-1.0, 1.0, 'within 1 min'), (1.0, 5.0, '1 to 5 min quicker'), (5.0, 10.0, '5 to 10 min quicker'),
           (10.0, 1e9, 'more than 10 min quicker')]


def load(name):
    import numpy as np
    d = np.load(os.path.join(RES, name + '.npz')); return {k: d[k] for k in d.files}


def align(A, B):
    """Two versions on one list of stations (those of either): the minutes of each, NaN where a version does not have the station."""
    import numpy as np
    ids = list(dict.fromkeys(list(A['ids']) + list(B['ids']))); pos = {s: i for i, s in enumerate(ids)}; out = []
    for V in (A, B):
        ix = np.array([pos[s] for s in V['ids']]); M = np.full((len(ids), len(ids)), np.nan); M[np.ix_(ix, ix)] = V['minutes']; out.append(M)
    meta = {}
    for k in ('names', 'lon', 'lat', 'lines'):
        v = [None] * len(ids)
        for V in (A, B):
            for s, x in zip(V['ids'], V[k]): v[pos[s]] = x
        meta[k] = np.array(v)
    return ids, out[0], out[1], meta


def journeys(M, ids, usage=None):
    """The census journeys to work on the minutes M: for each pair of communes, the quickest pair of stations (minutes door to door), and
    with 'usage' (sections x stations x stations, percent) the share of that journey riding through each section."""
    import numpy as np
    Z = np.load(os.path.join(RES, 'weights.npz')); near, acc, I, J, T = Z['near'], Z['acc'].astype(np.float64), Z['i'], Z['j'], Z['t'].astype(np.float64)
    old = Z['old'][np.maximum(near, 0)] & (near >= 0)                                             # stations of today: the five nearest; new stations: all those on file
    near = np.where((near >= 0) & (~old | (np.cumsum(old, axis=1) <= ACCESS_N)), near, -1)
    pos = {s: i for i, s in enumerate(ids)}; col = np.array([pos.get(s, -1) for s in Z['near_ids']]); near = np.where(near >= 0, col[np.maximum(near, 0)], -1)
    best = np.full(len(I), np.inf); share = np.zeros((0 if usage is None else len(usage), len(I)))
    for s in range(0, len(I), 20000):
        i, j = I[s:s + 20000], J[s:s + 20000]; ni, nj = near[i], near[j]
        m = M[np.maximum(ni, 0)[:, :, None], np.maximum(nj, 0)[:, None, :]] + acc[i][:, :, None] + acc[j][:, None, :]
        m = np.where((ni >= 0)[:, :, None] & (nj >= 0)[:, None, :] & np.isfinite(m), m, np.inf).reshape(len(i), -1)
        k = m.argmin(axis=1); best[s:s + 20000] = m[np.arange(len(i)), k]
        if usage is not None:
            a = np.take_along_axis(ni, (k // near.shape[1])[:, None], 1)[:, 0]; b = np.take_along_axis(nj, (k % near.shape[1])[:, None], 1)[:, 0]
            share[:, s:s + 20000] = usage[:, np.maximum(a, 0), np.maximum(b, 0)] / 100.0
    return best, share, (I, J, T, Z)


def riders(name, verbose=True):
    """Commuters of the census who ride through each watched section in the version 'name', one way in the morning."""
    import numpy as np
    V = load(name)
    if 'usage' not in V: return {}
    best, share, (I, J, T, Z) = journeys(V['minutes'].astype(np.float64), list(V['ids']), V['usage'])
    ok = np.isfinite(best); out = {str(w): float((share[k][ok] * T[ok]).sum()) for k, w in enumerate(V['watch'])}
    if verbose:
        print(name); [print(f'  {v:>10,.0f}  {k}') for k, v in out.items()]
    return out


def riders_file(names=None):
    """The commuters through each watched section, for every version on file (or those named): inputs/regiontimes/riders.json, read by
    model/flows.py, which turns them into passengers a day with the counts at the terminals."""
    names = names or sorted(f[:-4] for f in os.listdir(RES) if f.endswith('.npz') and f != 'weights.npz')
    out = {'unit': 'commuters of the census riding through the section, one way in the morning', 'versions': {n: {k: round(v) for k, v in riders(n, verbose=False).items()} for n in names}}
    json.dump(out, open(os.path.join(RES, 'riders.json'), 'w'), ensure_ascii=False, indent=1)
    return out


def compare(base, var, verbose=True):
    """What the version 'var' changes against 'base'. Two measures:
      reach   for each station, the average time to every other station, each weighted by the entries it has in a day; then the average
              of the stations, each weighted by its own entries;
      trips   the census journeys to work by public transport, commune to commune, each by its quickest pair of stations."""
    import numpy as np
    A, B = load(base), load(var); ids, Ma, Mb, meta = align(A, B)
    ent = station_entries(); w = np.array([ent.get(s, 0.0) for s in ids])
    ok = np.isfinite(Ma) & np.isfinite(Mb); np.fill_diagonal(ok, False)
    W = ok * w[None, :]; den = W.sum(axis=1); den[den == 0] = np.nan
    ra = (np.where(ok, Ma, 0) * W).sum(axis=1) / den; rb = (np.where(ok, Mb, 0) * W).sum(axis=1) / den; gain = ra - rb
    use = np.isfinite(gain) & (w > 0); ww = w[use]
    res = {'base': base, 'variant': var, 'label': str(B['label']), 'stations': int(use.sum()), 'entries': float(ww.sum()),
           'reach': {'base': float((ra[use] * ww).sum() / ww.sum()), 'variant': float((rb[use] * ww).sum() / ww.sum()), 'gain': float((gain[use] * ww).sum() / ww.sum()),
                     'max_gain': float(np.nanmax(gain[use])), 'max_at': str(meta['names'][np.where(use)[0][np.nanargmax(gain[use])]])}}
    cuts = [0.5, 1, 2, 5]
    res['reach']['entries_over'] = {str(c): float(ww[gain[use] >= c].sum()) for c in cuts}; res['reach']['stations_over'] = {str(c): int((gain[use] >= c).sum()) for c in cuts}
    res['reach']['entries_slower'] = float(ww[gain[use] <= -0.5].sum())
    # journeys to work
    if os.path.exists(os.path.join(RES, 'weights.npz')):
        ta, _, (I, J, T, Z) = journeys(Ma, ids); tb, _, _ = journeys(Mb, ids)
        okt = np.isfinite(ta) & np.isfinite(tb); d = ta[okt] - tb[okt]; t = T[okt]
        res['trips'] = {'commuters': float(t.sum()), 'all_in_region': float(T.sum()), 'base': float((ta[okt] * t).sum() / t.sum()), 'variant': float((tb[okt] * t).sum() / t.sum()),
                        'gain': float((d * t).sum() / t.sum()), 'hours_one_way': float((d * t).sum() / 60.0),
                        'classes': [{'label': c[2], 'lo': c[0], 'hi': c[1], 'commuters': float(t[(d >= c[0]) & (d < c[1])].sum()),
                                     'mean_gain': float((d * t)[(d >= c[0]) & (d < c[1])].sum() / max(t[(d >= c[0]) & (d < c[1])].sum(), 1e-9))} for c in CLASSES]}
        res['_od'] = (I[okt], J[okt], t, ta[okt], tb[okt])
    res['_st'] = (ids, w, ra, rb, use); res['_m'] = (Ma, Mb, meta)
    if verbose:
        r = res['reach']; print(f"{var} against {base}: {res['stations']} stations, {res['entries']:,.0f} entries a working day")
        print(f"  reach: {r['base']:.2f} -> {r['variant']:.2f} min, {r['gain']:.2f} min less on average; largest {r['max_gain']:.1f} min at {r['max_at']}")
        print('  entries at stations that gain at least', {k: f'{v:,.0f}' for k, v in r['entries_over'].items()}, '| stations', r['stations_over'], '| slower by 0.5 or more', f"{r['entries_slower']:,.0f}")
        if 'trips' in res:
            t = res['trips']; print(f"  journeys to work: {t['commuters']:,.0f} commuters, {t['base']:.2f} -> {t['variant']:.2f} min, {t['gain']:.2f} min less each; {t['hours_one_way']:,.0f} hours a morning")
            for c in t['classes']: print(f"    {c['label']:28s} {c['commuters']:>12,.0f}  (mean {c['mean_gain']:.1f} min)")
    return res


# ====================================================================== checking today's times against a journey planner
REF_ALIAS = {'montparnasse bienvenue': 'gare montparnasse', 'aeroport charles de gaulle 2 tgv': 'aeroport cdg terminal 2 tgv', "aeroport d orly": 'aeroport dorly terminaux 1 2 3'}
REF_SKIP = {('Saint-Germain-en-Laye', 'Gare de Lyon'): 'the planner sends this trip by tramway T13 on that day'}


def validate(name='today'):
    """The model's minutes on today's network beside those of a public journey planner (inputs/traffic/raw/reference_journeys.json)."""
    import numpy as np, re, unicodedata
    f = os.path.join(RAW, 'reference_journeys.json')
    if not os.path.exists(f): return None
    R = json.load(open(f)); T = load(name)
    norm = lambda x: re.sub(r'[^a-z0-9]+', ' ', unicodedata.normalize('NFKD', str(x)).encode('ascii', 'ignore').decode().lower()).strip()
    idx = {norm(n): i for i, n in enumerate(T['names'])}; rows = []; skipped = []
    for j in R['journeys']:
        a, b = norm(j['from']), norm(j['to']); a, b = REF_ALIAS.get(a, a), REF_ALIAS.get(b, b)
        if (j['from'], j['to']) in REF_SKIP or a not in idx or b not in idx:
            skipped.append({'from': j['from'], 'to': j['to'], 'why': REF_SKIP.get((j['from'], j['to']), 'station not matched')}); continue
        rows.append({'from': j['from'], 'to': j['to'], 'ref': j['duration_min'], 'model': round(float(T['minutes'][idx[a], idx[b]]), 1), 'changes': j.get('changes'),
                     'lines': ', '.join(re.sub(r' \(.*', '', l).replace('TER ', 'TER').split('TER')[0] or 'TER' for l in j.get('lines', []))})
    d = np.array([r['model'] - r['ref'] for r in rows])
    return {'rows': rows, 'skipped': skipped, 'n': len(rows), 'mean': round(float(d.mean()), 1), 'median': round(float(np.median(d)), 1), 'mean_abs': round(float(np.abs(d).mean()), 1),
            'within_5': int((np.abs(d) <= 5).sum()), 'corr': round(float(np.corrcoef([r['ref'] for r in rows], [r['model'] for r in rows])[0, 1]), 2),
            'planner': R.get('source'), 'queried': R.get('queried')}


# ====================================================================== the data of the chapter
BASE = 'future'                                                                        # the network before the project: today's, with lines 15 to 18
VERSIONS = ['plan_rer_f', 'plan_rer_g', 'plan_ter', 'plan_g_no_chatelet', 'plan', 'plan_kb_rd', 'variant_c']      # set side by side in the chapter
EXTRA = {'gpe': ('today', 'future'), 'plan_today': ('today', 'plan_today'), 'kb': ('plan', 'plan_kb_rd'), 'k_only': ('plan', 'plan_kb'), 'r_only': ('plan', 'plan_rd'), 'c_kb': ('plan_kb_rd', 'variant_c'), 'c_plan': ('plan', 'variant_c')}
GAIN_CLASSES = [(-1e9, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 1e9)]           # minutes saved on average from a station to the rest of the network
RER = ('A', 'B', 'C', 'D', 'E'); TRANSILIEN = ('H', 'J', 'K', 'L', 'N', 'P', 'R', 'U', 'V')
EXAMPLES = [('Clamart', 'Châtelet - Les Halles'), ('Vanves - Malakoff', "Gare de l'Est"), ('Versailles Chantiers', "Gare de l'Est"), ('Rambouillet', 'Gare du Nord'),
            ('Saint-Quentin en Yvelines - Montigny-le-Bretonneux', "Gare de l'Est"), ('Clichy - Levallois', "Gare de l'Est"), ('Meaux', 'Gare Montparnasse'),
            ('Chelles - Gournay', 'Gare Montparnasse'), ('Épinay - Villetaneuse', 'Gare Saint-Lazare'), ('Bécon les Bruyères', 'Gare du Nord'), ('Enghien-les-Bains', 'Gare Saint-Lazare'),
            ('Mitry - Claye', 'Gare Saint-Lazare'), ('Lagny - Thorigny', 'Châtelet - Les Halles'), ('Sarcelles - Saint-Brice', 'Gare Saint-Lazare'), ('Saint-Denis', 'Asnières-sur-Seine'),
            ('Gare du Nord', 'Gare Saint-Lazare'), ("Gare de l'Est", 'Gare Montparnasse')]
EXAMPLES_SAME = [('La Défense', 'Gare du Nord'), ('Cergy Préfecture', 'Gare du Nord'), ('Pontoise', 'Gare Montparnasse')]
# station pairs shown for the two variants studied in annexes (minutes: before the project, the plan, the variant)
EXAMPLES_KB = [('Melun', 'Châtelet - Les Halles'), ('Melun', 'Gare du Nord'), ('Fontainebleau - Avon', 'Châtelet - Les Halles'), ('Montereau', 'Gare du Nord'), ('Moret - Veneux-les-Sablons', 'Châtelet - Les Halles'),
               ('Dammartin - Juilly - Saint-Mard', 'Châtelet - Les Halles'), ('Crépy-en-Valois', 'Châtelet - Les Halles'), ('Dammartin - Juilly - Saint-Mard', 'Denfert-Rochereau'), ('Dammartin - Juilly - Saint-Mard', 'Gare Saint-Lazare')]
EXAMPLES_C = [('La Défense', 'Châtelet - Les Halles'), ('Bécon les Bruyères', 'Châtelet - Les Halles'), ('Saint-Cloud', "Gare d'Austerlitz"), ('Gare Saint-Lazare', "Gare d'Austerlitz"), ('Gare Saint-Lazare', 'Juvisy'),
              ('Clichy - Levallois', 'Bibliothèque François Mitterrand'), ('Versailles Château Rive Gauche', 'Gare du Nord'), ('Issy - Val de Seine', 'Gare du Nord'), ('Invalides', 'Gare du Nord'),
              ('Épinay - Villetaneuse', 'Saint-Michel Notre-Dame'), ('Ermont - Eaubonne', 'Invalides'), ('Enghien-les-Bains', 'Javel'), ('Juvisy', 'Châtelet - Les Halles'), ('Brétigny', 'Gare Saint-Lazare'),
              ('Choisy-le-Roi', 'La Défense'), ('Versailles Château Rive Gauche', "Gare d'Austerlitz"), ('Juvisy', 'Invalides'), ('Choisy-le-Roi', 'Champ de Mars - Tour Eiffel'), ('Bibliothèque François Mitterrand', 'Musée d\'Orsay'),
              ('Épinay - Villetaneuse', 'Gare Saint-Lazare'), ('Gare du Nord', 'Gare Saint-Lazare'), ('Bécon les Bruyères', 'Gare du Nord')]
METRO = ('1', '2', '3', '3B', '4', '5', '6', '7', '7B', '8', '9', '10', '11', '12', '13', '14')
RING = {'75': 'paris', '92': 'inner', '93': 'inner', '94': 'inner', '77': 'outer', '78': 'outer', '91': 'outer', '95': 'outer'}
SECTIONS = [('p_est', "P at Gare de l'Est"), ('n_mont', 'N at Montparnasse'), ('hk_nord', 'H and K at Gare du Nord'), ('l_sl', 'L at Saint-Lazare'), ('b', 'B, Châtelet to Gare du Nord'),
            ('d', 'D, Châtelet to Gare du Nord'), ('r_lyon', 'R at Gare de Lyon'), ('c', 'C, Saint-Michel to Austerlitz'), ('f', 'RER F tunnel, Nord-Est to Saint-Lazare'),
            ('g_n', 'RER G tunnel, Nord-Est to Châtelet'), ('g_s', 'RER G tunnel, Châtelet to Montparnasse'), ('c_sl_ch', 'New tunnel, Saint-Lazare to Châtelet'),
            ('c_ch_aus', 'New tunnel, Châtelet to Austerlitz'), ('c_sm_ch', 'New link, Saint-Michel to Châtelet'), ('c_ch_ne', 'New tunnel, Châtelet to Nord-Est (C and H)')]


def _summary(c, zn, n_od=8):
    """The figures of one comparison, as the chapter and the annexes print them."""
    import numpy as np
    r = lambda x, n=1: round(float(x), n); th = lambda x: int(round(float(x), -3)); hu = lambda x: int(round(float(x), -2))
    I, J, t, a, b = c['_od']; d = a - b; g = d >= 1; l = d <= -1
    out = {'label': c['label'], 'gain': r(c['reach']['gain'], 2), 'stations_1': c['reach']['stations_over']['1'], 'stations_5': c['reach']['stations_over']['5'],
           'entries_1': th(c['reach']['entries_over']['1']), 'entries_2': th(c['reach']['entries_over']['2']), 'entries_5': th(c['reach']['entries_over']['5']),
           'commuters_1': th(t[g].sum()), 'commuters_5': th(t[d >= 5].sum()), 'commuters_10': th(t[d >= 10].sum()), 'slower': hu(t[l].sum()),
           'slower_mean': r(-(d * t)[l].sum() / max(t[l].sum(), 1)), 'mean_of_gainers': r((d * t)[g].sum() / max(t[g].sum(), 1)),
           'hours_day': hu(2 * c['trips']['hours_one_way']), 'hours_gained': hu(2 * (d * t)[g].sum() / 60), 'hours_lost': hu(-2 * (d * t)[l].sum() / 60),
           'max_gain': r(c['reach']['max_gain']), 'max_at': c['reach']['max_at'], 'base_min': r(c['trips']['base']), 'variant_min': r(c['trips']['variant'])}
    def rows(order, test):
        o = []
        for k in order:
            if not test(d[k]) or len(o) >= n_od: continue
            o.append({'from': str(zn[I[k]]), 'to': str(zn[J[k]]), 'commuters': int(round(t[k], -1)), 'base': r(a[k], 0), 'variant': r(b[k], 0)})
        return o
    out['od_gain'] = rows(np.argsort(-(t * np.maximum(d, 0))), lambda x: x >= 3); out['od_loss'] = rows(np.argsort(-(t * np.maximum(-d, 0))), lambda x: x <= -2)
    return out


def export():
    import numpy as np, base64, gzip
    r = lambda x, n=1: round(float(x), n)
    th = lambda x: int(round(float(x), -3))
    main = compare(BASE, 'plan', verbose=False)
    ids, w, ra, rb, use = main['_st']; Ma, Mb, meta = main['_m']
    names, lon, lat, lines = meta['names'], meta['lon'].astype(np.float64), meta['lat'].astype(np.float64), meta['lines']
    keep = np.where(use)[0]; n = len(keep); gain = ra - rb
    x = (lon - NOTRE_DAME[0]) * math.cos(math.radians(NOTRE_DAME[1])) * 111.32; y = (lat - NOTRE_DAME[1]) * 110.57
    Z = np.load(os.path.join(RES, 'weights.npz')); zdep = np.array([c[:2] for c in Z['zone']]); zn = Z['zname']
    ring = []
    for k in keep:                                                      # the departement of a station: that of the nearest commune centre
        d = (Z['zlon'] - lon[k]) ** 2 * math.cos(math.radians(48.85)) ** 2 + (Z['zlat'] - lat[k]) ** 2; ring.append(RING[zdep[int(np.argmin(d))]])
    ring = np.array(ring)
    order = np.argsort(-w[keep]); keep = keep[order]; ring = ring[order]                         # busiest first: the names shown first on the map
    st = [[str(names[k]), r(x[k], 2), r(y[k], 2), str(lines[k]), int(round(w[k])), r(ra[k], 2), r(rb[k], 2)] for k in keep]
    # the two tables of minutes, a minute a step, one byte each: before the project, and what the plan saves (127 = no change, below = slower)
    Ta = Ma[np.ix_(keep, keep)]; Tb = Mb[np.ix_(keep, keep)]; ok = np.isfinite(Ta) & np.isfinite(Tb)
    half_up = lambda v: np.floor(v + 0.5)                       # whole minutes, rounded as the tables of the chapter round them
    qa = np.where(ok, np.minimum(half_up(Ta), 254), 255).astype(np.uint8)
    qg = np.where(ok, np.clip(half_up(Ta) - half_up(Tb) + 127, 0, 254), 255).astype(np.uint8)
    pack = lambda q: base64.b64encode(gzip.compress(q.tobytes(), 9, mtime=0)).decode('ascii')
    wk = w[keep]; gk = gain[keep]
    # ---- by class of gain, by ring, by line
    classes = [{'lo': lo, 'hi': hi, 'stations': int(((gk >= lo) & (gk < hi)).sum()), 'entries': th(wk[(gk >= lo) & (gk < hi)].sum())} for lo, hi in GAIN_CLASSES]
    rings = {}
    for name in ('paris', 'inner', 'outer'):
        m = ring == name; rings[name] = {'stations': int(m.sum()), 'entries': th(wk[m].sum()), 'today': r(ra[keep][m] @ wk[m] / wk[m].sum()), 'plan': r(rb[keep][m] @ wk[m] / wk[m].sum()),
                                         'gain': r(gk[m] @ wk[m] / wk[m].sum(), 2), 'entries_1': th(wk[m & (gk >= 1)].sum())}
    lb = line_boardings(); lns = []
    served = [set(str(lines[k]).split('|')) for k in range(len(ids))]
    for line in RER + TRANSILIEN + ('metro',):
        if line == 'metro': idx = [k for k in keep if served[k] & set(METRO)]; wt = np.array([w[k] for k in idx]); how = 'entries'
        else:
            cnt = lb.get(line, {}); idx = [k for k in keep if line in served[k]]
            wt = np.array([cnt.get(ids[k], 0.0) for k in idx]); how = 'boardings'
            if wt.sum() < 0.5 * sum(cnt.values()) or line in ('A', 'B'): wt = np.array([w[k] for k in idx]); how = 'entries'      # RATP stations of A and B have no count by line
        if not len(idx) or wt.sum() == 0: continue
        g = np.array([gain[k] for k in idx]); best = idx[int(np.argmax(g))]
        lns.append({'line': line, 'stations': len(idx), 'weight': th(wt.sum()), 'how': how, 'today': r(np.array([ra[k] for k in idx]) @ wt / wt.sum()),
                    'gain': r(g @ wt / wt.sum(), 2), 'share_1': r(wt[g >= 1].sum() / wt.sum(), 3), 'best': str(names[best]), 'best_gain': r(gain[best])})
    # ---- journeys to work
    I, J, t, ta, tb = main['_od']; d = ta - tb; home = np.array([RING[c] for c in zdep[I]])
    trips = dict(main['trips']); trips['classes'] = [{'lo': c['lo'], 'hi': c['hi'], 'commuters': th(c['commuters']), 'mean': r(c['mean_gain']), 'hours': int(round(c['commuters'] * c['mean_gain'] / 60, -1))} for c in trips['classes']]
    trips.update(commuters=th(trips['commuters']), all_in_region=th(trips['all_in_region']), base=r(trips['base']), variant=r(trips['variant']), gain=r(trips['gain'], 2),
                 hours_one_way=int(round(trips['hours_one_way'], -2)), hours_day=int(round(2 * trips['hours_one_way'], -2)),
                 over_1=th(t[d >= 1].sum()), over_5=th(t[d >= 5].sum()), over_10=th(t[d >= 10].sum()), slower=int(round(t[d <= -1].sum(), -2)), slower_mean=r(-(d * t)[d <= -1].sum() / max(t[d <= -1].sum(), 1)),
                 mean_of_gainers=r((d * t)[d >= 1].sum() / t[d >= 1].sum()), share_of_hours_over_5=r((d * t)[d >= 5].sum() / (d * t)[d >= 1].sum(), 3),
                 home={k: {'commuters': th(t[home == k].sum()), 'over_1': th(t[(home == k) & (d >= 1)].sum()), 'gain': r((d * t)[home == k].sum() / t[home == k].sum(), 2)} for k in ('paris', 'inner', 'outer')})
    top = np.argsort(-(t * np.maximum(d, 0)))
    od = [];
    for k in top:
        if d[k] < 5 or len(od) >= 12: continue
        od.append({'from': str(zn[I[k]]), 'to': str(zn[J[k]]), 'commuters': int(round(t[k], -1)), 'today': r(ta[k], 0), 'plan': r(tb[k], 0)})
    # ---- station pairs shown as examples (chosen by hand among busy relations; the minutes are the model's), and some where nothing changes
    name_pos = {p[0]: i for i, p in enumerate(st)}; D = np.where(ok, Ta - Tb, 0.0)
    def pair(a, b):
        i, j = name_pos[a], name_pos[b]
        return {'from': a, 'to': b, 'today': r(Ta[i, j], 0), 'plan': r(Tb[i, j], 0), 'saved': r(Ta[i, j], 0) - r(Tb[i, j], 0), 'share': r((Ta[i, j] - Tb[i, j]) / Ta[i, j], 3), 'entries': int(round(wk[i], -2))}
    pairs = sorted((pair(a, b) for a, b in EXAMPLES), key=lambda p: -p['saved']); same = [pair(a, b) for a, b in EXAMPLES_SAME]
    # ---- the versions side by side, each against the network before the project; and some versions against one another
    versions = []; extra = {}; mats = {'plan': Mb}
    for v in VERSIONS:
        if not os.path.exists(os.path.join(RES, v + '.npz')): continue
        c = compare(BASE, v, verbose=False); q = _summary(c, zn); q['id'] = v; versions.append(q); mats[v] = c['_m'][1]
    for key, (a, b) in EXTRA.items():
        if os.path.exists(os.path.join(RES, a + '.npz')) and os.path.exists(os.path.join(RES, b + '.npz')): extra[key] = _summary(compare(a, b, verbose=False), zn)
    pos = {s: i for i, s in enumerate(ids)}; byname = {str(names[k]): k for k in keep}
    def trio(a, b, v):                                                  # minutes before the project, with the plan, with the version v
        i, j = byname[a], byname[b]; return {'from': a, 'to': b, 'today': r(Ma[i, j], 0), 'plan': r(Mb[i, j], 0), 'var': r(mats[v][i, j], 0)}
    ex_kb = [trio(a, b, 'plan_kb_rd') for a, b in EXAMPLES_KB if a in byname and b in byname] if 'plan_kb_rd' in mats else []
    ex_c = [trio(a, b, 'variant_c') for a, b in EXAMPLES_C if a in byname and b in byname] if 'variant_c' in mats else []
    # ---- who rides through the central sections, version by version (commuters, one way in the morning)
    rid = riders_file()['versions']; tun = {}
    for v, R in rid.items(): tun[v] = {key: int(round(R[name], -2)) for key, name in SECTIONS if name in R}
    fl = os.path.join(HERE, '..', 'src', 'sections', 'flows', 'data.json'); factor = None
    if os.path.exists(fl): factor = (json.load(open(fl))['k'].get('engine') or {}).get('factor')
    day = {v: {key: th(val * factor) for key, val in R.items()} for v, R in tun.items()} if factor else {}
    # ---- the starting point: the stations, the check against a journey planner, lines 15 to 18
    T0 = load('today'); F0 = load(BASE); ent = station_entries(); kinds = collections.Counter(); nocount = []
    for sid, nm, ln in zip(T0['ids'], T0['names'], T0['lines']):
        L = set(str(ln).split('|')); kinds['metro' if L & set(METRO) else 'rer' if L & set(RER) else 'transilien' if L & set(TRANSILIEN) else 'ter'] += 1
        if ent.get(sid, 0) <= 0: nocount.append(str(nm))
    now = set(T0['ids']); gpe = json.load(open(os.path.join(NETS, 'gpe.json')))
    cover = {'stations': len(T0['ids']), 'kinds': dict(kinds), 'counted': len(T0['ids']) - len(nocount), 'not_counted': len(nocount), 'not_counted_names': sorted(nocount),
             'with_gpe': len(F0['ids']), 'gpe_new': int(sum(1 for s in F0['ids'] if s not in now)), 'gpe_stations': len(gpe['new_stops']), 'gpe_lines': [
                 {'line': l['line'], 'stops': len(l['stops']), 'minutes': r(l['stops'][-1][1], 0), 'headway': l['headway_min']} for l in gpe['new_lines']]}
    check = validate('today')
    joins = [j for j in json.loads(str(load('plan')['log'])) if 'joined' in j]
    k = {'stations': n, 'all_stations': len(ids), 'entries': th(wk.sum()), 'today': r(main['reach']['base']), 'plan': r(main['reach']['variant']), 'gain': r(main['reach']['gain'], 2),
         'gain_s': int(round(main['reach']['gain'] * 60, -1)), 'stations_05': main['reach']['stations_over']['0.5'], 'stations_1': main['reach']['stations_over']['1'], 'stations_2': main['reach']['stations_over']['2'], 'stations_5': main['reach']['stations_over']['5'],
         'entries_05': th(main['reach']['entries_over']['0.5']), 'entries_1': th(main['reach']['entries_over']['1']), 'entries_2': th(main['reach']['entries_over']['2']), 'entries_5': th(main['reach']['entries_over']['5']),
         'share_1': r(main['reach']['entries_over']['1'] / wk.sum(), 3), 'max_gain': r(main['reach']['max_gain']), 'max_at': main['reach']['max_at'],
         'pairs_total': int(ok.sum() - n), 'pairs_5': int((D >= 5).sum()), 'pairs_10': int((D >= 10).sum()), 'pairs_20': int((D >= 20).sum()), 'pairs_slower': int((D <= -1).sum()),
         'first_wait_cap': FIRST_WAIT_CAP // 60, 'step': STEP // 60, 'same_stop': SAME_STOP // 60, 'same_stop_far': SAME_STOP_FAR // 60, 'access_km': ACCESS_KM, 'access_n': ACCESS_N,
         'factor': factor, 'gpe_walk': GPE_WALK[0], 'gpe_near': GPE_NEAR_M}
    out = {'day': DAY, 'st': st, 'ring': [str(x) for x in ring], 'today': pack(qa), 'saved': pack(qg), 'k': k, 'classes': classes, 'rings': rings, 'lines': lns, 'trips': trips, 'od': od,
           'pairs': pairs, 'same': same, 'versions': versions, 'joins': joins, 'x': extra, 'tun': tun, 'day_pax': day, 'cover': cover, 'check': check, 'ex_kb': ex_kb, 'ex_c': ex_c,
           'v': {q['id']: q for q in versions}, 'ln': {q['line']: q for q in lns}, 'ex': {q['from'] + '>' + q['to']: q for q in pairs + same},
           'exv': {q['from'] + '>' + q['to']: q for q in ex_kb + ex_c}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('stations', n, 'bytes', os.path.getsize(OUT), '| tables', len(out['today']), len(out['saved']))
    print('k', k); print('rings', rings); print('trips', {a: b for a, b in trips.items() if a != 'classes'})
    for c in trips['classes']: print('  ', c)
    for l in lns: print('  ', l)
    for p_ in pairs + same: print('  ', p_)
    for o in od: print('  ', o)
    for v in versions: print('  ', {a: b for a, b in v.items() if not a.startswith('od_')})
    for key, v in extra.items(): print('  ', key, {a: b for a, b in v.items() if not a.startswith('od_')}); [print('      +', o) for o in v['od_gain']]; [print('      -', o) for o in v['od_loss']]
    for v, R in tun.items(): print('  ', v, R)
    print('  day', day.get('plan')); print('  cover', {a: b for a, b in cover.items() if a != 'not_counted_names'})
    print('  check', {a: b for a, b in check.items() if a != 'rows'})
    for q in ex_kb + ex_c: print('  ', q)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'run': run(a[1], a[a.index('--gtfs') + 1])
    elif a and a[0] == 'gpe': make_gpe(a[a.index('--gtfs') + 1])
    elif a and a[0] == 'weights': make_weights(a[a.index('--communes') + 1], a[a.index('--mobpro') + 1])
    elif a and a[0] == 'compare': compare(a[1], a[2])
    elif a and a[0] == 'riders': riders_file(a[1:])
    elif a and a[0] == 'export': export()
    elif a and a[0] == 'validate':
        v = validate(*a[1:])
        for r in v['rows']: print('%-34s %-34s planner %3d  here %5.1f  %+5.1f' % (r['from'], r['to'], r['ref'], r['model'], r['model'] - r['ref']))
        print({k: x for k, x in v.items() if k != 'rows'})
    else: print(__doc__)
