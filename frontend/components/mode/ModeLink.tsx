'use client';

import Link, { type LinkProps } from 'next/link';
import { useSearchParams } from 'next/navigation';
import { forwardRef } from 'react';
import { modeHref } from '@/lib/mode/contract';
import { useAppMode } from './ModeRoute';

type Props = Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, keyof LinkProps | 'href'> &
  LinkProps & { href: string };

const ModeLink = forwardRef<HTMLAnchorElement, Props>(function ModeLink({ href, ...props }, ref) {
  return <Link ref={ref} href={useModeHref(href)} {...props} />;
});

export default ModeLink;

export function useModeHref(href: string): string {
  const { mode } = useAppMode();
  const searchParams = useSearchParams();
  const url = new URL(href, 'http://mode.local');
  const source = new URLSearchParams(searchParams.toString());
  url.searchParams.forEach((value, key) => source.set(key, value));
  return modeHref(url.pathname, mode, source);
}

