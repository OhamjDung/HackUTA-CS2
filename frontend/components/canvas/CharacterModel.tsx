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
 * Loads one character through the AssetManager singleton and plays its idle
 * clip. Blockout proxies ship no animation clips, so a procedural idle bob
 * stands in for `idleAnimationName` until AAA assets land.
 */
export default function CharacterModel({ config }: CharacterModelProps) {
  const [scene, setScene] = useState<THREE.Group | null>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const groupRef = useRef<THREE.Group>(null);

  useEffect(() => {
    let cancelled = false;
    const manager = AssetManager.getInstance();

    manager
      .loadInitialModel(config.id, config.url)
      .then((gltf) => {
        if (cancelled) return;
        const mixer = new THREE.AnimationMixer(gltf.scene);
        const clips: THREE.AnimationClip[] = gltf.animations ?? [];
        const clip =
          clips.find((c) => c.name === config.idleAnimationName) ?? clips[0];
        if (clip) {
          const action = mixer.clipAction(clip);
          action.play();
        }
        mixerRef.current = mixer;
        setScene(gltf.scene);
      })
      .catch((err) => {
        console.error(`Failed to load model [${config.id}]:`, err);
      });

    return () => {
      cancelled = true;
      mixerRef.current?.stopAllAction();
      mixerRef.current = null;
      setScene(null);
      manager.releaseModel(config.id);
    };
  }, [config.id, config.url, config.idleAnimationName]);

  useFrame((state, delta) => {
    mixerRef.current?.update(delta);
    if (groupRef.current) {
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
