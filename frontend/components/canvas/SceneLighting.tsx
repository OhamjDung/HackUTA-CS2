'use client';

import { useEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { stageInput } from '@/lib/stageInput';

/**
 * Hero light rig (character-local; the parent group follows the character).
 *
 * Built like a fighting-game select screen: a soft warm key, two hard
 * coloured rims from behind that carve the silhouette out of the dark, a top
 * kicker on hair and shoulders, and only a whisper of fill so the shadow side
 * keeps depth. With neutral tone mapping and a high bloom threshold, the rims are
 * the only thing that glows.
 *
 * Grounding: shadow catcher + tight contact shadow under the soles + a faint
 * pool of the character's colour on the floor, plus a low bounce light in the
 * same colour so the pool visibly reaches boots and shins. Rims flash briefly
 * on a swap.
 *
 * Interaction: the key light eases toward the cursor (highlights slide across
 * the model as the pointer moves) and the rims lift slightly while the cursor
 * is near the character. Both are off under prefers-reduced-motion.
 */

function radialTexture(stops: [number, string][], size = 256) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const ctx = c.getContext('2d')!;
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  for (const [o, col] of stops) g.addColorStop(o, col);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

export default function SceneLighting({ rimColor, accentColor }: { rimColor: string; accentColor: string }) {
  const keyRef = useRef<THREE.DirectionalLight>(null);
  const targetRef = useRef<THREE.Object3D>(null);
  const rimARef = useRef<THREE.DirectionalLight>(null);
  const rimBRef = useRef<THREE.DirectionalLight>(null);
  const fillRef = useRef<THREE.DirectionalLight>(null);
  const poolMatRef = useRef<THREE.MeshBasicMaterial>(null);
  const bounceRef = useRef<THREE.PointLight>(null);
  const keyPos = useRef({ x: 0, y: 0 });
  const nearRef = useRef(0);
  const calmRef = useRef(false);

  useEffect(() => {
    calmRef.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  useEffect(() => {
    const key = keyRef.current;
    const target = targetRef.current;
    if (!key || !target) return;
    for (const l of [key, rimARef.current, rimBRef.current, fillRef.current]) if (l) l.target = target;
    const cam = key.shadow.camera as THREE.OrthographicCamera;
    cam.left = -1.3;
    cam.right = 1.3;
    cam.top = 2.2;
    cam.bottom = -0.6;
    cam.near = 0.5;
    cam.far = 12;
    cam.updateProjectionMatrix();
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.bias = -0.0003;
    key.shadow.normalBias = 0.02;
    key.shadow.radius = 5;
  }, []);

  const tex = useMemo(() => {
    if (typeof document === 'undefined') return null;
    return {
      contact: radialTexture(
        [
          [0, 'rgba(0,0,0,1)'],
          [0.4, 'rgba(0,0,0,0.75)'],
          [0.75, 'rgba(0,0,0,0.2)'],
          [1, 'rgba(0,0,0,0)'],
        ],
        128,
      ),
      pool: radialTexture([
        [0, 'rgba(255,255,255,0.7)'],
        [0.35, 'rgba(255,255,255,0.28)'],
        [0.7, 'rgba(255,255,255,0.06)'],
        [1, 'rgba(255,255,255,0)'],
      ]),
    };
  }, []);

  useEffect(
    () => () => {
      tex?.contact.dispose();
      tex?.pool.dispose();
    },
    [tex],
  );

  const rimTarget = useMemo(() => new THREE.Color(rimColor), [rimColor]);
  const accentTarget = useMemo(() => new THREE.Color(accentColor), [accentColor]);

  useFrame((state, delta) => {
    const k = 1 - Math.exp(-Math.min(delta, 0.1) * 3.5);
    const since = (performance.now() - stageInput.glitchStartedAt) / 1000;
    // Swap flash: rises to the glitch midpoint, then decays over ~1 s.
    const flash = since > 0 && since < 2 ? Math.min(1, since / 0.3) * Math.exp(-Math.max(0, since - 0.3) * 3.5) : 0;
    const breathe = 0.5 + 0.5 * Math.sin(state.clock.elapsedTime * 0.9);
    const calm = calmRef.current;

    // Key light follows the cursor (eased), so highlights slide over the model.
    const kk = 1 - Math.exp(-Math.min(delta, 0.1) * 1.8);
    const cx = !calm && stageInput.pointerSeen ? stageInput.pointerX - (stageInput.anchorX * 2 - 1) : 0;
    const cy = !calm && stageInput.pointerSeen ? stageInput.pointerY : 0;
    keyPos.current.x += (THREE.MathUtils.clamp(cx, -1, 1) - keyPos.current.x) * kk;
    keyPos.current.y += (THREE.MathUtils.clamp(cy, -1, 1) - keyPos.current.y) * kk;
    if (keyRef.current) keyRef.current.position.set(2.2 + keyPos.current.x * 1.6, 3.4 + keyPos.current.y * 0.8, 2.6);

    // Rims lift while the cursor is near the character.
    const near = !calm && stageInput.pointerSeen ? Math.max(0, 1 - Math.hypot(cx * 1.4, cy - 0.1)) : 0;
    nearRef.current += (near - nearRef.current) * kk;
    const lift = 1 + nearRef.current * 0.22;

    if (rimARef.current) {
      rimARef.current.color.lerp(rimTarget, k);
      rimARef.current.intensity = (22 + flash * 18) * lift;
    }
    if (rimBRef.current) {
      rimBRef.current.color.lerp(accentTarget, k);
      rimBRef.current.intensity = (15 + flash * 12) * lift;
    }
    if (bounceRef.current) {
      bounceRef.current.color.lerp(rimTarget, k);
      bounceRef.current.intensity = 0.9 + breathe * 0.15 + flash * 1.2;
    }
    if (fillRef.current) fillRef.current.color.lerp(accentTarget, k);
    if (poolMatRef.current) {
      poolMatRef.current.color.lerp(rimTarget, k);
      poolMatRef.current.opacity = 0.35 + breathe * 0.08 + flash * 0.35;
    }
  });

  return (
    <>
      <hemisphereLight args={['#cfd8ff', '#140f18', 0.3]} />
      <object3D ref={targetRef} position={[0, 1.0, 0]} />
      {/* Key: soft warm white, high front-right; the only shadow caster. */}
      <directionalLight ref={keyRef} position={[2.2, 3.4, 2.6]} intensity={2.1} color="#fff1df" castShadow />
      {/* Whisper of fill in the accent colour, low front-left. */}
      <directionalLight ref={fillRef} position={[-2.8, 0.9, 2.4]} intensity={0.45} color={accentColor} />
      {/* Hard coloured rims from behind. */}
      <directionalLight ref={rimARef} position={[-3.2, 2.2, -1.6]} intensity={22} color={rimColor} />
      <directionalLight ref={rimBRef} position={[3.2, 1.8, -1.4]} intensity={15} color={accentColor} />
      {/* Floor bounce in the character colour: ties boots and shins to the pool. */}
      <pointLight ref={bounceRef} position={[0, 0.12, 0.55]} intensity={0.9} distance={1.6} decay={2} color={rimColor} />
      {/* Top kicker: crowns hair, helmet and shoulders. */}
      <spotLight position={[0, 4.2, -0.7]} angle={0.42} penumbra={0.85} intensity={26} distance={8} decay={1.4} color="#ffffff" />

      <mesh rotation-x={-Math.PI / 2} position={[0, 0.001, 0]} receiveShadow>
        <planeGeometry args={[6, 6]} />
        <shadowMaterial transparent opacity={0.5} color="#020203" />
      </mesh>
      {tex && (
        <>
          <mesh rotation-x={-Math.PI / 2} position={[0, 0.0015, 0]} renderOrder={-2}>
            <planeGeometry args={[2.4, 1.6]} />
            <meshBasicMaterial
              ref={poolMatRef}
              map={tex.pool}
              transparent
              opacity={0.35}
              depthWrite={false}
              color={rimColor}
              blending={THREE.AdditiveBlending}
              toneMapped={false}
            />
          </mesh>
          <mesh rotation-x={-Math.PI / 2} position={[0, 0.003, 0.02]} renderOrder={-1}>
            <planeGeometry args={[0.9, 0.45]} />
            <meshBasicMaterial map={tex.contact} transparent opacity={0.85} depthWrite={false} color="#020203" />
          </mesh>
        </>
      )}
    </>
  );
}
