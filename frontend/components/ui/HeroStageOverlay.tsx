'use client';

import ModeLink from '@/components/mode/ModeLink';
import { DEMO_URL } from '@/lib/constants';
import type { CharacterConfig, CharacterId } from '@/types';
import { ArrowUpRight } from './icons';
import HeroSign from './HeroSign';

interface HeroStageOverlayProps {
  characters: CharacterConfig[];
  /** Character whose label is shown (switches at the glitch midpoint). */
  shownId: CharacterId;
  /** Character the segment bar points at (switches immediately on trigger). */
  targetId: CharacterId;
  glitching: boolean;
  thermalActive: boolean;
  onSelect: (id: CharacterId) => void;
}

/**
 * Left headline + right stage HUD. The wrapper is pointer-transparent so
 * clicks fall through to the stage ("Hold left click to scan."); only the
 * controls themselves take pointer events.
 */
export default function HeroStageOverlay({
  characters,
  shownId,
  targetId,
  glitching,
  thermalActive,
  onSelect,
}: HeroStageOverlayProps) {
  const shownIndex = characters.findIndex((c) => c.id === shownId);
  const shown = characters[shownIndex];

  return (
    <div className="pointer-events-none relative z-20 flex flex-col gap-10 px-[var(--gutter)] pb-12 min-[900px]:absolute min-[900px]:inset-0 min-[900px]:block min-[900px]:p-0">
      {/* Brand lockup: DoppelGamer sign, tagline, then the two calls to action. */}
      <div
        data-headline
        className="hero-lockup order-2 min-[900px]:absolute min-[900px]:left-[var(--gutter)] min-[900px]:top-[50%] min-[900px]:-translate-y-1/2"
      >
        <h1 className="contents">
          <HeroSign />
          <span className="lockup-tagline headline-accent">Clone anyone on any game.</span>
        </h1>

        <div className="lockup-actions pointer-events-auto flex flex-wrap justify-center gap-[14px]">
          <ModeLink
            href="/bots"
            className="group flex h-[48px] shrink-0 items-center gap-[12px] whitespace-nowrap rounded-full bg-[#F5F4F0] pl-[21px] pr-[6px] text-[16px] font-bold tracking-[-0.01em] text-[#111111] transition-colors hover:bg-white"
          >
            Choose your bot
            <span className="cta-arrow flex h-[36px] w-[36px] items-center justify-center rounded-full transition-transform group-hover:rotate-45">
              <ArrowUpRight size={16} strokeWidth={2} />
            </span>
          </ModeLink>
          <a
            href={DEMO_URL}
            className="flex h-[48px] shrink-0 items-center gap-[16px] whitespace-nowrap rounded-full border border-outline bg-black/20 pl-[20px] pr-[19px] text-[16px] font-medium tracking-[-0.01em] text-ink backdrop-blur-sm transition-colors hover:border-ink"
          >
            Watch demo
            <ArrowUpRight size={18} strokeWidth={1.8} />
          </a>
        </div>
      </div>

      {/* Character switcher: centred directly under the character. */}
      <div
        data-hud
        className="order-1 -mt-4 flex flex-wrap items-center justify-center gap-x-[22px] gap-y-[12px] min-[900px]:absolute min-[900px]:mt-0 min-[900px]:bottom-[clamp(36px,4.8vh,50px)] min-[900px]:left-[calc(var(--anchor-x,0.7)*100%)] min-[900px]:w-max min-[900px]:-translate-x-1/2 min-[900px]:flex-nowrap"
      >
        <p
          key={shownId}
          className={`hud-tint min-w-[11ch] font-mono text-[16px] font-semibold leading-none tracking-[0.02em] ${glitching ? 'hud-flicker' : ''}`}
          aria-live="polite"
        >
          0{shownIndex + 1} / {shown.displayName.toUpperCase()}
        </p>

        <div className="pointer-events-auto flex gap-[8px]" role="tablist" aria-label="Characters">
          {characters.map((c, i) => {
            const active = c.id === targetId;
            return (
              <button
                key={c.id}
                type="button"
                role="tab"
                aria-selected={active}
                aria-label={`0${i + 1} ${c.displayName}`}
                onClick={() => onSelect(c.id)}
                className="group flex h-4 cursor-pointer items-center"
              >
                <span
                  className={`block h-[5px] w-[22px] rounded-full transition-colors duration-300 ${
                    active ? 'seg-active' : 'bg-pill group-hover:bg-ink-subtle'
                  }`}
                />
              </button>
            );
          })}
        </div>

        <p className="whitespace-nowrap text-[14px] leading-none tracking-[-0.005em] text-ink-subtle">
          {thermalActive ? 'Scanning — release to close' : 'Hold left click to scan.'}
        </p>
      </div>
    </div>
  );
}
