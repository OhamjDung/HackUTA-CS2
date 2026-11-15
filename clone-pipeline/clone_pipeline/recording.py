"""Write a route segment as a CS2-Bot-Controller recording file (<name>.json.br).

The format is copied from CS2-Bot-Controller's own recorder:
csharp/BotControllerImpl/MotionRecording.cs and csharp/BotControllerApi/Types.cs
(https://github.com/XBribo/CS2-Bot-Controller). A recording is Brotli-compressed JSON with three
lists: Ticks (state before and after each tick), Subticks, and Commands (the input of each tick).

NOT TESTED IN THE GAME. The field layout matches the source. How the game uses each field during
playback is not documented, so these choices are assumptions:
  - Subticks is left empty. A recording made in the game has sub-tick input; a match recording does not.
  - DuckSpeed is set to 8.0, the game's usual value. A match recording does not store it.
  - Commands[].Fields, MouseDx and MouseDy are 0.
  - Buttons1 and Buttons2 (key press counters) are 0.
  - EntityFlags is rebuilt: "on ground" (1) unless the player moves vertically, plus "ducking" (2).
    A match recording does not store this field.
The first test on the game machine is: copy one file to the BotController plugin's "recordings"
folder and run "!replay <slot> <name>" in chat.
"""

import json
from pathlib import Path

import brotli
import pandas as pd

FORMAT_VERSION = 1
TICKRATE = 64
DEFAULT_DUCK_SPEED = 8.0


def _num(value, default: float = 0.0) -> float:
    return default if pd.isna(value) else float(value)


FLAG_ON_GROUND = 1
FLAG_DUCKING = 2


def _entity_flags(row: pd.Series, vertical_speed: float) -> int:
    flags = FLAG_ON_GROUND if abs(vertical_speed) < 1.0 else 0
    if bool(row["ducked"]):
        flags |= FLAG_DUCKING
    return flags


def _snapshot(row: pd.Series, velocity: tuple[float, float, float]) -> dict:
    return {
        "OriginX": _num(row["X"]), "OriginY": _num(row["Y"]), "OriginZ": _num(row["Z"]),
        "VelX": velocity[0], "VelY": velocity[1], "VelZ": velocity[2],
        "Pitch": _num(row["pitch"]), "Yaw": _num(row["yaw"]), "Roll": 0.0,
        "EntityFlags": _entity_flags(row, velocity[2]),
        "MoveType": int(_num(row["move_type"], 2)),
        "Buttons": int(_num(row["buttons"])), "Buttons1": 0, "Buttons2": 0,
        "DuckAmount": _num(row["duck_amount"]), "DuckSpeed": DEFAULT_DUCK_SPEED,
        "LadderNormalX": 0.0, "LadderNormalY": 0.0, "LadderNormalZ": 0.0,
        "Ducked": int(bool(row["ducked"])), "Ducking": int(bool(row["ducking"])),
        "DesiresDuck": int(bool(row["ducked"]) or bool(row["ducking"])),
        "ActualMoveType": int(_num(row["move_type"], 2)),
    }


def _velocity(ticks: pd.DataFrame, i: int) -> tuple[float, float, float]:
    """Recorded velocity, or position change per second where the recording has no velocity."""
    row = ticks.iloc[i]
    if not pd.isna(row["velocity_X"]):
        return (_num(row["velocity_X"]), _num(row["velocity_Y"]), _num(row["velocity_Z"]))
    j = min(i + 1, len(ticks) - 1)
    nxt = ticks.iloc[j]
    return tuple((_num(nxt[axis]) - _num(row[axis])) * TICKRATE for axis in ("X", "Y", "Z"))  # type: ignore[return-value]


def to_recording(ticks: pd.DataFrame) -> dict:
    """Convert the per-tick rows of one segment into the recording structure."""
    if len(ticks) < 2:
        raise ValueError("A recording needs at least 2 ticks.")
    out_ticks, out_commands = [], []
    for i in range(len(ticks) - 1):
        before, after = ticks.iloc[i], ticks.iloc[i + 1]
        weapon = int(_num(before["item_def_idx"]))
        out_ticks.append({
            "Pre": _snapshot(before, _velocity(ticks, i)),
            "Post": _snapshot(after, _velocity(ticks, i + 1)),
            "WeaponDefIndex": weapon, "NumSubtick": 0, "EventFlags": 0, "EventWeaponDefIndex": 0,
            "EventDropVectorFlags": 0,
            "EventDropTargetX": 0.0, "EventDropTargetY": 0.0, "EventDropTargetZ": 0.0,
            "EventDropVelocityX": 0.0, "EventDropVelocityY": 0.0, "EventDropVelocityZ": 0.0,
            "EventDropReleaseX": 0.0, "EventDropReleaseY": 0.0, "EventDropReleaseZ": 0.0,
            "EventDropReleaseQuatX": 0.0, "EventDropReleaseQuatY": 0.0, "EventDropReleaseQuatZ": 0.0,
            "EventDropReleaseQuatW": 1.0,
        })
        forward = float(bool(before["FORWARD"])) - float(bool(before["BACK"]))
        left = float(bool(before["LEFT"])) - float(bool(before["RIGHT"]))
        out_commands.append({
            "ForwardMove": forward, "LeftMove": left, "UpMove": 0.0,
            "Pitch": _num(before["pitch"]), "Yaw": _num(before["yaw"]), "Roll": 0.0,
            "Buttons": int(_num(before["buttons"])), "Buttons1": 0, "Buttons2": 0,
            "MouseDx": 0, "MouseDy": 0, "WeaponSelect": 0, "Fields": 0, "LeftHandDesired": 0,
        })
    return {
        "FormatVersion": FORMAT_VERSION, "Tickrate": TICKRATE,
        "Ticks": out_ticks, "Subticks": [], "Commands": out_commands, "InputHistory": "",
    }


def write_recording(ticks: pd.DataFrame, path: str | Path) -> int:
    """Write one segment to <path>. The path must end in .json.br. Returns the tick count."""
    path = Path(path)
    if not path.name.endswith(".json.br"):
        raise ValueError("CS2-Bot-Controller only loads files named <name>.json.br")
    recording = to_recording(ticks)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(brotli.compress(json.dumps(recording, separators=(",", ":")).encode("utf-8"), quality=9))
    return len(recording["Ticks"])


def read_recording(path: str | Path) -> dict:
    return json.loads(brotli.decompress(Path(path).read_bytes()))
