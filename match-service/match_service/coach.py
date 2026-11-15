"""Death coach: when the person at the CS2 PC dies, say one short piece of advice in CS2 chat and
speak it in the user's own voice (SPEC.md section 9.7).

How it works:
1. CloneDirector saves the last 10 seconds before a human death as a file in PUZZLE_DEATH_DIR
   (PuzzleMode.cs). The coach watches that folder.
2. feedback.py finds the rule-based mistakes in the window. A compact summary of the death plus those
   findings goes to Gemini, which writes one or two sentences. Without a Gemini key, or when Gemini
   fails or is slow, the top rule finding is used instead, so the player always gets something.
3. The text goes to CS2 chat as `say [Coach] ...` (through MatchBridge when available, so it runs on
   the server console), and to ElevenLabs, whose streamed PCM audio plays on this PC's speakers.

Keys come from the environment or from match-service/.env (git-ignored): GEMINI_API_KEY,
ELEVENLABS_API_KEY, one voice per player as ELEVENLABS_VOICE_<PLAYER> (ELEVENLABS_VOICE_DONK,
ELEVENLABS_VOICE_BROKY), and optionally ELEVENLABS_VOICE_ID as the voice for anyone else. The voice is the
player whose clone is in your match: a clone on your team first, else the one you play against
(`speaker_for`). A missing key turns that part off; nothing else changes.
When the speaker is an Odyssey character (Poseidon, Odysseus, Menelaus, Telemachus), it speaks in character
with that character's own voice: personas.py.
No Server API endpoint or message changes; the /coach routes are additions.

Written from zero on the documented REST APIs (no SDK), so the only new dependency is the optional
`sounddevice` for playback. Gemini and ElevenLabs calls were written from their docs and tested here
against fakes only.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import httpx

from .feedback import GRENADES, _at, _hero, death_time, feedback_for
from .personas import PERSONAS, Persona, persona_for

log = logging.getLogger("match_service.coach")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice}/stream"
SAMPLE_RATE = 24000  # ElevenLabs output_format pcm_24000: 16-bit little-endian mono
CHAT_PREFIX = "[Coach] "  # chat_lines(text, speaker) uses "[donk AI] " when a player speaks
VOICE_PREFIX = "ELEVENLABS_VOICE_"
# Clone id -> the real player it copies: donk_v1, donk_v2, donkL, donkL2, donkLF -> donk.
_CLONE_SUFFIX = re.compile(r"(_v\d+|L\d*F?)$")
CHAT_LINE = 120  # characters per chat line; CS2 cuts long chat messages
CHAT_LINES = 2
MAX_ADVICE = 220  # characters; about 10 seconds of speech

SYSTEM_PROMPT = (
    "You are a Counter-Strike 2 coach. The player just died in a private practice match against bots. "
    "You get a JSON summary of the last seconds before the death and the mistakes a rule checker found. "
    "Reply with one or two short sentences of advice spoken directly to the player (\"you\"), under 200 "
    "characters in total. Name the single most useful fix, and use the facts given (killer, weapon, "
    "utility, teammates). Plain text only: no markdown, no lists, no emojis, no quotation marks. "
    "Do not invent facts that are not in the summary. If the summary has speaking_as, you are the AI clone "
    "of that pro player, the player's teammate or opponent in this match as stated: talk like a teammate on "
    "comms (teammate) or as the opponent who just watched them (opponent), but never claim to be the real person."
)
TRASH_TALK_PROMPT = (
    "You are an AI opponent in a private Counter-Strike 2 practice match. The player opted in to trash talk. "
    "Roast their gameplay brutally and creatively in one or two short sentences, grounded in the supplied death "
    "facts. Keep it about their in-game decisions and skill; do not invent events or claim to be a real person. "
    "Plain text only, no lists or quotation marks, under 200 characters."
)
# The Odyssey characters' prompts (Poseidon's first, by Tom) are in personas.py.

# Other names the keys are often saved under; the first one set is used.
ALIASES = {
    "GEMINI_API_KEY": ("GOOGLE_API_KEY", "GEMINI_KEY", "GOOGLE_GENAI_API_KEY"),
    "ELEVENLABS_API_KEY": ("ELEVEN_LABS_API_KEY", "ELEVENLABS_KEY", "ELEVEN_API_KEY", "XI_API_KEY"),
}

# Anything that could end a console command or break the quoted argument is removed.
_UNSAFE_CHARS = re.compile(r'[;"\r\n\0\x00-\x1f\x7f]')


def read_env_file(path: Path) -> dict[str, str]:
    """KEY=value lines from a .env file (comments and blank lines skipped). Missing file: {}."""
    out: dict[str, str] = {}
    try:
        raw = path.read_bytes()
    except OSError:
        return out
    # Notepad and PowerShell's `>` can save UTF-16 or UTF-8 with a BOM.
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16", errors="replace")
    else:
        text = raw.decode("utf-8-sig", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key] = value
    return out


def clean_text(text: str, limit: int = MAX_ADVICE) -> str:
    """One plain line: no markdown, no characters that could break a console command, at most `limit`."""
    text = re.sub(r"[*_`#>]+", "", text)
    text = _UNSAFE_CHARS.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:-")
        text = cut + "..."
    return text


def player_of(clone_id: str | None) -> str | None:
    """The real player a clone copies, lower case: donkL2 -> donk, broky_v1 -> broky."""
    if not clone_id:
        return None
    return _CLONE_SUFFIX.sub("", clone_id).lower() or None


def chat_lines(text: str, speaker: str | None = None) -> list[str]:
    """Split advice into at most CHAT_LINES `say` commands of at most CHAT_LINE characters each."""
    prefix = f"[{clean_text(speaker, 20)} AI] " if speaker else CHAT_PREFIX
    words, lines, cur = clean_text(text).split(), [], ""
    width = CHAT_LINE - len(prefix)
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w[:width]
    if cur:
        lines.append(cur)
    if len(lines) > CHAT_LINES:
        lines = lines[:CHAT_LINES]
        lines[-1] = lines[-1][: width - 3].rstrip() + "..."
    return [f"say {prefix}{line}" for line in lines]


def death_summary(puzzle: dict, findings: list[dict]) -> dict:
    """The facts Gemini sees: who killed the player, with what, what they carried and did, who was near."""
    hero = _hero(puzzle) or {}
    t_death = death_time(puzzle, hero) if hero else None
    start = hero.get("start") or {}
    killer = next((e for e in puzzle.get("events", [])
                   if e.get("type") == "kill" and e.get("victim") == hero.get("name")), None)
    carried = sorted(w for w in start.get("weapons", []) if w in GRENADES)
    thrown = sorted({e.get("weapon") for e in puzzle.get("events", [])
                     if e.get("type") == "throw" and e.get("attacker") == hero.get("name")} - {None})
    near: dict = {}
    if t_death is not None and (h := _at(hero.get("track") or [], t_death)):
        for p in puzzle.get("players", []):
            if p is hero or not (s := _at(p.get("track") or [], t_death - 0.01)) or s.get("hp", 0) <= 0:
                continue
            d = math.dist((h["x"], h["y"]), (s["x"], s["y"]))
            group = "teammates" if p.get("side") == hero.get("side") else "enemies"
            near.setdefault(group, []).append({"name": p.get("name"), "distance": round(d)})
        for group in near.values():
            group.sort(key=lambda x: x["distance"])
    # The weapon in hand just before the death (the sample at the death itself is often empty).
    held = [s for s in hero.get("track") or [] if s.get("weapon") and (t_death is None or s["t"] <= t_death)]
    last = held[-1] if held else None
    return {
        "map": puzzle.get("map"),
        "player": {"name": hero.get("name"), "side": hero.get("side"),
                   "start_health": start.get("health"), "start_money": start.get("money"),
                   "weapons": start.get("weapons", []), "weapon_at_death": (last or {}).get("weapon")},
        "killed_by": {"name": killer.get("attacker"), "weapon": killer.get("weapon")} if killer else None,
        "kills_before_death": sum(1 for e in puzzle.get("events", []) if e.get("type") == "kill"
                                  and e.get("attacker") == hero.get("name")
                                  and (t_death is None or e.get("t", 0) <= t_death)),
        "utility_carried": carried,
        "utility_thrown": thrown,
        "alive_near_at_death_units": near,
        "rule_findings": [{"title": f["title"], "detail": f["detail"]} for f in findings],
    }


def fallback_advice(findings: list[dict]) -> str:
    if not findings:
        return "Tough one. Check where the shot came from and play that angle with a teammate next time."
    return findings[0]["detail"]


class AudioSink(Protocol):
    async def play(self, chunks) -> None: ...


class SpeakerSink:
    """Plays 16-bit mono PCM chunks on this PC's default output as they arrive (needs `sounddevice`)."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    async def play(self, chunks) -> None:
        try:
            import sounddevice as sd  # optional: PortAudio may be missing on a server
        except (ImportError, OSError) as exc:
            log.warning("no audio playback (%s); install sounddevice", exc)
            async for _ in chunks:
                pass
            return
        stream = sd.RawOutputStream(samplerate=self.sample_rate, channels=1, dtype="int16")
        stream.start()
        rest = b""
        try:
            async for chunk in chunks:
                data = rest + chunk
                even = len(data) - len(data) % 2  # never split a 16-bit sample
                rest = data[even:]
                if even:
                    await asyncio.to_thread(stream.write, data[:even])
        finally:
            await asyncio.to_thread(stream.stop)
            stream.close()


@dataclass
class CoachSettings:
    enabled: bool = True
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_thinking: str = "MINIMAL"  # thinkingConfig.thinkingLevel; empty: leave the field out
    gemini_timeout: float = 4.0
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""  # voice for a player with no voice of their own; empty: stay quiet
    voices: dict[str, str] = field(default_factory=dict)  # player (lower case) -> ElevenLabs voice id
    elevenlabs_model: str = "eleven_flash_v2_5"
    voice: bool = True  # speak the advice (needs both ElevenLabs values)
    chat: bool = True  # send the advice to CS2 chat
    poll_seconds: float = 1.0
    max_age_seconds: float = 30.0  # skip a death file older than this when it is first seen

    @classmethod
    def from_env(cls, env: dict[str, str], env_file: Path | list[Path] | None = None) -> "CoachSettings":
        """Settings from the environment, then the .env files in order (the first file that has a name wins).

        Other common spellings of the key names are accepted (ALIASES)."""
        files = [env_file] if isinstance(env_file, Path) else (env_file or [])
        values: dict[str, str] = {}
        for f in reversed(files):
            values.update({k: v for k, v in read_env_file(f).items() if v})
        values.update({k: v for k, v in env.items() if v})
        for name, others in ALIASES.items():
            if not values.get(name):
                values[name] = next((values[o] for o in others if values.get(o)), "")

        def flag(name: str, default: bool) -> bool:
            return values.get(name, "on" if default else "off").strip().lower() not in ("0", "off", "false", "no")

        return cls(
            enabled=flag("COACH", cls.enabled),
            gemini_api_key=values.get("GEMINI_API_KEY", ""),
            gemini_model=values.get("GEMINI_MODEL") or cls.gemini_model,
            gemini_thinking=values.get("GEMINI_THINKING", cls.gemini_thinking),
            gemini_timeout=float(values.get("GEMINI_TIMEOUT", cls.gemini_timeout)),
            elevenlabs_api_key=values.get("ELEVENLABS_API_KEY", ""),
            elevenlabs_voice_id=values.get("ELEVENLABS_VOICE_ID", ""),
            voices={k[len(VOICE_PREFIX):].lower(): v for k, v in values.items()
                    if k.startswith(VOICE_PREFIX) and k != "ELEVENLABS_VOICE_ID" and v
                    and k[len(VOICE_PREFIX):].lower() != "id"},
            elevenlabs_model=values.get("ELEVENLABS_MODEL") or cls.elevenlabs_model,
            voice=flag("COACH_VOICE", cls.voice),
            chat=flag("COACH_CHAT", cls.chat),
        )

    def all_voices(self) -> dict[str, str]:
        """Every known voice: the Odyssey characters' built-in voices, overridden by ELEVENLABS_VOICE_<NAME>."""
        return {**{p.clone_id: p.voice_id for p in PERSONAS.values() if p.voice_id}, **self.voices}

    def voice_for(self, player: str | None) -> str | None:
        """The ElevenLabs voice for this player, else the default voice, else None.

        An Odyssey character never takes the default voice (it may be the user's own): no voice, no speech."""
        own = self.all_voices().get(player or "")
        if own or persona_for(player):
            return own or None
        return self.elevenlabs_voice_id or None

    def can_speak(self) -> bool:
        return self.voice and bool(self.elevenlabs_api_key and (self.elevenlabs_voice_id or self.all_voices()))


Say = Callable[[list[str]], Awaitable[None]]
# The current match, for picking the voice: {"human_team": "CT"|"T"|None, "clones": [{"clone_id", "team"}]}.
MatchContext = Callable[[], "dict | None"]


def speaker_for(puzzle: dict, match: dict | None, voices: dict[str, str]) -> dict | None:
    """Whose voice gives the advice: {"player", "clone_id", "relation"} or None.

    From the current match: a clone on the person's team first (the teammate talks to you), else a clone on
    the other team. Without a match record, the death file's player names are tried (CloneDirector names a
    clone's bot after its clone id), teammates first. Among several, a player with their own voice wins.
    """
    def pick(cands: list[tuple[str, str]]) -> dict | None:
        cands = [(cid, rel) for cid, rel in cands if player_of(cid)]
        for cid, rel in sorted(cands, key=lambda c: (c[1] != "teammate", player_of(c[0]) not in voices)):
            return {"player": player_of(cid), "clone_id": cid, "relation": rel}
        return None

    if match and match.get("clones"):
        human = match.get("human_team")
        return pick([(c["clone_id"], "teammate" if human and c["team"] == human else "opponent")
                     for c in match["clones"]])
    hero = _hero(puzzle) or {}
    cands = [(p.get("name"), "teammate" if p.get("side") == hero.get("side") else "opponent")
             for p in puzzle.get("players", []) if p is not hero
             and (player_of(p.get("name")) in voices or persona_for(p.get("name")))]
    return pick(cands)


class Coach:
    def __init__(self, settings: CoachSettings, death_dir: Path, http: Callable[[], httpx.AsyncClient],
                 say: Say | None, sink: AudioSink | None = None, match: MatchContext | None = None):
        self.s = settings
        self.death_dir = death_dir
        self.http = http
        self.say = say
        self.sink = sink or SpeakerSink()
        self.match = match or (lambda: None)
        self.seen: set[str] = set()
        self.last: dict | None = None  # the most recent coaching, for GET /coach
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None

    # --- watching for deaths ---------------------------------------------------------------------

    def start(self) -> None:
        if not self.s.enabled:
            return
        self.seen = {p.name for p in self._files()}  # deaths from before the service started are old
        log.info("coach on: watching %s (exists: %s); gemini %s (%s); voices %s; default voice %s; chat %s",
                 self.death_dir, self.death_dir.is_dir(), "on" if self.s.gemini_api_key else "OFF, no key",
                 self.s.gemini_model, sorted(self.s.all_voices()) or "none",
                 "set" if self.s.elevenlabs_voice_id else "none",
                 "on" if self.s.chat and self.say else "off")
        if self.s.voice and not self.s.elevenlabs_api_key:
            log.warning("coach voice OFF: no ELEVENLABS_API_KEY")
        self._task = asyncio.create_task(self._watch())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def _files(self) -> list[Path]:
        if not self.death_dir.is_dir():
            return []
        return sorted(self.death_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)

    async def check_once(self) -> list[dict]:
        """Coach every death file that appeared since the last check (newest last). Returns the results."""
        results = []
        for path in self._files():
            if path.name in self.seen:
                continue
            self.seen.add(path.name)
            if time.time() - path.stat().st_mtime > self.s.max_age_seconds:
                log.info("coach: skipping old death file %s", path.name)
                continue
            log.info("coach: new death file %s", path.name)
            try:
                puzzle = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("could not read death %s: %s", path.name, exc)
                continue
            results.append(await self.coach(puzzle))
        return results

    async def _watch(self) -> None:
        while True:
            try:
                await self.check_once()
            except Exception:  # never let the watcher die
                log.exception("coach watcher error")
            await asyncio.sleep(self.s.poll_seconds)

    # --- one death -------------------------------------------------------------------------------

    async def coach(self, puzzle: dict) -> dict:
        """Advice for one death window: write it, send it to chat, speak it. Returns what happened."""
        async with self._lock:
            findings = feedback_for(puzzle)
            summary = death_summary(puzzle, findings)
            match = self.match()
            trash_talk = bool(match and match.get("coach_style") == "trash_talk")
            speaker = speaker_for(puzzle, match, self.s.all_voices())
            if speaker:
                summary["speaking_as"] = speaker
            source, text = "rules", fallback_advice(findings)
            # An Odyssey character always speaks in character, whatever the trash-talk setting (personas.py).
            persona = persona_for(speaker["player"]) if speaker else None
            if persona:
                text = persona.opener(speaker["relation"]) + text
            elif trash_talk:
                text = "Nice try. " + text
            if self.s.gemini_api_key:
                try:
                    t0 = time.monotonic()
                    if written := await self.ask_gemini(summary, trash_talk=trash_talk, persona=persona):
                        source, text = "gemini", written
                    log.info("coach: Gemini answered in %.1f s", time.monotonic() - t0)
                except (httpx.HTTPError, asyncio.TimeoutError, ValueError, KeyError) as exc:
                    log.warning("coach: Gemini failed (%s), using the rule feedback: %r", self.s.gemini_model, exc)
            text = clean_text(text)
            player = speaker["player"] if speaker else None
            voice_id = self.s.voice_for(player)
            result = {"death_id": puzzle.get("id"), "source": source, "text": text, "speaker": speaker,
                      "character": persona.name if persona else None,
                      "voice_id": voice_id, "chat": False, "voice": False, "errors": []}
            jobs = []
            if self.s.chat and self.say:
                jobs.append(self._chat(text, persona.name if persona else player, result))
            if self.s.voice and self.s.elevenlabs_api_key and voice_id:
                jobs.append(self._speak(text, voice_id, result))
            started = time.monotonic()
            await asyncio.gather(*jobs)
            self.last = result
            log.info("coach: death %s, advice from %s, speaker %s, voice id %s, chat %s, voice %s, %.1f s: %s%s",
                     result["death_id"], source, player or "none", voice_id or "none",
                     "sent" if result["chat"] else "not sent", "played" if result["voice"] else "not played",
                     time.monotonic() - started, text, f" | errors: {result['errors']}" if result["errors"] else "")
            return result

    async def ask_gemini(self, summary: dict, trash_talk: bool = False, persona: Persona | None = None) -> str:
        prompt = persona.prompt if persona else TRASH_TALK_PROMPT if trash_talk else SYSTEM_PROMPT
        body: dict = {
            "systemInstruction": {"parts": [{"text": prompt}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps(summary, separators=(",", ":"))}]}],
            "generationConfig": {"maxOutputTokens": 200},
        }
        if self.s.gemini_thinking:
            body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": self.s.gemini_thinking}
        r = await asyncio.wait_for(self.http().post(
            GEMINI_URL.format(model=self.s.gemini_model), json=body,
            headers={"x-goog-api-key": self.s.gemini_api_key}), self.s.gemini_timeout)
        if r.status_code != 200:
            raise ValueError(f"Gemini answered {r.status_code}: {r.text[:300]}")
        parts = r.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()

    async def _chat(self, text: str, player: str | None, result: dict) -> None:
        try:
            await self.say(chat_lines(text, player))
            result["chat"] = True
        except Exception as exc:  # the console may be gone; the voice can still play
            result["errors"].append(f"chat: {exc}")
            log.warning("could not send coach chat: %s", exc)

    async def _speak(self, text: str, voice_id: str, result: dict) -> None:
        url = ELEVEN_URL.format(voice=voice_id)
        try:
            async with self.http().stream(
                    "POST", url, params={"output_format": f"pcm_{SAMPLE_RATE}"},
                    headers={"xi-api-key": self.s.elevenlabs_api_key},
                    json={"text": text, "model_id": self.s.elevenlabs_model},
                    timeout=httpx.Timeout(10.0, read=15.0)) as r:
                if r.status_code != 200:
                    raise ValueError(f"ElevenLabs answered {r.status_code}: {(await r.aread())[:300]!r}")
                await self.sink.play(r.aiter_bytes())
            result["voice"] = True
        except Exception as exc:
            result["errors"].append(f"voice: {exc}")
            log.warning("could not speak coach advice: %s", exc)

    def status(self) -> dict:
        return {"enabled": self.s.enabled, "gemini": bool(self.s.gemini_api_key), "model": self.s.gemini_model,
                "voice": self.s.can_speak(), "voices": sorted(self.s.all_voices()),
                # Each Odyssey character and whether it has a voice yet (personas.py, ELEVENLABS_VOICE_<ID>).
                "characters": {p.clone_id: {"name": p.name, "voice": bool(self.s.voice_for(p.clone_id))}
                               for p in PERSONAS.values()},
                "default_voice": bool(self.s.elevenlabs_voice_id), "match": self.match(), "chat": self.s.chat and self.say is not None,
                "death_dir": str(self.death_dir), "last": self.last}
