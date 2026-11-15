'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import HeroSign from '@/components/ui/HeroSign';
import styles from './DemoGate.module.css';

const ENTRY_KEY = 'doppelgamer.demoEntered';
const DEFAULT_RETURN = '/?mode=faze';

type GateState = 'checking' | 'locked' | 'entered';

export function safeInternalReturn(candidate: string, origin: string): string {
  try {
    if (!candidate.startsWith('/') || candidate.startsWith('//') || candidate.includes('\\')) return DEFAULT_RETURN;
    const url = new URL(candidate, origin);
    if (url.origin !== origin || url.username || url.password) return DEFAULT_RETURN;
    if (url.pathname.startsWith('/_next') || url.pathname.startsWith('/api')) return DEFAULT_RETURN;
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return DEFAULT_RETURN;
  }
}

export default function DemoGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [gate, setGate] = useState<GateState>('checking');
  const [returnTo, setReturnTo] = useState(DEFAULT_RETURN);

  useEffect(() => {
    const current = safeInternalReturn(`${location.pathname}${location.search}${location.hash}`, location.origin);
    setReturnTo(current);
    try {
      setGate(sessionStorage.getItem(ENTRY_KEY) === 'true' ? 'entered' : 'locked');
    } catch {
      setGate('locked');
    }
  }, []);

  const logout = () => {
    try { sessionStorage.removeItem(ENTRY_KEY); } catch { /* storage can be unavailable */ }
    setReturnTo(DEFAULT_RETURN);
    setGate('locked');
    router.replace(DEFAULT_RETURN, { scroll: false });
  };

  if (gate === 'checking') return <div className={styles.checking} aria-label="Checking demo access" />;
  if (gate === 'locked') return <DemoLogin returnTo={returnTo} onEntered={() => setGate('entered')} />;

  return <>
    {children}
    <button type="button" className={styles.logout} onClick={logout}>Log out</button>
  </>;
}

function DemoLogin({ returnTo, onEntered }: { returnTo: string; onEntered: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState('');
  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => { emailRef.current?.focus(); }, []);

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email.trim() || !password) {
      setMessage('Enter both an email and password to continue.');
      return;
    }
    setEmail('');
    setPassword('');
    setMessage('');
    try { sessionStorage.setItem(ENTRY_KEY, 'true'); } catch { /* allow this tab session in memory */ }
    // The current location already is the validated requested route; no credentials enter navigation.
    if (safeInternalReturn(returnTo, location.origin) !== `${location.pathname}${location.search}${location.hash}`) {
      history.replaceState(null, '', safeInternalReturn(returnTo, location.origin));
    }
    onEntered();
  };

  return <main className={styles.login}>
    {/* Same 14-segment sign as the FaZe home page; the background image no longer carries its own. */}
    <HeroSign className={styles.sign} />
    <form className={styles.panel} onSubmit={submit} noValidate autoComplete="off">
      <h1 className={styles.eyebrow}>Welcome back</h1>
      <label>Email<input ref={emailRef} name="demo-email" type="text" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="off" /></label>
      <label>Password<span className={styles.passwordField}><input name="demo-password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="off" /><button type="button" onClick={() => setShowPassword((shown) => !shown)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? 'Hide' : 'Show'}</button></span></label>
      {message && <p className={styles.error} role="alert">{message}</p>}
      <button className={styles.enter} type="submit">Enter DoppelGamer</button>
      <p className={styles.note}>Demo login — use any email and password.</p>
    </form>
  </main>;
}

