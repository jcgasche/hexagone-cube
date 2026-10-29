#!/usr/bin/env python3
"""From a regional express train (TER) to the two airports and to the TGVs, today and with the plan, from each of the four
directions the TER come from. The TER leg to Paris is the same in both cases; what changes is the part inside Paris, counted here
from the moment the TER reaches its first Paris station.

    python3 model/airports.py <folder of the IDFM GTFS export>     -> model/inputs/airports.json (the legs read from the timetable)
    python3 model/airports.py                                      -> src/data/airports.json (today and the plan, from those legs)

Today a TER ends at a terminal: the passenger walks to the concourse, then to the metro or RER, and rides to the airport, with the
changes that the network imposes (Montparnasse to Roissy: metro 4, RER D, RER B). These rides are read from the Île-de-France
timetable (IDFM GTFS): the earliest arrival at the airport for departures every 7 minutes from 10:00 to 10:49 on a weekday, from the
terminal's own platforms, with the transfer times of the timetable file, averaged. With the plan every TER runs through two of the
three TGV stations, 6 minutes apart, so the passenger reaches Nord-Est (RER B to Roissy, as from Gare du Nord today) or Gare de Lyon
(line 14 to Orly) either on the TER itself, or by any TGV between two stations: a change of train inside one station, never a
crossing of Paris. The walks inside the deep stations are assumptions. A TER passenger who wants a TGV finds one to every direction at
the two stations the TER serves: one change inside one station, against a change of station across Paris today."""
import csv, json, os, sys, bisect, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(HERE, 'inputs', 'airports.json')
OUT = os.path.join(HERE, '..', 'src', 'data', 'airports.json')

# ---------------------------------------------------------------- what the model assumes
RUN = 6.0                    # the TGV run between any two of the three stations (nordest.TH_ACCESS)
TER_STOP = 5.0               # a TER stops 5 minutes at a through station (nordest.TER_STOP): on board, the next station is RUN + TER_STOP away
TGV_PER_HOUR = {('NE', 'LY'): 7, ('LY', 'NE'): 7, ('MP', 'LY'): 9, ('LY', 'MP'): 9, ('NE', 'MP'): 6, ('MP', 'NE'): 6}   # TGVs an hour on each side of the triangle (nordest.ter_paths: nelyon, link, nemont)
DEEP_TO_TGV = 4.0            # minutes from a TER platform to a TGV platform of the same deep station (ASSUMPTION)
DEEP_TO_METRO = 5.0          # minutes from a deep platform to the RER B or line 14 platform of the same station complex (ASSUMPTION)
# today: TER platform to the concourse, then concourse to the platform of the first line used, from the access model (model.py TERMINALS)
TODAY_WALK = {'Nord': 2 + 4, 'Est': 2 + 3, 'Lyon': 3 + 4, 'Bercy': 3 + 4, 'Montparnasse': 2 + 6}      # Bercy: ASSUMPTION, as Gare de Lyon
# the four directions the TER come from: today's terminal, the two stations the plan's TER serves in order, some of the towns served
DIRECTIONS = [
    {'id': 'north', 'name': 'From the north', 'towns': 'Amiens, Compiègne, Beauvais, Saint-Quentin', 'today': 'Nord', 'plan': ['NE', 'MP']},
    {'id': 'east', 'name': 'From the east', 'towns': 'Château-Thierry, Reims, Troyes', 'today': 'Est', 'plan': ['NE', 'LY']},
    {'id': 'burgundy', 'name': 'From Burgundy', 'towns': 'Laroche-Migennes, Auxerre, Dijon by TER', 'today': 'Bercy', 'plan': ['LY', 'NE']},
    {'id': 'atlantic', 'name': 'From the west', 'towns': 'Chartres, Dreux, Granville', 'today': 'Montparnasse', 'plan': ['MP', 'NE']},
]
AIRPORT_FROM = {'cdg': 'NE', 'orly': 'LY'}           # the station each airport's line leaves from: RER B at Nord-Est, line 14 at Gare de Lyon
AIRPORT_LEG = {'cdg': ('Nord', 'cdg'), 'orly': ('Lyon', 'orly')}      # the ride, read from today's timetable from the terminal above the deep station

# ---------------------------------------------------------------- the timetable
STATION = {'Nord': 'IDFM:71410', 'Est': 'IDFM:71359', 'Lyon': 'IDFM:73626', 'Bercy': 'IDFM:71607', 'Montparnasse': 'IDFM:71139',
           'cdg': 'IDFM:73699', 'orly': 'IDFM:63284'}       # parent stations of the IDFM file: Roissy is Terminal 2, Orly the station of terminals 1 to 3
DATE, TIMES = '20261103', [600 + 7 * i for i in range(8)]   # a Tuesday, departures from 10:00 every 7 minutes: a mean over the waits
CHANGE = 2.0                                                # minutes to leave one train and board another at the same platform
SAME_STATION = 3.0                                          # platform to platform inside one station when the file gives no transfer time


def read_legs(folder):
    """Earliest arrival from every terminal to both airports, and from Nord to Roissy and Lyon to Orly, on the IDFM timetable."""
    wd = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day = wd[datetime.date(int(DATE[:4]), int(DATE[4:6]), int(DATE[6:])).weekday()]
    svc = {r['service_id'] for r in csv.DictReader(open(f'{folder}/calendar.txt')) if r[day] == '1' and r['start_date'] <= DATE <= r['end_date']}
    for r in csv.DictReader(open(f'{folder}/calendar_dates.txt')):
        if r['date'] == DATE: (svc.add if r['exception_type'] == '1' else svc.discard)(r['service_id'])
    run = {r['trip_id'] for r in csv.DictReader(open(f'{folder}/trips.txt')) if r['service_id'] in svc}
    parent = {}
    for r in csv.DictReader(open(f'{folder}/stops.txt')): parent[r['stop_id']] = r['parent_station'] or r['stop_id']
    hm = lambda t: int(t[:2]) * 60 + int(t[3:5]) + int(t[6:8]) / 60
    st = collections.defaultdict(list)
    for r in csv.DictReader(open(f'{folder}/stop_times.txt')):
        if r['trip_id'] in run: st[r['trip_id']].append((int(r['stop_sequence']), r['stop_id'], hm(r['arrival_time']), hm(r['departure_time'])))
    conns = sorted((a[3], b[2], a[1], b[1], tid) for tid, L in st.items() for a, b in zip(sorted(L), sorted(L)[1:]))
    deps = [c[0] for c in conns]
    foot = collections.defaultdict(list)
    for r in csv.DictReader(open(f'{folder}/transfers.txt')): foot[r['from_stop_id']].append((r['to_stop_id'], float(r['min_transfer_time'] or 120) / 60))
    kids = collections.defaultdict(list)
    for s, p in parent.items(): kids[p].append(s)
    for ks in kids.values():
        for a in ks:
            have = {x[0] for x in foot[a]}
            foot[a].extend((b, SAME_STATION) for b in ks if b != a and b not in have)

    def earliest(src, dst, t0):
        arr, via = collections.defaultdict(lambda: 1e9), {}
        def relax(s, t, tid):
            if t < arr[s]:
                arr[s] = t; via[s] = tid
                for s2, dt in foot[s]:
                    if t + dt < arr[s2]: arr[s2] = t + dt; via[s2] = tid
        for k in kids[src]: relax(k, t0, None)
        done = set()
        for i in range(bisect.bisect_left(deps, t0), len(conns)):
            dep, a, u, v, tid = conns[i]
            if dep > t0 + 180: break
            if tid in done or (u in via and arr[u] + (0 if via[u] == tid else CHANGE) <= dep): done.add(tid); relax(v, a, tid)
        return min(arr[k] for k in kids[dst]) - t0

    legs = {}
    for a in ('Nord', 'Est', 'Lyon', 'Bercy', 'Montparnasse'):
        for b in ('cdg', 'orly'):
            ts = [earliest(STATION[a], STATION[b], t0) for t0 in TIMES]
            legs[f'{a}-{b}'] = {'mean': sum(ts) / len(ts), 'min': min(ts), 'max': max(ts)}
            print(f'{a:13s} -> {b}: {legs[a + "-" + b]["mean"]:5.1f} min ({min(ts):.0f} to {max(ts):.0f})')
    return legs


def compute(legs):
    """Today and with the plan, for each direction and each airport, in minutes from the TER's first Paris station."""
    ride = {k: legs[f'{a}-{b}']['mean'] for k, (a, b) in AIRPORT_LEG.items()}        # the airport line's ride, platform to platform, wait included
    rows = []
    for d in DIRECTIONS:
        r = {'id': d['id'], 'name': d['name'], 'towns': d['towns'], 'terminal': d['today'], 'stations': d['plan']}
        for ap in ('cdg', 'orly'):
            today = TODAY_WALK[d['today']] + legs[f'{d["today"]}-{ap}']['mean']
            hub = AIRPORT_FROM[ap]
            ways = {}
            if d['plan'][0] == hub: ways['first'] = DEEP_TO_METRO + ride[ap]                                 # the TER stops there first
            if d['plan'][1] == hub: ways['on_board'] = RUN + TER_STOP + DEEP_TO_METRO + ride[ap]              # stay on the TER to its second station
            if d['plan'][0] != hub: ways['tgv'] = DEEP_TO_TGV + 30.0 / TGV_PER_HOUR[(d['plan'][0], hub)] + RUN + DEEP_TO_METRO + ride[ap]   # any TGV from the first station to the hub
            how = min(ways, key=ways.get)
            r[ap] = {'today': today, 'plan': ways[how], 'how': how, 'ways': ways}
        rows.append(r)
    return {'_note': 'Written by model/airports.py from model/inputs/airports.json (the IDFM timetable). Minutes inside Paris, from the TER\'s first station.',
            'params': {'run': RUN, 'ter_stop': TER_STOP, 'deep_to_tgv': DEEP_TO_TGV, 'deep_to_metro': DEEP_TO_METRO, 'today_walk': TODAY_WALK,
                       'tgv_per_hour': {a + b: n for (a, b), n in TGV_PER_HOUR.items()}, 'date': DATE, 'departures': len(TIMES)},
            'ride': ride, 'legs': legs, 'rows': rows,
            'gain': {ap: {'min': min(r[ap]['today'] - r[ap]['plan'] for r in rows), 'max': max(r[ap]['today'] - r[ap]['plan'] for r in rows)} for ap in ('cdg', 'orly')}}


if __name__ == '__main__':
    if len(sys.argv) > 1:
        legs = read_legs(sys.argv[1])
        json.dump({'_note': f'Written by model/airports.py from the IDFM GTFS: {DATE}, departures 10:00 to 10:49 every 7 minutes, minutes platform to platform, wait included.',
                   'legs': legs}, open(INPUT, 'w'), indent=1)
        print('->', INPUT)
    legs = json.load(open(INPUT))['legs']
    out = compute(legs)
    json.dump(out, open(OUT, 'w'), indent=1, ensure_ascii=False)
    for r in out['rows']:
        print(f"{r['name']:16s} Roissy {r['cdg']['today']:5.1f} -> {r['cdg']['plan']:5.1f} ({r['cdg']['how']})   Orly {r['orly']['today']:5.1f} -> {r['orly']['plan']:5.1f} ({r['orly']['how']})")
    print('->', OUT)
