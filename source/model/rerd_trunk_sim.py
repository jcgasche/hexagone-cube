"""Train-by-train simulation of the Gare du Nord (Nord-Est) to Chatelet-Les Halles section, one direction, morning peak.

Question (Charles, 14 Nov 2026): with the RER G tunnel there are four tracks (two each way) for three lines (B, D, G) instead of
two tracks for two lines. Which way of sharing them works best: the plan (B+D | G), D+G | B, B+G | D, a mix (D split between both
tunnels), or six tracks (each line alone)?

Model. Each track pair is: platform tracks at Nord, a two-track tunnel, platform tracks at Chatelet; the lines part after Chatelet.
A train arrives at Nord late by a random amount (its line's own lateness, made upstream), takes the first free platform track of
its line, stands for a random dwell, leaves no sooner than H seconds after the train before it in the tunnel, runs to Chatelet,
takes a free platform track there, dwells and leaves. Trains are served in order of arrival. A train that would wait more than
W minutes to get its platform at Nord is cancelled (what operators do to keep the line moving). Outputs: trains through in the peak
hour, seconds of delay the section ADDS to a train (queueing only, beyond its own lateness and dwell), trains cancelled.

Calibration: H of the existing tunnel is set so that today's 20 B + 12 D timetable lets about 29.5 trains through
(Cour des comptes 2023: 28 to 29; RER B line committee Nov 2023: B runs 17.5 instead of 20, plus 12 D). With NExTEO (2032) and in
a new tunnel H = 90 s (ASSUMPTION; RER A runs 30 an hour on one platform track each way).
Everything marked ASSUMPTION is a judgement, not a measurement. Run: python3 model/rerd_trunk_sim.py > model/inputs/rerd_trunk_results.json (about ten minutes), then python3 model/rerd.py"""
import json, sys, numpy as np

PEAK_H = 2.0            # hours at full frequency (ASSUMPTION)
WARM_H, COOL_H = 0.5, 1.0
COOL_F = 0.6            # share of the peak frequency after the peak
RUN = 180.0             # s, Nord to Chatelet
DW_SCHED = 50.0         # s, timetabled dwell
REOCC = 60.0            # s from a departure to the next train standing at the same platform track (ASSUMPTION)
H_FOLLOW = 45.0         # s between two trains reaching the Chatelet platforms (ASSUMPTION)
H_LINE = 90.0           # s between two trains of one line leaving Chatelet
W_CANCEL = 240.0        # s of queueing at Nord after which a train is cancelled (ASSUMPTION)
C_UP = 0.025            # share of trains cancelled before they reach Paris, any line (ASSUMPTION)
H_NEW = 90.0            # s, tunnel headway with NExTEO or in a new tunnel (ASSUMPTION)
# line: mean dwell (s), share of trains that arrive 'late' (2 min + exponential of mean 4 min); the others arrive with a jitter of mean 30 s.
# Late shares give P(more than 5 min late on arrival) = half the line's 2026 non-punctuality (IDFM bulletin, cumulated to April 2026:
# B 89.2 %, D 83.0 %, P 89.3 %, N 93.6 %); the other half is taken to arise in or after Paris (ASSUMPTION).
LINES = {'B': {'dwell': 60.0, 'late': 0.115}, 'D': {'dwell': 70.0, 'late': 0.18}, 'G': {'dwell': 60.0, 'late': 0.09}}
DWELL_CV = 0.4


def timetable(freq, rng):
    """freq: {line: trains an hour}. Evenly spaced slots over warm-up, peak and cool-down; lines spread as evenly as possible."""
    F = sum(freq.values()); out = []
    def fill(t0, t1, k):
        n = int(round(F * k * (t1 - t0))); step = (t1 - t0) * 3600 / max(n, 1)
        acc = {l: 0.0 for l in freq}
        for i in range(n):
            for l in freq: acc[l] += freq[l] / F
            l = max(acc, key=acc.get); acc[l] -= 1.0
            out.append((t0 * 3600 + i * step, l))
    fill(0, WARM_H, 1.0); fill(WARM_H, WARM_H + PEAK_H, 1.0); fill(WARM_H + PEAK_H, WARM_H + PEAK_H + COOL_H, COOL_F)
    return out


def dwell(line, rng, scale=1.0):
    m = LINES[line]['dwell'] * scale; s2 = np.log(1 + DWELL_CV ** 2)
    return float(rng.lognormal(np.log(m) - s2 / 2, np.sqrt(s2)))


def one_day(freq, plat1, plat2, h, rng, saturate=False, late_scale=1.0, c_up=C_UP, w_cancel=W_CANCEL):
    """plat1, plat2: {line: [platform-track ids]} at Nord and at Chatelet. Returns per-train records for trains timetabled in the peak."""
    tt = timetable(freq, rng); trains = []
    for s, l in tt:
        if not saturate and rng.random() < c_up: continue
        if saturate: e = -1e6 + s * 1e-3          # everyone already waiting, in timetable order
        elif rng.random() < LINES[l]['late'] * late_scale: e = 120.0 + rng.exponential(240.0)
        else: e = rng.exponential(30.0)
        trains.append((s + e, s, l))
    trains.sort()
    free1 = {t: -1e9 for ts in plat1.values() for t in ts}; free2 = {t: -1e9 for ts in plat2.values() for t in ts}
    last_dep1 = last_in2 = -1e9; last_out = {l: -1e9 for l in freq}
    rec = []
    for a, s, l in trains:
        if saturate: a = 0.0
        t1 = min(plat1[l], key=free1.get); t_in = max(a, free1[t1])
        if not saturate and t_in - a > w_cancel:
            rec.append((s, l, None, None)); continue
        d1, d2 = dwell(l, rng), dwell(l, rng)
        ready = max(t_in + d1, (s + DW_SCHED) if not saturate else -1e9)
        dep1 = max(ready, last_dep1 + h); free1[t1] = dep1 + REOCC; last_dep1 = dep1
        arr2 = dep1 + RUN; t2 = min(plat2[l], key=free2.get)
        in2 = max(arr2, free2[t2], last_in2 + H_FOLLOW); last_in2 = in2
        dep2 = max(in2 + d2, last_out[l] + H_LINE); free2[t2] = dep2 + REOCC; last_out[l] = dep2
        free_run = max(a + d1, s + DW_SCHED) + RUN + d2
        rec.append((s, l, dep2, max(dep2 - free_run, 0.0)))
    return rec


def run(freq, plat1, plat2, h, days=300, seed=1, **kw):
    rng = np.random.default_rng(seed); p0, p1 = WARM_H * 3600, (WARM_H + PEAK_H) * 3600
    add = {l: [] for l in freq}; canc = {l: 0 for l in freq}; sched = {l: 0 for l in freq}; thru = []
    for _ in range(days):
        rec = one_day(freq, plat1, plat2, h, rng, **kw)
        n = 0
        for s, l, dep2, ad in rec:
            if dep2 is not None and p0 + RUN <= dep2 < p1 + RUN: n += 1
            if p0 <= s < p1:
                if dep2 is None: canc[l] += 1
                else: add[l].append(ad)
        thru.append(n / PEAK_H)
        for s, l in timetable(freq, rng):
            if p0 <= s < p1: sched[l] += 1
    out = {'timetabled': sum(freq.values()), 'through': round(float(np.mean(thru)), 1), 'lines': {}}
    for l in freq:
        a = np.array(add[l]) if add[l] else np.zeros(1)
        out['lines'][l] = {'freq': freq[l], 'added_s': round(float(a.mean()), 1), 'over_3min': round(float((a > 180).mean()), 3),
                           'cancelled_in_tunnel': round(canc[l] / max(sched[l], 1), 4)}
    return out


def capacity(freq, plat1, plat2, h, seed=2):
    """Trains an hour the pair lets through when trains are always waiting (the timetable's mix of lines)."""
    rng = np.random.default_rng(seed); n = []
    for _ in range(40):
        rec = one_day({l: f * 3 for l, f in freq.items()}, plat1, plat2, h, rng, saturate=True)
        deps = sorted(r[2] for r in rec)
        n.append((len(deps) - 1) * 3600 / (deps[-1] - deps[0]))
    return round(float(np.mean(n)), 1)


def calibrate(target=29.5):
    lo, hi = 90.0, 130.0; f = {'B': 20, 'D': 12}; p = {'B': ['b'], 'D': ['d']}
    for _ in range(12):
        mid = (lo + hi) / 2
        if run(f, p, p, mid, days=200)['through'] > target: lo = mid
        else: hi = mid
    return round((lo + hi) / 2, 1)


# ---------------------------------------------------------------- the ways of sharing the tracks
def layouts(B, D, G):
    """Each layout: list of pairs (name, freq, platforms at Nord, platforms at Chatelet)."""
    own = lambda *ls: {l: [l.lower()] for l in ls}
    pool = lambda ls, tracks: {l: list(tracks) for l in ls}
    half = D / 2
    return {
        'plan: B+D in the old tunnel, G alone': [('old', {'B': B, 'D': D}, own('B', 'D'), own('B', 'D')), ('new', {'G': G}, own('G'), own('G'))],
        'D+G in the new tunnel, B alone in the old': [('old', {'B': B}, pool('B', 'xy'), pool('B', 'xy')), ('new', {'D': D, 'G': G}, own('D', 'G'), pool('DG', 'xy'))],
        'B+G in the new tunnel, D alone in the old': [('old', {'D': D}, pool('D', 'xy'), pool('D', 'xy')), ('new', {'B': B, 'G': G}, own('B', 'G'), pool('BG', 'xy'))],
        'mix: half the D in each tunnel': [('old', {'B': B, 'D': half}, own('B', 'D'), own('B', 'D')), ('new', {'D': half, 'G': G}, own('D', 'G'), pool('DG', 'xy'))],
        'mix: a quarter of the D with the B, three quarters with the G': [('old', {'B': B, 'D': D / 4}, own('B', 'D'), own('B', 'D')), ('new', {'D': 3 * D / 4, 'G': G}, own('D', 'G'), pool('DG', 'xy'))],
        'six tracks: B, D and G each alone': [('old', {'B': B}, pool('B', 'xy'), pool('B', 'xy')), ('D pair', {'D': D}, own('D'), own('D')), ('new', {'G': G}, own('G'), own('G'))],
    }


if __name__ == '__main__':
    h_old = calibrate()
    res = {'h_old_s': h_old, 'h_new_s': H_NEW,
           'check_today': {'old tunnel, 20 B + 12 D, today': run({'B': 20, 'D': 12}, {'B': ['b'], 'D': ['d']}, {'B': ['b'], 'D': ['d']}, h_old),
                           'capacity today': capacity({'B': 20, 'D': 12}, {'B': ['b'], 'D': ['d']}, {'B': ['b'], 'D': ['d']}, h_old),
                           'old tunnel with NExTEO': run({'B': 20, 'D': 12}, {'B': ['b'], 'D': ['d']}, {'B': ['b'], 'D': ['d']}, H_NEW),
                           'capacity with NExTEO': capacity({'B': 20, 'D': 12}, {'B': ['b'], 'D': ['d']}, {'B': ['b'], 'D': ['d']}, H_NEW)},
           'scenarios': {}}
    SC = {'today: B 20, D 12, G 12': (20, 12, 12), 'growth: B 24, D 16, G 16': (24, 16, 16), 'growth with line R in the D: B 24, D 20, G 16': (24, 20, 16)}
    for sc, (B, D, G) in SC.items():
        res['scenarios'][sc] = {}
        for name, pairs in layouts(B, D, G).items():
            res['scenarios'][sc][name] = {pn: dict(run(f, p1, p2, H_NEW), capacity=capacity(f, p1, p2, H_NEW)) for pn, f, p1, p2 in pairs}
    # sensitivities on the plan and on the best four-track layout, growth scenario
    sens = {}
    for lab, kw, h in [('lateness x1.5', {'late_scale': 1.5}, H_NEW), ('lateness x0.5', {'late_scale': 0.5}, H_NEW), ('tunnel headway 100 s', {}, 100.0), ('tunnel headway 80 s', {}, 80.0)]:
        sens[lab] = {name: {pn: run(f, p1, p2, h, **kw) for pn, f, p1, p2 in pairs} for name, pairs in layouts(24, 16, 16).items()}
    res['sensitivity_growth'] = sens
    # practical capacity: the largest timetable (trains an hour) a pair runs with under 60 s added to a train and under 1 % cancelled
    own = lambda *ls: {l: [l.lower()] for l in ls}; pool = lambda ls, tracks: {l: list(tracks) for l in ls}
    kinds = {'old tunnel, B and D together (5 B for 3 D), one platform track each': (lambda n: {'B': n * 5 / 8, 'D': n * 3 / 8}, own('B', 'D'), own('B', 'D')),
             'old tunnel, B alone on both platform tracks': (lambda n: {'B': n}, pool('B', 'xy'), pool('B', 'xy')),
             'new tunnel, D and G together (half each), two platform tracks at Chatelet': (lambda n: {'D': n / 2, 'G': n / 2}, own('D', 'G'), pool('DG', 'xy')),
             'new tunnel, B and G together (5 B for 3 G)': (lambda n: {'B': n * 5 / 8, 'G': n * 3 / 8}, own('B', 'G'), pool('BG', 'xy')),
             'one line alone on one platform track each way (G in the plan, D on its own pair)': (lambda n: {'D': n}, own('D'), own('D'))}
    prac = {}
    for k, (f, p1, p2) in kinds.items():
        prac[k] = {}
        for h in (80.0, 90.0, 100.0):
            best = 0
            for n in range(12, 41):
                x = run(f(n), p1, p2, h, days=120)
                if all(y['added_s'] < 60 and y['cancelled_in_tunnel'] < 0.01 for y in x['lines'].values()): best = n
                else: break
            prac[k][f'{h:g} s'] = best
    res['practical_capacity'] = prac
    json.dump(res, sys.stdout, indent=1)
