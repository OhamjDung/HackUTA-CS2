'use client';

import type { CharacterConfig, CharacterId } from '@/types';

interface NavigationDeckProps {
  characters: CharacterConfig[];
  activeId: CharacterId;
  onSelect: (id: CharacterId) => void;
  disabled?: boolean;
}

export default function NavigationDeck({
  characters,
  activeId,
  onSelect,
  disabled = false,
}: NavigationDeckProps) {
  return (
    <nav
      aria-label="Character selection"
      className="absolute bottom-16 left-1/2 z-20 flex -translate-x-1/2 gap-2 rounded-full border border-white/15 bg-black/70 p-2 backdrop-blur-md"
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
            className={`min-w-20 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] transition-colors ${
              isActive
                ? 'bg-white text-black'
                : 'bg-transparent text-white/70 hover:bg-white/10 hover:text-white'
            } ${disabled && !isActive ? 'cursor-wait opacity-50' : ''}`}
          >
            <span className="mr-1 text-white/30">0{index + 1}</span> {character.name}
          </button>
        );
      })}
    </nav>
  );
}
