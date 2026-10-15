"""Writes the data files the site reads (src/data/*.json) from the model outputs. Run after nordest.py and finance.py:

    python3 model/nordest.py && python3 model/finance.py && python3 model/export.py && python3 build.py
"""
import csv, json, os, statistics as S
import nordest as N
from estimate import W

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'src', 'data')
KEYS = ['Nord', 'Est', 'Lyon', 'Montparnasse']


def main():
    os.makedirs(OUT, exist_ok=True)
    d = json.load(open(f'{HERE}/outputs/nordest.json'))
    fin = json.load(open(f'{HERE}/outputs/finance.json'))
    # ---- model.json: the parts of the traffic and cost model that pages show
    keep = ['TH', 'TH_ACCESS', 'tunnels', 'sub_tracks', 'reg_platforms', 'corridor_km', 'TR', 'conn', 'paris', 'far_stop_share', 'by_arr', 'by_dir', 'share_quicker', 'share_slower', 'share_within1', 'max_gain', 'value_of_choice', 'access_effect',
            'connecting', 'regional', 'regional_high', 'regional_low', 'service', 'service_full', 'cost', 'cost_low', 'cost_high', 'layout', 'len', 'link_km', 'rates', 'rates_low', 'rates_high',
            'backtest', 'AF', 'idc', 'ratios', 'params', 'yearly', 'yearly_ride', 'sens', 'deep2_scaled', 'rate_tests', 'gross_up', 'stages', 'extras', 'station_total', 'today', 'destinations', 'dest_axis', 'dest']
    m = {k: d[k] for k in keep}
    m['access'] = {k: d['access'][k] for k in ('central', 'ride', 'no_choice', 'nord_hall', 'deep2')}
    m['tripend_shares'] = N.SH; m['vot'] = {'long_distance': N.VOT_LD, 'regional_express': N.VOT_TER, 'paris_region': N.VOT_IDF}; m['elasticity'] = N.ELAST
    m['hour_today'] = N.HOUR_TODAY; m['hour_full'] = N.HOUR_FULL; m['reverse'] = N.REVERSE; m['per_track'] = N.PER_TRACK
    m['stop_min'] = N.STOP_MIN; m['reserve_min'] = N.RESERVE_MIN; m['run_min'] = N.TH['L'] - N.STOP_MIN; m['clear_min'] = N.CLEAR_MIN; m['util'] = N.UTIL; m['tracks_per_direction'] = N.TRACKS_PER_DIRECTION
    # the corridor lengths of the project map must be the model's
    proj = json.load(open(os.path.join(HERE, '..', 'src', 'sections', 'project', 'data.json')))
    for c in proj['corridors']:
        want = N.LINK_KM if c['id'] == 'link' else N.CORRIDOR_KM[c['id']]
        assert abs(c['km'] - want) < 1e-9, f"project/data.json: corridor {c['id']} is {c['km']} km, the model says {want}"
    json.dump(m, open(f'{OUT}/model.json', 'w'), separators=(',', ':'))
    json.dump(fin, open(f'{OUT}/finance.json', 'w'), separators=(',', ':'))
    # ---- points.json: the 1,000 points of the access map
    rows = []; pure = []; best = []; today = []
    for r in csv.DictReader(open(f'{HERE}/inputs/points.csv')):
        t = {k: float(r['t_' + k]) for k in KEYS}
        p = N.tgv_times(t, 0.0); b = N.tgv_times(t, 0.0, True, 'ride')      # at the station entrance; counting the ride, the passenger picking the train
        rows.append([int(float(r['id'])) if 'id' in r else len(rows) + 1, round(float(r['lat']), 5), round(float(r['lon']), 5), int(float(r['arr']))]
                    + [round(t[k], 1) for k in KEYS] + [round(p[k], 1) for k in KEYS] + [round(b[k], 1) for k in KEYS])
        today.append(sum(W[k] * t[k] for k in KEYS)); pure.append(sum(W[k] * p[k] for k in KEYS)); best.append(sum(W[k] * b[k] for k in KEYS))
    slower = sum(1 for x, y in zip(pure, today) if x > y + 1e-9) + sum(1 for x, y in zip(best, today) if x > y + 1e-9)
    assert slower == 0, 'a point is slower than today: the measure is broken'
    pts = {'rows': rows, 'cols': ['id', 'lat', 'lon', 'arr', 'today_N', 'today_E', 'today_L', 'today_M', 'station_N', 'station_E', 'station_L', 'station_M', 'ride_N', 'ride_E', 'ride_L', 'ride_M'],
           'w': W, 'th': N.TH_ACCESS,
           'avg': {'today': S.mean(today), 'station': S.mean(pure), 'ride': S.mean(best)},
           'share_quicker': {'station': sum(1 for x, y in zip(pure, today) if x < y - 0.05) / len(rows), 'ride': sum(1 for x, y in zip(best, today) if x < y - 0.05) / len(rows)},
           'max_gain': {'station': max(y - x for x, y in zip(pure, today)), 'ride': max(y - x for x, y in zip(best, today))}}
    json.dump(pts, open(f'{OUT}/points.json', 'w'), separators=(',', ':'))
    print('model.json', os.path.getsize(f'{OUT}/model.json'), 'finance.json', os.path.getsize(f'{OUT}/finance.json'), 'points.json', os.path.getsize(f'{OUT}/points.json'))
    print('Paris averages', {k: round(v, 2) for k, v in pts['avg'].items()}, 'quicker', pts['share_quicker'], 'max gain', {k: round(v, 1) for k, v in pts['max_gain'].items()})


if __name__ == '__main__':
    main()
