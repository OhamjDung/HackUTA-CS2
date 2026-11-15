'use client';

import { useCallback, useEffect, useState } from 'react';

const AUDIO_URL = '/audio/odyssey-theme.mp3';
const MUTE_KEY = 'doppelgamer.odyssey.musicMuted';
const ROUTE_GRACE_MS = 180;

type MusicSnapshot = { muted: boolean; playing: boolean; started: boolean; unavailable: boolean };

let audio: HTMLAudioElement | null = null;
let desiredPlayback = false;
let mountedControllers = 0;
let pauseTimer: number | null = null;
let snapshot: MusicSnapshot = { muted: false, playing: false, started: false, unavailable: false };
const subscribers = new Set<(next: MusicSnapshot) => void>();

function publish(next: Partial<MusicSnapshot>) {
  snapshot = { ...snapshot, ...next };
  subscribers.forEach((subscriber) => subscriber(snapshot));
}

function getAudio(): HTMLAudioElement | null {
  if (typeof window === 'undefined') return null;
  if (!audio) {
    audio = new Audio(AUDIO_URL);
    audio.loop = true;
    audio.volume = 0.15;
    audio.preload = 'metadata';
    audio.dataset.odysseyMusic = 'true';
    audio.setAttribute('aria-hidden', 'true');
    audio.hidden = true;
    document.body.appendChild(audio);
    audio.addEventListener('play', () => publish({ playing: true, unavailable: false }));
    audio.addEventListener('pause', () => publish({ playing: false }));
    audio.addEventListener('error', () => publish({ playing: false, unavailable: true }));
  }
  return audio;
}

async function playIfAllowed() {
  const player = getAudio();
  if (!player || snapshot.muted || document.hidden || !desiredPlayback) return;
  try {
    await player.play();
  } catch {
    // Autoplay rejection or a missing file leaves the control available for retry.
    publish({ playing: false });
  }
}

function pause() {
  audio?.pause();
}

export function useOdysseyMusic() {
  const [state, setState] = useState(snapshot);

  useEffect(() => {
    subscribers.add(setState);
    mountedControllers += 1;
    if (pauseTimer) {
      window.clearTimeout(pauseTimer);
      pauseTimer = null;
    }

    try {
      const saved = localStorage.getItem(MUTE_KEY);
      if (saved === 'true' || saved === 'false') publish({ muted: saved === 'true' });
    } catch {
      // Storage is optional; keep the in-memory preference.
    }

    const onVisibility = () => {
      if (document.hidden) pause();
      else void playIfAllowed();
    };
    document.addEventListener('visibilitychange', onVisibility);
    desiredPlayback = true;
    publish({ started: true });
    void playIfAllowed();

    return () => {
      subscribers.delete(setState);
      document.removeEventListener('visibilitychange', onVisibility);
      mountedControllers = Math.max(0, mountedControllers - 1);
      pauseTimer = window.setTimeout(() => {
        if (mountedControllers === 0) {
          pause();
          audio?.remove();
          audio = null;
          desiredPlayback = false;
          publish({ playing: false, started: false, unavailable: false });
        }
      }, ROUTE_GRACE_MS);
    };
  }, []);

  const start = useCallback(() => {
    desiredPlayback = true;
    publish({ started: true });
    void playIfAllowed();
  }, []);

  const toggle = useCallback(() => {
    const turnOn = snapshot.unavailable || snapshot.muted || !desiredPlayback;
    desiredPlayback = turnOn;
    publish({ muted: !turnOn, started: snapshot.started || turnOn, unavailable: false });
    try { localStorage.setItem(MUTE_KEY, String(!turnOn)); } catch { /* optional */ }
    if (turnOn) void playIfAllowed();
    else pause();
  }, []);

  return { ...state, start, toggle };
}
