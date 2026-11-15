'use client';

import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { AppMode } from '@/lib/mode/contract';

interface ModeContextValue {
  mode: AppMode;
  transitioning: boolean;
  setTransitioning: (value: boolean) => void;
}

const ModeContext = createContext<ModeContextValue>({ mode: 'faze', transitioning: false, setTransitioning: () => {} });

export default function ModeRoute({ mode, children }: { mode: AppMode; children: React.ReactNode }) {
  const [transitioning, setTransitioning] = useState(false);
  useEffect(() => setTransitioning(false), [mode]);
  const value = useMemo(() => ({ mode, transitioning, setTransitioning }), [mode, transitioning]);
  return (
    <ModeContext.Provider value={value}>
      <div
        data-mode={mode}
        className={`${mode === 'faze' ? 'hub-charcoal text-ink' : ''} ${transitioning ? 'mode-route mode-route--leaving' : 'mode-route'}`}
      >
        {children}
      </div>
    </ModeContext.Provider>
  );
}

export const useAppMode = () => useContext(ModeContext);

