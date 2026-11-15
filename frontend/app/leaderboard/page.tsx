import PageShell from '@/components/shell/PageShell';
import LeaderboardTable from '@/components/shell/LeaderboardTable';
import ModeRoute from '@/components/mode/ModeRoute';
import OdysseyExperience from '@/modes/odyssey/OdysseyExperience';
import { resolveMode } from '@/lib/mode/contract';

export const metadata = { title: 'Leaderboard — DoppelGamer.' };

export default async function LeaderboardPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const mode = resolveMode(await searchParams);
  if (mode === 'odyssey') return <ModeRoute mode={mode}><OdysseyExperience /></ModeRoute>;
  return (
    <ModeRoute mode={mode}><PageShell
      eyebrow="Leaderboard"
      title={
        <>
          Who beat
          <br />
          the bots.
        </>
      }
      subtitle="Best runs against every bot in the roster."
    >
      <LeaderboardTable />
    </PageShell></ModeRoute>
  );
}
