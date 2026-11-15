'use client';

import type { CharacterConfig, CharacterId } from '@/types';

interface NavigationDeckProps {
  characters: CharacterConfig[];
  activeId: CharacterId;
  onSelect: (id: CharacterId) => void;
  disabled?: boolean;
  /** Showcase auto-cycle running; toggle freezes the loop for inspection. */
  autoPlay: boolean;
  onToggleAutoPlay: () => void;
}

export default function NavigationDeck({
  characters,
  activeId,
  onSelect,
  disabled = false,
  autoPlay,
  onToggleAutoPlay,
}: NavigationDeckProps) {
  const activeAccent =
    characters.find((c) => c.id === activeId)?.accentColor ?? '#ffffff';
  return (
    <nav
      aria-label="Character selection"
      className="absolute bottom-16 left-1/2 z-20 flex -translate-x-1/2 items-center gap-2 rounded-full border border-white/15 bg-black/70 p-2 backdrop-blur-md"
      style={{ borderColor: `${activeAccent}55` }}
    >
      {characters.map((character, index) => {
        const isActive = character.id === activeId;
        return (
          <button
            key={character.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(character.id)}
            aria-pressed={isActive}
            style={
              isActive
                ? { backgroundColor: character.accentColor, color: '#000000' }
                : undefined
            }
            className={`min-w-20 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] transition-colors ${
              isActive
                ? ''
                : 'bg-transparent text-white/70 hover:bg-white/10 hover:text-white'
            } ${disabled && !isActive ? 'cursor-wait opacity-50' : ''}`}
          >
            <span className="mr-1 text-white/30">0{index + 1}</span> {character.name}
          </button>
        );
      })}
      <button
        type="button"
        onClick={onToggleAutoPlay}
        aria-pressed={autoPlay}
        aria-label={autoPlay ? 'Pause auto-cycle' : 'Resume auto-cycle'}
        title={autoPlay ? 'Pause auto-cycle (inspect this model)' : 'Resume auto-cycle'}
        className="flex h-9 w-9 items-center justify-center rounded-full border border-white/15 text-white/70 transition-colors hover:bg-white/10 hover:text-white"
      >
        {autoPlay ? (
          <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden>
            <rect x="2" y="1" width="3" height="10" fill="currentColor" />
            <rect x="7" y="1" width="3" height="10" fill="currentColor" />
          </svg>
        ) : (
          <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden>
            <polygon points="3,1 11,6 3,11" fill="currentColor" />
          </svg>
        )}
      </button>
    </nav>
  );
}
