"""Paris Through Rail Programme - 1,000-point connectivity study.

Screening model of public-transport access time from 1,000 points evenly spread
over Paris to (a) today's four TGV terminals and (b) the Saint-Denis-Pleyel hub.

Network: IDFM network of 2026-10-05 (metro, RER, tram) - stations, coordinates,
stop order per line. Link times are modelled from distance, not from the timetable.
"""
import json, math, heapq, collections, csv, sys
try:                                    # shapely is only needed to rebuild the grid of points (python3 model.py)
    from shapely.geometry import shape, Point
    from shapely.ops import unary_union
except ImportError:
    shape = Point = unary_union = None

DATA = '/home/claude/data'
OUT = '/home/claude/build/model'

# ----------------------------------------------------------------- parameters
WALK_MIN_PER_KM = 60 / 4.5 * 1.3          # 4.5 km/h, detour factor 1.3 on straight-line distance
MAX_WALK_KM = 1.5                         # search radius for boarding stations
METRO_SPEED = {'1': 28.5, '2': 21.8, '3': 22.3, '4': 23.7, '5': 25.1, '6': 24.8, '7': 24.0,
               '8': 26.9, '9': 22.6, '10': 24.5, '11': 28.1, '12': 25.0, '13': 26.0,
               '3B': 20.0, '7B': 20.0}    # commercial speed km/h (length / end-to-end time)
L14_END_TO_END_MIN = 40.0                 # official Saint-Denis-Pleyel to Orly
METRO_DWELL = 0.5                         # min per stop, inside the end-to-end time
TRACK_FACTOR = 1.03                       # track length / sum of straight-line station spacing
RER_RUN = {'A': 60, 'B': 60, 'D': 60, 'E': 60, 'C': 45}   # running speed km/h
RER_STOP_PENALTY = 1.0                    # min per stop (dwell + braking + acceleration)
RER_TRACK_FACTOR = 1.10
TRAM_SPEED = 18.0
HEADWAY = {'1': 2.0, '14': 2.0, '4': 2.5, '7': 4.0, '13': 5.0, '3B': 5.0, '7B': 5.0,
           'A': 4.0, 'B': 5.0, 'C': 7.5, 'D': 7.5, 'E': 5.0}      # daytime minutes
DEF_HEADWAY = {'metro': 3.0, 'rer': 6.0, 'tram': 5.0, 'train': 10.0, 'gpe': 3.0}
ACCESS = {'metro': 1.5, 'rer': 3.0, 'tram': 0.5, 'train': 2.0, 'gpe': 3.0}   # street to platform, minutes
ACCESS_L14 = 2.5
CONCOURSE_FROM_STREET = 2.0               # street at the station to main-line concourse

# main-line concourse reached from a platform of the station complex (minutes)
TERMINALS = {
    'Nord':         {'station': 'IDFM:71410', 'plat': {'4': 3, '5': 3, 'B': 4, 'D': 4, 'H': 2, 'K': 2}, 'xy': (48.880185, 2.355151)},
    'Est':          {'station': 'IDFM:71359', 'plat': {'4': 3, '5': 3, '7': 3, 'P': 2}, 'xy': (48.876742, 2.358424)},
    'Lyon':         {'station': 'IDFM:73626', 'plat': {'1': 3, '14': 4, 'A': 4, 'D': 4, 'R': 3}, 'xy': (48.844888, 2.373520)},
    'Montparnasse': {'station': 'IDFM:71139', 'plat': {'6': 4, '13': 4, '4': 6, '12': 6, 'N': 2}, 'xy': (48.841172, 2.320514)},
    'Pleyel':       {'station': 'IDFM:490784', 'plat': {'14': 4, '15': 4, '16': 4, '17': 4}, 'xy': (48.917214, 2.345011)},
}
# share of high-speed passengers by today's terminal (derived estimates, 2024)
HS_PAX = {'Montparnasse': 44.0, 'Lyon': 35.0, 'Nord': 21.5, 'Est': 12.0}
# first-order change in on-train time when the train serves Pleyel instead of the terminal (min)
TRAIN_DELTA = {'Nord': -2.5, 'Est': 0.0, 'Lyon': 3.5, 'Montparnasse': 3.0}


KW, KQ, KR = 1.0, 1.0, 1.0   # weights on walking, on waiting and on riding metro, RER, tram or suburban train


def set_weights(walk=1.0, wait=1.0, ride=1.0):
    global KW, KQ, KR
    KW, KQ, KR = walk, wait, ride


def hav(a, b):
    R = 6371.0088
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def build(with_programme=False, regional=False):
    d = json.load(open(f'{DATA}/metropolist_idfm/metropolist-data.json'))
    modes = ('metro', 'rer', 'tram', 'train') if regional else ('metro', 'rer', 'tram')
    lines = {l['id']: l for l in d['lines'] if l['mode'] in modes}
    st = {s['id']: s for s in d['stations']}
    xy = lambda sid: (st[sid]['latitude'], st[sid]['longitude'])
    variants = collections.defaultdict(list)
    for ls in d['lineStops']:
        if ls['lineId'] in lines:
            variants[(ls['lineId'], ls['routeVariantId'])].append((ls['order'], ls['stationId']))
    G = collections.defaultdict(dict)            # directed: G[u][v] = minutes

    def add(u, v, t):
        if v not in G[u] or t < G[u][v]:
            G[u][v] = t
        G[v]  # ensure node exists

    line_at = collections.defaultdict(set)      # station -> {(mode, shortName)}
    # metro running speed per line, calibrated on the longest variant
    run_speed = {}
    for (lid, vid), stops in variants.items():
        l = lines[lid]
        if l['mode'] != 'metro':
            continue
        ids = [s for _, s in sorted(stops)]
        L = sum(hav(xy(a), xy(b)) for a, b in zip(ids, ids[1:]))
        n = len(ids) - 1
        if l['shortName'] == '14':
            T = L14_END_TO_END_MIN
        else:
            T = L * TRACK_FACTOR / METRO_SPEED[l['shortName']] * 60
        key = l['shortName']
        if key not in run_speed or L > run_speed[key][0]:
            run_speed[key] = (L, L / max(T - METRO_DWELL * n, 1e-6) * 60)
    for (lid, vid), stops in variants.items():
        l = lines[lid]
        mode, name = l['mode'], l['shortName']
        ids = [s for _, s in sorted(stops)]
        for a, b in zip(ids, ids[1:]):
            dist = hav(xy(a), xy(b))
            if mode == 'metro':
                t = METRO_DWELL + dist / run_speed[name][1] * 60
            elif mode == 'rer':
                t = RER_STOP_PENALTY + dist * RER_TRACK_FACTOR / RER_RUN[name] * 60
            elif mode == 'train':
                t = 1.5 + dist * RER_TRACK_FACTOR / 75 * 60
            else:
                t = dist * 1.05 / TRAM_SPEED * 60
            add(('P', a, name), ('P', b, name), KR * t)
        for s in ids:
            line_at[s].add((mode, name))


    if regional:
        # Grand Paris Express lines 15, 16 and 17 (all due by 2031), added by hand
        NEW = {'Vitry Centre': (48.7895, 2.3925), 'Champigny Centre': (48.8165, 2.5100), 'Bry-Villiers-Champigny': (48.8250, 2.5450),
               'Drancy-Bobigny': (48.9135, 2.4290), 'Nanterre La Boule': (48.8885, 2.1990), 'Rueil-Suresnes Mont-Valérien': (48.8720, 2.2000),
               'Le Blanc-Mesnil': (48.9390, 2.4720), 'Aulnay': (48.9530, 2.4950), 'Le Bourget Aéroport': (48.9480, 2.4330),
               'Triangle de Gonesse': (48.9760, 2.4720), 'Le Mesnil-Amelot': (49.0180, 2.5950), 'Fort d Issy': (48.8140, 2.2740)}
        for nm, (la, lo) in NEW.items():
            st['GPE:' + nm] = {'id': 'GPE:' + nm, 'name': nm, 'latitude': la, 'longitude': lo}
        byname = {}
        for sid in line_at:
            byname.setdefault(st[sid]['name'], sid)
        def sid_of(nm):
            if nm in NEW:
                return 'GPE:' + nm
            return byname[nm]
        L15 = ['Pont de Sèvres', 'Issy', 'Fort d Issy', 'Châtillon - Montrouge', 'Bagneux - Lucie Aubrac', 'Arcueil - Cachan',
               'Villejuif - Gustave Roussy', 'Villejuif - Louis Aragon', 'Vitry Centre', 'Les Ardoines', 'Le Vert de Maisons',
               "Créteil - L'Échat", 'Saint-Maur - Créteil', 'Champigny Centre', 'Nogent - Le Perreux', 'Val de Fontenay',
               'Rosny Bois Perrier', 'Bondy', 'Pont de Bondy', 'Bobigny - Pablo Picasso', 'Drancy-Bobigny', "Fort d'Aubervilliers",
               "Mairie d'Aubervilliers", 'La Plaine Stade de France', 'Saint-Denis - Pleyel', 'Les Grésillons', 'Les Agnettes',
               'Bois-Colombes', 'Bécon les Bruyères', 'La Défense', 'Nanterre La Boule', 'Rueil-Suresnes Mont-Valérien',
               'Saint-Cloud', 'Pont de Sèvres']
        L15b = ['Champigny Centre', 'Bry-Villiers-Champigny', 'Noisy - Champs']
        L16 = ['Saint-Denis - Pleyel', 'La Courneuve - Six Routes', 'Le Bourget', 'Le Blanc-Mesnil', 'Aulnay', 'Sevran - Beaudottes',
               'Sevran - Livry', 'Clichy - Montfermeil', 'Chelles - Gournay', 'Noisy - Champs']
        L17 = ['Saint-Denis - Pleyel', 'La Courneuve - Six Routes', 'Le Bourget', 'Le Bourget Aéroport', 'Triangle de Gonesse',
               'Parc des Expositions', 'Aéroport CDG (Terminal 2) - TGV', 'Le Mesnil-Amelot']
        missing = [n for seq in (L15, L15b, L16, L17) for n in seq if n not in NEW and n not in byname]
        if missing:
            raise SystemExit('GPE station names not found: ' + repr(sorted(set(missing))))
        for nm, seq, v in (('15', L15, 55.0), ('15', L15b, 55.0), ('16', L16, 65.0), ('17', L17, 65.0)):
            ids = [sid_of(x) for x in seq]
            for a, b in zip(ids, ids[1:]):
                t = KR * hav(xy(a), xy(b)) * 1.05 / v * 60
                add(('P', a, nm), ('P', b, nm), t); add(('P', b, nm), ('P', a, nm), t)
            for sid in ids:
                line_at[sid].add(('gpe', nm))

    def wait(mode, name):
        return min(HEADWAY.get(name, DEF_HEADWAY[mode]) / 2, 5.0)

    def acc(mode, name):
        return ACCESS_L14 if name == '14' else ACCESS[mode]

    MONTP = 'IDFM:71139'
    for s, ls in line_at.items():
        big = len([1 for m, n in ls if m != 'tram']) >= 4
        for mode, name in ls:
            add(('S', s), ('P', s, name), KW * acc(mode, name) + KQ * wait(mode, name))
            add(('P', s, name), ('S', s), KW * acc(mode, name))
            for mode2, name2 in ls:
                if name2 == name:
                    continue
                w = 3.0 + (1.0 if 'rer' in (mode, mode2) or '14' in (name, name2) else 0.0) + (1.0 if big else 0.0)
                if s == MONTP and ({name, name2} & {'4', '12'}) and ({name, name2} & {'6', '13'}):
                    w = 6.0
                add(('P', s, name), ('P', s, name2), KW * w + KQ * wait(mode2, name2))
    # walking links between station complexes: published transfer times and short walks
    rail = list(line_at)
    for tr in d['transfers']:
        a, b = tr['fromStationId'], tr['toStationId']
        if a in line_at and b in line_at:
            t = max(tr['minTransferTime'] / 60 - 3.0, hav(xy(a), xy(b)) * WALK_MIN_PER_KM)
            add(('S', a), ('S', b), KW * t)
    for i, a in enumerate(rail):
        for b in rail[i + 1:]:
            dd = hav(xy(a), xy(b))
            if dd <= 0.7:
                add(('S', a), ('S', b), KW * dd * WALK_MIN_PER_KM)
                add(('S', b), ('S', a), KW * dd * WALK_MIN_PER_KM)

    if with_programme:
        # Programme regional lines, assuming regional trains call at Pleyel (assumption of this study).
        # X1: Pleyel - Paris Nord - Gare de Lyon (lines H/K-R plus TER), X2: Paris Nord - Montparnasse (P-N plus TER)
        PLE, NOR, LYO, MON = (TERMINALS[k]['station'] for k in ('Pleyel', 'Nord', 'Lyon', 'Montparnasse'))
        hw = 5.0
        for u, v, t in ((('P', PLE, 'X1'), ('P', NOR, 'X1'), 5.0), (('P', NOR, 'X1'), ('P', LYO, 'X1'), 5.5),
                        (('P', NOR, 'X2'), ('P', MON, 'X2'), 6.5)):
            add(u, v, KR * t); add(v, u, KR * t)
        add(('P', NOR, 'X1'), ('P', NOR, 'X2'), KW * 3.0 + KQ * hw / 2)
        add(('P', NOR, 'X2'), ('P', NOR, 'X1'), KW * 3.0 + KQ * hw / 2)
        for s, nm in ((PLE, 'X1'), (NOR, 'X1'), (NOR, 'X2'), (LYO, 'X1'), (MON, 'X2')):
            add(('S', s), ('P', s, nm), KW * 4.0 + KQ * hw / 2)
            add(('P', s, nm), ('S', s), KW * 4.0)
            for mode, name in line_at[s]:
                add(('P', s, name), ('P', s, nm), KW * 5.0 + KQ * hw / 2)
                add(('P', s, nm), ('P', s, name), KW * 5.0 + KQ * wait(mode, name))
    return G, st, line_at


def times_to(G, dest, with_programme=False):
    """Minutes from every node to the main-line concourse of `dest` (reverse Dijkstra)."""
    T = TERMINALS[dest]
    R = collections.defaultdict(list)
    for u, nb in G.items():
        for v, t in nb.items():
            R[v].append((u, t))
    dist = {}
    pq = []
    for name, t in T['plat'].items():
        heapq.heappush(pq, (KW * float(t), ('P', T['station'], name)))
    if with_programme and dest == 'Pleyel':
        heapq.heappush(pq, (KW * 3.0, ('P', T['station'], 'X1')))
    heapq.heappush(pq, (KW * CONCOURSE_FROM_STREET, ('S', T['station'])))
    while pq:
        dd, u = heapq.heappop(pq)
        if u in dist:
            continue
        dist[u] = dd
        for v, t in R[u]:
            if v not in dist:
                heapq.heappush(pq, (dd + t, v))
    return dist


def grid_points(n_target=1000):
    arr = json.load(open(f'{DATA}/boundaries/paris_arrondissements_from_iris.geojson'))
    bois = json.load(open(f'{DATA}/boundaries/paris_bois_from_iris.geojson'))
    polys = {f['properties']['arrondissement']: shape(f['geometry']) for f in arr['features']}
    woods = unary_union([shape(f['geometry']) for f in bois['features']])
    paris = unary_union(list(polys.values())).difference(woods)
    minx, miny, maxx, maxy = paris.bounds
    lat0 = (miny + maxy) / 2
    kx = 111.32 * math.cos(math.radians(lat0)); ky = 110.57
    # hexagonal grid; tune spacing by bisection to get exactly n_target points
    def make(sp):
        pts = []
        dy = sp * math.sqrt(3) / 2
        j = 0
        y = miny * ky
        while y <= maxy * ky:
            x = minx * kx + (sp / 2 if j % 2 else 0)
            while x <= maxx * kx:
                p = Point(x / kx, y / ky)
                if paris.contains(p):
                    pts.append(p)
                x += sp
            y += dy; j += 1
        return pts
    lo, hi = 0.20, 0.40
    best = None
    for _ in range(60):
        mid = (lo + hi) / 2
        pts = make(mid)
        if best is None or abs(len(pts) - n_target) < abs(len(best[1]) - n_target):
            best = (mid, pts)
        if len(pts) == n_target:
            break
        if len(pts) > n_target:
            lo = mid
        else:
            hi = mid
    sp, pts = best
    out = []
    for p in pts:
        a = next((k for k, g in polys.items() if g.contains(p)), None)
        out.append((p.y, p.x, a))
    return out, sp, paris


def point_time(pt, dist, st, line_at, dest):
    best = KW * (hav(pt, TERMINALS[dest]['xy']) * WALK_MIN_PER_KM + 1.0)   # walk all the way
    for s in line_at:
        dd = hav(pt, (st[s]['latitude'], st[s]['longitude']))
        if dd <= MAX_WALK_KM and ('S', s) in dist:
            t = KW * dd * WALK_MIN_PER_KM + dist[('S', s)]
            if t < best:
                best = t
    return best


def run_points(pts):
    G0, st, line_at = build(False)                      # today's network: metro, RER, tram
    G31, st31, la31 = build(False, regional=True)       # 2031 network: adds suburban rail and lines 15, 16, 17
    G31p, st31p, la31p = build(True, regional=True)     # 2031 network plus programme regional tunnels calling at Pleyel
    D0 = {k: times_to(G0, k) for k in TERMINALS}
    D31 = times_to(G31, 'Pleyel')
    D31p = times_to(G31p, 'Pleyel', True)
    rows = []
    for i, (lat, lon, arr) in enumerate(pts):
        r = {'id': i + 1, 'lat': round(lat, 6), 'lon': round(lon, 6), 'arr': arr}
        for k in TERMINALS:
            r['t_' + k] = round(point_time((lat, lon), D0[k], st, line_at, k), 2)
        r['t_Pleyel_2031'] = round(min(point_time((lat, lon), D31, st31, la31, 'Pleyel'), r['t_Pleyel']), 2)
        r['t_Pleyel_prog'] = round(min(point_time((lat, lon), D31p, st31p, la31p, 'Pleyel'), r['t_Pleyel_2031']), 2)
        rows.append(r)
    return rows


if __name__ == '__main__':
    pts, spacing, paris = grid_points(1000)
    RUNS = (('', (1.0, 1.0, 1.0)), ('_weighted', (2.0, 1.5, 1.0)))
    if len(sys.argv) > 2 and sys.argv[1] == 'comfort':
        RUNS = (('_comfort', (2.0, 1.5, float(sys.argv[2]))),)   # metro and RER riding counted heavier than a seat on a main-line train
    for tag, (kw, kq, kr) in RUNS:
        set_weights(kw, kq, kr)
        rows = run_points(pts)
        with open(f'{OUT}/points{tag}.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)
    json.dump({'spacing_km': spacing, 'n': len(pts), 'area_km2': paris.area * 111.32 * math.cos(math.radians(48.86)) * 110.57},
              open(f'{OUT}/grid.json', 'w'))
    print('points', len(pts), 'spacing km', round(spacing, 4))
