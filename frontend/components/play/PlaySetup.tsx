'use client';

import ModeLink from '@/components/mode/ModeLink';
import { useEffect } from 'react';
import { useBotSelection, useBrand } from '@/app/providers';
import { Avatar } from '@/components/bots/RosterArc';
import { BOTS, CURATED_SCENES } from '@/lib/bots';

const arrow = (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
    <path d="M3 9h11M10 4.5 14.5 9 10 13.5" stroke="white" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

/** Match setup: bot preselected from ?bot= (or the shared selection), scene from ?scene=. */
export default function PlaySetup({ botParam, sceneParam }: { botParam?: string; sceneParam?: string }) {
  const { selectedId, setSelectedId } = useBotSelection();
  const brand = useBrand();

  useEffect(() => {
    if (botParam && BOTS.some((b) => b.id === botParam)) setSelectedId(botParam);
  }, [botParam, setSelectedId]);

  const bot = BOTS.find((b) => b.id === selectedId) ?? BOTS[0];
  const scene = CURATED_SCENES.find((s) => s.id === sceneParam);
  const sceneLabel = sceneParam === 'upload' ? 'Your uploaded game' : scene ? `${scene.title} · ${scene.setting}` : 'Quick match';

  return (
    <div className="grid gap-[24px] min-[1024px]:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
      <section aria-label="Choose bot" className="rounded-[16px] border border-white/[0.16] bg-[#131316]/80 p-[28px]">
        <p className="font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">01 / Bot</p>
        <div className="mt-[22px] flex flex-wrap gap-[28px]" role="radiogroup" aria-label="Bot">
          {BOTS.map((b) => {
            const on = b.id === bot.id;
            return (
              <button
                key={b.id}
                type="button"
                role="radio"
                aria-checked={on}
                data-play-bot={b.id}
                onClick={() => setSelectedId(b.id)}
                className="flex cursor-pointer items-center gap-[14px] text-left"
              >
                <span className="block h-[64px] w-[64px] p-[6.5px]">
                  <span
                    className="block h-full w-full overflow-hidden rounded-full"
                    style={{ boxShadow: on ? '0 0 0 2px rgba(255,255,255,0.9), 0 0 0 4px #0f0f12, 0 0 0 6.5px #E4002B' : '0 0 0 1.5px rgba(255,255,255,0.18)' }}
                  >
                    <Avatar url={brand.bots[b.id]} name={b.name} />
                  </span>
                </span>
                <span className="flex flex-col">
                  <span className={`text-[19px] font-bold leading-none tracking-[-0.03em] ${on ? 'text-white' : 'text-[#D4D4D8]'}`}>{b.name}</span>
                  <span className="mt-[6px] text-[14px] text-[#9E9EA8]">{b.game}</span>
                </span>
              </button>
            );
          })}
        </div>

        <p className="mt-[36px] font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">02 / Scene</p>
        <div className="mt-[16px] flex flex-wrap items-center gap-[16px]">
          <span className="text-[20px] font-bold tracking-[-0.02em] text-white">{sceneLabel}</span>
          <ModeLink href={`/scenes?tab=famous&bot=${bot.id}`} className="border-b border-white/60 pb-[1px] text-[14px] font-medium text-white hover:border-white">
            Change scene
          </ModeLink>
        </div>
      </section>

      <section aria-label="Ready" className="flex flex-col justify-between rounded-[16px] border border-white/[0.16] bg-[#131316]/80 p-[28px]">
        <div>
          <p className="font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">03 / Ready</p>
          <p className="mt-[18px] text-[clamp(2.4rem,3.2vw,3.2rem)] font-extrabold leading-[0.98] tracking-[-0.045em] text-white" data-play-selected>
            {bot.name}
          </p>
          <p className="mt-[10px] text-[18px] text-[#B8B8C2]">
            {bot.game} · {bot.tags.join(' / ')}
          </p>
        </div>
        <ModeLink
          href={`/studio?bot=${bot.id}${sceneParam ? `&scene=${sceneParam}` : ''}`}
          className="group mt-[32px] flex h-[62px] items-center justify-between rounded-full bg-[#F5F4F0] pl-[28px] pr-[10px] text-[20px] font-bold text-[#111111] transition-colors hover:bg-white"
        >
          Start match in studio
          <span className="flex h-[42px] w-[42px] items-center justify-center rounded-full bg-brand transition-transform group-hover:translate-x-0.5">{arrow}</span>
        </ModeLink>
      </section>
    </div>
  );
}
