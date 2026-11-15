'use client';

import Image from 'next/image';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { useSessionUploads } from '@/app/providers';
import ModeLink from '@/components/mode/ModeLink';
import ModeSwitch from '@/components/mode/ModeSwitch';
import styles from './OdysseyExperience.module.css';
import { useOdysseyMusic } from './useOdysseyMusic';

type OdysseyBotId = 'telemachus' | 'menelaus' | 'odysseus' | 'poseidon';
const BOTS: Array<{ id: OdysseyBotId; name: string; role: string; dialogue: string }> = [
  { id: 'telemachus', name: 'Telemachus', role: 'The Heir', dialogue: 'A name is earned. Will you help me earn mine?' },
  { id: 'menelaus', name: 'Menelaus', role: 'The Warlord', dialogue: 'Stand your ground, and history may remember you.' },
  { id: 'odysseus', name: 'Odysseus', role: 'The Strategist', dialogue: 'I have faced the seas. Can you face me?' },
  { id: 'poseidon', name: 'Poseidon', role: 'The Tempest', dialogue: 'The tide answers to me. How long will you endure?' },
];
const BOT_IDS = new Set(BOTS.map((bot) => bot.id));
const BOT_KEY = 'doppelgamer.odyssey.selectedBot';
const NAV = [['/', 'Home'], ['/bots', 'Bots'], ['/scenes', 'Scene'], ['/leaderboard', 'Leaderboard']] as const;

export default function OdysseyExperience() {
  const pathname = usePathname() ?? '/';
  const search = useSearchParams();
  const router = useRouter();
  const selectionNavigation = useRef<number | null>(null);
  const urlBot = search.get('bot');
  const [selectedId, setSelectedId] = useState<OdysseyBotId>(BOT_IDS.has(urlBot as OdysseyBotId) ? urlBot as OdysseyBotId : 'odysseus');
  const music = useOdysseyMusic();

  useEffect(() => {
    const explicit = search.get('bot');
    if (BOT_IDS.has(explicit as OdysseyBotId)) {
      setSelectedId(explicit as OdysseyBotId);
      try { sessionStorage.setItem(BOT_KEY, explicit!); } catch { /* unavailable storage */ }
      return;
    }
    try {
      const saved = sessionStorage.getItem(BOT_KEY);
      if (BOT_IDS.has(saved as OdysseyBotId)) setSelectedId(saved as OdysseyBotId);
    } catch { /* keep deterministic default */ }
  }, [search]);

  useEffect(() => () => {
    if (selectionNavigation.current) window.clearTimeout(selectionNavigation.current);
  }, []);

  const selectBot = (id: OdysseyBotId) => {
    setSelectedId(id);
    try { sessionStorage.setItem(BOT_KEY, id); } catch { /* keep in memory */ }
    if (pathname === '/bots') {
      if (selectionNavigation.current) window.clearTimeout(selectionNavigation.current);
      selectionNavigation.current = window.setTimeout(
        () => router.replace(`/bots?mode=odyssey&bot=${id}`, { scroll: false }),
        90,
      );
    }
  };

  return <main className={styles.shell} data-odyssey-route={pathname}>
    <Header pathname={pathname} selectedId={selectedId} music={music} />
    {pathname === '/' && <Home selectedId={selectedId} onSelect={selectBot} onBegin={music.start} />}
    {pathname === '/bots' && <><PageIntro n="01" eyebrow="The challengers" title="Choose your legend" body="Four rivals. Four styles. One epic challenge." /><Bots selectedId={selectedId} onSelect={selectBot} /></>}
    {pathname === '/scenes' && <><PageIntro n="02" eyebrow="Your next chapter" title="Play a scene" body="Bring your own moment, or enter a legendary trial." /><Scenes detailed /></>}
    {pathname === '/leaderboard' && <><PageIntro n="03" eyebrow="The hall of heroes" title="Claim your crown" body="Illustrative rankings until live scoring is connected." /><Leaderboard /></>}
    {pathname === '/play' && <Play selectedId={selectedId} />}
    {pathname === '/studio' && <Studio selectedId={selectedId} />}
    <Footer />
  </main>;
}

function Header({ pathname, selectedId, music }: { pathname: string; selectedId: OdysseyBotId; music: ReturnType<typeof useOdysseyMusic> }) {
  const soundOn = music.playing && !music.muted;
  const label = music.unavailable ? 'Odyssey music unavailable — retry' : soundOn ? 'Turn Odyssey music off' : 'Turn Odyssey music on';
  return <header className={styles.header}><ModeLink href="/" className={styles.brand} aria-label="DoppelGamer Odyssey home">DOPPELGAMER<span>THE ODYSSEY EVENT</span></ModeLink><nav aria-label="Odyssey primary">{NAV.map(([href, navLabel]) => <ModeLink key={href} href={href} aria-current={pathname === href ? 'page' : undefined}>{navLabel}</ModeLink>)}</nav><div className={styles.headerActions}><button type="button" className={styles.soundToggle} aria-label={label} aria-pressed={soundOn} title={label} onClick={music.toggle}><span aria-hidden>{soundOn ? '♪' : '♪̸'}</span></button><ModeSwitch compact /><ModeLink href={`/play?bot=${selectedId}`} className={styles.outlineButton}>Enter the event</ModeLink></div></header>;
}

function Home({ selectedId, onSelect, onBegin }: { selectedId: OdysseyBotId; onSelect: (id: OdysseyBotId) => void; onBegin: () => void }) {
  return <><section className={styles.hero}><div className={styles.heroCopy}><p>A new legend begins</p><h1>Doppel<br />Gamer</h1><h2>The Odyssey Event</h2><ModeLink href={`/play?bot=${selectedId}`} className={styles.blueButton} onClick={onBegin}>Begin your Odyssey <span>→</span></ModeLink></div><a href="#odyssey-intro" className={styles.scrollCue}>Scroll to discover <span>⌄</span></a></section><section id="odyssey-intro" className={styles.intro}><div><h2>This is<br />the Odyssey event</h2><p>Step into the arena and play with Odyssey bots.</p><h3>Are you ready<br />for the challenge?</h3></div></section><PageIntro n="01" eyebrow="The challengers" title="Choose your legend" body="Four rivals. Four styles. One epic challenge." /><Bots selectedId={selectedId} onSelect={onSelect} /><PageIntro n="02" eyebrow="Your next chapter" title="Play a scene" /><Scenes /><PageIntro n="03" eyebrow="The hall of heroes" title="Claim your crown" /><Leaderboard compact /></>;
}

function PageIntro({ n, eyebrow, title, body }: { n: string; eyebrow: string; title: string; body?: string }) {
  return <div className={styles.pageIntro}><p>{n} / {eyebrow}</p><h1>{title}</h1>{body && <span>{body}</span>}</div>;
}

function Bots({ selectedId, onSelect }: { selectedId: OdysseyBotId; onSelect: (id: OdysseyBotId) => void }) {
  const bot = BOTS.find((item) => item.id === selectedId)!;
  const [revealed, setRevealed] = useState(true);
  const revealTimer = useRef<number | null>(null);
  useEffect(() => { setRevealed(false); if (revealTimer.current) clearTimeout(revealTimer.current); revealTimer.current = window.setTimeout(() => setRevealed(true), 80); return () => { if (revealTimer.current) clearTimeout(revealTimer.current); }; }, [selectedId]);
  return <section className={styles.botsSection} aria-label="Odyssey challengers"><div className={styles.roster} role="list">{BOTS.map((item) => <button key={item.id} type="button" aria-pressed={selectedId === item.id} onClick={() => onSelect(item.id)}><span><Image src={`/images/odyssey/bots/${item.id}.png`} alt="" width={188} height={188} /></span><strong>{item.name}</strong><small>{item.role}</small></button>)}</div><article key={bot.id} className={`${styles.feature} ${revealed ? styles.revealed : ''}`}><Image src={`/images/odyssey/bots/${bot.id}-feature.png`} alt={`Engraved illustration of ${bot.name}`} width={1819} height={865} /><div className={styles.dialogue}><p aria-live="polite">{bot.dialogue}</p><span className={styles.typing} aria-hidden><i /><i /><i /></span></div><div className={styles.featureMeta}><h2>{bot.name} <span>/ {bot.role}</span></h2><ModeLink href={`/play?bot=${bot.id}`} className={styles.blueButton}>Challenge {bot.name} <span>→</span></ModeLink></div></article></section>;
}

function Scenes({ detailed = false }: { detailed?: boolean }) {
  const search = useSearchParams();
  const uploads = useSessionUploads();
  const input = useRef<HTMLInputElement>(null);
  const tab = search.get('tab');
  return <section className={styles.scenesSection} aria-label="Odyssey scenes"><div className={styles.sceneGrid}><ModeLink href="/scenes?tab=upload" className={styles.sceneCard}><Image src="/images/odyssey/scenes/your-games-arena.png" alt="Ancient arena overlooking the sea" fill sizes="(max-width: 760px) 100vw, 50vw" /><span><strong>Your games</strong><small>Upload a clip or demo</small><b>→</b></span></ModeLink><ModeLink href="/scenes?tab=famous" className={styles.sceneCard}><Image src="/images/odyssey/scenes/legendary-scenes-temple.png" alt="Greek temple beside the Aegean sea" fill sizes="(max-width: 760px) 100vw, 50vw" /><span><strong>Legendary scenes</strong><small>Explore curated challenges</small><b>→</b></span></ModeLink></div>{detailed && tab === 'upload' && <div className={styles.flowPanel}><h2>Your game</h2><p>Uploads stay in this browser tab. Match reconstruction is not connected yet.</p><button type="button" onClick={() => input.current?.click()}>Choose a demo or clip</button><input ref={input} hidden type="file" accept=".dem,.mp4,.mov,.webm,.mkv" onChange={(event) => uploads.setUpload('odyssey', event.target.files?.[0] ?? null)} />{uploads.odyssey && <strong>Ready: {uploads.odyssey.name}</strong>}</div>}{detailed && tab === 'famous' && <div className={styles.flowPanel}><h2>Legendary scenes</h2><p>Curated Odyssey challenges are preview content. Live scene loading is not connected yet.</p><ModeLink href="/play?scene=legendary">Continue with a legendary trial →</ModeLink></div>}</section>;
}

const RANKS = [['01', 'Ithaca', '24', '2,840'], ['02', 'Blueoracle', '21', '2,610'], ['03', 'Aegis', '19', '2,390'], ['04', 'Seaborn', '17', '2,180'], ['05', 'You', '12', '1,760']];
function Leaderboard({ compact = false }: { compact?: boolean }) {
  return <section className={`${styles.leaderboard} ${compact ? styles.compact : ''}`}><table><caption>Sample rankings — live scoring is not connected</caption><thead><tr><th>Rank</th><th>Player</th><th>Wins</th><th>Points</th></tr></thead><tbody>{RANKS.map((row, index) => <tr key={row[0]}><td>{row[0]}</td><th scope="row">{row[1]} {index === 0 && <span className={styles.crown} aria-label="First place">♛</span>}</th><td>{row[2]}</td><td>{row[3]}</td></tr>)}</tbody></table></section>;
}

function Play({ selectedId }: { selectedId: OdysseyBotId }) {
  const search = useSearchParams();
  const id = BOT_IDS.has(search.get('bot') as OdysseyBotId) ? search.get('bot') as OdysseyBotId : selectedId;
  const bot = BOTS.find((item) => item.id === id)!;
  const scene = search.get('scene') === 'legendary' ? 'Legendary trial' : search.get('scene') === 'upload' ? 'Your uploaded game' : 'Quick challenge';
  return <section className={styles.setup}><PageIntro n="04" eyebrow="Prepare for glory" title="Enter the arena" /><div className={styles.setupGrid}><article><Image src={`/images/odyssey/bots/${bot.id}.png`} alt="" width={180} height={180} /><div><small>Challenger</small><h2>{bot.name}</h2><p>{bot.role}</p><ModeLink href="/bots">Change legend</ModeLink></div></article><article><small>Scene</small><h2>{scene}</h2><p>The match service is not connected to this frontend yet.</p><ModeLink href="/scenes">Change scene</ModeLink></article><ModeLink href={`/studio?bot=${bot.id}${search.get('scene') ? `&scene=${search.get('scene')}` : ''}`} className={styles.blueButton}>Enter studio →</ModeLink></div></section>;
}

function Studio({ selectedId }: { selectedId: OdysseyBotId }) {
  const search = useSearchParams();
  const id = BOT_IDS.has(search.get('bot') as OdysseyBotId) ? search.get('bot') as OdysseyBotId : selectedId;
  const bot = BOTS.find((item) => item.id === id)!;
  return <section className={styles.setup}><PageIntro n="05" eyebrow="The arena" title="Your challenge awaits" /><div className={styles.studioCard}><Image src={`/images/odyssey/bots/${bot.id}-feature.png`} alt={`Engraved illustration of ${bot.name}`} width={1819} height={865} /><div><small>Selected legend</small><h2>{bot.name}</h2><p>Studio launching is a preview. No live match has been started.</p><ModeLink href={`/play?bot=${bot.id}`} className={styles.blueButton}>Back to setup →</ModeLink></div></div></section>;
}

function Footer() { return <footer className={styles.footer}><div><ModeLink href="/" className={styles.brand}>DOPPELGAMER<span>THE ODYSSEY EVENT</span></ModeLink><nav aria-label="Odyssey footer">{NAV.map(([href, label]) => <ModeLink key={href} href={href}>{label}</ModeLink>)}</nav></div></footer>; }
