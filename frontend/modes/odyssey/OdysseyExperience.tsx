'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
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

/** Layered art cut by `scripts/odyssey-layers/split.py`. Every layer is the full picture size. */
const LAYERS = '/images/odyssey/layers';

const useIsoLayoutEffect = typeof window === 'undefined' ? useEffect : useLayoutEffect;
const cssVars = (vars: Record<string, string | number>) => vars as React.CSSProperties;

function motionAllowed(): boolean {
  if (typeof window === 'undefined') return false;
  return !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// The page component remounts on every Odyssey route change. A remount soon after an
// unmount is a move inside Odyssey; anything else is an arrival (first load or from FaZe).
let lastUnmountAt = -Infinity;

export default function OdysseyExperience() {
  const pathname = usePathname() ?? '/';
  const search = useSearchParams();
  const router = useRouter();
  const selectionNavigation = useRef<number | null>(null);
  const shellRef = useRef<HTMLElement>(null);
  const urlBot = search.get('bot');
  const [selectedId, setSelectedId] = useState<OdysseyBotId>(BOT_IDS.has(urlBot as OdysseyBotId) ? urlBot as OdysseyBotId : 'odysseus');
  const [wash, setWash] = useState(false);
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

  useMotionSystem(shellRef, setWash);

  // Backstop for the arrival wash: a page opened in a background tab never runs the
  // animation, so `animationend` never fires and the wash would cover the page for good.
  useEffect(() => {
    if (!wash) return;
    const timer = window.setTimeout(() => setWash(false), 1300);
    return () => window.clearTimeout(timer);
  }, [wash]);

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

  return <main ref={shellRef} className={styles.shell} data-odyssey-route={pathname}>
    <Header pathname={pathname} selectedId={selectedId} music={music} />
    {pathname === '/' && <Home selectedId={selectedId} onSelect={selectBot} onBegin={music.start} />}
    {pathname === '/bots' && <><PageIntro n="01" eyebrow="The challengers" title="Choose your legend" body="Four rivals. Four styles. One epic challenge." /><Bots selectedId={selectedId} onSelect={selectBot} /></>}
    {pathname === '/scenes' && <><PageIntro n="02" eyebrow="Your next chapter" title="Play a scene" body="Bring your own moment, or enter a legendary trial." /><Scenes detailed /></>}
    {pathname === '/leaderboard' && <><PageIntro n="03" eyebrow="The hall of heroes" title="Claim your crown" body="Illustrative rankings until live scoring is connected." /><Leaderboard /></>}
    {pathname === '/play' && <Play selectedId={selectedId} />}
    {pathname === '/studio' && <Studio selectedId={selectedId} />}
    <Footer />
    {wash && <div className={styles.inkWash} aria-hidden onAnimationEnd={() => setWash(false)} />}
  </main>;
}

/**
 * One place for the page's motion plumbing:
 * - `data-motion` on the shell turns on entrances and loops (never under reduced motion);
 * - one IntersectionObserver marks `[data-reveal]` / `[data-stage]` elements `data-shown` the first
 *   time they scroll into view, and toggles `data-inview` on `[data-loop]` sections so their loops
 *   pause off screen; a MutationObserver picks up elements added later (route and tab changes);
 * - pointer position (`--px`, `--py`, -1..1) and hero scroll progress (`--hero-p`, 0..1) are written
 *   as CSS variables, so parallax needs no React renders.
 */
function useMotionSystem(shellRef: React.RefObject<HTMLElement | null>, setWash: (on: boolean) => void) {
  // Layout effect: `data-motion` must be set before the first paint, or revealed content flashes.
  useIsoLayoutEffect(() => {
    const shell = shellRef.current;
    if (!shell) return;
    const motion = motionAllowed();
    if (motion) shell.dataset.motion = 'on';
    if (motion && performance.now() - lastUnmountAt > 1000) setWash(true);

    const reveal = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        const el = entry.target as HTMLElement;
        if (el.hasAttribute('data-loop')) {
          if (entry.isIntersecting) el.dataset.inview = 'true';
          else delete el.dataset.inview;
        }
        if (entry.isIntersecting && (el.hasAttribute('data-reveal') || el.hasAttribute('data-stage'))) {
          el.dataset.shown = 'true';
          if (!el.hasAttribute('data-loop')) reveal.unobserve(el);
        }
      }
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
    const watched = new WeakSet<Element>();
    const scan = () => shell.querySelectorAll('[data-reveal],[data-stage],[data-loop]').forEach((el) => {
      if (watched.has(el)) return;
      watched.add(el);
      reveal.observe(el);
    });
    scan();
    const mutations = new MutationObserver(scan);
    mutations.observe(shell, { childList: true, subtree: true });

    let frame = 0;
    let px = 0;
    let py = 0;
    const write = () => {
      frame = 0;
      shell.style.setProperty('--px', px.toFixed(3));
      shell.style.setProperty('--py', py.toFixed(3));
      const hero = shell.querySelector<HTMLElement>('[data-hero]');
      if (hero) shell.style.setProperty('--hero-p', Math.min(1, Math.max(0, window.scrollY / hero.offsetHeight)).toFixed(3));
    };
    const queue = () => { if (!frame) frame = requestAnimationFrame(write); };
    const onMove = (event: PointerEvent) => {
      if (event.pointerType !== 'mouse') return;
      px = (event.clientX / window.innerWidth) * 2 - 1;
      py = (event.clientY / window.innerHeight) * 2 - 1;
      queue();
    };
    if (motion) {
      window.addEventListener('pointermove', onMove, { passive: true });
      window.addEventListener('scroll', queue, { passive: true });
      queue();
    }

    return () => {
      lastUnmountAt = performance.now();
      reveal.disconnect();
      mutations.disconnect();
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('scroll', queue);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [shellRef, setWash]);
}

/** Pointer position inside one element, as CSS variables, for tilt, sheen and card parallax. */
const tilt = {
  onPointerMove(event: React.PointerEvent<HTMLElement>) {
    if (event.pointerType !== 'mouse') return;
    const el = event.currentTarget;
    const r = el.getBoundingClientRect();
    const x = (event.clientX - r.left) / r.width;
    const y = (event.clientY - r.top) / r.height;
    el.style.setProperty('--mx', `${(x * 100).toFixed(1)}%`);
    el.style.setProperty('--my', `${(y * 100).toFixed(1)}%`);
    el.style.setProperty('--tx', (x * 2 - 1).toFixed(3));
    el.style.setProperty('--ty', (y * 2 - 1).toFixed(3));
  },
  onPointerLeave(event: React.PointerEvent<HTMLElement>) {
    const el = event.currentTarget;
    el.style.setProperty('--tx', '0');
    el.style.setProperty('--ty', '0');
  },
};

type Layer = { name: string; className?: string; depth?: number };

/**
 * A stack of same-size layers. `cover` makes the stack cover its (sized) parent the way a
 * `background-size: cover` image would, keeping the picture's aspect ratio, so a layer's
 * `transform-origin` in percent is a point on the picture.
 */
function Stack({ dir, width, height, layers, cover = false, anchor = 'bottom', eager = false, className = '', children }: {
  dir: string; width: number; height: number; layers: Layer[]; cover?: boolean; anchor?: 'bottom' | 'center';
  eager?: boolean; className?: string; children?: React.ReactNode;
}) {
  return <div
    className={`${styles.stack} ${cover ? styles.cover : ''} ${anchor === 'center' ? styles.coverCenter : ''} ${className}`}
    style={cssVars({ '--ar': `${width} / ${height}`, '--ar-n': (width / height).toFixed(5) })}
    aria-hidden
  >
    {layers.map((layer) => <img
      key={layer.name}
      src={`${LAYERS}/${dir}/${layer.name}.webp`}
      alt=""
      draggable={false}
      decoding="async"
      loading={eager ? 'eager' : 'lazy'}
      className={`${styles.layer} ${layer.depth ? styles.depth : ''} ${layer.className ?? ''}`}
      style={layer.depth ? cssVars({ '--d': layer.depth }) : undefined}
    />)}
    {children}
  </div>;
}

/** Text split into words of letters, each with `--i`, for staggered letter entrances. */
function Letters({ text, start = 0 }: { text: string; start?: number }) {
  let i = start;
  const words = text.split(' ');
  // Spaces sit between the word boxes: a trailing space inside an inline-block collapses.
  return <>{words.map((word, w) => <span key={w}>
    <span className={styles.word} aria-hidden>
      {[...word].map((ch) => <span key={i} className={styles.letter} style={cssVars({ '--i': i++ })}>{ch}</span>)}
    </span>
    {w < words.length - 1 ? ' ' : null}
  </span>)}</>;
}

function Header({ pathname, selectedId, music }: { pathname: string; selectedId: OdysseyBotId; music: ReturnType<typeof useOdysseyMusic> }) {
  const soundOn = music.playing && !music.muted;
  const label = music.unavailable ? 'Odyssey music unavailable — retry' : soundOn ? 'Turn Odyssey music off' : 'Turn Odyssey music on';
  return <header className={styles.header}>
    <ModeLink href="/" className={styles.brand} aria-label="DoppelGamer Odyssey home">
      <b className={styles.brandMark}>DOPPELGAMER</b>
      <span className={styles.brandSub}><Letters text="THE ODYSSEY EVENT" /></span>
    </ModeLink>
    <nav aria-label="Odyssey primary">{NAV.map(([href, navLabel]) => <ModeLink key={href} href={href} aria-current={pathname === href ? 'page' : undefined}>{navLabel}</ModeLink>)}</nav>
    <div className={styles.headerActions}>
      <button type="button" className={styles.soundToggle} aria-label={label} aria-pressed={soundOn} title={label} onClick={music.toggle}>
        <span className={styles.bars} aria-hidden><i /><i /><i /></span>
      </button>
      <ModeSwitch compact />
      <ModeLink href={`/play?bot=${selectedId}`} className={styles.outlineButton}><span>Enter the event</span></ModeLink>
    </div>
  </header>;
}

const HERO_LAYERS: Layer[] = [
  { name: 'paper' },
  { name: 'land', depth: 2 },
  { name: 'columnLeft', depth: 4, className: styles.heroColumn },
  { name: 'columnRight', depth: 4, className: styles.heroColumn },
  { name: 'waves', depth: 8, className: styles.heroWaves },
  { name: 'ship', depth: 6, className: styles.heroShip },
  { name: 'helmet', depth: 11, className: styles.heroHelmet },
];

function Home({ selectedId, onSelect, onBegin }: { selectedId: OdysseyBotId; onSelect: (id: OdysseyBotId) => void; onBegin: () => void }) {
  return <>
    <section className={styles.hero} data-hero data-loop>
      <Stack dir="hero" width={1536} height={1024} layers={HERO_LAYERS} cover eager className={styles.heroArt} />
      <div className={styles.burn} aria-hidden />
      <div className={styles.heroCopy}>
        <p data-reveal style={cssVars({ '--i': 0 })}>A new legend begins</p>
        <h1 aria-label="DoppelGamer">
          <span data-reveal style={cssVars({ '--i': 1 })} aria-hidden>Doppel</span>
          <span data-reveal style={cssVars({ '--i': 2 })} aria-hidden>Gamer</span>
        </h1>
        <h2 data-reveal style={cssVars({ '--i': 3 })}>The Odyssey Event</h2>
        <div data-reveal style={cssVars({ '--i': 4 })}>
          <ModeLink href={`/play?bot=${selectedId}`} className={styles.blueButton} onClick={onBegin}>Begin your Odyssey <span>→</span></ModeLink>
        </div>
      </div>
      <a href="#odyssey-intro" className={styles.scrollCue}>Scroll to discover <span aria-hidden>⌄</span></a>
    </section>
    <section id="odyssey-intro" className={styles.intro} data-stage data-loop>
      <Stack dir="intro" width={1774} height={887} cover anchor="center" className={styles.introArt} layers={[
        { name: 'paper' },
        { name: 'rest' },
        { name: 'meander', className: styles.introMeander },
        { name: 'olivesTop', className: styles.introOlivesTop },
        { name: 'olivesLow', className: styles.introOlivesLow },
        { name: 'amphora', className: styles.introAmphora },
        { name: 'hermes', className: styles.introHermes },
      ]} />
      <div className={styles.introCopy}>
        <h2>
          <span data-reveal style={cssVars({ '--i': 0 })}>This is</span>
          <span data-reveal style={cssVars({ '--i': 1 })}>the Odyssey event</span>
        </h2>
        <p data-reveal style={cssVars({ '--i': 2 })}>Step into the arena and play with Odyssey bots.</p>
        <h3>
          <span data-reveal style={cssVars({ '--i': 3 })}>Are you ready</span>
          <span data-reveal style={cssVars({ '--i': 4 })}>for the challenge?</span>
        </h3>
      </div>
    </section>
    <PageIntro n="01" eyebrow="The challengers" title="Choose your legend" body="Four rivals. Four styles. One epic challenge." />
    <Bots selectedId={selectedId} onSelect={onSelect} />
    <PageIntro n="02" eyebrow="Your next chapter" title="Play a scene" />
    <Scenes />
    <PageIntro n="03" eyebrow="The hall of heroes" title="Claim your crown" />
    <Leaderboard compact />
  </>;
}

function PageIntro({ n, eyebrow, title, body }: { n: string; eyebrow: string; title: string; body?: string }) {
  return <div className={styles.pageIntro} data-stage>
    <p><span className={styles.introNum}>{n}</span> {eyebrow}</p>
    <h1 aria-label={title}><Letters text={title} /></h1>
    <i className={styles.rule} aria-hidden />
    {body && <span className={styles.introBody}>{body}</span>}
  </div>;
}

/** Portrait coin: face disc plus a separate Greek-key ring that can turn. */
function Medal({ id }: { id: OdysseyBotId }) {
  return <span className={styles.medal}>
    <img src={`${LAYERS}/portraits/${id}-face.webp`} alt="" draggable={false} decoding="async" />
    <img src={`${LAYERS}/portraits/${id}-ring.webp`} alt="" draggable={false} decoding="async" className={styles.ring} />
    <i className={styles.sheen} aria-hidden />
  </span>;
}

function Bots({ selectedId, onSelect }: { selectedId: OdysseyBotId; onSelect: (id: OdysseyBotId) => void }) {
  const bot = BOTS.find((item) => item.id === selectedId)!;
  return <section className={styles.botsSection} aria-label="Odyssey challengers">
    <div className={styles.roster} role="group" aria-label="Choose a challenger">
      {BOTS.map((item, index) => <button key={item.id} type="button" aria-pressed={selectedId === item.id} onClick={() => onSelect(item.id)} data-reveal style={cssVars({ '--i': index })} {...tilt}>
        <span className={styles.medalTilt}><Medal id={item.id} /></span>
        <strong>{item.name}</strong>
        <small>{item.role}</small>
      </button>)}
    </div>
    <Feature bot={bot} />
  </section>;
}

function useTypedText(text: string, start: boolean): number {
  const [count, setCount] = useState(text.length);
  useIsoLayoutEffect(() => {
    if (!motionAllowed()) { setCount(text.length); return; }
    setCount(0);
    if (!start) return;
    let typed = 0;
    let interval = 0;
    const delay = window.setTimeout(() => {
      interval = window.setInterval(() => {
        typed += 1;
        setCount(typed);
        if (typed >= text.length) window.clearInterval(interval);
      }, 28);
    }, 950);
    return () => { window.clearTimeout(delay); window.clearInterval(interval); };
  }, [text, start]);
  return count;
}

function useSeen(ref: React.RefObject<HTMLElement | null>): boolean {
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([entry]) => { if (entry.isIntersecting) { setSeen(true); io.disconnect(); } }, { threshold: 0.3 });
    io.observe(el);
    return () => io.disconnect();
  }, [ref]);
  return seen;
}

function FeatureLayers({ id, phase }: { id: OdysseyBotId; phase: 'enter' | 'leave' }) {
  return <Stack dir={`${id}-feature`} width={1819} height={865} className={`${styles.featureGroup} ${phase === 'enter' ? styles.enter : styles.leave}`} layers={[
    { name: 'figure', className: styles.figure },
    { name: 'waves', className: styles.featureWaves },
    { name: 'cloud', className: styles.cloud },
  ]} />;
}

/** The selected bot's card. On a change the old figure sinks behind its waves and the new one rises. */
function Feature({ bot, compact = false }: { bot: (typeof BOTS)[number]; compact?: boolean }) {
  const [current, setCurrent] = useState(bot.id);
  const [leaving, setLeaving] = useState<OdysseyBotId | null>(null);
  const articleRef = useRef<HTMLElement>(null);
  const seen = useSeen(articleRef);
  const typed = useTypedText(bot.dialogue, seen);

  useEffect(() => {
    if (bot.id === current) return;
    setLeaving(current);
    setCurrent(bot.id);
    const timer = window.setTimeout(() => setLeaving(null), 700);
    return () => window.clearTimeout(timer);
  }, [bot.id, current]);

  return <article ref={articleRef} className={styles.feature} data-stage data-loop>
    <div className={styles.featureArt} aria-hidden>
      <img src={`${LAYERS}/${current}-feature/paper.webp`} alt="" className={`${styles.layer} ${styles.softPaper}`} draggable={false} decoding="async" />
      {leaving && <FeatureLayers key={`leave-${leaving}`} id={leaving} phase="leave" />}
      <FeatureLayers key={`enter-${current}`} id={current} phase="enter" />
    </div>
    <span className={styles.srOnly}>Engraved illustration of {bot.name}</span>
    {!compact && <div className={styles.dialogue}>
      <p className={styles.srOnly} aria-live="polite">{bot.dialogue}</p>
      <p key={bot.id} aria-hidden>{bot.dialogue.slice(0, typed)}<span className={styles.untyped}>{bot.dialogue.slice(typed)}</span></p>
      <span className={styles.typing} data-done={typed >= bot.dialogue.length || undefined} aria-hidden><i /><i /><i /></span>
    </div>}
    {!compact && <div className={styles.featureMeta}>
      <h2>{bot.name} <span>/ {bot.role}</span></h2>
      <ModeLink href={`/play?bot=${bot.id}`} className={styles.blueButton}>Challenge {bot.name} <span>→</span></ModeLink>
    </div>}
  </article>;
}

function SceneCard({ href, art, title, body }: { href: string; art: 'temple' | 'arena'; title: string; body: string }) {
  const layers: Layer[] = art === 'temple'
    ? [{ name: 'paper' }, { name: 'sun', className: styles.sun }, { name: 'mountains', depth: 3 }, { name: 'front', depth: 8 }]
    : [
      { name: 'paper' },
      { name: 'arena', depth: 3 },
      { name: 'flag1', depth: 3, className: `${styles.flag} ${styles.flag1}` },
      { name: 'flag2', depth: 3, className: `${styles.flag} ${styles.flag2}` },
      { name: 'flag3', depth: 3, className: `${styles.flag} ${styles.flag3}` },
      { name: 'flag4', depth: 3, className: `${styles.flag} ${styles.flag4}` },
      { name: 'cypressLeft', depth: 9, className: `${styles.cypress} ${styles.cypressLeft}` },
      { name: 'cypressRight', depth: 9, className: `${styles.cypress} ${styles.cypressRight}` },
    ];
  return <div className={styles.sceneSlot} data-reveal>
    <ModeLink href={href} className={styles.sceneCard} {...tilt}>
      <Stack dir={`scene-${art}`} width={1536} height={1024} cover anchor="center" layers={layers} />
      <span className={styles.sceneText}><strong>{title}</strong><small>{body}</small><b aria-hidden>→</b></span>
      <span className={styles.srOnly}>{art === 'temple' ? 'Greek temple beside the Aegean sea' : 'Ancient arena overlooking the sea'}</span>
    </ModeLink>
  </div>;
}

function Scenes({ detailed = false }: { detailed?: boolean }) {
  const search = useSearchParams();
  const uploads = useSessionUploads();
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const tab = search.get('tab');
  const takeFile = (file: File | null) => uploads.setUpload('odyssey', file);
  return <section className={styles.scenesSection} aria-label="Odyssey scenes" data-loop>
    <div className={styles.sceneGrid}>
      <SceneCard href="/scenes?tab=upload" art="arena" title="Your games" body="Upload a clip or demo" />
      <SceneCard href="/scenes?tab=famous" art="temple" title="Legendary scenes" body="Explore curated challenges" />
    </div>
    {detailed && tab === 'upload' && <div key="upload" className={styles.flowPanel}>
      <h2>Your game</h2>
      <p>Uploads stay in this browser tab. Match reconstruction is not connected yet.</p>
      <button
        type="button"
        className={styles.dropZone}
        data-dragging={dragging || undefined}
        onClick={() => input.current?.click()}
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => { event.preventDefault(); setDragging(false); takeFile(event.dataTransfer.files?.[0] ?? null); }}
      >
        <strong>Choose a demo or clip</strong>
        <small>or drop it here · .dem .mp4 .mov .webm .mkv</small>
      </button>
      <input ref={input} hidden type="file" accept=".dem,.mp4,.mov,.webm,.mkv" onChange={(event) => takeFile(event.target.files?.[0] ?? null)} />
      {uploads.odyssey && <p key={uploads.odyssey.name} className={styles.ready}><span className={styles.seal} aria-hidden>✓</span><strong>Ready: {uploads.odyssey.name}</strong></p>}
    </div>}
    {detailed && tab === 'famous' && <div key="famous" className={styles.flowPanel}>
      <h2>Legendary scenes</h2>
      <p>Curated Odyssey challenges are preview content. Live scene loading is not connected yet.</p>
      <ModeLink href="/play?scene=legendary" className={styles.blueButton}>Continue with a legendary trial <span>→</span></ModeLink>
    </div>}
  </section>;
}

/** Counts up to `value` the first time it is on screen. */
function CountUp({ value }: { value: string }) {
  const target = Number(value.replace(/,/g, ''));
  const ref = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState(value);
  useEffect(() => {
    const el = ref.current;
    if (!el || !motionAllowed()) return;
    setShown('0');
    let frame = 0;
    const io = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      io.disconnect();
      const t0 = performance.now();
      const step = (now: number) => {
        const t = Math.min(1, (now - t0) / 1100);
        const eased = 1 - Math.pow(1 - t, 3);
        setShown(Math.round(target * eased).toLocaleString('en-US'));
        if (t < 1) frame = requestAnimationFrame(step);
      };
      frame = requestAnimationFrame(step);
    }, { threshold: 0.4 });
    io.observe(el);
    return () => { io.disconnect(); cancelAnimationFrame(frame); };
  }, [target]);
  return <span ref={ref} className={styles.count}>{shown}</span>;
}

const RANKS = [['01', 'Ithaca', '24', '2,840'], ['02', 'Blueoracle', '21', '2,610'], ['03', 'Aegis', '19', '2,390'], ['04', 'Seaborn', '17', '2,180'], ['05', 'You', '12', '1,760']];
function Leaderboard({ compact = false }: { compact?: boolean }) {
  return <section className={`${styles.leaderboard} ${compact ? styles.compact : ''}`}>
    <div className={styles.tablet} data-reveal>
      <table>
        <caption>Sample rankings — live scoring is not connected</caption>
        <thead><tr><th>Rank</th><th>Player</th><th>Wins</th><th>Points</th></tr></thead>
        <tbody>{RANKS.map((row, index) => <tr key={row[0]} data-reveal data-you={row[1] === 'You' || undefined} style={cssVars({ '--i': index + 1 })}>
          <td>{row[0]}</td>
          <th scope="row">{row[1]} {index === 0 && <span className={styles.crown} role="img" aria-label="First place" />}</th>
          <td>{row[2]}</td>
          <td><CountUp value={row[3]} /></td>
        </tr>)}</tbody>
      </table>
    </div>
  </section>;
}

function Play({ selectedId }: { selectedId: OdysseyBotId }) {
  const search = useSearchParams();
  const id = BOT_IDS.has(search.get('bot') as OdysseyBotId) ? search.get('bot') as OdysseyBotId : selectedId;
  const bot = BOTS.find((item) => item.id === id)!;
  const scene = search.get('scene') === 'legendary' ? 'Legendary trial' : search.get('scene') === 'upload' ? 'Your uploaded game' : 'Quick challenge';
  return <section className={styles.setup}>
    <PageIntro n="04" eyebrow="Prepare for glory" title="Enter the arena" />
    <div className={styles.setupGrid}>
      <article data-reveal style={cssVars({ '--i': 0 })} {...tilt}>
        <span className={styles.setupMedal}><Medal id={bot.id} /></span>
        <div><small>Challenger</small><h2>{bot.name}</h2><p>{bot.role}</p><ModeLink href="/bots" className={styles.inkLink}>Change legend</ModeLink></div>
      </article>
      <article data-reveal style={cssVars({ '--i': 1 })} {...tilt}>
        <div><small>Scene</small><h2>{scene}</h2><p>The match service is not connected to this frontend yet.</p><ModeLink href="/scenes" className={styles.inkLink}>Change scene</ModeLink></div>
      </article>
      <div className={styles.setupAction} data-reveal style={cssVars({ '--i': 2 })}>
        <ModeLink href={`/studio?bot=${bot.id}${search.get('scene') ? `&scene=${search.get('scene')}` : ''}`} className={styles.blueButton}>Enter studio <span>→</span></ModeLink>
      </div>
    </div>
  </section>;
}

function Studio({ selectedId }: { selectedId: OdysseyBotId }) {
  const search = useSearchParams();
  const id = BOT_IDS.has(search.get('bot') as OdysseyBotId) ? search.get('bot') as OdysseyBotId : selectedId;
  const bot = BOTS.find((item) => item.id === id)!;
  return <section className={styles.setup}>
    <PageIntro n="05" eyebrow="The arena" title="Your challenge awaits" />
    <div className={styles.studioCard}>
      <Feature bot={bot} compact />
      <div data-reveal>
        <small>Selected legend</small>
        <h2>{bot.name}</h2>
        <p>Studio launching is a preview. No live match has been started.</p>
        <ModeLink href={`/play?bot=${bot.id}`} className={styles.blueButton}>Back to setup <span>→</span></ModeLink>
      </div>
    </div>
  </section>;
}

function Footer() {
  return <footer className={styles.footer} data-stage data-loop>
    <Stack dir="footer" width={1536} height={1024} cover className={styles.footerArt} layers={[
      { name: 'paper' },
      { name: 'meander', className: styles.footerMeander },
      { name: 'oliveLeft', className: styles.footerOliveLeft },
      { name: 'oliveRight', className: styles.footerOliveRight },
      { name: 'ship', className: styles.footerShip },
      { name: 'sea' },
    ]}>
      <span className={styles.bandWindow}><img src={`${LAYERS}/footer/band-strip.webp`} alt="" draggable={false} decoding="async" loading="lazy" className={styles.band} /></span>
    </Stack>
    <div className={styles.burn} aria-hidden />
    <div className={styles.footerContent}>
      <ModeLink href="/" className={styles.brand}><b className={styles.brandMark}>DOPPELGAMER</b><span className={styles.brandSub}>THE ODYSSEY EVENT</span></ModeLink>
      <nav aria-label="Odyssey footer">{NAV.map(([href, label]) => <ModeLink key={href} href={href}>{label}</ModeLink>)}</nav>
    </div>
  </footer>;
}
