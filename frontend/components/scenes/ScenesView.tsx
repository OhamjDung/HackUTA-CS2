'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';
import { useSelectedBot, useSessionUploads } from '@/app/providers';
import { CURATED_SCENES } from '@/lib/bots';
import { useModeHref } from '@/components/mode/ModeLink';

export type ScenesTab = 'upload' | 'famous';

const TABS: { id: ScenesTab; label: string; hint: string }[] = [
  { id: 'upload', label: 'Your games', hint: 'Upload a clip or demo' },
  { id: 'famous', label: 'Famous games', hint: 'Explore curated moments' },
];

const ACCEPT = '.dem,.mp4,.mov,.webm,.mkv';

const arrow = (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
    <path d="M3 9h11M10 4.5 14.5 9 10 13.5" stroke="white" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export default function ScenesView({ initialTab }: { initialTab: ScenesTab }) {
  const router = useRouter();
  const bot = useSelectedBot();
  const [tab, setTab] = useState<ScenesTab>(initialTab);
  const uploads = useSessionUploads();
  const file = uploads.faze;
  const setFile = (next: File | null) => uploads.setUpload('faze', next);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const famousHref = useModeHref('/scenes?tab=famous');
  const uploadPlayHref = useModeHref(`/play?bot=${bot.id}&scene=upload`);

  const switchTab = (t: ScenesTab) => {
    setTab(t);
    router.replace(t === 'famous' ? famousHref : famousHref.replace('tab=famous', 'tab=upload'), { scroll: false });
  };

  // The selected bot's game first. A game with no curated scenes (Smash Bros) shows the others as the main set.
  const own = CURATED_SCENES.filter((s) => s.game === bot.game);
  const rest = CURATED_SCENES.filter((s) => s.game !== bot.game);
  const famous = own.length ? own : rest;
  const others = own.length ? rest : [];
  const famousTitle = `${famous[0]?.game ?? bot.game} moments`;

  return (
    <div>
      <div className="flex gap-[clamp(10px,0.92vw,14px)]" role="tablist" aria-label="Scene source">
        {TABS.map((t) => {
          const on = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={on}
              onClick={() => switchTab(t.id)}
              className={`flex h-[40px] cursor-pointer items-center whitespace-nowrap rounded-full px-[22px] text-[16px] tracking-[-0.01em] transition-colors ${
                on ? 'bg-[#F5F4F0] font-bold text-[#111111]' : 'border border-white/[0.22] font-medium text-[#E8E8EC] hover:border-white/45'
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {tab === 'upload' ? (
        <section className="mt-[32px] grid gap-[24px] min-[1024px]:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]" aria-label="Upload your game">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const f = e.dataTransfer.files?.[0];
              if (f) setFile(f);
            }}
            className={`flex min-h-[300px] flex-col items-center justify-center rounded-[16px] border border-dashed px-8 text-center transition-colors ${
              dragOver ? 'border-brand bg-[#1a1a1e]' : 'border-white/[0.22] bg-[#131316]/80'
            }`}
          >
            <p className="text-[24px] font-bold tracking-[-0.03em] text-white">Drop a demo or clip here</p>
            <p className="mt-[10px] text-[16px] text-[#B8B8C2]">CS2 .dem files or video clips (.mp4, .mov, .webm, .mkv)</p>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="mt-[26px] flex h-[46px] cursor-pointer items-center rounded-full border border-white/[0.22] px-[24px] text-[16px] font-medium text-white transition-colors hover:border-white/45"
            >
              Browse files
            </button>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPT}
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            {file && (
              <p className="mt-[20px] font-mono text-[14px] text-white" data-upload-file>
                Ready: {file.name} · {(file.size / 1_048_576).toFixed(1)} MB
              </p>
            )}
          </div>

          <div className="flex flex-col justify-between rounded-[16px] border border-white/[0.16] bg-[#131316]/80 p-[28px]">
            <div>
              <p className="font-mono text-[13px] font-bold uppercase tracking-[0.06em] text-[#D8D8DE]">How it works</p>
              <ol className="mt-[18px] space-y-[14px] text-[16px] leading-snug text-[#B8B8C2]">
                <li><span className="font-mono text-white">01</span>&nbsp;&nbsp;Upload a round you played.</li>
                <li><span className="font-mono text-white">02</span>&nbsp;&nbsp;We rebuild it as a playable scene.</li>
                <li><span className="font-mono text-white">03</span>&nbsp;&nbsp;Replay it against {bot.name}.</li>
              </ol>
            </div>
            <button
              type="button"
              disabled={!file}
              onClick={() => router.push(uploadPlayHref)}
              className="group mt-[28px] flex h-[56px] w-full cursor-pointer items-center justify-between rounded-full bg-[#F5F4F0] pl-[26px] pr-[8px] text-[18px] font-bold text-[#111111] transition-opacity hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              {file ? `Play it vs ${bot.name}` : 'Upload a file to continue'}
              <span className="flex h-[40px] w-[40px] items-center justify-center rounded-full bg-brand">{arrow}</span>
            </button>
          </div>
        </section>
      ) : (
        <section className="mt-[32px]" aria-label="Famous games">
          <SceneGrid title={famousTitle} scenes={famous} botId={bot.id} />
          {others.length > 0 && <SceneGrid title="Other games" scenes={others} botId={bot.id} muted />}
          <p className="mt-[18px] text-[12.5px] text-[#9E9EA8]">Curated set · preview</p>
        </section>
      )}
    </div>
  );
}

function SceneGrid({
  title,
  scenes,
  botId,
  muted,
}: {
  title: string;
  scenes: typeof CURATED_SCENES;
  botId: string;
  muted?: boolean;
}) {
  return (
    <div className={muted ? 'mt-[40px]' : undefined}>
      <h2 className="text-[26px] font-bold leading-none tracking-[-0.04em] text-white">{title}</h2>
      <div className="mt-[20px] grid grid-cols-1 gap-[20px] sm:grid-cols-2 min-[1200px]:grid-cols-4">
        {scenes.map((s) => (
          <Link
            key={s.id}
            href={`/play?bot=${botId}&scene=${s.id}`}
            className={`group overflow-hidden rounded-[12px] border border-white/[0.16] bg-[#131316]/80 transition-colors hover:border-white/30 ${muted ? 'opacity-80 hover:opacity-100' : ''}`}
          >
            <span className="relative block aspect-[16/9] w-full overflow-hidden bg-gradient-to-br from-[#222228] to-[#121215]">
              {s.image ? (
                <Image src={s.image} alt={s.setting} fill sizes="(min-width:1200px) 25vw, 50vw" className="object-cover transition-transform duration-500 group-hover:scale-[1.04]" />
              ) : (
                <span className="absolute inset-0 flex items-center justify-center font-mono text-[13px] uppercase tracking-[0.14em] text-white/40">{s.setting}</span>
              )}
            </span>
            <span className="block p-[16px]">
              <span className="font-mono text-[11.5px] font-bold uppercase tracking-[0.06em] text-[#9E9EA8]">
                {s.game} · {s.setting}
              </span>
              <span className="mt-[6px] block text-[18.5px] font-bold leading-tight tracking-[-0.02em] text-white">{s.title}</span>
              <span className="mt-[6px] block text-[15px] leading-snug text-[#B8B8C2]">{s.blurb}</span>
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
