'use client';

import { useEffect, useState } from 'react';
import { CloseIcon } from './icons';

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

/** Small, low-contrast "Model credits" trigger + modal (CC-BY-4.0 attribution). */
export default function CreditsLink() {
  const [creditsOpen, setCreditsOpen] = useState(false);
  const [creditLines, setCreditLines] = useState<string[] | null>(null);
  const [creditsError, setCreditsError] = useState(false);

  useEffect(() => {
    if (!creditsOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setCreditsOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [creditsOpen]);

  const openCredits = () => {
    setCreditsOpen(true);
    if (creditLines || creditsError) return;
    loadCreditLines()
      .then(setCreditLines)
      .catch(() => setCreditsError(true));
  };

  return (
    <>
      <button
        type="button"
        onClick={openCredits}
        className="fixed bottom-[10px] left-1/2 z-40 -translate-x-1/2 cursor-pointer font-mono text-[10.5px] uppercase tracking-[0.14em] text-white/35 transition-colors hover:text-white/80"
      >
        Model credits
      </button>
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
            className="absolute inset-0 cursor-default bg-black/70"
          />
          <div className="relative max-h-[80vh] w-full max-w-lg overflow-auto rounded-2xl border border-outline bg-surface p-6 shadow-[0_24px_60px_-24px_rgba(0,0,0,0.9)]">
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
                className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full bg-ink text-studio transition-transform hover:scale-105"
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
