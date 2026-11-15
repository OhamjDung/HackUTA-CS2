import Link from 'next/link';
import PageShell from '@/components/shell/PageShell';
import PuzzleLibrary from '@/components/puzzles/PuzzleLibrary';
import CreatePuzzle from '@/components/puzzles/CreatePuzzle';

export const metadata = { title: 'Puzzles — DoppelGamer.' };

type Search = Promise<{ tab?: string; death?: string }>;

const tab = (on: boolean) =>
  `flex h-[40px] items-center whitespace-nowrap rounded-full px-[22px] text-[16px] tracking-[-0.01em] transition-colors ${
    on ? 'bg-[#F5F4F0] font-bold text-[#111111]' : 'border border-white/[0.22] font-medium text-[#E8E8EC] hover:border-white/45'
  }`;

export default async function PuzzlesPage({ searchParams }: { searchParams: Search }) {
  const { tab: tabParam, death } = await searchParams;
  const create = tabParam === 'create';
  return (
    <PageShell
      eyebrow="Puzzles"
      title={
        <>
          Try that
          <br />
          moment again.
        </>
      }
      subtitle="Every death can be replayed from 10 seconds earlier. Save the good ones, practise pro moments, climb the rating."
    >
      <nav aria-label="Puzzles sections" className="mb-[28px] flex gap-[12px]">
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
