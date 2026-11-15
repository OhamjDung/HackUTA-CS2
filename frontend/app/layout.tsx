import type { Metadata } from 'next';
import './globals.css';
import { INITIAL_CHARACTER_ID, CHARACTER_MAP, TRANSCODER_JS, TRANSCODER_WASM } from '@/lib/constants';

export const metadata: Metadata = {
  title: 'FaZe Character Viewer',
  description: 'WebGPU character hot-swap viewer — CS2, Smash, Fortnite, FIFA, Halo blockouts.',
  metadataBase: new URL('http://localhost:3000'),
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const initialModelUrl = CHARACTER_MAP[INITIAL_CHARACTER_ID].url;

  return (
    <html lang="en">
      <head>
        {/* HLD stage 1: preload Basis transcoder + Model 1 binary for sub-second TTFF. */}
        <link rel="preload" href={TRANSCODER_WASM} as="fetch" crossOrigin="anonymous" />
        <link rel="preload" href={TRANSCODER_JS} as="script" />
        <link rel="preload" href={initialModelUrl} as="fetch" crossOrigin="anonymous" />
      </head>
      <body className="bg-black text-white antialiased">{children}</body>
    </html>
  );
}
