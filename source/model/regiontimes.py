#!/usr/bin/env python3
"""Travel times from every station to every other station of the Paris region, for any version of the network (chapter 'times').

A set of reusable steps. Each version of the network is a small JSON file (model/inputs/networks/*.json) that says how it differs
from the published timetable; the same commands run on any of them, and 'compare' sets two versions side by side.

    python3 model/regiontimes.py run <network.json> --gtfs <IDFM GTFS folder>      -> model/inputs/regiontimes/<name>.npz
    python3 model/regiontimes.py weights --communes <communes.json> --mobpro <mobpro_flows.csv.gz>
                                                                                    -> model/inputs/regiontimes/weights.npz
    python3 model/regiontimes.py compare <base name> <variant name>                 (prints the gains of the variant over the base)
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
def apply_network(trips, S, walks, net):
    """The timetable of a version: new platforms, their walks, and the lines joined end to end. Returns (trips, S, walks, members, log):
    members = {new stop: [stations it belongs to]}; log = what was joined."""
    S = dict(S); walks = list(walks); members = {}; log = []
    for ns in net.get('new_stops', []):
        S[ns['id']] = (ns['name'], ns['lon'], ns['lat'], ns['id']); members[ns['id']] = ns.get('member_of', [])
        for like in ns.get('like', []):
            for a, b, s in list(walks):
                if a == like: walks.append((ns['id'], b, s))
                if b == like: walks.append((a, ns['id'], s))
            w = int(ns.get('to_like_min', 5) * 60); walks += [(ns['id'], like, w), (like, ns['id'], w)]
    for a, b, m in net.get('walks', []):
        walks += [(a, b, int(m * 60)), (b, a, int(m * 60))]
    par = lambda s: S[s][3]
    for sp in net.get('through', []):
        dwell = int(sp['dwell_min'] * 60); maxw = int(sp['max_wait_min'] * 60); path = sp['path']; total = path[-1][1]
        for A, B, pth in ((sp['a'], sp['b'], path), (sp['b'], sp['a'], [[p[0], total - p[1]] for p in reversed(path)])):
            inbound = sorted((t for t in trips if t['stops'][-1][5] in A['lines'] and par(t['stops'][-1][0]) == A['terminal']), key=lambda t: t['stops'][-1][1])
            outbound = sorted((t for t in trips if t['stops'][0][5] in B['lines'] and par(t['stops'][0][0]) == B['terminal'] and not t.get('joined')), key=lambda t: t['stops'][0][2])
            ready = []
            for t in inbound:                                           # every arriving train runs on along the path
                t0 = t['stops'][-1][1]; ln = t['stops'][-1][5]
                t['stops'][-1] = [pth[0][0], t0, t0 + dwell, True, True, ln]
                for stop, minute in pth[1:]:
                    a = t0 + int(minute * 60); t['stops'].append([stop, a, a + dwell, True, True, ln])
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
                t['stops'][-1][2] = d
                t['stops'] += [list(x) for x in o['stops'][1:]]
                o['gone'] = True; done += 1
            for o in outbound:                                          # a departure with no partner starts from its own end of the path
                if not o.get('gone'):
                    s0 = o['stops'][0]; o['stops'][0] = [pth[-1][0], s0[1], s0[2], True, True, s0[5]]; o['joined'] = True
            log.append({'name': sp['name'], 'from': '+'.join(A['lines']), 'to': '+'.join(B['lines']), 'arrivals': len(inbound), 'departures': len(outbound), 'joined': done,
                        'mean_wait_min': round(sum(waits) / len(waits), 1) if waits else None})
            trips = [t for t in trips if not t.get('gone')]
    return trips, S, walks, members, log


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
            hops.append((a[2], k, nid(a[0], a[5], t['kind']), nid(b[0], b[5], t['kind']), max(b[1], a[2]), ti, a[3], b[4]))
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


def scan(net, origins, verbose=True):
    """Minutes from each station of 'origins' to every station: the average over the starting times, the first wait capped."""
    import numpy as np
    stations = sorted(net['station']); spos = {s: i for i, s in enumerate(stations)}
    taus = np.arange(T0, T1 + LOOK + 1, STEP).astype(np.int32); K = len(taus); KE = int((T1 - T0) // STEP) + 1
    hops = net['hops']; nh = len(hops); foot = net['foot']
    ntr = max(h[5] for h in hops) + 1
    out = np.full((len(origins), len(stations)), np.nan, np.float32)
    batch = max(1, 9000 // K)
    members = [np.array(net['station'][s]) for s in stations]
    for b0 in range(0, len(origins), batch):
        ob = origins[b0:b0 + batch]; R = len(ob) * K
        A = np.full((net['n'], R), BIG, np.int32); F = np.zeros((ntr, R), bool)
        for oi, o in enumerate(ob):
            sl = slice(oi * K, (oi + 1) * K)
            for i in net['station'][o]:
                A[i, sl] = np.minimum(A[i, sl], taus)
                for j, w in foot[i]: A[j, sl] = np.minimum(A[j, sl], taus + w)
        for dep, _, a, b, arr, tr, pick, drop in hops:
            f = F[tr]
            if pick: np.logical_or(f, A[a] <= dep, out=f)
            if not drop or not f.any(): continue
            new = np.where(f, np.int32(arr), np.int32(BIG))
            better = new < A[b]
            if not better.any(): continue
            np.minimum(A[b], new, out=A[b])
            for j, w in foot[b]: np.minimum(A[j], new + np.int32(w), out=A[j])
        # arrival at each station = the first of its platforms reached
        for oi, o in enumerate(ob):
            sl = slice(oi * K, (oi + 1) * K)
            arr = np.stack([A[m, sl].min(axis=0) for m in members])                                    # stations x starting times
            jour = np.where(arr < BIG, arr - taus[None, :], BIG).astype(np.float64)                   # seconds from each starting time
            best = np.full((len(stations), KE), np.inf)
            for k in range(KE):
                m1 = min(K, k + int(LOOK // STEP) + 1)
                wait = np.minimum(taus[k:m1] - taus[k], FIRST_WAIT_CAP)[None, :]
                cand = np.where(jour[:, k:m1] < BIG, jour[:, k:m1] + wait, np.inf)
                best[:, k] = cand.min(axis=1)
            ok = np.isfinite(best).all(axis=1)
            out[b0 + oi, ok] = (best[ok].mean(axis=1) / 60.0).astype(np.float32)
            out[b0 + oi, spos[o]] = 0.0
        if verbose: print(f'  scanned {min(b0 + batch, len(origins))}/{len(origins)} origins', flush=True)
    return stations, out


def run(net_file, gtfs):
    import numpy as np
    net = json.load(open(net_file)); t0 = time.time()
    trips, S, walks = load_timetable(gtfs)
    trips, S, walks, members, log = apply_network(trips, S, walks, net)
    for l in log: print('  joined', l)
    N = build(trips, S, walks, members)
    # the stations of the table: those a metro or a train serves (tram stops are used on the way, not listed)
    serves = collections.defaultdict(set); kinds = collections.defaultdict(set)
    for stop in N['lines_at']:
        for p in (members[stop] if stop in members else [S[stop][3]]):
            serves[p] |= N['lines_at'][stop]; kinds[p] |= N['kinds'][stop]
    origins = sorted(s for s in N['station'] if kinds[s] & {1, 2})
    print(f"  {len(trips)} trains, {len(N['hops'])} hops, {N['n']} platforms, {len(origins)} stations of {len(N['station'])}", flush=True)
    stations, M = scan(N, origins)
    keep = [stations.index(s) for s in origins]; M = M[:, keep]
    os.makedirs(RES, exist_ok=True); out = os.path.join(RES, net['name'] + '.npz')
    np.savez_compressed(out, minutes=np.round(M, 2).astype(np.float32), ids=np.array(origins), names=np.array([S[s][0] for s in origins]),
                        lon=np.array([S[s][1] for s in origins]), lat=np.array([S[s][2] for s in origins]),
                        lines=np.array(['|'.join(sorted(serves[s])) for s in origins]), kinds=np.array(['|'.join(str(k) for k in sorted(kinds[s])) for s in origins]),
                        log=json.dumps(log), label=net.get('label', net['name']))
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


ACCESS_N, ACCESS_KM = 5, 8.0           # a commune is tied to its five nearest stations, within 8 km


def access_min(d_km, ha):
    """Minutes on the clock from a commune to a station d km from its centre: part of the commune lives closer, so 0.6 x d plus a term
    for its size; on foot, or by a feeder bus (5 minutes of wait, 18 km/h, 3 minutes of walk) when that is quicker (ASSUMPTION, as in
    the job-access model of the study, without its weights)."""
    r = math.sqrt(ha / 100.0 / math.pi) if ha else 1.0; e = max(0.3, 0.6 * d_km + 0.25 * r)
    return min(e * 1.3 / 4.5 * 60, 5 + e * 1.3 / 18 * 60 + 3)


def make_weights(communes, mobpro):
    """The census journeys to work by public transport (INSEE, 2022), commune to commune, and the stations each commune uses."""
    import numpy as np, pandas as pd
    base = np.load(os.path.join(RES, 'today.npz')); ids = list(base['ids']); lon = base['lon']; lat = base['lat']
    C = json.load(open(communes)); Z = []; seen = set()
    for r in C['communes'] + C['paris_arrondissements']:
        if r['code'] == '75056' or r['code'] in seen or not r['code'].startswith(('75', '77', '78', '91', '92', '93', '94', '95')) or 'centre' not in r: continue
        seen.add(r['code']); Z.append((r['code'], r['nom'], r['centre']['coordinates'][0], r['centre']['coordinates'][1], r.get('surface', 0)))
    pos = {z[0]: i for i, z in enumerate(Z)}; near = np.full((len(Z), ACCESS_N), -1, np.int32); acc = np.full((len(Z), ACCESS_N), np.nan, np.float32)
    for k, (code, nom, zlon, zlat, ha) in enumerate(Z):
        d = np.array([hav(zlon, zlat, lo, la) for lo, la in zip(lon, lat)]); o = np.argsort(d)[:ACCESS_N]
        for q, j in enumerate(o):
            if d[j] <= ACCESS_KM: near[k, q] = j; acc[k, q] = access_min(float(d[j]), ha)
    df = pd.read_csv(mobpro, dtype={'COMMUNE': str, 'DCLT': str}); df = df[df.TRANS == 6]; total = float(df.SUM_IPONDI.sum())
    df['i'] = df.COMMUNE.map(pos); df['j'] = df.DCLT.map(pos); df = df.dropna(subset=['i', 'j']); df = df[df.i != df.j]
    g = df.groupby(['i', 'j']).SUM_IPONDI.sum().reset_index()
    np.savez_compressed(os.path.join(RES, 'weights.npz'), zone=np.array([z[0] for z in Z]), zname=np.array([z[1] for z in Z]), zlon=np.array([z[2] for z in Z]), zlat=np.array([z[3] for z in Z]),
                        near=near, acc=acc, near_ids=np.array(ids), i=g.i.values.astype(np.int32), j=g.j.values.astype(np.int32), t=g.SUM_IPONDI.values.astype(np.float32),
                        all_pt=np.float32(total))
    print(f'  {len(Z)} communes, {len(g)} pairs, {g.SUM_IPONDI.sum():,.0f} commuters between two communes of the region (of {total:,.0f} in the file)')


# ====================================================================== comparing two versions
CLASSES = [(-1e9, -1.0, 'slower by more than 1 min'), (-1.0, 1.0, 'within 1 min'), (1.0, 5.0, '1 to 5 min quicker'), (5.0, 10.0, '5 to 10 min quicker'),
           (10.0, 1e9, 'more than 10 min quicker')]


def load(name):
    import numpy as np
    d = np.load(os.path.join(RES, name + '.npz')); return {k: d[k] for k in d.files}


def compare(base, var, verbose=True):
    """What the version 'var' changes against 'base'. Two measures:
      reach   for each station, the average time to every other station, each weighted by the entries it has in a day; then the average
              of the stations, each weighted by its own entries;
      trips   the census journeys to work by public transport, commune to commune, each by its quickest pair of stations."""
    import numpy as np
    A, B = load(base), load(var); ids = list(A['ids']); assert ids == list(B['ids'])
    Ma, Mb = A['minutes'].astype(np.float64), B['minutes'].astype(np.float64)
    ent = station_entries(); w = np.array([ent.get(s, 0.0) for s in ids])
    ok = np.isfinite(Ma) & np.isfinite(Mb); np.fill_diagonal(ok, False)
    W = ok * w[None, :]; den = W.sum(axis=1); den[den == 0] = np.nan
    ra = (np.where(ok, Ma, 0) * W).sum(axis=1) / den; rb = (np.where(ok, Mb, 0) * W).sum(axis=1) / den; gain = ra - rb
    use = np.isfinite(gain) & (w > 0); ww = w[use]
    res = {'base': base, 'variant': var, 'label': str(B['label']), 'stations': int(use.sum()), 'entries': float(ww.sum()),
           'reach': {'base': float((ra[use] * ww).sum() / ww.sum()), 'variant': float((rb[use] * ww).sum() / ww.sum()), 'gain': float((gain[use] * ww).sum() / ww.sum()),
                     'max_gain': float(np.nanmax(gain[use])), 'max_at': str(A['names'][np.where(use)[0][np.nanargmax(gain[use])]])}}
    cuts = [0.5, 1, 2, 5]
    res['reach']['entries_over'] = {str(c): float(ww[gain[use] >= c].sum()) for c in cuts}; res['reach']['stations_over'] = {str(c): int((gain[use] >= c).sum()) for c in cuts}
    res['reach']['entries_slower'] = float(ww[gain[use] <= -0.5].sum())
    # journeys to work
    wf = os.path.join(RES, 'weights.npz')
    if os.path.exists(wf):
        Z = np.load(wf); near, acc, I, J, T = Z['near'], Z['acc'].astype(np.float64), Z['i'], Z['j'], Z['t'].astype(np.float64)
        assert list(Z['near_ids']) == ids
        def od(M):
            best = np.full(len(I), np.inf)
            for s in range(0, len(I), 20000):
                i, j = I[s:s + 20000], J[s:s + 20000]; ni, nj = near[i], near[j]
                m = M[np.maximum(ni, 0)[:, :, None], np.maximum(nj, 0)[:, None, :]] + acc[i][:, :, None] + acc[j][:, None, :]
                m = np.where((ni >= 0)[:, :, None] & (nj >= 0)[:, None, :] & np.isfinite(m), m, np.inf)
                best[s:s + 20000] = m.reshape(len(i), -1).min(axis=1)
            return best
        ta, tb = od(Ma), od(Mb); okt = np.isfinite(ta) & np.isfinite(tb); d = ta[okt] - tb[okt]; t = T[okt]
        res['trips'] = {'commuters': float(t.sum()), 'all_in_region': float(T.sum()), 'base': float((ta[okt] * t).sum() / t.sum()), 'variant': float((tb[okt] * t).sum() / t.sum()),
                        'gain': float((d * t).sum() / t.sum()), 'hours_one_way': float((d * t).sum() / 60.0),
                        'classes': [{'label': c[2], 'lo': c[0], 'hi': c[1], 'commuters': float(t[(d >= c[0]) & (d < c[1])].sum()),
                                     'mean_gain': float((d * t)[(d >= c[0]) & (d < c[1])].sum() / max(t[(d >= c[0]) & (d < c[1])].sum(), 1e-9))} for c in CLASSES]}
        res['_od'] = (I[okt], J[okt], t, ta[okt], tb[okt])
    res['_st'] = (ids, w, ra, rb, use)
    if verbose:
        r = res['reach']; print(f"{var} against {base}: {res['stations']} stations, {res['entries']:,.0f} entries a working day")
        print(f"  reach: {r['base']:.2f} -> {r['variant']:.2f} min, {r['gain']:.2f} min less on average; largest {r['max_gain']:.1f} min at {r['max_at']}")
        print('  entries at stations that gain at least', {k: f'{v:,.0f}' for k, v in r['entries_over'].items()}, '| stations', r['stations_over'], '| slower by 0.5 or more', f"{r['entries_slower']:,.0f}")
        if 'trips' in res:
            t = res['trips']; print(f"  journeys to work: {t['commuters']:,.0f} commuters, {t['base']:.2f} -> {t['variant']:.2f} min, {t['gain']:.2f} min less each; {t['hours_one_way']:,.0f} hours a morning")
            for c in t['classes']: print(f"    {c['label']:28s} {c['commuters']:>12,.0f}  (mean {c['mean_gain']:.1f} min)")
    return res


# ====================================================================== the data of the chapter
VERSIONS = ['plan_rer_f', 'plan_rer_g', 'plan_ter', 'plan_g_no_chatelet', 'plan']      # the versions set side by side in the chapter, the plan last
GAIN_CLASSES = [(-1e9, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 1e9)]           # minutes saved on average from a station to the rest of the network
RER = ('A', 'B', 'C', 'D', 'E'); TRANSILIEN = ('H', 'J', 'K', 'L', 'N', 'P', 'R', 'U', 'V')
EXAMPLES = [('Clamart', 'Châtelet - Les Halles'), ('Vanves - Malakoff', "Gare de l'Est"), ('Versailles Chantiers', "Gare de l'Est"), ('Rambouillet', 'Gare du Nord'),
            ('Saint-Quentin en Yvelines - Montigny-le-Bretonneux', "Gare de l'Est"), ('Clichy - Levallois', "Gare de l'Est"), ('Meaux', 'Gare Montparnasse'),
            ('Chelles - Gournay', 'Gare Montparnasse'), ('Épinay - Villetaneuse', 'Gare Saint-Lazare'), ('Bécon les Bruyères', 'Gare du Nord'), ('Enghien-les-Bains', 'Gare Saint-Lazare'),
            ('Mitry - Claye', 'Gare Saint-Lazare'), ('Lagny - Thorigny', 'Châtelet - Les Halles'), ('Sarcelles - Saint-Brice', 'Gare Saint-Lazare'), ('Saint-Denis', 'Asnières-sur-Seine'),
            ('Gare du Nord', 'Gare Saint-Lazare'), ("Gare de l'Est", 'Gare Montparnasse')]
EXAMPLES_SAME = [('La Défense', 'Gare du Nord'), ('Cergy Préfecture', 'Gare du Nord'), ('Pontoise', 'Gare Montparnasse')]
METRO = ('1', '2', '3', '3B', '4', '5', '6', '7', '7B', '8', '9', '10', '11', '12', '13', '14')
RING = {'75': 'paris', '92': 'inner', '93': 'inner', '94': 'inner', '77': 'outer', '78': 'outer', '91': 'outer', '95': 'outer'}


def export():
    import numpy as np, base64, gzip
    r = lambda x, n=1: round(float(x), n)
    th = lambda x: int(round(float(x), -3))
    main = compare('today', 'plan', verbose=False)
    ids, w, ra, rb, use = main['_st']; A, B = load('today'), load('plan')
    Ma, Mb = A['minutes'].astype(np.float64), B['minutes'].astype(np.float64)
    keep = np.where(use)[0]; n = len(keep); gain = ra - rb
    x = (A['lon'] - NOTRE_DAME[0]) * math.cos(math.radians(NOTRE_DAME[1])) * 111.32; y = (A['lat'] - NOTRE_DAME[1]) * 110.57
    Z = np.load(os.path.join(RES, 'weights.npz')); zdep = np.array([c[:2] for c in Z['zone']])
    ring = []
    for k in keep:                                                      # the departement of a station: that of the nearest commune centre
        d = (Z['zlon'] - A['lon'][k]) ** 2 * math.cos(math.radians(48.85)) ** 2 + (Z['zlat'] - A['lat'][k]) ** 2; ring.append(RING[zdep[int(np.argmin(d))]])
    ring = np.array(ring)
    order = np.argsort(-w[keep]); keep = keep[order]; ring = ring[order]                         # busiest first: the names shown first on the map
    st = [[str(A['names'][k]), r(x[k], 2), r(y[k], 2), str(A['lines'][k]), int(round(w[k])), r(ra[k], 2), r(rb[k], 2)] for k in keep]
    # the two tables of minutes, half a minute a step, one byte each: today, and what the plan saves (127 = no change, below = slower)
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
    lb = line_boardings(); pos = {s: i for i, s in enumerate(ids)}; lines = []
    served = [set(str(A['lines'][k]).split('|')) for k in range(len(ids))]
    for line in RER + TRANSILIEN + ('metro',):
        if line == 'metro': idx = [k for k in keep if served[k] & set(METRO)]; wt = np.array([w[k] for k in idx]); how = 'entries'
        else:
            cnt = lb.get(line, {}); idx = [k for k in keep if line in served[k]]
            wt = np.array([cnt.get(ids[k], 0.0) for k in idx]); how = 'boardings'
            if wt.sum() < 0.5 * sum(cnt.values()) or line in ('A', 'B'): wt = np.array([w[k] for k in idx]); how = 'entries'      # RATP stations of A and B have no count by line
        if not len(idx) or wt.sum() == 0: continue
        g = np.array([gain[k] for k in idx]); best = idx[int(np.argmax(g))]
        lines.append({'line': line, 'stations': len(idx), 'weight': th(wt.sum()), 'how': how, 'today': r(np.array([ra[k] for k in idx]) @ wt / wt.sum()),
                      'gain': r(g @ wt / wt.sum(), 2), 'share_1': r(wt[g >= 1].sum() / wt.sum(), 3), 'best': str(A['names'][best]), 'best_gain': r(gain[best])})
    # ---- journeys to work
    I, J, t, ta, tb = main['_od']; d = ta - tb; home = np.array([RING[c] for c in zdep[I]])
    trips = dict(main['trips']); trips['classes'] = [{'lo': c['lo'], 'hi': c['hi'], 'commuters': th(c['commuters']), 'mean': r(c['mean_gain']), 'hours': int(round(c['commuters'] * c['mean_gain'] / 60, -1))} for c in trips['classes']]
    trips.update(commuters=th(trips['commuters']), all_in_region=th(trips['all_in_region']), base=r(trips['base']), variant=r(trips['variant']), gain=r(trips['gain'], 2),
                 hours_one_way=int(round(trips['hours_one_way'], -2)), hours_day=int(round(2 * trips['hours_one_way'], -2)),
                 over_1=th(t[d >= 1].sum()), over_5=th(t[d >= 5].sum()), over_10=th(t[d >= 10].sum()), slower=th(t[d <= -1].sum()), slower_mean=r(-(d * t)[d <= -1].sum() / max(t[d <= -1].sum(), 1)),
                 mean_of_gainers=r((d * t)[d >= 1].sum() / t[d >= 1].sum()), share_of_hours_over_5=r((d * t)[d >= 5].sum() / (d * t)[d >= 1].sum(), 3),
                 home={k: {'commuters': th(t[home == k].sum()), 'over_1': th(t[(home == k) & (d >= 1)].sum()), 'gain': r((d * t)[home == k].sum() / t[home == k].sum(), 2)} for k in ('paris', 'inner', 'outer')})
    zn = Z['zname']; top = np.argsort(-(t * np.maximum(d, 0)))
    od = [];
    for k in top:
        if d[k] < 5 or len(od) >= 12: continue
        od.append({'from': str(zn[I[k]]), 'to': str(zn[J[k]]), 'commuters': int(round(t[k], -1)), 'today': r(ta[k], 0), 'plan': r(tb[k], 0)})
    # ---- station pairs shown as examples (chosen by hand among busy relations; the minutes are the model's), and two where nothing changes
    name_pos = {p[0]: i for i, p in enumerate(st)}; D = np.where(ok, Ta - Tb, 0.0)
    def pair(a, b):
        i, j = name_pos[a], name_pos[b]
        return {'from': a, 'to': b, 'today': r(Ta[i, j], 0), 'plan': r(Tb[i, j], 0), 'saved': r(Ta[i, j], 0) - r(Tb[i, j], 0), 'share': r((Ta[i, j] - Tb[i, j]) / Ta[i, j], 3), 'entries': int(round(wk[i], -2))}
    pairs = sorted((pair(a, b) for a, b in EXAMPLES), key=lambda p: -p['saved']); same = [pair(a, b) for a, b in EXAMPLES_SAME]
    # ---- the versions side by side
    versions = []
    for v in VERSIONS:
        if not os.path.exists(os.path.join(RES, v + '.npz')): continue
        c = compare('today', v, verbose=False); I2, J2, t2, a2, b2 = c['_od']; d2 = a2 - b2
        versions.append({'id': v, 'label': c['label'], 'gain': r(c['reach']['gain'], 2), 'stations_1': c['reach']['stations_over']['1'], 'entries_1': th(c['reach']['entries_over']['1']),
                         'entries_2': th(c['reach']['entries_over']['2']), 'entries_5': th(c['reach']['entries_over']['5']), 'commuters_1': th(t2[d2 >= 1].sum()), 'commuters_5': th(t2[d2 >= 5].sum()),
                         'slower': th(t2[d2 <= -1].sum()), 'hours_day': int(round(2 * c['trips']['hours_one_way'], -2)), 'max_gain': r(c['reach']['max_gain']), 'max_at': c['reach']['max_at']})
    joins = json.loads(str(B['log']))
    k = {'stations': n, 'all_stations': len(ids), 'entries': th(wk.sum()), 'today': r(main['reach']['base']), 'plan': r(main['reach']['variant']), 'gain': r(main['reach']['gain'], 2),
         'gain_s': int(round(main['reach']['gain'] * 60, -1)), 'stations_05': main['reach']['stations_over']['0.5'], 'stations_1': main['reach']['stations_over']['1'], 'stations_2': main['reach']['stations_over']['2'], 'stations_5': main['reach']['stations_over']['5'],
         'entries_05': th(main['reach']['entries_over']['0.5']), 'entries_1': th(main['reach']['entries_over']['1']), 'entries_2': th(main['reach']['entries_over']['2']), 'entries_5': th(main['reach']['entries_over']['5']),
         'share_1': r(main['reach']['entries_over']['1'] / wk.sum(), 3), 'max_gain': r(main['reach']['max_gain']), 'max_at': main['reach']['max_at'],
         'pairs_total': int(ok.sum() - n), 'pairs_5': int((D >= 5).sum()), 'pairs_10': int((D >= 10).sum()), 'pairs_20': int((D >= 20).sum()), 'pairs_slower': int((D <= -1).sum()),
         'first_wait_cap': FIRST_WAIT_CAP // 60, 'step': STEP // 60, 'same_stop': SAME_STOP // 60, 'same_stop_far': SAME_STOP_FAR // 60, 'access_km': ACCESS_KM, 'access_n': ACCESS_N}
    out = {'day': DAY, 'st': st, 'ring': [str(x) for x in ring], 'today': pack(qa), 'saved': pack(qg), 'k': k, 'classes': classes, 'rings': rings, 'lines': lines, 'trips': trips, 'od': od,
           'pairs': pairs, 'same': same, 'versions': versions, 'joins': joins,
           'v': {x['id']: x for x in versions}, 'ln': {x['line']: x for x in lines}, 'ex': {x['from'] + '>' + x['to']: x for x in pairs + same}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('stations', n, 'bytes', os.path.getsize(OUT), '| tables', len(out['today']), len(out['saved']))
    print('k', k); print('rings', rings); print('trips', {a: b for a, b in trips.items() if a != 'classes'})
    for c in trips['classes']: print('  ', c)
    for l in lines: print('  ', l)
    for p_ in pairs + same: print('  ', p_)
    for o in od: print('  ', o)
    for v in versions: print('  ', v)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'run': run(a[1], a[a.index('--gtfs') + 1])
    elif a and a[0] == 'weights': make_weights(a[a.index('--communes') + 1], a[a.index('--mobpro') + 1])
    elif a and a[0] == 'compare': compare(a[1], a[2])
    elif a and a[0] == 'export': export()
    else: print(__doc__)
