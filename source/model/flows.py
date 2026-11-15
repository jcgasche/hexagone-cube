#!/usr/bin/env python3
"""Passengers and trains on every rail line of the Paris region, section by section, today and with the plan (chapter 'flows').

    python3 model/flows.py <IDFM GTFS folder> <communes.json> <mobpro_flows.csv.gz>   -> model/inputs/flows_network.json
    python3 model/flows.py                                                            -> src/sections/flows/data.json

Step 1 (needs pandas and scipy, and the three inputs) reads the Ile-de-France Mobilites timetable (GTFS) of one Tuesday and builds:
  - the rail graph: stations joined where a train runs from one to the next without passing another station (links that only express
    trains make are folded onto the stations they pass);
  - on each link and for each line, the trains that run in a day and in the busiest 60 minutes, each way (a count, nothing assumed);
  - for each line, who rides from which station to which: the census journeys to work by public transport (INSEE, 2022, commune to
    commune) each put on its quickest route through the timetable network, metro and tram included;
  - the fit to the counts: each station of a line gets a factor, so that the boardings at the station equal the boardings counted
    there (SNCF counts aboard Transilien trains; IDFM validations at the stations of the RATP that one line serves). Stations without
    a count share one factor, set so that the line carries its published total (inputs/flows_published.json) or, failing that, the
    median factor of the line. The passengers on a link are then those of all the station pairs whose ride passes over it.
Step 2 (plain python) adds the TER and the TGV from published totals, the plan's tunnels from the study's own model, the places on
the trains and the capacity of the sections for which one is published, and writes the data of the map.

What is measured, derived and missing is carried with every figure (field 'q'): 'count' a count on the timetable, 'published' a
published figure, 'model' the commuter model scaled to a published line total, 'split' a published total shared out by trains,
'none' no figure found. Everything marked ASSUMPTION is a judgement."""
import json, os, sys, math, heapq, collections, csv, io, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
NET = os.path.join(HERE, 'inputs', 'flows_network.json')
PUB = os.path.join(HERE, 'inputs', 'flows_published.json')
OUT = os.path.join(HERE, '..', 'src', 'sections', 'flows', 'data.json')

DAY = '20261103'                       # the Tuesday read from the timetable
TERMINALS = {'IDFM:71410': 'Nord', 'IDFM:71359': 'Est', 'IDFM:73626': 'Lyon', 'IDFM:71607': 'Bercy', 'IDFM:71135': 'Austerlitz', 'IDFM:71139': 'Montparnasse', 'IDFM:71370': 'Saint-Lazare'}
RAIL = ('A', 'B', 'C', 'D', 'E', 'H', 'J', 'K', 'L', 'N', 'P', 'R', 'U', 'V') + tuple('TER ' + t for t in TERMINALS.values()) + ('TER other',)     # lines drawn (route type 2 of the file)
WAIT_W, WALK_W, WAIT_CAP, PEN = 1.5, 2.0, 15.0, 10.0      # weights of waiting and walking (DGITM), longest wait counted, minutes a change costs (as in the job-access model)
T0, T1 = 7 * 3600, 9 * 3600            # the two hours that give the interval between trains and the riding times
DETOUR = 1.25                          # a link is folded onto intermediate stations when that path is at most this much longer (ASSUMPTION)
RAW = os.path.join(HERE, 'inputs', 'traffic', 'raw')        # open data as downloaded (README.md there lists each file, its portal and its date)
# station names of the SNCF count that differ from the timetable's
ALIAS = {'AEROPORT-CHARLES-DE-GAULLE-1-(TERMINAL-3)': 'Aéroport CDG 1 (Terminal 3)', 'AEROPORT-CHARLES-DE-GAULLE-2-(TERMINAL-2)': 'Aéroport CDG (Terminal 2) - TGV',
         'BELLEVUE': 'Gare de Bellevue', 'PARIS-AUSTERLITZ': "Gare d'Austerlitz", 'PARIS-EST': "Gare de l'Est", 'PARIS-GARE-DE-LYON': 'Gare de Lyon', 'PARIS-GARE-DU-NORD': 'Gare du Nord',
         'PARIS-MONTPARNASSE': 'Gare Montparnasse', 'PARIS-SAINT-LAZARE': 'Gare Saint-Lazare', "PONT-DE-RUNGIS-AEROPORT-D'ORLY": 'Thiais - Orly (Pont de Rungis)'}
# networks of the IDFM validation files whose entries stand for boardings where the SNCF count has none: the RATP parts of RER A and B, and RER E
VALID = {('810', '801'): 'A', ('810', '802'): 'B', ('800', '805'): 'E'}
VALID.update({('800', '803'): 'C', ('800', '804'): 'D', ('800', '850'): 'P', ('800', '851'): 'R', ('800', '852'): 'N', ('800', '853'): 'H', ('800', '854'): 'L'})
PROFILE_AS = {'U': 'N', 'V': 'C', 'K': 'H', 'J': 'L'}       # lines whose hourly profile is read on the network they share validators with


def hav(lon1, lat1, lon2, lat2):
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


# ====================================================================== step 1: the timetable and the census
def step1(gtfs, communes, mobpro):
    import numpy as np, pandas as pd
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    tsec = lambda x: int(x[:-6]) * 3600 + int(x[-5:-3]) * 60 + int(x[-2:])
    stops = pd.read_csv(f'{gtfs}/stops.txt', dtype=str); routes = pd.read_csv(f'{gtfs}/routes.txt', dtype=str)
    trips = pd.read_csv(f'{gtfs}/trips.txt', dtype=str); cal = pd.read_csv(f'{gtfs}/calendar.txt', dtype=str); cd = pd.read_csv(f'{gtfs}/calendar_dates.txt', dtype=str)
    act = set(cal[(cal.tuesday == '1') & (cal.start_date <= DAY) & (cal.end_date >= DAY)].service_id)
    act |= set(cd[(cd.date == DAY) & (cd.exception_type == '1')].service_id); act -= set(cd[(cd.date == DAY) & (cd.exception_type == '2')].service_id)
    trips = trips[trips.service_id.isin(act)].merge(routes[['route_id', 'route_short_name', 'route_long_name', 'route_type']], on='route_id')
    trips['line'] = trips.route_short_name
    st = pd.read_csv(f'{gtfs}/stop_times.txt', dtype=str, usecols=['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence'])
    st = st[st.trip_id.isin(set(trips.trip_id))].copy()
    st['dep'] = st.departure_time.map(tsec); st['seq'] = st.stop_sequence.astype(int)
    parent = stops.set_index('stop_id').parent_station
    st['stn'] = st.stop_id.map(lambda s: parent.get(s) if isinstance(parent.get(s), str) else s)
    st = st.merge(trips[['trip_id', 'line', 'direction_id', 'route_type', 'route_long_name']], on='trip_id').sort_values(['trip_id', 'seq'])
    ter = st[st.line == 'TER']                                         # a TER train takes the name of the Paris terminal it serves
    at = ter[ter.stn.isin(TERMINALS)].groupby('trip_id').stn.first().map(TERMINALS)
    st['line'] = np.where(st.line == 'TER', 'TER ' + st.trip_id.map(at).fillna('other'), st.line)
    stn = stops[stops.location_type == '1'].set_index('stop_id')[['stop_name', 'stop_lon', 'stop_lat']]
    lone = stops[(stops.location_type == '0') & stops.parent_station.isna()].set_index('stop_id')[['stop_name', 'stop_lon', 'stop_lat']]
    stn = pd.concat([stn, lone]).astype({'stop_lon': float, 'stop_lat': float})
    stn = stn[~stn.index.duplicated()]
    name = stn.stop_name.to_dict(); lon = stn.stop_lon.to_dict(); lat = stn.stop_lat.to_dict()
    dist = lambda a, b: hav(lon[a], lat[a], lon[b], lat[b])

    # ---- the rail graph: consecutive stops of every rail train of the day, then express links folded onto the stations they pass
    rail = st[st.route_type == '2']
    nxt = rail.groupby('trip_id').shift(-1)
    hop = pd.DataFrame({'trip': rail.trip_id, 'line': rail.line, 'dir': rail.direction_id, 'a': rail.stn, 'b': nxt.stn, 'dep': rail.dep}).dropna()
    hop = hop[hop.a != hop.b]
    und = lambda a, b: (a, b) if a < b else (b, a)
    raw = {und(a, b) for a, b in zip(hop.a, hop.b)}
    adj = collections.defaultdict(dict)
    for a, b in raw: adj[a][b] = adj[b][a] = dist(a, b)

    def path(a, b, cut=None, skip=None):
        """Shortest path a to b on the rail graph by length; `skip` an edge left out; None if longer than `cut`."""
        best = {a: 0.0}; prev = {}; pq = [(0.0, a)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == b: break
            if d > best.get(u, 1e18): continue
            for v, w in adj[u].items():
                if skip and und(u, v) == skip: continue
                nd = d + w
                if cut is not None and nd > cut: continue
                if nd < best.get(v, 1e18): best[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
        if b not in best: return None
        out = [b]
        while out[-1] != a: out.append(prev[out[-1]])
        return out[::-1]

    for a, b in sorted(raw, key=lambda e: -dist(*e)):           # longest first: drop a link that a chain of shorter links replaces
        d = adj[a][b]
        if path(a, b, cut=d * DETOUR + 0.3, skip=(a, b)) is not None:
            del adj[a][b]; del adj[b][a]
    edges = sorted({und(a, b) for a in adj for b in adj[a]}); eid = {e: i for i, e in enumerate(edges)}
    memo = {}
    def chain(a, b):
        if (a, b) not in memo:
            p = path(a, b); memo[(a, b)] = [(eid[und(u, v)], 0 if u < v else 1) for u, v in zip(p, p[1:])]
        return memo[(a, b)]

    # ---- trains: each hop of each train put on the links it runs over
    trains = collections.defaultdict(lambda: [0, 0]); bins = collections.defaultdict(lambda: np.zeros(24 * 12 + 60, int))
    for line, d, a, b, dep in zip(hop.line, hop.dir, hop.a, hop.b, hop.dep):
        for e, way in chain(a, b):
            trains[(line, e)][way] += 1; bins[(line, e, way)][min(int(dep // 300), 24 * 12 + 59)] += 1
    peak = {}
    for (line, e, way), v in bins.items():
        peak[(line, e, way)] = int(np.convolve(v, np.ones(12, int)).max())
    # all lines together on a link, each way, in its busiest 60 minutes (not the sum of each line's own peak)
    tot = collections.defaultdict(lambda: np.zeros(24 * 12 + 60, int))
    for (line, e, way), v in bins.items(): tot[(e, way)] += v
    peak_all = {k: int(np.convolve(v, np.ones(12, int)).max()) for k, v in tot.items()}

    # ---- the network a traveller sees: stations, one node per (line, station), riding, waiting, walking (as model job access)
    st2 = st.sort_values(['trip_id', 'seq'])
    win = st2[(st2.dep >= T0 - 3600) & (st2.dep <= T1)]; nx = win.groupby('trip_id').shift(-1)
    seg = pd.DataFrame({'line': win.line, 'a': win.stn, 'b': nx.stn, 'tt': (nx.dep - win.dep) / 60.0}).dropna()
    seg = seg[(seg.a != seg.b) & (seg.tt >= 0)]
    ride = seg.groupby(['line', 'a', 'b']).tt.median().reset_index(); ride['tt'] = ride.tt.clip(lower=0.5)
    depw = st2[(st2.dep >= T0) & (st2.dep < T1)]
    nd = depw.groupby(['stn', 'line', 'direction_id']).size().reset_index(name='n').groupby(['stn', 'line']).n.max().reset_index()
    hw = {(r.stn, r.line): 120.0 / r.n for r in nd.itertuples()}
    sid = list(stn.index); idx = {s: i for i, s in enumerate(sid)}
    ln = sorted(set(zip(ride.line, ride.a)) | set(zip(ride.line, ride.b))); lidx = {k: len(sid) + i for i, k in enumerate(ln)}
    nlines = collections.Counter(s for _, s in ln)
    intra = lambda n: 1.0 if n <= 1 else (2.0 if n <= 3 else 4.0)

    def graph():
        rows, cols, w, kind = [], [], [], {}
        def add(a, b, c, k=None):
            rows.append(a); cols.append(b); w.append(max(c, 1e-6))
            if k: kind[(a, b)] = k
        for (line, s) in ln:
            if s not in idx: continue
            add(idx[s], lidx[(line, s)], WAIT_W * min(hw.get((s, line), 60.0) / 2.0, WAIT_CAP) + PEN, ('board', line, s))
            add(lidx[(line, s)], idx[s], WALK_W * intra(nlines[s]))
        for r in ride.itertuples():
            if (r.line, r.a) in lidx and (r.line, r.b) in lidx: add(lidx[(r.line, r.a)], lidx[(r.line, r.b)], r.tt, ('ride', r.line, r.a, r.b))
        tr = pd.read_csv(f'{gtfs}/transfers.txt', dtype=str); P = lambda s: parent.get(s) if isinstance(parent.get(s), str) else s
        seen = set()
        for r in tr.itertuples():
            a, b = P(r.from_stop_id), P(r.to_stop_id)
            if a != b and a in idx and b in idx and (a, b) not in seen: seen.add((a, b)); add(idx[a], idx[b], WALK_W * float(r.min_transfer_time or 120) / 60.0)
        lo = stn.stop_lon.values; la = stn.stop_lat.values
        for i in range(len(sid)):
            d = 2 * 6371.0 * np.arcsin(np.sqrt(np.sin((la - la[i]) * math.pi / 360) ** 2 + math.cos(la[i] * math.pi / 180) * np.cos(la * math.pi / 180) * np.sin((lo - lo[i]) * math.pi / 360) ** 2))
            for j in np.where((d < 0.4) & (d > 0))[0]:
                if (sid[i], sid[j]) not in seen: add(i, j, WALK_W * (2 + d[j] * 1.3 / 4.5 * 60))
        return rows, cols, w, kind

    # ---- zones (communes, Paris arrondissements) and the census journeys to work by public transport
    C = json.load(open(communes)); Z = []
    for r in C['communes'] + C['paris_arrondissements']:
        if r['code'] == '75056' or not r['code'].startswith(('75', '77', '78', '91', '92', '93', '94', '95', '60')) or 'centre' not in r: continue
        Z.append((r['code'], r['centre']['coordinates'][0], r['centre']['coordinates'][1], r.get('surface', 0)))
    seen_z = set(); Z = [z for z in Z if not (z[0] in seen_z or seen_z.add(z[0]))]
    pos = {z[0]: i for i, z in enumerate(Z)}; nz = len(Z)
    df = pd.read_csv(mobpro, dtype={'COMMUNE': str, 'DCLT': str}); df = df[df.TRANS == 6]
    df['i'] = df.COMMUNE.map(pos); df['j'] = df.DCLT.map(pos); df = df.dropna(subset=['i', 'j'])
    T = np.zeros((nz, nz)); np.add.at(T, (df.i.astype(int).values, df.j.astype(int).values), df.SUM_IPONDI.values)
    np.fill_diagonal(T, 0.0)
    served = np.zeros(len(sid), bool)
    for (l, s) in lidx:
        if s in idx: served[idx[s]] = True
    railst = np.zeros(len(sid), bool)
    for (l, s) in lidx:
        if s in idx and l in RAIL: railst[idx[s]] = True
    lo = stn.stop_lon.values; la = stn.stop_lat.values

    def access(d_km, ha):
        r = math.sqrt(ha / 100.0 / math.pi) if ha else 1.0; e = max(0.3, 0.6 * d_km + 0.25 * r)
        return min(WALK_W * e * 1.3 / 4.5 * 60, WAIT_W * 5 + e * 1.3 / 18 * 60 + WALK_W * 3)

    # ---- every commuter on the quickest route; for each rail line, who boards where and gets off where, and by which hops
    rows, cols, w, kind = graph(); n0 = len(sid) + len(ln)
    for k, (code, zlon, zlat, ha) in enumerate(Z):
        d = 2 * 6371.0 * np.arcsin(np.sqrt(np.sin((la - zlat) * math.pi / 360) ** 2 + math.cos(zlat * math.pi / 180) * np.cos(la * math.pi / 180) * np.sin((lo - zlon) * math.pi / 360) ** 2))
        d[~served] = 1e9; dr = np.where(railst, d, 1e9)
        for j in set(np.argsort(d)[:6]) | set(np.argsort(dr)[:5]):          # the six nearest stops of any kind, and the five nearest railway stations
            if d[j] > 8: continue
            c = access(d[j], ha); rows += [n0 + k, j]; cols += [j, n0 + nz + k]; w += [c, c]
    N = n0 + 2 * nz
    A = csr_matrix((w, (rows, cols)), shape=(N, N))
    od = collections.defaultdict(lambda: collections.defaultdict(float)); hops = collections.defaultdict(dict); placed = 0.0
    for o in range(nz):
        if T[o].sum() == 0: continue
        D, pred = dijkstra(A, directed=True, indices=n0 + o, return_predecessors=True)
        for dz in np.where(T[o] > 0)[0]:
            v = n0 + nz + dz
            if not np.isfinite(D[v]): continue
            x = T[o, dz]; placed += x; seq = [v]
            while pred[seq[-1]] >= 0: seq.append(pred[seq[-1]])
            seq.reverse()
            # cut the route into rides: (line, boarding station, alighting station, hops between consecutive stops)
            segs = []; cur = None
            for a, b in zip(seq, seq[1:]):
                k = kind.get((a, b))
                if not k: continue
                if k[0] == 'board':
                    if cur and cur[3]: segs.append(cur)
                    cur = [k[1], k[2], k[2], []]
                elif cur is not None:
                    cur[3].append((k[2], k[3])); cur[2] = k[3]
            if cur and cur[3]: segs.append(cur)
            for line, a, b, hp in segs:
                if line in RAIL and a != b:
                    od[line][(a, b)] += x; hops[line].setdefault((a, b), hp)

    # ---- counts of boardings: SNCF counts on Transilien trains, by line and station; IDFM validations where the SNCF does not count
    norm = lambda s: re.sub(r'[^a-z0-9]+', ' ', unicodedata.normalize('NFD', s.lower()).encode('ascii', 'ignore').decode()).strip()
    def rd(f): return list(csv.DictReader(io.open(os.path.join(RAW, f), encoding='utf-8-sig'), delimiter=';'))
    line_st = collections.defaultdict(set)
    for (l, s) in ln: line_st[l].add(s)
    byname = collections.defaultdict(dict)
    for l in RAIL:
        for s in line_st[l]:
            if s in name: byname[l][norm(name[s])] = s
    allname = {norm(name[s]): s for l in RAIL for s in line_st[l] if s in name}
    counts = collections.defaultdict(dict); unmatched = collections.defaultdict(float); lost = collections.defaultdict(list)
    tmp = collections.defaultdict(lambda: [0.0, '0'])
    for r in rd('sncf_comptage-voyageurs-trains-transilien.csv'):
        if r['type_jour'] != 'JOB': continue
        line = 'V' if r['axe'] == 'V' and 'V' in line_st else r['ligne']
        t = tmp[(line, r['nom_gare'])]; t[0] += float(r['somme_de_montants'] or 0); t[1] = max(t[1], r['annee'])
    for (line, nm), (x, yr) in tmp.items():
        n = norm(ALIAS.get(nm, nm)); s = byname[line].get(n) or (allname.get(n) if n in allname and allname[n] in line_st[line] else None)
        if s is None and line == 'V': line = 'C'; s = byname['C'].get(n)
        if s is None: unmatched[line] += x; lost[line].append([nm, round(x)]); continue
        c = counts[line].setdefault(s, {'n': 0.0, 'src': 'sncf', 'year': yr}); c['n'] += x; c['year'] = max(c['year'], yr)
    nall = collections.Counter(s for _, s in ln)                      # lines of every kind at a station, metro and tram included
    for r in rd('idfm_validations_ferre_par_station.csv'):
        line = VALID.get((r['code_stif_trns'], r['code_stif_res'])); s = 'IDFM:' + r['id_zdc']
        if not line or s not in line_st[line] or s in counts[line] or nall[s] != 1: continue      # entries from the street only: kept where one line serves the station
        try: x = float(r['nb_vald_12m_lun_ven']) / float(r['nb_jours_12m_lun_ven'])
        except (ValueError, ZeroDivisionError): continue
        if float(r['nb_jours_12m_lun_ven']) < 200: continue
        counts[line][s] = {'n': x, 'src': 'idfm', 'year': '2026'}
    # share of a day's entries made in the busiest morning hour, by network (IDFM hourly profiles, working days outside school holidays)
    wk = {}
    for r in rd('idfm_validations_ferre_par_station.csv'):
        try: wk[(r['code_stif_trns'], r['code_stif_res'], r['code_stif_arret'])] = float(r['nb_vald_12m_lun_ven']) / float(r['nb_jours_12m_lun_ven'])
        except (ValueError, ZeroDivisionError): pass
    prof = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in rd('idfm_validations-reseau-ferre-profils-horaires-par-jour-type-2eme-trimestre.csv'):
        if r['cat_jour'] != 'JOHV': continue
        k = (r['code_stif_trns'].split('.')[0], r['code_stif_res'], r['code_stif_arret'])
        if k in wk: prof[VALID.get(k[:2])][r['trnc_horr_60']] += wk[k] * float(r['pourcentage_validations'] or 0) / 100
    peak_share = {}
    for l, d in prof.items():
        if l: peak_share[l] = max(d.get(h, 0.0) for h in ('6H-7H', '7H-8H', '8H-9H', '9H-10H')) / sum(d.values())
    for l, src in PROFILE_AS.items(): peak_share[l] = peak_share[src]

    # ---- each line fitted to its counts: station factors f so that boardings f_a * sum_b f_b * (od[a,b] + od[b,a]) equal the count
    pub = json.load(open(PUB))['lines'] if os.path.exists(PUB) else {}
    out = {'day': DAY, 'stations': {}, 'edges': [], 'lines': {}, 'commuters': float(T.sum()), 'placed': placed, 'peak_share': peak_share}
    used = set()
    for line in RAIL:
        if not any(l == line for (l, e) in trains): continue
        S = sorted({s for p in od[line] for s in p}); si = {s: i for i, s in enumerate(S)}; n = len(S)
        M = np.zeros((n, n))
        for (a, b), x in od[line].items(): M[si[a], si[b]] += x
        Ms = M + M.T
        tgt = np.array([counts[line].get(s, {}).get('n', np.nan) for s in S]); meas = np.isfinite(tgt) & (Ms.sum(1) > 0)
        total = pub.get(line, {}).get('day'); f = np.ones(n)
        if meas.any():
            f[:] = math.sqrt(tgt[meas].sum() / max(1e-9, Ms[meas].sum()))
            for it in range(400):
                r = f * (Ms @ f)
                f[meas] *= np.sqrt(tgt[meas] / np.maximum(r[meas], 1e-9))
                if (~meas).any():
                    if total and total > tgt[meas].sum():
                        r = f * (Ms @ f); ru = r[~meas].sum()
                        if ru > 0: f[~meas] *= math.sqrt(min(4.0, max(0.25, (total - tgt[meas].sum()) / ru)))
                    else: f[~meas] = np.median(f[meas])
        elif total and n: f[:] = math.sqrt(total / Ms.sum())
        fit = f * (Ms @ f)
        L = {'edges': {}, 'stations': {}, 'fitted': bool(meas.any() or total), 'count_total': float(np.nansum(tgt)) if meas.any() else None,
             'count_unplaced': float(sum(c['n'] for s, c in counts[line].items() if s not in si or Ms[si[s]].sum() == 0)) + unmatched.get(line, 0.0),
             'unplaced': lost[line] + [[name[s], round(c['n'])] for s, c in counts[line].items() if s not in si or Ms[si[s]].sum() == 0],
             'model_total': float(Ms.sum()), 'fit_total': float(fit.sum()), 'published': total}
        am = collections.defaultdict(lambda: [0.0, 0.0])
        for (a, b), x in od[line].items():
            y = x * f[si[a]] * f[si[b]]
            for (u, v) in hops[line][(a, b)]:
                for e, way in chain(u, v): am[e][way] += y
        for (l, e), tr2 in trains.items():
            if l != line: continue
            a0, a1 = am.get(e, [0.0, 0.0])
            L['edges'][e] = {'day': tr2, 'peak': [peak.get((l, e, 0), 0), peak.get((l, e, 1), 0)], 'pax': round(2 * (a0 + a1), 1), 'am': round(a0 / (a0 + a1), 3) if a0 + a1 > 0 else None}
            used.update(edges[e])
        for s in S:
            c = counts[line].get(s)
            L['stations'][s] = {'count': round(c['n']) if c else None, 'src': c['src'] if c else None, 'year': c['year'] if c else None,
                                'model': round(float(Ms[si[s]].sum()), 1), 'fit': round(float(fit[si[s]]), 1)}
        out['lines'][line] = L
    out['edges'] = [[a, b, round(dist(a, b), 3), peak_all.get((i, 0), 0), peak_all.get((i, 1), 0)] for i, (a, b) in enumerate(edges)]
    out['stations'] = {s: [name[s], round(lon[s], 5), round(lat[s], 5)] for s in sorted(used)}
    json.dump(out, open(NET, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('stations', len(out['stations']), 'links', len(edges), 'commuters', round(T.sum()), 'placed', round(placed))
    for line, L in out['lines'].items():
        ms = [s for s, v in L['stations'].items() if v['count'] is not None and v['model'] > 0]
        err = max((abs(L['stations'][s]['fit'] / L['stations'][s]['count'] - 1) for s in ms if L['stations'][s]['count'] > 0), default=0)
        print(' ', line, 'links', len(L['edges']), 'stations', len(L['stations']), 'counted', len(ms), 'counts', round(L['count_total'] or 0), 'unplaced', round(L['count_unplaced']),
              'model', round(L['model_total']), 'fit', round(L['fit_total']), 'published', L['published'], 'worst fit', round(err, 3), 'peak share', round(peak_share.get(line, 0), 3))


# ====================================================================== step 2: the data of the map
LON0, LAT0 = 2.3488, 48.8534           # Notre-Dame: the map is in kilometres east and north of it
NAMES = {'A': 'RER A', 'B': 'RER B', 'C': 'RER C', 'D': 'RER D', 'E': 'RER E', 'H': 'Line H', 'J': 'Line J', 'K': 'Line K', 'L': 'Line L', 'N': 'Line N', 'P': 'Line P', 'R': 'Line R',
         'U': 'Line U', 'V': 'Line V', 'F': 'RER F', 'G': 'RER G'}
RER = ('A', 'B', 'C', 'D', 'E')
PROJECT_LINE = {'H': 'F', 'K': 'F', 'L': 'F', 'P': 'G', 'N': 'G'}          # the plan joins lines H, K and L into RER F, and P and N into RER G
AM_TUNNEL = 0.6                        # share of a new tunnel's morning riders who go the busier way (ASSUMPTION)
# high-speed lines, drawn by hand from the terminal to the edge of the map (longitude, latitude)
TGV = {
    'TGV Nord': ('Nord', [(2.3553, 48.8809), (2.3460, 48.9350), (2.4000, 48.9800), (2.4700, 49.0150), (2.5650, 49.0600), (2.6000, 49.1300), (2.6500, 49.2600), (2.7200, 49.4200)]),
    'TGV Est': ('Est', [(2.3590, 48.8770), (2.4100, 48.8950), (2.4600, 48.8950), (2.5830, 48.8740), (2.6400, 48.8720), (2.7300, 48.9100), (2.8100, 48.9450), (3.1000, 48.9900), (3.4500, 49.0300)]),
    'TGV Sud-Est': ('Lyon', [(2.3735, 48.8449), (2.4300, 48.8000), (2.4400, 48.7700), (2.4650, 48.7480), (2.5300, 48.7200), (2.7000, 48.6700), (2.7450, 48.5700), (2.9500, 48.4000), (3.2500, 48.1800)]),
    'TGV Atlantique': ('Montparnasse', [(2.3205, 48.8412), (2.2950, 48.8200), (2.2800, 48.7800), (2.2600, 48.7260), (2.2200, 48.6800), (1.9500, 48.5700), (1.6500, 48.4300), (1.3500, 48.2800)]),
    'TGV around Paris': (None, [(2.5650, 49.0600), (2.5710, 49.0040), (2.6900, 48.9500), (2.7830, 48.8700), (2.7600, 48.7600), (2.7000, 48.6700)]),
    'TGV Massy to Valenton': (None, [(2.2600, 48.7260), (2.3100, 48.7350), (2.3700, 48.7500), (2.4650, 48.7480)]),
}
TGV_AXIS = {'TGV Nord': 'North', 'TGV Est': 'East', 'TGV Sud-Est': 'Southeast', 'TGV Atlantique': 'Atlantic'}
LABELS = ['Gare du Nord', 'Gare de Lyon', 'Gare Montparnasse', 'Gare Saint-Lazare', 'Châtelet - Les Halles', "Gare de l'Est", "Gare d'Austerlitz", 'La Défense', 'Bercy',      # by priority
          'Aéroport CDG (Terminal 2) - TGV', 'Versailles Chantiers', 'Massy - Palaiseau', 'Marne-la-Vallée Chessy', 'Cergy le Haut', 'Mantes-la-Jolie', 'Melun', 'Meaux', 'Creil', 'Pontoise',
          'Rambouillet', 'Étampes', 'Fontainebleau - Avon', 'Provins', 'Saint-Rémy-lès-Chevreuse', 'Corbeil-Essonnes', 'Juvisy', 'Saint-Denis', 'Chelles - Gournay',
          'Saint-Quentin en Yvelines - Montigny-le-Bretonneux', 'Dourdan', 'Malesherbes', 'Montereau', 'Coulommiers', 'Château-Thierry', 'Crépy-en-Valois', 'Persan - Beaumont',
          'Dreux', 'Beauvais', 'Montargis', 'Chartres', 'Vernon - Giverny', 'Saint-Germain-en-Laye', 'Poissy', 'Orry-la-Ville - Coye', 'Mitry - Claye', 'Tournan', 'Robinson',
          'Aulnay-sous-Bois', 'Villeneuve-Saint-Georges', 'Nanterre-La-Folie', 'Val de Fontenay', 'Noisy-le-Sec', 'Ermont - Eaubonne', 'Argenteuil', 'Saint-Michel Notre-Dame',
          'Invalides', 'Pont Cardinet', 'Asnières-sur-Seine', 'Boissy-Saint-Léger', 'Torcy']


def step2():
    import nordest as nd, model as md
    net = json.load(open(NET)); pub = json.load(open(PUB)); m = json.load(open(os.path.join(HERE, '..', 'src', 'data', 'model.json')))
    S, E, PS = net['stations'], net['edges'], net['peak_share']
    xy = lambda lon, lat: (round((lon - LON0) * math.cos(math.radians(LAT0)) * 111.32, 2), round((lat - LAT0) * 110.57, 2))
    ids = sorted(S); ni = {s: i for i, s in enumerate(ids)}
    nodes = [list(xy(S[s][1], S[s][2])) + [S[s][0]] for s in ids]
    links = [[ni[a], ni[b]] for a, b, *_ in E]
    by_name = {S[s][0]: ni[s] for s in ids}
    def link_between(a, b):                                             # a link of the map, added when the two stations are not yet joined
        k = [a, b] if a < b else [b, a]
        if k not in links: links.append(k)
        return links.index(k)
    def poly(pts):                                                     # a hand-drawn line: new points, joined in order; starts at an existing station when one is at its first point
        out = []; prev = None
        for i, (lon, lat) in enumerate(pts):
            x, y = xy(lon, lat); hit = [j for j, n in enumerate(nodes) if abs(n[0] - x) < 0.25 and abs(n[1] - y) < 0.25]
            j = hit[0] if hit else len(nodes)
            if not hit: nodes.append([x, y, None])
            if prev is not None and prev != j: out.append(link_between(prev, j))
            prev = j
        return out
    places = pub.get('places', {}); cap = pub.get('capacity', {})
    series = {}; today = []; proj = []
    def rec(link, sid, pax, q, tph, tpd, load=None, seats=None, extra=None):
        return {'l': link, 's': sid, 'p': None if pax is None else round(pax), 'q': q, 'h': tph, 'd': tpd, 'ld': None if load is None else round(load), 'pl': seats, **(extra or {})}

    # ---- RER and Transilien: fitted to the station counts
    line_rows = []
    for line in [l for l in RAIL if l in net['lines'] and not l.startswith('TER')]:
        L = net['lines'][line]; pl = places.get(line, {}).get('n'); share = PS.get(line)
        series[line] = {'name': NAMES[line], 'kind': 'rer' if line in RER else 'transilien'}
        whole = pub['lines'].get(line); q = 'fit' if not whole else 'fit+'
        best = None
        for e, v in L['edges'].items():
            e = int(e); am = v['am']; way = 0 if (am is None or am >= 0.5) else 1; s = max(am, 1 - am) if am is not None else None
            tph = v['peak'][way] if am is not None else max(v['peak']); load = share * s * v['pax'] if (share and s is not None) else None
            r = rec(e, line, v['pax'] if v['pax'] > 0 else None, q if v['pax'] > 0 else 'none', tph, v['day'][0] + v['day'][1], load, pl * tph if (pl and tph) else None)
            today.append(r)
            if r['p'] and (best is None or r['p'] > best['p']): best = r
        cnt = [v for v in L['stations'].values() if v['count'] is not None]
        tm = [L['stations'][sx]['count'] for sx in TERMINALS if sx in L['stations'] and L['stations'][sx]['count']] if line not in RER else []
        line_rows.append({'line': line, 'name': NAMES[line], 'counted': round(sum(v['count'] for v in cnt)), 'stations': len(cnt), 'of': len(L['stations']),
                          'years': sorted({v['year'] for v in cnt}), 'by': sorted({v['src'] for v in cnt}), 'fit': round(L['fit_total']), 'unplaced': round(L['count_unplaced']),
                          'published': (whole or pub['published'].get(line) or {}).get('day'), 'pub_year': (whole or pub['published'].get(line) or {}).get('year'),
                          'pub_src': (whole or pub['published'].get(line) or {}).get('src'), 'used_total': bool(whole), 'peak_share': share, 'places': pl, 'places_src': places.get(line, {}).get('src'),
                          'max_p': best['p'] if best else None, 'max_at': [nodes[links[best['l']][0]][2], nodes[links[best['l']][1]][2]] if best else None,
                          'max_h': best['h'] if best else None, 'max_ld': best['ld'] if best else None,
                          'term': tm[0] if tm else None, 'term_share': round(2 * tm[0] / sum(v['count'] for v in cnt), 3) if tm else None})

    # ---- TER: the published total at the Paris terminal, shared out by the trains of the IDFM timetable (which lists only part of them); nothing where no total is published
    ter_rows = []
    for line in [l for l in RAIL if l in net['lines'] and l.startswith('TER ') and l != 'TER other']:
        L = net['lines'][line]; t = line[4:]; tot = pub['ter'].get(t); series[line] = {'name': 'TER ' + t, 'kind': 'ter'}
        term = ni[[s for s, n in TERMINALS.items() if n == t][0]]
        at = sum(v['day'][0] + v['day'][1] for e, v in L['edges'].items() if term in links[int(e)])
        for e, v in L['edges'].items():
            tpd = v['day'][0] + v['day'][1]
            today.append(rec(int(e), line, tot['day'] * min(1.0, tpd / at) if tot and at else None, 'split' if tot else 'none', max(v['peak']), tpd))
        ter_rows.append({'terminal': t, 'day': tot['day'] if tot else None, 'year': tot['year'] if tot else None, 'src': tot['src'] if tot else None, 'trains_idfm': at})

    # ---- TGV: passengers of each line at its Paris terminal (the study's figures, from the regulator), the same along the line; trains of the study's busy hour
    tgv_rows = []; tgv_links = {}
    for name, (term, pts) in TGV.items():
        series[name] = {'name': name, 'kind': 'tgv'}; ls = poly(pts); tgv_links[name] = ls
        axis = TGV_AXIS.get(name); pax = md.HS_PAX[term] * 1e6 / 365 if term else None; tph = m['hour_today'][axis] if axis else None
        for l in ls: today.append(rec(l, name, pax, 'published' if pax else 'none', tph, None))
        if term: tgv_rows.append({'line': name, 'terminal': term, 'year_m': md.HS_PAX[term], 'day': round(pax), 'hour': tph, 'hour_full': m['hour_full'][axis]})

    # ---- with the plan, by line: today's passengers on the same lines, renamed, and the passengers of the new tunnels from the study's own model
    for line in ('F', 'G'): series[line] = {'name': NAMES[line], 'kind': 'rer'}
    for r in today:
        r2 = dict(r); r2['s'] = PROJECT_LINE.get(r['s'], r['s']); proj.append(r2)
    merged = {}                                                        # lines joined into one: their passengers and trains on a link add up
    for r in proj:
        k = (r['l'], r['s'])
        if k not in merged: merged[k] = r; continue
        o = merged[k]
        for f in ('p', 'h', 'd', 'ld', 'pl'):
            if r[f] is not None: o[f] = (o[f] or 0) + r[f]
        if o['q'] == 'none': o['q'] = r['q']
    proj = list(merged.values())
    R = m['regional']; ss = R['second_station_by_line']; cross = R['cross']['pairs']; W260 = 1e6 / 260
    f_pax = (ss['H'] + ss['K'] + ss['L'] + cross['H-L']['project'] + cross['K-L']['project'] + cross['P-L']['project']) * W260
    g_pax = (ss['P'] + ss['N'] + cross['P-N']['project'] + cross['H-N']['project'] + cross['K-N']['project']) * W260
    RP = m['reg_platforms']; nordN, est, sl, mont, lyon, chat = (by_name[n] for n in ('Gare du Nord', "Gare de l'Est", 'Gare Saint-Lazare', 'Gare Montparnasse', 'Gare de Lyon', 'Châtelet - Les Halles'))
    # The suburban tunnels: the travel-time engine (model/regiontimes.py) sends each commuter of the census by the quickest route on the plan's
    # network, lines 15 to 18 in service, and counts who rides through each tunnel. A commuter of the engine stands for as many passengers a day
    # as on today's network at the three terminals it reproduces well: line P at Gare de l'Est, line N at Montparnasse, lines H and K at Gare du Nord.
    g_pax_s = g_pax; engine = None
    rf = os.path.join(HERE, 'inputs', 'regiontimes', 'riders.json')
    if os.path.exists(rf):
        RV = json.load(open(rf))['versions']; T0 = RV['today']; P1 = RV['plan']
        term = lambda recs, name, lines: sum(r['p'] or 0 for r in recs if r['s'] in lines and by_name[name] in links[r['l']])
        counted = term(today, "Gare de l'Est", ('P',)) + term(today, 'Gare Montparnasse', ('N',)) + term(today, 'Gare du Nord', ('H', 'K'))
        modelled = T0["P at Gare de l'Est"] + T0['N at Montparnasse'] + T0['H and K at Gare du Nord']; fac = counted / modelled
        nm = {'f': 'RER F tunnel, Nord-Est to Saint-Lazare', 'g': 'RER G tunnel, Nord-Est to Châtelet', 'g_s': 'RER G tunnel, Châtelet to Montparnasse',
              'b': 'B, Châtelet to Gare du Nord', 'd': 'D, Châtelet to Gare du Nord'}
        f_pax, g_pax, g_pax_s = (P1[nm[x]] * fac for x in ('f', 'g', 'g_s'))
        engine = {'factor': round(fac, 2), 'counted': round(counted, -3), 'modelled': round(modelled, -2), 'commuters': {x: round(P1[nm[x]], -2) for x in nm},
                  'bd_future': round(RV['future'][nm['b']] + RV['future'][nm['d']], -2), 'bd_plan': round(P1[nm['b']] + P1[nm['d']], -2),
                  'bd_relief': round(1 - (P1[nm['b']] + P1[nm['d']]) / (RV['future'][nm['b']] + RV['future'][nm['d']]), 3),
                  'l_modelled': round(T0['L at Saint-Lazare'], -2), 'l_counted': round(term(today, 'Gare Saint-Lazare', ('L',)), -3),
                  'bd_modelled': round(T0[nm['b']] + T0[nm['d']], -2),
                  'today_net': {x: int(round(RV['plan_today'][nm[x]] * fac, -3)) for x in ('f', 'g', 'g_s')} if 'plan_today' in RV else None}
    def tunnel(a, b, sid, pax, tph, capacity, lines_for_load, name):
        share = sum(PS.get(l, 0) for l in lines_for_load) / len(lines_for_load) if lines_for_load else None
        pl = [places.get(l, {}).get('n') for l in lines_for_load]; pl = sum(pl) / len(pl) if lines_for_load and all(pl) else None
        return rec(link_between(a, b), sid, pax, 'study', tph, None, share * AM_TUNNEL * pax if share else None, pl * tph if pl else None, {'cap': capacity, 'new': name})
    f_tph = max(sum(RP['h']['peak'].values()), RP['h']['peak_l']); g_tph = m['params']['g_trains_h']
    proj.append(tunnel(nordN, sl, 'F', f_pax, f_tph, RP['h']['per_track'] * RP['h']['tracks'] / 2, ['H', 'L'], 'RER F tunnel'))
    proj.append(tunnel(est, chat, 'G', g_pax, g_tph, RP['n']['per_track'] * RP['n']['tracks'] / 2, ['P', 'N'], 'RER G tunnel'))
    proj.append(tunnel(chat, mont, 'G', g_pax_s, g_tph, RP['n']['per_track'] * RP['n']['tracks'] / 2, ['P', 'N'], 'RER G tunnel'))
    # TGV: who rides through a tunnel. Each passenger of the Paris region takes the stop that is quickest for them, the ride between stops counted
    # (as nordest.far_stop_share); passengers who cross Paris ride the side that joins their two lines.
    pts, reg = nd.DATA['clock']; TH = nd.TH_ACCESS; ringpop = collections.defaultdict(float)
    reg = [r for r in reg if nd.ring(r['dep']) != 'Paris']                # Paris is covered by the sample of points
    for r in reg: ringpop[nd.ring(r['dep'])] += r['pop']
    samples = [({k: t[k] for k in nd.KEYS}, nd.SH['Paris'] / len(pts)) for t in pts] + [({k: r['t_' + k] for k in nd.KEYS}, nd.SH[nd.ring(r['dep'])] * r['pop'] / ringpop[nd.ring(r['dep'])]) for r in reg]
    assert abs(sum(w for _, w in samples) - 1) < 1e-6
    side = collections.defaultdict(float)                              # share of a line's Paris-region passengers who ride each side
    for t, w in samples:
        ne = min(t['Nord'], t['Est'])
        o = {'Lyon': t['Lyon'], 'NL': ne + TH['L'], 'ML': t['Montparnasse'] + TH['LM']}; k = min(o, key=o.get); side[('Lyon', k)] += w
        o = {'Montparnasse': t['Montparnasse'], 'NM': ne + TH['M'], 'ML': t['Lyon'] + TH['LM']}; k = min(o, key=o.get); side[('Montparnasse', k)] += w
        o = {'NE': ne, 'NL': t['Lyon'] + TH['L'], 'NM': t['Montparnasse'] + TH['M']}; k = min(o, key=o.get); side[('NE', k)] += w
    conn = nd.CONN + m['yearly']['tgv_conn_journeys']; idf = nd.HS_TERMINALS - 2 * nd.CONN; q = {k: idf * w for k, w in nd.W.items()}
    from estimate import PSH
    pair = lambda a, b: PSH.get((a, b), PSH.get((b, a), 0.0)) * conn
    tg = {'NL': q['Lyon'] * side[('Lyon', 'NL')] + (q['Nord'] + q['Est']) * side[('NE', 'NL')] + pair('Lyon', 'Nord') + pair('Lyon', 'Est'),
          'NM': q['Montparnasse'] * side[('Montparnasse', 'NM')] + (q['Nord'] + q['Est']) * side[('NE', 'NM')] + pair('Montparnasse', 'Nord') + pair('Montparnasse', 'Est'),
          'ML': q['Lyon'] * side[('Lyon', 'ML')] + q['Montparnasse'] * side[('Montparnasse', 'ML')] + pair('Montparnasse', 'Lyon')}
    TP = m['ter_paths']; loads = TP['loads']; paths = TP['paths_per_hour']
    sh = R['second_station_share']; TERY = m['params'].get('ter') or {k: v * 350 / 1e6 for k, v in nd.TER_DAY.items()}
    ter_nm = (TERY['Nord'] * sh['TER Nord'] + TERY['Montparnasse'] * sh['TER Montparnasse']); ter_nl = (TERY['Est'] * sh['TER Est'] + TERY['Lyon'] * sh['TER Lyon'])
    thr = R['through_ter']; tn = TERY['Nord'] + TERY['Montparnasse']; te = TERY['Est'] + TERY['Lyon']
    ter_nm += thr * tn / (tn + te); ter_nl += thr * te / (tn + te)
    series['TGV tunnels'] = {'name': 'TGV', 'kind': 'tgv'}; series['TER tunnels'] = {'name': 'TER', 'kind': 'ter'}
    tunnels = [('NM', nordN, mont, 'nemont', ter_nm, 'Nord-Est to Montparnasse'), ('NL', nordN, lyon, 'nelyon', ter_nl, 'Nord-Est to Gare de Lyon'), ('ML', mont, lyon, 'link', 0.0, 'Montparnasse to Gare de Lyon')]
    tun_rows = []
    for k, a, b, key, ter_y, name in tunnels:
        l = link_between(a, b); ld = loads[key]
        proj.append(rec(l, 'TGV tunnels', tg[k] * 1e6 / 365, 'study', ld['tgv'], None, None, None, {'cap': paths, 'new': name, 'all': ld['total']}))
        if ter_y > 0: proj.append(rec(l, 'TER tunnels', ter_y * 1e6 / 350, 'study', ld['ter'], None, None, None, {'cap': paths, 'new': name, 'all': ld['total']}))
        tun_rows.append({'name': name, 'tgv': round(tg[k] * 1e6 / 365), 'ter': round(ter_y * 1e6 / 350), 'trains': ld['total'], 'tgv_h': ld['tgv'], 'ter_h': ld['ter'], 'cap': paths})
    for name, axis in TGV_AXIS.items():                                # the approaches at the busy hour of the plan
        key = {'North': 'north', 'East': 'east', 'Southeast': 'southeast', 'Atlantic': 'atlantic'}[axis]
        for r in proj:
            if r['s'] == name: r['h'] = loads[key]['tgv']; r['cap'] = paths; r['all'] = loads[key]['total']

    # ---- by track: the lines that share a pair of tracks on a link are added up. In Paris each RER tunnel is one pair (RER B and D share theirs
    # between Chatelet and Gare du Nord); elsewhere the open data do not say which trains share which tracks: each RER line is taken alone, and
    # the Transilien and TER trains of a link together.
    bd = link_between(by_name['Gare du Nord'], chat)
    e_core = {link_between(by_name[a], by_name[b]) for a, b in (('Magenta', 'Haussmann Saint-Lazare'), ('Haussmann Saint-Lazare', 'Neuilly - Porte Maillot'), ('Neuilly - Porte Maillot', 'La Défense'), ('La Défense', 'Nanterre-La-Folie'))
              if by_name.get(a) is not None and by_name.get(b) is not None}
    def group(r, plan):
        s = r['s']
        if series[s]['kind'] == 'tgv' and 'new' not in r: return s
        if 'new' in r: return 'T:' + r['new'] if s in ('TGV tunnels', 'TER tunnels') else s
        if s in ('B', 'D') and r['l'] == bd: return 'BD'
        if s in RER or s in ('F', 'G'): return s
        return 'S'
    def tracks(recs, plan):
        g = {}
        for r in recs:
            k = (r['l'], group(r, plan)); o = g.setdefault(k, {'l': r['l'], 's': k[1], 'p': 0, 'h': 0, 'ld': 0, 'pl': 0, 'who': [], 'miss': False, 'nopl': False, 'q': r['q']})
            o['who'].append(r['s'])
            if r['p'] is None: o['miss'] = True
            else: o['p'] += r['p']
            o['h'] += r['h'] or 0
            if r['ld'] is not None and r['pl']: o['ld'] += r['ld']; o['pl'] += r['pl']
            elif r['p']: o['nopl'] = True
            for f in ('cap', 'new', 'all'):
                if f in r: o[f] = r[f]
        out = []
        for (l, k), o in g.items():
            if k == 'BD': o['cap'] = cap['BD']['cap']
            if k == 'E' and l in e_core: o['cap'] = cap['E']['cap']
            if k == 'TGV Sud-Est' and not plan: o['cap'] = cap['LGVSE']['cap']
            if 'all' in o: o['h'] = o['all']
            o['crowd'] = round(o['ld'] / o['pl'], 3) if o['pl'] and not o['nopl'] else None
            o['use'] = round(o['h'] / o['cap'], 3) if o.get('cap') and o['h'] else None
            if o['p'] == 0 and o['miss']: o['p'] = None
            for f in ('ld', 'pl', 'miss', 'nopl', 'all'): o.pop(f, None)
            out.append(o)
        return out
    gt, gp = tracks(today, False), tracks(proj, True)
    gnames = {'BD': 'RER B and D, shared tunnel', 'S': 'Transilien and TER tracks'}
    for o in gt + gp:
        if o['s'] not in series and o['s'] not in gnames: gnames[o['s']] = o['s'][2:] if o['s'].startswith('T:') else o['s']

    # ---- the sections worth a line in the table
    def at_station(recs, name, lines):
        n = by_name[name]; return sum(r['p'] or 0 for r in recs if r['s'] in lines and n in links[r['l']])
    def on_link(recs, a, b, lines):
        l = link_between(by_name[a], by_name[b]); rs = [r for r in recs if r['l'] == l and r['s'] in lines]
        ld = sum(r['ld'] or 0 for r in rs); pl = sum(r['pl'] or 0 for r in rs if r['ld'] is not None)
        return {'p': sum(r['p'] or 0 for r in rs), 'h': sum(r['h'] or 0 for r in rs), 'ld': round(ld), 'crowd': round(ld / pl, 3) if pl else None}
    def at_term(name, lines):                                          # a line where it enters its Paris terminal: passengers a day both ways, trains and passengers in the busiest hour, busier way
        n = by_name[name]; rs = [r for r in today if r['s'] in lines and n in links[r['l']]]
        return {'p': sum(r['p'] or 0 for r in rs), 'h': sum(r['h'] or 0 for r in rs), 'ld': round(sum(r['ld'] or 0 for r in rs))}
    bal = {'HK': at_term('Gare du Nord', ('H', 'K')), 'H': at_term('Gare du Nord', ('H',)), 'K': at_term('Gare du Nord', ('K',)), 'L': at_term('Gare Saint-Lazare', ('L',)), 'J': at_term('Gare Saint-Lazare', ('J',)),
           'P': at_term("Gare de l'Est", ('P',)), 'N': at_term('Gare Montparnasse', ('N',)), 'R': at_term('Gare de Lyon', ('R',))}
    study_h = {'H': RP['h']['peak']['H'], 'K': RP['h']['peak']['K'], 'HK': RP['h']['peak']['H'] + RP['h']['peak']['K'], 'L': RP['h']['peak_l'], 'P': RP['n']['peak']['P'], 'N': RP['n']['peak']['N']}
    for k, v in bal.items():                                           # trains: the counts the study uses at each terminal where it has one (same timetable, busiest 60 minutes)
        v['h'] = study_h.get(k, v['h']); v['per_train'] = int(round(v['ld'] / v['h'], -1)) if v['h'] else None
    lrow = next(l for l in line_rows if l['line'] == 'L')              # line L is busiest a little beyond its terminal
    bal['L'].update(max_p=lrow['max_p'], max_at=lrow['max_at'], max_ld=lrow['max_ld'], max_per_train=int(round(lrow['max_ld'] / bal['L']['h'], -1)))
    bal['ratio'] = {'N_P': round(bal['N']['p'] / bal['P']['p'], 3), 'L_HK': round(bal['L']['p'] / bal['HK']['p'], 3), 'Lmax_HK': round(lrow['max_p'] / bal['HK']['p'], 3), 'J_HK': round(bal['J']['p'] / bal['HK']['p'], 3)}
    for k, v in bal.items():
        if k != 'ratio': v['p'] = int(round(v['p'], -3)); v['ld'] = int(round(v['ld'], -2))
    bal['L']['max_p'] = int(round(bal['L']['max_p'], -3)); bal['L']['max_ld'] = int(round(bal['L']['max_ld'], -2))
    print('balance', bal)
    sec = {'bd': on_link(today, 'Gare du Nord', 'Châtelet - Les Halles', ('B', 'D')), 'b_bd': on_link(today, 'Gare du Nord', 'Châtelet - Les Halles', ('B',)), 'd_bd': on_link(today, 'Gare du Nord', 'Châtelet - Les Halles', ('D',)),
           'a': on_link(today, 'Châtelet - Les Halles', 'Gare de Lyon', ('A',)), 'd_lyon': on_link(today, 'Châtelet - Les Halles', 'Gare de Lyon', ('D',)),
           'b_south': on_link(today, 'Châtelet - Les Halles', 'Saint-Michel Notre-Dame', ('B',)), 'e': on_link(today, 'Magenta', 'Haussmann Saint-Lazare', ('E',)),
           'h_nord': {'p': at_station(today, 'Gare du Nord', ('H',))}, 'k_nord': {'p': at_station(today, 'Gare du Nord', ('K',))}, 'p_est': {'p': at_station(today, "Gare de l'Est", ('P',))},
           'l_sl': {'p': at_station(today, 'Gare Saint-Lazare', ('L',))}, 'j_sl': {'p': at_station(today, 'Gare Saint-Lazare', ('J',))}, 'n_mont': {'p': at_station(today, 'Gare Montparnasse', ('N',))},
           'r_lyon': {'p': at_station(today, 'Gare de Lyon', ('R',))}, 'f': {'p': round(f_pax), 'h': f_tph, 'cap': RP['h']['per_track'] * RP['h']['tracks'] / 2},
           'g': {'p': round(g_pax), 'h': g_tph, 'cap': RP['n']['per_track'] * RP['n']['tracks'] / 2}}
    tot = {l['line']: l['fit'] for l in line_rows}
    key = {'dpn': tot['D'] + tot['P'] + tot['N'], 'pn': tot['P'] + tot['N'], 'hkl': tot['H'] + tot['K'] + tot['L'], 'all': sum(tot.values()),
           'counted': sum(l['counted'] for l in line_rows), 'stations': sum(l['stations'] for l in line_rows), 'links': len(E), 'commuters': round(net['commuters']),
           'g_share_of_d': g_pax / sec['d_bd']['p'] if sec['d_bd']['p'] else None, 'side': {'%s %s' % k: round(v, 3) for k, v in side.items()}, 'conn_project': conn, 'am_tunnel': AM_TUNNEL}
    th = lambda x: None if x is None else int(round(x / 1000.0)) * 1000           # figures written in the text, to the nearest thousand
    lr = {l['line']: l for l in line_rows}
    k = {'bd': th(sec['bd']['p']), 'b_bd': th(sec['b_bd']['p']), 'd_bd': th(sec['d_bd']['p']), 'a': th(sec['a']['p']), 'e': th(sec['e']['p']), 'b_south': th(sec['b_south']['p']), 'd_lyon': th(sec['d_lyon']['p']),
         'f': th(f_pax), 'g': th(g_pax), 'g_s': th(g_pax_s), 'engine': engine, 'dpn': th(key['dpn']), 'pn': th(key['pn']), 'hkl': th(key['hkl']), 'counted': th(key['counted']), 'all': th(key['all']),
         'line': {l: th(v['fit']) for l, v in lr.items()}, 'count': {l: th(v['counted']) for l, v in lr.items()}, 'term_share': {l: v['term_share'] for l, v in lr.items() if v['term_share']},
         'tun': {t['name']: {'tgv': th(t['tgv']), 'ter': th(t['ter']), 'all': th(t['tgv'] + t['ter']), 'trains': t['trains']} for t in tun_rows},
         'study_day': {l: th(q * 1e6 / 260) for l, q in nd.LINES.items()}, 'tgv_day': {r['terminal']: th(r['day']) for r in tgv_rows},
         'crowd': {n: sec[n]['crowd'] for n in ('bd', 'b_bd', 'd_bd', 'a', 'e', 'b_south', 'd_lyon')}, 'ld': {n: th(sec[n]['ld']) for n in ('bd', 'b_bd', 'd_bd', 'a', 'e')},
         'at': {n: th(sec[n]['p']) for n in ('h_nord', 'k_nord', 'p_est', 'l_sl', 'j_sl', 'n_mont', 'r_lyon')}, 'h': {n: sec[n]['h'] for n in ('bd', 'a', 'e', 'b_south', 'd_lyon', 'f', 'g')},
         'tgv_year': {r['terminal']: r['year_m'] for r in tgv_rows}, 'tgv_total': sum(r['year_m'] for r in tgv_rows),
         'f_ss': th((ss['H'] + ss['K'] + ss['L']) * W260), 'g_ss': th((ss['P'] + ss['N']) * W260), 'ter_trains': {r['terminal']: r['trains_idfm'] for r in ter_rows}}
    # ---- write: compact rows [link, series, passengers, quality, trains in the busy hour, trains a day, passengers in the busy hour one way, places in that hour, capacity, tunnel name]
    sid = {k: i for i, k in enumerate(series)}; gid = {k: i for i, k in enumerate(list(series) + [k for k in gnames])}
    row = lambda r: [r['l'], sid[r['s']], r['p'], r['q'], r['h'], r['d'], r['ld'], r['pl'], r.get('cap'), r.get('new')]
    grow = lambda o: [o['l'], gid[o['s']], o['p'], o['q'], o['h'], o['crowd'], o['use'], o.get('cap'), [sid[w] for w in sorted(set(o['who']), key=lambda w: sid[w])], o.get('new')]
    # station names: the hand-picked ones first, then every other station, the busiest first; the page shows as many as fit at the zoom chosen
    busy = {}
    for r in today:
        for n in links[r['l']]: busy[n] = busy.get(n, 0) + (r['p'] or 0)
    first = [by_name[n] for n in LABELS if n in by_name]
    label = first + sorted((i for i, n in enumerate(nodes) if n[2] and i not in first), key=lambda i: -busy.get(i, 0))
    # landmarks under the lines: the borders of the departements (IGN Admin Express, by way of france-geojson) and the rivers (OpenStreetMap)
    def thin(pts, step):                                               # drop points closer than 'step' km to the last one kept
        out = [pts[0]]
        for q in pts[1:-1]:
            if math.hypot(q[0] - out[-1][0], q[1] - out[-1][1]) >= step: out.append(q)
        return out + [pts[-1]]
    geo = {'dep': [], 'rivers': []}
    f = os.path.join(RAW, 'ign_departements-ile-de-france.geojson')
    if os.path.exists(f):
        for ft in json.load(open(f))['features']:
            g = ft['geometry']; polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
            for pl in polys: geo['dep'].append([ft['properties']['code'], thin([list(xy(lon, lat)) for lon, lat in pl[0]], 0.25 if ft['properties']['code'] == '75' else 0.6)])
    f = os.path.join(RAW, 'osm_rivers_idf.json')
    if os.path.exists(f):
        for name, ways in json.load(open(f))['rivers'].items():
            for w in ways:
                pts = thin([list(xy(lon, lat)) for lon, lat in w], 0.15)
                if len(pts) > 1: geo['rivers'].append([name, pts])
    f = os.path.join(HERE, '..', 'src', 'data', 'paris_geo.json')              # the two woods of Paris, as on the other maps of the study
    geo['parks'] = [thin([list(xy(lon, lat)) for lon, lat in w['r'][0]], 0.1) for w in json.load(open(f))['bois']] if os.path.exists(f) else []
    out = {'day': net['day'], 'nodes': nodes, 'links': links, 'label': label, 'geo': geo, 'balance': bal, 'series': [dict(id=k, **v) for k, v in series.items()], 'groups': [{'id': k, 'name': v} for k, v in gnames.items()],
           'today': [row(r) for r in today], 'project': [row(r) for r in proj], 'today_tracks': [grow(o) for o in gt], 'project_tracks': [grow(o) for o in gp],
           'lines': line_rows, 'ter': ter_rows, 'tgv': tgv_rows, 'tunnels': tun_rows, 'sec': sec, 'key': key, 'k': k, 'peak_share': PS, 'capacity': cap, 'published': pub}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('nodes', len(nodes), 'links', len(links), 'rows', len(today), len(proj), len(gt), len(gp), 'bytes', os.path.getsize(OUT))
    for l in line_rows: print(' ', l['line'], 'counted', l['counted'], 'fit', l['fit'], 'busiest', l['max_p'], l['max_at'], 'trains', l['max_h'], 'peak load', l['max_ld'])
    print('sections', json.dumps(sec)); print('tunnels', tun_rows); print('key', key)


if __name__ == '__main__':
    if len(sys.argv) == 4: step1(*sys.argv[1:])
    else: step2()
