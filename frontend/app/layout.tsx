import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import localFont from 'next/font/local';
import './globals.css';
import Providers from './providers';
import { resolveBrandAssets } from '@/lib/brandAssets';

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700', '800'],
  variable: '--font-inter',
  display: 'swap',
});

const mono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['500', '600', '700'],
  variable: '--font-mono',
  display: 'swap',
});

/** DSEG14 Classic (SIL OFL 1.1, see app/fonts/DSEG-LICENSE.txt): 14-segment LED glyphs. */
const led = localFont({
  src: './fonts/DSEG14Classic-Regular.woff2',
  variable: '--font-led',
  display: 'block',
});

export const metadata: Metadata = {
  title: 'DoppelGamer. — Your stream. Another dimension.',
  description: 'A mixed-reality co-host. Built for your next great moment.',
  metadataBase: new URL('http://localhost:3000'),
};

export const viewport: Viewport = {
  themeColor: '#0c0c0e',
  colorScheme: 'dark',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // Resolved per request on the server so optional assets (FaZe mark, portraits,
  // profile photo) only render when the file actually exists — no 404s.
  const brand = resolveBrandAssets();

  return (
    <html lang="en" className={`${inter.variable} ${mono.variable} ${led.variable}`}>
      <body className="min-h-screen font-sans antialiased">
        <Providers brand={brand}>{children}</Providers>
      </body>
    </html>
  );
}
