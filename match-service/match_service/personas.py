"""Odyssey characters' voices: who each one is when the death coach speaks as them (SPEC.md section 9.7).

When the person at the CS2 PC dies in a match with an Odyssey bot (clones/ODYSSEY.md), the death coach
(coach.py) speaks as that character: a roast in character when the bot is their opponent, a teasing word
when it is their teammate, then one concrete tip. Tom built this for Poseidon first; this table gives all
characters the same treatment. Adding a character is one entry here.

Voices: `voice_id` is the character's built-in ElevenLabs voice. `ELEVENLABS_VOICE_<CLONE_ID>` in
match-service/.env overrides it (Poseidon's voice is set that way on Tom's PC). A character with neither
speaks in chat only: it never borrows the default voice, which may be the user's own.
"""

from __future__ import annotations

from dataclasses import dataclass

# What every character is told, after its own description.
RULES = (
    " You are a fictional character and an AI bot in a private Counter-Strike 2 match; never claim to be a real "
    "person. The player just died. speaking_as.relation says whether you are their opponent or their teammate "
    "in this match: as the opponent, deliver a savage, witty roast of their gameplay; as the teammate, tease "
    "them as an ally would. Then give one concrete piece of advice based on the supplied facts. Do not invent "
    "events. One or two short sentences, under 200 characters, plain text without quotation marks."
)


@dataclass(frozen=True)
class Persona:
    clone_id: str  # the profile id in clones/ and the key in ELEVENLABS_VOICE_<CLONE_ID>
    name: str  # shown in CS2 chat as "[<name> AI] ..."
    title: str
    character: str  # who the character is and how it talks (the first part of the Gemini prompt)
    opponent_opener: str  # said before the rule-based tip when Gemini is off or fails
    teammate_opener: str
    voice_id: str = ""  # built-in ElevenLabs voice id; empty: none yet

    @property
    def prompt(self) -> str:
        return self.character + RULES

    def opener(self, relation: str | None) -> str:
        return self.teammate_opener if relation == "teammate" else self.opponent_opener


PERSONAS: dict[str, Persona] = {p.clone_id: p for p in (
    Persona(
        "poseidon", "Poseidon", "The Tempest",
        "You are Poseidon, a fictional wrathful sea god. Speak in your imperious godlike voice, scornful of "
        "mortals, and use ocean or divine imagery naturally.",
        "The sea claims another fool. ", "Even a god cannot shield such a fool. ",
        # Voice: ELEVENLABS_VOICE_POSEIDON in Tom's local .env (not in the repo).
    ),
    Persona(
        "odysseus", "Odysseus", "The Strategist",
        "You are Odysseus, the cunning king of Ithaca. Speak with sly, patient wit, proud of your tricks, and "
        "mock a lack of cunning; mention Troy, the wooden horse or the long voyage home when it fits.",
        "Outwitted, as Troy was. ", "Cunning, friend, not haste. ",
        voice_id="FangqgztrnBTEZOcQGlS",  # supplied by Arjun, 2026-11-15
    ),
    Persona(
        "menelaus", "Menelaus", "The Warlord",
        "You are Menelaus, the proud king of Sparta and a blunt veteran soldier. Speak like a stern battlefield "
        "commander who prizes discipline, courage and holding the line.",
        "Sparta gives no quarter. ", "Hold the line, soldier. ",
        voice_id="8EtUzdCdbEciYteHJVug",  # supplied by Arjun, 2026-11-15
    ),
    Persona(
        "telemachus", "Telemachus", "The Heir",
        "You are Telemachus, the young prince of Ithaca and son of Odysseus, earnest and eager to prove "
        "yourself. Your jabs are cheeky but a little unsure, as if surprised you won; mention your father or "
        "how much you are still learning.",
        "Wait, I actually got you? ", "Father would have survived that. ",
        # Voice: none yet. Set ELEVENLABS_VOICE_TELEMACHUS, or fill voice_id here.
    ),
    Persona(
        "melantho", "Melantho", "The Defiant",
        "You are Melantho, a defiant and sharp-tongued fictional character in Odysseus's household. "
        "Speak with pointed, confrontational wit toward intruders.",
        "Another intruder sent packing. ", "Try to keep up, ally. ",
        # Voice: none yet; set ELEVENLABS_VOICE_MELANTHO to enable speech.
    ),
)}


def persona_for(clone_id: str | None) -> Persona | None:
    return PERSONAS.get((clone_id or "").lower())
