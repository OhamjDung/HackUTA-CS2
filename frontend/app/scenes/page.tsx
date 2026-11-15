import PageShell from '@/components/shell/PageShell';
import BotContextChip from '@/components/shell/BotContextChip';
import ScenesView, { type ScenesTab } from '@/components/scenes/ScenesView';

export const metadata = { title: 'Scenes — DoppelGamer.' };

type Search = Promise<{ tab?: string; bot?: string }>;

export default async function ScenesPage({ searchParams }: { searchParams: Search }) {
  const { tab, bot } = await searchParams;
  const initialTab: ScenesTab = tab === 'upload' ? 'upload' : 'famous';
  return (
    <PageShell
      eyebrow="Play a scene"
      title={
        <>
          Pick the moment.
          <br />
          Bring the rival.
        </>
      }
      subtitle="Replay one of your own rounds, or drop into a curated moment."
      aside={<BotContextChip botParam={bot} />}
    >
      <ScenesView key={initialTab} initialTab={initialTab} />
    </PageShell>
  );
}
