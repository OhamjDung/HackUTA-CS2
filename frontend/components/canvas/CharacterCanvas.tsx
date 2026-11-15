'use client';

import { useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { RenderPipeline, WebGPURenderer } from 'three/webgpu';
import { pass } from 'three/tsl';
import { AssetManager } from '@/lib/AssetManager';
import { createStageOutput } from '@/lib/shaders/glitchPass';
import {
  CHARACTER_MAP,
  CHARACTERS,
  GLITCH_DURATION_MS,
  SCOPE_RADIUS_PX,
  STAGE_CAMERA,
} from '@/lib/constants';
import { stageInput } from '@/lib/stageInput';
import type { CharacterId } from '@/types';
import CharacterModel from './CharacterModel';
import SceneLighting from './SceneLighting';

interface CharacterCanvasProps {
  activeId: CharacterId;
  /** Reports which backend actually initialized (WebGPU vs WebGL2 fallback). */
  onBackendReady?: (backend: 'webgpu' | 'webgl2') => void;
}

/** Glitch envelope over the 0.6 s transition: rises to 1 at the swap midpoint, then releases. */
function glitchEnvelope(elapsedMs: number): number {
  const p = elapsedMs / GLITCH_DURATION_MS;
  if (p <= 0 || p >= 1) return 0;
  return Math.pow(Math.sin(Math.PI * p), 0.55);
}

/**
 * Owns the TSL RenderPipeline and takes over the frame loop (priority 1), so
 * the only path to the screen is the studio output node. Uniforms are fed
 * from `stageInput` every frame: no React state is touched per frame.
 */
function RenderDriver() {
  const gl = useThree((s) => s.gl);
  const scene = useThree((s) => s.scene);
  const camera = useThree((s) => s.camera);
  const scopeOpen = useRef(0);
  const reducedMotion = useRef(false);

  useEffect(() => {
    reducedMotion.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  const rig = useMemo(() => {
    const renderer = gl as unknown as WebGPURenderer;
    const scenePass = pass(scene, camera);
    const output = createStageOutput(scenePass);
    const pipeline = new RenderPipeline(renderer, output.node);
    pipeline.needsUpdate = true;
    return { pipeline, output };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gl]);

  useEffect(() => () => rig.pipeline.dispose(), [rig]);

  useFrame((state, delta) => {
    const { output } = rig;
    const env = glitchEnvelope(performance.now() - stageInput.glitchStartedAt);
    output.intensity.value = reducedMotion.current ? env * 0.35 : env;

    // Lens opens/closes with a quick ease; radius in device pixels.
    const target = stageInput.scopeActive ? 1 : 0;
    scopeOpen.current += (target - scopeOpen.current) * Math.min(1, delta * 14);
    if (Math.abs(scopeOpen.current - target) < 0.002) scopeOpen.current = target;
    const eased = 1 - Math.pow(1 - scopeOpen.current, 3);
    output.scopeRadius.value = SCOPE_RADIUS_PX * state.viewport.dpr * eased;
    output.scopePos.value.set(stageInput.scopeX, stageInput.scopeY);

    rig.pipeline.render();
  }, 1);

  return null;
}

const CAMERA_DISTANCE = new THREE.Vector3(...STAGE_CAMERA.position).distanceTo(
  new THREE.Vector3(...STAGE_CAMERA.target),
);

/**
 * Places the character (and its light rig) at the stage's horizontal anchor:
 * `stageInput.anchorX`, measured by the page from the headline/HUD layout.
 */
function StageRig({ children }: { children: React.ReactNode }) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    const g = groupRef.current;
    if (!g) return;
    const cam = state.camera as THREE.PerspectiveCamera;
    const halfH = Math.tan(THREE.MathUtils.degToRad(cam.fov / 2)) * CAMERA_DISTANCE;
    const halfW = halfH * (state.size.width / Math.max(1, state.size.height));
    g.position.x = (stageInput.anchorX * 2 - 1) * halfW;
    g.scale.setScalar(stageInput.anchorScale);
  });

  return <group ref={groupRef}>{children}</group>;
}

export default function CharacterCanvas({ activeId, onBackendReady }: CharacterCanvasProps) {
  const managerRef = useRef<AssetManager | null>(null);
  if (!managerRef.current) managerRef.current = AssetManager.getInstance();

  // Background chunk fetch (concurrency 2) once the loaders are ready.
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

  // Full VRAM teardown when the stage unmounts (page leave / HMR).
  useEffect(() => {
    const manager = managerRef.current!;
    return () => {
      manager.evictAll();
    };
  }, []);

  const activeConfig = CHARACTER_MAP[activeId];

  return (
    <div className="absolute inset-0" aria-hidden>
      <Canvas
        flat
        // Object form: R3F assigns it onto gl.shadowMap (PCFSoft is removed in r187's WebGPURenderer).
        shadows={{ enabled: true, type: THREE.PCFShadowMap }}
        gl={async (props) => {
          // WebGPURenderer with r187's built-in WebGL2 fallback.
          const canvas = props.canvas as HTMLCanvasElement;
          const renderer = new WebGPURenderer({
            canvas,
            antialias: true,
            alpha: false,
            powerPreference: 'high-performance',
          } as ConstructorParameters<typeof WebGPURenderer>[0]);
          await renderer.init();
          // Transparent clear: the pass alpha becomes the character mask that
          // the output node composites over the studio background.
          renderer.setClearColor(0x000000, 0);
          await managerRef.current!.initialize(renderer);
          return renderer;
        }}
        camera={{ position: STAGE_CAMERA.position, fov: STAGE_CAMERA.fov, near: 0.1, far: 50 }}
        dpr={[1, 2]}
        onCreated={(state) => {
          // The async gl factory resolves after R3F's initial size pass; apply
          // the size explicitly (later resizes flow through the subscription).
          state.gl.setPixelRatio(state.viewport.dpr);
          state.gl.setSize(state.size.width, state.size.height, true);
          state.camera.lookAt(...STAGE_CAMERA.target);
          const backend = (state.gl as unknown as { backend?: { isWebGPUBackend?: boolean } }).backend;
          const backendName = backend?.isWebGPUBackend ? 'webgpu' : 'webgl2';
          console.info(`[viewer] renderer backend: ${backendName}`);
          onBackendReady?.(backendName);
        }}
      >
        <StageRig>
          <SceneLighting rimColor={activeConfig.rimColor} />
          <CharacterModel key={activeConfig.id} config={activeConfig} />
        </StageRig>
        <RenderDriver />
      </Canvas>
    </div>
  );
}
