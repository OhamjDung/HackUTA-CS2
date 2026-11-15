## &#x20;Folder-Level Design (Project Directory Structure)

We enforce a modular, feature-isolated architecture within our Next.js 16 App Router setup to ensure zero bundle-bloat and clean separation of concerns.

Plaintext

```
├── app/
│   ├── layout.tsx                # Root layout with critical preloads (Basis WASM, Model 1)
│   ├── page.tsx                  # Main entry point (Client wrapper)
│   └── globals.css               # Tailwind CSS & reset styles (OLED pure black #000000)
├── components/
│   ├── canvas/
│   │   ├── CharacterCanvas.tsx   # R3F Canvas container configured for WebGPURenderer
│   │   ├── CharacterModel.tsx    # Individual character node loader & animation mixer wrapper
│   │   └── SceneLighting.tsx     # Directional, rim, and key lights optimized for baked textures
│   └── ui/
│       ├── GlitchOverlay.tsx     # HTML/CSS HUD framing the 3D viewport
│       └── NavigationDeck.tsx    # Character selection buttons triggering the swap sequence
├── lib/
│   ├── AssetManager.ts           # Singleton cache, KTX2/Meshopt loader, and VRAM reference counter
│   ├── shaders/
│   │   └── glitchPass.ts         # Three.js TSL (Three Shading Language) post-processing node
│   └── constants.ts              # Asset URLs, character metadata, and animation configuration
├── public/
│   ├── decoders/
│   │   ├── basis_transcoder.js   # KTX2 basis transcoder script
│   │   └── basis_transcoder.wasm # KTX2 basis transcoder binary
│   └── models/
│       ├── 01_cs2_blockout.glb   # Initial proxy model (replaced by AAA on integration)
│       ├── 02_smash_blockout.glb
│       ├── 03_fortnite_blockout.glb
│       ├── 04_fifa_blockout.glb
│       └── 05_halo_blockout.glb
└── types/
    └── index.ts                  # Shared TypeScript interfaces (CharacterState, AssetManifest)

```

## 2. High-Level Design (HLD)

The system architecture guarantees sub-second Time-to-First-Frame (TTFF) and seamless 60+ FPS hot-swapping through a four-stage pipeline:

Plaintext

```
[1. DNS / Preload Phase] 
  └── RootLayout pushes <link rel="preload"> for basis transcoder & Model 1 binary.

[2. Initialization Phase]
  └── CharacterCanvas mounts -> WebGPURenderer initializes backend -> AssetManager boots loaders.

[3. Immediate Render & Background Sourcing]
  └── Model 1 (CS2) renders instantly (<800ms TTFF). 
  └── AssetManager concurrently kicks off background chunk loading (Concurrency = 2) for Models 2-5.

[4. The Hot-Swap & Glitch Loop]
  └── User clicks character switch -> TSL Glitch Shader pass activates (RGB split + scanlines) 
  └── Active scene graph swaps model reference -> Old model textures/geometry flagged for asynchronous VRAM disposal.

```

## 3. Low-Level Design (LLD)

### A. Data Models & TypeScript Interfaces (`types/index.ts`)

TypeScript

```
export type CharacterId = 'cs2' | 'smash' | 'fortnite' | 'fifa' | 'halo';

export interface CharacterConfig {
  id: CharacterId;
  name: string;
  url: string;
  scale: [number, number, number];
  position: [number, number, number];
  idleAnimationName: string;
  accentColor: string; // HUD accent (active pill, signal bar, locked dot) + cool fill light
  rimColor: string;    // Key rim light color for the OLED stage
}

export interface AssetCacheEntry {
  gltf: any; // GLTF result from GLTFLoader
  refCount: number;
  lastAccessed: number;
}

```

### B. OOP Singleton: Asset Manager (`lib/AssetManager.ts`)

This class manages asset lifecycle, decoder attachment, and memory residency to prevent VRAM leaks during rapid switching.

TypeScript

```
import { WebGPURenderer } from 'three/webgpu';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { AssetCacheEntry, CharacterId } from '@/types';

export class AssetManager {
  private static instance: AssetManager;
  private gltfLoader: GLTFLoader | null = null;
  private modelCache: Map<CharacterId, AssetCacheEntry> = new Map();
  private activePrefetchIndex = 0;
  private isPrefetching = false;

  private constructor() {}

  public static getInstance(): AssetManager {
    if (!AssetManager.instance) {
      AssetManager.instance = new AssetManager();
    }
    return AssetManager.instance;
  }

  /**
   * Initializes loaders with WebGPU Renderer per r187 specifications.
   */
  public async initialize(renderer: WebGPURenderer): Promise<void> {
    if (this.gltfLoader) return;

    // MANDATORY r187 execution order: Await backend initialization before KTX2 setup
    await renderer.init();

    const ktx2Loader = new KTX2Loader()
      .setTranscoderPath('/decoders/')
      .detectSupport(renderer); // detectSupportAsync is deprecated in r181+

    this.gltfLoader = new GLTFLoader()
      .setKTX2Loader(ktx2Loader)
      .setMeshoptDecoder(MeshoptDecoder);
  }

  /**
   * Loads the initial priority model for instant TTFF.
   */
  public async loadInitialModel(id: CharacterId, url: string): Promise<any> {
    if (!this.gltfLoader) throw new Error('AssetManager not initialized');
    
    if (this.modelCache.has(id)) {
      const entry = this.modelCache.get(id)!;
      entry.refCount++;
      entry.lastAccessed = performance.now();
      return entry.gltf;
    }

    const gltf = await this.gltfLoader.loadAsync(url);
    this.modelCache.set(id, {
      gltf,
      refCount: 1,
      lastAccessed: performance.now(),
    });

    return gltf;
  }

  /**
   * Background chunk loader for remaining models at Concurrency = 2.
   */
  public async prefetchRemainingModels(configs: { id: CharacterId; url: string }[]): Promise<void> {
    if (this.isPrefetching || !this.gltfLoader) return;
    this.isPrefetching = true;

    for (let i = 0; i < configs.length; i += 2) {
      const chunk = configs.slice(i, i + 2);
      await Promise.all(
        chunk.map(async ({ id, url }) => {
          if (!this.modelCache.has(id)) {
            try {
              const gltf = await this.gltfLoader!.loadAsync(url);
              this.modelCache.set(id, {
                gltf,
                refCount: 0, // In background cache
                lastAccessed: performance.now(),
              });
            } catch (err) {
              console.error(`Failed to prefetch model [${id}]:`, err);
            }
          }
        })
      );
    }
    this.isPrefetching = false;
  }

  /**
   * Decrements the reference count. Node B4 carousel policy: decoded scenes
   * stay resident (5-model loop, <10MB budget) — no dispose here. Eviction is
   * explicit via evictModel/evictAll, or LRU past MAX_RESIDENT_MODELS (8).
   */
  public releaseModel(id: CharacterId): void {
    const entry = this.modelCache.get(id);
    if (!entry) return;

    entry.refCount = Math.max(0, entry.refCount - 1);
    this.evictLRUIfNeeded();
  }

  /** Frees one unmounted model. Refuses while refCount > 0. */
  public evictModel(id: CharacterId): void { /* dispose + delete if refCount === 0 */ }

  /** Full VRAM teardown on showcase unmount. */
  public evictAll(): void { /* dispose every resident scene, clear cache */ }

  private disposeGlft(gltf: any): void {
    gltf.scene.traverse((child: any) => {
      if (child.isMesh) {
        child.geometry.dispose();
        if (Array.isArray(child.material)) {
          child.material.forEach((mat: any) => mat.dispose());
        } else if (child.material) {
          child.material.dispose();
        }
      }
    });
  }
}

```

### C. TSL Glitch Shader Pass (`lib/shaders/glitchPass.ts`)

Three.js Shading Language (TSL) node implementation for the transition effect. Runs entirely on the GPU.

TypeScript

```
import { tslFn, screenUV, texture, uniform, float, vec2, vec3, vec4, hash } from 'three/tsl';

/**
 * Creates a TSL node function for the procedural glitch and RGB split effect.
 * @param inputTextureNode The color texture node from the scene render pass.
 * @param glitchIntensityUniform Uniform float controlling the distortion amount (0.0 to 1.0).
 */
export const createGlitchPassNode = (inputTextureManager: any, glitchIntensityUniform: any) => {
  return tslFn(() => {
    const uv = screenUV.toVar();
    
    // Generate block noise based on vertical coordinate and time
    const timeComponent = uniform('float', 0.0);
    const blockNoise = hash(uv.y.mul(100.0).floor().add(timeComponent));
    
    // Conditionally apply glitch displacement when intensity > threshold
    const shouldGlitch = glitchIntensityUniform.greaterThan(0.05).mul(blockNoise.lessThan(glitchIntensityUniform));
    
    // Compute RGB split offsets
    const rOffset = vec2(glitchIntensityUniform.mul(0.05), 0.0);
    const bOffset = vec2(glitchIntensityUniform.mul(-0.04), 0.0);
    
    const displacedUV = uv.add(shouldGlitch.select(vec2(blockNoise.sub(0.5).mul(0.1), 0.0), vec2(0.0)));
    
    const sampledR = inputTextureManager.sample(displacedUV.add(rOffset)).r;
    const sampledG = inputTextureManager.sample(displacedUV).g;
    const sampledB = inputTextureManager.sample(displacedUV.sub(bOffset)).b;
    
    const finalColor = vec3(sampledR, sampledG, sampledB);
    
    // Add horizontal scanline artifacts
    const scanline = float(1.0).sub(uv.y.mul(400.0).sin().mul(0.15).mul(glitchIntensityUniform));
    
    return vec4(finalColor.mul(scanline), 1.0);
  })();
};

```

### D. Component Logic: Character Canvas (`components/canvas/CharacterCanvas.tsx`)

TypeScript

```
'use client';

import React, { useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { WebGPURenderer } from 'three/webgpu';
import { AssetManager } from '@/lib/AssetManager';

export default function CharacterCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    // Initialize Asset Manager singleton on mount
    const assetManager = AssetManager.getInstance();
    
    // Pre-fetch remaining models after initial render
    assetManager.prefetchRemainingModels([
      { id: 'smash', url: '/models/02_smash_blockout.glb' },
      { id: 'fortnite', url: '/models/03_fortnite_blockout.glb' },
      { id: 'fifa', url: '/models/04_fifa_blockout.glb' },
      { id: 'halo', url: '/models/05_halo_blockout.glb' },
    ]);
  }, []);

  return (
    <div className="w-full h-screen bg-black overflow-hidden">
      <Canvas
        ref={canvasRef}
        gl={async (canvas) => {
          // Force WebGPURenderer implementation with WebGL2 fallback baked into r187
          const renderer = new WebGPURenderer({
            canvas,
            antialias: true,
            alpha: false,
            powerPreference: 'high-performance',
          });
          await renderer.init();
          return renderer;
        }}
        camera={{ position: [0, 1.5, 4], fov: 45 }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={1.2} />
        <directionalLight position={[5, 8, 5]} intensity={2.5} />
        {/* Character Scene Controller rendered here */}
      </Canvas>
    </div>
  );
}

```

## 4. Execution Checkpoints for Developer

1. **Checkpoint B1:** Verify that `CharacterCanvas` boots up using `WebGPURenderer` without throwing WebGPU backend context exceptions in console.
2. **Checkpoint B2:** Confirm `AssetManager` loads `01_cs2_blockout.glb` under 800ms and successfully triggers background fetching for models 2 through 5.
3. **Checkpoint B3:** Implement `glitchPass.ts` into the post-processing pipeline and verify that changing the uniform value produces an immediate GPU-accelerated RGB shift without CPU stutter.

## 5. Node B4: Auto-Cycle Loop & Skeletal Animation Fallback

Drop-in readiness for the 3D artist's rigged AAA models with zero code changes:

1. **Dual-mode `CharacterModel`:** if `gltf.animations.length > 0`, a fresh `THREE.AnimationMixer`
   binds `gltf.scene` per mount and plays `idleAnimationName` (fallback: first clip) via
   `mixer.update(delta)`; cleanup calls `stopAllAction()` + `uncacheRoot()` so no mixer or bone
   state survives unmount. With zero clips, the procedural idle bob applies instead.
2. **Showcase loop (`page.tsx`, `NavigationDeck.tsx`):** auto-advance every
   `AUTO_SWAP_INTERVAL_MS` (4000ms, in `lib/constants.ts`) through
   `cs2 -> smash -> fortnite -> fifa -> halo -> cs2`. Every swap (auto or manual) restarts the
   timer, manual clicks can never collide with an auto-swap mid-glitch, and a Pause/Play toggle
   freezes the loop for inspection.
3. **Carousel residency (`AssetManager.ts`):** `releaseModel` never disposes; all 5 decoded
   scenes stay resident, eviction is explicit (`evictModel`/`evictAll` on unmount) or LRU past a
   high-water mark of 8 — no re-fetch/re-upload on the 20-second loop.