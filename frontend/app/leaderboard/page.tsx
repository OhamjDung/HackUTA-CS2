import PageShell from '@/components/shell/PageShell';
import LeaderboardTable from '@/components/shell/LeaderboardTable';

export const metadata = { title: 'Leaderboard — DoppelGamer.' };

export default function LeaderboardPage() {
  return (
    <PageShell
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
    </PageShell>
  );
}
