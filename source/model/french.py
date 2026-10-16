"""The economic return under the French appraisal rules, with the complete list of benefits.

Two readings of the same project, both built on nordest.py (access, traffic, cost) and finance.py (the two accounts):
- the study's own reading: the benefits of the opening year, at today's traffic, held flat for 60 years at 3%, against the
  yearly cost of finance.py (repayment of construction plus running costs);
- the French method (Instruction of 16 June 2014 and the DGITM fiches-outils of May 2019, see the sources of the economy
  section): one real discount rate of 4.5%, construction from 2028, opening in 2040, explicit years to 2070, residual value
  2071-2140 with flows held flat, values of time growing 0.84% a year (elasticity 0.7 to GDP per head at +1.2%), long-distance
  traffic +1.2% a year and short-distance +0.3% until 2070, the official carbon path, a cost of public funds of 1.2 on net
  public money, producers' balances counted, wider effects reported apart from the headline net present value (NPV).

The list of benefits is the complete one of the two study notes of 15 and 16 October 2026 (/evaluation and /benefits-deep-study
in the project files): the official items first, then the items valued in the deep study, each with a low, central and high
value. Where an added item replaces a rougher term of the official list (suburb-to-suburb users for the corridor estimate,
crowding relief for the borrowed comfort ratio), the rougher term is switched off. The borrowed wider-effect ratios of the
Grand Paris Express appraisal are computed but not used: the measured wider effects (W1 to W5) take their place.

Inputs that come from outside the model are named constants below with their source or the mark ASSUMPTION; the job-access
results of the demand model fitted on the INSEE census and the IDFM timetable are read from inputs/job_access.json.

    python3 model/french.py        -> model/outputs/french.json (about one minute: the traffic model runs once)

Money in billions of 2026 euros; present values discounted to 2026.
"""
import json, math, os, io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import nordest as N
    import finance as F

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'outputs')
JOBS = json.load(open(os.path.join(HERE, 'inputs', 'job_access.json')))

# ------------------------------------------------------------------ timing
BASE_YEAR, BUILD_START, OPEN, LAST, RESID_END = 2026, 2028, 2040, 2070, 2140      # 12 years of works (model), open 2040 (ASSUMPTION)
YEARS = list(range(BUILD_START, RESID_END + 1))

# ------------------------------------------------------------------ French method parameters (DGITM fiches V.1 to V.8, May 2019; see sources fr_*)
R_FR = 0.045                 # the single real rate used in rail and road dossiers
R_PUBLIC_2021 = 0.032        # the revised public rate of 2021 at beta 1, shown as a test
VOT_GROWTH = 0.7 * 0.012     # values of time: elasticity 0.7 to GDP per head, which grows 1.2% a year
LD_GROWTH, SD_GROWTH = 0.012, 0.003      # long-distance and short-distance demand, reference scenario, to 2070
COFP = 0.20                  # cost of public funds: each euro of net public money counts 1.2
EUR2015 = 1.22               # euros of 2026 per euro of 2015 (ASSUMPTION: consumer prices; no official deflator retrieved)
CARBON_2015 = {2018: 53, 2030: 246, 2040: 491, 2050: 763, 2060: 1184}      # euros of 2015 a tonne, flat after 2060

# ------------------------------------------------------------------ the full service level and busy-hour capacity
PATHS_TODAY, PATHS_REF, PATHS_PROJ = 36.0, 39.5, 46.0     # TGV paths each way in the busy hour: today, without the project, with it
PEAK_SHARE = 0.5             # share of TGV journeys in the hours that run full (ASSUMPTION: about 5 to 6 hours a weekday)
CAP_VALUE = 20.0             # euros a journey the network cannot carry in the busy hours without the project (ASSUMPTION; 15 to 40)
CAP_LOST = 0.5               # share of those journeys lost rather than moved to another hour (ASSUMPTION)

# ------------------------------------------------------------------ producers (operators and the track owner)
OPERATOR_MARGIN = 0.10       # operator margin on the fare of a new TGV journey, after track charges (ASSUMPTION)
WEAR = 0.15                  # share of track charges that pays for the extra wear (ASSUMPTION)
FLEET = {'TGV': (17, 3.1e-3), 'TER': (4.5, 2.0e-3), 'Suburban': (11.0, 2.0e-3)}      # trainsets freed by through running and their yearly cost (derived)
TERMINAL_UPKEEP = 0.030      # bn a year: surface throats and track fields that close, about 150 track-km plus switches (derived, 0.02 to 0.05)

# ------------------------------------------------------------------ car trips avoided (the model's carbon assumption) and road externalities
CAR_SHARE, TRIP_KM, KG_PKM, OCC = 0.25, 450, 0.10, 2.2      # as nordest.py (extras co2_kt) and finance.py TAX
ROAD_EXT = 2.15e-2           # euros of 2015 a car-km: pollution, accidents once rates halve, noise, interurban (DGITM V.2; derived)
DECONGEST = 1.31 / 14.2      # road decongestion against transport effects in the Grand Paris Express appraisal

# ------------------------------------------------------------------ the official corridor estimate (replaced by the job-access model) and borrowed ratios
CORRIDORS = {'H/K and L': {'today': (0.6, 3.0, 6.0), 'saving': 23.0, 'uplift': 2.0},
             'P and N': {'today': (0.2, 0.8, 1.1), 'saving': 45.5, 'uplift': 2.52}}
TGV_WIDER_SHARE = 0.25       # the study's borrowed ratio for TGV links (British practice 20 to 30%); computed, not used
AGGLO_ELAST = (0.02, 0.04)   # productivity to effective density: French central and British
GDP_PER_JOB = 0.1e-3         # bn of output a job in the outer suburbs (ASSUMPTION)

# ------------------------------------------------------------------ the items valued in the deep study (low, central, high)
P = {
 'jobs_users': (JOBS['users_low'], JOBS['users_central'], JOBS['users_high']),                       # bn a year, users of the through suburban lines
 'jobs_agglo': tuple(JOBS['agglomeration'][k] for k in ('low', 'central', 'high')),                  # bn a year, denser job markets
 'jobs_labour': tuple(JOBS['labour'][k] for k in ('low', 'central', 'high')),                        # bn a year, people into work
 'jobs_better': tuple(JOBS['better_jobs'][k] for k in ('low', 'central', 'high')),                   # bn a year, moves to better jobs
 'land': (0.1, 0.7, 2.2), 'parks': (-0.1, -0.05, 0.2),        # bn once, freed land sold for building net of works; parks net of creation and upkeep (research note on land)
 'tgv_elast': (0.02, 0.04, 0.125), 'business_share': (0.18, 0.25, 0.33),   # elasticity of output to market access between cities; business share of TGV trips
 'resignal': (0.05, 0.15, 0.30),                              # bn once in 2036: old terminal signal boxes not renewed
 'punct_points': (-3.0, 0.0, 3.0),                            # change in punctuality of the merged suburban lines, points
 'noise': (0.003, 0.0055, 0.008),                             # bn a year: rail noise removed along the approaches that close
 'air_dom': (250e3, 430e3, 650e3), 'air_lon': (90e3, 170e3, 250e3),      # air passengers a year who switch to rail, domestic and London
 'margin_min': (0.0, 2.5, 5.0),                               # minutes later a TGV passenger arrives for a train at a known through platform (ASSUMPTION)
 'build_co2': (1.0, 1.4, 2.3), 'disruption': (-2.5, -1.2, -0.4),          # Mt CO2e of the works; bn once, disruption to today's trains during the works
}
LEVELS = ('low', 'central', 'high')
AIR_CO2_T = 133e3            # tonnes CO2e a year avoided at the central shift (0.3 kg a passenger-km with contrails, ADEME)
FARE_DOM, FARE_LON = 80.0, 130.0      # average rail fare of a switched journey, euros (ASSUMPTION)
USER_GAIN_AIR = 15.0         # euros of gain for each traveller who switches, rule of a half (ASSUMPTION)
CROWD_PEN = 0.40             # extra equivalent minute per minute ridden in a crowded metro or RER leg: 60% standing at 1.52, 40% seated at 1.08 (DGITM comfort factors; derived)
PEAK = 0.5                   # share of the relieved trips made in the crowded hours (ASSUMPTION)
EXTERNAL = 0.7               # relief to the riders left on board, as a share of a rider's own crowding (derived)
TGV_CROSS_TODAY = 5.2        # million TGV journeys across Paris today (the model's CONN, rounded)
PUNCT_TRIPS = 190e6          # trips a year on lines H, K, L, P and N (model counts, L added; ASSUMPTION)
PARIS_GDP = 800.0            # Ile-de-France output, bn (ASSUMPTION, rounded)
X_TODAY, X_PROJ = 50.0, 25.0 # minutes between arriving in Paris and leaving it for another region: today, and with the project (ASSUMPTION)
CITIES = {'Lille': ('N', 60, 62), 'Strasbourg': ('E', 32, 106), 'Reims': ('E', 12, 46), 'Metz': ('E', 13, 84), 'Nancy': ('E', 13, 90),
          'Lyon': ('S', 95, 117), 'Marseille': ('S', 75, 195), 'Nice': ('S', 40, 330), 'Montpellier': ('S', 30, 200), 'Grenoble': ('S', 25, 180),
          'Dijon': ('S', 13, 95), 'Toulon': ('S', 20, 240), 'Avignon': ('S', 10, 160), 'Bordeaux': ('A', 55, 124), 'Nantes': ('A', 45, 128),
          'Rennes': ('A', 35, 85), 'Toulouse': ('A', 60, 260), 'Tours': ('A', 14, 60), 'Le Mans': ('A', 10, 55), 'Angers': ('A', 12, 95), 'Brest': ('A', 10, 215)}
VIA_PARIS = {frozenset('NS'): 0.5, frozenset('NA'): 0.5, frozenset('ES'): 0.6, frozenset('EA'): 0.8, frozenset('AS'): 0.6, frozenset('NE'): 0.0}
LAND_YEARS = (2043, 2055); RESIGNAL_YEAR = 2036; DISRUPT_START = 2030

# ------------------------------------------------------------------ names of the items, in the order the page shows them
OFFICIAL = ['Construction', 'Renewal of rail systems', 'Running tunnels and stations', 'Extra regional train running',
            'TGV time: Paris region', 'TGV time: crossing Paris', 'TGV capacity in the busy hours', 'Regional time: Paris side',
            'Regional time: suburb to suburb across Paris', 'TER time: crossing Paris', 'Comfort on relieved lines',
            'Producers: margins and track charges on new TGV journeys', 'Trainsets freed by through running', 'Upkeep of surface terminals saved',
            'Carbon', 'Road accidents, noise, pollution, congestion', 'Cost of public funds',
            'Wider: suburban job markets (study ratio)', 'Wider: TGV links', 'Wider: agglomeration, French elasticity']
BORROWED = ('Wider: suburban job markets (study ratio)', 'Wider: TGV links', 'Wider: agglomeration, French elasticity')
ADDED = ['1. Job access: suburb-to-suburb users', '2. Freed land (net sale value)', '2. Parks (amenity less upkeep)',
         '3. Crowding relief (replaces the borrowed comfort ratio)', '5. Signal boxes not renewed', '6. Reliability of the merged lines',
         '7. Noise along the closed approaches', '8. Shift from air: carbon', '8. Shift from air: travellers and operators',
         '10. Departure margin at through platforms', '11. Carbon of the works', '11. Disruption during the works',
         'Public funds on the items above',
         'W1. Job access: agglomeration', 'W2. Job access: people into work', 'W3. Job access: better jobs',
         'W4. TGV links: market access', 'W5. TGV links: imperfect competition']
JOB_USERS, CROWD = ADDED[0], ADDED[3]
WIDER_ADDED = [k for k in ADDED if k.startswith('W')]

# Families used by the site to show the benefits at a glance (every item above belongs to exactly one)
FAMILIES = [
    ('Passengers’ time', ['TGV time: Paris region', 'TGV time: crossing Paris', 'Regional time: Paris side', 'Regional time: suburb to suburb across Paris', 'TER time: crossing Paris']),
    ('Room for more trains in the busy hours', ['TGV capacity in the busy hours']),
    ('The railway’s own gains', ['Producers: margins and track charges on new TGV journeys', 'Trainsets freed by through running', 'Upkeep of surface terminals saved']),
    ('Comfort and ease', ['Comfort on relieved lines', '3. Crowding relief (replaces the borrowed comfort ratio)', '10. Departure margin at through platforms', '8. Shift from air: travellers and operators', '6. Reliability of the merged lines']),
    ('Job access across Paris', ['1. Job access: suburb-to-suburb users']),
    ('Environment', ['Carbon', 'Road accidents, noise, pollution, congestion', '7. Noise along the closed approaches', '8. Shift from air: carbon']),
    ('Land, parks and one-off savings', ['2. Freed land (net sale value)', '2. Parks (amenity less upkeep)', '5. Signal boxes not renewed']),
    ('Costs of the works themselves', ['11. Carbon of the works', '11. Disruption during the works']),
    ('Construction and running costs', ['Construction', 'Renewal of rail systems', 'Running tunnels and stations', 'Extra regional train running']),
    ('Cost of public funds', ['Cost of public funds', 'Public funds on the items above']),
    ('Wider effects, measured', ['W1. Job access: agglomeration', 'W2. Job access: people into work', 'W3. Job access: better jobs', 'W4. TGV links: market access', 'W5. TGV links: imperfect competition']),
]
FAMILY_OF = {k: f for f, ks in FAMILIES for k in ks}
assert set(FAMILY_OF) == set(OFFICIAL + ADDED) - set(BORROWED), set(OFFICIAL + ADDED) - set(BORROWED) ^ set(FAMILY_OF)


def by_family(items):
    """Sums a dict of item values by family, in the order of FAMILIES; families with no item are left out."""
    out = {}
    for f, ks in FAMILIES:
        v = [items[k] for k in ks if k in items]
        if v: out[f] = sum(v)
    return out


def model_figures():
    """What the project model gives: traffic, benefits, cost and running cost of the opening year at today's traffic."""
    Y = N.yearly(); base = F.make_base(); A = F.accounts(base)
    C = N.cost(); CL, CH = N.cost(N.RATE_LOW), N.cost(N.RATE_HIGH)
    reg = N.regional()
    sys_cost = C['items']['Tunnels, rail systems'] * (1 + N.RATE['design'] + N.RATE['client']) * (1 + N.RATE['risk'])
    ter_users = sum(N.TER.values()); ter_cross_today = ter_users * N.TER_THROUGH_SHARE
    ter_cross_new = Y['through_ter'] - ter_cross_today
    ter_saving = 35.0 * 1.5 - N.TR['M']                          # today's change across Paris weighted 1.5, less the 7-minute ride
    return {'Y': Y, 'A': A, 'cost': C['total'], 'cost_low': CL['total'], 'cost_high': CH['total'], 'hard': C['hard'], 'items': C['items'],
            'tunnel_km': C['tunnel_km'], 'platform_m': C['platform_total'], 'tracks': C['tracks_total'], 'systems': sys_cost,
            'om_infra': Y['om_infra'], 'om_trains': Y['om_trains'],
            'tgv_access': Y['tgv_access_benefit'], 'tgv_cross': Y['tgv_conn_benefit'], 'tgv_new': Y['tgv_journeys'], 'tgv_revenue': Y['tgv_revenue'],
            'rev_paris': Y['tgv_access_journeys'] * N.FARE / 1000, 'rev_cross_one': Y['tgv_conn_journeys'] * N.FARE / 1000,
            'reg_paris': reg['paris_benefit'], 'reg_cross_model': reg['cross_benefit'], 'comfort': Y['comfort'], 'wider_model': Y['wider'],
            'ter_cross': (ter_cross_today * ter_saving / 60 + ter_cross_new * ter_saving / 120) * N.VOT_TER / 1000,
            'new_reg': Y['reg_journeys'], 'ops_rev': A['ops_rev_total'], 'ops_rev_items': A['ops_rev'], 'tax': A['tax'],
            'second_station': reg['second_station_sub'] + reg['second_station_ter'],
            'benefit_model': Y['benefit_total'], 'cost_yearly_model': Y['cost'], 'annuity': A['annuity'], 'renewal_year': A['ops_cost']['Renewal of rail systems, set aside each year'],
            'yearly_cost': A['yearly_cost']}


def corridors(level=1):
    out = {}
    for k, c in CORRIDORS.items():
        d0 = c['today'][level]; n = d0 * (c['uplift'] - 1)
        out[k] = {'today': d0, 'new': n, 'benefit': (d0 * c['saving'] / 60 + n * c['saving'] / 120) * N.VOT_IDF / 1000}
    return out


def agglomeration(elast):
    """The study's own rough agglomeration term on the four corridors (effective density of jobs); computed, not used in the headline."""
    C = {k: N.CORRIDOR[k] for k in ('H', 'P', 'N', 'L')}
    ow = lambda z: C[z][2]
    today = {('H', 'L'): ow('H') + 18 * 1.5 + ow('L'), ('P', 'N'): ow('P') + 35 * 1.5 + ow('N'),
             ('H', 'N'): ow('H') + 35 * 1.5 + ow('N'), ('P', 'L'): ow('P') + 18 * 1.5 + ow('L')}
    proj = {('H', 'L'): ow('H') + N.TR['SL'] + ow('L'), ('P', 'N'): ow('P') + N.TR['M'] + ow('N'),
            ('H', 'N'): ow('H') + N.TR['M'] + 16 + ow('N'), ('P', 'L'): ow('P') + N.TR['SL'] + 16 + ow('L')}
    rest = 6400 - sum(C[z][1] for z in C)
    def ed(z, times):
        v = C[z][1] / 15.0 + rest / 60.0
        for (a, b), t in times.items():
            if z == a: v += C[b][1] / t
            elif z == b: v += C[a][1] / t
        return v
    gain = 0.0
    for z in C:
        e0, e1 = ed(z, today), ed(z, proj)
        gain += elast * (e1 / e0 - 1) * C[z][1] * 1000 * GDP_PER_JOB
    return gain


def carbon(t):
    """Official value of a tonne of CO2 in year t, bn euros of 2026."""
    ys = sorted(CARBON_2015)
    if t >= ys[-1]: v = CARBON_2015[ys[-1]]
    else:
        for a, b in zip(ys, ys[1:]):
            if a <= t <= b: v = CARBON_2015[a] + (CARBON_2015[b] - CARBON_2015[a]) * (t - a) / (b - a); break
    return v * EUR2015 / 1e9


def air_decarb(t):
    """Air emissions per passenger-km fall to half by 2050, then stay (ASSUMPTION: sustainable-fuel mandate; contrails unchanged)."""
    return 1.0 - 0.5 * min(max(t - BASE_YEAR, 0), 2050 - BASE_YEAR) / (2050 - BASE_YEAR)


def growth_opts(o):
    return (o.get('ld_growth', LD_GROWTH), o.get('sd_growth', SD_GROWTH), o.get('vot_growth', VOT_GROWTH))


def official_streams(m, o):
    """Yearly flows of the official list, by item, for the options o: {item: [value per year of YEARS]}, + benefit, - cost."""
    tgv_rev = m['rev_paris'] + o.get('cross_fares', 2.0) * m['rev_cross_one']          # a crossing trip pays two fares (model rule)
    g_ld, g_sd, g_v = growth_opts(o)
    capex = m['cost_' + o['cost']] if o.get('cost') in ('low', 'high') else m['cost']
    cor = corridors(o.get('corridor_level', 1)); cor_ben = sum(c['benefit'] for c in cor.values()) * o.get('corridor_scale', 1.0)
    reg_user = m['reg_paris'] + cor_ben
    comfort = reg_user * N.R_COMFORT
    agg = agglomeration(o.get('agglo_elast', AGGLO_ELAST[0]))
    cap_value = o.get('cap_value', CAP_VALUE)
    flows = {k: [] for k in OFFICIAL}
    tg_today = N.HS_TERMINALS
    for t in YEARS:
        z = {k: 0.0 for k in flows}
        if t < OPEN:
            z['Construction'] = -capex / (OPEN - BUILD_START)
        else:
            te = min(t, LAST)                                  # growth stops in 2070; the residual years are held flat
            vot = (1 + g_v) ** (te - BASE_YEAR)
            D = tg_today * (1 + g_ld) ** (te - BASE_YEAR)
            cap_p = PEAK_SHARE * tg_today * PATHS_PROJ / PATHS_TODAY; cap_r = PEAK_SHARE * tg_today * PATHS_REF / PATHS_TODAY
            carried = min(PEAK_SHARE * D, cap_p) + (1 - PEAK_SHARE) * D
            f_tgv = carried / tg_today                         # TGV traffic against today's, within the project's capacity
            enabled = max(0.0, min(PEAK_SHARE * D, cap_p) - min(PEAK_SHARE * D, cap_r))
            f_sd = (1 + g_sd) ** (te - BASE_YEAR)
            ld_vot = vot * o.get('vot_ld_scale', 1.0)
            z['TGV time: Paris region'] = m['tgv_access'] * f_tgv * ld_vot
            z['TGV time: crossing Paris'] = m['tgv_cross'] * f_tgv * ld_vot
            if o.get('capacity', True):
                z['TGV capacity in the busy hours'] = enabled * (cap_value * ld_vot + CAP_LOST * N.FARE * (N.TRACK_SHARE * (1 - WEAR) + OPERATOR_MARGIN)) / 1000
            z['Regional time: Paris side'] = m['reg_paris'] * f_sd * vot
            z['Regional time: suburb to suburb across Paris'] = cor_ben * f_sd * vot
            z['TER time: crossing Paris'] = m['ter_cross'] * f_sd * vot
            z['Comfort on relieved lines'] = comfort * f_sd * vot
            if o.get('producers', True):
                z['Producers: margins and track charges on new TGV journeys'] = tgv_rev * f_tgv * (N.TRACK_SHARE * (1 - WEAR) + OPERATOR_MARGIN)
                z['Trainsets freed by through running'] = sum(n * c for n, c in FLEET.values())
                z['Upkeep of surface terminals saved'] = TERMINAL_UPKEEP
            car_km = m['tgv_new'] * f_tgv * 1e6 * CAR_SHARE * TRIP_KM / OCC
            decarb = 1.0 if o.get('ame') else max(0.0, (2050 - t) / (2050 - BASE_YEAR))      # reference scenario: road transport carbon-free by 2050
            z['Carbon'] = car_km * OCC * KG_PKM / 1000 * decarb * carbon(t) if o.get('externalities', True) else 0.0
            z['Road accidents, noise, pollution, congestion'] = (car_km * ROAD_EXT * EUR2015 / 1e9 + (m['reg_paris'] + cor_ben) * DECONGEST * f_sd * vot) if o.get('externalities', True) else 0.0
            z['Running tunnels and stations'] = -m['om_infra'] * o.get('om_scale', 1.0)
            z['Extra regional train running'] = -m['om_trains']
            z['Wider: suburban job markets (study ratio)'] = (reg_user + comfort) * N.R_WIDER * f_sd * vot
            z['Wider: TGV links'] = (m['tgv_access'] + m['tgv_cross']) * TGV_WIDER_SHARE * f_tgv * ld_vot
            z['Wider: agglomeration, French elasticity'] = agg * f_sd
        if t in (2070, 2100, 2130):
            z['Renewal of rail systems'] = -m['systems']
        if o.get('cofp', True):
            # net public money: construction, renewal and running, less the project's income, the track charges the public track owner
            # earns on new journeys, and VAT in new tickets less fuel duty lost
            pub = -(z['Construction'] + z['Renewal of rail systems'] + z['Running tunnels and stations'] + z['Extra regional train running'])
            if t >= OPEN:
                te = min(t, LAST); f = (1 + g_ld) ** (te - BASE_YEAR)
                pub -= (m['ops_rev'] - m['ops_rev_items'].get('Track charges on new TGV journeys', 0.0)) * min(f, 1 + (PATHS_PROJ / PATHS_TODAY - 1))
                pub -= tgv_rev * N.TRACK_SHARE * (1 - WEAR) * min(f, 1.5)
                pub -= m['tax']['VAT inside the new ticket money'] + m['tax']['Fuel duty lost on car trips moved to rail']
            z['Cost of public funds'] = -o.get('cofp_rate', COFP) * pub
        for k in flows: flows[k].append(z[k])
    return flows, capex


def crowding(m):
    """Crowding relief, bn a year at today's traffic: riders who no longer take a crowded metro or RER leg, and those left on board."""
    second = m['second_station']                                            # M journeys a year now reaching the second station on their train
    cross_sub = JOBS['trips_day']['ref'] * 0.6 * 365 / 1e6 * 0.75            # suburb-to-suburb trips on improved pairs riding a metro or RER leg today (60%, ASSUMPTION)
    legs = [(second, 10.0, N.VOT_IDF), (cross_sub, 15.0, N.VOT_IDF), (TGV_CROSS_TODAY, 20.0, N.VOT_LD)]      # minutes of crowded leg avoided (ASSUMPTION)
    own = sum(n * mn * PEAK * CROWD_PEN * v / 60 / 1000 for n, mn, v in legs)
    return own * (1 + EXTERNAL), {'second_station_M': second, 'cross_sub_M': cross_sub, 'own': own}


def tgv_agglo(elast):
    """Market access between the regions: output gain, bn a year at today's output, with an effect halving every 30 minutes."""
    d = math.log(2) / 30.0; gain = 0.0
    for a, (ta, ga, xa) in CITIES.items():
        ma = ga + PARIS_GDP * math.exp(-d * xa); dma = 0.0
        for b, (tb, gb, xb) in CITIES.items():
            if a == b: continue
            t0 = xa + xb + (X_TODAY if ta != tb else 15.0); t1 = xa + xb + (X_PROJ if ta != tb else 15.0)
            ma += gb * math.exp(-d * t0)
            s = VIA_PARIS.get(frozenset(ta + tb), 0.0) if ta != tb else 0.0
            dma += s * gb * (math.exp(-d * t1) - math.exp(-d * t0))
        gain += elast * dma / ma * ga
    return gain


_CROWD = {}
def added_streams(m, L, o):
    """Yearly flows of the items valued in the deep study, for level L (0 low, 1 central, 2 high)."""
    if 'v' not in _CROWD: _CROWD['v'] = crowding(m)
    crowd = _CROWD['v'][0]
    g_ld, g_sd, g_v = growth_opts(o)
    tgv_time = m['tgv_access'] + m['tgv_cross']
    rail_new = P['air_dom'][L] * FARE_DOM + P['air_lon'][L] * FARE_LON
    dep = (N.HS_TERMINALS - 2 * N.CONN) / 2                              # M departing TGV journeys a year
    f = {k: [] for k in ADDED}
    for t in YEARS:
        z = {k: 0.0 for k in f}
        te = min(t, LAST)
        vot = (1 + g_v) ** (te - BASE_YEAR); fsd = (1 + g_sd) ** (te - BASE_YEAR)
        fld = min((1 + g_ld) ** (te - BASE_YEAR), 1.5); gdp = (1.015 if g_ld else 1.0) ** (te - BASE_YEAR)
        if t >= OPEN:
            z[JOB_USERS] = P['jobs_users'][L] * fsd * vot
            z[CROWD] = (crowd * [0.6, 1.0, 1.4][L]) * fsd * vot
            z['6. Reliability of the merged lines'] = P['punct_points'][L] * 1.0 * PUNCT_TRIPS * N.VOT_IDF / 60 / 1e9 * fsd * vot     # 1 point = 1 minute a trip
            z['7. Noise along the closed approaches'] = P['noise'][L] * vot
            z['8. Shift from air: carbon'] = AIR_CO2_T * (P['air_dom'][L] + P['air_lon'][L]) / 600e3 * carbon(t) * air_decarb(t)
            z['8. Shift from air: travellers and operators'] = ((P['air_dom'][L] + P['air_lon'][L]) * USER_GAIN_AIR + rail_new * (N.TRACK_SHARE * (1 - WEAR) + OPERATOR_MARGIN)) / 1e9 * fld
            z['10. Departure margin at through platforms'] = dep * P['margin_min'][L] / 60 * 1.5 * N.VOT_LD / 1000 * fld * vot
            z['W1. Job access: agglomeration'] = P['jobs_agglo'][L] * fsd * gdp
            z['W2. Job access: people into work'] = P['jobs_labour'][L] * fsd * vot
            z['W3. Job access: better jobs'] = P['jobs_better'][L] * fsd * vot
            z['W4. TGV links: market access'] = tgv_agglo(P['tgv_elast'][L]) * gdp
            z['W5. TGV links: imperfect competition'] = 0.1 * P['business_share'][L] * tgv_time * fld * vot
        if LAND_YEARS[0] <= t <= LAND_YEARS[1]:
            n = LAND_YEARS[1] - LAND_YEARS[0] + 1
            z['2. Freed land (net sale value)'] = P['land'][L] / n; z['2. Parks (amenity less upkeep)'] = P['parks'][L] / n
        if t == RESIGNAL_YEAR: z['5. Signal boxes not renewed'] = P['resignal'][L]
        if BUILD_START <= t < OPEN:
            z['11. Carbon of the works'] = -P['build_co2'][L] * 1e6 * carbon(t) / (OPEN - BUILD_START)
        if DISRUPT_START <= t < OPEN:
            z['11. Disruption during the works'] = P['disruption'][L] / (OPEN - DISRUPT_START)
        if o.get('cofp', True):
            pub = z['2. Freed land (net sale value)'] + z['5. Signal boxes not renewed'] + rail_new * N.TRACK_SHARE * (1 - WEAR) / 1e9 * (t >= OPEN)
            z['Public funds on the items above'] = o.get('cofp_rate', COFP) * pub
        for k in f: f[k].append(z[k])
    return f


def npv(flows, r, keys, base=BASE_YEAR):
    return sum(v / (1 + r) ** (t - base) for k in keys for t, v in zip(YEARS, flows[k]))


def irr(flows, keys):
    lo, hi = -0.05, 0.25
    if npv(flows, lo, keys) < 0: return None
    for _ in range(100):
        mid = (lo + hi) / 2
        if npv(flows, mid, keys) > 0: lo = mid
        else: hi = mid
    return (lo + hi) / 2


def evaluate(m, level=1, r=R_FR, only=None, drop=None, o=None):
    """The French reading. level: 0, 1, 2 for the added items; only: added items to include (None = all, [] = none);
    drop: added items to leave out; o: options of the official streams (cost, growth, capacity, producers...)."""
    o = dict({'cost': 'central'}, **(o or {}))
    add = added_streams(m, level, o)
    keep = [k for k in ADDED if (only is None or k in only) and not (drop and k in drop)]
    replace_corridor = JOB_USERS in keep
    fl, capex = official_streams(m, dict(o, corridor_scale=0.0) if replace_corridor else o)
    if CROWD in keep: fl = dict(fl); fl['Comfort on relieved lines'] = [0.0] * len(YEARS)
    head = [k for k in fl if k not in BORROWED]
    pv = {k: npv(fl, r, [k]) for k in fl}
    pva = {k: npv(add, r, [k]) for k in keep}
    hk = [k for k in keep if not k.startswith('W')]; wk = [k for k in keep if k.startswith('W')]
    npv_head = sum(pv[k] for k in head) + sum(pva[k] for k in hk)
    npv_wider = npv_head + sum(pva[k] for k in wk)
    pv_capex = -pv['Construction']
    allfl = {**{k: fl[k] for k in head}, **{k: add[k] for k in hk}}
    allw = {**allfl, **{k: add[k] for k in wk}}
    pvs = {**{k: pv[k] for k in head}, **pva}
    pos = {k: v for k, v in pvs.items() if not k.startswith('W')}
    pv_benefits = sum(v for v in pos.values() if v > 0); pv_costs = -sum(v for v in pos.values() if v < 0)
    wider_pv = sum(pva[k] for k in wk)
    return {'npv': npv_head, 'per_euro': npv_head / pv_capex, 'irr': irr(allfl, list(allfl)), 'npv_wider': npv_wider,
            'per_euro_wider': npv_wider / pv_capex, 'irr_wider': irr(allw, list(allw)),
            'pv_benefits': pv_benefits, 'pv_costs': pv_costs, 'ratio': pv_benefits / pv_costs, 'ratio_wider': (pv_benefits + wider_pv) / pv_costs,
            'pv_wider': wider_pv, 'pv_borrowed': {k: pv[k] for k in BORROWED},
            'pv': pvs, 'pv_families': by_family(pvs), 'pv_capex': pv_capex, 'capex': capex, 'level': LEVELS[level], 'rate': r,
            'first_year': {**{k: fl[k][OPEN - BUILD_START] for k in head}, **{k: add[k][OPEN - BUILD_START] for k in keep}}}


def study_method(m, level=1):
    """The study's own reading with the complete list: opening-year flows at today's traffic and today's values (no growth, no cost of
    public funds; cars not decarbonised, as the study's carbon figure), held flat for 60 years at 3% against the yearly cost of finance.py.
    One-off items (land, signal boxes, works) have no yearly value and are listed apart."""
    o = {'cost': 'central', 'ld_growth': 0.0, 'sd_growth': 0.0, 'vot_growth': 0.0, 'cofp': False, 'ame': True}
    add = added_streams(m, level, o)
    fl, capex = official_streams(m, dict(o, corridor_scale=0.0))
    fl['Comfort on relieved lines'] = [0.0] * len(YEARS)
    i = OPEN - BUILD_START
    first = {k: fl[k][i] for k in fl if k not in BORROWED}
    first.update({k: add[k][i] for k in ADDED})
    borrowed = {k: fl[k][i] for k in BORROWED}
    yearly = {k: v for k, v in first.items() if v != 0 and not k.startswith('W') and k not in ('Construction', 'Renewal of rail systems', 'Running tunnels and stations', 'Extra regional train running', 'Public funds on the items above')}
    wider = {k: first[k] for k in WIDER_ADDED}
    once = {k: sum(add[k]) for k in ('2. Freed land (net sale value)', '2. Parks (amenity less upkeep)', '5. Signal boxes not renewed', '11. Carbon of the works', '11. Disruption during the works')}
    ben = sum(yearly.values()); wid = sum(wider.values())
    run = m['om_infra'] + m['om_trains']; cost = m['yearly_cost']
    def flat_irr(b):
        def v(rr):
            x = -sum(capex / N.BUILD_YEARS * (1 + rr) ** (k + 0.5) for k in range(N.BUILD_YEARS))
            x += sum((b - run) / (1 + rr) ** t for t in range(1, N.n_ + 1))
            return x - m['systems'] / (1 + rr) ** N.RENEW_YEAR
        lo, hi = -0.05, 0.25
        if v(lo) < 0: return None
        for _ in range(100):
            mid = (lo + hi) / 2
            if v(mid) > 0: lo = mid
            else: hi = mid
        return (lo + hi) / 2
    # the bridge from the first count of the study (finance.py, central case) to this complete count, by family
    A = m['A']['benefits']
    first_time = sum(v for k, v in A.items() if k.startswith('Time saved'))
    borrowed_ratios = m['A']['benefit_total'] - first_time                      # comfort and wider effects taken as ratios of another appraisal
    fam = by_family(yearly)
    bridge = [('First count of the study', m['A']['benefit_total']), ('Ratios borrowed from the Grand Paris appraisal, removed', -borrowed_ratios),
              ('Passengers’ time, re-measured', fam['Passengers’ time'] - first_time)]
    bridge += [(f, v) for f, v in fam.items() if f != 'Passengers’ time']
    bridge.append(('Complete count', ben))
    assert abs(sum(v for _, v in bridge[:-1]) - ben) < 1e-9
    return {'benefits': yearly, 'benefit_total': ben, 'wider': wider, 'wider_total': wid, 'borrowed': borrowed, 'once': once, 'families': fam, 'bridge': bridge,
            'first_time': first_time, 'first_borrowed': borrowed_ratios,
            'yearly_cost': cost, 'annuity': m['annuity'], 'running': run, 'renewal': m['renewal_year'],
            'cover': ben / cost, 'cover_wider': (ben + wid) / cost, 'cover_capital': ben / m['annuity'],
            'irr': flat_irr(ben), 'irr_wider': flat_irr(ben + wid), 'first_count': m['A']['benefit_total'], 'first_count_cover': m['A']['benefit_total'] / cost}


def main():
    m = model_figures()
    res = {'params': {'rate': R_FR, 'rate_public': R_PUBLIC_2021, 'vot_growth': VOT_GROWTH, 'ld_growth': LD_GROWTH, 'sd_growth': SD_GROWTH, 'cofp': 1 + COFP,
                      'eur2015': EUR2015, 'carbon': CARBON_2015, 'base_year': BASE_YEAR, 'build_start': BUILD_START, 'open': OPEN, 'last': LAST, 'resid_end': RESID_END,
                      'paths': {'today': PATHS_TODAY, 'ref': PATHS_REF, 'project': PATHS_PROJ}, 'peak_share': PEAK_SHARE, 'cap_value': CAP_VALUE, 'cap_lost': CAP_LOST,
                      'operator_margin': OPERATOR_MARGIN, 'wear': WEAR, 'fleet': {k: {'sets': n, 'cost': c, 'saving': n * c} for k, (n, c) in FLEET.items()}, 'terminal_upkeep': TERMINAL_UPKEEP,
                      'car_share': CAR_SHARE, 'trip_km': TRIP_KM, 'kg_pkm': KG_PKM, 'occ': OCC, 'road_ext': ROAD_EXT, 'tgv_wider_share': TGV_WIDER_SHARE, 'agglo_elast': AGGLO_ELAST,
                      'items': {k: {'low': v[0], 'central': v[1], 'high': v[2]} for k, v in P.items()},
                      'air_co2_t': AIR_CO2_T, 'fare_dom': FARE_DOM, 'fare_lon': FARE_LON, 'user_gain_air': USER_GAIN_AIR, 'crowd_pen': CROWD_PEN, 'peak': PEAK, 'external': EXTERNAL,
                      'punct_trips': PUNCT_TRIPS, 'x_today': X_TODAY, 'x_proj': X_PROJ, 'land_years': LAND_YEARS, 'resignal_year': RESIGNAL_YEAR, 'disrupt_start': DISRUPT_START,
                      'cities': len(CITIES), 'track_share': N.TRACK_SHARE, 'fare': N.FARE, 'vot': {'long_distance': N.VOT_LD, 'regional_express': N.VOT_TER, 'paris_region': N.VOT_IDF},
                      'crowding': crowding(m)[1], 'departures': (N.HS_TERMINALS - 2 * N.CONN) / 2, 'tgv_agglo_first_year': {str(e): tgv_agglo(e) for e in P['tgv_elast']}},
           'names': {'official': OFFICIAL, 'added': ADDED, 'borrowed': list(BORROWED), 'families': [[f, ks] for f, ks in FAMILIES]}}
    cases = {'baseline': dict(only=[]), 'low': dict(level=0), 'central': dict(level=1), 'high': dict(level=2), 'rate32': dict(r=R_PUBLIC_2021),
             'high_cost': dict(o=dict(cost='high')), 'low_cost': dict(o=dict(cost='low')),
             'no_growth_4': dict(r=0.04, o=dict(ld_growth=0.0, sd_growth=0.0, vot_growth=0.0)),
             'no_capacity': dict(o=dict(capacity=False)), 'capacity_40': dict(o=dict(cap_value=40.0)), 'no_producers': dict(o=dict(producers=False)),
             'vot_ld_085': dict(o=dict(vot_ld_scale=0.85)), 'cofp_125': dict(o=dict(cofp_rate=0.25)), 'fares_14': dict(o=dict(cross_fares=1.4)),
             'running_075': dict(o=dict(om_scale=0.75)), 'ame': dict(o=dict(ame=True))}
    res['cases'] = {name: evaluate(m, **kw) for name, kw in cases.items()}
    base = res['cases']['baseline']['npv']
    items = [k for k in ADDED if k != 'Public funds on the items above']
    res['each_alone'] = {k: evaluate(m, 1, only=[k])['npv' if not k.startswith('W') else 'npv_wider'] - base for k in items}
    res['all_but'] = {k: evaluate(m, 1, drop=[k])['npv' if not k.startswith('W') else 'npv_wider'] for k in items}
    res['study'] = {lv: study_method(m, i) for i, lv in enumerate(LEVELS)}
    res['model'] = {'capex': m['cost'], 'capex_low': m['cost_low'], 'capex_high': m['cost_high'], 'annuity': m['annuity'], 'running': m['om_infra'] + m['om_trains'],
                    'renewal_year': m['renewal_year'], 'yearly_cost': m['yearly_cost'], 'systems': m['systems'], 'ops_rev': m['ops_rev'], 'first_count': m['A']['benefit_total']}
    res['jobs'] = {k: JOBS[k] for k in ('beta', 'pen', 'branch', 'easy', 'commuters_pt_suburb_pairs', 'users_low', 'users_central', 'users_high', 'trips_day', 'today_obs_day',
                                          'improved_pairs', 'hubs', 'induced_jobs_net', 'top_pairs', 'obs_over_fit_improved', 'keep_per_change')}
    os.makedirs(OUT, exist_ok=True); json.dump(res, open(f'{OUT}/french.json', 'w'), indent=1, default=float)
    pr = lambda x: None if x is None else round(x, 3)
    for k, v in res['cases'].items():
        print(f"{k:14s} NPV {v['npv']:7.2f} per euro {v['per_euro']:6.3f} IRR {pr(v['irr'])}  with wider {v['npv_wider']:7.2f} per euro {v['per_euro_wider']:6.3f} IRR {pr(v['irr_wider'])}  ratio {v['ratio']:.2f} / {v['ratio_wider']:.2f}")
    c = res['cases']['central']
    print('PV by item (central):'); [print('  ', k.ljust(62), round(v, 3)) for k, v in c['pv'].items()]
    s = res['study']['central']
    print('STUDY METHOD, complete list: benefits', round(s['benefit_total'], 3), 'wider', round(s['wider_total'], 3), 'yearly cost', round(s['yearly_cost'], 3), 'cover', round(s['cover'], 3), round(s['cover_wider'], 3), 'irr', pr(s['irr']), 'first count', round(s['first_count'], 3))
    [print('  ', k.ljust(62), round(v, 3)) for k, v in s['benefits'].items()]
    print('  once:', {k[:30]: round(v, 3) for k, v in s['once'].items()})


if __name__ == '__main__':
    main()
