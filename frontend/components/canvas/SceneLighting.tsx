'use client';

import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';

/**
 * Bright studio 3-point rig + ground shadow catcher, positioned in the
 * character's local space (the parent group follows the character).
 *
 * - Soft key (front-right, high) casts the floor shadow with deep tonal contrast.
 * - Warm fill (front-left, low) lifts dark fabrics without flattening the key side.
 * - Subtle rim (back) in the character's tint for edge separation.
 * - Hemisphere base (dim, cool-dark ground) so whites keep shading instead of clipping.
 * - Floor: directional shadow catcher + compact #050507 contact AO under the soles.
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
    // Compact AO falloff: dense core under the soles, fast fade at the rim.
    g.addColorStop(0, 'rgba(0,0,0,1)');
    g.addColorStop(0.35, 'rgba(0,0,0,0.8)');
    g.addColorStop(0.7, 'rgba(0,0,0,0.25)');
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
      <hemisphereLight args={['#ffffff', '#3a3836', 0.7]} />
      <object3D ref={targetRef} position={[0, 0.9, 0]} />
      <directionalLight
        ref={keyRef}
        position={[2.8, 4.5, 3.2]}
        intensity={2.0}
        color="#fff6ea"
        castShadow
      />
      <directionalLight position={[-3.2, 2.0, 2.8]} intensity={0.55} color="#ffe9d6" />
      <directionalLight position={[1.5, 3.0, -4.5]} intensity={1.1} color={rimColor} />

      {/* Directional shadow catcher */}
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.001, 0]} receiveShadow>
        <planeGeometry args={[6, 6]} />
        <shadowMaterial transparent opacity={0.32} color="#050507" />
      </mesh>
      {/* Contact blob */}
      {contactTexture && (
        <mesh rotation-x={-Math.PI / 2} position={[0, 0.002, 0.02]} renderOrder={-1}>
          <planeGeometry args={[0.95, 0.42]} />
          <meshBasicMaterial
            map={contactTexture}
            transparent
            opacity={0.78}
            depthWrite={false}
            color="#050507"
          />
        </mesh>
      )}
    </>
  );
}
