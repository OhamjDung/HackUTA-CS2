'use client';

import ModeLink from '@/components/mode/ModeLink';
import { useEffect } from 'react';
import { useBotSelection, useSelectedBot } from '@/app/providers';
import { Avatar } from '@/components/bots/RosterArc';
import { BOTS } from '@/lib/bots';

/**
 * Shows the app-wide selected bot (photo + name) with a link back to Bots.
 * If the URL carries ?bot=<id> (e.g. "Try a scene", "Play bot") that bot becomes the selection.
 */
export default function BotContextChip({ botParam }: { botParam?: string }) {
  const { setSelectedId } = useBotSelection();
  const bot = useSelectedBot();

  useEffect(() => {
    if (botParam && BOTS.some((b) => b.id === botParam)) setSelectedId(botParam);
  }, [botParam, setSelectedId]);

  return (
    <div className="flex items-center gap-[14px] rounded-full border border-white/[0.16] bg-[#131316]/80 py-[6px] pl-[6px] pr-[20px]" data-bot-chip={bot.id}>
      <span className="block h-[46px] w-[46px] overflow-hidden rounded-full" style={{ boxShadow: '0 0 0 2px rgba(255,255,255,0.9), 0 0 0 4px #0f0f12, 0 0 0 6px #E4002B' }}>
        <Avatar url={bot.avatarUrl} name={bot.name} />
      </span>
      <span className="ml-[4px] flex flex-col">
        <span className="font-mono text-[11.5px] font-bold uppercase tracking-[0.06em] text-[#9E9EA8]">Playing with</span>
        <span className="text-[18px] font-bold leading-tight tracking-[-0.02em] text-white">
          {bot.name} <span className="font-medium text-[#B8B8C2]">· {bot.game}</span>
        </span>
      </span>
      <ModeLink href="/bots" className="ml-[10px] border-b border-white/60 pb-[1px] text-[14px] font-medium text-white hover:border-white">
        Change
      </ModeLink>
    </div>
  );
}
