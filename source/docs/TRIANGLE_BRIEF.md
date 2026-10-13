# The triangle: brief for updating the site (13 October 2026, updated in the evening for the shorter approach tunnels)

The site describes one project only: the triangle. Layouts A and B, the lean variants and the Pleyel hub are gone, not kept for
comparison. The model (model/nordest.py, model/finance.py, model/export.py, src/js/model.js) is already rebuilt; this brief says
what it now holds and what each page must say. Keep every chart, drawing component and script that works; change only the data
they read, the numbers, the assumptions and the text.

## 1. The concept

- Three deep through stations: Paris Nord-Est (under Gare du Nord and Gare de l'Est, entered from either hall), Gare de Lyon, Montparnasse.
- Tunnels: two pairs of tracks on the Y (north and east portals to Nord-Est; Nord-Est to Gare de Lyon and the south-east portal;
  Nord-Est to Montparnasse under the Seine and the Atlantic portal), 21.8 km each, plus one direct TGV link between the city ends of
  Montparnasse and Gare de Lyon, 5 km (4.5 to 6, assumption). 48.6 km of twin-track tunnel in all; seven corridors.
- Portals: the tunnels come up on the existing surface tracks at the ring road (north at Porte de la Chapelle, south-east at Porte de
  Charenton, Atlantic at Porte de Vanves) and, for the east, at Rosa Parks just inside it. At 35 mm per metre a tunnel 35 to 40 m deep
  reaches the surface in 1.0 to 1.2 km, so it need not stay underground further. Corridors (route km, read from maps, assumption):
  north 2.4, east 2.7, Nord-Est to Lyon 5.0, Nord-Est to Montparnasse 6.0, south-east 2.9, Atlantic 2.8 (`CORRIDOR_KM` in nordest.py;
  export.py checks that the project map uses the same lengths). Earlier: Saint-Denis 5.0, Pantin 4.5, Maisons-Alfort 7.0, Clamart 6.0.
- Pair 1 carries TGVs and regional express trains. Pair 2 carries suburban trains (lines H and K with N, P with R; changed on 13 October 2026, evening, from H and K with R, P with N:
  busiest line to the left bank, Val-d'Oise to the jobs of Versailles and Saint-Quentin, trains without a partner shared by both southern
  legs). Regional express: northern trains alternate between the two southern stations, eastern trains run on to Gare de Lyon. The link is for TGVs.
- No train reverses in Paris. Every TGV stops at two of the three stations. Every station has direct trains to all four directions,
  on half of the trains of each line.
- Service, lines at full capacity, trains an hour each way: Atlantic 15, south-east 16, north 8, east 4. Pairings: Atlantic to north 4,
  Atlantic to east 2, south-east to north 4, south-east to east 2, Atlantic to south-east by the link 9, one south-east train left
  without a partner turns back at Nord-Est. Tunnel legs each way: Montparnasse to Nord-Est 6, Gare de Lyon to Nord-Est 7, link 9.
  In the standard busy hour (12, 12, 8, 4): link 6, no spare train.
- Platforms, 40 tracks, 13,900 m:

  | Station | TGV, 400 m | Regional express, 350 m | Suburban, 225 m | Total |
  | --- | --- | --- | --- | --- |
  | Paris Nord-Est | 6 | 6 | 4 | 16 |
  | Gare de Lyon | 6 | 4 | 2 | 12 |
  | Montparnasse | 6 | 4 | 2 | 12 |

- TGV platform rule: platforms dedicated by direction, three each way. A stop is 4 minutes; a track needs about 3 minutes between a
  departure and the next arrival; a timetable can use 65% of that 7-minute cycle, so one track takes about 5.6 trains an hour
  (all three are assumptions). Two tracks each way would do on paper (a train every 8 minutes on each: 4 stopped, 4 empty); the third
  takes late trains. Load on the provided tracks with the lines full: Nord-Est 4.4, Gare de Lyon 5.3, Montparnasse 5.0 trains an hour
  per track. Benchmarks: Stuttgart's stress test about 6 per track an hour, Zürich's Löwenstrasse about 6 on average, Shinagawa's four
  tracks built for 15 trains an hour each way. Two-minute stops are ruled out (luggage); four-track TGV stations are ruled out (too tight).
- Regional express platforms are dedicated and 350 m long: Regio 2N sets are 81 to 135 m and run up to three coupled (270 to 330 m).
  14 platforms is the model's count, not a timetable (study point).
- London: no sealed pair. One of the six TGV tracks at Nord-Est can be closed off for each London departure, with a larger control hall
  and waiting room above (0.2 bn of works, assumption); boarding in 10 to 15 minutes. Arrivals from London need no check in Paris
  (checks are done before departure in London), so those trains can run on to the south. Northbound, passengers boarding in a
  southern station for London must be checked before boarding: open point. There are 12 non-stop London trains a day each way.
  Amsterdam already boards London trains from one closed-off platform.
- Surface: no surface hall is kept for trains. The four terminal sites become four park areas (about 160 hectares could be released,
  an estimate from maps; assumption). The land is not sold and the parks are not valued yet (study point). Open: CDG Express at Gare de l'Est.
- Cost basis: unit prices from final costs and signed contracts (they already hold past overruns); 27% for design, client costs and
  land bought; 15% risk central (10% low, 30% high). One 400 m platform track costs about 0.58 bn all-in; one km of twin tunnel about 0.26 bn.
- Charges (version 3.3, 14 October 2026): TGV charges fall only on new uses. 2.55 euros for boarding or leaving at a Paris station the
  passenger's line did not serve before (Gare de Lyon for the south-east, Montparnasse for the Atlantic, Nord-Est by either hall for the
  north and east keep today's price); 5.10 for crossing Paris, on a direct train or with a change in one station. A Paris-region
  passenger chooses the other station only when the time saved is worth more than the charge; no journey made today is lost.
  Regional express: 2.55 for
  getting off at the second station, 5.10 for crossing Paris without stopping. Nothing on suburban trains (Navigo pass and the
  Île-de-France ticket already cover the metro ride). Half of the operators' saving on trainsets is in the central case; shop rents
  at full yield are an option.

## 2. Central figures (2026 euros)

Version 3.3 (14 October 2026), what changed with the charge on new uses and the crossing traffic counted from the changes removed
(the older figures below are kept for the parts that did not change; where they differ, these win):
- Crossing Paris: each change of vehicle today keeps 63% of the potential traffic (British 37% loss per change, applied to each one,
  assumption); changes today by fewest-change route: Lyon-Nord 2, Lyon-Est 2, Montparnasse-Nord 2, Montparnasse-Est 2,
  Montparnasse-Lyon 3, Nord-Est 1. A change inside one station counts as half a change and keeps 79%, as for suburban trips (no pulse: each direction evenly spaced over the hour; the Swiss 89% is a test). Time model
  (elasticity -1.1) on the door-to-door trip, 55 minutes at the two ends; averaged over three main destinations per line (Lille,
  Brussels, London; Strasbourg, Metz, Reims; Lyon, Marseille, Montpellier; Bordeaux, Nantes, Rennes; fastest train times, unverified).
  Traffic with the project, times today: Atlantic-SE 4.13, Atlantic-N 2.64, Atlantic-E 2.66, SE-N 2.59, SE-E 2.60, N-E 1.36; all 3.07.
  New crossing journeys 10.7 M before the charge (low case, the earlier method: 1.56 M; high, all on direct trains: 12.9 M;
  Swiss timed change 11.6 M; a change in one station costing a full change 9.3 M).
- TGV traffic with the charge: 12.1 M new journeys (1.9 M Paris region, 10.2 M crossing), 1.5 M held back by the charge, none lost.
  38% of Paris-region passengers choose another station and pay; they gain 8.0 euros each; a crossing passenger gains 54 euros.
- Operations: income 747 m against 393 m (190%; surplus 353 m, which goes to the capital account): TGV charge 180, track charges on
  new journeys 378 (two fares for a crossing), Navigo 15, regional express fares 16, authority fee 35, shops 24, trainset share 26,
  regional express charge 72. 135% with no charge at all, 165% with the TGV charge alone, 99% in the low traffic case. Break-even 0.
- Benefits 1,505 m a year (TGV 559, regional 177, comfort 49, wider 381): 70% of the yearly cost, 52% time and comfort only, 107% on
  cost net of income; 99% with 1.5% growth. Rate of return 1.45% (2.95% with growth). Grant 10.6 bn (26%); public money in all
  32.3 bn (80%). Tax return 442 m. Before this version (with the regional pairing of 13 October): operations 123%, benefits 1,271 m
  and 59%, grant 16.7 bn (41%), rate of return 0.7%.
- Link ride 9 minutes instead of 6 (open question from the timetable study): under 1% fewer crossing journeys; operations and
  benefits move by under one point.

- Construction cost 40.5 bn (27.2 with low prices and 10% risk, 60.1 with high prices and 30% risk). Works 27.7 bn: tunnels 6.32 civil
  and 2.19 systems, stations 13.9, halls 1.8, junctions 1.5 (6 at 0.25), portals 1.2 (8 at 0.15), sidings 0.6, London control hall 0.2.
  Gross-up 1.4605. Stations all-in: Nord-Est 7.89, Gare de Lyon 6.21, Montparnasse 6.21.
- Repayment 1.755 bn a year (3%, 60 years, 12-year build, interest during works 1.20).
- Running cost 393 m a year (tunnels and stations 293, extra regional trains 55, renewal 45); low case 277, high case 454.
- Income 446 m: TGV charge 286, track charges lost on journeys given up minus 22, Navigo 14, regional express fares 12, authority fee 35,
  shops 22, half trainset saving 26, regional express charge 73 (second station 23.0 M passengers at 2.55 = 58; crossing 2.78 M at 5.10 = 14).
  Operations covered 113.5% (balance plus 53 m); 119% with shops at full yield; 161% with low running costs, 98% with high; 88% with the
  TGV charge alone; 40% with no charge at all. Break-even TGV charge 1.91 (0.55 low running, 2.65 high, 3.12 with the TGV charge alone).
  Neutral charge (journeys lost = journeys added) 1.70, 2.40 with response -0.5.
- TGV traffic: 103.3 M Paris-region journeys, 6.7 M crossing (5.18 M today + 1.56 M new), 3.17 M on direct trains; charge removes
  4.10 M journeys against 2.77 M added; net minus 1.32 M. Gain per Paris-region passenger 1.49 euros, per crossing passenger 53 euros.
- Benefits 905 m a year (after 6 m lost on journeys given up): access 153, crossing 316, regional time 129, comfort 35, wider effects
  277 (urban 54, productivity 82, employment 142). Benefits over yearly cost (2.15 bn) 42%; time and comfort only 29%; over the
  repayment alone 52%; on cost net of income (British basis) 53%. With 1.5% growth 59%; at 4.5% with growth 41%; with passengers
  picking their train 47%.
- Public money: grant 17.5 bn (43% of cost) on top of the business tax package (0.9 bn a year, 20.8 bn as money during the works) and
  the European grant 1 bn; public money in all 39.2 bn, 97% of the cost. The operations surplus is not counted against construction.
  No land sales.
- Tax return a year: 230 m central (0 to 849 m across the readings), 13% of the repayment.
- Rate of return for society: minus 0.8% central, +1.1% with growth, +2.3% best case.
- Access (1,000 points in Paris, equivalent minutes at official weights): today 27.4 minutes; to the entrance of the nearest station
  where the train stops 22.8; counting the ride between Paris stops 25.7 (the measure used for benefits, 2.55 weighted minutes saved,
  benefit 153 m, 1.22 M new journeys); if the passenger picks a train that calls at their best station 24.5 (4.35 minutes, 262 m,
  2.09 M new journeys). 98.9% of points quicker on the ride measure, the rest unchanged, none slower. By direction, ride measure:
  north 27.6 to 25.9, east 27.2 to 25.9, south-east 27.6 to 25.9, Atlantic 27.1 to 25.6 (pick: 25.1, 25.1, 24.2, 24.2).
- Crossing Paris: Montparnasse to Gare de Lyon 6 minutes direct by the link (was 29 via Nord-Est with a reversal); other pairs 10 or
  11 minutes direct; a change inside Nord-Est 12.5 clock minutes; today 57.5 minutes (30 between Gare du Nord and Gare de l'Est).
  Direct share 47%; uplift 30% in all (37% on direct trains, time model for the rest).
- Regional: 116.3 M users a year reach a Paris terminal (75.7 M suburban, 40.6 M regional express; line N corrected to 30.4 M); 23.7 M new journeys (21.7 suburban, of which 1.4 suburb to suburb across Paris; 2.0 regional express); average saving 2.7 clock minutes. Second station used by 38.0 M suburban and 22.6 M regional express passengers
  (shares: H and K 72%, P 44%, N 32%, R 19%; TER Nord 73%, Est 44%, Montparnasse 32%, Lyon 19%). Regional express crossing Paris
  2.78 M (5% of today's users, assumption, plus 37%). Regional time benefit 177 m a year: Paris trips 161 m,
  suburb to suburb across Paris 16 m (`cross_paris`: 1.06 M trips today, 2.44 M with the project; 14% of station trips only pass
  through between two suburbs (survey), 20% of those on these lines bound across the triangle, each change costs 37% of the traffic,
  a change across one platform half a change; keys `m.regional.cross`, `m.params.cross_share` and others).
- Stages (cost only, all-in): first stage Nord-Est and Gare de Lyon with the north, east, Nord-Est to Lyon and south-east corridors
  (26 km of twin tunnel) 26.3 bn; second stage Montparnasse with its two corridors and the link (22.6 km) 14.2 bn.
- Sensitivity (benefits over yearly cost): low prices 58%, high prices 30%, 15 years of works 41%, 2 minutes longer to board 24%,
  pick a train 48%, Nord hall only 35%, crowded metro heavier 45%, direct trains gain 57% 43%, time model only 42%, metro weights 38%,
  suburban +25% 43%, +5% 42%, tunnel upkeep high 41%, low 44%, crossing at top of survey 48%, half as many crossing 35%, 60% of traffic
  41%, 10% more TGV traffic from capacity 42% (income effect only).
- Back-test at 15% risk (model without risk, with risk, published): RER E 1999 3.18, 3.65, 2.49; RER E west 4.65, 5.35, 5.83 to 7.07;
  Lyon 3.54, 4.07, 3.84; Marseille 3.91, 4.49, 3.39; Stuttgart 12.6, 14.5, 14.5; Zürich 3.84, 4.41, 2.75; Munich 4.2, 4.8, 10.9.
- Comparables on the same basis: the Elizabeth line's 1.97 is on cost net of fares; on gross cost about 0.8 to 1.2. Capital per
  yearly journey: about 178 euros here (227 M journeys a year), about 150 for the Elizabeth line, about 210 for Lucerne.

## 3. Model keys (what the templates and scripts can read)

Old keys with A or B no longer exist. `{{ ... }}` expressions see `m` (src/data/model.json), `f` (finance cases), `b` (finance base),
`fp` (finance params), `pts` (points.json), `d` (all data files). Scripts read `PTS.data.model`, `PTS.data.finance`, `PTS.data.points`.

- `m.cost` is the one cost object: `total, hard, soft, land, risk, items{...}, tunnel_km (48.6), link_km (5), platform_m{station}, platform_total,
  tracks{station}, detail{station}{hs,ter,sub}, portals (8), junctions (6), station_cost{station}`. `m.cost_low`, `m.cost_high` are numbers.
  `m.layout` (pairs, halls, stations), `m.len` (hs 400, ter 350, sub 225), `m.link_km`, `m.rates` (now with `london_hall` and `risk` 0.15),
  `m.rates_low`, `m.rates_high`, `m.gross_up` (1.4605), `m.station_total{station}`.
- `m.service`, `m.service_full`: `flows{'Atlantic to north', 'Atlantic to east', 'Southeast to north', 'Southeast to east',
  'Atlantic to southeast, by the direct link'}, through_each_way, link_each_way, spare, rev_equiv, legs{'Montparnasse to Nord-Est',
  'Gare de Lyon to Nord-Est', 'Montparnasse to Gare de Lyon'}, per_track, tracks_per_direction, stops_direction{station},
  nordest_stops, nordest_tracks_calc, nordest_load, lyon_..., montparnasse_...`. `m.stop_min, m.clear_min, m.util, m.per_track,
  m.tracks_per_direction, m.reverse` (for the one turning train), `m.hour_today`, `m.hour_full`.
- `m.TH` has `L` 10, `M` 11, `LM` 6. `m.TR` unchanged.
- Access: `m.paris{today, nordest, pick, no_choice, nord_hall}`, `m.access{central, pick, no_choice, nord_hall, deep2}`,
  `m.access_effect{central, pick, no_choice, deep2, nord_hall, comfort}`, `m.by_dir[dir]{today, nordest, pick, no_choice}`, `m.by_arr`,
  `m.far_stop_share`, `m.value_of_choice`, `m.share_quicker`, `m.max_gain`. `pts.avg{today, station, ride, pick}`, `pts.share_quicker{...}`,
  `pts.max_gain{...}`, rows have 20 columns: id, lat, lon, arr, today N E L M, station N E L M, ride N E L M, pick N E L M.
- Crossing: `m.connecting{central, high, single, single_high, model_only, all_direct, none_direct, metro_weights, british_change}`
  (central and high use the changes removed; single is the earlier estimate); pairs carry `transfers` and `growth`;
  `m.destinations` (54 city pairs: from, to, pair, today, direct, change, transfers, mult_direct, mult_change), `m.dest_axis` by pair of
  lines, `m.dest`; `m.params.change_keep`, `station_keep`, `acc_egr`, `elast`; pairs
  `Montparnasse-Lyon` is served, direct 6 minutes.
- Regional: `m.regional` adds `second_station_sub, second_station_ter, second_station_share{...}, through_ter`.
- `m.params` adds `stop_min, clear_min, util, per_track, tracks_per_direction, second_min, ter_through_share, park_ha, direct_share`.
- `m.yearly` (central), `m.yearly_pick` (passenger picks the train), `m.sens{test name}` with the new test names:
  'Low unit prices and 10% risk', 'High unit prices and 30% risk', 'Passengers pick a train that calls at their best station',
  'Platforms no longer cap the lines: 10% more TGV traffic'; the tests on fixed pairs and on land are gone. `m.deep2_scaled`,
  `m.rate_tests{'3.6','4.6'}{all, time}`, `m.stages{first, second}{hard, total, km}`, `m.extras` (adds `park_ha`; `lost_charge_journeys` gone).
- Finance cases `f.<name>`: central, no_charge, tgv_charge_only, low_running, high_running, shops_full, no_fleet, package_low_running,
  growth, low_cost, high_cost, high_traffic, low_traffic, pick, best, navigo_all, navigo_low, tax_high, tax_low, rate45, rate45_flat,
  resp05, charge_double, all_levers; numbers `f.breakeven_charge`, `f.breakeven_charge_low_running`, `f.breakeven_charge_high_running`,
  `f.breakeven_charge_tgv_only` (neutral charges are gone: no journey is lost). Each case has the same fields as before plus
  `econ_cover_net`, `econ_cover_transport_net`. `ops_rev` keys: 'Charge on high-speed passengers', 'Track charges on
  new TGV journeys', 'New Navigo pass holders', 'Fares from new regional express passengers', 'Fee paid by the regional transport
  authority', 'Shops in the new station halls', 'Share of the operators’ saving on trainsets', 'Charge on regional express passengers'.
  `tgv`: paris, cross, through, change, paying_paris, pay_share, new_before_charge, held, held_paris, held_cross, net_new, new_paris,
  new_cross, paying, charge_gross, charge_paris, charge_cross, gain_paris_euro, gain_paris_all_euro, gain_cross_euro (lost and
  charge_net are gone). `benefits` has no line for journeys given up. `b.access_curve{station, ride}` holds the Paris-region response
  by level of charge; `b.traffic.<case>.cross_parts` the crossing flows.
  `cap_sources` keys: 'Surplus of the operations account', 'Regional business tax package', 'Payroll transport levy', 'European grant'.
- `b.layout` (capex{low,central,high}, systems, tunnel_km, platform_m, fee_km, om_low, om_high, items, hard, soft, land, risk, stations,
  station_m, tracks), `b.cost_def{rates, route_km, link_km, radials, len, layout}`, `b.traffic{central, high, low, pick}` with
  `rex_second, rex_through, sub_second`, `b.park_ha`, `b.rex_second`, `b.rex_through`, `b.defaults` (no layout; `shop_net` 0.5,
  `fleet_capture` 0.5, `rex_second`, `rex_through`). Gone: `b.layouts`, `b.land_nominal`, `b.land_delay`.
- `fp`: charge_end, charge_through, rex_second, rex_through, fare_response_low, navigo_new, om_low, om_high (numbers), station_low,
  shop_net, growth, fleet_capture, park_ha. Gone: charge_alt, reg_supp.
- `d.finance.irr{central, growth, low_cost, best}`.
- Browser: `PTS.model.cost(rates)` (optional second argument: a layout like `b.cost_def.layout`), `PTS.model.accounts(options)`
  (options may set cost, traffic, charge_end, charge_through, rex_second, rex_through, fare_response, navigo_new, om_scale ('low',
  'high' or a number), rate, growth, fleet_capture, shop_net, levy, payroll_pts, eu_grant, tax_wider, capex, systems),
  `PTS.model.breakevenCharge(options)`.

- Timetable of the hour (Annex D, evenly spaced, 4-minute stops; a pulse timed for changes as comparison; `model/timetable.py`, read as `d.timetable`): `inputs` (stop, clear, tracks, headway 3, change_same 4, change_other 6,
  run {L 6, M 7, LM 5}, model_run, technical, ratio of Paris to crossing passengers), `cases{even20, even10, pulse20, random20, pulse10, random10}` (cross,
  change_avg, wait_avg, change_wave, line, pairs), `frontier{stop minutes}`, `sens`, `chosen` and `standard` (every train with its minutes and
  tracks), `spare`, `turn_minutes`. The link runs 5 minutes in the timetable, not the model's 2 (start-to-stop check over 5 km).

## 4. Writing rules

- Follow CONTRIBUTING.md. No long dashes anywhere (use a comma, a semicolon, "to" or a new sentence). British spelling. Plain words.
- Mark unsourced figures with `<span class="tag assume">assumption</span>`; cite with `[[key]]` and a sources.json entry.
- Nothing about layouts A and B, the lean variants, the hub, reversing trains (except the one train an hour that turns back at
  Nord-Est when the south-east line is full), sealed tracks or land sales.
- Keep the figures honest: operations balance only with the income package; construction is not repaid by counted benefits; say what
  is assumed. Where a page used a quick figure from today, use the model's number instead.
- Keep every block id and anchor listed in CONTRIBUTING.md; the renamed anchors are project.layouts -> project.networks (plus the new
  project.parks) and service.reversing -> service.link. Links to removed anchors must be redirected.
- Do not edit shared files (src/css, src/js, build.py, manifest.json) or other sections. Run `python3 build.py` from the repo root
  until your sections report no error and no warning, then screenshot each of your sections at 1280 (light) and 400 (dark) with
  `NODE_PATH=/opt/npm-tools/node_modules node tools/shot.js --hash <id> --out <png>` (add `--width 400 --dark` for the phone view;
  `--full` for the whole page) and look at the images.

## 5. Study points to keep visible (not resolved today)

I1 what limits train numbers today; I2 one hour on six tracks at each station; I3 regional express trains an hour and platform count;
I4 one suburban pair against the peak of lines H, K and P (a third pair would cost about 10 bn); I5 London (closed-off platform
precedents, control hall, northbound checks); I6 CDG Express; I7 link geometry; I8 stages; I9 unit prices item by item (which are
all-in); I10 risk by item; I11 running costs net of today's terminals; I12 a fresh count of passengers crossing Paris; I13 the province
to province market (car, air, bypass trains: 13 M province to province passengers on bypass trains in 2009; Bordeaux to Lille 4h47
direct round Paris today, 4h21 with a change, about 3h25 through Paris); I14 regional benefits as through lines (frequency, crowding
relief, journeys across the region); I15 regional express passengers crossing Paris; I16 access with passenger choice (done in the
model as a second measure); I17 traffic growth (Velvet: 12 trains from 2028, 10 M more seats a year; south-east line to 16 trains an
hour by 2030); I18 wider effects for TGV links (Cologne to Frankfurt +8.5% output in intermediate towns, halving every 30 minutes of
travel; TGV links raised French group margins 0.6 to 0.8 points); I19 the parks (area, value, cost); I20 comparables on the same basis.
