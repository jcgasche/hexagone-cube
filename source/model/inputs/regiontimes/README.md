# Station-to-station times (chapter "Travel times in the region")

Written by `model/regiontimes.py`; the network versions are in `model/inputs/networks/`.

| File | What it is |
| --- | --- |
| `today.npz` | Today's network: minutes from every station to every other (770 x 770), with the stations' names, places and lines. Command `run`. |
| `future.npz` | The network before the project: today's network with metro lines 15 to 18 (792 stations). It is the base that every version of the project is compared with. Commands `gpe` then `run`. |
| `plan.npz`, `plan_rer_f.npz`, `plan_rer_g.npz`, `plan_ter.npz`, `plan_g_no_chatelet.npz` | The plan and its parts, each on the network before the project. |
| `plan_today.npz` | The plan on today's network, without lines 15 to 18. |
| `plan_kb.npz`, `plan_rd.npz`, `plan_kb_rd.npz` | The plan with line K run into RER B, line R run into RER D, or both (annex "RER D beside RER G"). |
| `variant_c.npz` | The variant of the annex "Line L with RER C": line L joined to RER C south, RER C west joined to line H, lines K and R through. |
| `weights.npz` | The towns of Ile-de-France, their nearest stations with the time to reach them, and the journeys to work by public transport from town to town (INSEE census 2022, MOBPRO). A town uses the five nearest stations of today's network and every new station on file, so that adding a station never makes a trip slower. Command `weights`. |
| `riders.json` | For each version, the people going to work one morning through the sections watched in the centre of Paris (terminals, tunnels). Command `riders`. Read by `model/flows.py` to size the tunnels of RER F and RER G. |

Inputs that are not stored here, because of their size:

- the timetable: Ile-de-France Mobilites, open data, "offre-horaires-tc-gtfs-idfm" (GTFS), version of 15 October 2026, day read: Tuesday 3 November 2026.
  https://data.iledefrance-mobilites.fr/explore/dataset/offre-horaires-tc-gtfs-idfm/
- the census files used by `weights` (the same as for `model/flows.py`): communes with their centres and areas, and the MOBPRO flows by mode.

A network version is a short JSON file. It can `include` other files (for instance `gpe` for lines 15 to 18, `rer_g`, `ter`, `k_into_b`), add platforms and walks, cut a line in two (`split`), run a line on along a new path (`extend`), join two lines end to end (`through`) and name the sections to count riders on (`watch`).

To test a new version of the network:

    python3 model/regiontimes.py run model/inputs/networks/my_version.json --gtfs <timetable folder>
    python3 model/regiontimes.py compare future my_version

To rebuild the figures of the study after a change, in this order (from `source/`):

    python3 model/regiontimes.py riders      # riders.json
    python3 model/flows.py                   # chapter "Passengers by line", tunnels sized from riders.json
    python3 model/regiontimes.py export      # chapter "Travel times in the region"; add a name to VERSIONS to list it
    python3 model/rerd.py                    # annex "RER D beside RER G"
    python3 model/variantc.py                # annex "Line L with RER C"
    python3 build.py

`python3 model/regiontimes.py validate` sets today's times beside those of a public journey planner (the trips are in `model/inputs/traffic/raw/reference_journeys.json`).
