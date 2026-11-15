"""Authored fictional personas, built on CloneDirector's existing native-bot/quirk controls.

Run from any folder: python make_odyssey_profiles.py. No neural weights, pro routes or voice assets.
Numbers are initial game-design targets; Tom must calibrate the installed bot base in private CS2.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IDS = ("poseidon", "odysseus", "menelaus", "telemachus", "melantho")

DESIGNS = {
    "poseidon": dict(title="The Tempest", difficulty="impossible", trait="Wrathful, implacable sea god; overwhelming pressure rather than deception.",
        skill=100, aggression=100, teamwork=15, reaction=0., delay=0., accel=999999., offset=.01,
        focus=.1, burst=12., single=.02, crouch=.05, jumps=0., quiet=0., memory=1.,
        primary=("ak47", "m4a1"), eco=("deagle", "deagle"), force=("galilar", "famas"),
        utility=["hegrenade", "smokegrenade", "flashbang"], immune=True, damage=1.),
    "odysseus": dict(title="The Strategist", difficulty="superhuman", trait="Patient, resourceful trickster and commander; precise, quiet and adaptable.",
        skill=100, aggression=72, teamwork=95, reaction=.10, delay=.015, accel=44000., offset=.06,
        focus=.8, burst=3., single=.58, crouch=.18, jumps=2., quiet=.85, memory=6.,
        primary=("ak47", "m4a1_silencer"), eco=("deagle", "deagle"), force=("mac10", "mp9"),
        utility=["smokegrenade", "flashbang", "flashbang"], immune=False, damage=1.08),
    "menelaus": dict(title="The Warlord", difficulty="medium", trait="Proud, steadfast veteran and loyal commander; direct rifle fights with dependable support.",
        skill=65, aggression=58, teamwork=85, reaction=.32, delay=.08, accel=12000., offset=.35,
        focus=1.8, burst=5., single=.25, crouch=.50, jumps=.5, quiet=.45, memory=3.,
        primary=("ak47", "m4a1"), eco=("p250", "p250"), force=("galilar", "famas"),
        utility=["flashbang", "hegrenade"], immune=False, damage=1.),
    "telemachus": dict(title="The Heir", difficulty="easy", trait="Earnest young learner seeking confidence; hesitant recognition, enthusiastic overfiring and simple equipment.",
        skill=20, aggression=30, teamwork=65, reaction=.65, delay=.25, accel=5000., offset=.90,
        focus=3., burst=9., single=.08, crouch=.70, jumps=6., quiet=.20, memory=1.,
        primary=("p90", "p90"), eco=("glock", "hkp2000"), force=("mac10", "mp9"),
        utility=["flashbang"], immune=False, damage=1.),
    "melantho": dict(title="The Defiant", difficulty="medium", trait="Defiant and sharp-tongued; confrontational toward intruders and aligned with the suitors.",
        skill=60, aggression=78, teamwork=50, reaction=.34, delay=.09, accel=11000., offset=.40,
        focus=1.9, burst=6., single=.20, crouch=.35, jumps=3., quiet=.35, memory=2.,
        primary=("ak47", "m4a1"), eco=("p250", "p250"), force=("mac10", "mp9"),
        utility=["flashbang", "hegrenade"], immune=False, damage=1.),
}

# The interpretations are ours, not claims that Homer measured Counter-Strike habits.
# Every row points to a real control consumed by the plugin, bot-profile patcher or buy planner.
TRAITS = {
    "poseidon": ["The advancing tide", "The solitary god", "Instant wrath", "The unwavering trident",
        "No hesitation", "Rolling thunder", "Stands above mortals", "No added parkour", "No imposed stealth",
        "Rifle broadside", "A dangerous lean round", "Relentless force buy", "Storm provisions", "Divine aegis"],
    "odysseus": ["The calculated opening", "The allied expedition", "Quick recognition", "The precise archer",
        "Decisive commitment", "Measured taps", "Flexible stance", "Occasional traversal hop", "The quiet ambush",
        "The versatile rifle", "The economical precision shot", "Resourceful close-range force buy", "Veil and distraction", "A mythic edge"],
    "menelaus": ["The direct challenge", "The loyal commander", "A fair reaction window", "The steady veteran",
        "Sets his shot", "Controlled rifle volleys", "The planted shield", "Grounded veteran", "Disciplined approach",
        "The dependable rifle", "The practical sidearm", "The affordable battle line", "Straightforward support", "Armor before ornament"],
    "telemachus": ["The hesitant challenger", "Seeks the company of allies", "Late recognition", "The unsteady first aim",
        "Checks before committing", "The enthusiastic spray", "The nervous crouch", "Restless travel", "Forgets stealth often",
        "The forgiving SMG", "Keeps the starting pistol", "A modest force buy", "One simple utility lesson", "Slowly finds his focus"],
    "melantho": ["Defiant challenge", "Company of the suitors", "A measured response", "A sharp eye",
        "A guarded commitment", "Sharp volleys", "Shifting stance", "A quick step", "Guarded approach",
        "A household rifle", "A spare pistol", "A bold force buy", "Flash of defiance", "Armor before risk"],
}


def make_profile(name):
    d = DESIGNS[name]
    native = {"Skill": str(d["skill"]), "Aggression": str(d["aggression"]), "Teamwork": str(d["teamwork"]),
        "ReactionTime": str(d["reaction"]), "AttackDelay": str(d["delay"]),
        "LookAngleMaxAccelNormal": str(d["accel"]), "LookAngleStiffnessNormal": "300.0", "LookAngleDampingNormal": "35.0",
        "LookAngleMaxAccelAttacking": str(d["accel"]), "LookAngleStiffnessAttacking": "600.0", "LookAngleDampingAttacking": "60.0",
        "AimFocusInitial": str(d["focus"]), "AimFocusDecay": ".2", "AimFocusOffsetScale": str(d["offset"]), "AimfocusInterval": ".25"}
    buys = {}
    for i, side in enumerate(("T", "CT")):
        pistol = "glock" if side == "T" else "hkp2000"
        # At most one primary; main weapon and armor before utility. No free money or free guns.
        buys[side] = {"pistol": {"aliases": [pistol, "vest"]},
            "eco": {"aliases": [d["eco"][i]]}, "force": {"aliases": [d["force"][i], "vest"]},
            "full": {"aliases": [d["primary"][i], "vesthelm"] + d["utility"] + (["defuser"] if side == "CT" else [])}}
    paths = ["odyssey.bot_profile.Aggression", "odyssey.bot_profile.Teamwork", "odyssey.bot_profile.ReactionTime",
        "odyssey.bot_profile.AimFocusOffsetScale", "odyssey.bot_profile.AttackDelay", "quirk_controls.shots_per_burst.value",
        "quirk_controls.crouched_shot_share.value", "quirk_controls.jumps_per_min.value", "game_sense.quiet_walk_share",
        "buy_plan.T.full.aliases", "buy_plan.T.eco.aliases", "buy_plan.T.force.aliases", "buy_plan.CT.full.aliases",
        {"poseidon": "odyssey.invulnerable", "odysseus": "odyssey.damage_multiplier", "menelaus": "buy_plan.T.full.aliases", "melantho": "buy_plan.T.full.aliases",
         "telemachus": "odyssey.bot_profile.AimFocusInitial"}[name]]
    effects = [f"Native aggression {d['aggression']}/100; pressure appetite, not a guaranteed path.",
        f"Native teamwork {d['teamwork']}/100; squad preference when teammates exist.",
        f"Configured reaction {d['reaction']*1000:g} ms, subject to the native AI and server tick.",
        f"Aim offset scale {d['offset']}; finite acceleration cap {d['accel']:g}. Calibration required.",
        f"Configured attack delay {d['delay']*1000:g} ms after the native AI decides to engage.",
        f"Burst target {d['burst']:g} shots, single-shot share {d['single']:.0%}; existing trigger suppression.",
        f"Extra crouch at burst start with probability {d['crouch']:.0%}; native crouching can also occur.",
        f"{d['jumps']:g} extra jumps/min target while running outside combat; zero means no injected jumps.",
        f"{d['quiet']:.0%} walk chance per eligible second near a recent heard step/reload; memory {d['memory']:g}s. Not global enemy awareness.",
        f"Full-buy primary T/CT: {d['primary'][0]}/{d['primary'][1]}; subject to money and alias support.",
        f"Eco sidearm T/CT: {d['eco'][0]}/{d['eco'][1]}; no armor/utility splurge.",
        f"Force primary T/CT: {d['force'][0]}/{d['force'][1]}, then vest; subject to affordability.",
        "Utility buy palette: " + ", ".join(d["utility"]) + ". Native AI chooses deployment; no authored lineups or fakes.",
        {"poseidon": "Block incoming gameplay damage before application, including bullets, grenades, fall and C4. Not a giant health pool.",
         "odysseus": "Multiply outgoing enemy-player damage by 1.08; explicit fantasy advantage, not a learned pro rating.",
         "menelaus": "Primary then vesthelm before utility, both sides; a protected but normally killable veteran.",
         "melantho": "Primary then vesthelm before utility, both sides; normal damage and health.",
         "telemachus": "AimFocusInitial 3.0: deliberately loose initial focus; no live confidence/learning system."}[name]]
    return dict(clone_id=name, display_name=name.title(), source="user", stand_in_bot=name, map="de_mirage",
        model=None, reaction_ms=round(d["reaction"]*1000), aim_skill=d["skill"]/100, aggression=d["aggression"]/100,
        weapons=list(dict.fromkeys(d["primary"])), positions={}, source_games=[], similarity=None,
        authored=True, buy_plan=buys, routes={"T": [], "CT": []}, route_shares={"T": {}, "CT": {}},
        quirk_controls={k: {"value": v} for k, v in {"shots_per_burst": d["burst"], "single_shot_burst_share": d["single"],
            "crouched_shot_share": d["crouch"], "jumps_per_min": d["jumps"], "slow_share": d["quiet"]}.items()},
        game_sense=dict(enemy_close_handoff=False, quiet_walk=d["quiet"]>0, quiet_walk_share=d["quiet"],
            heard_memory_seconds=d["memory"]),
        odyssey=dict(version=1, title=d["title"], difficulty=d["difficulty"], character_basis=d["trait"],
            invulnerable=d["immune"], damage_multiplier=d["damage"], bot_profile=native,
            behavior_source="authored persona + native bot AI; not a neural model or pro recording",
            live_validated=False, voice_owner="Tom; existing ElevenLabs voice mapped by clone_id; no voice IDs embedded",
            quirks=[dict(id=f"{name}_{i+1:02}", name=label, control=control, effect=effect)
                for i, (label, control, effect) in enumerate(zip(TRAITS[name], paths, effects))]))


def build(root=ROOT / "clones"):
    root.mkdir(parents=True, exist_ok=True)
    for name in IDS:
        (root / (name + ".json")).write_text(json.dumps(make_profile(name), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
