# Model credits

The five character models in this folder are processed (decimated, rigged where needed,
re-animated with an `Idle` clip, and compressed) from Sketchfab downloads licensed under
CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/). Credit lines as the authors require:

- `01_cs2_blockout.glb`: This work is based on "SAS | CS2 Agent Model Blue" (https://sketchfab.com/3d-models/sas-cs2-agent-model-blue-7f18aaccd0ee4694a36646101a12339e) by 6lucius (https://sketchfab.com/6lucius) licensed under CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)
- `02_smash_blockout.glb`: This work is based on "Mario obj" (https://sketchfab.com/3d-models/mario-obj-c549d24b60f74d8f85c7a5cbd2f55d0f) by MatiasH290 (https://sketchfab.com/matias029) licensed under CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)
- `03_fortnite_blockout.glb`: This work is based on "Jonesy" (https://sketchfab.com/3d-models/jonesy-a115bc7511e34987af20ec0d1be136d3) by MatthewDouglas (https://sketchfab.com/TheTopIsdown) licensed under CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)
- `04_fifa_blockout.glb`: This work is based on "Jett | Valorant" (https://sketchfab.com/3d-models/jett-valorant-f6cc2de8bb9e4881a8af4d481044074d) by ILilMitch (https://sketchfab.com/ILilMitch) licensed under CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)
- `05_halo_blockout.glb`: This work is based on "Halo Combat Eloved Annivarys Master Chief" (https://sketchfab.com/3d-models/halo-combat-eloved-annivarys-master-chief-0eabbf894a7d430ea7282d42dbda1e33) by Diddy_Blud_117 (https://sketchfab.com/marcosacevez57) licensed under CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)

Changes made: decimated (Mario 36.5k→20k tris, Jett 42.9k→20k), re-centred and scaled,
auto-rigged (Mario, Jonesy), new looping `Idle` animation, textures downscaled and KTX2/Meshopt compressed.
Regenerate with `scripts/chargen/process_raw.py` (see its docstring).
