'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { call, getPlayerName, ratingBand, setPlayerName, type Attempt, type PlayerStats, type PuzzleSummary } from '@/lib/puzzles';

const chip = (on: boolean) =>
  `flex h-[38px] cursor-pointer items-center whitespace-nowrap rounded-full px-[18px] text-[15px] tracking-[-0.01em] transition-colors ${
    on ? 'bg-[#F5F4F0] font-bold text-[#111111]' : 'border border-white/[0.22] font-medium text-[#E8E8EC] hover:border-white/45'
  }`;

function PuzzleCard({ p, tag }: { p: PuzzleSummary; tag?: string }) {
  return (
    <Link
      href={`/puzzles/${encodeURIComponent(p.id)}`}
      className="block rounded-[14px] border border-white/[0.16] bg-[#131316]/80 p-[18px] transition-colors hover:border-white/40"
    >
      <div className="flex items-center gap-[10px] font-mono text-[12px] uppercase tracking-[0.06em] text-[#9E9EA8]">
        {tag && <span className="rounded-full bg-[#E4002B]/20 px-[9px] py-[2px] text-[#ff8a9b]">{tag}</span>}
        <span>{p.source === 'pro' ? 'Pro moment' : 'Your game'}</span>
        <span className="ml-auto">{p.side}</span>
      </div>
      <h3 className="mt-[10px] text-[18px] font-bold leading-snug tracking-[-0.02em] text-white">{p.title}</h3>
      <p className="mt-[6px] text-[14px] text-[#B8B8C2]">
        Survive {p.window_seconds.toFixed(0)} s and get {p.need_kills} kill{p.need_kills === 1 ? '' : 's'} (the clip had {p.original.kills}).
      </p>
      <div className="mt-[12px] flex flex-wrap items-center gap-[8px] text-[13px]">
        <span className="rounded-full bg-white/[0.08] px-[10px] py-[2px] font-mono text-white">{p.rating}</span>
        <span className="text-[#B8B8C2]">{ratingBand(p.rating)}</span>
        {p.tags.map((t) => (
          <span key={t} className="rounded-full border border-white/[0.18] px-[9px] py-[1px] text-[12.5px] text-[#D8D8DE]">
            {t}
          </span>
        ))}
        <span className="ml-auto text-[#9E9EA8]">
          {p.solves}/{p.plays} solved · +{p.up} −{p.down}
        </span>
      </div>
    </Link>
  );
}

/** The puzzle library: daily puzzle, streak, filters, and the player's rating and history. */
export default function PuzzleLibrary() {
  const [name, setName] = useState('guest');
  const [me, setMe] = useState<PlayerStats | null>(null);
  const [history, setHistory] = useState<Attempt[]>([]);
  const [daily, setDaily] = useState<PuzzleSummary | null>(null);
  const [rows, setRows] = useState<PuzzleSummary[] | null>(null);
  const [tags, setTags] = useState<{ tag: string; count: number }[]>([]);
  const [tag, setTag] = useState('');
  const [source, setSource] = useState('');
  const [sort, setSort] = useState('rating');
  const [error, setError] = useState<string | null>(null);
  const [next, setNext] = useState<PuzzleSummary | null>(null);

  const load = useCallback(
    async (player: string) => {
      setError(null);
      try {
        const q = new URLSearchParams({ sort });
        if (tag) q.set('tag', tag);
        if (source) q.set('source', source);
        const [list, tg, stats, hist] = await Promise.all([
          call<PuzzleSummary[]>(`/puzzles?${q}`),
          call<{ tag: string; count: number }[]>('/puzzles/tags'),
          call<PlayerStats>(`/players/${encodeURIComponent(player)}`),
          call<Attempt[]>(`/players/${encodeURIComponent(player)}/history?limit=8`),
        ]);
        setRows(list);
        setTags(tg);
        setMe(stats);
        setHistory(hist);
        setDaily(await call<PuzzleSummary>('/puzzles/daily').catch(() => null));
        setNext(await call<PuzzleSummary>(`/puzzles/next?player=${encodeURIComponent(player)}`).catch(() => null));
      } catch (e) {
        setRows(null);
        setError(e instanceof Error ? e.message : 'Could not reach the match service');
      }
    },
    [tag, source, sort],
  );

  useEffect(() => {
    const n = getPlayerName();
    setName(n);
    load(n);
  }, [load]);

  const titleOf = (id: string) => rows?.find((r) => r.id === id)?.title ?? id;

  return (
    <div className="grid gap-[28px]">
      {error && (
        <p role="alert" className="rounded-[12px] border border-[#E4002B]/50 bg-[#E4002B]/10 p-[14px] text-[15px] text-[#ffb3be]">
          Could not load puzzles: {error}. Start the match service (<span className="font-mono">start-cs2.ps1</span>) and reload.
        </p>
      )}

      <section aria-label="Your rating" className="grid gap-[16px] rounded-[16px] border border-white/[0.16] bg-[#131316]/80 p-[22px] min-[900px]:grid-cols-[1.2fr_2fr]">
        <div>
          <p className="font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">Your rating</p>
          <p className="mt-[8px] text-[44px] font-extrabold leading-none tracking-[-0.04em] text-white">{me?.rating ?? '—'}</p>
          <label className="mt-[14px] flex items-center gap-[8px] text-[13.5px] text-[#B8B8C2]">
            Playing as
            <input
              value={name}
              maxLength={40}
              onChange={(e) => setName(e.target.value)}
              onBlur={() => {
                setPlayerName(name);
                load(name.trim() || 'guest');
              }}
              className="h-[34px] w-[150px] rounded-[8px] border border-white/[0.2] bg-transparent px-[10px] text-white"
            />
          </label>
        </div>
        <dl className="grid grid-cols-3 gap-[12px] text-center">
          {[
            ['Streak', me?.streak],
            ['Best streak', me?.best_streak],
            ['Solved', me ? `${me.solved}/${me.attempts}` : undefined],
          ].map(([label, v]) => (
            <div key={String(label)} className="rounded-[12px] bg-white/[0.04] p-[14px]">
              <dd className="text-[28px] font-bold tracking-[-0.03em] text-white">{v ?? '—'}</dd>
              <dt className="mt-[2px] text-[13px] text-[#9E9EA8]">{label}</dt>
            </div>
          ))}
        </dl>
      </section>

      <section className="grid gap-[16px] min-[900px]:grid-cols-2" aria-label="Start here">
        <div>
          <h2 className="mb-[10px] font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">Puzzle of the day</h2>
          {daily ? <PuzzleCard p={daily} tag="Daily" /> : <p className="text-[#9E9EA8]">No puzzles yet.</p>}
        </div>
        <div>
          <h2 className="mb-[10px] font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">Next for your rating</h2>
          {next ? <PuzzleCard p={next} tag={me && me.streak > 0 ? `Streak ${me.streak}` : 'Next'} /> : <p className="text-[#9E9EA8]">No puzzles yet.</p>}
        </div>
      </section>

      <section aria-label="All puzzles">
        <div className="flex flex-wrap items-center gap-[10px]">
          <button type="button" onClick={() => setTag('')} aria-pressed={!tag} className={chip(!tag)}>
            All themes
          </button>
          {tags.map((t) => (
            <button key={t.tag} type="button" aria-pressed={tag === t.tag} onClick={() => setTag(t.tag)} className={chip(tag === t.tag)}>
              {t.tag} <span className="ml-[6px] text-[12px] opacity-60">{t.count}</span>
            </button>
          ))}
          <span className="mx-[6px] h-[22px] w-px bg-white/[0.2]" aria-hidden />
          {[
            ['', 'All sources'],
            ['pro', 'Pro moments'],
            ['user', 'Your games'],
          ].map(([v, label]) => (
            <button key={v} type="button" aria-pressed={source === v} onClick={() => setSource(v)} className={chip(source === v)}>
              {label}
            </button>
          ))}
          <label className="ml-auto flex items-center gap-[8px] text-[14px] text-[#B8B8C2]">
            Sort
            <select value={sort} onChange={(e) => setSort(e.target.value)} className="h-[38px] rounded-[8px] border border-white/[0.2] bg-[#131316] px-[10px] text-white">
              <option value="rating">Difficulty</option>
              <option value="plays">Most played</option>
              <option value="votes">Top voted</option>
              <option value="new">Newest</option>
            </select>
          </label>
        </div>
        <div className="mt-[18px] grid gap-[14px] min-[900px]:grid-cols-2 min-[1280px]:grid-cols-3">
          {rows?.map((p) => <PuzzleCard key={p.id} p={p} />)}
        </div>
        {rows && rows.length === 0 && <p className="mt-[14px] text-[#9E9EA8]">No puzzles match this filter.</p>}
        {!rows && !error && <p className="mt-[14px] text-[#9E9EA8]">Loading…</p>}
      </section>

      <section aria-label="History">
        <h2 className="mb-[10px] font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">Your recent attempts</h2>
        {history.length === 0 ? (
          <p className="text-[#9E9EA8]">Nothing yet. Open a puzzle and play it.</p>
        ) : (
          <table className="w-full border-collapse text-left text-[15px] text-white">
            <thead>
              <tr className="border-b border-white/[0.15] font-mono text-[12.5px] uppercase tracking-[0.06em] text-[#9E9EA8]">
                <th className="pb-[10px] font-bold">Puzzle</th>
                <th className="pb-[10px] font-bold">Result</th>
                <th className="pb-[10px] font-bold">Kills</th>
                <th className="pb-[10px] text-right font-bold">Rating</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id} className="h-[44px] border-b border-white/[0.12]">
                  <td>
                    <Link href={`/puzzles/${encodeURIComponent(h.puzzle_id)}`} className="underline decoration-white/30 underline-offset-2">
                      {titleOf(h.puzzle_id)}
                    </Link>
                  </td>
                  <td className={h.solved ? 'text-[#7ee2a0]' : 'text-[#ff8a9b]'}>{h.solved ? 'Solved' : h.survived ? 'Survived, too few kills' : 'Died'}</td>
                  <td>{h.kills}</td>
                  <td className="text-right font-mono">
                    {Math.round(h.rating_after)} ({h.rating_after >= h.rating_before ? '+' : ''}
                    {Math.round(h.rating_after - h.rating_before)})
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
