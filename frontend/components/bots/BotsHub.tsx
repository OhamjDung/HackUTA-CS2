'use client';

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import CharacterCanvas from '@/components/canvas/CharacterCanvas';
import BottomHub from '@/components/bots/BottomHub';
import RosterArc from '@/components/bots/RosterArc';
import SelectedBotPanel from '@/components/bots/SelectedBotPanel';
import { useRouter } from 'next/navigation';
import { useBotSelection, useBrand } from '@/app/providers';
import CreditsLink from '@/components/ui/CreditsLink';
import SiteNav from '@/components/ui/SiteNav';
import { BOTS, GAME_FILTERS, type BotGame } from '@/lib/bots';
import { GLITCH_DURATION_MS, GLITCH_SWAP_AT_MS } from '@/lib/constants';
import { stageInput } from '@/lib/stageInput';
import { useModeHref } from '@/components/mode/ModeLink';

type Filter = 'all' | BotGame;

export default function BotsHub() {
  const router = useRouter();
  const { bots: avatars } = useBrand();
  const [filter, setFilter] = useState<Filter>('all');
  // Selection is app-wide (root-layout provider + sessionStorage), so it survives navigation.
  const { selectedId, setSelectedId } = useBotSelection();
  // The model + right panel switch at the glitch midpoint; the arc moves immediately.
  const [shownId, setShownId] = useState(selectedId);
  const [glitching, setGlitching] = useState(false);
  const timers = useRef<number[]>([]);
  const busy = useRef(false);
  const selectedRef = useRef(selectedId);
  selectedRef.current = selectedId;

  const roster = useMemo(() => BOTS.map((b) => ({ ...b, avatarUrl: avatars[b.id] })), [avatars]);
  const visibleBots = useMemo(() => roster.filter((b) => filter === 'all' || b.game === filter), [roster, filter]);
  const shown = BOTS.find((b) => b.id === shownId)!;
  const playHref = useModeHref(`/play?bot=${shown.id}`);

  useEffect(() => {
    // This stage has no thermal scope; make sure a scope left open on another page is closed.
    stageInput.scopeActive = false;
    const t = timers.current;
    return () => t.forEach((id) => window.clearTimeout(id));
  }, []);

  // Selection restored from storage (or changed elsewhere) while idle: show it without a glitch.
  useEffect(() => {
    if (!busy.current && selectedId !== shownId) setShownId(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const select = useCallback((id: string) => {
    if (id === selectedRef.current || busy.current) return;
    busy.current = true;
    setSelectedId(id);
    setGlitching(true);
    stageInput.glitchStartedAt = performance.now();
    timers.current.push(window.setTimeout(() => setShownId(id), GLITCH_SWAP_AT_MS));
    timers.current.push(
      window.setTimeout(() => {
        setGlitching(false);
        busy.current = false;
      }, GLITCH_DURATION_MS),
    );
  }, [setSelectedId]);

  // Filtering away the selected bot selects the first bot that remains.
  useEffect(() => {
    if (!visibleBots.some((b) => b.id === selectedRef.current) && visibleBots[0]) {
      busy.current = false;
      select(visibleBots[0].id);
    }
  }, [visibleBots, select]);

  // ---- stage anchor: centre the character between the roster arc and the right column
  const zoneRef = useRef<HTMLElement>(null);
  const canvasWrapRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const zone = zoneRef.current;
    const wrap = canvasWrapRef.current;
    if (!zone || !wrap) return;
    const measure = () => {
      const w = wrap.clientWidth;
      if (w < 1024) {
        stageInput.anchorX = 0.5;
        stageInput.anchorScale = 1;
        return;
      }
      const base = wrap.getBoundingClientRect().left;
      const arc = zone.querySelector<HTMLElement>('[data-arc]');
      const right = zone.querySelector<HTMLElement>('[data-right-col]');
      if (!arc || !right) return;
      const left = arc.getBoundingClientRect().left - base + 210; // avatar + longest name
      const rightEdge = right.getBoundingClientRect().left - base;
      const gap = rightEdge - left;
      stageInput.anchorX = Math.min(0.62, Math.max(0.45, (left + gap * 0.37) / w));
      // Width: fit the arc/right-column gap. Height: keep the head below the 60px nav
      // (camera frames the figure at 89% of the stage with a 7% floor margin).
      const h = wrap.clientHeight;
      const byHeight = (0.93 * h - 52) / (0.89 * h);
      stageInput.anchorScale = Math.min(1, byHeight, Math.max(0.72, gap / (0.42 * h)));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(wrap);
    document.fonts?.ready.then(measure);
    return () => ro.disconnect();
  }, []);

  const shownIndex = BOTS.findIndex((b) => b.id === shownId) + 1;

  return (
    <main className="relative min-h-screen w-full overflow-x-hidden">
      <section ref={zoneRef} className="hub-top relative flex w-full flex-col min-[1024px]:block" aria-label="Bot roster">
        <div
          ref={canvasWrapRef}
          className="relative order-3 h-[62svh] min-h-[440px] w-full min-[1024px]:absolute min-[1024px]:inset-0 min-[1024px]:h-auto"
        >
          <CharacterCanvas activeId={shown.modelId} />
        </div>

        <SiteNav />
        <CreditsLink />

        {/* Left: roster header + filters */}
        <div
          className="relative z-10 order-1 px-[var(--hub-gutter)] pt-[96px] min-[1024px]:absolute min-[1024px]:left-[var(--hub-gutter)] min-[1024px]:top-[28.6%] min-[1024px]:w-[min(26vw,380px)] min-[1024px]:p-0"
        >
          <p className="text-[16px] font-bold uppercase leading-none tracking-[0.16em] text-[#D8D8DE]">The bot roster</p>
          <h1 className="mt-[22px] text-[clamp(3.1rem,4.05vw,4.5rem)] font-extrabold leading-[0.96] tracking-[-0.045em] text-white">
            Choose your
            <br />
            next rival.
          </h1>
          <p className="mt-[20px] text-[18.5px] leading-snug tracking-[-0.01em] text-[#B8B8C2]">
            Pick a bot. Play a round. Make a moment.
          </p>
          <div className="mt-[22px] flex flex-wrap gap-[clamp(10px,0.92vw,14px)]" role="radiogroup" aria-label="Filter by game">
            {GAME_FILTERS.map((f) => {
              const on = filter === f.id;
              return (
                <button
                  key={f.id}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  onClick={() => setFilter(f.id)}
                  className={`flex h-[40px] cursor-pointer items-center whitespace-nowrap rounded-full px-[clamp(15px,1.43vw,22px)] text-[clamp(15px,1.04vw,16px)] tracking-[-0.01em] transition-colors ${
                    on ? 'bg-[#F5F4F0] font-bold text-[#111111]' : 'border border-white/[0.22] font-medium text-[#E8E8EC] hover:border-white/45'
                  }`}
                >
                  {f.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Arc roster */}
        <div
          data-arc
          className="relative z-10 order-2 mt-8 px-[var(--hub-gutter)] min-[1024px]:absolute min-[1024px]:left-[28.05vw] min-[1024px]:top-[18.5%] min-[1024px]:mt-0 min-[1024px]:p-0"
        >
          <RosterArc bots={visibleBots} selectedId={selectedId} onSelect={select} />
        </div>

        <p className="absolute bottom-[46px] left-[var(--hub-gutter)] z-10 hidden text-[13.5px] text-[#9E9EA8] min-[1024px]:block">
          {visibleBots.length} {visibleBots.length === 1 ? 'bot' : 'bots'} · roster preview
        </p>

        {/* Right: selected bot */}
        <div className="relative z-10 order-4 px-[var(--hub-gutter)] py-10 min-[1024px]:absolute min-[1024px]:left-[71.5vw] min-[1024px]:top-[21.5%] min-[1024px]:p-0">
          <SelectedBotPanel
            bot={shown}
            index={shownIndex}
            glitching={glitching}
            onPlay={() => router.push(playHref)}
          />
        </div>
      </section>

      <BottomHub />
    </main>
  );
}
