'use client';

import { useState } from 'react';
import { useBotSelection, useBrand } from '@/app/providers';
import { Avatar } from '@/components/bots/RosterArc';
import { BOTS, LEADERBOARD_FULL } from '@/lib/bots';

/** Full leaderboard with a per-bot filter; the selected bot is highlighted. */
export default function LeaderboardTable() {
  const { selectedId } = useBotSelection();
  const brand = useBrand();
  const [botFilter, setBotFilter] = useState<'all' | string>('all');
  const rows = LEADERBOARD_FULL.filter((r) => botFilter === 'all' || r.botId === botFilter);

  return (
    <div>
      <div className="flex flex-wrap gap-[12px]" role="radiogroup" aria-label="Filter by bot">
        {[{ id: 'all', name: 'All bots' }, ...BOTS].map((b) => {
          const on = botFilter === b.id;
          return (
            <button
              key={b.id}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => setBotFilter(b.id)}
              className={`flex h-[40px] cursor-pointer items-center whitespace-nowrap rounded-full px-[22px] text-[16px] tracking-[-0.01em] transition-colors ${
                on ? 'bg-[#F5F4F0] font-bold text-[#111111]' : 'border border-white/[0.22] font-medium text-[#E8E8EC] hover:border-white/45'
              }`}
            >
              {b.name}
            </button>
          );
        })}
      </div>

      <table className="mt-[28px] w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-white/[0.15] font-mono text-[12.5px] uppercase tracking-[0.06em] text-[#9E9EA8]">
            <th className="w-[90px] pb-[12px] font-bold">Rank</th>
            <th className="pb-[12px] font-bold">Player</th>
            <th className="pb-[12px] font-bold">Bot</th>
            <th className="pb-[12px] pr-[6px] text-right font-bold">Score</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const bot = BOTS.find((b) => b.id === r.botId)!;
            const mine = r.botId === selectedId;
            return (
              <tr key={r.rank} className="h-[56px] border-b border-white/[0.15] text-[16.5px] text-white">
                <td className="font-mono">{String(r.rank).padStart(2, '0')}</td>
                <td className="tracking-[-0.01em]">{r.name}</td>
                <td>
                  <span className="inline-flex items-center gap-[10px]">
                    <span
                      className="block h-[30px] w-[30px] overflow-hidden rounded-full"
                      style={{ boxShadow: mine ? '0 0 0 1.5px rgba(255,255,255,0.9), 0 0 0 3px #0f0f12, 0 0 0 5px #E4002B' : '0 0 0 1.5px rgba(255,255,255,0.18)' }}
                    >
                      <Avatar url={brand.bots[bot.id]} name={bot.name} />
                    </span>
                    {bot.name}
                    <span className="text-[#9E9EA8]">· {bot.game}</span>
                  </span>
                </td>
                <td className="pr-[6px] text-right">{r.score ?? '—'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-[14px] text-[12.5px] text-[#9E9EA8]">Sample data</p>
    </div>
  );
}
