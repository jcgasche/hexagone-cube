"""Tests on the real timetable of what could run in the room the new tunnels leave (annex 'parts', block parts.more).

Each test is a network version of model/inputs/networks/ run by model/regiontimes.py against the plan:
  plan_j_all, plan_j_cormeilles, plan_j_ermont   line J trains run on from Saint-Lazare to Nord-Est in the RER F tunnel
  future_cdgx_est                                CDG Express as it opens in 2027, at the surface of Gare de l'Est, with lines 15 to 18 (the plan's reference)
  plan_cdgx_est, plan_cdgx_through               CDG Express ending at Nord-Est, or running on through the RER G tunnel
  plan_cdgx_bd_lyon                              CDG Express through the old RER B and D tunnel to Chatelet and Gare de Lyon

For CDG Express it also counts the changes: the quickest journey of each starting time is followed train by train, and its boardings
and the minutes spent between its first boarding and its arrival off a train (walks and waits at the changes) are kept.

Run from source/:  python3 model/tunnel_room_tests.py --gtfs DIR [--cdg-only | --changes-only]     (about 10 minutes; DIR = the IDFM timetable folder, as for regiontimes.py run)
Writes model/inputs/tunnel_room_tests.json and removes the station-to-station tables it made, so that the chapter on travel times
keeps its own list of versions.
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import regiontimes as RT

NETS = os.path.join(HERE, 'inputs', 'networks'); OUT = os.path.join(HERE, 'inputs', 'tunnel_room_tests.json')
J = {'all': 'plan_j_all', 'cormeilles': 'plan_j_cormeilles', 'ermont': 'plan_j_ermont'}
PEAK = {'all': 25, 'cormeilles': 9, 'ermont': 9}        # trains arriving at Saint-Lazare from 7:30 to 8:30 (IDFM timetable of 3 November 2026)
CDG = {'today': 'future_cdgx_est', 'est': 'plan_cdgx_est', 'through': 'plan_cdgx_through', 'bd_lyon': 'plan_cdgx_bd_lyon'}; AIRPORT = 'X:CDG'
EXAMPLES = (('chatelet', 'Châtelet - Les Halles'), ('montparnasse', 'Gare Montparnasse'), ('lyon', 'Gare de Lyon'), ('defense', 'La Défense'), ('versailles', 'Versailles Chantiers'))
CENTRE = (2.3499, 48.8530); PARIS_KM = 6.0          # Notre-Dame; stations within 6 km stand for Paris inside the ring road


def trains(log, name):
    return next((l for l in log if l.get('name') == name), {})


def compare_rows(A, B, ent):
    """Minutes from and to the airport in version A against version B, each station weighed by its entries of a working day."""
    import numpy as np
    ia, ib = list(A['ids']), list(B['ids']); common = [s for s in ia if s in set(ib)]
    xa = np.array([ia.index(s) for s in common]); xb = np.array([ib.index(s) for s in common])
    i, j = ia.index(AIRPORT), ib.index(AIRPORT); w = np.array([ent.get(s, 0.0) for s in common])
    k = np.array([math.hypot((A['lon'][x] - CENTRE[0]) * 73.0, (A['lat'][x] - CENTRE[1]) * 111.2) for x in xa])
    res = {}
    for zone, mask in (('region', np.ones(len(common), bool)), ('paris', k <= PARIS_KM)):
        res[zone] = {}
        for way, get in (('from', lambda M, x, o: M[o, x]), ('to', lambda M, x, o: M[x, o])):
            a, b = get(A['minutes'], xa, i), get(B['minutes'], xb, j); ok = np.isfinite(a) & np.isfinite(b) & (w > 0) & mask; g = (a - b)[ok]; ww = w[ok]
            res[zone][way] = {'end': round(float((a[ok] * ww).sum() / ww.sum()), 1), 'through': round(float((b[ok] * ww).sum() / ww.sum()), 1), 'gain': round(float((g * ww).sum() / ww.sum()), 2),
                              'share_1': round(float(ww[g >= 1].sum() / ww.sum()), 3), 'gain_of_gainers': round(float((g * ww)[g >= 1].sum() / max(ww[g >= 1].sum(), 1)), 1)}
        res[zone]['gain'] = round((res[zone]['from']['gain'] + res[zone]['to']['gain']) / 2, 2)
        res[zone]['share_1'] = round((res[zone]['from']['share_1'] + res[zone]['to']['share_1']) / 2, 3)
    return res


def changes_scan(net, origins, targets):
    """The quickest journeys from each of 'origins' to each of 'targets' (stations), as the connection scan of regiontimes.py finds them,
    followed train by train: boardings, and seconds not aboard between the first boarding and the arrival. Same starting times, same
    first wait cap, same choice of the starting time as regiontimes.scan. Returns {(origin, target): (boardings, change seconds)}, the
    averages over the starting times."""
    import numpy as np
    taus = np.arange(RT.T0, RT.T1 + RT.LOOK + 1, RT.STEP).astype(np.int32); K = len(taus); KE = int((RT.T1 - RT.T0) // RT.STEP) + 1
    n, hops, foot = net['n'], net['hops'], net['foot']; ntr = max(h[5] for h in hops) + 1; BIG = RT.BIG; win = int(RT.LOOK // RT.STEP) + 1; out = {}
    batch = max(1, 8000 // K)
    for b0 in range(0, len(origins), batch):
        ob = origins[b0:b0 + batch]; R = len(ob) * K
        A = np.full((n, R), BIG, np.int32); Bd = np.zeros((n, R), np.int16); IV = np.zeros((n, R), np.int32); FB = np.full((n, R), BIG, np.int32)
        F = np.zeros((ntr, R), bool); BT = np.zeros((ntr, R), np.int16); IVT = np.zeros((ntr, R), np.int32); BTm = np.zeros((ntr, R), np.int32); FBT = np.zeros((ntr, R), np.int32)
        for oi, o in enumerate(ob):
            sl = slice(oi * K, (oi + 1) * K)
            for i in net['station'][o]:
                A[i, sl] = np.minimum(A[i, sl], taus)
                for j, w in foot[i]: A[j, sl] = np.minimum(A[j, sl], taus + w)
        for dep, _, a, b, arr, tr, pick, drop, wbit in hops:
            f = F[tr]
            if pick:
                can = A[a] <= dep; fresh = can & ~f
                if fresh.any():                                             # boards here: one boarding more, time aboard so far, time of boarding
                    np.copyto(BT[tr], Bd[a] + 1, where=fresh); np.copyto(IVT[tr], IV[a], where=fresh); BTm[tr][fresh] = dep
                    np.copyto(FBT[tr], np.where(FB[a] < BIG, FB[a], dep), where=fresh); f |= can
            if not drop or not f.any(): continue
            new = np.where(f, np.int32(arr), np.int32(BIG)); better = new < A[b]
            if not better.any(): continue
            ivn = IVT[tr] + (arr - BTm[tr])
            for j, nw, bj in [(b, new, better)] + [(j, new + np.int32(w), None) for j, w in foot[b]]:
                bj = nw < A[j] if bj is None else bj
                if bj.any(): np.copyto(A[j], nw, where=bj); np.copyto(Bd[j], BT[tr], where=bj); np.copyto(IV[j], ivn, where=bj); np.copyto(FB[j], FBT[tr], where=bj)
        for t in targets:
            m = np.array(net['station'][t]); sub = A[m]; am = sub.argmin(axis=0); c = np.arange(R)
            arv, bd, iv, fb = sub[am, c], Bd[m][am, c], IV[m][am, c], FB[m][am, c]
            for oi, o in enumerate(ob):
                if o == t: continue
                sl = slice(oi * K, (oi + 1) * K); ar = arv[sl]; jour = np.where(ar < BIG, ar - taus, BIG).astype(float); pk = []
                for k in range(KE):
                    m1 = min(K, k + win); cand = np.where(jour[k:m1] < BIG, jour[k:m1] + np.minimum(taus[k:m1] - taus[k], RT.FIRST_WAIT_CAP), np.inf); pk.append(k + int(cand.argmin()))
                pk = np.array(pk)
                if (jour[pk] >= BIG).any(): continue
                B_ = bd[sl][pk]; out[(o, t)] = (float(B_.mean()), float(np.where(B_ >= 1, ar[pk] - fb[sl][pk] - iv[sl][pk], 0).mean()), float(((B_ - 1) >= 2).mean()))
    return out


def changes(name, gtfs, ent):
    """Changes of the journeys from and to the airport in version 'name', each station weighed by its entries of a working day."""
    import pickle
    trips, S, walks = pickle.load(open(os.path.join(gtfs, '..', 'timetable_%s.pkl' % RT.DAY), 'rb'))
    trips, S, walks, members, log = RT.apply_network(trips, S, walks, RT.read_network(os.path.join(NETS, name + '.json'))); net = RT.build(trips, S, walks, members)
    st = [s for s in sorted(net['station']) if ent.get(s, 0) > 0 and s != AIRPORT and s in S]
    ways = {'from': changes_scan(net, [AIRPORT], st), 'to': changes_scan(net, st, [AIRPORT])}
    km = {s: math.hypot((S[s][1] - CENTRE[0]) * 73.0, (S[s][2] - CENTRE[1]) * 111.2) for s in st}; res = {}
    for zone, keep in (('region', lambda s: True), ('paris', lambda s: km[s] <= PARIS_KM)):
        res[zone] = {}
        for way, d in ways.items():
            rows = [(ent[s], v) for s in st if keep(s) for v in [d.get((AIRPORT, s) if way == 'from' else (s, AIRPORT))] if v]; W = sum(w for w, _ in rows)
            res[zone][way] = {'changes': round(sum(w * max(v[0] - 1, 0) for w, v in rows) / W, 2), 'change_min': round(sum(w * v[1] for w, v in rows) / W / 60, 1),
                              'two_plus': round(sum(w * v[2] for w, v in rows) / W, 3)}
        for k in ('changes', 'change_min', 'two_plus'): res[zone][k] = round((res[zone]['from'][k] + res[zone]['to'][k]) / 2, 3)
    print(' ', name, json.dumps(res['paris']), flush=True)
    return res


def main(gtfs, cdg_only=False, changes_only=False):
    import numpy as np
    made = []; out = {'_about': __doc__.strip().split('\n')[0] + ' Made by model/tunnel_room_tests.py; hours are those of the journeys to work of one working day, both ways.'}
    if changes_only:
        out = json.load(open(OUT)); ent = RT.station_entries()
        out['cdg_express']['changes'] = {k: changes(n, gtfs, ent) for k, n in CDG.items()}
        json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False); return
    # ---- line J in the RER F tunnel
    if cdg_only: out['line_j'] = json.load(open(OUT))['line_j']
    else:
        out['line_j'] = {}
        for key, name in J.items():
            RT.run(os.path.join(NETS, name + '.json'), gtfs); made.append(name)
            c = RT.compare('plan', name, verbose=False); t = c['trips']; cl = {x['label']: x for x in t['classes']}
            log = json.loads(str(RT.load(name)['log'])); ex = next(l for l in log if 'arrivals' in l and l.get('name', '').startswith('The plan, '))
            gain = [x for x in t['classes'] if x['lo'] >= 1]
            out['line_j'][key] = {'peak_trains': PEAK[key], 'trains_day': ex['arrivals'] + ex['departures'], 'hours_day': int(round(2 * t['hours_one_way'], -1)),
                                  'commuters_1': int(round(sum(x['commuters'] for x in gain), -2)),
                                  'mean_gain': round(sum(x['commuters'] * x['mean_gain'] for x in gain) / max(sum(x['commuters'] for x in gain), 1), 1)}
    # ---- CDG Express: minutes from and to the airport, each station weighed by its entries of a working day.
    # 'today' is the line as it opens in 2027; every other version is set against the plan with CDG Express ending at Nord-Est ('est').
    for name in CDG.values():
        if not os.path.exists(os.path.join(RT.RES, name + '.npz')): RT.run(os.path.join(NETS, name + '.json'), gtfs)     # a table left by an interrupted run is used again
        made.append(name)
    V = {k: RT.load(n) for k, n in CDG.items()}; ent = RT.station_entries(); E = V['est']
    res = {'through': compare_rows(E, V['through'], ent), 'bd_lyon': compare_rows(E, V['bd_lyon'], ent), 'plan_vs_2027': compare_rows(V['today'], E, ent)}
    res['region'], res['paris'] = res['through']['region'], res['through']['paris']        # the names read by model/levers.py
    names = {k: [str(x) for x in V[k]['names']] for k in V}
    def minutes(k, n):
        ids = list(V[k]['ids']); i = ids.index(AIRPORT); j = next(q for q, x in enumerate(names[k]) if x == n); return round(float(V[k]['minutes'][i, j]), 0)
    res['examples'] = {key: {'2027': minutes('today', n), 'end': minutes('est', n), 'through': minutes('through', n), 'bd_lyon': minutes('bd_lyon', n)} for key, n in EXAMPLES}
    res['changes'] = {k: changes(n, gtfs, ent) for k, n in CDG.items()}
    out['cdg_express'] = res
    for name in made:
        p = os.path.join(RT.RES, name + '.npz')
        if os.path.exists(p): os.remove(p)
    json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False); print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    a = sys.argv[1:]
    if '--gtfs' in a: main(a[a.index('--gtfs') + 1], '--cdg-only' in a, '--changes-only' in a)
    else: print(__doc__)
