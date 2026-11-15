'use client';

import { LEADERBOARD_SAMPLE, SCENES } from '@/lib/bots';
import { ArrowUpRight } from '@/components/ui/icons';
import Image from 'next/image';
import Link from 'next/link';

/** Bottom deck: "Play a scene" cards | hairline | "Leaderboard" (sample rows). */
export default function BottomHub() {
  return (
    <section
      className="relative"
      style={{ paddingLeft: 'var(--hub-gutter)', paddingRight: 'var(--hub-gutter)' }}
      aria-label="Scenes and leaderboard"
    >
      <div className="grid grid-cols-1 gap-12 border-t border-white/[0.15] pb-10 pt-[22px] min-[1024px]:grid-cols-[minmax(0,930fr)_68px_minmax(0,433fr)] min-[1024px]:gap-0 min-[1024px]:pb-0">
        {/* Play a scene */}
        <div id="scenes">
          <h2 className="text-[34px] font-bold leading-none tracking-[-0.04em] text-white">Play a scene</h2>
          <div className="mt-[30px] grid grid-cols-1 gap-[24px] sm:grid-cols-2">
            {SCENES.map((s) => (
              <Link
                key={s.id}
                href={s.href}
                className="group flex h-[102px] items-center overflow-hidden rounded-[12px] border border-white/[0.16] bg-[#131316]/80 pl-[8px] transition-[border-color,background-color] hover:border-white/30 hover:bg-[#18181c]/90"
              >
                <span className="relative block h-[86px] w-[164px] max-w-[42%] shrink-0 overflow-hidden rounded-[10px]">
                  <Image
                    src={s.image}
                    alt={s.alt}
                    fill
                    sizes="164px"
                    className="object-cover transition-transform duration-500 group-hover:scale-[1.04]"
                  />
                </span>
                <span className="flex min-w-0 flex-1 items-center justify-between gap-3 pl-[20px] pr-[18px]">
                  <span className="min-w-0">
                    <span className="block text-[18.5px] font-bold leading-tight tracking-[-0.02em] text-white">{s.title}</span>
                    <span className="mt-[6px] block truncate text-[15px] leading-tight text-[#B8B8C2]">{s.subtitle}</span>
                  </span>
                  <svg width="20" height="14" viewBox="0 0 20 14" fill="none" className="shrink-0 text-ink transition-transform group-hover:translate-x-0.5" aria-hidden>
                    <path d="M1 7h16M12 1.5 17.5 7 12 12.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
              </Link>
            ))}
          </div>
        </div>

        <div className="hidden justify-center min-[1024px]:flex" aria-hidden>
          <div className="mt-[2px] h-[180px] w-px bg-white/[0.15]" />
        </div>

        {/* Leaderboard */}
        <div id="leaderboard">
          <div className="flex items-end justify-between">
            <h2 className="text-[34px] font-bold leading-none tracking-[-0.04em] text-white">Leaderboard</h2>
            <Link href="/leaderboard" className="inline-flex items-center gap-[6px] border-b-[1.5px] border-ink pb-[2px] text-[16px] font-medium leading-none text-ink">
              View all
              <ArrowUpRight size={15} strokeWidth={1.8} />
            </Link>
          </div>
          <ol className="mt-[14px]">
            {LEADERBOARD_SAMPLE.map((r) => (
              <li key={r.rank} className="grid h-[36px] grid-cols-[66px_1fr_auto] items-center border-b border-white/[0.15] text-[16.5px] text-ink">
                <span className="font-mono text-[16px] tracking-[0.02em]">{String(r.rank).padStart(2, '0')}</span>
                <span className="tracking-[-0.01em]">{r.name}</span>
                <span className="pr-[6px]">{r.score ?? '—'}</span>
              </li>
            ))}
          </ol>
          <p className="mt-[11px] text-[12.5px] text-[#9E9EA8]">Sample data</p>
        </div>
      </div>
    </section>
  );
}
