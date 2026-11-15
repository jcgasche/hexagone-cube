# Station-to-station times (chapter "Travel times in the region")

Written by `model/regiontimes.py`; the network versions are in `model/inputs/networks/`.

| File | What it is |
| --- | --- |
| `today.npz`, `plan.npz`, `plan_rer_f.npz`, `plan_rer_g.npz`, `plan_ter.npz`, `plan_g_no_chatelet.npz` | For one version of the network: minutes from every station to every other (770 x 770), with the stations' names, places and lines, and the log of the trains joined end to end. Command `run`. |
| `weights.npz` | The towns of Ile-de-France, their nearest stations with the time to reach them, and the journeys to work by public transport from town to town (INSEE census 2022, MOBPRO). Command `weights`. |

Inputs that are not stored here, because of their size:

- the timetable: Ile-de-France Mobilites, open data, "offre-horaires-tc-gtfs-idfm" (GTFS), version of 15 October 2026, day read: Tuesday 3 November 2026.
  https://data.iledefrance-mobilites.fr/explore/dataset/offre-horaires-tc-gtfs-idfm/
- the census files used by `weights` (the same as for `model/flows.py`): communes with their centres and areas, and the MOBPRO flows by mode.

To test a new version of the network:

    python3 model/regiontimes.py run model/inputs/networks/my_version.json --gtfs <timetable folder>
    python3 model/regiontimes.py compare today my_version
    python3 model/regiontimes.py export        # writes src/sections/times/data.json; add the name to VERSIONS to list it in the chapter
