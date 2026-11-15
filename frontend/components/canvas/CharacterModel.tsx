'use client';

import { useEffect, useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { AssetManager } from '@/lib/AssetManager';
import { applyCharacterPose, bindCharacterPose, type CharacterPose } from '@/lib/posing';
import type { CharacterConfig, CharacterId } from '@/types';

interface CharacterModelProps {
  config: CharacterConfig;
}

/**
 * Dual-mode character with runtime staging (Nodes B4 + fidelity pass):
 * - Skeletal mode: `gltf.animations` has clips → fresh AnimationMixer per mount plays
 *   `config.idleAnimationName` (fallback: first clip), then the axis-free pose layer
 *   (`lib/posing.ts`) biases arms/head into the character's stance every frame.
 *   The mixer always runs first, so baked motion is preserved, never replaced.
 * - Blockout mode: no clips → procedural idle bob stands in for the idle clip.
 *
 * Staging details:
 * - Materials: base-color maps forced to sRGB, chalky roughness (> 0.88) clamped
 *   to 0.72, envMapIntensity 0.9 so the studio IBL gives specular shaping.
 * - Grounding: after the first mixer update the bind-pose bounding box is measured
 *   and the group is shifted so the lowest sole vertex sits at y = 0.000.
 *   Only above-the-hips bones are ever posed, so feet stay planted by construction.
 * - `gltf.scene` is shared from the AssetManager cache: cleanup stops actions,
 *   unbinds the mixer root, restores posed bone quats, and releases the ref.
 */
export default function CharacterModel({ config }: CharacterModelProps) {
  const [scene, setScene] = useState<THREE.Group | null>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const clipActiveRef = useRef(false);
  const poseRef = useRef<CharacterPose | null>(null);
  const groundOffsetRef = useRef(0);
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
          mixer.update(0);
          mixerRef.current = mixer;
          clipActiveRef.current = true;
          // Axis-free stance layer bound against the frame-0 pose.
          poseRef.current = bindCharacterPose(config.id as CharacterId, gltf.scene);
          // QA hook: headless tests assert the stance bound real bones.
          // TEMP-DIAG: dump bone names when arms fail to bind (remove after root-cause).
          const __names: string[] = [];
          gltf.scene.traverse((o: THREE.Object3D) => {
            if ((o as THREE.Bone).isBone) __names.push(o.name);
          });
          (window as unknown as { __poseInfo?: object }).__poseInfo = {
            id: config.id,
            clip: clip.name,
            aims: poseRef.current.aims.length,
            yaws: poseRef.current.yaws.length,
            bones: __names,
          };
        } else {
          clipActiveRef.current = false;
          poseRef.current = null;
        }
        // Material staging for the studio look.
        gltf.scene.traverse((o: THREE.Object3D) => {
          if (!(o as THREE.Mesh).isMesh) return;
          o.castShadow = true;
          // Quantized skinned meshes carry rest-pose bounds — skip frustum
          // culling to avoid pose-dependent pop-outs.
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
            if (typeof m.roughness === 'number' && m.roughness > 0.88) {
              m.roughness = 0.72;
            }
            if ('envMapIntensity' in m) {
              (m as unknown as { envMapIntensity: number }).envMapIntensity = 0.9;
            }
          }
        });
        // Foot grounding: snap the lowest sole vertex to y = 0.000.
        gltf.scene.updateMatrixWorld(true);
        const box = new THREE.Box3().setFromObject(gltf.scene);
        groundOffsetRef.current = Number.isFinite(box.min.y) ? -box.min.y : 0;
        setScene(gltf.scene);
      })
      .catch((err) => {
        console.error(`Failed to load model [${config.id}]:`, err);
      });

    return () => {
      cancelled = true;
      poseRef.current?.restore();
      poseRef.current = null;
      if (mixerRef.current) {
        mixerRef.current.stopAllAction();
        mixerRef.current.uncacheRoot(mixerRef.current.getRoot());
        mixerRef.current = null;
      }
      clipActiveRef.current = false;
      groundOffsetRef.current = 0;
      setScene(null);
      manager.releaseModel(config.id);
    };
  }, [config.id, config.url, config.idleAnimationName]);

  useFrame((state, delta) => {
    mixerRef.current?.update(delta);
    const pose = poseRef.current;
    if (pose) applyCharacterPose(pose, state.clock.elapsedTime);
    // Procedural bob is the blockout fallback only; skeletal clips own the bones.
    if (!clipActiveRef.current && groupRef.current) {
      groupRef.current.position.y =
        config.position[1] + Math.sin(state.clock.elapsedTime * 1.6) * 0.03;
    } else if (groupRef.current) {
      groupRef.current.position.y = config.position[1] + groundOffsetRef.current;
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
