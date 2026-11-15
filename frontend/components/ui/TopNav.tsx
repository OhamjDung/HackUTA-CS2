'use client';

import { useEffect, useRef, useState } from 'react';
import { STUDIO_URL } from '@/lib/constants';
import type { CharacterConfig, CharacterId } from '@/types';
import { CloseIcon, MenuIcon, ScopeIcon } from './icons';

interface TopNavProps {
  thermalActive: boolean;
  onToggleThermal: () => void;
  characters: CharacterConfig[];
  activeId: CharacterId;
  onSelect: (id: CharacterId) => void;
  autoPlay: boolean;
  onToggleAutoPlay: () => void;
}

/** Attribution lines live in one place: public/models/CREDITS.md (CC-BY-4.0). */
async function loadCreditLines(): Promise<string[]> {
  const res = await fetch('/models/CREDITS.md');
  if (!res.ok) throw new Error(`credits HTTP ${res.status}`);
  const text = await res.text();
  const lines = text
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.startsWith('- '))
    .map((l) => l.slice(2).trim())
    .filter(Boolean);
  if (lines.length === 0) throw new Error('no attribution lines found');
  return lines;
}

/** Renders raw URLs in a credit line as links; leaves the rest as text. */
function linkify(line: string, keyPrefix: string) {
  const parts = line.split(/(https?:\/\/[^\s)]+)/g);
  return parts.map((part, i) =>
    /^https?:\/\//.test(part) ? (
      <a
        key={`${keyPrefix}-${i}`}
        href={part}
        target="_blank"
        rel="noreferrer"
        className="text-brand underline decoration-brand/40 underline-offset-2"
      >
        {part}
      </a>
    ) : (
      <span key={`${keyPrefix}-${i}`}>{part}</span>
    ),
  );
}

export default function TopNav({
  thermalActive,
  onToggleThermal,
  characters,
  activeId,
  onSelect,
  autoPlay,
  onToggleAutoPlay,
}: TopNavProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [creditsOpen, setCreditsOpen] = useState(false);
  const [creditLines, setCreditLines] = useState<string[] | null>(null);
  const [creditsError, setCreditsError] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const onDown = (e: PointerEvent) => {
      if (!panelRef.current?.contains(e.target as Node)) setMenuOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setMenuOpen(false);
    window.addEventListener('pointerdown', onDown);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('pointerdown', onDown);
      window.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  useEffect(() => {
    if (!creditsOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setCreditsOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [creditsOpen]);

  const openCredits = () => {
    setMenuOpen(false);
    setCreditsOpen(true);
    if (creditLines || creditsError) return;
    loadCreditLines()
      .then(setCreditLines)
      .catch(() => setCreditsError(true));
  };

  return (
    <>
      <header
        className="absolute inset-x-0 top-0 z-30 flex h-[72px] items-center justify-between"
        style={{ paddingLeft: 'var(--gutter)', paddingRight: 'clamp(16px, 4.2vw, 64px)' }}
      >
        <a href="/" className="text-[26px] font-bold leading-none tracking-[-0.045em] text-ink" aria-label="DoppelGamer home">
          DoppelGamer<span className="text-brand">.</span>
        </a>

        <nav className="flex items-center gap-6 min-[900px]:gap-11" aria-label="Primary">
          <button
            type="button"
            onClick={onToggleThermal}
            aria-pressed={thermalActive}
            className="hidden cursor-pointer items-center gap-3 text-[15px] font-medium tracking-[-0.01em] text-ink transition-opacity hover:opacity-70 sm:flex"
          >
            <span className={thermalActive ? 'text-brand' : undefined}>
              <ScopeIcon />
            </span>
            Thermal scope
          </button>
          <a
            href={STUDIO_URL}
            className="hidden text-[15px] font-medium tracking-[-0.01em] text-ink transition-opacity hover:opacity-70 sm:inline"
          >
            Enter studio
          </a>

          <div className="relative min-[900px]:-ml-4" ref={panelRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              aria-expanded={menuOpen}
              aria-haspopup="true"
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-full bg-ink text-white transition-transform hover:scale-105"
            >
              {menuOpen ? <CloseIcon /> : <MenuIcon />}
            </button>

            {menuOpen && (
              <div
                role="menu"
                className="absolute right-0 top-12 w-64 rounded-2xl border border-hairline bg-white p-2 text-[14px] shadow-[0_18px_40px_-18px_rgba(17,17,17,0.25)]"
              >
                <p className="px-3 pb-1 pt-2 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-subtle">
                  Character
                </p>
                {characters.map((c, i) => (
                  <button
                    key={c.id}
                    type="button"
                    role="menuitemradio"
                    aria-checked={c.id === activeId}
                    onClick={() => {
                      onSelect(c.id);
                      setMenuOpen(false);
                    }}
                    className="flex w-full cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-left hover:bg-studio"
                  >
                    <span className="font-mono text-[12px] text-ink-subtle">0{i + 1}</span>
                    <span className="flex-1 font-medium">{c.displayName}</span>
                    {c.id === activeId && <span className="h-1.5 w-1.5 rounded-full bg-brand" />}
                  </button>
                ))}
                <div className="my-2 h-px bg-hairline" />
                <MenuToggle label="Thermal scope" on={thermalActive} onClick={onToggleThermal} />
                <MenuToggle label="Auto-cycle (6s)" on={autoPlay} onClick={onToggleAutoPlay} />
                <button
                  type="button"
                  onClick={openCredits}
                  className="mt-1 flex w-full cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-left font-medium hover:bg-studio"
                >
                  Model credits
                  <span aria-hidden className="text-ink-subtle">→</span>
                </button>
                <a
                  href={STUDIO_URL}
                  className="mt-1 block rounded-lg px-3 py-2 font-medium hover:bg-studio sm:hidden"
                >
                  Enter studio
                </a>
              </div>
            )}
          </div>
        </nav>
      </header>

      {creditsOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-6"
          role="dialog"
          aria-modal="true"
          aria-label="3D model credits"
        >
          <button
            type="button"
            aria-label="Close model credits"
            onClick={() => setCreditsOpen(false)}
            className="absolute inset-0 cursor-default bg-ink/40"
          />
          <div className="relative max-h-[80vh] w-full max-w-lg overflow-auto rounded-2xl border border-hairline bg-white p-6 shadow-[0_24px_60px_-24px_rgba(17,17,17,0.35)]">
            <div className="mb-3 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-[20px] font-bold tracking-[-0.02em] text-ink">Model credits</h2>
                <p className="mt-1 text-[13px] leading-relaxed text-ink-muted">
                  Character models adapted from Sketchfab, licensed under CC-BY-4.0.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setCreditsOpen(false)}
                aria-label="Close"
                className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full bg-ink text-white transition-transform hover:scale-105"
              >
                <CloseIcon />
              </button>
            </div>
            {creditsError ? (
              <p className="text-[13px] text-ink-muted">
                Credits could not be loaded. See <span className="font-mono">public/models/CREDITS.md</span>.
              </p>
            ) : creditLines ? (
              <ul className="space-y-3 text-[13px] leading-relaxed text-ink">
                {creditLines.map((line, i) => (
                  <li key={i} className="rounded-xl bg-studio px-3 py-2">
                    {linkify(line, `credit-${i}`)}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[13px] text-ink-muted">Loading credits…</p>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function MenuToggle({ label, on, onClick }: { label: string; on: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      role="menuitemcheckbox"
      aria-checked={on}
      onClick={onClick}
      className="flex w-full cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-left hover:bg-studio"
    >
      <span className="font-medium">{label}</span>
      <span
        className={`relative h-5 w-9 rounded-full transition-colors ${on ? 'bg-ink' : 'bg-pill'}`}
        aria-hidden
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${on ? 'translate-x-[18px]' : 'translate-x-0.5'}`}
        />
      </span>
    </button>
  );
}
