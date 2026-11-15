'use client';

import { useEffect, useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { AssetManager } from '@/lib/AssetManager';
import type { CharacterConfig } from '@/types';

interface CharacterModelProps {
  config: CharacterConfig;
}

/**
 * Dual-mode character (Node B4):
 * - Skeletal mode: `gltf.animations` has clips → bind an AnimationMixer and play
 *   `config.idleAnimationName` (fallback: first clip). Procedural bob is OFF.
 * - Blockout mode: no clips → procedural idle bob stands in for the idle clip.
 *
 * `gltf.scene` is shared from the AssetManager cache, so every mount binds a
 * FRESH mixer and the cleanup stops all actions plus `uncacheRoot`s the scene:
 * no mixer (and no driven bone state) ever survives an unmount, and re-mounting
 * a cached character can never stack duplicate mixers.
 */
export default function CharacterModel({ config }: CharacterModelProps) {
  const [scene, setScene] = useState<THREE.Group | null>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const clipActiveRef = useRef(false);
  const groupRef = useRef<THREE.Group>(null);

  useEffect(() => {
    let cancelled = false;
    const manager = AssetManager.getInstance();

    manager
      .loadInitialModel(config.id, config.url)
      .then((gltf) => {
        if (cancelled) return;
        const clips: THREE.AnimationClip[] = gltf.animations ?? [];
        const clip =
          clips.find((c) => c.name === config.idleAnimationName) ?? clips[0];
        if (clip) {
          // Fresh mixer per mount — the scene is cached/shared, so mixers must
          // never be reused across mounts or bone matrices go stale.
          const mixer = new THREE.AnimationMixer(gltf.scene);
          mixer.clipAction(clip).play();
          mixerRef.current = mixer;
          clipActiveRef.current = true;
        } else {
          clipActiveRef.current = false;
        }
        // Studio stage: characters cast the floor shadow. Quantized skinned
        // meshes carry rest-pose bounds, so skip frustum culling to avoid
        // pose-dependent pop-outs.
        gltf.scene.traverse((o: THREE.Object3D) => {
          if ((o as THREE.Mesh).isMesh) {
            o.castShadow = true;
            o.frustumCulled = false;
          }
        });
        setScene(gltf.scene);
      })
      .catch((err) => {
        console.error(`Failed to load model [${config.id}]:`, err);
      });

    return () => {
      cancelled = true;
      if (mixerRef.current) {
        mixerRef.current.stopAllAction();
        mixerRef.current.uncacheRoot(mixerRef.current.getRoot());
        mixerRef.current = null;
      }
      clipActiveRef.current = false;
      setScene(null);
      manager.releaseModel(config.id);
    };
  }, [config.id, config.url, config.idleAnimationName]);

  useFrame((state, delta) => {
    mixerRef.current?.update(delta);
    // Procedural bob is the blockout fallback only; skeletal clips own the bones.
    if (!clipActiveRef.current && groupRef.current) {
      groupRef.current.position.y =
        config.position[1] + Math.sin(state.clock.elapsedTime * 1.6) * 0.03;
    }
  });

  if (!scene) return null;

  return (
    <primitive
      ref={groupRef}
      object={scene}
      scale={config.scale}
      position={config.position}
    />
  );
}
