'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { call, getPlayerName, type DeathDetail, type Draft, type Side } from '@/lib/puzzles';
import FeedbackList from './FeedbackList';
import MapReplay from './MapReplay';

const TAGS = ['retake', 'post-plant', 'entry', 'hold', 'clutch', 'eco', 'rifle', 'awp', 'pistol'];
const pill = 'flex h-[44px] cursor-pointer items-center justify-center gap-[10px] rounded-full px-[24px] text-[15.5px] font-bold transition disabled:cursor-not-allowed disabled:opacity-45';
const ghost = 'h-[40px] cursor-pointer rounded-full border border-white/[0.22] px-[18px] text-[14.5px] font-semibold text-white transition hover:border-white/55 disabled:cursor-not-allowed disabled:opacity-40';
const field = 'h-[44px] w-full rounded-[10px] border border-white/[0.16] bg-[#0f0f12] px-[14px] text-[15px] text-white outline-none transition placeholder:text-[#6E6E78] hover:border-white/30 focus:border-[#E4002B]';
const label = 'grid gap-[8px] text-[13px] font-semibold uppercase tracking-[0.08em] text-[#9E9EA8]';
const card = 'rounded-[18px] border border-white/[0.14] bg-[#131316] p-[26px]';
/** Chevron for the custom selects (inline: Tailwind cannot build this data URL as a class). */
const chevron: React.CSSProperties = {
  backgroundImage:
    "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8'><path d='M1 1l5 5 5-5' fill='none' stroke='white' stroke-width='1.8'/></svg>\")",
  backgroundRepeat: 'no-repeat',
  backgroundPosition: 'right 15px center',
  backgroundSize: '12px 8px',
};
/** Section header used by both panels: red numbered eyebrow, title, one-line summary. */
function PanelHead({ n, eyebrow, title, children }: { n: string; eyebrow: string; title: string; children?: React.ReactNode }) {
  return (
    <header>
      <p className="flex items-center gap-[8px] font-mono text-[13px] font-bold uppercase tracking-[0.1em] text-[#D8D8DE]">
        <span className="text-[#E4002B]">{n}</span>
        <span className="text-[#E4002B]/60">/</span>
        {eyebrow}
      </p>
      <h2 className="mt-[10px] text-[26px] font-extrabold leading-tight tracking-[-0.03em] text-white">{title}</h2>
      {children}
    </header>
  );
}

/** Save a recent death as a puzzle, or start a puzzle from every player's POV footage. */
export default function CreatePuzzle({ deathParam }: { deathParam?: string }) {
  return (
    <div className="grid items-start gap-[24px] min-[1100px]:grid-cols-2">
      <FromDeath deathParam={deathParam} />
      <FromFootage />
    </div>
  );
}

function FromDeath({ deathParam }: { deathParam?: string }) {
  const [deaths, setDeaths] = useState<{ id: string; title: string; created: string; killer: string | null }[]>([]);
  const [id, setId] = useState(deathParam ?? '');
  const [death, setDeath] = useState<DeathDetail | null>(null);
  const [title, setTitle] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [msg, setMsg] = useState<{ ok: boolean; text: string; href?: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    call<typeof deaths>('/deaths')
      .then((d) => {
        setDeaths(d);
        if (!id && d[0]) setId(d[0].id);
      })
      .catch(() => setDeaths([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!id) return;
    call<DeathDetail>(`/deaths/${encodeURIComponent(id)}`)
      .then((d) => {
        setDeath(d);
        const hero = d.puzzle.players.find((p) => p.hero);
        setTitle(`${hero?.name ?? 'Me'} vs ${d.puzzle.events.find((e) => e.type === 'kill')?.attacker ?? 'the enemy'}`);
      })
      .catch((e) => setMsg({ ok: false, text: e instanceof Error ? e.message : String(e) }));
  }, [id]);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : String(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-label="Save a death" className={card}>
      <PanelHead n="01" eyebrow="From your last death" title="Save the last 10 seconds as a puzzle" />

      {deaths.length === 0 ? (
        <div className="mt-[20px] rounded-[14px] border border-dashed border-white/[0.16] bg-[#0f0f12] p-[22px]">
          <div className="flex items-center gap-[14px]">
            <span className="grid h-[44px] w-[44px] shrink-0 place-items-center rounded-full bg-[#E4002B]/15 text-[#ff4d63]" aria-hidden>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><circle cx="10" cy="10" r="8" /><path d="M10 5.5V10l3 2" /></svg>
            </span>
            <p className="text-[17px] font-bold text-white">No saved deaths yet.</p>
          </div>
          <ol className="mt-[18px] grid gap-[12px] text-[15px] text-[#B8B8C2]">
            {['Play a match in CS2 with CloneDirector.', 'Every time you die,', 'the last 10 seconds are saved here.'].map((t, i) => (
              <li key={t} className="flex items-center gap-[12px]">
                <span className="grid h-[26px] w-[26px] shrink-0 place-items-center rounded-full border border-white/[0.2] font-mono text-[12px] font-bold text-white">{i + 1}</span>
                {t}
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <>
          <label className={`mt-[20px] ${label}`}>
            Death
            <select value={id} onChange={(e) => setId(e.target.value)} style={chevron} className={`${field} appearance-none pr-[40px] normal-case tracking-normal`}>
              {deaths.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.created.slice(0, 19).replace('T', ' ')} · {d.killer ? `killed by ${d.killer}` : d.title}
                </option>
              ))}
            </select>
          </label>
          {death && (
            <div className="mt-[18px] grid gap-[18px]">
              <MapReplay puzzle={death.puzzle} mistakes={death.feedback} />
              <FeedbackList items={death.feedback} />
              <label className={label}>
                Title
                <input value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} className={`${field} normal-case tracking-normal`} />
              </label>
              <fieldset>
                <legend className="mb-[10px] text-[13px] font-semibold uppercase tracking-[0.08em] text-[#9E9EA8]">Themes</legend>
                <div className="flex flex-wrap gap-[8px]">
                  {TAGS.map((t) => {
                    const on = tags.includes(t);
                    return (
                      <button
                        key={t}
                        type="button"
                        aria-pressed={on}
                        onClick={() => setTags(on ? tags.filter((x) => x !== t) : [...tags, t])}
                        className={`h-[36px] cursor-pointer rounded-full px-[16px] text-[14px] capitalize transition ${on ? 'bg-[#F5F4F0] font-bold text-[#111111]' : 'border border-white/[0.22] font-medium text-[#E8E8EC] hover:border-white/50'}`}
                      >
                        {t}
                      </button>
                    );
                  })}
                </div>
              </fieldset>
              <div className="flex flex-wrap gap-[12px] border-t border-white/[0.1] pt-[18px]">
                <button
                  type="button"
                  disabled={busy || !title.trim()}
                  onClick={() =>
                    run(async () => {
                      const saved = await call<{ id: string }>(`/deaths/${encodeURIComponent(id)}/save`, { method: 'POST', json: { title, tags } });
                      setMsg({ ok: true, text: 'Saved to the library.', href: `/puzzles/${encodeURIComponent(saved.id)}` });
                    })
                  }
                  className={`${pill} bg-[#F5F4F0] text-[#111111]`}
                >
                  Save as puzzle
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    run(async () => {
                      await call(`/deaths/${encodeURIComponent(id)}/start`, { method: 'POST', json: { player: getPlayerName() } });
                      setMsg({ ok: true, text: 'Loaded in CS2. Switch to the game and try the moment again.' });
                    })
                  }
                  className={`${pill} bg-[#E4002B] text-white hover:bg-[#ff1a44]`}
                >
                  Retry in CS2
                </button>
              </div>
            </div>
          )}
        </>
      )}
      {msg && (
        <p role="status" className={`mt-[16px] rounded-[10px] px-[14px] py-[10px] text-[14.5px] ${msg.ok ? 'bg-[#7ee2a0]/10 text-[#7ee2a0]' : 'bg-[#E4002B]/10 text-[#ff8a9b]'}`}>
          {msg.text}{' '}
          {msg.href && (
            <Link href={msg.href} className="underline">
              Open it
            </Link>
          )}
        </p>
      )}
    </section>
  );
}

interface SlotForm {
  name: string;
  side: Side;
  offset: string;
  file: File | null;
}

const blank = (side: Side): SlotForm => ({ name: '', side, offset: '0', file: null });

function FromFootage() {
  const [title, setTitle] = useState('');
  const [slots, setSlots] = useState<SlotForm[]>([blank('CT'), blank('CT'), blank('T'), blank('T')]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);

  useEffect(() => {
    call<Draft[]>('/puzzles/drafts').then(setDrafts).catch(() => setDrafts([]));
  }, [draft]);

  const update = (i: number, patch: Partial<SlotForm>) => setSlots(slots.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const ready = slots.length >= 2 && slots.every((s) => s.name.trim() && s.file);

  const submit = async () => {
    setBusy(true);
    setMsg(null);
    try {
      let d = await call<Draft>('/puzzles/drafts', {
        method: 'POST',
        json: { title: title || 'Untitled', slots: slots.map((s) => ({ name: s.name.trim(), side: s.side, offset_seconds: Number(s.offset) || 0 })) },
      });
      for (let i = 0; i < slots.length; i++) {
        const f = slots[i].file!;
        const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase();
        d = await call<Draft>(`/puzzles/drafts/${d.id}/pov/${i}?ext=${encodeURIComponent(ext)}`, { method: 'PUT', body: f });
      }
      setDraft(d);
      setMsg({ ok: true, text: d.message });
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : String(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-label="Create from footage" className={card}>
      <PanelHead n="02" eyebrow="From footage" title="Build a puzzle from every player&rsquo;s POV" />
      <p role="note" className="mt-[14px] flex gap-[10px] rounded-[12px] border border-[#d29922]/40 bg-[#d29922]/[0.08] px-[14px] py-[11px] text-[13.5px] leading-snug text-[#f1d48a]">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" className="mt-[2px] shrink-0" aria-hidden><path d="M8 1.8 15 14H1L8 1.8Z" /><path d="M8 6.5v3.2M8 11.8v.1" /></svg>
        <span>
          Not finished: your videos are stored, but nothing reads player positions out of them yet, so no puzzle is created
          from this form. It is here so the feature has its place in the app.
        </span>
      </p>

      <label className={`mt-[20px] ${label}`}>
        Puzzle title
        <input value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} placeholder="Retake on B apartments" className={`${field} normal-case tracking-normal`} />
      </label>

      <div className="mt-[20px] flex items-center justify-between">
        <p className="text-[13px] font-semibold uppercase tracking-[0.08em] text-[#9E9EA8]">Players</p>
        <p className="text-[13px] text-[#6E6E78]">{slots.length} of 10</p>
      </div>
      <div className="mt-[10px] grid gap-[10px]">
        {slots.map((s, i) => (
          <div key={i} className="grid gap-[10px] rounded-[14px] border border-white/[0.1] bg-[#0f0f12] p-[12px]">
            <div className="grid grid-cols-[34px_minmax(0,1fr)_auto] items-center gap-[10px] min-[560px]:grid-cols-[34px_minmax(0,1fr)_auto_120px]">
              <span className={`grid h-[34px] w-[34px] place-items-center rounded-full font-mono text-[13px] font-bold text-white ${s.side === 'CT' ? 'bg-[#5a7fa8]' : 'bg-[#9c7a52]'}`} aria-hidden>{i + 1}</span>
              <input aria-label={`Player ${i + 1} name`} value={s.name} maxLength={40} placeholder={`Player ${i + 1}`} onChange={(e) => update(i, { name: e.target.value })} className={`${field} h-[40px]`} />
              {/* Side: the same CT / T choice, as a two-button switch. */}
              <div role="radiogroup" aria-label={`Player ${i + 1} side`} className="flex h-[40px] rounded-[10px] border border-white/[0.16] p-[3px]">
                {(['CT', 'T'] as const).map((side) => (
                  <button key={side} type="button" role="radio" aria-checked={s.side === side} onClick={() => update(i, { side })}
                    className={`w-[42px] rounded-[7px] text-[13px] font-bold transition ${s.side === side ? (side === 'CT' ? 'bg-[#5a7fa8] text-white' : 'bg-[#9c7a52] text-white') : 'text-[#9E9EA8] hover:text-white'}`}>
                    {side}
                  </button>
                ))}
              </div>
              <label className="col-span-3 flex h-[40px] items-center gap-[8px] rounded-[10px] border border-white/[0.16] px-[12px] text-[12.5px] text-[#9E9EA8] focus-within:border-[#E4002B] min-[560px]:col-span-1" title="Seconds this video starts after the first one">
                Offset
                <input aria-label={`Player ${i + 1} sync offset, seconds`} type="number" step="0.1" value={s.offset} onChange={(e) => update(i, { offset: e.target.value })} className="w-full min-w-0 bg-transparent text-right text-[15px] text-white outline-none" />
                <span>s</span>
              </label>
            </div>
            {/* File picker: the native input stays (screen readers, keyboard) but is drawn as a drop strip. */}
            <label className={`group relative flex h-[42px] cursor-pointer items-center gap-[10px] rounded-[10px] border border-dashed px-[14px] text-[14px] transition focus-within:border-[#E4002B] ${s.file ? 'border-[#7ee2a0]/50 bg-[#7ee2a0]/[0.06] text-white' : 'border-white/[0.2] text-[#B8B8C2] hover:border-white/45'}`}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className={s.file ? 'text-[#7ee2a0]' : 'text-[#9E9EA8]'} aria-hidden>
                {s.file ? <path d="M3 8.5 6.5 12 13 4.5" /> : <><path d="M8 11V2.5M4.5 6 8 2.5 11.5 6" /><path d="M2.5 11v2.5h11V11" /></>}
              </svg>
              <span className="min-w-0 flex-1 truncate">{s.file ? s.file.name : 'Choose POV video'}</span>
              <span className={`shrink-0 text-[12.5px] text-[#6E6E78] ${s.file ? '' : 'hidden min-[480px]:inline'}`}>{s.file ? `${(s.file.size / 1e6).toFixed(1)} MB` : '.mp4 .webm .mov .mkv'}</span>
              <input
                aria-label={`Player ${i + 1} POV video`}
                type="file"
                accept=".mp4,.webm,.mov,.mkv,video/*"
                onChange={(e) => update(i, { file: e.target.files?.[0] ?? null })}
                className="absolute inset-0 cursor-pointer opacity-0"
              />
            </label>
          </div>
        ))}
      </div>

      <div className="mt-[16px] flex flex-wrap items-center gap-[10px] border-t border-white/[0.1] pt-[18px]">
        <button type="button" disabled={slots.length >= 10} onClick={() => setSlots([...slots, blank('T')])} className={ghost}>
          + Add player
        </button>
        <button type="button" disabled={slots.length <= 2} onClick={() => setSlots(slots.slice(0, -1))} className={ghost}>
          Remove last
        </button>
        <button type="button" disabled={!ready || busy} onClick={submit} className={`${pill} ml-auto bg-[#F5F4F0] text-[#111111] hover:bg-white`}>
          {busy ? 'Uploading…' : 'Upload footage'}
          <span aria-hidden>↑</span>
        </button>
      </div>
      {!ready && <p className="mt-[10px] text-right text-[12.5px] text-[#6E6E78]">Name every player and choose a video for each to upload.</p>}
      {msg && (
        <p role="status" className={`mt-[12px] rounded-[10px] px-[14px] py-[10px] text-[14px] ${msg.ok ? 'bg-[#d29922]/10 text-[#f1d48a]' : 'bg-[#E4002B]/10 text-[#ff8a9b]'}`}>
          {msg.text}
        </p>
      )}
      {drafts.length > 0 && (
        <div className="mt-[20px] border-t border-white/[0.1] pt-[16px]">
          <h3 className="mb-[10px] font-mono text-[12.5px] font-bold uppercase tracking-[0.08em] text-[#9E9EA8]">Uploaded drafts</h3>
          <ul className="grid gap-[8px] text-[14px] text-[#D8D8DE]">
            {drafts.slice(0, 5).map((d) => (
              <li key={d.id} className="flex flex-wrap items-center gap-x-[10px] gap-y-[4px] rounded-[10px] bg-[#0f0f12] px-[14px] py-[10px]">
                <span className="font-semibold text-white">{d.title}</span>
                <span className="text-[#9E9EA8]">{d.slots.filter((s) => s.file).length}/{d.slots.length} POVs</span>
                <span className="ml-auto rounded-full bg-[#d29922]/15 px-[10px] py-[2px] text-[12.5px] text-[#f1d48a]">{d.status === 'needs_derivation' ? 'waiting for the (unbuilt) derivation step' : 'awaiting footage'}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
