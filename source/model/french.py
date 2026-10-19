"""The economic return under the French appraisal rules, with the complete list of benefits.

Two readings of the same project, both built on nordest.py (access, traffic, cost) and finance.py (the two accounts):
- the study's own reading: the benefits of the opening year, at today's traffic, held flat for 60 years at 3%, against the
  yearly cost of finance.py (repayment of construction plus running costs);
- the French method (Instruction of 16 June 2014 and the DGITM fiches-outils of May 2019, see the sources of the economy
  section): one real discount rate of 4.5%, construction from 2028, opening in 2040, explicit years to 2070, residual value
  2071-2140 with flows held flat, values of time growing 0.84% a year (elasticity 0.7 to GDP per head at +1.2%), long-distance
  traffic +1.2% a year and short-distance +0.3% until 2070, the official carbon path, a cost of public funds of 1.2 on net
  public money, producers' balances counted, wider effects reported apart from the headline net present value (NPV).

The list of benefits is complete (see /evaluation and /benefits-deep-study in the project files): the official items first,
then the items of the deep study, each with a low, central and high value. Where an item replaces a rougher term of the
official list (commuters measured on the census for the corridor estimate, the crowding count for the borrowed comfort ratio),
the rougher term is switched off. The borrowed wider-effect ratios of the Grand Paris Express appraisal are computed but not
used: the measured wider effects take their place. Disruption to today's trains during the works is not counted, as French
appraisals do not count it (Grand Paris Express, counter-expertise of 2022).

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
PRODUCER = N.TRACK_SHARE * (1 - WEAR) + OPERATOR_MARGIN      # what the railway keeps of a euro of new fare
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
 'jobs_users': (JOBS['users_low'], JOBS['users_central'], JOBS['users_high']),                       # bn a year, commuters who gain a through suburban line
 'jobs_agglo': tuple(JOBS['agglomeration'][k] for k in ('low', 'central', 'high')),                  # bn a year, denser job markets
 'jobs_labour': tuple(JOBS['labour'][k] for k in ('low', 'central', 'high')),                        # bn a year, people into work
 'jobs_better': tuple(JOBS['better_jobs'][k] for k in ('low', 'central', 'high')),                   # bn a year, moves to better jobs
 'landuse': (0.0, 0.5, 1.0),                                   # homes and jobs move towards the better access: rise of the job-access gains after 20 years (ASSUMPTION; Grand Paris appraisal: effects rise to 2035 then grow)
 'freed_ha': (82.0, 109.0, 136.0),                             # hectares of track freed inside Paris once the lines are underground, net of the RER, line R and freight tracks kept (research note on land)
 'plot_density': (15000.0, 25000.0, 32000.0), 'plot_price': (400.0, 650.0, 1000.0),    # m2 of floor space a hectare of building plot; euros a m2 net to the landowner (Bercy-Charenton, Gare des Mines)
 'park_visits_ha': (60e3, 100e3, 150e3),                       # visits a year a hectare of park: Buttes-Chaumont about 120,000 on 25 ha, La Villette about 40,000 on 55 ha (ASSUMPTION)
 'park_new_share': (0.5, 0.7, 0.85),                           # share of those visits not taken from another park (ASSUMPTION)
 'park_health': (0.5, 1.0, 1.0),                               # avoided health costs, as a multiple of the recreation value (London natural capital account: about equal)
 'park_make': (5.0, 3.6, 2.3), 'park_upkeep': (0.10, 0.05, 0.025),      # M euros a hectare to clear the tracks and make the park; M euros a hectare a year to keep it (research note on land)
 'tgv_elast': (0.02, 0.04, 0.125), 'business_share': (0.18, 0.25, 0.33),   # elasticity of output to market access between cities; business share of TGV trips
 'resignal': (0.05, 0.15, 0.30),                              # bn once in 2036: old terminal signal boxes not renewed
 'noise': (0.003, 0.0055, 0.008),                             # bn a year: rail noise removed along the approaches that close
 'air_lon': (90e3, 170e3, 250e3),                             # London air passengers a year who switch to a through train (CAA 2024, share curve)
 'timetable_min': (1.0, 2.5, 5.0),                            # equivalent minutes a TGV journey for a regular, memorable, repairable timetable (Wardman et al. 2004: 3.6 for an hourly clockface, 4.6 to 8.6 for even intervals at two to four trains an hour; part of today's timetable is already regular; ASSUMPTION)
 'displace_w': (0.3, 0.5, 0.7),                               # weight of a minute between the wanted and the next convenient train, against a minute in the train (ASSUMPTION)
 'margin_min': (0.0, 2.5, 5.0),                               # minutes later a TGV passenger arrives for a train at a known through platform (ASSUMPTION)
 'build_co2': (1.0, 1.4, 2.3),                                # Mt CO2e of the works
}
LEVELS = ('low', 'central', 'high')
PARK_SHARE, PLOT_SHARE = 0.80, 0.15      # of the freed hectares: parks, and the small plots kept for building; the rest is streets and edges (ASSUMPTION, the plan)
PARK_OPEN, PARK_MAKE_YEARS = 2043, (2040, 2042)      # the surface tracks are cleared in the three years after opening, the parks open after (ASSUMPTION)
VISIT_VALUE = 3.3            # euros of welfare a visit to an urban park (ORVal, University of Exeter: about 2.8 pounds; derived)
FARE_DOM, FARE_LON = 80.0, 130.0      # average rail fare of a cross-France or London journey, euros (ASSUMPTION)
USER_GAIN_AIR = 15.0         # euros of gain for each traveller who switches from the plane, rule of a half (ASSUMPTION)
AIR_KG_PKM, LON_KM, AIR_KM_RATIO = 0.3, 850.0, 0.8     # kg CO2e a passenger-km flown with contrails (ADEME); London flight km; air km as a share of road km (ASSUMPTION)
CROWD_PEN = 0.40             # extra equivalent minute per minute ridden in a crowded metro or RER leg: 60% standing at 1.52, 40% seated at 1.08 (DGITM comfort factors; derived)
PEAK = 0.5                   # share of the relieved trips made in the crowded hours (ASSUMPTION)
EXTERNAL = 0.7               # relief to the riders left on board, as a share of a rider's own crowding (derived)
TGV_CROSS_TODAY = 5.2        # million TGV journeys across Paris today (the model's CONN, rounded)
PARIS_GDP = 800.0            # Ile-de-France output, bn (ASSUMPTION, rounded)
# minutes between arriving in Paris and leaving it for another region: today with a change of station, the same figure as the traffic
# model (estimate.T_OLD), which SNCF's timetable confirms (model/paris_crossing.py: in_paris_median_min, the median of the city pairs); on a through
# train, its two stops and the run between them, as in the timetable
CROSSING = json.load(open(os.path.join(HERE, 'inputs', 'paris_crossing.json')))
X_TODAY, X_PROJ = N.T_OLD, N.TH['L'] + N.STOP_MIN
# the cities: side of Paris, output (bn), minutes to Paris by the fastest trains of 2026, road km from Paris (rounded; ASSUMPTION)
CITIES = {'Lille': ('N', 60, 62, 225), 'Strasbourg': ('E', 32, 106, 490), 'Reims': ('E', 12, 46, 145), 'Metz': ('E', 13, 84, 330), 'Nancy': ('E', 13, 90, 350),
          'Lyon': ('S', 95, 117, 465), 'Marseille': ('S', 75, 195, 775), 'Nice': ('S', 40, 330, 930), 'Montpellier': ('S', 30, 200, 750), 'Grenoble': ('S', 25, 180, 575),
          'Dijon': ('S', 13, 95, 315), 'Toulon': ('S', 20, 240, 835), 'Avignon': ('S', 10, 160, 690), 'Bordeaux': ('A', 55, 124, 585), 'Nantes': ('A', 45, 128, 385),
          'Rennes': ('A', 35, 85, 350), 'Toulouse': ('A', 60, 260, 680), 'Tours': ('A', 14, 60, 240), 'Le Mans': ('A', 10, 55, 210), 'Angers': ('A', 12, 95, 300), 'Brest': ('A', 10, 215, 590)}
VIA_PARIS = {frozenset('NS'): 0.5, frozenset('NA'): 0.5, frozenset('ES'): 0.6, frozenset('EA'): 0.8, frozenset('AS'): 0.6, frozenset('NE'): 0.0}
LAND_YEARS = (2043, 2055); RESIGNAL_YEAR = 2036

# ------------------------------------------------------------------ cross-France journeys: today's bypass trains, and the through trains of the project
# Province-to-province TGV passengers who avoid the Paris terminals today: 21.9 million in 2009 (RFF), of which 17.6 million on trains
# that stop in the Paris region (the Lille to Lyon trunk through Roissy and Marne-la-Vallee, and the Massy link for the west) and 4.3
# million between the east and the south through Dijon, which the project does not help. Scaled by the growth of TGV traffic since
# (117.2 to 122 million). By pair of sides: million passengers in 2009; extra minutes of today's bypass route against the sum of the
# two radial legs; direct trains a day on a typical pair of cities today (ASSUMPTION, read from the 2026 timetable).
BYPASS_2009, TGV_2009, TGV_NOW = 21.9, 117.2, 122.0
BYPASS = {frozenset('NS'): dict(pax=14.2, extra=0.0, per_day=7.0), frozenset('AS'): dict(pax=2.0, extra=25.0, per_day=4.0),
          frozenset('NA'): dict(pax=0.9, extra=65.0, per_day=2.0), frozenset('EA'): dict(pax=0.5, extra=75.0, per_day=2.0)}
PROJ_PER_DAY = 16.0          # through trains a day between two large cities once every radial train runs through Paris: hourly (the timetable chapter)
DAY_MIN = 16 * 60            # minutes of service a day
DISPLACE_CAP = 120.0         # the wait for the next convenient train is a quarter of the interval between trains, at most two hours (ASSUMPTION)
GC_ELAST = -1.0              # long-distance rail demand to generalised time (British demand handbook, order of magnitude)
# Air passengers between French cities in 2025 (DGAC), the pairs whose rail route runs through Paris; today's best rail time in minutes
# (a direct bypass train or a change of station in Paris; rounded timetable estimates), and the share of the pair for which the Paris
# route is the natural one (Nice to Strasbourg: half).
AIR_PAIRS = [('Marseille', 'Nantes', 382621, 360), ('Bordeaux', 'Lyon', 377447, 280), ('Lyon', 'Nantes', 319730, 260), ('Lille', 'Nice', 281995, 435),
             ('Nantes', 'Nice', 263856, 510), ('Nice', 'Strasbourg', 194650, 480, 0.5), ('Bordeaux', 'Lille', 126487, 285), ('Strasbourg', 'Toulouse', 120053, 400),
             ('Brest', 'Marseille', 113497, 450), ('Lille', 'Toulouse', 112317, 390), ('Bordeaux', 'Strasbourg', 109214, 315), ('Lille', 'Marseille', 100057, 275),
             ('Marseille', 'Strasbourg', 88980, 340), ('Nice', 'Rennes', 85086, 480), ('Brest', 'Lyon', 74856, 380), ('Nantes', 'Strasbourg', 66648, 300),
             ('Marseille', 'Rennes', 65585, 330), ('Lyon', 'Rennes', 63082, 230), ('Brest', 'Strasbourg', 21629, 380)]
SHARE_CURVE = [(120, .90), (150, .85), (180, .75), (210, .65), (240, .55), (270, .45), (300, .35), (330, .27), (360, .20), (420, .12), (480, .08)]   # rail's share of rail plus air by rail time (Hotrails 2024, Steer)
AIR_DOOR = (150.0, 10.0)     # door to door by air: 150 minutes to reach the airport, check in, board, leave and reach town, plus a minute per 10 km flown (ASSUMPTION)
# the pairs the page shows (the cities Charles named and the largest air pairs), with today's way of travelling
SHOW_PAIRS = [('Lille', 'Bordeaux'), ('Bordeaux', 'Strasbourg'), ('Lille', 'Lyon'), ('Lille', 'Marseille'), ('Rennes', 'Lyon'), ('Rennes', 'Strasbourg'), ('Nantes', 'Strasbourg'),
              ('Rennes', 'Dijon'), ('Bordeaux', 'Lyon'), ('Nantes', 'Lyon'), ('Nantes', 'Marseille'), ('Lille', 'Nantes'), ('Lyon', 'Strasbourg')]
DIRECT_TODAY = {frozenset(('Lille', 'Lyon')): 'direct by the bypass, about 7 a day', frozenset(('Lille', 'Marseille')): 'direct by the bypass, about 3 a day',
                frozenset(('Rennes', 'Lyon')): 'direct by Massy, about 4 a day', frozenset(('Bordeaux', 'Lyon')): 'direct by Massy, about 3 a day',
                frozenset(('Nantes', 'Lyon')): 'direct by Massy, about 6 a day', frozenset(('Nantes', 'Marseille')): 'direct by Massy, about 2 a day',
                frozenset(('Lille', 'Nantes')): 'direct by Massy, about 3 a day', frozenset(('Lille', 'Bordeaux')): 'a change of station in Paris, or one slow direct train',
                frozenset(('Bordeaux', 'Strasbourg')): 'direct by Massy, about 2 a day', frozenset(('Nantes', 'Strasbourg')): 'direct by Massy, about 2 a day',
                frozenset(('Rennes', 'Strasbourg')): 'a change of station in Paris', frozenset(('Rennes', 'Dijon')): 'a change of station in Paris',
                frozenset(('Lyon', 'Strasbourg')): 'direct by the Rhine-Rhone line in 3h45, about 5 a day; the project adds the Paris route'}
TODAY_MIN = {frozenset(('Lille', 'Lyon')): 180, frozenset(('Lille', 'Marseille')): 275, frozenset(('Rennes', 'Lyon')): 230, frozenset(('Bordeaux', 'Lyon')): 280,
             frozenset(('Nantes', 'Lyon')): 260, frozenset(('Nantes', 'Marseille')): 360, frozenset(('Lille', 'Nantes')): 230, frozenset(('Lille', 'Bordeaux')): 285,
             frozenset(('Bordeaux', 'Strasbourg')): 315, frozenset(('Nantes', 'Strasbourg')): 300, frozenset(('Rennes', 'Strasbourg')): 241, frozenset(('Rennes', 'Dijon')): 230,
             frozenset(('Lyon', 'Strasbourg')): 225}      # today's best rail time, minutes (rounded timetable estimates; a change of station counts 50 minutes)

# ------------------------------------------------------------------ names of the items, in the order the page shows them, and what each one is
OFFICIAL = ['Building the tunnels and stations', 'Renewing the rail systems every thirty years', 'Running the tunnels and stations', 'Running the extra regional trains',
            'TGV travellers of the Paris region: a nearer station', 'TGV travellers crossing Paris: no change of station', 'Room for more TGVs in the busy hours',
            'Regional travellers: the Paris side of their trip', 'Suburb-to-suburb trips across Paris, rough estimate (replaced by the measured count)',
            'Regional express travellers crossing Paris: no change', 'Comfort on relieved lines, ratio of another appraisal (replaced by the crowding count)',
            'Fares of the new TGV journeys kept by the railway', 'Trainsets saved: trains no longer wait in a terminal', 'Upkeep of the surface terminals no longer needed',
            'Carbon: car trips replaced by the new TGV journeys', 'Roads: fewer accidents, less noise, pollution and congestion', 'Cost of raising the public money',
            'Wider: suburban job markets (study ratio)', 'Wider: TGV links', 'Wider: agglomeration, French elasticity']
BORROWED = ('Wider: suburban job markets (study ratio)', 'Wider: TGV links', 'Wider: agglomeration, French elasticity')
COSTS = OFFICIAL[:4]
CONSTRUCTION, RENEWAL, RUNNING, EXTRA_TRAINS = COSTS
TGV_REGION, TGV_CROSS, CAPACITY, REG_PARIS, CORRIDOR, TER_CROSS, COMFORT, PRODUCERS, TRAINSETS, TERMINALS, CARBON_CAR, ROADS, COFP_ITEM = OFFICIAL[4:17]
JOB_USERS = 'Commuters who gain a through suburban line across Paris'
PLOTS, PARKS = 'Building plots at the edge of the freed tracks, sold', 'Three new parks on the freed tracks'
CROWD, RESIGNAL, NOISE = 'Less crowding on the metro and RER legs no longer ridden', 'Signal boxes of the surface approaches not renewed', 'Less rail noise along the approaches that close'
BYPASS_ITEM, AIR_USERS, FRANCE_FARES = 'Travellers of the western bypass trains: more trains, shorter routes', 'Travellers who leave the plane for a through train', 'Fares of the new cross-France journeys kept by the railway'
AIR_CO2, CAR_FRANCE = 'Carbon: flights replaced by through trains', 'Carbon and roads: car trips replaced on cross-France journeys'
TIMETABLE, MARGIN, BUILD_CO2 = 'A regular timetable: easy to read, easy to repair', 'TGV travellers arrive later: a known through platform', 'Carbon emitted by the works'
COFP_ADDED = 'Cost of raising the public money for these items'
WIDER_ADDED = ['Wider: denser job markets, more productive firms', 'Wider: people brought into work', 'Wider: workers moving to better jobs', 'Wider: cities joined, wider markets', 'Wider: business time, imperfect competition rule']
W_AGGLO, W_LABOUR, W_BETTER, W_MARKET, W_BUSINESS = WIDER_ADDED
ADDED = [JOB_USERS, PLOTS, PARKS, CROWD, RESIGNAL, NOISE, BYPASS_ITEM, AIR_USERS, FRANCE_FARES, AIR_CO2, CAR_FRANCE, TIMETABLE, MARGIN, BUILD_CO2, COFP_ADDED] + WIDER_ADDED
ONCE = [PLOTS, RESIGNAL, BUILD_CO2]      # items with no yearly value
FRANCE_ITEMS = [BYPASS_ITEM, AIR_USERS, FRANCE_FARES, AIR_CO2, CAR_FRANCE]
EXPLAIN = {
 CONSTRUCTION: 'The construction cost, spent evenly over the twelve years of works.',
 RENEWAL: 'Track, power and signalling of the tunnels replaced in 2070, 2100 and 2130.',
 RUNNING: 'Upkeep, power, staff and safety of the tunnels and the four stations, every year.',
 EXTRA_TRAINS: 'Regional express trains run through Paris instead of ending at a terminal, which costs more train-km.',
 TGV_REGION: 'Passengers who start or end in the Paris region board at the station nearest to them, since every direction is served from three stations.',
 TGV_CROSS: 'The passengers who today change station in Paris, by metro, RER or taxi, stay on their train; the time and the change saved, and the journeys this makes possible.',
 CAPACITY: 'As traffic grows, today’s terminals would turn journeys away in the busy hours; the through stations carry them. Nothing in the opening year.',
 REG_PARIS: 'Suburban and regional express passengers reach the Paris station on the far side of the centre without the metro.',
 CORRIDOR: 'The rough corridor estimate of the official list, replaced by the commuters measured on the census.',
 TER_CROSS: 'Regional express passengers from the north and the east run on to the south and the west instead of changing terminal.',
 COMFORT: 'The comfort ratio borrowed from the Grand Paris appraisal, replaced by the crowding count.',
 PRODUCERS: 'On each new journey the operator keeps a margin and the track owner its charges net of wear; the French method counts both as a gain.',
 TRAINSETS: 'Trains that run through instead of waiting in a terminal need fewer trainsets for the same service.',
 TERMINALS: 'The surface throats and track fields that close no longer need maintenance.',
 CARBON_CAR: 'A quarter of the new TGV journeys replace a car trip, at the official value of a tonne of carbon.',
 ROADS: 'Fewer car-km mean fewer accidents, less noise, pollution and congestion, at the official values.',
 COFP_ITEM: 'Each euro of net public money counts 1.2, because raising taxes has a cost of its own.',
 JOB_USERS: 'Commuters between the suburbs on both sides of Paris who gain a through suburban line, measured on the census and the timetable.',
 PLOTS: 'The small plots kept for building at the edge of the freed tracks, sold at the price SNCF got at Bercy-Charenton and Gare des Mines.',
 PARKS: 'Three large parks on the freed tracks: the visits they draw and the health they bring, less what they cost to make and keep.',
 CROWD: 'Passengers who reach the far side of Paris on their train no longer ride a crowded metro or RER leg; the riders left on board gain room too.',
 RESIGNAL: 'The signal boxes of the surface approaches are due for renewal; with the lines underground they are not renewed.',
 NOISE: 'Rail noise disappears along the surface approaches that close, for the homes beside them.',
 BYPASS_ITEM: 'Passengers between the west and the other regions ride a few slow bypass trains a day today; the project gives them an hourly through train by Paris, shorter by up to an hour.',
 AIR_USERS: 'Air passengers between French cities and from London who take the through train once it matches the plane door to door.',
 FRANCE_FARES: 'The margin and the track charges the railway keeps on the cross-France journeys the project adds.',
 AIR_CO2: 'The flights those passengers no longer take, at the official value of carbon, with contrails.',
 CAR_FRANCE: 'A quarter of the new cross-France journeys replace a car trip of several hundred kilometres.',
 TIMETABLE: 'Every direction leaves at the same minutes all day from a known platform: easy to remember, even intervals, and a known place for each train after an incident.',
 MARGIN: 'A train that stops at a known through platform lets passengers arrive a few minutes later at the station than for a train assigned at the last moment.',
 BUILD_CO2: 'The carbon of digging the tunnels and the stations, at the official value.',
 COFP_ADDED: 'The 1.2 on the public money of the items above: plots sold and signal boxes saved reduce it, the parks add to it.',
 W_AGGLO: 'Denser job markets make firms more productive: a published elasticity applied to the access measured.',
 W_LABOUR: 'Better access brings a few hundred people into work.',
 W_BETTER: 'Better access lets workers take jobs that suit them better.',
 W_MARKET: 'Cities joined without a change widen each other’s markets.',
 W_BUSINESS: 'Business time saved counts 1.1 in the French sensitivity rule for imperfect competition.',
}
CONFIDENCE = {TGV_REGION: 'Medium', TGV_CROSS: 'Medium', REG_PARIS: 'Medium', TER_CROSS: 'Medium', CAPACITY: 'Low', PRODUCERS: 'Official rule, debated', TRAINSETS: 'Medium', TERMINALS: 'Medium',
              CARBON_CAR: 'High', ROADS: 'High', JOB_USERS: 'Medium, measured', PLOTS: 'Low', PARKS: 'Low', CROWD: 'Medium', RESIGNAL: 'Medium', NOISE: 'Medium', BYPASS_ITEM: 'Medium',
              AIR_USERS: 'Medium', FRANCE_FARES: 'Medium', AIR_CO2: 'Medium', CAR_FRANCE: 'Medium', TIMETABLE: 'Low', MARGIN: 'Low', BUILD_CO2: 'Medium',
              W_AGGLO: 'Low', W_LABOUR: 'Low', W_BETTER: 'Low', W_MARKET: 'Low', W_BUSINESS: 'Low'}

# Families used by the site to show the benefits at a glance (every item above belongs to exactly one)
FAMILIES = [
    ('Passengers’ time', [TGV_REGION, TGV_CROSS, REG_PARIS, CORRIDOR, TER_CROSS, BYPASS_ITEM, AIR_USERS]),
    ('Room for more trains in the busy hours', [CAPACITY]),
    ('The railway’s own gains', [PRODUCERS, FRANCE_FARES, TRAINSETS, TERMINALS]),
    ('Comfort and ease', [COMFORT, CROWD, TIMETABLE, MARGIN]),
    ('Job access across Paris', [JOB_USERS]),
    ('Environment', [CARBON_CAR, ROADS, NOISE, AIR_CO2, CAR_FRANCE]),
    ('Parks, land and one-off savings', [PARKS, PLOTS, RESIGNAL]),
    ('Carbon of the works', [BUILD_CO2]),
    ('Construction and running costs', COSTS),
    ('Cost of public funds', [COFP_ITEM, COFP_ADDED]),
    ('Wider effects, measured', WIDER_ADDED),
]
FAMILY_OF = {k: f for f, ks in FAMILIES for k in ks}
assert set(FAMILY_OF) == set(OFFICIAL + ADDED) - set(BORROWED), set(OFFICIAL + ADDED) - set(BORROWED) ^ set(FAMILY_OF)
assert set(EXPLAIN) == set(FAMILY_OF), set(FAMILY_OF) ^ set(EXPLAIN)


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
            'yearly_cost': A['yearly_cost'], 'ops_cost_items': A['ops_cost']}


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


def car_decarb(t, ame=False):
    """Reference scenario: road transport carbon-free by 2050; ame: cars keep today's emissions."""
    return 1.0 if ame else max(0.0, (2050 - t) / (2050 - BASE_YEAR))


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
            z[CONSTRUCTION] = -capex / (OPEN - BUILD_START)
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
            z[TGV_REGION] = m['tgv_access'] * f_tgv * ld_vot
            z[TGV_CROSS] = m['tgv_cross'] * f_tgv * ld_vot
            if o.get('capacity', True):
                z[CAPACITY] = enabled * (cap_value * ld_vot + CAP_LOST * N.FARE * PRODUCER) / 1000
            z[REG_PARIS] = m['reg_paris'] * f_sd * vot
            z[CORRIDOR] = cor_ben * f_sd * vot
            z[TER_CROSS] = m['ter_cross'] * f_sd * vot
            z[COMFORT] = comfort * f_sd * vot
            if o.get('producers', True):
                z[PRODUCERS] = tgv_rev * f_tgv * PRODUCER
                z[TRAINSETS] = sum(n * c for n, c in FLEET.values())
                z[TERMINALS] = TERMINAL_UPKEEP
            car_km = m['tgv_new'] * f_tgv * 1e6 * CAR_SHARE * TRIP_KM / OCC
            z[CARBON_CAR] = car_km * OCC * KG_PKM / 1000 * car_decarb(t, o.get('ame')) * carbon(t) if o.get('externalities', True) else 0.0
            z[ROADS] = (car_km * ROAD_EXT * EUR2015 / 1e9 + (m['reg_paris'] + cor_ben) * DECONGEST * f_sd * vot) if o.get('externalities', True) else 0.0
            z[RUNNING] = -m['om_infra'] * o.get('om_scale', 1.0)
            z[EXTRA_TRAINS] = -m['om_trains']
            z['Wider: suburban job markets (study ratio)'] = (reg_user + comfort) * N.R_WIDER * f_sd * vot
            z['Wider: TGV links'] = (m['tgv_access'] + m['tgv_cross']) * TGV_WIDER_SHARE * f_tgv * ld_vot
            z['Wider: agglomeration, French elasticity'] = agg * f_sd
        if t in (2070, 2100, 2130):
            z[RENEWAL] = -m['systems']
        if o.get('cofp', True):
            # net public money: construction, renewal and running, less the project's income, the track charges the public track owner
            # earns on new journeys, and VAT in new tickets less fuel duty lost
            pub = -(z[CONSTRUCTION] + z[RENEWAL] + z[RUNNING] + z[EXTRA_TRAINS])
            if t >= OPEN:
                te = min(t, LAST); f = (1 + g_ld) ** (te - BASE_YEAR)
                pub -= (m['ops_rev'] - m['ops_rev_items'].get('Track charges on new TGV journeys', 0.0)) * min(f, 1 + (PATHS_PROJ / PATHS_TODAY - 1))
                pub -= tgv_rev * N.TRACK_SHARE * (1 - WEAR) * min(f, 1.5)
                pub -= m['tax']['VAT inside the new ticket money'] + m['tax']['Fuel duty lost on car trips moved to rail']
            z[COFP_ITEM] = -o.get('cofp_rate', COFP) * pub
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
    for a, (ta, ga, xa, _) in CITIES.items():
        ma = ga + PARIS_GDP * math.exp(-d * xa); dma = 0.0
        for b, (tb, gb, xb, _) in CITIES.items():
            if a == b: continue
            t0 = xa + xb + (X_TODAY if ta != tb else 15.0); t1 = xa + xb + (X_PROJ if ta != tb else 15.0)
            ma += gb * math.exp(-d * t0)
            s = VIA_PARIS.get(frozenset(ta + tb), 0.0) if ta != tb else 0.0
            dma += s * gb * (math.exp(-d * t1) - math.exp(-d * t0))
        gain += elast * dma / ma * ga
    return gain


def rail_share(t):
    """Rail's share of rail plus air on a city pair, by rail time in minutes."""
    if t <= SHARE_CURVE[0][0]: return SHARE_CURVE[0][1]
    for (a, sa), (b, sb) in zip(SHARE_CURVE, SHARE_CURVE[1:]):
        if a <= t <= b: return sa + (sb - sa) * (t - a) / (b - a)
    return SHARE_CURVE[-1][1]


def hm(minutes):
    return f'{int(minutes // 60)}h{int(round(minutes % 60)):02d}'


def france(L=1):
    """Cross-France journeys at today's traffic, level L: the bypass travellers of today, the air passengers who switch, the journeys added,
    and what follows (fares kept by the railway, carbon, car-km). Million passengers and bn euros a year."""
    scale = TGV_NOW / TGV_2009
    legs = {}       # output-weighted mean of the two radial legs and of the road km, by pair of sides
    for sp in BYPASS:
        a, b = sorted(sp)
        ca = [(g, x, km) for s, g, x, km in CITIES.values() if s == a]; cb = [(g, x, km) for s, g, x, km in CITIES.values() if s == b]
        w = sum(g for g, _, _ in ca) * sum(g for g, _, _ in cb)
        legs[sp] = (sum(g * x for g, x, _ in ca) / sum(g for g, _, _ in ca) + sum(g * x for g, x, _ in cb) / sum(g for g, _, _ in cb),
                    sum(g * km for g, _, km in ca) / sum(g for g, _, _ in ca) + sum(g * km for g, _, km in cb) / sum(g for g, _, _ in cb))
    by = {}
    disp1 = min(DAY_MIN / PROJ_PER_DAY / 4, DISPLACE_CAP)
    for sp, c in BYPASS.items():
        pax = c['pax'] * scale
        disp0 = min(DAY_MIN / c['per_day'] / 4, DISPLACE_CAP)
        w = P['displace_w'][L]
        gain = max(0.0, (c['extra'] - X_PROJ) + w * (disp0 - disp1))        # equivalent minutes; nothing if the bypass train stays the better choice
        gc0 = legs[sp][0] + c['extra'] + w * disp0
        new = pax * ((gc0 - gain) / gc0) ** GC_ELAST - pax if gain > 0 else 0.0
        by[''.join(sorted(sp))] = {'pax': pax, 'extra': c['extra'], 'per_day': c['per_day'], 'wait_today': disp0, 'wait_project': disp1, 'gain_min': gain, 'new': new,
                                   'legs_min': legs[sp][0], 'road_km': legs[sp][1],
                                   'users': (pax * gain + new * gain / 2) / 60 * N.VOT_LD / 1000, 'car_km': new * 1e6 * CAR_SHARE * legs[sp][1] / OCC}
    air = []; air_pax = 0.0; air_pkm = 0.0; pen = 30.0 if L == 2 else 0.0
    for p in AIR_PAIRS:
        a, b, pax, t0 = p[:4]; share = p[4] if len(p) > 4 else 1.0
        t1 = CITIES[a][2] + CITIES[b][2] + X_PROJ
        s0, s1 = rail_share(t0 + pen), rail_share(t1)
        f = max(0.0, (s1 - s0) / (1 - s0)) * (0.5 if L == 0 else 1.0)
        km = (CITIES[a][3] + CITIES[b][3]) * AIR_KM_RATIO
        sw = pax * share * f
        air.append({'pair': [a, b], 'air_pax': pax, 'today_min': t0, 'project_min': t1, 'share_today': s0, 'share_project': s1, 'switch': sw, 'air_km': km})
        air_pax += sw; air_pkm += sw * km
    lon = P['air_lon'][L]
    new_bypass = sum(v['new'] for v in by.values())
    out = {'by_side': by, 'air': air, 'air_pax': air_pax, 'air_pkm': air_pkm, 'air_lon': lon, 'bypass_pax': sum(v['pax'] for v in by.values()), 'new_bypass': new_bypass,
           'users_bypass': sum(v['users'] for v in by.values()),
           'users_air': (air_pax + lon) * USER_GAIN_AIR / 1e9,
           'fares': (new_bypass * 1e6 * FARE_DOM + air_pax * FARE_DOM + lon * FARE_LON) * PRODUCER / 1e9,
           'track_public': (new_bypass * 1e6 * FARE_DOM + air_pax * FARE_DOM + lon * FARE_LON) * N.TRACK_SHARE * (1 - WEAR) / 1e9,
           'air_t': (air_pkm + lon * LON_KM) * AIR_KG_PKM / 1000,                        # tonnes of CO2e a year avoided
           'car_km': sum(v['car_km'] for v in by.values()) + air_pax * 0.0}
    out['car_t'] = out['car_km'] * OCC * KG_PKM / 1000
    return out


def show_pairs():
    """The city pairs the page shows, read from SNCF's timetable (model/paris_crossing.py): today with a change of station in Paris
    (the median of the journeys a passenger would choose) against the through train; direct trains a day today (round Paris) and with
    the project, with today's number of high-speed trains; and the plane door to door."""
    rows = []
    for a, b in SHOW_PAIRS:
        k = frozenset((a, b)); m = CROSSING['pairs'][f'{a}-{b}']
        t0, t1 = m['via_paris_min'], m['legs_min'] + X_PROJ
        air_km = (CITIES[a][3] + CITIES[b][3]) * AIR_KM_RATIO; door = AIR_DOOR[0] + air_km / AIR_DOOR[1]
        ap = [p for p in AIR_PAIRS if frozenset(p[:2]) == k]
        rows.append({'pair': [a, b], 'today_min': t0, 'project_min': t1, 'in_paris_min': m['in_paris_min'], 'per_day': m['via_paris_day'],
                     'direct_day': m['direct_day'], 'direct_min': m['direct_min'], 'project_direct_day': m['project_direct_day'], 'more_direct_day': m['more_direct_day'],
                     'today': 'no direct train' if m['direct_day'] < 0.5 else f"{int(m['direct_day'] + 0.5)} direct train{'s' if m['direct_day'] >= 1.5 else ''} a day",
                     'air_door_min': door, 'air_pax': ap[0][2] if ap else None, 'share_today': rail_share(t0), 'share_project': rail_share(t1)})
    return rows


TURN_MIN = (15.0, 45.0)      # minutes a trainset waits at the end of its run before it goes back: the Swiss practice, and the French one (ASSUMPTION)
SERVICE_H = 17.0             # hours a trainset is in service in a day (ASSUMPTION)


def more_trains():
    """An hourly direct train between every two of the six directions (model/paris_crossing.py): the runs a day beyond today's trains
    run through, and the trainsets they need, low with the Swiss turn-round and high with the French one; the yearly cost of a
    trainset as in FLEET."""
    ex = CROSSING['more_trains']; runs = sum(v['extra_day'] for v in ex.values())
    sets = [sum(2 * v['extra_day'] * (v['legs_min'] + X_PROJ + t) for v in ex.values()) / 60 / SERVICE_H for t in TURN_MIN]
    return {'runs_day': runs, 'pairs': len(ex), 'per_day': HOURLY_DAY, 'sets_low': sets[0], 'sets_high': sets[1],
            'cost_low': sets[0] * FLEET['TGV'][1], 'cost_high': sets[1] * FLEET['TGV'][1], 'turn_min': list(TURN_MIN), 'service_h': SERVICE_H,
            'today_through_day': sum(v['same_day'] for v in ex.values())}
HOURLY_DAY = 16


def parks(L):
    """The three parks on the freed tracks: hectares, value of the visits and of health a year, cost to make and keep (bn)."""
    ha = P['freed_ha'][L] * PARK_SHARE
    visits = ha * P['park_visits_ha'][L]
    value = visits * P['park_new_share'][L] * VISIT_VALUE * (1 + P['park_health'][L]) / 1e9
    return {'ha': ha, 'visits': visits, 'value': value, 'make': ha * P['park_make'][L] / 1e3, 'upkeep': ha * P['park_upkeep'][L] / 1e3,
            'plots_ha': P['freed_ha'][L] * PLOT_SHARE, 'plots': P['freed_ha'][L] * PLOT_SHARE * P['plot_density'][L] * P['plot_price'][L] / 1e9}


_CACHE = {}
def added_streams(m, L, o):
    """Yearly flows of the items valued in the deep study, for level L (0 low, 1 central, 2 high)."""
    if 'crowd' not in _CACHE: _CACHE['crowd'] = crowding(m)
    if ('fr', L) not in _CACHE: _CACHE[('fr', L)] = france(L)
    crowd = _CACHE['crowd'][0]; fr = _CACHE[('fr', L)]; pk = parks(L)
    g_ld, g_sd, g_v = growth_opts(o)
    tgv_time = m['tgv_access'] + m['tgv_cross']
    dep = (N.HS_TERMINALS - 2 * N.CONN) / 2                              # M departing TGV journeys a year
    lu = o.get('landuse', P['landuse'][L]); lu_years = 20.0
    f = {k: [] for k in ADDED}
    for t in YEARS:
        z = {k: 0.0 for k in f}
        te = min(t, LAST)
        vot = (1 + g_v) ** (te - BASE_YEAR); fsd = (1 + g_sd) ** (te - BASE_YEAR)
        fld = min((1 + g_ld) ** (te - BASE_YEAR), 1.5); gdp = (1.015 if g_ld else 1.0) ** (te - BASE_YEAR)
        if t >= OPEN:
            flu = 1 + lu * min(1.0, (t - OPEN) / lu_years)                   # homes and jobs move towards the better access over twenty years
            z[JOB_USERS] = P['jobs_users'][L] * fsd * vot * flu
            z[CROWD] = (crowd * [0.6, 1.0, 1.4][L]) * fsd * vot
            z[NOISE] = P['noise'][L] * vot
            z[BYPASS_ITEM] = fr['users_bypass'] * fld * vot
            z[AIR_USERS] = fr['users_air'] * fld
            z[FRANCE_FARES] = fr['fares'] * fld
            z[AIR_CO2] = fr['air_t'] * carbon(t) * air_decarb(t) * fld
            z[CAR_FRANCE] = (fr['car_t'] * car_decarb(t, o.get('ame')) * carbon(t) + fr['car_km'] * ROAD_EXT * EUR2015 / 1e9) * fld
            z[TIMETABLE] = N.HS_TERMINALS * P['timetable_min'][L] / 60 * N.VOT_LD / 1000 * fld * vot
            z[MARGIN] = dep * P['margin_min'][L] / 60 * 1.5 * N.VOT_LD / 1000 * fld * vot
            z[W_AGGLO] = P['jobs_agglo'][L] * fsd * gdp * flu
            z[W_LABOUR] = P['jobs_labour'][L] * fsd * vot * flu
            z[W_BETTER] = P['jobs_better'][L] * fsd * vot * flu
            z[W_MARKET] = tgv_agglo(P['tgv_elast'][L]) * gdp
            z[W_BUSINESS] = 0.1 * P['business_share'][L] * tgv_time * fld * vot
        if LAND_YEARS[0] <= t <= LAND_YEARS[1]:
            z[PLOTS] = pk['plots'] / (LAND_YEARS[1] - LAND_YEARS[0] + 1)
        park_cost = 0.0
        if PARK_MAKE_YEARS[0] <= t <= PARK_MAKE_YEARS[1]: park_cost += pk['make'] / (PARK_MAKE_YEARS[1] - PARK_MAKE_YEARS[0] + 1)
        if t >= PARK_OPEN: park_cost += pk['upkeep']
        z[PARKS] = (pk['value'] * vot if t >= PARK_OPEN else 0.0) - park_cost
        if t == RESIGNAL_YEAR: z[RESIGNAL] = P['resignal'][L]
        if BUILD_START <= t < OPEN:
            z[BUILD_CO2] = -P['build_co2'][L] * 1e6 * carbon(t) / (OPEN - BUILD_START)
        if o.get('cofp', True):
            pub = z[PLOTS] + z[RESIGNAL] - park_cost + fr['track_public'] * fld * (t >= OPEN)
            z[COFP_ADDED] = o.get('cofp_rate', COFP) * pub
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


def evaluate(m, level=1, r=R_FR, only=None, drop=None, o=None, timeline=False):
    """The French reading. level: 0, 1, 2 for the added items; only: added items to include (None = all, [] = none);
    drop: added items to leave out; o: options of the official streams (cost, growth, capacity, producers...).
    timeline: also return the flows year by year, by family, and the running discounted total."""
    o = dict({'cost': 'central'}, **(o or {}))
    add = added_streams(m, level, o)
    keep = [k for k in ADDED if (only is None or k in only) and not (drop and k in drop)]
    replace_corridor = JOB_USERS in keep
    fl, capex = official_streams(m, dict(o, corridor_scale=0.0) if replace_corridor else o)
    if CROWD in keep: fl = dict(fl); fl[COMFORT] = [0.0] * len(YEARS)
    head = [k for k in fl if k not in BORROWED]
    pv = {k: npv(fl, r, [k]) for k in fl}
    pva = {k: npv(add, r, [k]) for k in keep}
    hk = [k for k in keep if k not in WIDER_ADDED]; wk = [k for k in keep if k in WIDER_ADDED]
    npv_head = sum(pv[k] for k in head) + sum(pva[k] for k in hk)
    npv_wider = npv_head + sum(pva[k] for k in wk)
    pv_capex = -pv[CONSTRUCTION]
    allfl = {**{k: fl[k] for k in head}, **{k: add[k] for k in hk}}
    allw = {**allfl, **{k: add[k] for k in wk}}
    pvs = {**{k: pv[k] for k in head}, **pva}
    pos = {k: v for k, v in pvs.items() if k not in WIDER_ADDED}
    pv_benefits = sum(v for v in pos.values() if v > 0); pv_costs = -sum(v for v in pos.values() if v < 0)
    wider_pv = sum(pva[k] for k in wk)
    out = {'npv': npv_head, 'per_euro': npv_head / pv_capex, 'irr': irr(allfl, list(allfl)), 'npv_wider': npv_wider,
           'per_euro_wider': npv_wider / pv_capex, 'irr_wider': irr(allw, list(allw)),
           'pv_benefits': pv_benefits, 'pv_costs': pv_costs, 'ratio': pv_benefits / pv_costs, 'ratio_wider': (pv_benefits + wider_pv) / pv_costs,
           'pv_wider': wider_pv, 'pv_borrowed': {k: pv[k] for k in BORROWED},
           'pv': pvs, 'pv_families': by_family(pvs), 'pv_capex': pv_capex, 'capex': capex, 'level': LEVELS[level], 'rate': r,
           'first_year': {**{k: fl[k][OPEN - BUILD_START] for k in head}, **{k: add[k][OPEN - BUILD_START] for k in keep}}}
    if timeline:
        fam = {}
        for f_, ks in FAMILIES:
            ks = [k for k in ks if k in allw]
            if ks: fam[f_] = [sum(allw[k][i] for k in ks) for i in range(len(YEARS))]
        disc = [1 / (1 + r) ** (t - BASE_YEAR) for t in YEARS]
        net = [sum(allfl[k][i] for k in allfl) for i in range(len(YEARS))]
        netw = [sum(allw[k][i] for k in allw) for i in range(len(YEARS))]
        cum = []; c = 0.0
        for i in range(len(YEARS)): c += net[i] * disc[i]; cum.append(c)
        cumw = []; c = 0.0
        for i in range(len(YEARS)): c += netw[i] * disc[i]; cumw.append(c)
        cross = next((t for t, v in zip(YEARS, cum) if v >= 0 and t > OPEN), None)
        cross_w = next((t for t, v in zip(YEARS, cumw) if v >= 0 and t > OPEN), None)
        costf = ('Construction and running costs', 'Cost of public funds', 'Carbon of the works')
        bens = [sum(v[i] for f_, v in fam.items() if f_ not in costf and f_ != 'Wider effects, measured') for i in range(len(YEARS))]
        costs = [-sum(fam[f_][i] for f_ in costf if f_ in fam) for i in range(len(YEARS))]
        out['timeline'] = {'years': YEARS, 'families': fam, 'net': net, 'benefits': bens, 'costs': costs, 'cum_npv': cum, 'cum_npv_wider': cumw, 'break_even': cross, 'break_even_wider': cross_w,
                           'jobs': {'users': add[JOB_USERS], 'wider': [add[W_AGGLO][i] + add[W_LABOUR][i] + add[W_BETTER][i] for i in range(len(YEARS))]}}
    return out


def study_method(m, level=1):
    """The study's own reading with the complete list: opening-year flows at today's traffic and today's values (no growth, no cost of
    public funds; cars not decarbonised, as the study's carbon figure), held flat for 60 years at 3% against the yearly cost of finance.py.
    One-off items (plots, signal boxes, the carbon of the works, making the parks) have no yearly value and are listed apart."""
    o = {'cost': 'central', 'ld_growth': 0.0, 'sd_growth': 0.0, 'vot_growth': 0.0, 'cofp': False, 'ame': True, 'landuse': 0.0}
    add = added_streams(m, level, o)
    fl, capex = official_streams(m, dict(o, corridor_scale=0.0))
    fl[COMFORT] = [0.0] * len(YEARS)
    i = OPEN - BUILD_START; ip = PARK_OPEN - BUILD_START
    first = {k: fl[k][i] for k in fl if k not in BORROWED}
    first.update({k: add[k][i] for k in ADDED})
    pk = parks(level)
    first[PARKS] = pk['value'] - pk['upkeep']                                  # the parks' yearly value once open, without the years of making them
    borrowed = {k: fl[k][i] for k in BORROWED}
    yearly = {k: v for k, v in first.items() if v != 0 and k not in WIDER_ADDED and k not in COSTS and k != COFP_ADDED}
    wider = {k: first[k] for k in WIDER_ADDED}
    once = {k: sum(add[k]) for k in ONCE}; once['Making the parks'] = -pk['make']
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
    res = {'benefits': yearly, 'benefit_total': ben, 'wider': wider, 'wider_total': wid, 'borrowed': borrowed, 'once': once, 'families': by_family(yearly),
            'yearly_cost': cost, 'annuity': m['annuity'], 'running': run, 'renewal': m['renewal_year'],
            'cover': ben / cost, 'cover_wider': (ben + wid) / cost, 'cover_capital': ben / m['annuity'],
            'irr': flat_irr(ben), 'irr_wider': flat_irr(ben + wid)}
    res['tests'] = study_tests(res)
    return res


_MODEL_JSON = None
def model_json():
    global _MODEL_JSON
    if _MODEL_JSON is None:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'model.json')) as fh: _MODEL_JSON = json.load(fh)
    return _MODEL_JSON


def study_tests(s):
    """The station model's one-at-a-time tests carried onto the complete count: each test's change of benefit and of yearly cost is applied to the
    simple reading's totals, the added items unchanged, except that two minutes more to board also cut the later arrival at through platforms.
    The official discount rates of the fiche (benefits held flat) and passengers' time alone are added as tests of their own."""
    mj = model_json(); Y = mj['yearly']; tot = s['benefit_total']; cost = s['yearly_cost']
    margin = s['benefits'].get(MARGIN, 0.0)
    def one(ben, c, cut=0.0):
        b = tot + ben - Y['benefit_total'] - cut; k = cost * c / Y['cost']
        return {'benefits': b, 'cost': k, 'cover': b / k}
    out = {k: one(v['benefit_total'], v['cost'], margin * min(1.0, 2.0 / P['margin_min'][1]) if 'longer to board' in k else 0.0) for k, v in mj['sens'].items()}
    for r, v in mj['rate_tests'].items(): out['rate_' + r] = one(Y['benefit_total'], Y['benefit_total'] / v['all'])
    time = next(v for k, v in s['families'].items() if k.startswith('Passengers'))
    out['time_only'] = {'benefits': time, 'cost': cost, 'cover': time / cost}
    return out


def budget(m):
    """The money year by year: what is spent, what the project earns, and the repayment of the simple reading (bn, no discounting)."""
    out = {'years': YEARS, 'construction': [], 'running': [], 'renewal': [], 'income': [], 'repayment': []}
    for t in YEARS:
        te = min(t, LAST); f = (1 + LD_GROWTH) ** (te - BASE_YEAR)
        out['construction'].append(m['cost'] / (OPEN - BUILD_START) if t < OPEN else 0.0)
        out['running'].append(m['om_infra'] + m['om_trains'] if t >= OPEN else 0.0)
        out['renewal'].append(m['systems'] if t in (2070, 2100, 2130) else 0.0)
        out['income'].append(m['ops_rev'] * min(f, 1 + (PATHS_PROJ / PATHS_TODAY - 1)) if t >= OPEN else 0.0)
        out['repayment'].append(m['annuity'] if OPEN <= t < OPEN + N.n_ else 0.0)
    return out


def main():
    m = model_figures()
    pk = {lv: parks(i) for i, lv in enumerate(LEVELS)}; fr = {lv: france(i) for i, lv in enumerate(LEVELS)}
    res = {'params': {'rate': R_FR, 'rate_public': R_PUBLIC_2021, 'vot_growth': VOT_GROWTH, 'ld_growth': LD_GROWTH, 'sd_growth': SD_GROWTH, 'cofp': 1 + COFP,
                      'eur2015': EUR2015, 'carbon': CARBON_2015, 'base_year': BASE_YEAR, 'build_start': BUILD_START, 'open': OPEN, 'last': LAST, 'resid_end': RESID_END,
                      'paths': {'today': PATHS_TODAY, 'ref': PATHS_REF, 'project': PATHS_PROJ}, 'peak_share': PEAK_SHARE, 'cap_value': CAP_VALUE, 'cap_lost': CAP_LOST,
                      'operator_margin': OPERATOR_MARGIN, 'wear': WEAR, 'fleet': {k: {'sets': n, 'cost': c, 'saving': n * c} for k, (n, c) in FLEET.items()}, 'terminal_upkeep': TERMINAL_UPKEEP,
                      'car_share': CAR_SHARE, 'trip_km': TRIP_KM, 'kg_pkm': KG_PKM, 'occ': OCC, 'road_ext': ROAD_EXT, 'tgv_wider_share': TGV_WIDER_SHARE, 'agglo_elast': AGGLO_ELAST,
                      'items': {k: {'low': v[0], 'central': v[1], 'high': v[2]} for k, v in P.items()},
                      'park_share': PARK_SHARE, 'plot_share': PLOT_SHARE, 'park_open': PARK_OPEN, 'visit_value': VISIT_VALUE,
                      'fare_dom': FARE_DOM, 'fare_lon': FARE_LON, 'user_gain_air': USER_GAIN_AIR, 'air_kg_pkm': AIR_KG_PKM, 'crowd_pen': CROWD_PEN, 'peak': PEAK, 'external': EXTERNAL,
                      'x_today': X_TODAY, 'x_proj': X_PROJ, 'land_years': LAND_YEARS, 'resignal_year': RESIGNAL_YEAR, 'landuse_years': 20,
                      'bypass_2009': BYPASS_2009, 'tgv_2009': TGV_2009, 'tgv_now': TGV_NOW, 'proj_per_day': PROJ_PER_DAY, 'displace_cap': DISPLACE_CAP, 'gc_elast': GC_ELAST,
                      'air_door': AIR_DOOR, 'share_curve': SHARE_CURVE, 'cities': len(CITIES), 'track_share': N.TRACK_SHARE, 'fare': N.FARE, 'hs_terminals': N.HS_TERMINALS,
                      'vot': {'long_distance': N.VOT_LD, 'regional_express': N.VOT_TER, 'paris_region': N.VOT_IDF},
                      'crowding': crowding(m)[1], 'departures': (N.HS_TERMINALS - 2 * N.CONN) / 2, 'tgv_agglo_first_year': {str(e): tgv_agglo(e) for e in P['tgv_elast']}},
           'names': {'official': OFFICIAL, 'added': ADDED, 'borrowed': list(BORROWED), 'wider': WIDER_ADDED, 'once': ONCE, 'costs': COSTS, 'france': FRANCE_ITEMS,
                     'key': {'job_users': JOB_USERS, 'plots': PLOTS, 'parks': PARKS, 'crowd': CROWD, 'resignal': RESIGNAL, 'noise': NOISE, 'bypass': BYPASS_ITEM, 'air_users': AIR_USERS,
                              'france_fares': FRANCE_FARES, 'air_co2': AIR_CO2, 'car_france': CAR_FRANCE, 'timetable': TIMETABLE, 'margin': MARGIN, 'build_co2': BUILD_CO2, 'cofp_added': COFP_ADDED,
                              'tgv_region': TGV_REGION, 'tgv_cross': TGV_CROSS, 'capacity': CAPACITY, 'reg_paris': REG_PARIS, 'ter_cross': TER_CROSS, 'producers': PRODUCERS,
                              'trainsets': TRAINSETS, 'terminals': TERMINALS, 'carbon_car': CARBON_CAR, 'roads': ROADS, 'cofp': COFP_ITEM, 'construction': CONSTRUCTION},
                     'explain': EXPLAIN, 'confidence': CONFIDENCE, 'families': [[f, ks] for f, ks in FAMILIES]}}
    cases = {'baseline': dict(only=[]), 'low': dict(level=0), 'central': dict(level=1, timeline=True), 'high': dict(level=2), 'rate32': dict(r=R_PUBLIC_2021),
             'high_cost': dict(o=dict(cost='high')), 'low_cost': dict(o=dict(cost='low')),
             'no_growth_4': dict(r=0.04, o=dict(ld_growth=0.0, sd_growth=0.0, vot_growth=0.0)),
             'no_capacity': dict(o=dict(capacity=False)), 'capacity_40': dict(o=dict(cap_value=40.0)), 'no_producers': dict(o=dict(producers=False)),
             'vot_ld_085': dict(o=dict(vot_ld_scale=0.85)), 'cofp_125': dict(o=dict(cofp_rate=0.25)), 'fares_14': dict(o=dict(cross_fares=1.4)),
             'running_075': dict(o=dict(om_scale=0.75)), 'ame': dict(o=dict(ame=True)),
             'no_timetable': dict(drop=[TIMETABLE]), 'no_france': dict(drop=FRANCE_ITEMS), 'no_parks': dict(drop=[PARKS]), 'no_landuse': dict(o=dict(landuse=0.0)),
             'no_margin': dict(drop=[MARGIN])}
    res['cases'] = {name: evaluate(m, **kw) for name, kw in cases.items()}
    res['timeline'] = res['cases']['central'].pop('timeline')
    res['timeline']['low'] = evaluate(m, 0, timeline=True)['timeline']['cum_npv']; res['timeline']['high'] = evaluate(m, 2, timeline=True)['timeline']['cum_npv']
    res['timeline']['jobs_low'] = evaluate(m, 0, timeline=True)['timeline']['jobs']; res['timeline']['jobs_high'] = evaluate(m, 2, timeline=True)['timeline']['jobs']
    res['budget'] = budget(m)
    base = res['cases']['baseline']['npv']
    items = [k for k in ADDED if k != COFP_ADDED]
    res['each_alone'] = {k: evaluate(m, 1, only=[k])['npv' if k not in WIDER_ADDED else 'npv_wider'] - base for k in items}
    res['all_but'] = {k: evaluate(m, 1, drop=[k])['npv' if k not in WIDER_ADDED else 'npv_wider'] for k in items}
    res['study'] = {lv: study_method(m, i) for i, lv in enumerate(LEVELS)}
    res['model'] = {'capex': m['cost'], 'capex_low': m['cost_low'], 'capex_high': m['cost_high'], 'annuity': m['annuity'], 'running': m['om_infra'] + m['om_trains'],
                    'renewal_year': m['renewal_year'], 'yearly_cost': m['yearly_cost'], 'systems': m['systems'], 'ops_rev': m['ops_rev']}
    res['jobs'] = {k: JOBS[k] for k in ('beta', 'pen', 'branch', 'easy', 'commuters_pt_suburb_pairs', 'users_low', 'users_central', 'users_high', 'trips_day', 'today_obs_day',
                                          'improved_pairs', 'hubs', 'induced_jobs_net', 'top_pairs', 'obs_over_fit_improved', 'keep_per_change')}
    res['parks'] = pk
    res['more_trains'] = more_trains()
    res['france'] = {'levels': {lv: {k: v for k, v in fr[lv].items() if k != 'air'} for lv in LEVELS}, 'air_pairs': fr['central']['air'], 'show': show_pairs(),
                     'bypass_total_2009': BYPASS_2009, 'bypass_helped_2009': sum(c['pax'] for c in BYPASS.values())}
    os.makedirs(OUT, exist_ok=True); json.dump(res, open(f'{OUT}/french.json', 'w'), indent=1, default=float)
    pr = lambda x: None if x is None else round(x, 3)
    for k, v in res['cases'].items():
        print(f"{k:14s} NPV {v['npv']:7.2f} per euro {v['per_euro']:6.3f} IRR {pr(v['irr'])}  with wider {v['npv_wider']:7.2f} per euro {v['per_euro_wider']:6.3f} IRR {pr(v['irr_wider'])}  ratio {v['ratio']:.2f} / {v['ratio_wider']:.2f}")
    c = res['cases']['central']
    print('PV by item (central):'); [print('  ', k[:70].ljust(72), round(v, 3)) for k, v in c['pv'].items()]
    s = res['study']['central']
    print('STUDY METHOD, complete list: benefits', round(s['benefit_total'], 3), 'wider', round(s['wider_total'], 3), 'yearly cost', round(s['yearly_cost'], 3), 'cover', round(s['cover'], 3), round(s['cover_wider'], 3), 'irr', pr(s['irr']))
    [print('  ', k[:70].ljust(72), round(v, 4)) for k, v in s['benefits'].items()]
    print('  once:', {k[:30]: round(v, 3) for k, v in s['once'].items()})
    print('  parks:', {k: round(v, 3) for k, v in pk['central'].items()})
    print('  france:', {k: (round(v, 4) if isinstance(v, float) else v) for k, v in fr['central'].items() if k not in ('air', 'by_side')})
    for k, v in fr['central']['by_side'].items(): print('    ', k, {kk: round(vv, 2) for kk, vv in v.items()})
    print('  break even', res['timeline']['break_even'], res['timeline']['break_even_wider'])


if __name__ == '__main__':
    main()
