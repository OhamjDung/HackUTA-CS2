"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/puzzles";

type Clone = { clone_id: string; display_name: string; label?: string; playable?: boolean };
type Match = { match_id: string; status: string; round: number; score: { CT: number; T: number }; players: { display_name: string; team: string; is_clone: boolean }[]; error?: string; join_link?: string };
type Event = { event: string; sent_at: string; data: unknown };
type Summary = { match_id: string; status: string; players: string[] };
async function api<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, body === undefined ? undefined : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(Array.isArray(data?.detail) ? data.detail.map((x: { msg?: string }) => x.msg).join(", ") : data?.detail || res.statusText);
  return data as T;
}
const field = "rounded-lg border border-white/20 bg-[#202025] p-2 text-white";
const button = "rounded-full bg-white px-5 py-3 font-bold text-black disabled:opacity-40";

export default function MatchControls() {
  const [kind, setKind] = useState<"watch" | "play">("watch");
  const [clones, setClones] = useState<Clone[]>([]);
  const [matches, setMatches] = useState<Summary[]>([]);
  const [ct, setCt] = useState(""); const [t, setT] = useState("");
  const [side, setSide] = useState("CT"); const [steam, setSteam] = useState("76561198000000001");
  const [enemies, setEnemies] = useState<string[]>([]); const [mates, setMates] = useState<string[]>([]);
  const [map, setMap] = useState("de_mirage"); const [mode, setMode] = useState("wingman");
  const [id, setId] = useState(""); const [match, setMatch] = useState<Match | null>(null); const [events, setEvents] = useState<Event[]>([]);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => {
    api<Clone[]>("/clones").then(all => {
      const available = all.filter(c => c.playable !== false); setClones(available);
      setCt(available.find(c => c.clone_id === "donk_v1")?.clone_id ?? available[0]?.clone_id ?? "");
      const enemy = available.find(c => c.clone_id === "broky_v1")?.clone_id ?? available[1]?.clone_id ?? available[0]?.clone_id ?? "";
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
        const [m, e] = await Promise.all([api<Match>(`/matches/${encodeURIComponent(id)}`), api<Event[]>(`/matches/${encodeURIComponent(id)}/events`)]);
        if (!active) return; setMatch(m); setEvents(e); setError("");
        if (m.status !== "ended" && m.status !== "failed") timer = setTimeout(tick, 500);
      } catch (e) { if (active) { setError((e as Error).message); timer = setTimeout(tick, 2000); } }
    };
    void tick(); return () => { active = false; clearTimeout(timer); };
  }, [id]);
  function attach(next: string) { setMatch(null); setEvents([]); setId(next); const url = new URL(window.location.href); url.searchParams.set("match", next); history.replaceState(null, "", url); }
  async function start() {
    setError(""); setBusy(true);
    try {
      const body = kind === "watch" ? { map, mode, players: [], clones: [{ clone_id: ct, team: "CT" }, { clone_id: t, team: "T" }] }
        : { map, mode, players: [{ steam_id: steam.trim(), team: side }], clones: [...enemies.map(clone_id => ({ clone_id, team: side === "CT" ? "T" : "CT" })), ...mates.filter(x => !enemies.includes(x)).map(clone_id => ({ clone_id, team: side }))] };
      const result = await api<{ match_id: string }>("/matches", body); attach(result.match_id);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function stop() { setBusy(true); try { await api(`/matches/${encodeURIComponent(id)}/stop`, {}); const m = await api<Match>(`/matches/${encodeURIComponent(id)}`); setMatch(m); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  const select = (value: string, change: (x: string) => void) => <select className={field} value={value} onChange={e => change(e.target.value)}>{clones.map(c => <option key={c.clone_id} value={c.clone_id}>{c.display_name} ({c.clone_id}){c.label ? ` · ${c.label}` : ""}</option>)}</select>;
  const checks = (selected: string[], change: (x: string[]) => void) => <div className="flex flex-wrap gap-4">{clones.map(c => <label key={c.clone_id} className="flex gap-2"><input type="checkbox" checked={selected.includes(c.clone_id)} onChange={e => change(e.target.checked ? [...selected, c.clone_id] : selected.filter(x => x !== c.clone_id))} />{c.display_name} ({c.clone_id})</label>)}</div>;
  return <div className="space-y-6 text-white">
    <div className="flex gap-3"><button className={button} aria-pressed={kind === "watch"} onClick={() => setKind("watch")}>Bot vs bot</button><button className={button} aria-pressed={kind === "play"} onClick={() => setKind("play")}>Play vs bot</button></div>
    <section className="space-y-5 rounded-2xl border border-white/20 bg-[#131316] p-6">
      <div className="flex flex-wrap gap-4">
        {kind === "watch" ? <><label className="grid gap-2">CT{select(ct, setCt)}</label><label className="grid gap-2">T{select(t, setT)}</label></> : <><label className="grid gap-2">Your side<select className={field} value={side} onChange={e => setSide(e.target.value)}><option>CT</option><option>T</option></select></label><label className="grid gap-2">Your Steam ID<input className={field} value={steam} onChange={e => setSteam(e.target.value)} /></label></>}
        <label className="grid gap-2">Map<select className={field} value={map} onChange={e => setMap(e.target.value)}>{["de_mirage", "de_inferno", "de_dust2"].map(x => <option key={x}>{x}</option>)}</select></label>
        <label className="grid gap-2">Mode<select className={field} value={mode} onChange={e => setMode(e.target.value)}><option value="wingman">Wingman (first to 9)</option><option value="competitive">Competitive (first to 13)</option></select></label>
      </div>
      {kind === "play" && <><div><p className="mb-2">Opponents</p>{checks(enemies, setEnemies)}</div><div><p className="mb-2">Teammates (optional)</p>{checks(mates, setMates)}</div></>}
      <button className={button} disabled={busy || !clones.length} onClick={start}>Start match</button>
      {kind === "watch" && <label className="grid max-w-md gap-2">Watch an existing match<select className={field} value="" onChange={e => e.target.value && attach(e.target.value)}><option value="">Choose a match</option>{matches.map(m => <option key={m.match_id} value={m.match_id}>{m.match_id} · {m.status} · {m.players.join(" vs ")}</option>)}</select></label>}
      {error && <p role="alert" className="text-red-300">{error}</p>}
    </section>
    {match && <section className="space-y-4 rounded-2xl border border-white/20 bg-[#131316] p-6" aria-live="polite"><div className="flex flex-wrap items-center gap-4"><h2 className="text-xl font-bold">Match {id} · {match.status}</h2><button className={button} disabled={busy || ["ended", "failed"].includes(match.status)} onClick={stop}>Stop match</button><a href={`${API_URL}/demo/replay.html?match=${encodeURIComponent(id)}`} className="underline">Open replay</a></div><p>CT {match.score.CT} — {match.score.T} T · {match.status === "live" ? `round ${match.round + 1}` : match.status}</p><p>{match.players.map(p => `${p.display_name} (${p.team})`).join(" vs ")}</p>{kind === "play" && <p>Play at the CS2 PC. {match.join_link && <a className="underline" href={match.join_link}>Join link</a>}</p>}{match.error && <p role="alert">{match.error}</p>}<h3 className="font-bold">Events</h3><div className="max-h-64 overflow-auto text-sm">{events.length ? [...events].reverse().map((e, i) => <p key={i}>{e.event} · {JSON.stringify(e.data)}</p>) : "No events yet."}</div><p className="text-sm text-[#aaa]">Live position maps and replay are available in the <a className="underline" href={`${API_URL}/demo/watch.html?match=${encodeURIComponent(id)}`}>match viewer</a>. CS2 sends positions while spectating.</p></section>}
  </div>;
}
