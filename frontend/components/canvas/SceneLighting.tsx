'use client';

import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

/**
 * Bright studio 3-point rig + ground shadow catcher, positioned in the
 * character's local space (the parent group follows the character).
 *
 * - Soft key (front-left, high) casts the floor shadow.
 * - Warm fill (front-right) lifts dark fabrics off the off-white stage.
 * - Subtle rim (back) in the character's tint for edge separation.
 * - Hemisphere base so no surface goes muddy against #FAF9F6.
 */
export default function SceneLighting({ rimColor }: { rimColor: string }) {
  const keyRef = useRef<THREE.DirectionalLight>(null);
  const targetRef = useRef<THREE.Object3D>(null);

  useEffect(() => {
    const key = keyRef.current;
    if (!key || !targetRef.current) return;
    key.target = targetRef.current;
    const cam = key.shadow.camera as THREE.OrthographicCamera;
    cam.left = -1.4;
    cam.right = 1.4;
    cam.top = 1.6;
    cam.bottom = -1.2;
    cam.near = 0.5;
    cam.far = 14;
    cam.updateProjectionMatrix();
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.bias = -0.0004;
    key.shadow.normalBias = 0.02;
    key.shadow.radius = 6;
  }, []);

  // Soft elliptical contact shadow (ambient occlusion under the feet).
  const contactTexture = useMemo(() => {
    if (typeof document === 'undefined') return null;
    const c = document.createElement('canvas');
    c.width = c.height = 128;
    const ctx = c.getContext('2d')!;
    const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    g.addColorStop(0, 'rgba(0,0,0,1)');
    g.addColorStop(0.45, 'rgba(0,0,0,0.55)');
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 128, 128);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }, []);

  useEffect(() => () => contactTexture?.dispose(), [contactTexture]);

  return (
    <>
      <hemisphereLight args={['#ffffff', '#d9d6cf', 1.35]} />
      <object3D ref={targetRef} position={[0, 0.9, 0]} />
      <directionalLight
        ref={keyRef}
        position={[-2.6, 5.2, 3.6]}
        intensity={2.2}
        color="#fff6ea"
        castShadow
      />
      <directionalLight position={[3.2, 2.2, 3.0]} intensity={0.75} color="#ffe9d6" />
      <directionalLight position={[1.5, 3.0, -4.5]} intensity={1.1} color={rimColor} />

      {/* Directional shadow catcher */}
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.001, 0]} receiveShadow>
        <planeGeometry args={[6, 6]} />
        <shadowMaterial transparent opacity={0.14} />
      </mesh>
      {/* Contact blob */}
      {contactTexture && (
        <mesh rotation-x={-Math.PI / 2} position={[0, 0.002, 0.02]} renderOrder={-1}>
          <planeGeometry args={[1.25, 0.55]} />
          <meshBasicMaterial
            map={contactTexture}
            transparent
            opacity={0.2}
            depthWrite={false}
            color="#000000"
          />
        </mesh>
      )}
    </>
  );
}
