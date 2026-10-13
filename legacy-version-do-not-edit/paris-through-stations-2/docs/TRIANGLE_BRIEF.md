# The triangle: brief for updating the site (13 October 2026)

The site describes one project only: the triangle. Layouts A and B, the lean variants and the Pleyel hub are gone, not kept for
comparison. The model (model/nordest.py, model/finance.py, model/export.py, src/js/model.js) is already rebuilt; this brief says
what it now holds and what each page must say. Keep every chart, drawing component and script that works; change only the data
they read, the numbers, the assumptions and the text.

## 1. The concept

- Three deep through stations: Paris Nord-Est (under Gare du Nord and Gare de l'Est, entered from either hall), Gare de Lyon, Montparnasse.
- Tunnels: two pairs of tracks on the Y (north and east portals to Nord-Est; Nord-Est to Gare de Lyon and the south-east portal;
  Nord-Est to Montparnasse under the Seine and the Atlantic portal), 33.5 km each, plus one direct TGV link between the city ends of
  Montparnasse and Gare de Lyon, 5 km (4.5 to 6, assumption). 72 km of twin-track tunnel in all; seven corridors.
- Pair 1 carries TGVs and regional express trains. Pair 2 carries suburban trains (lines H and K with R, P with N). The link is for TGVs.
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
- Charges: TGV 2.55 euros per Paris departure or arrival, 5.10 for crossing on a direct train (unchanged). Regional express: 2.55 for
  getting off at the second station, 5.10 for crossing Paris without stopping. Nothing on suburban trains (Navigo pass and the
  Île-de-France ticket already cover the metro ride). Half of the operators' saving on trainsets is in the central case; shop rents
  at full yield are an option.

## 2. Central figures (2026 euros)

- Construction cost 46.4 bn (31.7 with low prices and 10% risk, 69.4 with high prices and 30% risk). Works 31.8 bn: tunnels 9.36 civil
  and 3.24 systems, stations 13.9, halls 1.8, junctions 1.5 (6 at 0.25), portals 1.2 (8 at 0.15), sidings 0.6, London control hall 0.2.
  Gross-up 1.4605. Stations all-in: Nord-Est 7.89, Gare de Lyon 6.21, Montparnasse 6.21.
- Repayment 2.014 bn a year (3%, 60 years, 12-year build, interest during works 1.20).
- Running cost 467 m a year (tunnels and stations 345, extra regional trains 55, renewal 67); low case 322, high case 557.
- Income 465 m: TGV charge 286, track charges lost on journeys given up minus 22, Navigo 14, regional express fares 12, authority fee 54,
  shops 22, half trainset saving 26, regional express charge 73 (second station 23.0 M passengers at 2.55 = 58; crossing 2.78 M at 5.10 = 14).
  Operations covered 99.5% (balance minus 2 m); 104% with shops at full yield; 144% with low running costs, 83% with high; 78% with the
  TGV charge alone; 38% with no charge at all. Break-even TGV charge 2.58 (0.85 low running, 3.70 high, 3.82 with the TGV charge alone).
  Neutral charge (journeys lost = journeys added) 1.70, 2.40 with response -0.5.
- TGV traffic: 103.3 M Paris-region journeys, 6.7 M crossing (5.18 M today + 1.56 M new), 3.17 M on direct trains; charge removes
  4.10 M journeys against 2.77 M added; net minus 1.32 M. Gain per Paris-region passenger 1.49 euros, per crossing passenger 53 euros.
- Benefits 905 m a year (after 6 m lost on journeys given up): access 153, crossing 316, regional time 129, comfort 35, wider effects
  277 (urban 54, productivity 82, employment 142). Benefits over yearly cost (2.48 bn) 36.5%; time and comfort only 25%; over the
  repayment alone 45%; on cost net of income (British basis) 45%. With 1.5% growth 51%; at 4.5% with growth 35%; with passengers
  picking their train 41%.
- Public money: grant 24.7 bn (53% of cost) on top of the business tax package (0.9 bn a year, 20.8 bn as money during the works) and
  the European grant 1 bn; public money in all 46.5 bn, about 100% of the cost. No land sales.
- Tax return a year: 230 m central (0 to 849 m across the readings), 11% of the repayment.
- Rate of return for society: minus 1.5% central, +0.5% with growth, +1.7% best case.
- Access (1,000 points in Paris, equivalent minutes at official weights): today 27.4 minutes; to the entrance of the nearest station
  where the train stops 22.8; counting the ride between Paris stops 25.7 (the measure used for benefits, 2.55 weighted minutes saved,
  benefit 153 m, 1.22 M new journeys); if the passenger picks a train that calls at their best station 24.5 (4.35 minutes, 262 m,
  2.09 M new journeys). 98.9% of points quicker on the ride measure, the rest unchanged, none slower. By direction, ride measure:
  north 27.6 to 25.9, east 27.2 to 25.9, south-east 27.6 to 25.9, Atlantic 27.1 to 25.6 (pick: 25.1, 25.1, 24.2, 24.2).
- Crossing Paris: Montparnasse to Gare de Lyon 6 minutes direct by the link (was 29 via Nord-Est with a reversal); other pairs 10 or
  11 minutes direct; a change inside Nord-Est 12.5 clock minutes; today 57.5 minutes (30 between Gare du Nord and Gare de l'Est).
  Direct share 47%; uplift 30% in all (37% on direct trains, time model for the rest).
- Regional: 114.5 M users a year reach a Paris terminal (73.9 M suburban, 40.6 M regional express); 21.3 M new journeys (19.9 suburban,
  1.5 regional express); average saving 2.3 clock minutes. Second station used by 37.0 M suburban and 22.9 M regional express passengers
  (shares: H and K 67%, P 51%, N 32%, R 19%; TER Nord 72%, Est 63%, Montparnasse 32%, Lyon 19%). Regional express crossing Paris
  2.78 M (5% of today's users, assumption, plus 37%).
- Stages (cost only, all-in): first stage Nord-Est and Gare de Lyon with the north, east, Nord-Est to Lyon and south-east corridors
  (43 km of twin tunnel) 30.6 bn; second stage Montparnasse with its two corridors and the link (29 km) 15.8 bn.
- Sensitivity (benefits over yearly cost): low prices 50%, high prices 26%, 15 years of works 35%, 2 minutes longer to board 20%,
  pick a train 41%, Nord hall only 31%, crowded metro heavier 39%, direct trains gain 57% 37%, time model only 37%, metro weights 33%,
  suburban +25% 37%, +5% 36%, tunnel upkeep high 35%, low 38%, crossing at top of survey 42%, half as many crossing 31%, 60% of traffic
  36%, 10% more TGV traffic from capacity 37% (income effect only).
- Back-test at 15% risk (model without risk, with risk, published): RER E 1999 3.18, 3.65, 2.49; RER E west 4.65, 5.35, 5.83 to 7.07;
  Lyon 3.54, 4.07, 3.84; Marseille 3.91, 4.49, 3.39; Stuttgart 12.6, 14.5, 14.5; Zürich 3.84, 4.41, 2.75; Munich 4.2, 4.8, 10.9.
- Comparables on the same basis: the Elizabeth line's 1.97 is on cost net of fares; on gross cost about 0.8 to 1.2. Capital per
  yearly journey: about 204 euros here (227 M journeys a year), about 150 for the Elizabeth line, about 210 for Lucerne.

## 3. Model keys (what the templates and scripts can read)

Old keys with A or B no longer exist. `{{ ... }}` expressions see `m` (src/data/model.json), `f` (finance cases), `b` (finance base),
`fp` (finance params), `pts` (points.json), `d` (all data files). Scripts read `PTS.data.model`, `PTS.data.finance`, `PTS.data.points`.

- `m.cost` is the one cost object: `total, hard, soft, land, risk, items{...}, tunnel_km (72), link_km (5), platform_m{station}, platform_total,
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
- Crossing: `m.connecting{central, high, model_only, all_direct, none_direct, metro_weights}` (no `corridor`); pairs
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
  `f.breakeven_charge_tgv_only`, `f.neutral_charge`, `f.neutral_charge_resp05`. Each case has the same fields as before plus
  `econ_cover_net`, `econ_cover_transport_net`. `ops_rev` keys: 'Charge on high-speed passengers', 'Track charges on the net change
  in TGV journeys', 'New Navigo pass holders', 'Fares from new regional express passengers', 'Fee paid by the regional transport
  authority', 'Shops in the new station halls', 'Share of the operators’ saving on trainsets', 'Charge on regional express passengers'.
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
