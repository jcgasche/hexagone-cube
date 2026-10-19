#!/usr/bin/env python3
"""Crossing Paris today, read from SNCF's own timetable: for the city pairs the site shows, every journey of a weekday that a
passenger would choose, direct or with a change of station in Paris, and the time it spends in Paris between the two trains.

    python3 model/paris_crossing.py <folder of the SNCF GTFS export> [YYYYMMDD]     -> model/inputs/paris_crossing.json

The timetable is SNCF's open data, export-opendata-sncf-gtfs.zip from https://eu.ftp.opendatasoft.com/sncf/plandata/ (not kept
in the repository). A journey is kept only if no other journey of the day leaves later and arrives as early or earlier, so the
times are those of the best connection for each departure, never a wait chosen on purpose. Departures from 05:00 to 21:00.
A change in Paris needs the metro or a walk between the two stations (MOVE, minutes, ASSUMPTION from the RATP journey planner's
usual times) plus a margin of 15 minutes to make the train (ASSUMPTION)."""
import csv, json, os, statistics, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
CITY = {'Lille': {'87286005', '87223263'}, 'Bordeaux': {'87581009'}, 'Strasbourg': {'87212027'}, 'Lyon': {'87723197', '87722025', '87762906'},
        'Marseille': {'87751008'}, 'Rennes': {'87471003'}, 'Nantes': {'87481002'}, 'Dijon': {'87713040'}}
PARIS = {'87271007': 'Nord', '87113001': 'Est', '87686006': 'Lyon', '87686667': 'Bercy', '87391003': 'Montparnasse', '87391102': 'Montparnasse',
         '87547000': 'Austerlitz', '87384008': 'Saint-Lazare'}
MARGIN = 15
MOVE = {('Nord', 'Est'): 10, ('Nord', 'Lyon'): 22, ('Nord', 'Montparnasse'): 33, ('Nord', 'Austerlitz'): 27, ('Nord', 'Saint-Lazare'): 20, ('Nord', 'Bercy'): 27,
        ('Est', 'Lyon'): 25, ('Est', 'Montparnasse'): 31, ('Est', 'Austerlitz'): 25, ('Est', 'Saint-Lazare'): 20, ('Est', 'Bercy'): 28,
        ('Lyon', 'Montparnasse'): 30, ('Lyon', 'Austerlitz'): 12, ('Lyon', 'Saint-Lazare'): 20, ('Lyon', 'Bercy'): 8,
        ('Montparnasse', 'Austerlitz'): 22, ('Montparnasse', 'Saint-Lazare'): 20, ('Montparnasse', 'Bercy'): 30,
        ('Austerlitz', 'Saint-Lazare'): 25, ('Austerlitz', 'Bercy'): 15, ('Saint-Lazare', 'Bercy'): 25}
PAIRS = [('Lille', 'Bordeaux'), ('Bordeaux', 'Strasbourg'), ('Lille', 'Lyon'), ('Lille', 'Marseille'), ('Rennes', 'Lyon'), ('Rennes', 'Strasbourg'), ('Nantes', 'Strasbourg'),
         ('Rennes', 'Dijon'), ('Bordeaux', 'Lyon'), ('Nantes', 'Lyon'), ('Nantes', 'Marseille'), ('Lille', 'Nantes'), ('Lyon', 'Strasbourg')]
FIRST, LAST = 5 * 60, 21 * 60


def load(folder, date):
    """Every train (not the coaches) running on that date: its stops as (station code, arrival, departure) in minutes."""
    svc = {r['service_id'] for r in csv.DictReader(open(f'{folder}/calendar_dates.txt')) if r['date'] == date and r['exception_type'] == '1'}
    run = {r['trip_id'] for r in csv.DictReader(open(f'{folder}/trips.txt')) if r['service_id'] in svc}
    trips = collections.defaultdict(list)
    for r in csv.DictReader(open(f'{folder}/stop_times.txt')):
        if r['trip_id'] not in run or 'OCECar' in r['stop_id']: continue
        hm = lambda t: int(t.split(':')[0]) * 60 + int(t.split(':')[1])
        trips[r['trip_id']].append((int(r['stop_sequence']), r['stop_id'][-8:], hm(r['arrival_time']), hm(r['departure_time'])))
    return {k: [x[1:] for x in sorted(v)] for k, v in trips.items()}


def legs(trips, frm, to):
    """(departure, arrival, trip, departure station, arrival station) for each train calling at frm, then later at to."""
    out = []
    for t, s in trips.items():
        for i, x in enumerate(s):
            if x[0] not in frm: continue
            j = next((k for k in range(i + 1, len(s)) if s[k][0] in to), None)
            if j is not None: out.append((x[2], s[j][1], t, x[0], s[j][0]))
            break
    return out


def chosen(js):
    """The journeys a passenger would choose: no other one leaves later and arrives as early or earlier."""
    js = sorted({(j[0], j[1]): j for j in js if FIRST <= j[0] <= LAST}.values())
    return [j for j in js if not any(k[0] >= j[0] and k[1] <= j[1] and k[:2] != j[:2] for k in js)]


def pair(trips, a, b):
    direct = [(d, ar, 'direct') for d, ar, *_ in legs(trips, CITY[a], CITY[b])]
    l1 = legs(trips, CITY[a], set(PARIS))
    l2 = [x for st in PARIS for x in legs(trips, {st}, CITY[b])]
    move = lambda p, q: MARGIN + (0 if PARIS[p] == PARIS[q] else MOVE.get((PARIS[p], PARIS[q]), MOVE.get((PARIS[q], PARIS[p]))))
    via = [(d1, a2, 'paris', a1, d2) for d1, a1, t1, _, p in l1 for d2, a2, t2, q, _ in l2 if t1 != t2 and d2 >= a1 + move(p, q)]
    best, vbest, dbest = chosen(direct + via), chosen(via), chosen(direct)
    return {'journeys_day': len(best), 'direct_day': len(dbest), 'via_paris_day': len(vbest),
            'via_paris_min': statistics.median(x[1] - x[0] for x in vbest), 'in_paris_min': statistics.median(x[4] - x[3] for x in vbest),
            'legs_min': statistics.median((x[1] - x[0]) - (x[4] - x[3]) for x in vbest),
            'direct_min': statistics.median(x[1] - x[0] for x in dbest) if dbest else None}


def main():
    folder = sys.argv[1]; date = sys.argv[2] if len(sys.argv) > 2 else '20260317'
    trips = load(folder, date)
    out = {'_note': f'SNCF timetable (open data, GTFS), {date[:4]}-{date[4:6]}-{date[6:]}, departures 05:00 to 21:00; medians of the journeys a passenger would choose. '
                    'Each figure is the mean of the two directions. model/paris_crossing.py', 'date': date, 'pairs': {}}
    gaps = []
    for a, b in PAIRS:
        both = [pair(trips, a, b), pair(trips, b, a)]
        m = {k: (None if any(x[k] is None for x in both) else round(sum(x[k] for x in both) / 2, 1)) for k in both[0]}
        out['pairs'][f'{a}-{b}'] = m; gaps.append(m['in_paris_min'])
        print(f"{a}-{b}: {m}")
    out['in_paris_median_min'] = statistics.median(gaps)
    json.dump(out, open(f'{HERE}/inputs/paris_crossing.json', 'w'), indent=1)
    print('time in Paris between the two trains, median of the pairs:', out['in_paris_median_min'])


if __name__ == '__main__':
    main()
