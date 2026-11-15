'use client';

import { usePathname } from 'next/navigation';
import ModeLink from '@/components/mode/ModeLink';
import ModeSwitch from '@/components/mode/ModeSwitch';
import styles from './OdysseyExperience.module.css';

const LINKS = [
  ['/', 'Mission'],
  ['/bots', 'Crew'],
  ['/scenes', 'Worlds'],
  ['/leaderboard', 'Signals'],
  ['/play', 'Launch'],
  ['/studio', 'Bridge'],
] as const;

const COPY: Record<string, { eyebrow: string; title: string; body: string }> = {
  '/': { eyebrow: 'Odyssey / Foundation', title: 'A second world, cleanly separated.', body: 'The Odyssey experience is ready for its own art direction without loading the FaZe stage.' },
  '/bots': { eyebrow: 'Crew roster', title: 'Choose an expedition partner.', body: 'Atlas and Echo are lightweight placeholders for the upcoming Odyssey roster.' },
  '/scenes': { eyebrow: 'Worlds', title: 'Chart the next destination.', body: 'Launch Bay and Deep Space reserve the scene-selection contract for Odyssey.' },
  '/leaderboard': { eyebrow: 'Signals', title: 'Expedition records arrive here.', body: 'This route is isolated from FaZe scores and bot identifiers.' },
  '/play': { eyebrow: 'Launch', title: 'Prepare the mission.', body: 'Mission configuration will land after the shared foundation is accepted.' },
  '/studio': { eyebrow: 'Bridge', title: 'Odyssey control is standing by.', body: 'No WebGPU support is required to use this mode.' },
};

export default function OdysseyExperience() {
  const pathname = usePathname() ?? '/';
  const copy = COPY[pathname] ?? COPY['/'];
  return (
    <main className={styles.shell} data-odyssey-route={pathname}>
      <header className={styles.nav}>
        <ModeLink href="/" className={styles.brand} aria-label="Odyssey home">ODYSSEY<span>FOUNDATION</span></ModeLink>
        <nav aria-label="Odyssey primary">
          {LINKS.map(([href, label]) => <ModeLink key={href} href={href} aria-current={pathname === href ? 'page' : undefined}>{label}</ModeLink>)}
        </nav>
        <ModeSwitch compact />
      </header>
      <section className={styles.hero}>
        <p className={styles.eyebrow}>{copy.eyebrow}</p>
        <h1>{copy.title}</h1>
        <div className={styles.orbit} aria-hidden><span /><span /><span /></div>
        <p className={styles.copy}>{copy.body}</p>
        <div className={styles.actions}>
          <ModeLink href={pathname === '/studio' ? '/' : '/studio'}>{pathname === '/studio' ? 'Return to mission' : 'Enter the bridge'}</ModeLink>
          <span>HTML + CSS only · no 3D runtime</span>
        </div>
      </section>
    </main>
  );
}

