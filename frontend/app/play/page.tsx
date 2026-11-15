import PageShell from '@/components/shell/PageShell';
import MatchControls from '@/components/play/MatchControls';
import ModeRoute from '@/components/mode/ModeRoute';
import OdysseyExperience from '@/modes/odyssey/OdysseyExperience';
import { resolveMode } from '@/lib/mode/contract';

export const metadata = { title: 'Play — DoppelGamer.' };

type Search = Promise<{ bot?: string; scene?: string; mode?: string }>;

export default async function PlayPage({ searchParams }: { searchParams: Search }) {
  const params = await searchParams;
  const mode = resolveMode(params);
  if (mode === 'odyssey') return <ModeRoute mode={mode}><OdysseyExperience /></ModeRoute>;
  return (
    <ModeRoute mode={mode}><PageShell
      eyebrow="Match setup"
      title={
        <>
          Set the stage.
          <br />
          Then play.
        </>
      }
      subtitle="Set up a private CS2 match to watch or play."
    >
      <MatchControls />
    </PageShell></ModeRoute>
  );
}
