import { SEVERITY_LABEL, type Mistake } from '@/lib/puzzles';

/** The key mistakes found in a death, biggest first. */
export default function FeedbackList({ items, empty }: { items: Mistake[]; empty?: string }) {
  if (!items.length) {
    return <p className="text-[15px] text-[#B8B8C2]">{empty ?? 'No clear mistake found in this window.'}</p>;
  }
  return (
    <ol className="grid gap-[12px]">
      {items.map((m, i) => (
        <li key={m.id} className="rounded-[12px] border border-white/[0.14] bg-white/[0.03] p-[16px]">
          <div className="flex items-center gap-[10px]">
            <span className="font-mono text-[12.5px] text-[#9E9EA8]">{String(i + 1).padStart(2, '0')}</span>
            <span className="text-[16.5px] font-bold tracking-[-0.01em] text-white">{m.title}</span>
            <span
              className={`ml-auto rounded-full px-[10px] py-[2px] font-mono text-[11.5px] uppercase tracking-[0.06em] ${
                m.severity === 3 ? 'bg-[#E4002B]/20 text-[#ff8a9b]' : 'bg-white/[0.08] text-[#D8D8DE]'
              }`}
            >
              {SEVERITY_LABEL[m.severity]} · {m.t.toFixed(1)} s
            </span>
          </div>
          <p className="mt-[6px] text-[14.5px] leading-snug text-[#B8B8C2]">{m.detail}</p>
        </li>
      ))}
    </ol>
  );
}
