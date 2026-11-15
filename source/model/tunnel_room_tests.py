"""Tests on the real timetable of what could run in the room the new tunnels leave (annex 'parts', block parts.more).

Each test is a network version of model/inputs/networks/ run by model/regiontimes.py against the plan:
  plan_j_all, plan_j_cormeilles, plan_j_ermont   line J trains run on from Saint-Lazare to Nord-Est in the RER F tunnel
  future_cdgx_est                                CDG Express as it opens in 2027, at the surface of Gare de l'Est, with lines 15 to 18 (the plan's reference)
  plan_cdgx_est, plan_cdgx_through               CDG Express ending at Nord-Est, or running on through the RER G tunnel
  plan_cdgx_bd_lyon                              CDG Express through the old RER B and D tunnel to Chatelet and Gare de Lyon

Run from source/:  python3 model/tunnel_room_tests.py --gtfs DIR [--cdg-only]     (about 7 minutes; DIR = the IDFM timetable folder, as for regiontimes.py run)
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


def main(gtfs, cdg_only=False):
    import numpy as np
    made = []; out = {'_about': __doc__.strip().split('\n')[0] + ' Made by model/tunnel_room_tests.py; hours are those of the journeys to work of one working day, both ways.'}
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
    out['cdg_express'] = res
    for name in made:
        p = os.path.join(RT.RES, name + '.npz')
        if os.path.exists(p): os.remove(p)
    json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False); print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    a = sys.argv[1:]
    if '--gtfs' in a: main(a[a.index('--gtfs') + 1], '--cdg-only' in a)
    else: print(__doc__)
