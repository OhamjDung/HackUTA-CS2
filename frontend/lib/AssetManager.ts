import { WebGPURenderer } from 'three/webgpu';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import type { AssetCacheEntry, CharacterId } from '@/types';
import { TRANSCODER_PATH } from '@/lib/constants';

export class AssetManager {
  private static instance: AssetManager;
  private gltfLoader: GLTFLoader | null = null;
  private modelCache: Map<CharacterId, AssetCacheEntry> = new Map();
  private isPrefetching = false;
  private readyPromise: Promise<void>;
  private resolveReady!: () => void;

  private constructor() {
    this.readyPromise = new Promise<void>((resolve) => {
      this.resolveReady = resolve;
    });
  }

  public static getInstance(): AssetManager {
    if (!AssetManager.instance) {
      AssetManager.instance = new AssetManager();
    }
    return AssetManager.instance;
  }

  /**
   * Resolves once initialize() has set up the loaders. Lets background work
   * (prefetch) wait for a slow/stalled renderer backend instead of silently
   * skipping when the loader isn't ready yet.
   */
  public whenReady(): Promise<void> {
    return this.readyPromise;
  }

  /**
   * Initializes loaders with WebGPU Renderer per r187 specifications.
   */
  public async initialize(renderer: WebGPURenderer): Promise<void> {
    if (this.gltfLoader) return;

    // MANDATORY r187 execution order: Await backend initialization before KTX2 setup
    await renderer.init();

    const ktx2Loader = new KTX2Loader()
      .setTranscoderPath(TRANSCODER_PATH)
      .detectSupport(renderer); // detectSupportAsync is deprecated in r181+

    this.gltfLoader = new GLTFLoader()
      .setKTX2Loader(ktx2Loader)
      .setMeshoptDecoder(MeshoptDecoder);
    this.resolveReady();
  }

  /**
   * Loads the initial priority model for instant TTFF.
   * Cache hits bump the ref count so hot-swaps never re-fetch.
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
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

    try {
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
          }),
        );
      }
    } finally {
      this.isPrefetching = false;
    }
  }

  /**
   * Decrements reference count and triggers asynchronous VRAM disposal if unused.
   */
  public releaseModel(id: CharacterId): void {
    const entry = this.modelCache.get(id);
    if (!entry) return;

    entry.refCount = Math.max(0, entry.refCount - 1);

    // Evict if unreferenced and memory pressure requires it
    if (entry.refCount === 0) {
      this.disposeGltf(entry.gltf);
      this.modelCache.delete(id);
    }
  }

  /** Test hook: is a model resident in the background cache? */
  public hasModel(id: CharacterId): boolean {
    return this.modelCache.has(id);
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private disposeGltf(gltf: any): void {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    gltf.scene.traverse((child: any) => {
      if (child.isMesh) {
        child.geometry.dispose();
        if (Array.isArray(child.material)) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          child.material.forEach((mat: any) => mat.dispose());
        } else if (child.material) {
          child.material.dispose();
        }
        // Dispose baked textures so VRAM is actually freed
        const materials = Array.isArray(child.material) ? child.material : [child.material];
        for (const mat of materials) {
          if (!mat) continue;
          for (const key of Object.keys(mat)) {
            const value = mat[key] as unknown;
            if (value && typeof value === 'object' && 'isTexture' in value) {
              (value as unknown as { dispose: () => void }).dispose();
            }
          }
        }
      }
    });
  }
}
