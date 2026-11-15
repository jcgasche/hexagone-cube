"""Three ways to make the plan earn more (asked by Charles, 15 November 2026). Nothing here changes the plan, its cost or its benefits.

1. THE PARTS. The economic return (model/french.py) counts the plan as one block. Here its yearly flows are shared between the parts
   that earn them: the TGV and TER triangle (T), RER F (F), RER G (G), and what comes only once every surface track is gone (S: the
   parks, the plots, the noise, the old signal boxes, the upkeep of the surface terminals). The sum of the parts is the plan, to the cent.
2. THE STAGES. french.py opens everything in 2040. Here each part can open in its own year, the money being spent at the same yearly
   rate, to compare the order of the Works chapter (north, east and south-east TGVs with RER F first) with the triangle first.
3. RER D ON ITS OWN PAIR, WITH LINE R (annex 'rerd'), counted with the rules of the economic return, the trains it adds included.
4. RER B AND D: what the plan's relief of their tunnel is worth in trains on time (model/rerd_trunk_sim.py with shorter stops), on
   top of the crowding already counted, and what more trains in the two suburban tunnels would bring and cost.

Run from source/: python3 model/levers.py   -> model/outputs/levers.json   (about 40 s, most of it french.model_figures)
Everything marked ASSUMPTION is a judgement, not a measurement."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import french as FR, nordest as N, rerd_trunk_sim as SIM

YEARS, R = FR.YEARS, FR.R_FR; NY = len(YEARS); IX = {t: i for i, t in enumerate(YEARS)}
pv = lambda s: sum(v / (1 + R) ** (t - FR.BASE_YEAR) for t, v in zip(YEARS, s))
zero = lambda: [0.0] * NY
scale = lambda s, k: [v * k for v in s]
plus = lambda *ss: [sum(x) for x in zip(*ss)]
PARTS = ('T', 'F', 'G', 'S')
NAMES = {'T': 'TGV and TER triangle', 'F': 'RER F', 'G': 'RER G', 'S': 'Surface freed (needs every part)'}

m = FR.model_figures(); O = {'cost': 'central'}
add = FR.added_streams(m, 1, O)
fl, capex = FR.official_streams(m, dict(O, corridor_scale=0.0)); fl = dict(fl); fl[FR.COMFORT] = zero()          # as french.evaluate does
ITEMS = {**{k: fl[k] for k in fl if k not in FR.BORROWED}, **{k: add[k] for k in FR.ADDED if k not in FR.WIDER_ADDED}}
g_ld, g_sd, g_v = FR.growth_opts(O)
te = lambda t: min(t, FR.LAST)
fsd = lambda t: (1 + g_sd) ** (te(t) - FR.BASE_YEAR); vot = lambda t: (1 + g_v) ** (te(t) - FR.BASE_YEAR)
fld = lambda t: (1 + g_ld) ** (te(t) - FR.BASE_YEAR)

# ---------------------------------------------------------------- 1. what each part costs
def hard(Rt):
    tun = Rt['tunnel_civil'] + Rt['tunnel_systems']; st = N.LAYOUT['stations']; sub = lambda k: sum(v.get(k, 0) for v in N.SUB_TRACKS.values()) * N.LEN['sub'] * Rt['platform_m']
    T = (N.TUNNEL_KM['tgv'] * tun + sum(s['hs'] * N.LEN['hs'] + s['ter'] * N.LEN['ter'] for s in st.values()) * Rt['platform_m'] + sum(Rt['hall'][h] for h in N.LAYOUT['halls'])
         + (N.JUNCTIONS['tgv'] + N.JUNCTIONS['ter']) * Rt['junction'] + (N.PORTALS['tgv'] + N.PORTALS['ter']) * Rt['portal'] + Rt['sidings'] + Rt['london_hall'] + Rt['ter_links'])
    F = N.TUNNEL_KM['h'] * tun + sub('h') + N.PORTALS['h'] * Rt['portal']
    G = N.TUNNEL_KM['n'] * tun + sub('n') + N.PORTALS['n'] * Rt['portal'] + Rt['chatelet_links']
    return {'T': T, 'F': F, 'G': G}
up = lambda Rt: (1 + Rt['design'] + Rt['client'] + Rt['land']) * (1 + Rt['risk'])
H = hard(N.RATE); assert abs(sum(H.values()) - N.cost()['hard']) < 1e-9
cost = {k: {'central': H[k] * up(N.RATE), 'low': hard(N.RATE_LOW)[k] * up(N.RATE_LOW), 'high': hard(N.RATE_HIGH)[k] * up(N.RATE_HIGH), 'hard': H[k]} for k in H}
assert abs(sum(c['central'] for c in cost.values()) - capex) < 1e-6
c_share = {k: cost[k]['central'] / capex for k in H}
KM = {'T': N.TUNNEL_KM['tgv'], 'F': N.TUNNEL_KM['h'], 'G': N.TUNNEL_KM['n']}; km_share = {k: v / sum(KM.values()) for k, v in KM.items()}
PLAT = {'T': sum(s['hs'] * N.LEN['hs'] + s['ter'] * N.LEN['ter'] for s in N.LAYOUT['stations'].values()),
        'F': sum(v.get('h', 0) for v in N.SUB_TRACKS.values()) * N.LEN['sub'], 'G': sum(v.get('n', 0) for v in N.SUB_TRACKS.values()) * N.LEN['sub']}
om = {k: KM[k] * N.OM_TUNNEL + PLAT[k] * N.OM_STATION for k in KM}; assert abs(sum(om.values()) - m['om_infra']) < 1e-9
om_share = {k: v / m['om_infra'] for k, v in om.items()}

# ---------------------------------------------------------------- 1. what each part earns: shares of each yearly flow
def reg_by_line():
    """The Paris-side gain of the regional travellers, line by line (the sum of nordest.regional, written out)."""
    sv, _ = N.regional_saving('eq', 'both'); out = {'TER': 0.0}
    val = lambda u, n, s, v: N.gain(u, n, s, v) if s >= 0 else -N.loss(u, 0.0, -s, v)
    for l, q in N.LINES.items():
        thr = N.THROUGH_TRAINS.get(l, 1.0) if sv[l] > 0 else 0.0; s_ = sv[l]
        out[l] = val(q * N.TERM_SHARE[l] * thr, q * thr * N.REG_UPLIFT * (max(0.0, s_ / sv[l]) if sv[l] > 0 else 0.0), s_, N.VOT_IDF)
    for k, q in N.TER.items():
        s_ = sv['TER ' + k]
        if s_ > 0: out['TER'] += val(q, q * ((1 - max(0.0, s_) / N.TER_TRIP) ** N.ELAST - 1), s_, N.VOT_TER)
    return out
rb = reg_by_line(); assert abs(sum(rb.values()) - m['reg_paris']) < 1e-9, (sum(rb.values()), m['reg_paris'])
LINE_PART = {'H': 'F', 'K': 'F', 'L': 'F', 'P': 'G', 'N': 'G', 'R': 'T', 'TER': 'T'}
reg = {p: sum(v for l, v in rb.items() if LINE_PART[l] == p) / m['reg_paris'] for p in 'TFG'}

sb = m['second_station_by_line']; g_second = sb['P'] + sb['N']; second = m['second_station'] - g_second          # as french.crowding
sub_f = sum(sb[l] for l in ('H', 'K', 'L')); ter_second = second - sub_f
cross_sub = FR.JOBS['trips_day']['ref'] * 0.6 * 365 / 1e6 * 0.75 * (1 - FR.G_CROSS_SHARE)
leg = lambda n, mn, v: n * mn * FR.PEAK * FR.CROWD_PEN * v / 60 / 1000
crowd = {'F': leg(sub_f, 10.0, N.VOT_IDF) + leg(cross_sub, 15.0, N.VOT_IDF), 'T': leg(ter_second, 10.0, N.VOT_IDF) + leg(FR.TGV_CROSS_TODAY, 20.0, N.VOT_LD)}
crowd = {k: v / sum(crowd.values()) for k, v in crowd.items()}

fleet = {k: n * c for k, (n, c) in FR.FLEET.items()}; f_sub = FR.FLEET['Suburban'][1]
g_sets = 11.0 * N.G_TRAINS_H / (N.G_TRAINS_H + 23) - N.G_STOP_SETS           # the suburban trainsets saved, shared as the trains of the busiest hour (12 and 23), less those the Chatelet stop takes
sets = {'T': fleet['TGV'] + fleet['TER'], 'G': g_sets * f_sub, 'F': fleet['Suburban'] - g_sets * f_sub}; sets = {k: v / sum(sets.values()) for k, v in sets.items()}
g_run = N.G_STOP_RUN / m['om_trains']

one = lambda p: {p: 1.0}
SHARE = {FR.CONSTRUCTION: c_share, FR.RENEWAL: km_share, FR.RUNNING: om_share, FR.EXTRA_TRAINS: {'T': 1 - g_run, 'G': g_run},
         FR.TGV_REGION: one('T'), FR.TGV_CROSS: one('T'), FR.CAPACITY: one('T'), FR.REG_PARIS: reg, FR.CORRIDOR: one('F'), FR.TER_CROSS: one('T'), FR.COMFORT: one('F'),
         FR.PRODUCERS: one('T'), FR.TRAINSETS: sets, FR.TERMINALS: one('S'), FR.CARBON_CAR: one('T'),
         FR.JOB_USERS: {'F': 1 - FR.G_CROSS_SHARE, 'G': FR.G_CROSS_SHARE}, FR.G_STOP_ITEM: one('G'), FR.G_CROWD: one('G'), FR.CROWD: crowd,
         FR.PLOTS: one('S'), FR.PARKS: one('S'), FR.RESIGNAL: one('S'), FR.NOISE: one('S'),
         FR.BYPASS_ITEM: one('T'), FR.AIR_USERS: one('T'), FR.FRANCE_FARES: one('T'), FR.AIR_CO2: one('T'), FR.CAR_FRANCE: one('T'), FR.TIMETABLE: one('T'), FR.MARGIN: one('T'),
         FR.BUILD_CO2: c_share}
part = {p: {} for p in PARTS}                                   # part -> item -> yearly flow
for k, s in SHARE.items():
    for p in PARTS: part[p][k] = scale(ITEMS[k], s.get(p, 0.0))
# roads: the cars taken off by new TGV journeys go to the triangle, the relief of the suburban roads follows the regional gain
roads_reg = [m['reg_paris'] * FR.DECONGEST * fsd(t) * vot(t) if t >= FR.OPEN else 0.0 for t in YEARS]
for p in PARTS: part[p][FR.ROADS] = scale(roads_reg, reg.get(p, 0.0))
part['T'][FR.ROADS] = plus(part['T'][FR.ROADS], [a - b for a, b in zip(ITEMS[FR.ROADS], roads_reg)])
# cost of public funds: 20% of each part's net public money (french.official_streams, the income shared by who pays it)
ri = m['ops_rev_items']; fee_km = {'T': sum(N.CORRIDOR_KM[c] for c in N.TER_CORRIDORS), 'F': KM['F'], 'G': KM['G']}
inc = {p: 0.0 for p in PARTS}
inc['T'] += ri['Charge on high-speed passengers'] + ri['Fares from new regional express passengers'] + ri['Shops in the new station halls'] + ri['Charge on regional express passengers']
for p in 'TFG':
    inc[p] += ri['Fee paid by the regional transport authority'] * fee_km[p] / sum(fee_km.values()) + ri['Share of the operators’ saving on trainsets'] * sets[p]
    inc[p] += ri['New Navigo pass holders'] * {'T': 0.0, 'F': reg['F'] / (reg['F'] + reg['G']), 'G': reg['G'] / (reg['F'] + reg['G'])}[p]
assert abs(sum(inc.values()) - (m['ops_rev'] - ri['Track charges on new TGV journeys'])) < 1e-9
tgv_rev = m['rev_paris'] + 2.0 * m['rev_cross_one']; tax = m['tax']['VAT inside the new ticket money'] + m['tax']['Fuel duty lost on car trips moved to rail']
for p in PARTS:
    s = []
    for i, t in enumerate(YEARS):
        pub = -(part[p][FR.CONSTRUCTION][i] + part[p][FR.RENEWAL][i] + part[p][FR.RUNNING][i] + part[p][FR.EXTRA_TRAINS][i])
        if t >= FR.OPEN:
            pub -= inc[p] * min(fld(t), 1 + (FR.PATHS_PROJ / FR.PATHS_TODAY - 1))
            if p == 'T': pub -= tgv_rev * N.TRACK_SHARE * (1 - FR.WEAR) * min(fld(t), 1.5) + tax
        s.append(-FR.COFP * pub)
    part[p][FR.COFP_ITEM] = s
fr_c = FR.france(1)
t_added = [FR.COFP * fr_c['track_public'] * min(fld(t), 1.5) * (t >= FR.OPEN) for t in YEARS]
part['T'][FR.COFP_ADDED] = t_added; part['S'][FR.COFP_ADDED] = [a - b for a, b in zip(ITEMS[FR.COFP_ADDED], t_added)]
for p in 'FG': part[p][FR.COFP_ADDED] = zero()
for k in ITEMS:                                                 # the parts add up to the plan, item by item and year by year
    tot = plus(*[part[p][k] for p in PARTS]); assert max(abs(a - b) for a, b in zip(tot, ITEMS[k])) < 1e-9, k
COST_ITEMS = [k for k in ITEMS if pv(ITEMS[k]) < 0]


def tally(streams):
    """Present values of a set of flows {item: yearly flow}: benefits, costs, net, ratio (items sorted as in the plan)."""
    b = sum(pv(s) for k, s in streams.items() if k not in COST_ITEMS); c = -sum(pv(s) for k, s in streams.items() if k in COST_ITEMS)
    return {'pv_benefits': round(b, 2), 'pv_costs': round(c, 2), 'npv': round(b - c, 2), 'ratio': round(b / c, 2) if c else None}
def merge(*ps):
    return {k: plus(*[p[k] for p in ps]) for k in ITEMS}
whole = tally(merge(*[part[p] for p in PARTS])); ref = FR.evaluate(m, 1)
assert abs(whole['npv'] - ref['npv']) < 0.01 and abs(whole['ratio'] - ref['ratio']) < 0.01, (whole, ref['npv'], ref['ratio'])
y0 = IX[FR.OPEN]
def first_year(p): return {'benefits': round(sum(s[y0] for k, s in part[p].items() if k not in COST_ITEMS), 3), 'running': round(-part[p][FR.RUNNING][y0] - part[p][FR.EXTRA_TRAINS][y0], 3)}
parts_out = {p: dict(tally(part[p]), name=NAMES[p], capex=round(cost[p]['central'], 2) if p in cost else 0.0, capex_low=round(cost[p]['low'], 2) if p in cost else 0.0,
                     capex_high=round(cost[p]['high'], 2) if p in cost else 0.0, first_year=first_year(p),
                     items={k: round(pv(s), 2) for k, s in part[p].items() if abs(pv(s)) >= 0.005}) for p in PARTS}
combos = {'T': tally(part['T']), 'T+F': tally(merge(part['T'], part['F'])), 'T+G': tally(merge(part['T'], part['G'])), 'F+G+S': tally(merge(part['F'], part['G'], part['S'])),
          'F+S': tally(merge(part['F'], part['S'])), 'G+S': tally(merge(part['G'], part['S'])), 'plan': whole}

# ---------------------------------------------------------------- 2. the stages: each part opens in its own year
BUILD = (FR.CONSTRUCTION, FR.BUILD_CO2); FIXED = (FR.RENEWAL, FR.RESIGNAL)
def cofp_split(p):
    """The cost of public funds of a part, in what follows the works, what follows the renewals, and what follows the opening."""
    b = [-FR.COFP * -part[p][FR.CONSTRUCTION][i] for i in range(NY)]; f = [-FR.COFP * -part[p][FR.RENEWAL][i] for i in range(NY)]
    return b, f, [a - x - y for a, x, y in zip(part[p][FR.COFP_ITEM], b, f)]
def timed(p, open_year, build=None, share=1.0, cost_share=None):
    """Flows of part p (or a share of it) opened in open_year. build = (first, last) years of its works; None keeps the plan's
    twelve years. The flows of 2040 onwards keep their calendar values; before 2040 they follow the growth of 2040 to 2041."""
    cs = share if cost_share is None else cost_share; out = {}
    cb, cf, co = cofp_split(p)
    for k, s in part[p].items():
        if k in BUILD or k in FIXED: z = scale(s, cs)
        elif k == FR.COFP_ITEM: z = None
        else:
            z = zero(); g = (s[y0 + 1] / s[y0]) if abs(s[y0]) > 1e-12 else 1.0
            if k in (FR.JOB_USERS,): g = (1 + g_sd) * (1 + g_v)                       # without the land-use ramp, which starts at the opening
            for i, t in enumerate(YEARS):
                if t < open_year: continue
                z[i] = (s[i] if t >= FR.OPEN else s[y0] * g ** (t - FR.OPEN)) * (cs if k in (FR.RUNNING, FR.EXTRA_TRAINS) else share)
        out[k] = z
    g_op = (co[y0 + 1] / co[y0]) if abs(co[y0]) > 1e-12 else 1.0
    op = [((co[i] if t >= FR.OPEN else co[y0] * g_op ** (t - FR.OPEN)) * share if t >= open_year else 0.0) for i, t in enumerate(YEARS)]
    out[FR.COFP_ITEM] = plus(scale(cb, cs), scale(cf, cs), op)
    if build:                                                   # the works of this part on their own years
        a, b = build; n = b - a + 1; tot = sum(part[p][FR.CONSTRUCTION]) * cs
        out[FR.CONSTRUCTION] = [tot / n if a <= t <= b else 0.0 for t in YEARS]
        out[FR.COFP_ITEM] = plus([-FR.COFP * -v for v in out[FR.CONSTRUCTION]], scale(cf, cs), op)
    return out
def later(streams, d):
    """The same flows d years later (the surface is freed d years later)."""
    return {k: ([0.0] * d + s[:NY - d] if d > 0 else list(s)) for k, s in streams.items()}

# the first stage of the Works chapter: TGVs of the north, east and south-east, Nord-Est, Gare de Lyon, RER F. Its share of the
# triangle's gains (ASSUMPTION, item by item):
pairs = N.connecting()['pairs']; cross1 = sum(v['share'] for k, v in pairs.items() if 'Montparnasse' not in k)      # crossings that do not need Montparnasse
lines1 = sum(v for k, v in N.HOUR_TODAY.items() if k != 'Atlantic') / sum(N.HOUR_TODAY.values())                      # TGVs of the three lines of stage 1
access1 = lines1 * 2 / 3                                                                                              # they get two of the three stations (ASSUMPTION)
new1 = (m['rev_paris'] * access1 + 2.0 * m['rev_cross_one'] * cross1) / tgv_rev                                       # new journeys follow the gains
cap1 = (N.HOUR_FULL['Southeast'] - N.HOUR_TODAY['Southeast']) / sum(N.HOUR_FULL[k] - N.HOUR_TODAY[k] for k in N.HOUR_TODAY)
ter1 = N.TER['Est'] / (N.TER['Est'] + N.TER['Nord'] + N.TER['Montparnasse'])                                          # only the eastern TER run through (to Gare de Lyon)
st1 = N.yearly()['stages'] if 'stages' in N.yearly() else None
T1_SHARE = {FR.TGV_REGION: access1, FR.TGV_CROSS: cross1, FR.CAPACITY: cap1, FR.PRODUCERS: new1, FR.CARBON_CAR: new1, FR.ROADS: new1, FR.TIMETABLE: lines1, FR.MARGIN: lines1,
            FR.TRAINSETS: lines1, FR.REG_PARIS: ter1, FR.TER_CROSS: ter1, FR.CROWD: cross1, FR.BYPASS_ITEM: 0.0, FR.AIR_USERS: 0.0, FR.FRANCE_FARES: 0.0, FR.AIR_CO2: 0.0, FR.CAR_FRANCE: 0.0}
b40 = {k: part['T'][k][y0] for k in part['T'] if k not in COST_ITEMS}
t1_ben = sum(b40[k] * T1_SHARE.get(k, 0.0) for k in b40) / sum(b40.values())                # share of the triangle's yearly gains that stage 1 brings
stage1_hard = None
def stage_cost():
    f = up(N.RATE); tun = N.RATE['tunnel_civil'] + N.RATE['tunnel_systems']
    km1 = sum(N.CORRIDOR_KM[c] for c in N.STAGE_CORRIDORS['first'])
    h1 = km1 * tun + (6 + 8) * N.LEN['hs'] * N.RATE['platform_m'] + sum(N.RATE['hall'][h] for h in ('Nord', 'Est', 'Lyon')) + (N.JUNCTIONS['tgv'] - 2) * N.RATE['junction'] + (N.PORTALS['tgv'] - 1) * N.RATE['portal'] + 0.4 + 0.5 + N.RATE['london_hall']
    return h1 * f
t1_cost = stage_cost() / cost['T']['central']                                               # share of the triangle's cost in stage 1 (nordest's stages, without RER F)

def scenario(name, flows, opens):
    t = tally(flows); return dict(t, name=name, opens=opens)
T, F, G, S = (part[p] for p in PARTS)
def t_split(open1, open2):
    """The triangle in two stages: the share of stage 1 from open1, the rest from open2."""
    a = timed('T', open1, share=t1_ben, cost_share=t1_cost); b = timed('T', open2, share=1 - t1_ben, cost_share=1 - t1_cost)
    return merge(a, b)
S1, S2 = 2037, 2040                         # the Works chapter: the first stage opens after nine years, the second after twelve
stages = {
    'counted': scenario('As the economic return counts it: everything opens in 2040', merge(T, F, G, S), {'T': 2040, 'F': 2040, 'G': 2040}),
    'works': scenario('The order of the Works chapter: north, east and south-east TGVs with RER F in 2037, the rest in 2040',
                      merge(t_split(S1, S2), timed('F', S1), timed('G', S2), S), {'T1': S1, 'F': S1, 'T2': S2, 'G': S2}),
    'triangle': scenario('The triangle first: every TGV and TER in 2037, RER F and RER G in 2040', merge(timed('T', S1), timed('F', S2), timed('G', S2), S), {'T': S1, 'F': S2, 'G': S2}),
    'triangle_f': scenario('The triangle and RER F in 2037, RER G in 2040 (if the money of nine years allowed it)', merge(timed('T', S1), timed('F', S1), timed('G', S2), S), {'T': S1, 'F': S1, 'G': S2}),
}
# the suburban tunnels decided later: the triangle paid in the nine years to 2036, RER F and RER G in the three years before they open
tri = timed('T', S1, build=(FR.BUILD_START, S1 - 1))
for d, lab in ((5, 'later5'), (10, 'later10')):
    o = S2 + d
    stages[lab] = scenario('The triangle in 2037, RER F and RER G in %d' % o, merge(tri, timed('F', o, build=(o - 3, o - 1)), timed('G', o, build=(o - 3, o - 1)), later(S, d)), {'T': S1, 'F': o, 'G': o})
stages['no_g'] = scenario('The triangle in 2037, RER F in 2040, no RER G (the surface of Gare de l’Est and Montparnasse not freed)', merge(tri, timed('F', S2, build=(S2 - 3, S2 - 1))), {'T': S1, 'F': S2})
# where the gain of the triangle first comes from: the years between the two openings, item by item (the works are paid in the same years)
_a = merge(T, F, G, S); _b = merge(timed('T', S1), timed('F', S2), timed('G', S2), S); _d = lambda ks: sum(pv(_b[k]) - pv(_a[k]) for k in ks)
_ben = [k for k in ITEMS if k not in COST_ITEMS]; _run = [FR.RUNNING, FR.EXTRA_TRAINS]; _rest = [k for k in COST_ITEMS if k not in _run and k != FR.COFP_ITEM]
early = {'years': S2 - S1, 'benefits_sum': round(sum(_b[k][IX[t]] - _a[k][IX[t]] for k in _ben for t in range(S1, S2)), 2), 'benefits': round(_d(_ben), 2), 'running': round(-_d(_run), 2),
         'public_money': round(_d([FR.COFP_ITEM]), 2), 'works': round(_d(_rest), 2), 'net': round(_d(ITEMS), 2), 'per_year': round(_d(ITEMS) / (S2 - S1), 1),
         'after': round(sum(pv([v if t >= S2 else 0.0 for t, v in zip(YEARS, _b[k])]) - pv([v if t >= S2 else 0.0 for t, v in zip(YEARS, _a[k])]) for k in ITEMS), 2)}
print('EARLY', early)
# how much the order of the Works chapter depends on the share of the triangle's gains given to its first stage
t1_keep = t1_ben; sens1 = {}
for sh in (0.25, 0.5):
    t1_ben = sh; sens1[str(sh)] = tally(merge(t_split(S1, S2), timed('F', S1), timed('G', S2), S))['npv']
t1_ben = t1_keep
stages['triangle_only'] = scenario('The triangle alone in 2037, no suburban tunnel', {k: tri[k] for k in ITEMS}, {'T': S1})
spend = {'triangle_by_2036': round(cost['T']['central'], 1), 'spent_by_2036_at_the_plan_rate': round(capex * 9 / 12, 1), 'stage1_of_the_works_chapter': round(stage_cost() + cost['F']['central'], 1)}

# ---------------------------------------------------------------- 3. RER D on its own pair, with line R, by the rules of the economic return
RD = json.load(open(os.path.join(HERE, '..', 'src', 'sections', 'rerd', 'data.json'))); TM = json.load(open(os.path.join(HERE, '..', 'src', 'sections', 'times', 'data.json')))
VOT_D, DAYS, W_LATE = RD['params']['vot'], RD['params']['days'], RD['params']['w_late']
ALL_TRIPS = TM['k']['factor'] / 2
PEAK_HOURS = 4.0                           # hours a working day the added trains run (ASSUMPTION: two in the morning, two in the evening)
RUN_KM = {'B': 50.0, 'D': 70.0, 'G': 70.0, 'F': 45.0}          # km of an average run of an added train (ASSUMPTION)
ROUND_H = {'B': 2.5, 'D': 3.5, 'G': 3.5, 'F': 2.5}             # hours of a round trip, turnbacks included (ASSUMPTION)
def trains_cost(line, per_hour):
    """bn a year to run per_hour more trains each way at the peaks: train-km at the model's price, and the trainsets."""
    km = per_hour * 2 * PEAK_HOURS * DAYS * RUN_KM[line]; n = per_hour * ROUND_H[line]
    return km * N.REG_TRAINKM_COST / 1e9 + n * f_sub, km, n
r_time = TM['x']['r_only']['hours_day'] * ALL_TRIPS * DAYS * VOT_D / 1e9
d_cost = {l: RD['cost']['own'][l] + RD['cost']['r_fold'][l] for l in ('low', 'central', 'high')}; d_upkeep = RD['cost']['own']['upkeep']
sim = RD['sim']; to_bn = lambda minutes: minutes * W_LATE * VOT_D / 60 * DAYS / 1e9
rd_cases = {
    'today': {'name': 'Today’s trains: RER B 20, RER D 12 and line R 5', 'reliability': RD['value']['own']['reliability'], 'more_trains': 0.0, 'r_time': r_time, 'trains': 0.0},
    'growth': {'name': 'More trains: RER B 24, RER D 16 and line R 5', 'reliability': to_bn(sim['today']['plan']['delay_min'] - sim['growth_r']['six']['delay_min']),
               'more_trains': RD['more']['central'], 'r_time': r_time, 'trains': trains_cost('B', 4)[0] + trains_cost('D', 4)[0]}}
def addon(benefit, running, capex_bn, open_year=FR.OPEN, build=(FR.BUILD_START, FR.OPEN - 1)):
    """Present values of an add-on: yearly gain and running cost at today's values (bn), cost of the works; rules of french.py."""
    a, b = build; n = b - a + 1; B = C = 0.0
    for t in YEARS:
        d = 1 / (1 + R) ** (t - FR.BASE_YEAR)
        if a <= t <= b: C += capex_bn / n * (1 + FR.COFP) * d
        if t >= open_year: B += benefit * fsd(t) * vot(t) * d; C += running * (1 + FR.COFP) * d
    return {'pv_benefits': round(B, 2), 'pv_costs': round(C, 2), 'npv': round(B - C, 2), 'ratio': round(B / C, 2) if C else None}
for c in rd_cases.values():
    c['benefit'] = c['reliability'] + c['more_trains'] + c['r_time']
    c.update({k: round(v, 4) for k, v in c.items() if isinstance(v, float)})
    c['french'] = addon(c['benefit'], d_upkeep + c['trains'], d_cost['central']); c['french_trains_free'] = addon(c['benefit'], d_upkeep, d_cost['central'])
    c['french_low'] = addon(c['benefit'], d_upkeep + c['trains'], d_cost['high']); c['french_high'] = addon(c['benefit'], d_upkeep + c['trains'], d_cost['low'])
    c['with_plan'] = {'npv': round(whole['npv'] + c['french']['npv'], 2), 'ratio': round((whole['pv_benefits'] + c['french']['pv_benefits']) / (whole['pv_costs'] + c['french']['pv_costs']), 3)}
rd_out = {'cost': d_cost, 'upkeep': d_upkeep, 'cases': rd_cases, 'trains_b': trains_cost('B', 4), 'trains_d': trains_cost('D', 4), 'r_hours_day': TM['x']['r_only']['hours_day'],
          'params': {'peak_hours': PEAK_HOURS, 'run_km': RUN_KM, 'round_h': ROUND_H, 'trainkm_cost': N.REG_TRAINKM_COST, 'trainset_year': f_sub, 'all_trips': ALL_TRIPS}}

# ---------------------------------------------------------------- 4. RER B and D: trains on time once riders leave their tunnel
tun = TM['tun']; relief = {}
for name, key in (('plan', 'plan'), ('plan_kr', 'plan_kb_rd'), ('variant', 'variant_c')):
    relief[name] = {l: 1 - tun[key][l] / tun['future'][l] for l in ('b', 'd')}
    relief[name]['both'] = 1 - (tun[key]['b'] + tun[key]['d']) / (tun['future']['b'] + tun['future']['d'])
DOORS = 20.0                               # seconds of a stop that do not depend on the riders: doors, departure (ASSUMPTION)
RID = RD['riders']; PEAK_R, HIT = RD['params']['peak'], RD['params']['hit']; CANCEL = {'B': 4.0, 'D': 8.0}
def trunk(cut):
    """The old tunnel with 20 RER B and 12 RER D, stops shortened as riders leave: minutes of delay the section adds to a rider of each line."""
    d0 = {l: SIM.LINES[l]['dwell'] for l in 'BD'}
    try:
        for l in 'BD': SIM.LINES[l]['dwell'] = DOORS + (d0[l] - DOORS) * (1 - cut[l.lower()])
        x = SIM.run({'B': 20, 'D': 12}, {'B': ['b'], 'D': ['d']}, {'B': ['b'], 'D': ['d']}, SIM.H_NEW)
    finally:
        for l in 'BD': SIM.LINES[l]['dwell'] = d0[l]
    return {'through': x['through'], 'b_s': x['lines']['B']['added_s'], 'd_s': x['lines']['D']['added_s'],
            'rider_min': {l: x['lines'][l]['added_s'] / 60 + x['lines'][l]['cancelled_in_tunnel'] * CANCEL[l] for l in 'BD'}}
base = trunk({'b': 0.0, 'd': 0.0}); bd = {'base': base, 'doors_s': DOORS}
for name, cut in relief.items():
    x = trunk(cut)                                              # the riders who stay see less delay; those who left are counted with the line they take
    mins = sum(RID[l] * (1 - cut[l.lower()]) * PEAK_R * HIT * (base['rider_min'][l] - x['rider_min'][l]) for l in 'BD')
    bd[name] = dict(x, relief=round(cut['both'], 3), relief_b=round(cut['b'], 3), relief_d=round(cut['d'], 3), minutes_day=round(mins, -3), year=round(to_bn(mins), 4), french=addon(to_bn(mins), 0.0, 0.0))
counted = {'g_crowd_year': round(ITEMS[FR.G_CROWD][y0], 3), 'crowd_year': round(ITEMS[FR.CROWD][y0], 3), 'g_crowd_pv': round(pv(ITEMS[FR.G_CROWD]), 2), 'crowd_pv': round(pv(ITEMS[FR.CROWD]), 2)}

# more trains in the two suburban tunnels: what four more an hour bring and cost (the rule of the annex 'rerd': wait and crowding)
FLOW = json.load(open(os.path.join(HERE, '..', 'src', 'sections', 'flows', 'data.json')))
def more(line, riders, n0, n1, branches):
    """bn a year: riders wait less (a quarter of the cut in the interval of their branch, counted once) and stand less."""
    pk = riders * PEAK_R; i0, i1 = 60.0 * branches / n0, 60.0 * branches / n1
    wait = pk * (i0 - i1) / 4; crowd = pk * HIT * 20 * 0.4 * (1 - n0 / n1)                   # 20 minutes aboard; crowding weight 0.40 down with the load of a train
    gain = (wait + crowd) * VOT_D / 60 * DAYS / 1e9; run, km, sets_n = trains_cost(line, n1 - n0)
    return {'from': n0, 'to': n1, 'gain': round(gain, 3), 'running': round(run, 3), 'net': round(gain - run, 3), 'french': addon(gain, run, 0.0)}
room = {'G': dict(more('G', FLOW['key']['pn'], 12, 16, 3), platform_limit=20), 'F': dict(more('F', FLOW['k']['hkl'], 23, 27, 4), platform_limit=32)}

# what the two suburban tunnels lack to pay for themselves, and to match the plan
sub = tally(merge(F, G, S)); need = {'to_pay': round(sub['pv_costs'] - sub['pv_benefits'], 2), 'to_match_plan': round(sub['pv_costs'] * whole['ratio'] - sub['pv_benefits'], 2)}
per_bn_year = addon(1.0, 0.0, 0.0)['pv_benefits']               # present value of one bn a year from 2040 (growing as the suburban gains do)
need['to_pay_year'] = round(need['to_pay'] / per_bn_year, 3); need['to_match_plan_year'] = round(need['to_match_plan'] / per_bn_year, 3)

out = {'parts': parts_out, 'combos': combos, 'shares': {'cost': c_share, 'stage1_of_triangle_gains': round(t1_ben, 3), 'stage1_of_triangle_cost': round(t1_cost, 3),
                                                       'stage1_items': {k: round(v, 3) for k, v in T1_SHARE.items()}, 'regional_by_part': reg, 'crowding_by_part': crowd},
       'stages': stages, 'early': early, 'stage1_sensitivity': sens1, 'spend': spend, 'rerd': rd_out, 'bd': bd, 'counted_crowding': counted, 'relief': relief, 'room': room, 'need': need}
json.dump(out, open(os.path.join(FR.OUT, 'levers.json'), 'w'), indent=1, ensure_ascii=False)

# the annex 'parts' reads the same figures, with short keys for the items it names and whole widths for its bars
KEYS = {'job': FR.JOB_USERS, 'g_stop': FR.G_STOP_ITEM, 'g_crowd': FR.G_CROWD, 'crowd': FR.CROWD, 'reg': 'Regional travellers: the Paris side of their trip', 'sets': 'Trainsets saved: trains no longer wait in a terminal'}
top = max(max(v['pv_benefits'], v['pv_costs']) for v in parts_out.values()); top_s = max(v['npv'] for v in stages.values())
page = dict(out, k={q: {k: parts_out[q]['items'].get(n, 0.0) for k, n in KEYS.items()} for q in 'TFG'},
            bar={'parts': {q: {'b': int(round(100 * v['pv_benefits'] / top)), 'c': int(round(100 * v['pv_costs'] / top))} for q, v in parts_out.items()},
                 'stages': {q: int(round(100 * v['npv'] / top_s)) for q, v in stages.items()}},
            years={'counted': FR.OPEN, 'first': FR.OPEN - 3, 'build_start': FR.BUILD_START})
json.dump(page, open(os.path.join(HERE, '..', 'src', 'sections', 'parts', 'data.json'), 'w'), indent=1, ensure_ascii=False)
if __name__ == '__main__':
    print('PARTS'); [print('  %-34s capex %5.1f  PV benefits %6.2f  PV costs %6.2f  NPV %6.2f  ratio %s   first year %s' % (v['name'], v['capex'], v['pv_benefits'], v['pv_costs'], v['npv'], v['ratio'], v['first_year'])) for v in parts_out.values()]
    print('COMBOS'); [print('  %-8s %s' % (k, v)) for k, v in combos.items()]
    print('STAGE 1 share of the triangle: gains %.2f, cost %.2f' % (t1_ben, t1_cost), spend, 'works-order NPV if that share were', sens1)
    print('STAGES'); [print('  NPV %6.2f  ratio %.2f  %s' % (v['npv'], v['ratio'], v['name'])) for v in stages.values()]
    print('RER D'); [print('  ', k, {a: b for a, b in v.items()}) for k, v in rd_cases.items()]; print('  trains', rd_out['trains_b'], rd_out['trains_d'])
    print('B+D', bd); print('counted', counted); print('ROOM', room); print('NEED', need)
