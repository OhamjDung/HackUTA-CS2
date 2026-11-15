'use client';

import { useEffect, useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { AssetManager } from '@/lib/AssetManager';
import { applyPresence, bindPresence, restorePresence, type Presence } from '@/lib/presence';
import { HERO_HEIGHT, HERO_WIDTH, HERO_YAW } from '@/lib/constants';
import { stageInput } from '@/lib/stageInput';
import type { CharacterConfig, CharacterId } from '@/types';

interface CharacterModelProps {
  config: CharacterConfig;
}

/**
 * Hero-staged character.
 *
 * - The artist's Idle clip plays untouched (fresh AnimationMixer per mount) and
 *   owns the arms and legs: the clip's pose is clean on every rig, so nothing
 *   re-aims limbs (the old stance layer pushed Mario's hand through his chest).
 * - `lib/presence.ts` adds small, anatomically safe life on top: breath, a
 *   weight shift through the spine, and a restrained head follow.
 * - Every character is normalized to the same on-stage height (HERO_HEIGHT),
 *   grounded so the lowest sole sits at y = 0, and turned to a three-quarter
 *   hero angle (HERO_YAW) with only a slight lean toward the cursor.
 * - Entrance: a short rise-and-settle so a swap lands with weight.
 * - `gltf.scene` is shared from the AssetManager cache: its transform is reset
 *   before measuring, and cleanup restores bones and unbinds the mixer.
 */
export default function CharacterModel({ config }: CharacterModelProps) {
  const [scene, setScene] = useState<THREE.Group | null>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const presenceRef = useRef<Presence | null>(null);
  const groundOffsetRef = useRef(0);
  const fitScaleRef = useRef(1);
  const sceneRef = useRef<THREE.Group | null>(null);
  const rootRef = useRef<THREE.Group>(null);
  const bornAtRef = useRef<number | null>(null);
  const leanRef = useRef(0);
  const calmRef = useRef(false);
  const rootQ = useRef(new THREE.Quaternion());

  useEffect(() => {
    calmRef.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  useEffect(() => {
    let cancelled = false;
    const manager = AssetManager.getInstance();

    manager
      .loadInitialModel(config.id, config.url)
      .then((gltf) => {
        if (cancelled) return;
        const root = gltf.scene as THREE.Group;
        // Cached scenes keep transforms from a previous mount: reset before measuring.
        root.position.set(0, 0, 0);
        root.rotation.set(0, 0, 0);
        root.scale.set(1, 1, 1);

        const clips: THREE.AnimationClip[] = gltf.animations ?? [];
        const clip = clips.find((c) => c.name === config.idleAnimationName) ?? clips[0];
        if (clip) {
          const mixer = new THREE.AnimationMixer(root);
          mixer.clipAction(clip).play();
          mixer.update(0);
          mixerRef.current = mixer;
        }
        presenceRef.current = bindPresence(config.id as CharacterId, root);

        root.traverse((o: THREE.Object3D) => {
          if (!(o as THREE.Mesh).isMesh) return;
          o.castShadow = true;
          o.receiveShadow = true;
          // Quantized skinned meshes carry rest-pose bounds: skip culling to avoid pop-outs.
          o.frustumCulled = false;
          const mesh = o as THREE.Mesh;
          const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          for (const mat of mats) {
            if (!mat) continue;
            const m = mat as THREE.MeshStandardMaterial;
            if (m.map && m.map.colorSpace !== THREE.SRGBColorSpace) {
              m.map.colorSpace = THREE.SRGBColorSpace;
              m.needsUpdate = true;
            }
            // Chalky surfaces kill the rim light; give them a little sheen.
            if (typeof m.roughness === 'number' && m.roughness > 0.8) m.roughness = 0.68;
            if ('envMapIntensity' in m) {
              (m as unknown as { envMapIntensity: number }).envMapIntensity = 1.0;
            }
          }
        });

        // Ground and normalize height from the frame-0 pose.
        root.updateMatrixWorld(true);
        const box = new THREE.Box3().setFromObject(root);
        const h = box.max.y - box.min.y;
        groundOffsetRef.current = Number.isFinite(box.min.y) ? -box.min.y : 0;
        const w = box.max.x - box.min.x;
        // Fit by height, but never wider than HERO_WIDTH (chibi/broad rigs like Mario).
        fitScaleRef.current =
          Number.isFinite(h) && h > 0.2 ? Math.min(HERO_HEIGHT / h, w > 0 ? HERO_WIDTH / w : Infinity) : 1;
        sceneRef.current = root;
        setScene(root);
      })
      .catch((err) => {
        console.error(`Failed to load model [${config.id}]:`, err);
      });

    return () => {
      cancelled = true;
      if (presenceRef.current) restorePresence(presenceRef.current);
      presenceRef.current = null;
      if (mixerRef.current) {
        mixerRef.current.stopAllAction();
        mixerRef.current.uncacheRoot(mixerRef.current.getRoot());
        mixerRef.current = null;
      }
      groundOffsetRef.current = 0;
      fitScaleRef.current = 1;
      bornAtRef.current = null;
      sceneRef.current = null;
      setScene(null);
      manager.releaseModel(config.id);
    };
  }, [config.id, config.url, config.idleAnimationName]);

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime;
    const dt = Math.min(delta, 0.1);
    const root = rootRef.current;
    const model = sceneRef.current;
    const calm = calmRef.current;
    if (!root || !model) return;

    if (bornAtRef.current === null) bornAtRef.current = t;
    const age = t - bornAtRef.current;
    // Rise-and-settle: lifts 4 cm, overshoots slightly, lands. Reads as weight, not a spin.
    const p = Math.min(1, age / 0.7);
    const ease = 1 - Math.pow(1 - p, 3);
    const land = calm ? 0 : (1 - ease) * -0.06 + Math.sin(Math.min(1, age / 0.9) * Math.PI) * 0.008;

    // Hero three-quarter angle plus a gentle lean toward the cursor.
    const cursor = stageInput.pointerSeen ? stageInput.pointerX - (stageInput.anchorX * 2 - 1) : 0;
    const leanTarget = calm ? 0 : THREE.MathUtils.clamp(cursor, -1, 1) * 0.12;
    leanRef.current += (leanTarget - leanRef.current) * (1 - Math.exp(-dt * 1.6));
    root.rotation.y = HERO_YAW + leanRef.current;

    const s = fitScaleRef.current * (config.stageScale ?? 1);
    root.scale.setScalar(s);
    root.position.y = land * s;
    model.position.y = config.position[1] + groundOffsetRef.current;

    root.updateMatrixWorld();
    root.getWorldQuaternion(rootQ.current);

    mixerRef.current?.update(delta);

    const presence = presenceRef.current;
    if (presence) {
      applyPresence(presence, {
        t,
        dt,
        lookX: stageInput.pointerSeen ? cursor : 0,
        lookY: stageInput.pointerSeen ? stageInput.pointerY - 0.3 : 0,
        rootQ: rootQ.current,
        calm,
      });
    }
  });

  if (!scene) return null;

  return (
    <group ref={rootRef}>
      <primitive object={scene} scale={config.scale} />
    </group>
  );
}
