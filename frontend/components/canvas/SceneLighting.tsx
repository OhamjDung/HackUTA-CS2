'use client';

export default function SceneLighting() {
  return (
    <>
      {/* Base fill so baked textures are never pitch black */}
      <ambientLight intensity={1.2} />
      {/* Key light */}
      <directionalLight position={[5, 8, 5]} intensity={2.5} />
      {/* Rim light for silhouette separation on pure-black background */}
      <directionalLight position={[-6, 4, -6]} intensity={1.4} color="#88ccff" />
      {/* Low front fill to lift baked-texture shadows */}
      <directionalLight position={[0, 1.5, 6]} intensity={0.6} color="#fff2e0" />
    </>
  );
}
