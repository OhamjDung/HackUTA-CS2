/**
 * Mutable, render-loop-shared stage input. Pointer handlers write here and the
 * WebGPU frame loop reads it every frame, so cursor tracking never triggers a
 * React re-render.
 *
 * Coordinates are normalized to the stage canvas: (0,0) top-left, (1,1) bottom-right.
 */
export const stageInput = {
  scopeX: 0.62,
  scopeY: 0.3,
  /** Scope requested open (UI state mirrors this). */
  scopeActive: false,
  /** True when the lens was opened by a click on the stage (open at that point). */
  scopeAnchored: false,
  /** performance.now() at the latest swap trigger; -Infinity when idle. */
  glitchStartedAt: Number.NEGATIVE_INFINITY,
  /** Character anchor as a fraction of stage width (measured from the layout). */
  anchorX: 0.625,
  /** Character scale so it fits the measured headline/HUD gap (1 at the reference layout). */
  anchorScale: 1,
  /** Pointer over the window, normalized −1..1 (x right, y up). Drives head look + body turn. */
  pointerX: 0,
  pointerY: 0,
  /** False until the pointer has moved, so the idle look plays first. */
  pointerSeen: false,
};
