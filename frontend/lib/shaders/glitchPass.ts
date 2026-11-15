import {
  Fn,
  float,
  hash,
  screenUV,
  time,
  uniform,
  vec2,
  vec3,
  vec4,
} from 'three/tsl';
import type Node from 'three/src/nodes/core/Node.js';
import type PassNode from 'three/src/nodes/display/PassNode.js';
import type UniformNode from 'three/src/nodes/core/UniformNode.js';

/**
 * TSL glitch / RGB-split post-processing node (AGENTS.md §3C).
 *
 * NOTE (r187 API deviation): the spec snippet uses `tslFn(...)` and
 * `uniform('float', 0.0)`. In three r187 the factory is `Fn` and uniforms
 * infer their type from the value (`uniform(0)`), so this module follows the
 * installed r187 API while keeping the spec's effect design: block-noise
 * tearing + RGB channel split + horizontal scanlines, all GPU-side.
 */

export type GlitchIntensity = UniformNode<'float', number>;

/** Mutable 0.0 → 1.0 distortion driver. The render loop writes `.value`. */
export const createGlitchIntensity = (initialValue = 0): GlitchIntensity => {
  return uniform(initialValue);
};

/**
 * Builds the fullscreen output node for `RenderPipeline` (three/webgpu).
 *
 * @param scenePass  `pass(scene, camera)` node rendering the 3D view.
 * @param intensity  Uniform float controlling distortion (0.0 to 1.0).
 */
export const createGlitchOutputNode = (
  scenePass: PassNode,
  intensity: GlitchIntensity,
): Node => {
  return Fn(() => {
    const uv = screenUV.toVar();

    // Block noise: one random value per horizontal band, stepped per frame.
    const frameStep = time.mul(24.0).floor();
    const bandNoise = hash(uv.y.mul(140.0).floor().add(frameStep));

    // Tear only where the effect is armed and the band "wins" the noise roll.
    // Masks stay in float arithmetic (no boolean select) for typing stability.
    const gate = float(intensity.greaterThan(0.02));
    const hit = float(bandNoise.lessThan(intensity));
    const tearOffset = bandNoise
      .sub(0.5)
      .mul(0.25)
      .mul(intensity)
      .mul(gate.mul(hit));

    const displacedUV = vec2(uv.x.add(tearOffset), uv.y).toVar();
    const sceneTexture = scenePass.getTextureNode();

    // RGB split: R/B sampled with mirrored horizontal offsets.
    const split = vec2(intensity.mul(0.03), float(0));
    const sampledR = sceneTexture.sample(displacedUV.add(split)).r;
    const sampledG = sceneTexture.sample(displacedUV).g;
    const sampledB = sceneTexture.sample(displacedUV.sub(split)).b;

    const finalColor = vec3(sampledR, sampledG, sampledB).toVar();

    // Horizontal scanline darkening, scaled by intensity.
    const scanline = float(1.0).sub(
      uv.y.mul(400.0).sin().abs().mul(0.25).mul(intensity),
    );

    return vec4(finalColor.mul(scanline), float(1.0));
  })();
};
