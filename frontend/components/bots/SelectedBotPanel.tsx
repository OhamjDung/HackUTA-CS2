'use client';

import Link from 'next/link';
import type { Bot } from '@/lib/bots';
import { ArrowUpRight } from '@/components/ui/icons';

interface SelectedBotPanelProps {
  bot: Bot;
  /** 1-based roster position of the shown bot. */
  index: number;
  glitching: boolean;
  onPlay: () => void;
}

/** Right column: "03 / SELECTED BOT", name, tagline, chips, Play bot, Try a scene. */
export default function SelectedBotPanel({ bot, index, glitching, onPlay }: SelectedBotPanelProps) {
  return (
    <div data-right-col>
      <p className="font-mono text-[16px] font-bold uppercase leading-none tracking-[0.06em] text-[#E4E4E8] [word-spacing:-0.3em]">
        {String(index).padStart(2, '0')} / Selected bot
      </p>

      <h2
        key={bot.id}
        className={`mt-[22px] text-[clamp(3.6rem,5.2vw,5rem)] font-extrabold leading-[0.98] tracking-[-0.045em] text-white ${
          glitching ? 'hud-flicker' : ''
        }`}
        aria-live="polite"
      >
        {bot.name}
      </h2>
      <p className="mt-[16px] text-[20px] leading-tight tracking-[-0.01em] text-[#B8B8C2]">
        {bot.game} · Player-inspired bot
      </p>
      <p className="mt-[22px] text-[20px] leading-tight tracking-[-0.01em] text-[#B8B8C2]">
        Your next challenger is ready.
      </p>

      <ul className="mt-[22px] flex flex-wrap gap-[16px]" aria-label="Playstyle">
        {bot.tags.map((t) => (
          <li
            key={t}
            className="flex h-[38px] items-center rounded-full border border-white/[0.22] bg-transparent px-[27px] text-[16.5px] font-medium tracking-[-0.01em] text-[#E8E8EC] transition-colors hover:border-white/45"
          >
            {t}
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={onPlay}
        className="group mt-[38px] flex h-[62px] w-[256px] cursor-pointer items-center justify-between rounded-full bg-gradient-to-b from-[#FFFFFF] via-[#F5F4F0] to-[#E5E4DF] pl-[70px] pr-[10px] text-[21px] font-bold tracking-[-0.01em] text-[#111111] shadow-[0_6px_20px_rgba(0,0,0,0.45),inset_0_1px_0_#FFFFFF] transition-[filter] hover:brightness-[1.04]"
      >
        Play bot
        <span className="flex h-[42px] w-[42px] items-center justify-center rounded-full bg-brand transition-transform group-hover:translate-x-0.5">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
            <path d="M3 9h11M10 4.5 14.5 9 10 13.5" stroke="white" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </button>

      <Link
        href={`/scenes?bot=${bot.id}`}
        className="mt-[26px] inline-flex items-center gap-[8px] border-b-[1.5px] border-ink pb-[3px] text-[18.5px] font-medium leading-none tracking-[-0.01em] text-ink"
      >
        Try a scene
        <ArrowUpRight size={17} strokeWidth={1.8} />
      </Link>
    </div>
  );
}
