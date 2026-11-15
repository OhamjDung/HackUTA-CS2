'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { BrandAssets } from '@/lib/brandAssets';
import { BOTS, DEFAULT_BOT_ID } from '@/lib/bots';

const BrandContext = createContext<BrandAssets>({ bots: {} });

interface BotSelection {
  selectedId: string;
  setSelectedId: (id: string) => void;
}
const BotSelectionContext = createContext<BotSelection>({ selectedId: DEFAULT_BOT_ID, setSelectedId: () => {} });

const STORAGE_KEY = 'doppelgamer.selectedBot';

/**
 * App-wide state shared by every route:
 * - brand/portrait asset URLs (resolved on the server in the root layout)
 * - the selected bot — lives above the routes, so it survives client navigation
 *   (Bots → Home/Scenes/Leaderboard → Bots) and is mirrored to sessionStorage so
 *   it also survives a reload within the tab.
 */
export default function Providers({ brand, children }: { brand: BrandAssets; children: React.ReactNode }) {
  const [selectedId, setSelected] = useState(DEFAULT_BOT_ID);

  useEffect(() => {
    try {
      const saved = window.sessionStorage.getItem(STORAGE_KEY);
      if (saved && BOTS.some((b) => b.id === saved)) setSelected(saved);
    } catch {
      /* storage unavailable: keep the default */
    }
  }, []);

  const setSelectedId = useCallback((id: string) => {
    setSelected(id);
    try {
      window.sessionStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* ignore */
    }
  }, []);

  const selection = useMemo(() => ({ selectedId, setSelectedId }), [selectedId, setSelectedId]);

  return (
    <BrandContext.Provider value={brand}>
      <BotSelectionContext.Provider value={selection}>{children}</BotSelectionContext.Provider>
    </BrandContext.Provider>
  );
}

export const useBrand = () => useContext(BrandContext);
export const useBotSelection = () => useContext(BotSelectionContext);

/** The selected bot with its resolved portrait URL. */
export function useSelectedBot() {
  const { selectedId } = useBotSelection();
  const brand = useBrand();
  const bot = BOTS.find((b) => b.id === selectedId) ?? BOTS[0];
  return { ...bot, avatarUrl: brand.bots[bot.id] };
}
