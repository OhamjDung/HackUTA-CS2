'use client';

import { useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { RenderPipeline, WebGPURenderer } from 'three/webgpu';
import { pass } from 'three/tsl';
import { AssetManager } from '@/lib/AssetManager';
import {
  createGlitchIntensity,
  createGlitchOutputNode,
} from '@/lib/shaders/glitchPass';
import { CHARACTER_MAP, CHARACTERS } from '@/lib/constants';
import type { CharacterId } from '@/types';
import CharacterModel from './CharacterModel';
import SceneLighting from './SceneLighting';

interface CharacterCanvasProps {
  activeId: CharacterId;
  /** 0.0 (clean) → 1.0 (full glitch). Mirrors the HUD overlay. */
  glitchIntensity: number;
  /** Reports which backend actually initialized (B1: WebGPU vs WebGL2 fallback). */
  onBackendReady?: (backend: 'webgpu' | 'webgl2') => void;
}

/**
 * Owns the TSL RenderPipeline and takes over the frame loop.
 * A render priority > 0 disables R3F's automatic `gl.render`, so the only
 * path to the screen is `pipeline.render` through the glitch output node
 * (checkpoint B3). Mixer/idle updates run at default priority (0) first.
 */
function RenderDriver({ targetIntensity }: { targetIntensity: number }) {
  const gl = useThree((s) => s.gl);
  const scene = useThree((s) => s.scene);
  const camera = useThree((s) => s.camera);
  const targetRef = useRef(targetIntensity);
  targetRef.current = targetIntensity;

  const rig = useMemo(() => {
    const renderer = gl as unknown as WebGPURenderer;
    const intensity = createGlitchIntensity(0);
    const scenePass = pass(scene, camera);
    const pipeline = new RenderPipeline(renderer, createGlitchOutputNode(scenePass, intensity));
    // RenderPipeline compiles lazily; force it now so the first hot-swap is free.
    pipeline.needsUpdate = true;
    return { pipeline, intensity };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gl]);

  useEffect(() => {
    return () => {
      rig.pipeline.dispose();
    };
  }, [rig]);

  useFrame((_, delta) => {
    // Exponential approach: fast attack, smooth release, no CPU-side keyframes.
    const current = Number(rig.intensity.value);
    const next = current + (targetRef.current - current) * Math.min(1, delta * 9);
    rig.intensity.value = Math.abs(next - targetRef.current) < 0.002 ? targetRef.current : next;
    // Scene/camera are baked into the pass() node; RenderPipeline.render() takes no args.
    rig.pipeline.render();
  }, 1);

  return null;
}

export default function CharacterCanvas({ activeId, glitchIntensity, onBackendReady }: CharacterCanvasProps) {
  const managerRef = useRef<AssetManager | null>(null);
  if (!managerRef.current) managerRef.current = AssetManager.getInstance();

  // Kick off background chunk fetch (concurrency 2) once the loaders are ready.
  // AssetManager.initialize runs after the renderer backend is ready, and
  // whenReady() bridges any gap (slow backend init, background tabs).
  useEffect(() => {
    const manager = managerRef.current!;
    let cancelled = false;
    const timer = window.setTimeout(() => {
      void manager.whenReady().then(() => {
        if (cancelled) return;
        return manager.prefetchRemainingModels(
          CHARACTERS.filter((c) => c.id !== activeId).map(({ id, url }) => ({ id, url })),
        );
      });
    }, 1200);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activeConfig = CHARACTER_MAP[activeId];

  return (
    <div className="absolute inset-0 bg-black">
      <Canvas
        gl={async (props) => {
          // Force WebGPURenderer implementation with WebGL2 fallback baked into r187.
          // NOTE: r187 types omit `canvas` from the params interface even though
          // the backend reads it — cast is intentional, not a version mismatch.
          const canvas = props.canvas as HTMLCanvasElement;
          const renderer = new WebGPURenderer({
            canvas,
            antialias: true,
            alpha: false,
            powerPreference: 'high-performance',
          } as ConstructorParameters<typeof WebGPURenderer>[0]);
          await renderer.init();
          await managerRef.current!.initialize(renderer);
          return renderer;
        }}
        camera={{ position: [0, 1.3, 4.2], fov: 45 }}
        dpr={[1, 2]}
        onCreated={(state) => {
          // The async gl factory resolves after R3F's initial size pass, so the
          // store's size subscription (≈1280×577 vs old 0×0) runs while gl is
          // still undefined and never retries. Apply the size explicitly here;
          // later resizes flow through the subscription normally.
          state.gl.setPixelRatio(state.viewport.dpr);
          state.gl.setSize(state.size.width, state.size.height, true);
          // Frame the ~1.9-unit blockout (feet y=0, head y≈1.9): aim at its center.
          state.camera.lookAt(0, 0.95, 0);
          // Checkpoint B1: reaching here means the backend initialized cleanly.
          const backend = (state.gl as unknown as { backend?: { isWebGPUBackend?: boolean } }).backend;
          const backendName = backend?.isWebGPUBackend ? 'webgpu' : 'webgl2';
          console.info(`[viewer] renderer backend: ${backendName}`);
          onBackendReady?.(backendName);
        }}
      >
        <SceneLighting />
        <CharacterModel key={activeConfig.id} config={activeConfig} />
        <RenderDriver targetIntensity={glitchIntensity} />
      </Canvas>
    </div>
  );
}
