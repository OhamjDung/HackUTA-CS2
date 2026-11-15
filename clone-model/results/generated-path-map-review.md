# Generated-path map review: development cases

**Automated geometry check only; a person must still review paths before use.** A pass here is
not an approval. Both identities failed their held-out test (SPEC 8.6), so no path below is the
player's learned style.

## What ran (2026-11-14, CPU, macOS arm64)

- `clone-model/map_review.py` on `Generated-path-review-dev.json` (`cs2.clone.review.v1`, sha256
  `f247ddd81f86300d4366746f4fa0d41edcc86003c5125bc0f2df3d730adf5e8c`): 8 development cases,
  4 traces each (actual, own, other, base), 16 points of 0.25 s plus the start position.
- Mesh: CS-NET `maps/optimized_obj_files/de_mirage.obj` at
  `268dd2193c8a3d6e330c07dde5a851196c94eeaa` (sha256 `01ec905a2ded45df1c66652e93ccbaa295b44fe5578642081f4d813a22a4dbbf`,
  823,214 triangles).
- Python 3.11 venv with open3d 0.20.0, numpy 2.4.6, matplotlib and pytest from PyPI.
- Ray casting follows CS-NET's `map_loader.py` (Open3D `RaycastingScene`, OBJ scale 0.0254, axis
  mapping from `config.py`, eye height 64).
- Outputs (git-ignored): `data/map-review/Generated-path-review-dev.check.json`,
  `.check-details.json` and `.case-0.png` … `.case-7.png`.
- Held-out matches 2393242 and 2393024 were not used. The checker rejects a file that contains them.

## Checks and thresholds

Step i goes from the point at t=0.25·i (step 0 starts at `start_position`) to t=0.25·(i+1).

| Check | Rule | Fails? |
|---|---|---|
| Wall crossing | Segment ray between consecutive points blocked at both 36 and 64 units above the feet (0.5-unit tolerance) | Yes |
| Low obstacle | Blocked at 20 or 36 but not a wall, with both end points within 18 units of a floor (no jump or fall) | Yes |
| Floor support | Down ray from 24 above the feet: miss = outside the map or inside solid; surface more than 18 above the feet = below floor; gap over 72 = floating unless the path drops 8+ units into or out of that point (falling) | Yes |
| Buried / headroom | Up ray from 1 above the feet hits an upward-facing surface 18–64 above (below a floor), or a downward-facing surface 18–32 above (no room even crouched; crouch hull is 54) | Yes |
| Speed | Horizontal move over 80 units per step (320 u/s, `sv_maxspeed`) | Yes |
| Long stop | 8 or more steps (2 s) with under 4 units per step | Report only |
| Native early stop | `end_stopped_at` not -1 / null | Report only |

Calibration on the 8 real (`actual`) paths, 136 points and 128 steps: **all pass.** Near limits:
0 steps above 62.5 units (250 u/s; max 60.4 per step); 6 points more than 36 units above the floor
(jumps; max 52.3, limit 72); 8 points with a surface above the feet (stairs; max 8.3, limit 18);
lowest ceiling above 18 units is 38.0 (limit 32); 1 step (case 2, step 11, t=3.0 s) blocked at
36 units while the player was airborne, which the airborne exception passes.

Sanity runs on the real mesh (scratch script, not committed): 32 straight constant-height 55-unit
step paths from four case starts in eight directions all fail; each real path moved up 150 units
fails (8/8), and moved down 30 units fails (8/8).

## Results

| Case | Player | Match | Round | Actual | Own | Other | Base | Notes |
|---|---|---|---|---|---|---|---|---|
| 0 | donk | 2393237 | 4 | pass | pass | pass | pass | Own/other/base stand still for 4 s |
| 1 | donk | 2393237 | 7 | pass | pass | pass | pass | Generated paths run straight along a wall edge |
| 2 | donk | 2393237 | 10 | pass | pass | pass | pass | Generated paths zigzag on stairs; real path jumps |
| 3 | donk | 2393237 | 15 | pass | pass | pass | pass | Own/other/base stand still for 4 s |
| 4 | broky | 2392601 | 1 | pass | pass | pass | pass | Own/other/base move once, then stop 3.75 s |
| 5 | broky | 2392601 | 2 | pass | pass | pass | pass | All stand still on a raised box (real: 3.5 s) |
| 6 | broky | 2392601 | 4 | pass | pass | pass | pass | Generated paths pass through a doorway |
| 7 | broky | 2392601 | 5 | pass | pass | pass | pass | All four stand still for 4 s |

No trace fails. No native early stop occurred (all 16 steps present). Long stops are reported for
17 traces: 15 generated ones (cases 0, 3, 4, 5, 7) and the real paths of cases 5 and 7.

What the figures show (read by eye): in cases 0, 3, 5 and 7 the three generated traces are a dot
at the start. In case 1 they go straight south-southwest to about (-180, -2320), past the
corner of a raised floor edge, while the real player curves west. In case 2 they swing back and
forth across a staircase and end near its foot, while the real player walks out and back. In case 4 they
make one short step and stop, while the real player walks about 260 units south. In case 6 they go west through a
doorway between two wall pieces, while the real player loops north and back south. Own, other and
base overlap almost exactly in every case.

So the generated paths pass mainly because they barely move: 15 of 24 have a long stop. Passing
says nothing about whether a stop is reasonable (SPEC 8.5 step 4 asks a person to reject paths
that stop for no reason).

## Limits

- The body is a set of rays along the path's centre line at 20, 36 and 64 units. The real collision
  hull is 32 units wide (72 standing, 54 crouched), so a path that clips a corner by less than 16
  units, or squeezes through a gap narrower than the hull, is not caught.
- Positions are sampled every 0.25 s and joined with straight lines. A real jump arc between
  samples can cut through a low obstacle; the airborne exception passes such steps. A fast move
  that crosses a thin wall and comes back within one step is not seen.
- The mesh is CS-NET's simplified visual mesh, not CS2's collision or player-clip geometry.
  Stairs are visual steps (real feet sit up to 8 units below a tread); clip brushes and
  invisible walls are missing. A point sunk less than 18 units into a slab is tolerated.
- Thresholds were set on only 8 real paths (largest real height change per step 49 units, largest
  move 60 units). Ladders, long drops and bunny hops were not in the sample, so a real path of that
  kind may fail.
- Only geometry and speed are checked. Visibility, timing, view angles and enemy positions are not.
- Not checked in CS2.

Tests: `clone-model/tests/test_map_review.py`, 12 tests on a synthetic floor-and-wall mesh and on
malformed files; they skip the 5 mesh tests if Open3D is missing.
