import dynamic from 'next/dynamic';
import ModeRoute from '@/components/mode/ModeRoute';
import OdysseyExperience from '@/modes/odyssey/OdysseyExperience';
import { resolveMode } from '@/lib/mode/contract';

const BotsHub = dynamic(() => import('@/components/bots/BotsHub'));

export const metadata = { title: 'Bots — DoppelGamer.' };

/** Portraits and the selected bot come from the root-layout providers. */
export default async function BotsPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const mode = resolveMode(await searchParams);
  return <ModeRoute mode={mode}>{mode === 'odyssey' ? <OdysseyExperience /> : <BotsHub />}</ModeRoute>;
}
