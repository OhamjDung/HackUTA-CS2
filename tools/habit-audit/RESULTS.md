# Measured source-player habits

Ran on 2026-11-14 (America/Chicago), Python 3.14 on macOS. Base main was
`a2caf02`; the audit ran after cleanup commit `58c5dde`. The exact audit source SHA256
is `4dd30a408acb2e7fb078ae9b8102fa3e192dcc1954a53a3efdb663c2a0d45e9e`;
method SHA256 is `8f55611f274bda02abf3029dd19091669ed6ae71e1a7f64504b16f5bf63718da`.
Full outputs, input checksums and procedural locks are in ignored `data/habit-audit/`.
No code under clone-model/, clone-director/, match-service/, frontend/ or committed
clones/ was changed by this audit.

Seven verified build matches were analyzed first: donk 2393237/2393232/2393240
(62 rounds), broky 2392601/2393037/2393059/2393063 (79 rounds). Match 2393226 was
excluded. The method and training-only purchase policy were fixed before describing
holdouts 2393242/2393024, which were read once by this audit (39 rounds). `method-lock.json`
records the audit/method hashes and hash of `policy-freeze.json`; `holdout/audit.json`
was produced only afterward. No held-out result selected a weapon policy or threshold.

| Split / player / side | Matches / rounds | First-known sampled AWP rounds / known inventory rounds | AWP held seconds / known-inventory alive seconds | AWP gun-fire events / all gun-fire events | AWP kills / all kills |
|---|---:|---:|---:|---:|---:|
| Build broky CT | 4 / 41 | 23 / 41 | 1489.69 / 2521.25 | 45 / 341 | 16 / 31 |
| Build broky T | 4 / 38 | 13 / 38 | 1092.81 / 3163.80 | 19 / 273 | 9 / 25 |
| Build donk CT | 3 / 36 | 0 / 36 | 0 / 2669.12 | 0 / 697 | 0 / 30 |
| Build donk T | 3 / 26 | 0 / 26 | 0 / 1803.06 | 0 / 431 | 0 / 22 |
| Holdout broky CT | 1 / 12 | 9 / 12 | 678.94 / 883.61 | 17 / 58 | 9 / 14 |
| Holdout broky T | 1 / 10 | 2 / 10 | 155.56 / 794.84 | 4 / 93 | 1 / 3 |
| Holdout donk CT | 1 / 12 | 0 / 12 | 0 / 700.98 | 0 / 159 | 0 / 10 |
| Holdout donk T | 1 / 5 | 0 / 5 | 0 / 461.16 | 0 / 57 | 0 / 2 |

The build evidence independently supports the reported role mismatch: broky held an
AWP for 59.1% of known-inventory alive CT time and 34.5% of T time, despite relatively
few AWP gun-fire events. Both committed full-buy lists instead choose a rifle. CT AWP
time share ranged 50.2–65.4% across the four build matches; T ranged 0–39.4%. A single
static buy plan cannot express this match-to-match mixture. Donk had no observed AWP
possession in any of the verified build matches. None of these comparisons says a
candidate purchase will execute correctly in CS2.

The held-out description reproduces the historical **10 of 17** broky AWP kills. It
also shows the limit of a universal sniper description: on the T holdout side broky
held the AWP in only 2 of 10 first-known inventories and spent more alive time carrying
an AK. This observation was not used to revise the frozen policy. A gun-fire event,
active weapon, carried weapon and kill weapon are separate measures, not interchangeable
ratings of preference or skill.

| Split / player / side | Median horizontal speed (units/s) | Pause share (<10 units/s) | Mean yaw turn (degrees/s) | Observed opening seconds / alive seconds |
|---|---:|---:|---:|---:|
| Build broky CT | 97.6 | 23.4% | 31.7 | 720.83 / 2521.25 |
| Build broky T | 108.1 | 20.9% | 33.9 | 690.31 / 3163.80 |
| Build donk CT | 113.3 | 9.2% | 39.0 | 621.78 / 2669.12 |
| Build donk T | 116.1 | 13.3% | 37.1 | 475.56 / 1803.06 |
| Holdout broky CT | 98.5 | 30.4% | 26.4 | 214.80 / 883.61 |
| Holdout broky T | 97.7 | 16.6% | 27.0 | 184.17 / 794.84 |
| Holdout donk CT | 111.5 | 13.1% | 35.8 | 213.02 / 700.98 |
| Holdout donk T | 119.3 | 11.2% | 49.8 | 89.14 / 461.16 |

These proxies describe movement only. Speed comes from position differences and real
time deltas, not the archive's apparently scaled velocity arrays. Mean turns wrap yaw
at 180 degrees. Both endpoints must be alive and finite, so death-boundary intervals
are omitted from speed/turn denominators while alive duration is clipped at the death
event. Build openings cover 21.8–28.6% of alive time by side, consistent with a short
recorded opening followed by generic bot behavior. The sparse estimate is not an exact
rebuild of the pipeline's 64 Hz route files.

Area and occupied-position grid distributions are in the full JSON. Top build areas
were broky CT: CTSpawn/BombsiteA/Shop; broky T: SideAlley/BombsiteA/TopofMid;
donk CT: CTSpawn/BombsiteA/Jungle; donk T: TopofMid/TSpawn/BombsiteA. Areas are weighted
by observed alive seconds; occupied grid cells are not map geometry.

All 180 selected rounds had inventory available at the first alive sample. Nevertheless,
this is first-known sampled possession, **not freeze-end possession**: most source samples
start at 0.5 s. Missing starts and final unsampled tails are not extrapolated. In this
run all observed inventory/active weapon/area/position values were valid, no event
indices were rejected, and only movement/turn intervals touching death or a dead
endpoint were omitted (73 build intervals, 17 holdout intervals). Missing-field behavior
is covered by synthetic tests. Fire counts are source parser `sound`/`fire` events,
not sampled shot-array sums; they remain event-count proxies with a shorter sampled
horizon. An independent raw-demoparser2 build-only check counted through round end:
broky CT **345 gun fires / 47 AWP** versus sparse **341 / 45**; broky T **281 / 20**
versus **273 / 19**; donk CT **704** versus **697**, and donk T **433** versus **431**
(no AWP). These small differences are consistent with events after the last sparse
sample; they are not evidence of per-listener multiplication. The precise cause was
not joined event by event. Method and holdout reports were not rerun or tuned for
equality. Raw provenance is in `data/habit-audit/pipeline-evidence.json`.

Ran:

```bash
python3 tools/habit-audit/fetch_parsed.py --out data/habit-audit
python3 -m unittest discover -s tools/habit-audit -p 'test_audit.py' -v
python3 tools/habit-audit/audit.py --json-dir data/habit-audit/parsed/round_json --games clone-model/games.json --out data/habit-audit/train --split train
python3 tools/habit-audit/audit.py --json-dir data/habit-audit/parsed/round_json --games clone-model/games.json --out data/habit-audit/holdout --split test --method-lock data/habit-audit/method-lock.json
```

Download SHA256 matched the handoff; 11 synthetic tests passed. They cover retained
AWP/knife active, duplicate inventory items, reordered per-file indices, explicit
missing versus empty inventory, death clipping, irregular elapsed intervals, yaw wrap,
nonfinite coordinates, invalid event fields, exact-ID ambiguity rejection, split/excluded
account guards and CLI output. Full source-report JSON/CSV/Markdown and locks stay
outside Git. The companion pipeline correction has its own tests/raw-demo candidate
runs. No live gameplay, purchase aliases, generated identity, combat strength or
player-identical behavior was tested by this audit.
