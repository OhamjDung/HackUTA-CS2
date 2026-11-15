import Link from 'next/link';
import PageShell from '@/components/shell/PageShell';
import BotContextChip from '@/components/shell/BotContextChip';

export const metadata = { title: 'Studio — DoppelGamer.' };

type Search = Promise<{ bot?: string; scene?: string }>;

/** Single studio destination for every "Enter studio" / "Start match" entry point. */
export default async function StudioPage({ searchParams }: { searchParams: Search }) {
  const { bot } = await searchParams;
  return (
    <PageShell
      eyebrow="Studio"
      title={
        <>
          Your stream.
          <br />
          Your co-host.
        </>
      }
      subtitle="The live studio connects your stream, your bot and your scene."
      aside={<BotContextChip botParam={bot} />}
    >
      <div className="grid gap-[20px] sm:grid-cols-3">
        {[
          { n: '01', t: 'Bot', d: 'Choose who you face.', href: '/bots', cta: 'Open roster' },
          { n: '02', t: 'Scene', d: 'Upload a round or pick a moment.', href: '/scenes', cta: 'Browse scenes' },
          { n: '03', t: 'Match', d: 'Lock it in and go live.', href: '/play', cta: 'Match setup' },
        ].map((c) => (
          <Link key={c.n} href={c.href} className="group rounded-[16px] border border-white/[0.16] bg-[#131316]/80 p-[26px] transition-colors hover:border-white/30">
            <p className="font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">{c.n} / {c.t}</p>
            <p className="mt-[14px] text-[18px] text-[#B8B8C2]">{c.d}</p>
            <p className="mt-[22px] inline-block border-b border-white/60 pb-[1px] text-[15px] font-medium text-white group-hover:border-white">{c.cta}</p>
          </Link>
        ))}
      </div>
    </PageShell>
  );
}
