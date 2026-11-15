# Character generator

Builds the 5 rigged, animated characters in `public/models/` procedurally with Blender's Python API.

```bash
pip install bpy==5.1.2            # headless Blender (Python 3.13)
python3 build.py                  # all five -> /home/claude/build/*.raw.glb (+ preview PNGs)
python3 build.py smash --close    # one character, close-up previews
```

Then compress each raw export (gltf-transform 4.5 and KTX-Software `ktx` must be on PATH):

```bash
gltf-transform dedup   X.raw.glb t1.glb
gltf-transform prune   t1.glb t2.glb
gltf-transform resample t2.glb t3.glb
gltf-transform etc1s   t3.glb t4.glb --slots "{baseColorTexture,emissiveTexture}"
gltf-transform uastc   t4.glb t5.glb --slots "{metallicRoughnessTexture,normalTexture,occlusionTexture}"
gltf-transform meshopt t5.glb X.glb --level high --quantize-position 16
```

Edit `OUT` in build.py to change the output folder. Characters, palettes, and stances are in `chars.py`.
The rig, IK stance solve, `Idle` bake, and palette material are in `core.py`.
