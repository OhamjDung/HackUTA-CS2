import PageShell from '@/components/shell/PageShell';
import PlaySetup from '@/components/play/PlaySetup';
import ModeRoute from '@/components/mode/ModeRoute';
import OdysseyExperience from '@/modes/odyssey/OdysseyExperience';
import { resolveMode } from '@/lib/mode/contract';

export const metadata = { title: 'Play — DoppelGamer.' };

type Search = Promise<{ bot?: string; scene?: string; mode?: string }>;

export default async function PlayPage({ searchParams }: { searchParams: Search }) {
  const params = await searchParams;
  const mode = resolveMode(params);
  if (mode === 'odyssey') return <ModeRoute mode={mode}><OdysseyExperience /></ModeRoute>;
  const { bot, scene } = params;
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
      subtitle="Your bot is locked in from the roster. Change it here or pick a different scene."
    >
      <PlaySetup botParam={bot} sceneParam={scene} />
    </PageShell></ModeRoute>
  );
}
