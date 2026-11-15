import PageShell from '@/components/shell/PageShell';
import BotContextChip from '@/components/shell/BotContextChip';
import ScenesView, { type ScenesTab } from '@/components/scenes/ScenesView';
import ModeRoute from '@/components/mode/ModeRoute';
import OdysseyExperience from '@/modes/odyssey/OdysseyExperience';
import { resolveMode } from '@/lib/mode/contract';

export const metadata = { title: 'Scenes — DoppelGamer.' };

type Search = Promise<{ tab?: string; bot?: string; mode?: string }>;

export default async function ScenesPage({ searchParams }: { searchParams: Search }) {
  const params = await searchParams;
  const mode = resolveMode(params);
  if (mode === 'odyssey') return <ModeRoute mode={mode}><OdysseyExperience /></ModeRoute>;
  const { tab, bot } = params;
  const initialTab: ScenesTab = tab === 'upload' ? 'upload' : 'famous';
  return (
    <ModeRoute mode={mode}><PageShell
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
    </PageShell></ModeRoute>
  );
}
