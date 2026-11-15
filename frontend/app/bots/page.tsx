import BotsHub from '@/components/bots/BotsHub';

export const metadata = { title: 'Bots — DoppelGamer.' };

/** Portraits and the selected bot come from the root-layout providers. */
export default function BotsPage() {
  return <BotsHub />;
}
