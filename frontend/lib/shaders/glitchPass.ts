import { Color, SRGBColorSpace, Vector2 } from 'three';
import {
  Fn,
  clamp,
  dot,
  float,
  hash,
  length,
  mix,
  screenSize,
  screenUV,
  smoothstep,
  time,
  uniform,
  vec2,
  vec3,
  vec4,
} from 'three/tsl';
import { bloom } from 'three/addons/tsl/display/BloomNode.js';
import type Node from 'three/src/nodes/core/Node.js';
import type PassNode from 'three/src/nodes/display/PassNode.js';
import type UniformNode from 'three/src/nodes/core/UniformNode.js';

/**
 * Studio output pass (TSL, three r187).
 *
 * The scene renders into `scenePass` over a transparent clear, so the pass
 * alpha is a character mask (meshes = 1, contact shadow = soft). This node:
 *
 *  1. Character-only glitch: band tearing + RGB split are applied to the
 *     sampled character layer only. The canvas is transparent (premultiplied
 *     colour + coverage), so the page backdrop shows through and never tears.
 *  2. Thermal scope: inside a circular lens at `scopePos` the composite is
 *     replaced by a heat-map LUT (character = warm, background = cold).
 *
 * Every input is a uniform, so the render loop drives it with zero re-renders.
 */

export type GlitchIntensity = UniformNode<'float', number>;

export interface StageOutput {
  node: Node;
  /** 0 (clean) → 1 (full tear). */
  intensity: GlitchIntensity;
  /** Lens centre in stage UV (0,0 = top-left). */
  scopePos: UniformNode<'vec2', Vector2>;
  /** Lens radius in physical (device) pixels; 0 = closed. */
  scopeRadius: UniformNode<'float', number>;
}

const linRGB = (r: number, g: number, b: number) => {
  const c = new Color().setRGB(r, g, b, SRGBColorSpace);
  return vec3(c.r, c.g, c.b);
};

// Thermal LUT stops (sRGB authored, converted to linear once).
const T0 = linRGB(0.1, 0.04, 0.32);
const T1 = linRGB(0.42, 0.1, 0.78);
const T2 = linRGB(0.86, 0.18, 0.85);
const T3 = linRGB(1.0, 0.35, 0.42);
const T4 = linRGB(1.0, 0.7, 0.12);
const T5 = linRGB(1.0, 0.98, 0.7);

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const thermalLUT = (h: any) => {
  const c = mix(T0, T1, clamp(h.div(0.25), 0, 1)).toVar();
  c.assign(mix(c, T2, clamp(h.sub(0.25).div(0.23), 0, 1)));
  c.assign(mix(c, T3, clamp(h.sub(0.48).div(0.2), 0, 1)));
  c.assign(mix(c, T4, clamp(h.sub(0.68).div(0.16), 0, 1)));
  c.assign(mix(c, T5, clamp(h.sub(0.84).div(0.16), 0, 1)));
  return c;
};

export const createStageOutput = (scenePass: PassNode): StageOutput => {
  const intensity = uniform(0) as GlitchIntensity;
  const scopePos = uniform(new Vector2(0.62, 0.3));
  const scopeRadius = uniform(0);

  const bloomNode = bloom(scenePass.getTextureNode(), 0.4, 0.4, 0.92);

  const node = Fn(() => {
    const uv = screenUV.toVar();
    const tex = scenePass.getTextureNode();

    // --- 1. character-only glitch ------------------------------------------
    const frameStep = time.mul(24.0).floor();
    const bandNoise = hash(uv.y.mul(70.0).floor().add(frameStep));
    const hit = float(bandNoise.lessThan(intensity.mul(0.5)));
    const tear = bandNoise.sub(0.25).mul(0.11).mul(intensity).mul(hit);
    const duv = vec2(uv.x.add(tear), uv.y).toVar();

    const split = vec2(intensity.mul(0.0065), float(0));
    const sR = tex.sample(duv.add(split));
    const sG = tex.sample(duv);
    const sB = tex.sample(duv.sub(split));

    // Pass colour is effectively premultiplied (blended over a 0-alpha clear).
    // The canvas is transparent: output premultiplied colour + coverage so the
    // page's CSS backdrop (flat black, charcoal radial glow, ...) shows through.
    // Bloom on the brightest edges only (rims, visor, highlights): high threshold.
    const glow = bloomNode.rgb;
    const comp = vec3(sR.r, sG.g, sB.b).add(glow).toVar();
    const coverage = sR.a.max(sG.a).max(sB.a).max(clamp(dot(glow, vec3(0.2126, 0.7152, 0.0722)), 0, 1));

    // Scanlines only where the character is.
    const scan = float(1).sub(
      uv.y.mul(screenSize.y).mul(0.5).sin().abs().mul(0.22).mul(intensity).mul(sG.a),
    );
    comp.mulAssign(scan);

    // --- 2. thermal scope lens ------------------------------------------------
    const d = length(uv.sub(scopePos).mul(screenSize));
    const lens = float(1)
      .sub(smoothstep(scopeRadius.sub(1.5), scopeRadius.add(0.5), d))
      .mul(float(scopeRadius.greaterThan(1.0)));

    const lum = dot(sG.rgb, vec3(0.2126, 0.7152, 0.0722));
    const warm = clamp(
      lum.pow(0.5).mul(0.62).add(0.5).add(float(1).sub(uv.y).mul(0.12)),
      0,
      1,
    );
    const cold = float(0.16).add(d.div(scopeRadius.max(1)).mul(0.06));
    const grain = hash(uv.mul(screenSize).floor().add(frameStep)).sub(0.5).mul(0.035);
    const heat = clamp(mix(cold, warm, smoothstep(0.05, 0.6, sG.a)).add(grain), 0, 1);
    const thermal = thermalLUT(heat).toVar();
    // Faint scan rows inside the lens.
    thermal.mulAssign(float(1).sub(uv.y.mul(screenSize.y).mul(0.35).sin().abs().mul(0.06)));

    return vec4(mix(comp, thermal, lens), mix(coverage, float(1), lens));
  })();

  return { node, intensity, scopePos, scopeRadius };
};
