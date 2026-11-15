'use client';

interface RightScaleRulerProps {
  activeIndex: number;
  count: number;
}

/**
 * Right-edge precision ruler: hairline ticks every 7px (long tick every 5th)
 * with the brand-red indicator dot travelling to the active character's stop.
 */
export default function RightScaleRuler({ activeIndex, count }: RightScaleRulerProps) {
  const t = count > 1 ? activeIndex / (count - 1) : 0;
  return (
    <div
      className="pointer-events-none absolute bottom-[25px] right-[12px] top-[72px] z-20 hidden w-[12px] min-[900px]:block"
      aria-hidden
    >
      <div
        className="absolute inset-y-0 right-0 w-[5px]"
        style={{
          backgroundImage:
            'repeating-linear-gradient(to bottom, #C9C8C2 0 1px, transparent 1px 7px)',
        }}
      />
      <div
        className="absolute inset-y-0 right-0 w-[9px]"
        style={{
          backgroundImage:
            'repeating-linear-gradient(to bottom, #B5B4AE 0 1px, transparent 1px 35px)',
        }}
      />
      <span
        className="absolute left-[-1px] h-[8px] w-[8px] rounded-full bg-brand transition-[top] duration-700 ease-[cubic-bezier(0.22,1,0.36,1)]"
        style={{ top: `calc(${t} * (100% - 8px))` }}
      />
    </div>
  );
}
