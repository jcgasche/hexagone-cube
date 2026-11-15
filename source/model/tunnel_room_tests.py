"""Tests on the real timetable of what could run in the room the new tunnels leave (annex 'parts', block parts.more).

Each test is a network version of model/inputs/networks/ run by model/regiontimes.py against the plan:
  plan_j_all, plan_j_cormeilles, plan_j_ermont   line J trains run on from Saint-Lazare to Nord-Est in the RER F tunnel
  plan_cdgx_est, plan_cdgx_through               CDG Express ending at Nord-Est, or running on through the RER G tunnel

Run from source/:  python3 model/tunnel_room_tests.py --gtfs DIR      (about 5 minutes; DIR = the IDFM timetable folder, as for regiontimes.py run)
Writes model/inputs/tunnel_room_tests.json and removes the station-to-station tables it made, so that the chapter on travel times
keeps its own list of versions.
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import regiontimes as RT

NETS = os.path.join(HERE, 'inputs', 'networks'); OUT = os.path.join(HERE, 'inputs', 'tunnel_room_tests.json')
J = {'all': 'plan_j_all', 'cormeilles': 'plan_j_cormeilles', 'ermont': 'plan_j_ermont'}
PEAK = {'all': 25, 'cormeilles': 9, 'ermont': 9}        # trains arriving at Saint-Lazare from 7:30 to 8:30 (IDFM timetable of 3 November 2026)
CDG = ('plan_cdgx_est', 'plan_cdgx_through'); AIRPORT = 'X:CDG'
CENTRE = (2.3499, 48.8530); PARIS_KM = 6.0          # Notre-Dame; stations within 6 km stand for Paris inside the ring road


def trains(log, name):
    return next((l for l in log if l.get('name') == name), {})


def main(gtfs):
    import numpy as np
    made = []; out = {'_about': __doc__.strip().split('\n')[0] + ' Made by model/tunnel_room_tests.py; hours are those of the journeys to work of one working day, both ways.'}
    # ---- line J in the RER F tunnel
    out['line_j'] = {}
    for key, name in J.items():
        RT.run(os.path.join(NETS, name + '.json'), gtfs); made.append(name)
        c = RT.compare('plan', name, verbose=False); t = c['trips']; cl = {x['label']: x for x in t['classes']}
        log = json.loads(str(RT.load(name)['log'])); ex = next(l for l in log if 'arrivals' in l and l.get('name', '').startswith('The plan, '))
        gain = [x for x in t['classes'] if x['lo'] >= 1]
        out['line_j'][key] = {'peak_trains': PEAK[key], 'trains_day': ex['arrivals'] + ex['departures'], 'hours_day': int(round(2 * t['hours_one_way'], -1)),
                              'commuters_1': int(round(sum(x['commuters'] for x in gain), -2)),
                              'mean_gain': round(sum(x['commuters'] * x['mean_gain'] for x in gain) / max(sum(x['commuters'] for x in gain), 1), 1)}
    # ---- CDG Express: minutes from and to the airport, each station weighed by its entries of a working day
    for name in CDG: RT.run(os.path.join(NETS, name + '.json'), gtfs); made.append(name)
    A, B = RT.load(CDG[0]), RT.load(CDG[1]); ids = list(A['ids']); assert list(B['ids']) == ids
    i = ids.index(AIRPORT); ent = RT.station_entries(); w = np.array([ent.get(s, 0.0) for s in ids])
    km = np.array([math.hypot((lo - CENTRE[0]) * 73.0, (la - CENTRE[1]) * 111.2) for lo, la in zip(A['lon'], A['lat'])])
    res = {}
    for zone, mask in (('region', np.ones(len(ids), bool)), ('paris', km <= PARIS_KM)):
        res[zone] = {}
        for way, row in (('from', lambda M: M[i, :]), ('to', lambda M: M[:, i])):
            a, b = row(A['minutes']), row(B['minutes']); ok = np.isfinite(a) & np.isfinite(b) & (w > 0) & mask; g = (a - b)[ok]; ww = w[ok]
            res[zone][way] = {'end': round(float((a[ok] * ww).sum() / ww.sum()), 1), 'through': round(float((b[ok] * ww).sum() / ww.sum()), 1), 'gain': round(float((g * ww).sum() / ww.sum()), 2),
                              'share_1': round(float(ww[g >= 1].sum() / ww.sum()), 3), 'gain_of_gainers': round(float((g * ww)[g >= 1].sum() / max(ww[g >= 1].sum(), 1)), 1)}
        res[zone]['gain'] = round((res[zone]['from']['gain'] + res[zone]['to']['gain']) / 2, 2)
        res[zone]['share_1'] = round((res[zone]['from']['share_1'] + res[zone]['to']['share_1']) / 2, 3)
    a, b = A['minutes'][i, :], B['minutes'][i, :]; names = [str(x) for x in A['names']]
    pick = lambda n: next(j for j, x in enumerate(names) if x == n)
    res['examples'] = {k: {'end': round(float(a[pick(n)]), 0), 'through': round(float(b[pick(n)]), 0)} for k, n in (('chatelet', 'Châtelet - Les Halles'), ('montparnasse', 'Gare Montparnasse'), ('versailles', 'Versailles Chantiers'))}
    out['cdg_express'] = res
    for name in made:
        p = os.path.join(RT.RES, name + '.npz')
        if os.path.exists(p): os.remove(p)
    json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False); print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    a = sys.argv[1:]
    if '--gtfs' in a: main(a[a.index('--gtfs') + 1])
    else: print(__doc__)
