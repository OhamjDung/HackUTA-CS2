'use client';

import { usePathname } from 'next/navigation';
import { useBrand } from '@/app/providers';
import { Avatar } from '@/components/bots/RosterArc';
import { STUDIO_URL } from '@/lib/constants';
import ModeLink from '@/components/mode/ModeLink';
import ModeSwitch from '@/components/mode/ModeSwitch';

const LINKS = [
  { id: 'home', label: 'Home', href: '/' },
  { id: 'bots', label: 'Bots', href: '/bots' },
  { id: 'scenes', label: 'Scenes', href: '/scenes' },
  { id: 'puzzles', label: 'Puzzles', href: '/puzzles' },
  { id: 'leaderboard', label: 'Leaderboard', href: '/leaderboard' },
] as const;

/** FaZe mark sizing rule: Logo 1 at ≥60px, 1-colour mark at 40–59px, never below 40px. */
const MARK_PX = 44;

function isActive(pathname: string, href: string) {
  return href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(`${href}/`);
}

/**
 * Top-left brand lockup: FaZe mark stacked above the 14-segment LED
 * "DoppelGamer" wordmark. Clear space ≥ 25% of the mark width on every side
 * (padding) with a 14px gap between mark and wordmark. Links to Home.
 *
 * The FaZe mark is loaded from the official file in public/images/brand/
 * (faze-mark-1color.* preferred at this size, faze-mark.* otherwise). If no file
 * is present the wordmark stands alone; the mark is never redrawn here.
 */
function BrandLockup({ wordmark }: { wordmark: boolean }) {
  const brand = useBrand();
  const mark = MARK_PX < 60 ? (brand.fazeMarkMono ?? brand.fazeMark) : (brand.fazeMark ?? brand.fazeMarkMono);
  const clear = Math.ceil(MARK_PX * 0.25);
  return (
    <ModeLink
      href="/"
      aria-label="FaZe × DoppelGamer — home"
      data-lockup
      className="flex flex-col items-start justify-self-start"
      style={{ padding: `${clear}px ${clear}px ${clear}px 0`, gap: 14 }}
    >
      {mark && (
        // Same 44px mark; a soft red halo and an occasional light sweep give it presence.
        <span className="faze-mark" style={{ '--mark': `url("${mark}")` } as React.CSSProperties}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={mark} alt="FaZe Clan" width={MARK_PX} height={MARK_PX} style={{ width: MARK_PX, height: 'auto', minWidth: 40 }} />
          <span className="faze-sheen" aria-hidden />
        </span>
      )}
      {(wordmark || !mark) && (
        <span className="led-wordmark whitespace-nowrap text-[clamp(17px,1.32vw,21px)] leading-none">DoppelGamer</span>
      )}
    </ModeLink>
  );
}

/**
 * Shared top bar for every route: lockup · centred tabs · profile + Enter studio.
 * `wordmark={false}` drops the small wordmark from the lockup (the home page
 * shows it large in the stage instead).
 */
export default function SiteNav({ wordmark = true }: { wordmark?: boolean } = {}) {
  const pathname = usePathname() ?? '/';
  const brand = useBrand();
  const hasMark = Boolean(brand.fazeMark ?? brand.fazeMarkMono);

  return (
    <header
      className={`absolute inset-x-0 top-0 z-30 flex items-center justify-between min-[760px]:grid min-[760px]:grid-cols-[1fr_auto_1fr] ${
        hasMark ? 'h-[104px]' : 'h-[68px]'
      }`}
      style={{ paddingLeft: 'var(--hub-gutter)', paddingRight: 'var(--hub-gutter)' }}
    >
      <BrandLockup wordmark={wordmark} />

      <nav aria-label="Primary" className="hidden items-center gap-[clamp(28px,3.1vw,48px)] min-[760px]:flex">
        {LINKS.map((l) => {
          const on = isActive(pathname, l.href);
          return (
            <ModeLink
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
            </ModeLink>
          );
        })}
      </nav>

      <div className="flex items-center gap-[14px] justify-self-end">
        <ModeSwitch compact />
        {brand.profile && (
          <span
            className="hidden h-[40px] w-[40px] overflow-hidden rounded-full border border-white/20 min-[480px]:block"
            aria-label="Your profile"
            role="img"
          >
            <Avatar url={brand.profile} name="You" />
          </span>
        )}
        <ModeLink
          href={STUDIO_URL}
          className="flex h-[41px] items-center whitespace-nowrap rounded-full bg-[#F5F4F0] px-[clamp(16px,1.56vw,24px)] text-[clamp(14px,1.07vw,16.5px)] font-bold tracking-[-0.01em] text-[#111111] transition-colors hover:bg-white"
        >
          Enter studio
        </ModeLink>
      </div>
    </header>
  );
}
