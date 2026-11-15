'use client';

import Image, { type StaticImageData } from 'next/image';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import dust2 from '@/components/img/dust2.jpeg';
import inferno from '@/components/img/inferno.webp';
import mirage from '@/components/img/De_mirage_cs2.webp';
import { call, getPlayerName, ratingBand, setPlayerName, type Attempt, type PlayerStats, type PuzzleSummary } from '@/lib/puzzles';

/** Map picture and display name for a puzzle's map id (e.g. `de_mirage`). Unknown maps get a dark gradient. */
const MAPS: Record<string, { name: string; image: StaticImageData }> = {
  de_mirage: { name: 'Mirage', image: mirage },
  de_dust2: { name: 'Dust II', image: dust2 },
  de_inferno: { name: 'Inferno', image: inferno },
};
const mapOf = (id: string) => MAPS[id] ?? { name: id.replace(/^de_/, '').replace(/^\w/, (c) => c.toUpperCase()), image: undefined };

const card = 'rounded-[16px] border border-white/[0.14] bg-[#131316]';
const eyebrow = 'font-mono text-[13px] font-bold uppercase tracking-[0.1em] text-[#D8D8DE]';
const pill = (on: boolean) =>
  `flex h-[40px] cursor-pointer items-center whitespace-nowrap rounded-full px-[22px] text-[15px] tracking-[-0.01em] transition-colors ${
    on ? 'bg-[#F5F4F0] font-bold text-[#111111]' : 'border border-white/[0.22] font-medium text-[#E8E8EC] hover:border-white/45'
  }`;
const selectBox =
  'h-[40px] appearance-none rounded-[10px] border border-white/[0.2] bg-[#131316] pl-[16px] pr-[40px] text-[15px] font-medium text-white outline-none transition hover:border-white/45 focus:border-[#E4002B]';
/** Chevron for the custom selects (inline: Tailwind cannot build this data URL as a class). */
const chevron: React.CSSProperties = {
  backgroundImage:
    "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8'><path d='M1 1l5 5 5-5' fill='none' stroke='white' stroke-width='1.8'/></svg>\")",
  backgroundRepeat: 'no-repeat',
  backgroundPosition: 'right 15px center',
  backgroundSize: '12px 8px',
};
const Arrow = ({ size = 30 }: { size?: number }) => (
  <span className="grid shrink-0 place-items-center rounded-full bg-[#E4002B] text-white transition-transform group-hover:translate-x-0.5" style={{ width: size, height: size }} aria-hidden>
    <svg width={size * 0.5} height={size * 0.5} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 8h10M9 4l4 4-4 4" /></svg>
  </span>
);
/** Map picture filling its (positioned) parent, darkened toward the bottom for text. */
function MapArt({ map, sizes, priority = false }: { map: string; sizes: string; priority?: boolean }) {
  const m = mapOf(map);
  return (
    <>
      {m.image ? (
        <Image src={m.image} alt="" fill sizes={sizes} priority={priority} className="object-cover transition duration-700 group-hover:scale-[1.04]" />
      ) : (
        <span className="absolute inset-0 bg-[radial-gradient(120%_90%_at_30%_20%,#3a3a44_0%,#1c1c22_55%,#101014_100%)]" aria-hidden />
      )}
      <span className="absolute inset-0 bg-gradient-to-t from-[#0b0b0d] via-[#0b0b0d]/45 to-transparent" aria-hidden />
    </>
  );
}
const describe = (p: PuzzleSummary) =>
  `Survive ${p.window_seconds.toFixed(0)} s and get ${p.need_kills} kill${p.need_kills === 1 ? '' : 's'} (the clip had ${p.original.kills}).`;

/** Library card: map picture, title, meta line and the same stats as before. */
function PuzzleCard({ p, tag }: { p: PuzzleSummary; tag?: string }) {
  return (
    <Link href={`/puzzles/${encodeURIComponent(p.id)}`} className={`group relative block aspect-[16/7.6] min-h-[200px] overflow-hidden ${card} transition-colors hover:border-white/40`}>
      <MapArt map={p.map} sizes="(min-width: 1280px) 33vw, (min-width: 900px) 50vw, 100vw" />
      <div className="absolute inset-x-[16px] top-[14px] flex items-center gap-[8px] font-mono text-[11.5px] uppercase tracking-[0.06em]">
        {tag && <span className="rounded-[5px] bg-[#E4002B] px-[8px] py-[3px] font-bold text-white">{tag}</span>}
        <span className="rounded-[5px] bg-black/55 px-[8px] py-[3px] text-[#E8E8EC] backdrop-blur-sm">{p.source === 'pro' ? 'Pro moment' : 'Your game'}</span>
        <span className="rounded-[5px] bg-black/55 px-[8px] py-[3px] text-[#E8E8EC] backdrop-blur-sm">{p.side}</span>
        <span className="ml-auto rounded-[5px] bg-black/55 px-[8px] py-[3px] text-[#E8E8EC] backdrop-blur-sm">
          {p.solves}/{p.plays} solved · +{p.up} −{p.down}
        </span>
      </div>
      <div className="absolute inset-x-[20px] bottom-[16px] flex items-end gap-[12px]">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-[23px] font-extrabold leading-tight tracking-[-0.025em] text-white">{p.title}</h3>
          <p className="mt-[4px] truncate text-[14.5px] text-[#C8C8D0]">
            {mapOf(p.map).name}
            {p.tags.map((t) => (
              <span key={t}> · {t}</span>
            ))}
            <span className="text-white"> · {ratingBand(p.rating)}</span>
            <span className="font-mono text-[13px] text-[#9E9EA8]"> · {p.rating}</span>
          </p>
          <p className="mt-[3px] truncate text-[13px] text-[#9E9EA8]">{describe(p)}</p>
        </div>
        <Arrow />
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
  const unrated = !me || me.attempts === 0;

  return (
    <div className="grid gap-[30px]">
      {error && (
        <p role="alert" className="flex items-center gap-[10px] rounded-[12px] border border-[#E4002B]/40 bg-[#E4002B]/[0.08] px-[16px] py-[12px] text-[14.5px] text-[#ffb3be]">
          <span className="h-[8px] w-[8px] shrink-0 rounded-full bg-[#E4002B]" aria-hidden />
          <span>
            Could not load puzzles: {error}. Start the match service (<span className="font-mono">start-cs2.ps1</span>) and reload.
          </span>
        </p>
      )}

      <div className="grid gap-[18px] min-[1100px]:grid-cols-[minmax(0,1.95fr)_minmax(0,1fr)]">
        {/* Puzzle of the day */}
        <section aria-label="Puzzle of the day" className={`group relative min-h-[400px] overflow-hidden ${card}`}>
          {daily ? (
            <Link href={`/puzzles/${encodeURIComponent(daily.id)}`} className="absolute inset-0" aria-label={`Play puzzle of the day: ${daily.title}`}>
              <MapArt map={daily.map} sizes="(min-width: 1100px) 64vw, 100vw" priority />
            </Link>
          ) : (
            <span className="absolute inset-0 bg-[radial-gradient(110%_90%_at_70%_10%,#2a2a33_0%,#151519_55%,#0f0f12_100%)]" aria-hidden />
          )}
          <span className="pointer-events-none absolute left-[24px] top-[22px] rounded-[5px] bg-[#E4002B] px-[12px] py-[6px] font-mono text-[13px] font-bold uppercase tracking-[0.1em] text-white">
            Puzzle of the day
          </span>
          <div className="pointer-events-none absolute inset-x-[26px] bottom-[24px]">
            {daily ? (
              <>
                <h2 className="text-[clamp(28px,2.8vw,40px)] font-extrabold leading-[1.05] tracking-[-0.03em] text-white">{daily.title}</h2>
                <div className="mt-[12px] flex flex-wrap gap-[8px] text-[14px] text-white">
                  {[mapOf(daily.map).name, daily.source === 'pro' ? 'Pro moment' : 'Your game', daily.side, ...daily.tags, ratingBand(daily.rating)].map((t, i) => (
                    <span key={`${t}-${i}`} className="rounded-full border border-white/40 bg-black/35 px-[14px] py-[4px] backdrop-blur-sm">
                      {t}
                    </span>
                  ))}
                </div>
                <p className="mt-[12px] text-[16px] text-[#D8D8DE]">{describe(daily)}</p>
                <span className="mt-[16px] inline-flex h-[46px] items-center gap-[14px] rounded-full bg-white pl-[24px] pr-[8px] text-[16px] font-bold text-black">
                  Play puzzle <Arrow />
                </span>
              </>
            ) : (
              <>
                <h2 className="text-[clamp(26px,2.6vw,36px)] font-extrabold leading-[1.05] tracking-[-0.03em] text-white">No puzzles yet.</h2>
                <p className="mt-[10px] text-[16px] text-[#B8B8C2]">The daily puzzle appears here once the match service has puzzles.</p>
              </>
            )}
          </div>
        </section>

        <div className="grid gap-[18px]">
          {/* Your rating */}
          <section aria-label="Your rating" className={`${card} p-[24px]`}>
            <p className={eyebrow}>Your rating</p>
            <p className="mt-[6px] text-[40px] font-extrabold leading-none tracking-[-0.04em] text-white">{me ? (unrated ? 'Unrated' : me.rating) : '—'}</p>
            <label className="mt-[12px] flex items-center gap-[10px] text-[14px] text-[#B8B8C2]">
              Playing as
              <input
                value={name}
                maxLength={40}
                onChange={(e) => setName(e.target.value)}
                onBlur={() => {
                  setPlayerName(name);
                  load(name.trim() || 'guest');
                }}
                className="h-[34px] w-[160px] rounded-[8px] border border-white/[0.2] bg-transparent px-[10px] text-white outline-none transition focus:border-[#E4002B]"
              />
            </label>
            <dl className="mt-[18px] grid grid-cols-3 divide-x divide-white/[0.14] text-center">
              {[
                ['Streak', me?.streak],
                ['Best streak', me?.best_streak],
                ['Solved', me ? `${me.solved}/${me.attempts}` : undefined],
              ].map(([label, v]) => (
                <div key={String(label)} className="flex flex-col-reverse px-[8px]">
                  <dt className="mt-[2px] text-[14px] text-[#B8B8C2]">{label}</dt>
                  <dd className="text-[28px] font-extrabold leading-tight tracking-[-0.03em] text-white">{v ?? '—'}</dd>
                </div>
              ))}
            </dl>
          </section>

          {/* Next for your rating */}
          <section aria-label="Next for your rating" className={`${card} flex flex-col p-[24px]`}>
            <p className={eyebrow}>Next for your rating</p>
            {next ? (
              <>
                <p className="mt-[8px] text-[26px] font-extrabold leading-tight tracking-[-0.03em] text-white">{next.title}</p>
                <p className="mt-[6px] text-[15px] text-[#B8B8C2]">
                  {mapOf(next.map).name} · {ratingBand(next.rating)} · {next.rating}
                  {me && me.streak > 0 ? ` · Streak ${me.streak}` : ''}
                </p>
                <p className="mt-[4px] text-[14px] text-[#9E9EA8]">{describe(next)}</p>
                <Link href={`/puzzles/${encodeURIComponent(next.id)}`} className="mt-auto inline-flex w-fit items-center gap-[6px] pt-[16px] text-[16px] font-bold text-[#ff2a4b] hover:text-[#ff5c76]">
                  Play this puzzle <span aria-hidden>↗</span>
                </Link>
              </>
            ) : (
              <p className="mt-[8px] text-[16px] text-[#9E9EA8]">No puzzles yet.</p>
            )}
          </section>
        </div>
      </div>

      {/* Library */}
      <section aria-label="All puzzles">
        <h2 className="text-[30px] font-extrabold tracking-[-0.03em] text-white">Puzzle library</h2>
        <div className="mt-[16px] flex flex-wrap items-center gap-[12px]">
          <select aria-label="Theme" style={chevron} className={selectBox} value={tag} onChange={(e) => setTag(e.target.value)}>
            <option value="">Theme: All</option>
            {tags.map((t) => (
              <option key={t.tag} value={t.tag}>
                Theme: {t.tag} ({t.count})
              </option>
            ))}
          </select>
          <span className="mx-[4px] h-[24px] w-px bg-white/[0.2]" aria-hidden />
          {[
            ['', 'All sources'],
            ['pro', 'Pro moments'],
            ['user', 'Your games'],
          ].map(([v, label]) => (
            <button key={v} type="button" aria-pressed={source === v} onClick={() => setSource(v)} className={pill(source === v)}>
              {label}
            </button>
          ))}
          <label className="ml-auto flex items-center gap-[10px] text-[14px] text-[#B8B8C2]">
            Sort
            <select value={sort} onChange={(e) => setSort(e.target.value)} style={chevron} className={selectBox}>
              <option value="rating">Difficulty</option>
              <option value="plays">Most played</option>
              <option value="votes">Top voted</option>
              <option value="new">Newest</option>
            </select>
          </label>
        </div>
        <div className="mt-[18px] grid gap-[16px] min-[900px]:grid-cols-2 min-[1280px]:grid-cols-3">
          {rows?.map((p) => <PuzzleCard key={p.id} p={p} />)}
        </div>
        {rows && rows.length === 0 && <p className="mt-[14px] text-[#9E9EA8]">No puzzles match this filter.</p>}
        {!rows && !error && <p className="mt-[14px] text-[#9E9EA8]">Loading…</p>}
        {!rows && error && <p className="mt-[14px] text-[#9E9EA8]">Puzzles appear here once the match service is running.</p>}
      </section>

      {/* History */}
      <section aria-label="History" className="border-t border-white/[0.15] pt-[22px]">
        <div className="flex flex-wrap items-center gap-x-[18px] gap-y-[6px]">
          <h2 className="text-[24px] font-extrabold tracking-[-0.025em] text-white">Recent attempts</h2>
          {history.length === 0 && (
            <>
              <span className="h-[26px] w-px bg-white/[0.2]" aria-hidden />
              <p className="text-[16px] text-[#B8B8C2]">Nothing yet. Open a puzzle and play it.</p>
            </>
          )}
        </div>
        {history.length > 0 && (
          <div className={`${card} mt-[14px] overflow-x-auto px-[20px] py-[6px]`}>
            <table className="w-full border-collapse text-left text-[15px] text-white">
              <thead>
                <tr className="border-b border-white/[0.15] font-mono text-[12.5px] uppercase tracking-[0.08em] text-[#9E9EA8]">
                  <th className="py-[12px] font-bold">Puzzle</th>
                  <th className="py-[12px] font-bold">Result</th>
                  <th className="py-[12px] font-bold">Kills</th>
                  <th className="py-[12px] text-right font-bold">Rating</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id} className="h-[48px] border-b border-white/[0.08] last:border-0">
                    <td>
                      <Link href={`/puzzles/${encodeURIComponent(h.puzzle_id)}`} className="font-semibold hover:text-[#ff5c76]">
                        {titleOf(h.puzzle_id)}
                      </Link>
                    </td>
                    <td>
                      <span className={`inline-flex items-center gap-[7px] ${h.solved ? 'text-[#7ee2a0]' : 'text-[#ff8a9b]'}`}>
                        <span className={`h-[7px] w-[7px] rounded-full ${h.solved ? 'bg-[#7ee2a0]' : 'bg-[#ff8a9b]'}`} aria-hidden />
                        {h.solved ? 'Solved' : h.survived ? 'Survived, too few kills' : 'Died'}
                      </span>
                    </td>
                    <td>{h.kills}</td>
                    <td className="text-right font-mono">
                      {Math.round(h.rating_after)}{' '}
                      <span className={h.rating_after >= h.rating_before ? 'text-[#7ee2a0]' : 'text-[#ff8a9b]'}>
                        ({h.rating_after >= h.rating_before ? '+' : ''}
                        {Math.round(h.rating_after - h.rating_before)})
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
