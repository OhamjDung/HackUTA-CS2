"use client";

import Image, { type StaticImageData } from "next/image";
import { useEffect, useState } from "react";
import dust2 from "@/components/img/dust2.jpeg";
import inferno from "@/components/img/inferno.webp";
import mirage from "@/components/img/De_mirage_cs2.webp";
import { API_URL } from "@/lib/puzzles";

type Clone = { clone_id: string; display_name: string; label?: string; playable?: boolean; reason?: string | null };
type Match = { match_id: string; status: string; round: number; score: { CT: number; T: number }; players: { display_name: string; team: string; is_clone: boolean }[]; error?: string; join_link?: string };
type TracePlayer = { name: string; team: string; clone_id?: string; path: number[][]; died_at?: number | null };
type Trace = { source: string; live_round: number | null; rounds: { round: number; players: TracePlayer[] }[] };
type Event = { event: string; sent_at: string; data: unknown };
type Summary = { match_id: string; status: string; players: string[] };
async function api<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, body === undefined ? undefined : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(Array.isArray(data?.detail) ? data.detail.map((x: { msg?: string } | string) => typeof x === "string" ? x : x.msg).join(", ") : data?.detail || res.statusText);
  return data as T;
}
const button = "rounded-full bg-white px-5 py-3 font-bold text-black disabled:opacity-40";

/** Maps the service accepts. A map without `image` falls back to a warm gradient card. */
const MAPS: { id: string; name: string; image?: StaticImageData }[] = [
  { id: "de_mirage", name: "Mirage", image: mirage },
  { id: "de_dust2", name: "Dust II", image: dust2 },
  { id: "de_inferno", name: "Inferno", image: inferno },
];
const MODES: { id: string; name: string; rounds: number }[] = [
  { id: "wingman", name: "Wingman", rounds: 9 },
  { id: "competitive", name: "Competitive", rounds: 13 },
];
/** Shown while the match service is offline, so the layout still reads (Start stays disabled). */
const PLACEHOLDER_CLONES: Clone[] = [{ clone_id: "broky_v1", display_name: "broky" }, { clone_id: "donk_v1", display_name: "donk" }];
/** Portrait for a clone from its player name (donkL, donk_v2, broky_v1 ... all map to the player photo). */
function photoFor(c?: Clone): string | undefined {
  const name = `${c?.display_name ?? ""} ${c?.clone_id ?? ""}`.toLowerCase();
  if (name.includes("donk")) return "/images/bots/donk.webp";
  if (name.includes("broky")) return "/images/bots/broky.webp";
  return undefined;
}
const cloneName = (c?: Clone) => c?.display_name || c?.clone_id || "Choose a bot";
const card = "rounded-2xl border border-white/[0.14] bg-[#131316]";
const step = (n: string, title: string) => <h2 className="flex items-baseline gap-2 text-[22px] font-extrabold tracking-[-0.02em]"><span className="text-[#e4002b]">{n}</span><span className="text-[#e4002b]/70">/</span>{title}</h2>;
const selectBox = "w-full appearance-none rounded-lg border border-white/[0.18] bg-[#16161a] px-5 py-3 pr-12 text-[16px] text-white outline-none transition focus:border-[#e4002b]";
/** Chevron for the custom selects (inline: Tailwind cannot build this data URL as a class). */
const chevron: React.CSSProperties = { backgroundImage: "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8'><path d='M1 1l5 5 5-5' fill='none' stroke='white' stroke-width='1.8'/></svg>\")", backgroundRepeat: "no-repeat", backgroundPosition: "right 18px center", backgroundSize: "12px 8px" };

export default function MatchControls() {
  const [kind, setKind] = useState<"watch" | "play">("watch");
  const [clones, setClones] = useState<Clone[]>([]);
  const [catalogueLoaded, setCatalogueLoaded] = useState(false);
  const [matches, setMatches] = useState<Summary[]>([]);
  const [ct, setCt] = useState(""); const [t, setT] = useState("");
  const [side, setSide] = useState("CT"); const [steam, setSteam] = useState("");
  const [enemies, setEnemies] = useState<string[]>([]); const [mates, setMates] = useState<string[]>([]);
  const [map, setMap] = useState("de_mirage"); const [mode, setMode] = useState("wingman");
  const [id, setId] = useState(""); const [match, setMatch] = useState<Match | null>(null); const [events, setEvents] = useState<Event[]>([]);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const [watchPick, setWatchPick] = useState("");
  useEffect(() => {
    api<Clone[]>("/clones").then(all => {
      const available = all.filter(c => c.playable !== false); setClones(all); setCatalogueLoaded(true);
      setCt(available.find(c => c.clone_id === "broky_v1")?.clone_id ?? available[0]?.clone_id ?? "");
      const enemy = available.find(c => c.clone_id === "donk_v1")?.clone_id ?? available[1]?.clone_id ?? available[0]?.clone_id ?? "";
      setT(enemy); setEnemies(enemy ? [enemy] : []);
    }).catch(e => setError(`Match service unavailable: ${e.message}`));
    api<Summary[]>("/matches").then(setMatches).catch(() => {});
    const initial = new URLSearchParams(window.location.search).get("match"); if (initial) setId(initial);
  }, []);
  useEffect(() => {
    if (!id) return;
    let active = true; let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const [m, e, tr] = await Promise.all([api<Match>(`/matches/${encodeURIComponent(id)}`), api<Event[]>(`/matches/${encodeURIComponent(id)}/events`), api<Trace>(`/matches/${encodeURIComponent(id)}/trace`).catch(() => null)]);
        if (!active) return; setMatch(m); setEvents(e); setTrace(tr); setError("");
        if (m.status !== "ended" && m.status !== "failed") timer = setTimeout(tick, 500);
      } catch (e) { if (active) { setError((e as Error).message); timer = setTimeout(tick, 2000); } }
    };
    void tick(); return () => { active = false; clearTimeout(timer); };
  }, [id]);
  function attach(next: string) { setMatch(null); setEvents([]); setTrace(null); setId(next); const url = new URL(window.location.href); url.searchParams.set("match", next); history.replaceState(null, "", url); }
  async function start() {
    setError("");
    if (kind === "watch" && ct === t) { setError("Choose a different clone for each side."); return; }
    if (kind === "play" && !/^7656119\d{10}$/.test(steam.trim())) { setError("Enter your 17-digit Steam ID."); return; }
    if (kind === "play" && !enemies.length) { setError("Choose at least one opponent."); return; }
    setBusy(true);
    try {
      const body = kind === "watch" ? { map, mode, players: [], clones: [{ clone_id: ct, team: "CT" }, { clone_id: t, team: "T" }] }
        : { map, mode, players: [{ steam_id: steam.trim(), team: side }], clones: [...enemies.map(clone_id => ({ clone_id, team: side === "CT" ? "T" : "CT" })), ...mates.filter(x => !enemies.includes(x)).map(clone_id => ({ clone_id, team: side }))] };
      const result = await api<{ match_id: string }>("/matches", body); attach(result.match_id); void api<Summary[]>("/matches").then(setMatches).catch(() => {});
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function stop() { setBusy(true); try { await api(`/matches/${encodeURIComponent(id)}/stop`, {}); const m = await api<Match>(`/matches/${encodeURIComponent(id)}`); setMatch(m); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  const offline = !catalogueLoaded;
  const hasPlayable = clones.some(c => c.playable !== false);
  const roster = clones;
  const byId = (cid: string) => roster.find(c => c.clone_id === cid);
  const ctClone = offline ? PLACEHOLDER_CLONES[0] : byId(ct);
  const tClone = offline ? PLACEHOLDER_CLONES[1] : byId(t);
  const mapInfo = MAPS.find(m => m.id === map) ?? MAPS[0];
  const modeInfo = MODES.find(m => m.id === mode) ?? MODES[0];
  const toggle = (selected: string[], change: (x: string[]) => void, cid: string) => change(selected.includes(cid) ? selected.filter(x => x !== cid) : [...selected, cid]);
  const enemyNames = enemies.map(e => cloneName(byId(e))).join(" & ") || "your opponents";
  const title = kind === "watch" ? `${cloneName(ctClone)} vs ${cloneName(tClone)}` : `You vs ${enemyNames}`;
  const status = offline && error.startsWith("Match service unavailable") ? "Match service offline. Start it and refresh this page." : error || (catalogueLoaded && !hasPlayable ? "No playable bots are available from the match service." : "");

  /** CT / T opponent card. "Change bot" is a native select laid over the link, so it stays keyboard and screen-reader friendly. */
  const opponent = (team: "CT" | "T", c: Clone | undefined, value: string, change: (x: string) => void) => {
    const photo = photoFor(c);
    return <div className={`${card} relative flex min-h-[176px] items-stretch overflow-hidden bg-[#18181c]`}>
      <div className="relative w-[38%] shrink-0 overflow-hidden">
        {photo ? <img src={photo} alt="" className="absolute inset-0 h-full w-full object-cover object-top" /> : <div className="grid h-full place-items-center text-[44px] font-extrabold text-white/30">{cloneName(c).slice(0, 1).toUpperCase()}</div>}
        <span className="absolute inset-y-0 right-0 w-1/3 bg-gradient-to-r from-transparent to-[#18181c]" aria-hidden />
      </div>
      <div className="flex min-w-0 flex-1 flex-col justify-center gap-1 py-5 pr-5">
        <p className="flex items-center gap-2 whitespace-nowrap text-[11px] font-semibold uppercase tracking-[0.08em] text-[#B8B8C2]"><span className={`rounded px-1.5 py-0.5 text-[12px] font-bold text-white ${team === "CT" ? "bg-[#5a7fa8]" : "bg-[#9c7a52]"}`}>{team}</span>{team === "CT" ? "Counter-Terrorist" : "Terrorist"}</p>
        <p className="truncate text-[clamp(28px,2.6vw,40px)] font-extrabold leading-tight tracking-[-0.03em] text-white">{cloneName(c)}</p>
        <p className="truncate text-[14px] text-[#B8B8C2]">{c?.label || "Player-inspired bot"}</p>
        <label className="relative mt-2 inline-flex w-fit items-center gap-1.5 text-[14px] font-bold text-white hover:text-[#ff4d63]">
          Change bot <span aria-hidden>↗</span>
          <select aria-label={`Change ${team === "CT" ? "Counter-Terrorist" : "Terrorist"} bot`} className="absolute inset-0 cursor-pointer opacity-0" value={value} disabled={offline} onChange={e => change(e.target.value)}>
            {clones.map(x => <option key={x.clone_id} value={x.clone_id} disabled={x.playable === false}>{x.display_name} ({x.clone_id}){x.label ? ` / ${x.label}` : ""}{x.playable === false ? ` — unavailable${x.reason ? `: ${x.reason}` : ""}` : ""}</option>)}
          </select>
        </label>
      </div>
    </div>;
  };

  /** Bot chip for Play vs bot (opponents / teammates). */
  const chip = (c: Clone, selected: string[], change: (x: string[]) => void) => {
    const on = selected.includes(c.clone_id); const photo = photoFor(c);
    return <button key={c.clone_id} type="button" aria-pressed={on} disabled={offline || c.playable === false} title={c.reason || undefined} onClick={() => toggle(selected, change, c.clone_id)}
      className={`flex items-center gap-3 rounded-xl border p-2 pr-4 text-left transition ${on ? "border-[#e4002b] bg-[#e4002b]/10" : "border-white/[0.14] bg-[#18181c] hover:border-white/40"} disabled:opacity-60`}>
      {photo ? <img src={photo} alt="" className="h-11 w-11 rounded-lg object-cover object-top" /> : <span className="grid h-11 w-11 place-items-center rounded-lg bg-white/10 font-bold">{cloneName(c).slice(0, 1).toUpperCase()}</span>}
      <span><span className="block font-bold">{c.display_name}</span><span className="block text-[12px] text-[#B8B8C2]">{c.clone_id}</span>{c.playable === false && <span className="block text-[12px] text-[#B8B8C2]">Unavailable{c.reason ? `: ${c.reason}` : ""}</span>}</span>
    </button>;
  };

  return <div className="space-y-6 text-white">
    <div role="tablist" aria-label="Match type" className="flex gap-2 border-b border-white/[0.15]">
      {([["watch", "Bot vs bot"], ["play", "Play vs bot"]] as const).map(([k, label]) =>
        <button key={k} role="tab" type="button" aria-selected={kind === k} onClick={() => setKind(k)}
          className={`relative -mb-px px-6 pb-4 pt-1 text-[19px] font-bold transition ${kind === k ? "text-white after:absolute after:inset-x-0 after:bottom-0 after:h-[3px] after:rounded-full after:bg-[#e4002b]" : "text-[#9a9aa3] hover:text-white"}`}>{label}</button>)}
    </div>

    <div className="grid gap-6 min-[1100px]:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
      <section className={`${card} space-y-7 p-6`} aria-label="Match setup">
        {kind === "watch" ? <div className="space-y-4">
          {step("01", "Choose your opponents")}
          <div className="grid items-center gap-4 min-[760px]:grid-cols-[1fr_auto_1fr]">
            {opponent("CT", ctClone, ct, setCt)}
            <span className="text-center text-[24px] font-extrabold text-[#B8B8C2]">vs</span>
            {opponent("T", tClone, t, setT)}
          </div>
        </div> : <div className="space-y-5">
          {step("01", "Choose your side")}
          <div className="grid gap-4 min-[760px]:grid-cols-2">
            <label className="grid gap-2 text-[14px] font-semibold text-[#B8B8C2]">Your side
              <select style={chevron} className={selectBox} value={side} onChange={e => setSide(e.target.value)}><option value="CT">Counter-Terrorist (CT)</option><option value="T">Terrorist (T)</option></select></label>
            <label className="grid gap-2 text-[14px] font-semibold text-[#B8B8C2]">Your Steam ID
              <input className={selectBox} placeholder="7656119…" inputMode="numeric" value={steam} onChange={e => setSteam(e.target.value)} /></label>
          </div>
          <div className="space-y-2"><p className="text-[14px] font-semibold text-[#B8B8C2]">Opponents</p><div className="flex flex-wrap gap-3">{roster.map(c => chip(c, enemies, setEnemies))}</div></div>
          {offline && <p className="text-sm text-[#B8B8C2]">Connect to the match service to load the bot catalogue.</p>}
          {catalogueLoaded && !roster.length && <p className="text-sm text-[#B8B8C2]">The match service returned no bots.</p>}
          <div className="space-y-2"><p className="text-[14px] font-semibold text-[#B8B8C2]">Teammates (optional)</p><div className="flex flex-wrap gap-3">{roster.map(c => chip(c, mates, setMates))}</div></div>
        </div>}

        <div className="space-y-4">
          {step("02", "Choose your map")}
          <div role="radiogroup" aria-label="Map" className="grid grid-cols-3 gap-3">
            {MAPS.map(m => <button key={m.id} type="button" role="radio" aria-checked={map === m.id} onClick={() => setMap(m.id)}
              className={`group relative aspect-[16/9] overflow-hidden rounded-xl border-2 text-left transition ${map === m.id ? "border-[#e4002b]" : "border-white/[0.14] hover:border-white/50"}`}>
              {m.image ? <Image src={m.image} alt="" fill sizes="(min-width: 1100px) 20vw, 33vw" className="object-cover transition duration-500 group-hover:scale-105" />
                : <span className="absolute inset-0 bg-[radial-gradient(120%_90%_at_30%_20%,#c96a3b_0%,#7a3b22_45%,#2a1610_100%)]" aria-hidden />}
              <span className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" aria-hidden />
              <span className="absolute bottom-2.5 left-3 text-[clamp(15px,1.5vw,22px)] font-extrabold text-white drop-shadow">{m.name}</span>
              {map === m.id && <span className="absolute right-2.5 top-2.5 grid h-7 w-7 place-items-center rounded-full bg-[#e4002b] text-[14px] font-black" aria-hidden>✓</span>}
            </button>)}
          </div>
        </div>

        <div className="space-y-4">
          {step("03", "Match rules")}
          <div className="grid gap-4 min-[760px]:grid-cols-2">
            <select aria-label="Mode" style={chevron} className={selectBox} value={mode} onChange={e => setMode(e.target.value)}>{MODES.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}</select>
            {/* The service fixes the round count per mode, so this picks the mode by its round count. */}
            <select aria-label="Rounds to win" style={chevron} className={selectBox} value={mode} onChange={e => setMode(e.target.value)}>{MODES.map(m => <option key={m.id} value={m.id}>First to {m.rounds} rounds</option>)}</select>
          </div>
        </div>
      </section>

      <aside className={`${card} relative flex min-h-[520px] flex-col overflow-hidden`} aria-label="Match preview">
        <div className="relative flex-1">
          {mapInfo.image ? <Image src={mapInfo.image} alt="" fill sizes="(min-width: 1100px) 40vw, 100vw" className="object-cover" priority />
            : <span className="absolute inset-0 bg-[radial-gradient(120%_90%_at_30%_20%,#c96a3b_0%,#7a3b22_45%,#2a1610_100%)]" aria-hidden />}
          <span className="absolute inset-0 bg-gradient-to-t from-[#131316] via-[#131316]/40 to-transparent" aria-hidden />
          <div className="absolute inset-x-0 bottom-0 p-6 pb-5">
            <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-[#D8D8DE]">Match preview</p>
            <p className="mt-1 text-[clamp(30px,3vw,44px)] font-extrabold leading-tight tracking-[-0.03em]">{title}</p>
            <p className="mt-1 text-[17px] text-[#B8B8C2]">{mapInfo.name} <span aria-hidden>·</span> {modeInfo.name} <span aria-hidden>·</span> First to {modeInfo.rounds}</p>
          </div>
        </div>
        <div className="mx-6 border-t border-white/[0.15]" />
        <div className="space-y-4 p-6 pt-5">
          <div className="flex items-center justify-between gap-4 text-[15px]">
            <p className="font-bold">{kind === "watch" ? "You will watch this match." : "You will play this match."}</p>
            <p className="flex items-center gap-1.5 text-[#B8B8C2]"><svg width="14" height="16" viewBox="0 0 14 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden><rect x="1.5" y="7" width="11" height="8" rx="1.5" /><path d="M4 7V4.8a3 3 0 0 1 6 0V7" /></svg>Private match</p>
          </div>
          <button type="button" disabled={busy || offline || !hasPlayable} onClick={start}
            className="group relative flex h-14 w-full items-center justify-center rounded-full bg-white text-[18px] font-bold text-black transition hover:bg-[#f2f2f4] disabled:bg-white/60 disabled:text-black/60">
            {busy ? "Starting…" : "Start match"}
            <span className="absolute right-2 grid h-10 w-10 place-items-center rounded-full bg-black/10 transition group-enabled:group-hover:translate-x-0.5" aria-hidden>→</span>
          </button>
          <p role={status ? "alert" : undefined} className={`min-h-[20px] text-[14px] ${status && !offline ? "text-red-300" : "text-[#B8B8C2]"}`}>{status}</p>
        </div>
      </aside>
    </div>

    {kind === "watch" && <section className={`${card} flex flex-col gap-4 p-5 min-[900px]:flex-row min-[900px]:items-center min-[900px]:gap-8`} aria-label="Watch an existing match">
      <h2 className="shrink-0 text-[22px] font-extrabold tracking-[-0.02em]">Watch an existing match</h2>
      <select aria-label="Existing match" style={chevron} className={`${selectBox} min-[900px]:max-w-[640px]`} value={watchPick} onChange={e => setWatchPick(e.target.value)}>
        <option value="">{matches.length ? "Choose a match" : "No matches yet"}</option>
        {matches.map(m => <option key={m.match_id} value={m.match_id}>{m.match_id} / {m.status} / {m.players.join(" vs ")}</option>)}
      </select>
      <button type="button" disabled={!watchPick} onClick={() => watchPick && attach(watchPick)}
        className="ml-auto inline-flex h-12 shrink-0 items-center gap-2 rounded-full border border-white/70 px-7 text-[16px] font-bold transition hover:bg-white hover:text-black disabled:opacity-40">Watch <span aria-hidden>↗</span></button>
    </section>}

    {match && <section className="space-y-4 rounded-2xl border border-white/20 bg-[#131316] p-6" aria-live="polite"><div className="flex flex-wrap items-center gap-4"><h2 className="text-xl font-bold">Match {id} / {match.status}</h2><button className={button} disabled={busy || ["ended", "failed"].includes(match.status)} onClick={stop}>Stop match</button><a href={`${API_URL}/demo/replay.html?match=${encodeURIComponent(id)}`} className="underline">Open replay</a></div><p>CT {match.score.CT} - {match.score.T} T / {match.status === "live" ? `round ${match.round + 1}` : match.status}</p><p>{match.players.map(p => `${p.display_name} (${p.team})`).join(" vs ")}</p>{match.players.some(p => !p.is_clone) && <p>Play at the CS2 PC. {match.join_link && <a className="underline" href={match.join_link}>Join link</a>}</p>}{match.error && <p role="alert">{match.error}</p>}<PositionMaps trace={trace} match={match} /><h3 className="font-bold">Events</h3><div className="max-h-64 overflow-auto text-sm">{events.length ? [...events].reverse().map((e, i) => <p key={i}>{e.event} / {JSON.stringify(e.data)}</p>) : "No events yet."}</div><p className="text-sm text-[#aaa]">Live position maps and replay are available in the <a className="underline" href={`${API_URL}/demo/watch.html?match=${encodeURIComponent(id)}`}>match viewer</a>. CS2 sends positions while spectating.</p></section>}
  </div>;
}


function PositionMaps({ trace, match }: { trace: Trace | null; match: Match }) {
  const shown = trace?.live_round ?? trace?.rounds[trace.rounds.length - 1]?.round;
  const round = trace?.rounds.find(r => r.round === shown);
  const bots = match.players.filter(p => p.is_clone);
  return <div className="grid gap-4 md:grid-cols-2">{bots.map((bot, index) => <div key={`${bot.display_name}-${index}`} className="rounded-xl border border-white/20 p-3"><h3>{bot.display_name} · {bot.team}</h3>{round?.players.length ? <svg viewBox="-2600 -1000 4200 3800" className="mt-2 w-full rounded bg-[#171c22]" role="img" aria-label={`${bot.display_name} position map, round ${shown}`}>{round.players.map((p, i) => { const points = p.path.map(point => `${point[1]},${-point[2]}`).join(" "); const last = p.path[p.path.length - 1]; return <g key={i} opacity={p.name === bot.display_name ? 1 : 0.35}><polyline points={points} fill="none" stroke={p.team === "CT" ? "#5aa7ff" : "#f0a93b"} strokeWidth="28" />{last && <circle cx={last[1]} cy={-last[2]} r="55" fill={p.team === "CT" ? "#5aa7ff" : "#f0a93b"} />}</g>; })}</svg> : <p className="py-8 text-sm text-[#aaa]">{trace?.source === "gsi" ? "Waiting for positions. CS2 sends them while spectating." : "Waiting for the first round and position data."}</p>}</div>)}</div>;
}
