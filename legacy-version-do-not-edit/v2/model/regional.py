"""Regional cross-check: population-weighted change in access time for every Ile-de-France commune,
on the 2031 network (Grand Paris Express lines 15, 16, 17 open)."""
import json, csv, collections, statistics as S
from shapely.geometry import shape
import sys
import model
from model import build, times_to, hav, TERMINALS, HS_PAX, TRAIN_DELTA, WALK_MIN_PER_KM
MODE = sys.argv[1] if len(sys.argv) > 1 else ''
WEIGHTED = MODE in ('weighted', 'comfort')
KRIDE = float(sys.argv[2]) if MODE == 'comfort' else 1.0
if WEIGHTED: model.set_weights(2.0, 1.5, KRIDE)
KWR = 2.0 if WEIGHTED else 1.0
tot = sum(HS_PAX.values()); W = {k: v / tot for k, v in HS_PAX.items()}
G0, st, la = build(False, regional=True)
G1, st1, la1 = build(True, regional=True)
D0 = {k: times_to(G0, k) for k in TERMINALS}
D1 = times_to(G1, 'Pleyel', True)
def feeder(km):
    return KWR * km * WALK_MIN_PER_KM if km <= 1.0 else KWR * WALK_MIN_PER_KM + 4.0 + (km - 1.0) * 3.0   # walk, then bus or car at 20 km/h
def t(pt, dist, stn, lat, dest):
    best = 1e9
    for s in lat:
        km = hav(pt, (stn[s]['latitude'], stn[s]['longitude']))
        if km <= 12 and ('S', s) in dist:
            v = feeder(km) + dist[('S', s)]
            if v < best: best = v
    return min(best, feeder(hav(pt, TERMINALS[dest]['xy'])) + 2)
g = json.load(open('/home/claude/data/communescore/communes_scores.geojson'))
rows = []
for f in g['features']:
    p = f['properties']; code = str(p['code_insee']); pop = p.get('population') or 0
    c = shape(f['geometry']).representative_point(); pt = (c.y, c.x)
    r = {'code': code, 'name': p.get('name') or p.get('nom'), 'dep': code[:2], 'pop': pop}
    for k in TERMINALS: r['t_' + k] = t(pt, D0[k], st, la, k)
    r['t_Pleyel_prog'] = min(t(pt, D1, st1, la1, 'Pleyel'), r['t_Pleyel'])
    r['today'] = sum(W[k] * r['t_' + k] for k in W)
    r['d1'] = r['t_Pleyel'] - r['today']; r['d2'] = r['t_Pleyel_prog'] - r['today']
    rows.append(r)
ring = lambda d: 'Paris' if d == '75' else ('Petite couronne' if d in ('92', '93', '94') else 'Grande couronne')
agg = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    for key in (ring(r['dep']), 'dep ' + r['dep'], 'IDF'):
        a = agg[key]; a['pop'] += r['pop']
        for k in ('today', 't_Pleyel', 't_Pleyel_prog', 'd1', 'd2'): a[k] += r['pop'] * r[k]
        a['gain1'] += r['pop'] * (r['d1'] < 0); a['gain2'] += r['pop'] * (r['d2'] < 0)
out = {}
for key, a in sorted(agg.items()):
    out[key] = {k: round(a[k] / a['pop'], 2) for k in ('today', 't_Pleyel', 't_Pleyel_prog', 'd1', 'd2', 'gain1', 'gain2')}; out[key]['pop'] = a['pop']
    print(f"{key:18s} pop {a['pop']:>9,d}  today {out[key]['today']:5.1f}  hub {out[key]['t_Pleyel']:5.1f}  hub+prog {out[key]['t_Pleyel_prog']:5.1f}  d1 {out[key]['d1']:+5.1f}  d2 {out[key]['d2']:+5.1f}  pop gaining {out[key]['gain1']:.0%} / {out[key]['gain2']:.0%}")
json.dump({'agg': out, 'rows': rows}, open({'weighted': 'regional_weighted.json', 'comfort': 'regional_comfort.json'}.get(MODE, 'regional.json'), 'w'))
for nm in ['Versailles', 'Saint-Denis', 'Boulogne-Billancourt', 'Montreuil', 'Nanterre', 'Créteil', 'Massy', 'Cergy', 'Meaux', 'Argenteuil', 'Aulnay-sous-Bois', 'Vitry-sur-Seine', 'Évry-Courcouronnes']:
    for r in rows:
        if r['name'] == nm: print(f"{nm:22s} Nord {r['t_Nord']:5.1f} Est {r['t_Est']:5.1f} Lyon {r['t_Lyon']:5.1f} Montp {r['t_Montparnasse']:5.1f} | Pleyel {r['t_Pleyel']:5.1f} prog {r['t_Pleyel_prog']:5.1f}")
