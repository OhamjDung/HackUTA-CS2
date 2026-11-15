import Link from 'next/link';
import PageShell from '@/components/shell/PageShell';
import PuzzleLibrary from '@/components/puzzles/PuzzleLibrary';
import CreatePuzzle from '@/components/puzzles/CreatePuzzle';

export const metadata = { title: 'Puzzles — DoppelGamer.' };

type Search = Promise<{ tab?: string; death?: string }>;

const tab = (on: boolean) =>
  `relative -mb-px flex items-center whitespace-nowrap px-[20px] pb-[14px] pt-[2px] text-[18px] tracking-[-0.01em] transition-colors ${
    on
      ? 'font-bold text-white after:absolute after:inset-x-[8px] after:bottom-0 after:h-[3px] after:rounded-full after:bg-[#E4002B]'
      : 'font-semibold text-[#9E9EA8] hover:text-white'
  }`;

export default async function PuzzlesPage({ searchParams }: { searchParams: Search }) {
  const { tab: tabParam, death } = await searchParams;
  const create = tabParam === 'create';
  return (
    <PageShell
      eyebrow="Puzzles"
      title="Try that moment again."
      subtitle="Every death can be replayed from 10 seconds earlier. Save the good ones, practise pro moments, climb the rating."
    >
      <nav aria-label="Puzzles sections" className="-mt-[10px] mb-[26px] flex gap-[6px] border-b border-white/[0.15]">
        <Link href="/puzzles" aria-current={create ? undefined : 'page'} className={tab(!create)}>
          Library
        </Link>
        <Link href="/puzzles?tab=create" aria-current={create ? 'page' : undefined} className={tab(create)}>
          Create
        </Link>
      </nav>
      {create ? <CreatePuzzle deathParam={death} /> : <PuzzleLibrary />}
    </PageShell>
  );
}
