'use client';

export default function SceneLighting({
  rimColor,
  fillColor,
}: {
  /** Key rim light — per-character signature color, shifts at the swap midpoint. */
  rimColor: string;
  /** Cool front fill — the character's accent color. */
  fillColor: string;
}) {
  return (
    <>
      {/* Base fill so baked textures are never pitch black */}
      <ambientLight intensity={1.2} />
      {/* Key light */}
      <directionalLight position={[5, 8, 5]} intensity={2.5} />
      {/* Rim light for silhouette separation on pure-black background */}
      <directionalLight position={[-7, 3, -4]} intensity={2.6} color={rimColor} />
      {/* Low front fill in the character's accent tone */}
      <directionalLight position={[0, 1.5, 6]} intensity={0.6} color={fillColor} />
    </>
  );
}
