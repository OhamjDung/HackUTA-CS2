'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { call, getPlayerName, type DeathDetail } from '@/lib/puzzles';
import FeedbackList from './FeedbackList';

const SEEN_KEY = 'doppelgamer.lastDeathSeen';
const POLL_MS = 2000;
const IDLE_POLL_MS = 5000;  // slower while there is no service or no death yet

/**
 * Shows the key mistakes the moment a human dies in CS2. CloneDirector saves each death as a file; the
 * service lists it at /deaths/latest. The first poll only remembers the newest death, so an old one does
 * not pop up when the page opens. Silent when the service or the game is not running.
 */
export default function DeathWatcher() {
  const [death, setDeath] = useState<DeathDetail | null>(null);
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    let stop = false;
    let first = true;
    let timer: ReturnType<typeof setTimeout>;
    const seen = () => {
      try {
        return window.sessionStorage.getItem(SEEN_KEY);
      } catch {
        return null;
      }
    };
    const poll = async () => {
      let delay = IDLE_POLL_MS;
      try {
        const latest = await call<DeathDetail>('/deaths/latest');
        if (stop) return;
        delay = POLL_MS;
        if (first && seen() === null) {
          window.sessionStorage.setItem(SEEN_KEY, latest.id);  // an old death: remember it, do not show it
        } else if (latest.id !== seen()) {
          window.sessionStorage.setItem(SEEN_KEY, latest.id);
          setDeath(latest);
          setNote(null);
          setOpen(true);
        }
      } catch {
        /* no service, or no deaths yet */
      }
      first = false;
      if (!stop) timer = setTimeout(poll, delay);
    };
    poll();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  if (!death || !open) return null;
  const hero = death.puzzle.players.find((p) => p.hero);
  const killer = death.puzzle.events.find((e) => e.type === 'kill' && e.victim === hero?.name);

  return (
    <aside
      role="dialog"
      aria-label="What went wrong"
      className="fixed bottom-[20px] right-[20px] z-50 w-[min(440px,calc(100vw-40px))] rounded-[16px] border border-white/[0.2] bg-[#131316] p-[22px] shadow-[0_24px_60px_-20px_rgba(0,0,0,0.9)]"
    >
      <div className="flex items-start gap-[12px]">
        <div>
          <p className="font-mono text-[12.5px] font-bold uppercase tracking-[0.1em] text-[#ff8a9b]">You died</p>
          <h2 className="mt-[4px] text-[20px] font-extrabold tracking-[-0.02em] text-white">
            {killer?.attacker ? `${killer.attacker} got you` : 'Key mistakes'}
            {killer?.weapon ? <span className="font-medium text-[#9E9EA8]"> · {killer.weapon}</span> : null}
          </h2>
        </div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          aria-label="Close"
          className="ml-auto flex h-[34px] w-[34px] cursor-pointer items-center justify-center rounded-full bg-white/[0.1] text-white hover:bg-white/[0.2]"
        >
          ×
        </button>
      </div>
      <div className="mt-[14px]">
        <FeedbackList items={death.feedback} />
      </div>
      <div className="mt-[16px] flex flex-wrap gap-[10px]">
        <Link
          href={`/puzzles?tab=create&death=${encodeURIComponent(death.id)}`}
          className="flex h-[40px] items-center rounded-full bg-[#F5F4F0] px-[18px] text-[15px] font-bold text-[#111111]"
        >
          Save as puzzle
        </Link>
        <button
          type="button"
          onClick={() =>
            call(`/deaths/${encodeURIComponent(death.id)}/start`, { method: 'POST', json: { player: getPlayerName() } })
              .then(() => setNote({ ok: true, text: 'Loaded in CS2. Switch to the game and try it again.' }))
              .catch((e) => setNote({ ok: false, text: e instanceof Error ? e.message : String(e) }))
          }
          className="flex h-[40px] cursor-pointer items-center rounded-full border border-white/[0.25] px-[18px] text-[15px] font-medium text-white hover:border-white/50"
        >
          Retry last 10 s
        </button>
      </div>
      {note && (
        <p role="status" className={`mt-[12px] text-[14px] ${note.ok ? 'text-[#7ee2a0]' : 'text-[#ff8a9b]'}`}>
          {note.text}
        </p>
      )}
    </aside>
  );
}
