'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { call, getPlayerName, ratingBand, type AttemptResult, type PuzzleDetail } from '@/lib/puzzles';
import FeedbackList from './FeedbackList';
import MapReplay from './MapReplay';

const pill = 'flex h-[42px] cursor-pointer items-center justify-center rounded-full px-[22px] text-[15.5px] font-bold disabled:cursor-not-allowed disabled:opacity-50';

/** One puzzle: watch the original clip, practice it in CS2, log the result, vote. */
export default function PuzzlePractice({ id }: { id: string }) {
  const [p, setP] = useState<PuzzleDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [survived, setSurvived] = useState(true);
  const [kills, setKills] = useState(1);
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [automatic, setAutomatic] = useState<AttemptResult | null>(null);
  const [watch, setWatch] = useState<string | null>(null);

  const load = () =>
    call<PuzzleDetail>(`/puzzles/${encodeURIComponent(id)}`)
      .then(setP)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!watch) return;
    let stopped = false;
    const poll = async () => {
      try {
        const state = await call<{ state: 'pending' | 'finished' | 'cancelled'; result?: AttemptResult; reason?: string }>(`/puzzle-attempts/${encodeURIComponent(watch)}`);
        // Starting a match, puzzle or scene in CS2 ends this attempt (the service replaces what is running).
        if (!stopped && state.state === 'cancelled') {
          setWatch(null);
          setStatus({ ok: false, text: `This attempt was stopped: ${state.reason ?? 'something new started in CS2'}.` });
        }
        if (!stopped && state.state === 'finished' && state.result) {
          setAutomatic(state.result);
          setWatch(null);
          setStatus({ ok: true, text: 'Result received from CS2.' });
          load();
        }
      } catch {
        if (!stopped) setStatus({ ok: false, text: 'Waiting for the result; the match service could not be reached.' });
      }
    };
    const timer = window.setInterval(poll, 2000);
    const timeout = window.setTimeout(() => {
      setWatch(null);
      setStatus({ ok: false, text: 'No result arrived within two minutes. Check CS2 and CloneDirector, then try again.' });
    }, 120000);
    return () => { stopped = true; window.clearInterval(timer); window.clearTimeout(timeout); };
    // load is intentionally not a dependency: polling belongs to the active attempt.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, watch]);

  if (error) {
    return (
      <p role="alert" className="rounded-[12px] border border-[#E4002B]/50 bg-[#E4002B]/10 p-[14px] text-[15px] text-[#ffb3be]">
        {error}. <Link href="/puzzles" className="underline">Back to puzzles</Link>
      </p>
    );
  }
  if (!p) return <p className="text-[#9E9EA8]">Loading…</p>;

  const player = getPlayerName();
  const act = async (fn: () => Promise<void>) => {
    setBusy(true);
    setStatus(null);
    try {
      await fn();
    } catch (e) {
      setStatus({ ok: false, text: e instanceof Error ? e.message : String(e) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-[28px] min-[1024px]:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
      <section aria-label="Replay of the original clip">
        <MapReplay puzzle={p.puzzle} mistakes={p.feedback} />
        <p className="mt-[14px] text-[13.5px] text-[#9E9EA8]">
          Blue is CT, orange is T, the white ring is you ({p.hero}). A cross is a death. This is the clip as it happened;
          a white circle around a player means that player fired.
        </p>
      </section>

      <section className="grid content-start gap-[22px]" aria-label="Practice">
        <div>
          <p className="font-mono text-[12.5px] uppercase tracking-[0.08em] text-[#9E9EA8]">
            {p.source === 'pro' ? 'Pro moment' : 'Your game'} · {p.map} · {p.side} · {ratingBand(p.rating)} {p.rating}
          </p>
          <h2 className="mt-[6px] text-[26px] font-extrabold leading-tight tracking-[-0.03em] text-white">{p.title}</h2>
          <p className="mt-[10px] text-[16px] leading-snug text-[#D8D8DE]">
            <b>Goal:</b> do not die for {p.window_seconds.toFixed(0)} seconds and get at least {p.need_kills} kill{p.need_kills === 1 ? '' : 's'}.
            In the original, {p.hero} got {p.original.kills} and was killed by {p.original.killer ?? 'someone'}
            {p.original.weapon ? ` (${p.original.weapon})` : ''}. The other players repeat their recorded moves, so the same
            moment comes back each try.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-[12px]">
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              act(async () => {
                setWatch(null);
                setAutomatic(null);
                setResult(null);
                const started = await call<{ attempt_id: string }>(`/puzzles/${encodeURIComponent(id)}/start`, { method: 'POST', json: { player } });
                setWatch(started.attempt_id);
                setStatus({ ok: true, text: 'Sent to CS2. Switch to the game; the result will appear here when the attempt finishes.' });
              })
            }
            className={`${pill} bg-[#E4002B] text-white hover:bg-[#ff1a44]`}
          >
            Practice in CS2
          </button>
          <span className="text-[13.5px] text-[#9E9EA8]">Needs CS2 running with CloneDirector.</span>
        </div>
        {status && (
          <p role="status" className={`text-[14.5px] ${status.ok ? 'text-[#7ee2a0]' : 'text-[#ff8a9b]'}`}>
            {status.text}
          </p>
        )}

        {automatic && (
          <p role="status" className={`rounded-[12px] border border-white/[0.16] p-[14px] text-[15px] ${automatic.solved ? 'text-[#7ee2a0]' : 'text-[#ff8a9b]'}`}>
            {automatic.solved ? 'Solved.' : automatic.survived ? `Not solved: survived with ${automatic.kills} of ${p.need_kills} required kills.` : 'Not solved: you died.'}
            {' '}Rating {automatic.player.rating} ({automatic.rating_change >= 0 ? '+' : ''}{automatic.rating_change}).
          </p>
        )}

        <div>
          <h3 className="mb-[10px] font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">What went wrong in the clip</h3>
          <FeedbackList items={p.feedback} empty="The original player survived, or no clear mistake was found." />
        </div>

        <form
          className="rounded-[14px] border border-white/[0.16] bg-[#131316]/80 p-[18px]"
          onSubmit={(e) => {
            e.preventDefault();
            act(async () => {
              const r = await call<AttemptResult>(`/puzzles/${encodeURIComponent(id)}/result`, { method: 'POST', json: { player, survived, kills } });
              setWatch(null);
              setAutomatic(null);
              setResult(r);
              load();
            });
          }}
        >
          <h3 className="font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">Log an attempt</h3>
          <p className="mt-[6px] text-[13.5px] text-[#9E9EA8]">
            CS2 reports your result itself when it is connected. If it was not, enter what happened.
          </p>
          <div className="mt-[12px] flex flex-wrap items-center gap-[16px] text-[15px] text-white">
            <label className="flex items-center gap-[8px]">
              <input type="checkbox" checked={survived} onChange={(e) => setSurvived(e.target.checked)} className="h-[18px] w-[18px] accent-[#E4002B]" />
              I survived
            </label>
            <label className="flex items-center gap-[8px]">
              Kills
              <input
                type="number"
                min={0}
                max={30}
                value={kills}
                onChange={(e) => setKills(Math.max(0, Math.min(30, Number(e.target.value) || 0)))}
                className="h-[36px] w-[70px] rounded-[8px] border border-white/[0.2] bg-transparent px-[10px]"
              />
            </label>
            <button type="submit" disabled={busy} className={`${pill} h-[38px] bg-[#F5F4F0] text-[#111111]`}>
              Save attempt
            </button>
          </div>
          {result && (
            <p role="status" className={`mt-[12px] text-[15px] ${result.solved ? 'text-[#7ee2a0]' : 'text-[#ff8a9b]'}`}>
              {result.solved ? 'Solved. ' : result.survived ? `Survived, but you needed ${result.need_kills} kills. ` : 'Not solved. '}
              Rating {result.player.rating} ({result.rating_change >= 0 ? '+' : ''}
              {result.rating_change}) · streak {result.player.streak}
            </p>
          )}
        </form>

        <div className="flex flex-wrap items-center gap-[10px] text-[14.5px] text-[#B8B8C2]">
          <span>Was this a good puzzle?</span>
          {[
            [1, `Yes (${p.up})`],
            [-1, `No (${p.down})`],
          ].map(([v, label]) => (
            <button
              key={String(v)}
              type="button"
              disabled={busy}
              onClick={() => act(async () => { await call(`/puzzles/${encodeURIComponent(id)}/vote`, { method: 'POST', json: { player, value: v } }); await load(); })}
              className="h-[34px] cursor-pointer rounded-full border border-white/[0.22] px-[14px] text-white hover:border-white/50 disabled:opacity-50"
            >
              {label}
            </button>
          ))}
          {p.source === 'user' && (
            <button
              type="button"
              disabled={busy}
              onClick={() => act(async () => { await call(`/puzzles/${encodeURIComponent(id)}`, { method: 'DELETE' }); location.assign('/puzzles'); })}
              className="ml-auto h-[34px] cursor-pointer rounded-full border border-[#E4002B]/50 px-[14px] text-[#ff8a9b] hover:bg-[#E4002B]/10"
            >
              Delete puzzle
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
