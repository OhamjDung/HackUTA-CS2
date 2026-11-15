import Link from 'next/link';
import PageShell from '@/components/shell/PageShell';
import PuzzlePractice from '@/components/puzzles/PuzzlePractice';

export const metadata = { title: 'Practice — DoppelGamer.' };

export default async function PuzzlePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <PageShell
      eyebrow="Practice"
      title={
        <>
          Again.
          <br />
          Better.
        </>
      }
      subtitle="Watch what happened, then play the same ten seconds."
      aside={
        <Link href="/puzzles" className="flex h-[41px] items-center rounded-full border border-white/[0.25] px-[20px] text-[15.5px] font-medium text-white hover:border-white/50">
          ← All puzzles
        </Link>
      }
    >
      <PuzzlePractice id={decodeURIComponent(id)} />
    </PageShell>
  );
}
