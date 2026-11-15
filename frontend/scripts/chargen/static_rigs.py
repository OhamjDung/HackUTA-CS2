"""Joint tables for the two static Sketchfab meshes (metres, normalised space).

Read off 5 cm-grid ortho renders after process_raw.py normalisation (character faces -Y,
its left is +X; only the left side is listed, the right is mirrored).
"""

RIGS = {
    # Mario (1.65 m, T-pose, oversized head)
    '02_smash': dict(
        torso_x=0.20, hip_y=0.05, hip_z=0.47, spine_z=0.62, chest_y=0.04, chest_z=0.78, neck_y=0.07, neck_z=0.93,
        head_y=0.06, head_z=1.0, top_z=1.6,
        sh=(0.22, 0.06, 0.92), el=(0.41, 0.06, 0.92), wr=(0.57, 0.06, 0.92), hd=(0.80, 0.06, 0.92),
        hp=(0.10, 0.08, 0.43), kn=(0.11, 0.06, 0.25), an=(0.12, 0.10, 0.10), to=(0.12, -0.13, 0.04),
    ),
    # Jonesy (1.84 m, relaxed A-pose)
    '03_fortnite': dict(
        hip_y=0.03, hip_z=0.95, spine_z=1.10, chest_y=0.03, chest_z=1.27, neck_y=0.03, neck_z=1.55,
        head_y=0.0, head_z=1.62, top_z=1.84,
        sh=(0.18, 0.05, 1.46), el=(0.27, 0.06, 1.17), wr=(0.30, -0.02, 0.97), hd=(0.30, -0.05, 0.83),
        hp=(0.09, 0.03, 0.92), kn=(0.10, 0.00, 0.52), an=(0.11, 0.03, 0.10), to=(0.11, -0.11, 0.03),
    ),
}
