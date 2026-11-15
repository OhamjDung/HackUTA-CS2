'use client';

import ModeLink from '@/components/mode/ModeLink';
import { DEMO_URL } from '@/lib/constants';
import type { CharacterConfig, CharacterId } from '@/types';
import { ArrowUpRight } from './icons';

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
      {/* Display wordmark: fills the open space above the headline. */}
      <p
        aria-hidden
        className="hero-wordmark led-wordmark order-first min-[900px]:absolute min-[900px]:left-[var(--gutter)] min-[900px]:top-[clamp(150px,34%,360px)]"
      >
        DoppelGamer
      </p>

      {/* Headline */}
      <h1
        data-headline
        className="headline text-ink min-[900px]:absolute min-[900px]:bottom-[clamp(32px,4.1vw,64px)] min-[900px]:left-[var(--gutter)]"
      >
        <span className="headline-accent block">
          Clone anyone
          <br />
          on any game.
        </span>
      </h1>

      {/* Right HUD column */}
      <div data-hud className="flex flex-col gap-10 min-[900px]:absolute min-[900px]:bottom-[clamp(40px,4.9vw,75px)] min-[900px]:right-[clamp(40px,3.1vw,48px)] min-[900px]:top-[clamp(120px,23.5%,180px)] min-[900px]:w-[max(24rem,25.2vw)] min-[900px]:justify-between min-[900px]:gap-0">
        <div className="min-[900px]:pl-[7px]">
          <p
            key={shownId}
            className={`hud-tint font-mono text-[18px] font-semibold leading-none tracking-[0.02em] ${glitching ? 'hud-flicker' : ''}`}
            aria-live="polite"
          >
            0{shownIndex + 1} / {shown.displayName.toUpperCase()}
          </p>

          <div className="pointer-events-auto mt-[19px] flex gap-[8px]" role="tablist" aria-label="Characters">
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

          <p className="mt-[15px] text-[15px] leading-none tracking-[-0.005em] text-ink-subtle">
            {thermalActive ? 'Scanning — release to close' : 'Hold left click to scan.'}
          </p>
        </div>

        <div>
          <p className="max-w-[20ch] text-[clamp(20px,1.62vw,25px)] leading-[1.33] tracking-[-0.012em] text-ink-muted min-[900px]:pl-[7px]">
            A mixed-reality co-host. Built for your next great moment.
          </p>

          <div className="pointer-events-auto mt-[42px] flex flex-wrap gap-[14px] min-[900px]:flex-nowrap">
            <ModeLink
              href="/bots"
              className="group flex h-[48px] shrink-0 items-center gap-[12px] whitespace-nowrap rounded-full bg-[#F5F4F0] pl-[21px] pr-[6px] text-[16px] font-bold tracking-[-0.01em] text-[#111111] transition-colors hover:bg-white"
            >
              Choose your bot
              <span className="flex h-[36px] w-[36px] items-center justify-center rounded-full bg-brand text-white transition-transform group-hover:rotate-45">
                <ArrowUpRight size={16} strokeWidth={2} />
              </span>
            </ModeLink>
            <a
              href={DEMO_URL}
              className="flex h-[48px] shrink-0 items-center gap-[16px] whitespace-nowrap rounded-full border border-outline bg-transparent pl-[20px] pr-[19px] text-[16px] font-medium tracking-[-0.01em] text-ink transition-colors hover:border-ink"
            >
              Watch demo
              <ArrowUpRight size={18} strokeWidth={1.8} />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
