import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { INITIAL_CHARACTER_ID, CHARACTER_MAP, TRANSCODER_JS, TRANSCODER_WASM } from '@/lib/constants';

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-inter',
  display: 'swap',
});

const mono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['500', '600'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'DoppelGamer. — Your stream. Another dimension.',
  description: 'A mixed-reality co-host. Built for your next great moment.',
  metadataBase: new URL('http://localhost:3000'),
};

export const viewport: Viewport = {
  themeColor: '#FAF9F6',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const initialModelUrl = CHARACTER_MAP[INITIAL_CHARACTER_ID].url;

  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <head>
        {/* Preload Basis transcoder + Model 1 binary for sub-second first frame. */}
        <link rel="preload" href={TRANSCODER_WASM} as="fetch" crossOrigin="anonymous" />
        <link rel="preload" href={TRANSCODER_JS} as="fetch" crossOrigin="anonymous" />
        <link rel="preload" href={initialModelUrl} as="fetch" crossOrigin="anonymous" />
      </head>
      <body className="bg-studio font-sans text-ink antialiased">{children}</body>
    </html>
  );
}
