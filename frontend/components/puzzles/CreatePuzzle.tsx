'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { call, getPlayerName, type DeathDetail, type Draft, type Side } from '@/lib/puzzles';
import FeedbackList from './FeedbackList';
import MapReplay from './MapReplay';

const TAGS = ['retake', 'post-plant', 'entry', 'hold', 'clutch', 'eco', 'rifle', 'awp', 'pistol'];
const pill = 'flex h-[42px] cursor-pointer items-center justify-center rounded-full px-[22px] text-[15.5px] font-bold disabled:cursor-not-allowed disabled:opacity-50';
const field = 'h-[40px] rounded-[8px] border border-white/[0.2] bg-transparent px-[12px] text-[15px] text-white';

/** Save a recent death as a puzzle, or start a puzzle from every player's POV footage. */
export default function CreatePuzzle({ deathParam }: { deathParam?: string }) {
  return (
    <div className="grid gap-[28px] min-[1100px]:grid-cols-2">
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
    <section aria-label="Save a death" className="rounded-[16px] border border-white/[0.16] bg-[#131316]/80 p-[24px]">
      <p className="font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">From your last death</p>
      <h2 className="mt-[8px] text-[22px] font-bold tracking-[-0.02em] text-white">Save the last 10 seconds as a puzzle</h2>

      {deaths.length === 0 ? (
        <p className="mt-[14px] text-[15px] text-[#B8B8C2]">
          No saved deaths yet. Play a match in CS2 with CloneDirector; every time you die, the last 10 seconds are saved here.
        </p>
      ) : (
        <>
          <label className="mt-[16px] grid gap-[6px] text-[13.5px] text-[#B8B8C2]">
            Death
            <select value={id} onChange={(e) => setId(e.target.value)} className={`${field} bg-[#131316]`}>
              {deaths.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.created.slice(0, 19).replace('T', ' ')} · {d.killer ? `killed by ${d.killer}` : d.title}
                </option>
              ))}
            </select>
          </label>
          {death && (
            <div className="mt-[16px] grid gap-[16px]">
              <MapReplay puzzle={death.puzzle} mistakes={death.feedback} />
              <FeedbackList items={death.feedback} />
              <label className="grid gap-[6px] text-[13.5px] text-[#B8B8C2]">
                Title
                <input value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} className={field} />
              </label>
              <fieldset>
                <legend className="mb-[8px] text-[13.5px] text-[#B8B8C2]">Themes</legend>
                <div className="flex flex-wrap gap-[8px]">
                  {TAGS.map((t) => {
                    const on = tags.includes(t);
                    return (
                      <button
                        key={t}
                        type="button"
                        aria-pressed={on}
                        onClick={() => setTags(on ? tags.filter((x) => x !== t) : [...tags, t])}
                        className={`h-[34px] cursor-pointer rounded-full px-[14px] text-[14px] ${on ? 'bg-[#F5F4F0] font-bold text-[#111111]' : 'border border-white/[0.22] text-[#E8E8EC] hover:border-white/45'}`}
                      >
                        {t}
                      </button>
                    );
                  })}
                </div>
              </fieldset>
              <div className="flex flex-wrap gap-[12px]">
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
        <p role="status" className={`mt-[14px] text-[15px] ${msg.ok ? 'text-[#7ee2a0]' : 'text-[#ff8a9b]'}`}>
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
    <section aria-label="Create from footage" className="rounded-[16px] border border-white/[0.16] bg-[#131316]/80 p-[24px]">
      <p className="font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">From footage</p>
      <h2 className="mt-[8px] text-[22px] font-bold tracking-[-0.02em] text-white">Build a puzzle from every player&rsquo;s POV</h2>
      <p role="note" className="mt-[12px] rounded-[10px] border border-[#d29922]/60 bg-[#d29922]/10 p-[12px] text-[14px] text-[#f1d48a]">
        Not finished: your videos are stored, but nothing reads player positions out of them yet, so no puzzle is created
        from this form. It is here so the feature has its place in the app.
      </p>

      <label className="mt-[16px] grid gap-[6px] text-[13.5px] text-[#B8B8C2]">
        Puzzle title
        <input value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} placeholder="Retake on B apartments" className={field} />
      </label>

      <div className="mt-[16px] grid gap-[12px]">
        {slots.map((s, i) => (
          <div key={i} className="grid gap-[8px] rounded-[12px] border border-white/[0.12] p-[12px] min-[560px]:grid-cols-[1fr_90px_80px]">
            <input aria-label={`Player ${i + 1} name`} value={s.name} maxLength={40} placeholder={`Player ${i + 1}`} onChange={(e) => update(i, { name: e.target.value })} className={field} />
            <select aria-label={`Player ${i + 1} side`} value={s.side} onChange={(e) => update(i, { side: e.target.value as Side })} className={`${field} bg-[#131316]`}>
              <option value="CT">CT</option>
              <option value="T">T</option>
            </select>
            <input aria-label={`Player ${i + 1} sync offset, seconds`} title="Seconds this video starts after the first one" type="number" step="0.1" value={s.offset} onChange={(e) => update(i, { offset: e.target.value })} className={field} />
            <input
              aria-label={`Player ${i + 1} POV video`}
              type="file"
              accept=".mp4,.webm,.mov,.mkv,video/*"
              onChange={(e) => update(i, { file: e.target.files?.[0] ?? null })}
              className="text-[13.5px] text-[#B8B8C2] min-[560px]:col-span-3"
            />
          </div>
        ))}
      </div>

      <div className="mt-[14px] flex flex-wrap gap-[12px]">
        <button type="button" disabled={slots.length >= 10} onClick={() => setSlots([...slots, blank('T')])} className="h-[38px] cursor-pointer rounded-full border border-white/[0.25] px-[16px] text-[14.5px] text-white hover:border-white/50 disabled:opacity-50">
          Add player
        </button>
        <button type="button" disabled={slots.length <= 2} onClick={() => setSlots(slots.slice(0, -1))} className="h-[38px] cursor-pointer rounded-full border border-white/[0.25] px-[16px] text-[14.5px] text-white hover:border-white/50 disabled:opacity-50">
          Remove last
        </button>
        <button type="button" disabled={!ready || busy} onClick={submit} className={`${pill} ml-auto h-[38px] bg-[#F5F4F0] text-[#111111]`}>
          {busy ? 'Uploading…' : 'Upload footage'}
        </button>
      </div>
      {msg && (
        <p role="status" className={`mt-[12px] text-[14.5px] ${msg.ok ? 'text-[#f1d48a]' : 'text-[#ff8a9b]'}`}>
          {msg.text}
        </p>
      )}
      {drafts.length > 0 && (
        <div className="mt-[18px]">
          <h3 className="mb-[8px] font-mono text-[12.5px] font-bold uppercase tracking-[0.06em] text-[#9E9EA8]">Uploaded drafts</h3>
          <ul className="grid gap-[6px] text-[14px] text-[#D8D8DE]">
            {drafts.slice(0, 5).map((d) => (
              <li key={d.id}>
                {d.title} · {d.slots.filter((s) => s.file).length}/{d.slots.length} POVs · <span className="text-[#f1d48a]">{d.status === 'needs_derivation' ? 'waiting for the (unbuilt) derivation step' : 'awaiting footage'}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
