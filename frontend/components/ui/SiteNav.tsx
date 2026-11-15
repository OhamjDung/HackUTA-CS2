'use client';

import { Avatar } from '@/components/bots/RosterArc';
import { STUDIO_URL } from '@/lib/constants';

const LINKS = [
  { id: 'home', label: 'Home', href: '/' },
  { id: 'bots', label: 'Bots', href: '/bots' },
  { id: 'scenes', label: 'Scenes', href: '#scenes' },
  { id: 'leaderboard', label: 'Leaderboard', href: '#leaderboard' },
] as const;

export type SiteNavId = (typeof LINKS)[number]['id'];

/** Hub navigation: logo · centred section links · avatar + Enter studio. */
export default function SiteNav({ active, profileUrl }: { active: SiteNavId; profileUrl?: string }) {
  return (
    <header
      className="absolute inset-x-0 top-0 z-30 flex h-[60px] items-center justify-between min-[760px]:grid min-[760px]:grid-cols-[1fr_auto_1fr]"
      style={{ paddingLeft: 'var(--hub-gutter)', paddingRight: 'var(--hub-gutter)' }}
    >
      <a href="/" className="justify-self-start text-[clamp(22px,1.76vw,27px)] font-bold leading-none tracking-[-0.045em] text-ink" aria-label="DoppelGamer home">
        DoppelGamer<span className="text-brand">.</span>
      </a>

      <nav aria-label="Primary" className="hidden items-center gap-[clamp(28px,3.1vw,48px)] min-[760px]:flex">
        {LINKS.map((l) => {
          const on = l.id === active;
          return (
            <a
              key={l.id}
              href={l.href}
              aria-current={on ? 'page' : undefined}
              className={`relative pb-[3px] text-[16.5px] font-semibold leading-none tracking-[-0.01em] transition-colors ${
                on ? 'text-white' : 'text-[#D4D4D8] hover:text-white'
              }`}
            >
              {l.label}
              <span
                className={`absolute -bottom-[10px] left-0 h-[2.5px] w-full rounded-full bg-brand transition-opacity ${
                  on ? 'opacity-100' : 'opacity-0'
                }`}
                aria-hidden
              />
            </a>
          );
        })}
      </nav>

      <div className="flex items-center gap-[14px] justify-self-end">
        <span
          className="hidden h-[40px] w-[40px] overflow-hidden rounded-full border border-white/20 min-[480px]:block"
          aria-label="Your profile"
          role="img"
        >
          <Avatar url={profileUrl} />
        </span>
        <a
          href={STUDIO_URL}
          className="flex h-[41px] items-center whitespace-nowrap rounded-full bg-[#F5F4F0] px-[clamp(16px,1.56vw,24px)] text-[clamp(14px,1.07vw,16.5px)] font-bold tracking-[-0.01em] text-[#111111] transition-colors hover:bg-white"
        >
          Enter studio
        </a>
      </div>
    </header>
  );
}
