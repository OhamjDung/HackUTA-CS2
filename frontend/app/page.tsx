import dynamic from 'next/dynamic';
import ModeRoute from '@/components/mode/ModeRoute';
import OdysseyExperience from '@/modes/odyssey/OdysseyExperience';
import { resolveMode } from '@/lib/mode/contract';

// The query-resolved server boundary keeps mode markup identical through hydration.
const FazeHome = dynamic(() => import('@/components/faze/FazeHome'));

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const mode = resolveMode(await searchParams);
  return <ModeRoute mode={mode}>{mode === 'odyssey' ? <OdysseyExperience /> : <FazeHome />}</ModeRoute>;
}
