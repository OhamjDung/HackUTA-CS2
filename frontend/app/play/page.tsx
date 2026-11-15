import PageShell from '@/components/shell/PageShell';
import PlaySetup from '@/components/play/PlaySetup';

export const metadata = { title: 'Play — DoppelGamer.' };

type Search = Promise<{ bot?: string; scene?: string }>;

export default async function PlayPage({ searchParams }: { searchParams: Search }) {
  const { bot, scene } = await searchParams;
  return (
    <PageShell
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
    </PageShell>
  );
}
