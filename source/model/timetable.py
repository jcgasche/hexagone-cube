"""A pulse timetable for the three stations: the minute at which every high-speed train arrives and leaves, in one hour at full
capacity, chosen so that passengers crossing Paris wait as little as possible, with the platforms and tunnels of the project.

    python3 model/timetable.py        # -> model/outputs/timetable.json and src/sections/timetable/data.json (about two minutes)

Run after nordest.py (it reads the traffic results). Every figure that is not from the model or a source is marked ASSUMPTION.

How it works
- Trains run on six routes, each way: Atlantic to the north or east by Montparnasse and Nord-Est, south-east to the north or east by
  Gare de Lyon and Nord-Est, Atlantic to south-east by the direct link. The number of trains on each route is the model's service plan
  with the southern lines full (nordest.HOUR_FULL); a pattern that repeats every P minutes holds P/60 of them.
- A train stands STOP_MIN minutes at each of its two Paris stations, plus any extra minutes the timetable gives it to hold a connection.
- Rules: at a station, platforms are dedicated by direction (three tracks each way); a track takes a train, then CLEAR_MIN minutes
  before the next; on each side of a station two trains arrive, or two leave, at least HEADWAY minutes apart, because each side is
  reached by one tunnel track.
- A passenger crossing Paris arrives on any train of their line and leaves on the first train that takes them to their line, by their
  own train or after one change, whichever leaves Paris first. Changes take CHANGE_SAME minutes between trains going the same way
  and CHANGE_OTHER minutes to the other side of the station.
- Measure: minutes from the arrival at the first Paris station to the departure from the last one, averaged over passengers crossing
  Paris, weighted by the share of each pair of lines (estimate.PSH), plus the extra minutes that Paris passengers sit through when a
  train is held, weighted by their number.
- The search (simulated annealing, fixed seed) moves the minutes of the trains and the extra stops; it is run for patterns that repeat
  every 10, 20 and 60 minutes, and against timetables drawn at random within the same rules.
"""
import json, math, os, random
import nordest as N
from estimate import PSH

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, '..', 'src', 'sections', 'timetable')

# ------------------------------------------------------------------ inputs
STOP = N.STOP_MIN                     # minutes a train stands at a platform (model, 4)
CLEAR = N.CLEAR_MIN                   # minutes from a departure to the next arrival on the same track (model, 3)
TRACKS = N.TRACKS_PER_DIRECTION       # platform tracks each way at each station (model, 3)
HEADWAY = 3                           # minutes between two trains entering, or two leaving, one side of a station (ASSUMPTION:
                                      # about what the south-east line needs for 16 trains an hour; 2.5 and 4 are tested)
CHANGE_SAME, CHANGE_OTHER = 4, 6      # minutes for a change between trains going the same way, and to the other direction (ASSUMPTION;
                                      # Zürich sells 4 across one platform and uses 7 as the standard)
EXTRA_MAX = 3                         # most extra minutes a train may be held at one stop
LONDON_PRE = 10                       # minutes the London track at Nord-Est is closed off before a train to London arrives, so that passengers
                                      # checked in the control hall wait on the sealed platform and board in a normal stop (ASSUMPTION)
LONDON_TRACK = 3                      # the Nord-Est track, on the side of trains to the north, that is closed off for London departures
# run times between the stations, without the stop. The model's rides include a stop of STOP minutes (nordest.TH).
# A check from the length of each tunnel: start, run at 100 km/h, stop; 0.4 m/s2 to start, 0.5 m/s2 to brake, 7% margin (ASSUMPTION).
V, ACC, BRK, MARGIN = 100 / 3.6, 0.4, 0.5, 1.07
def technical(km):
    d = km * 1000; da, db = V * V / (2 * ACC), V * V / (2 * BRK)
    t = (V / ACC + V / BRK + (d - da - db) / V) if d > da + db else 2 * math.sqrt(d / (ACC / 2 + ACC * ACC / (2 * BRK)))
    return t * MARGIN / 60
KM = {'M': N.CORRIDOR_KM['nemont'], 'L': N.CORRIDOR_KM['nelyon'], 'LM': N.LINK_KM}
TECH = {k: technical(v) for k, v in KM.items()}
MODEL_RUN = {k: N.TH[k] - STOP for k in N.TH}                                  # 7, 6 and 2 minutes
RUN = {k: max(MODEL_RUN[k], math.ceil(TECH[k] - 1e-9)) for k in N.TH}         # the link: 2 in the model is below the 4.3 a start-to-stop needs

# lines: A Atlantic (Montparnasse), S south-east (Gare de Lyon), N north, E east (both at Nord-Est)
LINE_OF = {'Montparnasse': 'A', 'Lyon': 'S', 'Nord': 'N', 'Est': 'E'}
PAIR = {}
for (a, b), v in PSH.items(): PAIR[frozenset((LINE_OF[a], LINE_OF[b]))] = v        # share of the passengers crossing Paris, by pair of lines
STN = ('NE', 'LY', 'MP')
# routes: first station and side, second station and side, run, the line it comes from and goes to ('NE*': north or east, by train).
# Sides: 'in' = trains coming from the station's own outer line (MP: from the Atlantic; LY: from the south-east; NE: from the north
# or east), 'out' = trains leaving towards it. Three tracks on each side.
ROUTES = {
    'AN': (('MP', 'in'), ('NE', 'out'), 'M', 'A', 'NE*'),
    'NA': (('NE', 'in'), ('MP', 'out'), 'M', 'NE*', 'A'),
    'SN': (('LY', 'in'), ('NE', 'out'), 'L', 'S', 'NE*'),
    'NS': (('NE', 'in'), ('LY', 'out'), 'L', 'NE*', 'S'),
    'AS': (('MP', 'in'), ('LY', 'out'), 'LM', 'A', 'S'),
    'SA': (('LY', 'in'), ('MP', 'out'), 'LM', 'S', 'A'),
}
SF = N.service(N.HOUR_FULL)['flows']
HOUR = {'AN': SF['Atlantic to north'] + SF['Atlantic to east'], 'SN': SF['Southeast to north'] + SF['Southeast to east'],
        'AS': SF['Atlantic to southeast, by the direct link']}
HOUR.update({'NA': HOUR['AN'], 'NS': HOUR['SN'], 'SA': HOUR['AS']})               # 6, 6, 9 trains an hour each way
EAST = {'AN': SF['Atlantic to east'], 'SN': SF['Southeast to east']}; EAST.update({'NA': EAST['AN'], 'NS': EAST['SN']})   # of them, to or from the east

# who sits through an extra minute at a stop: passengers crossing Paris (counted in the measure) and Paris passengers riding between
# the two stops, those whose quicker station is the train's second one (inbound) or first one (outbound): derived from the 1,000 points.
PTS = N.DATA['clock'][0]
def t_of(t, st): return min(t['Nord'], t['Est']) if st == 'NE' else t['Lyon'] if st == 'LY' else t['Montparnasse']
RIDE_SHARE = {r: sum(t_of(t, ROUTES[r][1][0]) < t_of(t, ROUTES[r][0][0]) for t in PTS) / len(PTS) for r in ROUTES}
NO = json.load(open(os.path.join(HERE, 'outputs', 'nordest.json')))
Y = NO['yearly']
PARIS_TRIPS = N.HS_TERMINALS - 2 * Y['conn_base'] + Y['tgv_access_journeys']     # million a year, with the project
CROSS_TRIPS = Y['conn_base'] + Y['tgv_conn_journeys']
RATIO = PARIS_TRIPS / CROSS_TRIPS                                               # about 15 Paris passengers for one crossing Paris


# ------------------------------------------------------------------ one timetable
class Pattern:
    """Trains of one pattern repeating every P minutes; each slot has a first arrival minute, extra minutes at its two stops and,
    for routes to or from the north and east, which of the two lines it serves in each repetition of the hour."""
    def __init__(self, P, rng, hour=None, D=None):
        self.P, self.R, self.D = P, 60 // P, STOP if D is None else D
        hour = hour or HOUR
        self.slots = []
        for r in ROUTES:
            n = hour[r] * P / 60
            assert abs(n - round(n)) < 1e-9, (r, P)
            for i in range(round(n)): self.slots.append({'r': r, 't': rng.randrange(P), 'e': [0, 0]})
        # labels: north or east for each repetition of each slot on the routes to or from Nord-Est
        self.lab = {}
        for r in ('AN', 'NA', 'SN', 'NS'):
            cells = [(i, k) for i, s in enumerate(self.slots) if s['r'] == r for k in range(self.R)]
            east = round(EAST[r] * len(cells) / hour[r]) if hour is HOUR else round(len(cells) / 3)
            rng.shuffle(cells)
            for j, c in enumerate(cells): self.lab[c] = 'E' if j < east else 'N'

    def copy(self):
        q = Pattern.__new__(Pattern); q.P, q.R, q.D = self.P, self.R, self.D
        q.slots = [{'r': s['r'], 't': s['t'], 'e': list(s['e'])} for s in self.slots]; q.lab = dict(self.lab); return q

    def trains(self):
        out = []
        # London trains: one an hour each way, on the first south-east to north path of the hour (Marseille or Lyon to London) and
        # the first north to south-east path (London to Lyon or Marseille). Towards London the train stops at Nord-Est on the one
        # track that can be closed off for border checks, closed LONDON_PRE minutes before it arrives; from London it stops as any other.
        # The train keeps the minutes of its path: a longer stop would push its departure into the path of the next train.
        ldn = set()
        for r in ('SN', 'NS'):
            cells = sorted(c for c, v in self.lab.items() if v == 'N' and self.slots[c[0]]['r'] == r)
            if cells: ldn.add(cells[0])
        for i, s in enumerate(self.slots):
            (s1, d1), (s2, d2), leg, frm, to = ROUTES[s['r']]
            for k in range(self.R):
                lab = self.lab.get((i, k)); london = (i, k) in ldn
                a1 = s['t'] + k * self.P; dp1 = a1 + self.D + s['e'][0]; a2 = dp1 + RUN[leg]; dp2 = a2 + self.D + s['e'][1]
                out.append({'r': s['r'], 'slot': i, 'rep': k, 'from': lab if frm == 'NE*' else frm, 'to': lab if to == 'NE*' else to, 'svc': (i, lab), 'london': london,
                            'stops': [(s1, d1, a1, dp1), (s2, d2, a2, dp2)], 'e': [x + self.D - STOP for x in s['e']]})
        return out


def gaps_short(times, need):
    """Minutes missing to keep `need` between successive times on a 60-minute circle."""
    if len(times) < 2: return 0.0
    ts = sorted(x % 60 for x in times); miss = 0.0
    for i in range(len(ts)):
        g = (ts[(i + 1) % len(ts)] - ts[i]) % 60 if i + 1 < len(ts) else ts[0] + 60 - ts[i]
        if g < need: miss += need - g
    return miss


def overlap_excess(iv):
    """Train-minutes above the number of tracks, for occupations [a, b) on a 60-minute circle."""
    occ = [0] * 60
    for a, b in iv:
        for m in range(int(a), int(math.ceil(b))): occ[m % 60] += 1
    return sum(max(0, o - TRACKS) for o in occ)


def penalty(trs, headway=None):
    hw = HEADWAY if headway is None else headway
    arr, dep, occ = {}, {}, {}
    for t in trs:
        for st, side, a, d in t['stops']:
            k = (st, side); arr.setdefault(k, []).append(a); dep.setdefault(k, []).append(d); occ.setdefault(k, []).append((a - (LONDON_PRE if lon(t, st, side) else 0), d + CLEAR))
    return sum(gaps_short(arr[k], hw) + gaps_short(dep[k], hw) + overlap_excess(occ[k]) for k in arr)


def crossing_line(trs, cs=None, co=None):
    """The easy reading: the passenger takes the first train to their line, whatever its destination on that line. Average minutes in
    Paris, weighted by pair of lines."""
    cs = CHANGE_SAME if cs is None else cs; co = CHANGE_OTHER if co is None else co
    by_line, leave = {}, {}
    for t in trs:
        by_line.setdefault(t['from'], []).append(t)
        (s1, d1, a1, p1), (s2, d2, a2, p2) = t['stops']
        leave.setdefault((s1, t['to']), []).append((p1, d1, p2 - p1)); leave.setdefault((s2, t['to']), []).append((p2, d2, 0))
    total = 0.0
    for X, lst in by_line.items():
        for Yl in LINES:
            if Yl == X: continue
            w = PAIR[frozenset((X, Yl))] / 2 / len(lst)
            for t in lst:
                (s1, d1, a1, p1), (s2, d2, a2, p2) = t['stops']
                best = p2 - a1 if t['to'] == Yl else 1e9
                for st, side, a in ((s1, d1, a1), (s2, d2, a2)):
                    for dp, sd, rest in leave.get((st, Yl), ()):
                        need = a + (cs if sd == side else co)
                        best = min(best, need + (dp - need) % 60 + rest - a1)
                total += w * best
    return total


LINES = ('A', 'S', 'N', 'E')
def change(t, u, cs, co):
    """Minutes from train t reaching its first Paris station to train u leaving its last one, with one change where both call;
    u is waited for until its next departure (each train is a service of its own, running once an hour). Also the wait itself."""
    a1 = t['stops'][0][2]; best, wait, at = 1e9, 0.0, None
    for st, side, a, _ in t['stops']:
        for j, (su, sdu, au, du) in enumerate(u['stops']):
            if su != st: continue
            need = a + (cs if sdu == side else co); dd = need + (du - need) % 60
            out = dd + (u['stops'][1][3] - du if j == 0 else 0) - a1
            if out < best: best, wait, at = out, dd - need, st
    return best, wait, at


def crossing(trs, cs=None, co=None, detail=False):
    """Average minutes in Paris of a passenger crossing it. A service is one path of the pattern to one line: it runs every P minutes
    (or less often where the path serves the north and the east in turn), and a passenger waits for the next run of the service of
    their destination. On the pairs of lines with direct trains, a share DIRECT_SHARE of passengers find one for their trip and stay
    on board; the others, and everyone between the north and the east, change once, from the train they came on to the next train of
    the service they need. Every train and every service count alike."""
    cs = CHANGE_SAME if cs is None else cs; co = CHANGE_OTHER if co is None else co
    frm, svc = {}, {}
    for t in trs: frm.setdefault(t['from'], []).append(t); svc.setdefault((t['to'], t['svc']), []).append(t)
    total, per, dist = 0.0, {}, []
    for X in LINES:
        for Yl in LINES:
            if Yl == X: continue
            w = PAIR[frozenset((X, Yl))] / 2
            dts = [t for t in frm[X] if t['to'] == Yl]
            ds = N.DIRECT_SHARE if dts else 0.0
            dv = [t['stops'][1][3] - t['stops'][0][2] for t in dts]
            ch = []
            for (yl, key), runs in svc.items():
                if yl != Yl: continue
                for t in frm[X]:
                    if t['svc'] == key: continue
                    ch.append((min(change(t, u, cs, co) for u in runs), len(runs)))
            n = sum(k for _, k in ch)
            cv = sum(c[0] * k for c, k in ch) / n
            val = (ds * sum(dv) / len(dv) if dts else 0.0) + (1 - ds) * cv
            total += w * val
            if detail:
                per[X + Yl] = {'share': w, 'direct_share': ds, 'direct': sum(dv) / len(dv) if dv else None, 'change': cv,
                               'wait': sum(c[1] * k for c, k in ch) / n, 'avg': val, 'direct_trains': len(dts)}
                dist += [(v, w * ds / len(dv), 'direct') for v in dv] + [(c[0], w * (1 - ds) * k / n, 'change', c[1]) for c, k in ch]
    return (total, per, dist) if detail else total


def held_cost(trs):
    """Extra minutes Paris passengers sit through, per passenger crossing Paris (the measure's unit)."""
    n = len(trs)
    return sum(RATIO * RIDE_SHARE[t['r']] * (t['e'][0] + t['e'][1]) / (2 * n) for t in trs)


def mean_wait(times):
    """Average minutes from a random moment to the next of these times, on a 60-minute circle (half the gap, weighted by gap)."""
    ts = sorted(x % 60 for x in times)
    if not ts: return None
    gaps = [(ts[(i + 1) % len(ts)] - ts[i]) % 60 or 60 for i in range(len(ts))] if len(ts) > 1 else [60]
    return sum(g * g for g in gaps) / 120


LINE_WEIGHT = {'A': N.HOUR_FULL['Atlantic'], 'S': N.HOUR_FULL['Southeast'], 'N': N.HOUR_FULL['North'], 'E': N.HOUR_FULL['East']}   # Paris traffic of each line, taken in proportion to its trains (ASSUMPTION)
def evenness(trs, cs=None, co=None):
    """How evenly the hour is spread. For each line: the average wait, from a random minute, for the next train leaving Paris to it and
    for the next train arriving from it (Paris passengers). For each pair of lines with direct trains: the average wait for the next
    direct train (passengers crossing Paris who pick a direct train). Between the north and the east: minutes in Paris with one change
    at Nord-Est to the next train to the other line."""
    cs = CHANGE_SAME if cs is None else cs; co = CHANGE_OTHER if co is None else co
    line = {}
    for Xl in LINES:
        dep = [t['stops'][1][3] for t in trs if t['to'] == Xl]; arr = [t['stops'][0][2] for t in trs if t['from'] == Xl]
        line[Xl] = {'out': mean_wait(dep), 'in': mean_wait(arr), 'trains': len(dep)}
    pair = {}
    for X in LINES:
        for Yl in LINES:
            if X == Yl or frozenset((X, Yl)) == frozenset(('N', 'E')): continue
            pair[X + Yl] = mean_wait([t['stops'][0][2] for t in trs if t['from'] == X and t['to'] == Yl])
    ne = []
    for X, Yl in (('N', 'E'), ('E', 'N')):
        outs = [t for t in trs if t['to'] == Yl]
        for t in (t for t in trs if t['from'] == X):
            st, side, a, _ = t['stops'][0]
            best = min(need + (u['stops'][1][3] - need) % 60 - a for u in outs for need in [a + (cs if u['stops'][1][1] == side else co)])
            ne.append(best)
    wl = sum(LINE_WEIGHT.values())
    paris = sum(LINE_WEIGHT[k] / wl * (v['out'] + v['in']) / 2 for k, v in line.items())
    cross = sum(PAIR[frozenset(k)] / 2 * v for k, v in pair.items()) / sum(PAIR[frozenset(k)] / 2 for k in pair)
    return {'line': line, 'pair': pair, 'ne_change': sum(ne) / len(ne), 'paris_wait': paris, 'direct_wait': cross,
            'score': paris + cross + W_NE * sum(ne) / len(ne)}


W_NE, W_SPARE = 0.2, 0.3      # weight of the north-east change (6% of passengers crossing Paris) and of each path left for regional express
                              # trains, against one minute of average wait (ASSUMPTION: a compromise found by trial; see the annex)


def score(p, **kw):
    trs = p.trains(); pen = penalty(trs, kw.get('headway'))
    if kw.get('goal') == 'even':                                        # 4-minute stops, trains spread through the hour, paths kept for regional trains
        return evenness(trs)['score'] - W_SPARE * spare_count(trs) + 50 * pen, pen
    x = crossing(trs, kw.get('cs'), kw.get('co'))
    return x + held_cost(trs) + 50 * pen, pen


# ------------------------------------------------------------------ search
def anneal(P, seed, steps, feasible_only=False, hour=None, D=None, **kw):
    rng = random.Random(seed)
    p = Pattern(P, rng, hour, D)
    if not feasible_only:                                              # start from a timetable that keeps the rules, then never break them
        p = anneal(P, seed, 50000, feasible_only=True, hour=hour, D=D, headway=kw.get('headway'))
    def f(q):
        if feasible_only:                                              # only the rules: no need to measure passengers' time
            pen = penalty(q.trains(), kw.get('headway')); return 50 * pen, pen
        s, pen = score(q, **kw)
        return s, pen
    cur, pen = f(p); best, bestv = p.copy(), cur
    T0, T1 = 6.0, 0.02
    for i in range(steps):
        T = T0 * (T1 / T0) ** (i / steps)
        q = p.copy(); mv = rng.random()
        if mv < 0.6:
            s = rng.choice(q.slots); s['t'] = (s['t'] + rng.choice((-3, -2, -1, 1, 2, 3))) % P
        elif mv < 0.85 and not feasible_only and kw.get('hold', True):
            s = rng.choice(q.slots); j = rng.randrange(2); s['e'][j] = min(EXTRA_MAX, max(0, s['e'][j] + rng.choice((-1, 1))))
        else:
            ks = list(q.lab)
            a = rng.choice(ks); same = [k for k in ks if q.slots[k[0]]['r'] == q.slots[a[0]]['r'] and q.lab[k] != q.lab[a]]
            if not same: continue
            b = rng.choice(same); q.lab[a], q.lab[b] = q.lab[b], q.lab[a]
        v, pn = f(q)
        if pn > 0 and not feasible_only: continue
        if v <= cur or rng.random() < math.exp((cur - v) / T):
            p, cur, pen = q, v, pn
            if v < bestv: best, bestv = p.copy(), v
        if feasible_only and pen == 0: return p
    return best


CACHE = os.environ.get('TT_CACHE')           # a file to keep solved patterns between runs while working on the page (optional)
def solve(P, seeds, steps, hour=None, D=None, **kw):
    key = repr((P, list(seeds), steps, sorted((hour or {}).items()), D, sorted(kw.items()), RUN))
    if CACHE:
        import pickle
        store = pickle.load(open(CACHE, 'rb')) if os.path.exists(CACHE) else {}
        if key in store: return store[key]
    p = _solve(P, seeds, steps, hour, D, **kw)
    if CACHE:
        store = pickle.load(open(CACHE, 'rb')) if os.path.exists(CACHE) else {}
        store[key] = p; pickle.dump(store, open(CACHE, 'wb'))
    print('  solved', P, D, kw, 'none' if p is None else round(score(p, **kw)[0], 2), flush=True)
    return p


def _solve(P, seeds, steps, hour=None, D=None, **kw):
    best = None
    for sd in seeds:
        p = anneal(P, sd, steps, hour=hour, D=D, **kw)
        v, pen = score(p, **kw)
        if pen == 0 and tracks(p.trains(), strict=False) is None: pen = 1      # the load fits but no track plan does
        if pen == 0 and (best is None or v < best[0]): best = (v, p)
    return best[1] if best else None


def summary(p, **kw):
    trs = p.trains(); x, per, dist = crossing(trs, kw.get('cs'), kw.get('co'), detail=True); ev = evenness(trs, kw.get('cs'), kw.get('co'))
    wt = sum(d[1] for d in dist); chg = [d for d in dist if d[2] == 'change']; wc = sum(d[1] for d in chg)
    within = lambda m: sum(d[1] for d in dist if d[0] <= m + 1e-9) / wt
    held = sum(t['e'][0] + t['e'][1] for t in trs)
    pairs = {}
    for k, v in per.items():
        q = pairs.setdefault(''.join(sorted(k)), {'share': 0.0, 'avg': 0.0, 'change': 0.0, 'wait': 0.0, 'direct': v['direct'], 'direct_share': v['direct_share']})
        q['share'] += v['share']; q['avg'] += v['avg'] / 2; q['change'] += v['change'] / 2; q['wait'] += v['wait'] / 2
    return {'cross': x, 'line': crossing_line(trs, kw.get('cs'), kw.get('co')), 'held_cost': held_cost(trs), 'score': x + held_cost(trs),
            'change_avg': sum(d[0] * d[1] for d in chg) / wc, 'wait_avg': sum(d[3] * d[1] for d in chg) / wc,
            'change_wave': sum(d[1] for d in chg if d[3] <= 10 + 1e-9) / wc,
            'within20': within(20), 'within30': within(30), 'held_minutes': held, 'held_trains': sum(1 for t in trs if t['e'][0] + t['e'][1] > 0),
            'trains': len(trs), 'pairs': pairs, 'penalty': penalty(trs, kw.get('headway')), 'even': ev,
            'paris_wait': ev['paris_wait'], 'direct_wait': ev['direct_wait'], 'ne_change': ev['ne_change']}


def lon(t, st, side): return bool(t.get('london')) and t['to'] == 'N' and st == 'NE' and side == 'out'


def tracks(trs, strict=True):
    """Platform track of each stop (1 to 3 on each side): a track holds a train from its arrival to CLEAR minutes after it leaves,
    and the hour repeats, so occupations are arcs on a 60-minute circle; found by a small exhaustive search."""
    out = {}
    def clash(x, y):
        a1, b1 = x[0] % 60, x[0] % 60 + x[1]; a2, b2 = y[0] % 60, y[0] % 60 + y[1]
        return any(a1 < b2 + k and a2 + k < b1 for k in (-60, 0, 60))
    for st in STN:
        for side in ('in', 'out'):
            evs = sorted([(a - (LONDON_PRE if lon(t, s_, sd) else 0), (d + CLEAR) - a + (LONDON_PRE if lon(t, s_, sd) else 0), id(t), j, lon(t, s_, sd)) for t in trs for j, (s_, sd, a, d) in enumerate(t['stops']) if s_ == st and sd == side], key=lambda e: (not e[4], e[0] % 60))
            asg = [0] * len(evs)
            def place(i):
                if i == len(evs): return True
                for k in ([LONDON_TRACK] if evs[i][4] else range(1, TRACKS + 1)):
                    if not evs[i][4] and k > max(asg[:i] + [0, LONDON_TRACK if any(e[4] for e in evs) else 0]) + 1: break   # open tracks in order
                    if all(not (asg[j] == k and clash(evs[i], evs[j])) for j in range(i)):
                        asg[i] = k
                        if place(i + 1): return True
                asg[i] = 0
                return False
            if not place(0):
                if strict: raise RuntimeError(f'no track plan at {st} {side}')
                return None
            for e, k in zip(evs, asg): out[(e[2], e[3])] = k
    return out


def export(p, name):
    trs = p.trains(); tk = tracks(trs)
    rows = []
    for t in trs:
        rows.append({'route': t['r'], 'from': t['from'], 'to': t['to'], 'slot': t['slot'], 'rep': t['rep'], 'london': t.get('london', False),
                     'stops': [{'st': st, 'side': sd, 'arr': a % 60, 'dep': d % 60, 'arr_abs': a, 'dep_abs': d, 'track': tk[(id(t), j)], 'held': t['e'][j]}
                               for j, (st, sd, a, d) in enumerate(t['stops'])]})
    rows.sort(key=lambda r: (r['stops'][0]['arr_abs'] % 60, r['route']))
    return {'name': name, 'period': p.P, 'trains': rows}


def turn_slot(p):
    """Minutes at which the sixteenth south-east train, which has no partner, can arrive at Gare de Lyon, run to Nord-Est, stand there
    REVERSE + 1 minutes on a northbound track to change ends, and go back to Gare de Lyon and the south-east line, within the rules."""
    trs = p.trains(); ok = []
    for m in range(60):
        a1, p1 = m, m + STOP; a2 = p1 + RUN['L']; p2 = a2 + N.REVERSE + 1; a3 = p2 + RUN['L']; p3 = a3 + STOP
        up = {'r': 'SN', 'e': [0, 0], 'stops': [('LY', 'in', a1, p1), ('NE', 'out', a2, p2)]}
        if penalty(trs + [up]) > 0: continue
        sides = {}
        for t in trs:
            for st, sd, a, d in t['stops']: sides.setdefault((st, sd), []).append((a, d))
        dep_s = [d for a, d in sides[('NE', 'in')]] + [p2]                        # it leaves southwards among the trains from the north
        ly = sides[('LY', 'out')] + [(a3, p3)]
        if gaps_short(dep_s, HEADWAY) + gaps_short([a for a, d in ly], HEADWAY) + gaps_short([d for a, d in ly], HEADWAY) + overlap_excess([(a, d + CLEAR) for a, d in ly]) == 0:
            ok.append(m)
    return ok


def spare_count(trs):
    n = 0
    for st in STN:
        for side in ('in', 'out'):
            ts = sorted(s[2] % 60 for t in trs for s in t['stops'] if s[0] == st and s[1] == side)
            n += sum(max(0, int(((ts[(i + 1) % len(ts)] - ts[i]) % 60 or 60) // HEADWAY) - 1) for i in range(len(ts)))
    return n


def spare_paths(p):
    """Paths left on each side of each station for other trains (regional express trains share the first pair of tunnels):
    in each gap between two high-speed trains, one more train fits every HEADWAY minutes."""
    trs = p.trains(); out = {}
    for st in STN:
        for side in ('in', 'out'):
            ts = sorted(s[2] % 60 for t in trs for s in t['stops'] if s[0] == st and s[1] == side)
            gaps = [(ts[(i + 1) % len(ts)] - ts[i]) % 60 or 60 for i in range(len(ts))]
            out[st + ' ' + side] = {'tgv': len(ts), 'spare': sum(max(0, int(g // HEADWAY) - 1) for g in gaps)}
    return out


# the most trains the three stations can take: the southern lines at the limits of their lines (15 Atlantic, 15 of the 16 south-east,
# as in the full hour), and Nord-Est filled to 18 trains an hour each way from the north and east (12 north, 6 east: ASSUMPTION, the
# capacity of the northern and eastern lines is not known to this study); 6 Atlantic to south-east trains by the link.
MAX_HOUR = {'AN': 9, 'NA': 9, 'SN': 9, 'NS': 9, 'AS': 6, 'SA': 6}
def ceiling():
    """Trains an hour one side of a station can take: one every HEADWAY minutes on its tunnel track, and TRACKS tracks each freed
    for the next train STOP + CLEAR minutes after a train arrives (STOP and 5 minutes)."""
    return {'headway': 60 / HEADWAY, 'tracks_stop4': TRACKS * 60 / (STOP + CLEAR), 'tracks_stop5': TRACKS * 60 / (5 + CLEAR),
            'two_tracks_stop4': 2 * 60 / (STOP + CLEAR), 'two_tracks_stop5': 2 * 60 / (5 + CLEAR)}


# regional express trains (TER and Intercités, not suburban) at today's terminals in the busiest hour, peak direction: own count from
# the SNCF timetable open data (GTFS published 13 October 2026, Tuesday 17 November 2026); Gare de Lyon counted with Bercy
TER_PEAK = {'Nord': 11, 'Est': 3, 'Montparnasse': 6, 'Lyon': 3}
def platforms(out):
    """Platform tracks for the trains the first pair of tunnels can bring. Each side of a station is reached by one tunnel track,
    so all the trains of a side, high-speed and regional, share one train every HEADWAY minutes: TUNNEL an hour in theory, and the
    solved timetables show what fits in practice. Tracks a side needs follow the platform rule of the report (nordest.PER_TRACK)."""
    sides = {'NE': ('Paris Nord-Est', out['max_hour']['AN'] + out['max_hour']['SN']),
             'MP': ('Montparnasse', out['max_hour']['AN'] + out['max_hour']['AS']),
             'LY': ('Gare de Lyon', out['max_hour']['SN'] + out['max_hour']['AS'])}
    tunnel = 60 / HEADWAY
    # what fits in practice: a pattern with the same number of trains on every side, every 20 minutes, on TRACKS tracks each way
    practical, check = None, {}
    for n in (9,):                                                 # 18 trains a side (20 would leave no slack at all)
        hour = {r: n for r in ROUTES}
        q = next((p for p in (anneal(20, 900 + sd, 60000, feasible_only=True, hour=hour) for sd in range(3))
                  if penalty(p.trains()) == 0 and tracks(p.trains(), strict=False) is not None), None)
        check[2 * n] = q is not None
        if q is not None: practical = 2 * n
    # regional peak a side, with regional trains running through: from the north half to each southern station, from the east to Lyon
    ter = {'NE': TER_PEAK['Nord'] + TER_PEAK['Est'], 'MP': max(TER_PEAK['Montparnasse'], TER_PEAK['Nord'] / 2),
           'LY': max(TER_PEAK['Lyon'], TER_PEAK['Nord'] / 2 + TER_PEAK['Est'])}
    tgv = {'today': {'NE': N.HOUR_TODAY['North'] + N.HOUR_TODAY['East'], 'MP': N.HOUR_TODAY['Atlantic'], 'LY': N.HOUR_TODAY['Southeast']},
           'full': {'NE': out['inputs']['hour']['AN'] + out['inputs']['hour']['SN'], 'MP': out['inputs']['hour']['AN'] + out['inputs']['hour']['AS'],
                    'LY': out['inputs']['hour']['SN'] + out['inputs']['hour']['AS']}}
    per = {D: 60 * N.UTIL / (D + CLEAR) for D in (4, 5)}
    rows = {}
    for k, (name, _) in sides.items():
        r = {'name': name, 'ter_peak': ter[k]}
        for h in ('today', 'full'):
            r[h] = {'tgv': tgv[h][k], 'demand': tgv[h][k] + ter[k], 'room': practical - tgv[h][k], 'short': max(0, tgv[h][k] + ter[k] - practical)}
        r['tracks_side'] = {D: math.ceil(practical / per[D] - 1e-9) for D in per}
        r['tracks_side_exact'] = {D: practical / per[D] for D in per}
        rows[k] = r
    # cost of the platform layouts, with the model's own cost function
    base = N.cost()
    def layout(hs, ter):
        L = {**N.LAYOUT, 'stations': {n: {'hs': hs, 'ter': ter, 'sub': v['sub']} for n, v in N.LAYOUT['stations'].items()}}
        return N.cost(L=L)
    alt8, alt6 = layout(8, 0), layout(6, 0)
    first = {n: v['hs'] + v['ter'] for n, v in N.LAYOUT['stations'].items()}
    return {'tunnel': tunnel, 'practical': practical, 'check': check, 'per_track': per, 'ter_peak': TER_PEAK, 'sides': rows,
            'layouts': {'report': {'tracks': first, 'platform_m': base['platform_total'], 'total': base['total']},
                        'shared8': {'tracks': 8, 'platform_m': alt8['platform_total'], 'total': alt8['total']},
                        'shared6': {'tracks': 6, 'platform_m': alt6['platform_total'], 'total': alt6['total']}}}


KEYS = ('cross', 'line', 'held_cost', 'score', 'change_avg', 'wait_avg', 'change_wave', 'within20', 'within30', 'paris_wait', 'direct_wait', 'ne_change')
def mean_of(rows): return {k: sum(r[k] for r in rows) / len(rows) for k in KEYS} if rows else None


def random_cases(P, n, hour=None, **kw):
    rows = []
    for sd in range(n):
        q = anneal(P, 1000 + sd, 50000, feasible_only=True, hour=hour, headway=kw.get('headway'))
        if penalty(q.trains(), kw.get('headway')) == 0 and tracks(q.trains(), strict=False) is not None: rows.append(summary(q, **kw))
    r = mean_of(rows)
    if r: r['n'] = len(rows)
    return r


def main():
    quick = os.environ.get('TT_QUICK')
    steps, seeds, nr = (3000, range(1), 6) if quick else (20000, range(4), 30)
    out = {'inputs': {'stop': STOP, 'clear': CLEAR, 'tracks': TRACKS, 'headway': HEADWAY, 'change_same': CHANGE_SAME, 'change_other': CHANGE_OTHER,
                      'extra_max': EXTRA_MAX, 'run': RUN, 'model_run': MODEL_RUN, 'technical': TECH, 'km': KM, 'speed_kmh': V * 3.6, 'acc': ACC, 'brake': BRK, 'margin': MARGIN,
                      'hour': HOUR, 'east': EAST, 'pair_share': {''.join(sorted(k)): v for k, v in PAIR.items()}, 'ride_share': RIDE_SHARE, 'direct_share': N.DIRECT_SHARE,
                      'paris_trips': PARIS_TRIPS, 'cross_trips': CROSS_TRIPS, 'ratio': RATIO, 'reverse': N.REVERSE,
                      'london_pre': LONDON_PRE, 'london_track': LONDON_TRACK}}
    std = {'AN': 6, 'NA': 6, 'SN': 6, 'NS': 6, 'AS': 6, 'SA': 6}                  # the standard busy hour: 12 trains on each southern line
    cases = {}
    even20 = solve(20, seeds, steps, goal='even', hold=False); cases['even20'] = summary(even20)
    even10 = solve(10, seeds, steps, hour=std, goal='even', hold=False); cases['even10'] = summary(even10)
    # the most the stations take: southern lines at their limits, Nord-Est filled to 6 trains each way every 20 minutes
    evenmax = solve(20, seeds, steps, hour=MAX_HOUR, goal='even', hold=False); cases['evenmax'] = summary(evenmax)
    best20 = solve(20, seeds, steps); cases['pulse20'] = summary(best20)
    cases['random20'] = random_cases(20, nr)
    best10 = solve(10, seeds, steps, hour=std); cases['pulse10'] = summary(best10)
    cases['random10'] = random_cases(10, nr, hour=std)
    # longer stops for everyone, as in a Swiss node: what passengers crossing Paris gain, what Paris passengers lose
    frontier = {}
    for D in range(int(STOP), 10):
        pk = solve(20, seeds[:2], steps * 2 // 3, D=D, hold=False)
        frontier[D] = {k: v for k, v in summary(pk).items() if k in KEYS} if pk else None     # None: no timetable keeps the rules
        if pk is None: break
    # the same search with other rules
    sens = {}
    for name, kw in {'headway 2.5': dict(headway=2.5), 'headway 4': dict(headway=4), 'changes 3 and 5': dict(cs=3, co=5), 'changes 5 and 8': dict(cs=5, co=8)}.items():
        pk = solve(20, seeds[:2], steps * 2 // 3, **kw); rc = random_cases(20, nr // 3, **kw)
        sens[name] = dict(mean_of([summary(pk, **kw)]), random=rc and rc['cross']) if pk else None      # None: no timetable keeps the rules
    keep = RUN['LM']; RUN['LM'] = MODEL_RUN['LM']
    pk = solve(20, seeds[:2], steps * 2 // 3); rc = random_cases(20, nr // 3)
    sens['link at the model time'] = dict(mean_of([summary(pk)]), random=rc and rc['cross']) if pk else None
    RUN['LM'] = keep
    out.update({'cases': cases, 'frontier': frontier, 'sens': sens, 'chosen': export(even20, 'even 20'), 'standard': export(even10, 'even 10'), 'maximum': export(evenmax, 'even 20, most trains'), 'spare_max': spare_paths(evenmax), 'max_hour': MAX_HOUR, 'ceiling': ceiling(),
                'turn_minutes': turn_slot(even20), 'spare': spare_paths(even20), 'spare_standard': spare_paths(even10)})
    out['platforms'] = platforms(json.loads(json.dumps(out)))
    os.makedirs(os.path.join(HERE, 'outputs'), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, 'outputs', 'timetable.json'), 'w'), indent=1)
    os.makedirs(SITE, exist_ok=True)
    json.dump(out, open(os.path.join(SITE, 'data.json'), 'w'), separators=(',', ':'))
    P = lambda v: round(v, 2) if isinstance(v, float) else v
    for k, v in cases.items(): print(k.ljust(10), {a: P(b) for a, b in v.items() if a not in ('pairs', 'even')})
    for k, v in frontier.items(): print('stop', k, v and {a: P(b) for a, b in v.items()})
    for k, v in sens.items(): print('sens', k.ljust(24), v and {a: P(b) for a, b in v.items()})
    print('run', RUN, 'technical', {k: P(v) for k, v in TECH.items()}, 'ratio', P(RATIO), 'turn', out['turn_minutes'], 'spare', out['spare'])


def refresh_platforms():
    """Recompute only the platform analysis from the saved timetables (seconds, no search)."""
    path = os.path.join(HERE, 'outputs', 'timetable.json')
    out = json.load(open(path)); out['platforms'] = platforms(out)
    json.dump(out, open(path, 'w'), indent=1); json.dump(out, open(os.path.join(SITE, 'data.json'), 'w'), separators=(',', ':'))
    print(json.dumps(out['platforms'], indent=1))


if __name__ == '__main__':
    import sys
    if '--platforms' in sys.argv: refresh_platforms()
    else: main()
