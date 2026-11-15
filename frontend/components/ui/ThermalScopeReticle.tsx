'use client';

import { useEffect, useRef } from 'react';
import { SCOPE_RADIUS_PX } from '@/lib/constants';
import { stageInput } from '@/lib/stageInput';

interface ThermalScopeReticleProps {
  /** The stage canvas container; coordinates are normalized to it. */
  containerRef: React.RefObject<HTMLDivElement | null>;
  active: boolean;
  /** Where the lens parks when opened without a pointer over the stage. */
  restPosition: () => { x: number; y: number };
}

const R = SCOPE_RADIUS_PX;
const PAD = 22;
const SIZE = (R + PAD) * 2;

/**
 * Crosshair ring drawn over the GPU thermal lens. Pointer tracking writes
 * straight to the DOM node's transform and to `stageInput` (read by the
 * shader uniforms), so following the cursor costs zero React renders.
 */
export default function ThermalScopeReticle({ containerRef, active, restPosition }: ThermalScopeReticleProps) {
  const nodeRef = useRef<HTMLDivElement>(null);
  const pointerInside = useRef(false);

  const place = (x: number, y: number) => {
    stageInput.scopeX = x;
    stageInput.scopeY = y;
    const el = containerRef.current;
    const node = nodeRef.current;
    if (!el || !node) return;
    const px = x * el.clientWidth - SIZE / 2;
    const py = y * el.clientHeight - SIZE / 2;
    node.style.transform = `translate3d(${px}px, ${py}px, 0)`;
  };

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width;
      const y = (e.clientY - r.top) / r.height;
      pointerInside.current = x >= 0 && x <= 1 && y >= 0 && y <= 1;
      if (pointerInside.current && stageInput.scopeActive) place(x, y);
      else if (pointerInside.current) {
        // Remember where the pointer is so the lens opens under it.
        stageInput.scopeX = x;
        stageInput.scopeY = y;
      }
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    return () => window.removeEventListener('pointermove', onMove);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [containerRef]);

  useEffect(() => {
    if (!active) return;
    if (pointerInside.current || stageInput.scopeAnchored) place(stageInput.scopeX, stageInput.scopeY);
    else {
      const p = restPosition();
      place(p.x, p.y);
    }
    // Keep the ring aligned through resizes.
    const onResize = () => place(stageInput.scopeX, stageInput.scopeY);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const c = SIZE / 2;
  return (
    <div
      ref={nodeRef}
      className="pointer-events-none absolute left-0 top-0 z-10 will-change-transform"
      style={{ width: SIZE, height: SIZE }}
      aria-hidden
    >
      <svg
        width={SIZE}
        height={SIZE}
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="transition-[opacity,transform] duration-200 ease-out"
        style={{ opacity: active ? 1 : 0, transform: `scale(${active ? 1 : 0.7})` }}
      >
        <circle cx={c} cy={c} r={R} fill="none" stroke="#F4F3EF" strokeWidth="2.25" />
        {/* outer ticks N/E/S/W */}
        <path
          d={`M${c} ${c - R - 16}V${c - R + 2} M${c} ${c + R - 2}V${c + R + 16} M${c - R - 16} ${c}H${c - R + 2} M${c + R - 2} ${c}H${c + R + 16}`}
          stroke="#F4F3EF"
          strokeWidth="2.25"
          strokeLinecap="round"
        />
        {/* inner brand marks */}
        <path
          d={`M${c - R + 6} ${c}H${c - R + 20} M${c + R - 20} ${c}H${c + R - 6} M${c} ${c - R + 6}V${c - R + 14} M${c} ${c + R - 14}V${c + R - 6}`}
          stroke="#FF3B1D"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <circle cx={c} cy={c} r="2" fill="#FF3B1D" />
      </svg>
    </div>
  );
}
