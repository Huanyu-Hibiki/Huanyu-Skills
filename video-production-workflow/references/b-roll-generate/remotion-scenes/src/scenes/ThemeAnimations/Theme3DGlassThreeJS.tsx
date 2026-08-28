/**
 * Theme3DGlassThreeJS - Three.js 3D Glass - 本格的な3Dガラス（Three.js使用）
 * MeshTransmissionMaterial使用
 */

import { useRef, useMemo, Suspense, useEffect } from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import { MeshTransmissionMaterial, Environment, Text } from "@react-three/drei";
import { font } from "../../common";

// ガラスマテリアルを持つ角丸ボックス
const GlassBox3D = ({ position, rotation, scale, progress }: {
  position: [number, number, number];
  rotation: [number, number, number];
  scale: number;
  progress: number;
}) => {
  const meshRef = useRef<THREE.Mesh>(null);

  // 角丸ボックスのジオメトリを作成
  const geometry = useMemo(() => {
    const shape = new THREE.Shape();
    const width = 3.2;
    const height = 2.4;
    const radius = 0.4;

    shape.moveTo(-width / 2 + radius, -height / 2);
    shape.lineTo(width / 2 - radius, -height / 2);
    shape.quadraticCurveTo(width / 2, -height / 2, width / 2, -height / 2 + radius);
    shape.lineTo(width / 2, height / 2 - radius);
    shape.quadraticCurveTo(width / 2, height / 2, width / 2 - radius, height / 2);
    shape.lineTo(-width / 2 + radius, height / 2);
    shape.quadraticCurveTo(-width / 2, height / 2, -width / 2, height / 2 - radius);
    shape.lineTo(-width / 2, -height / 2 + radius);
    shape.quadraticCurveTo(-width / 2, -height / 2, -width / 2 + radius, -height / 2);

    const extrudeSettings = {
      depth: 0.6,
      bevelEnabled: true,
      bevelThickness: 0.15,
      bevelSize: 0.15,
      bevelSegments: 16,
    };

    const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
    geo.center();
    return geo;
  }, []);

  return (
    <mesh
      ref={meshRef}
      position={position}
      rotation={rotation}
      scale={scale * progress}
      geometry={geometry}
    >
      <MeshTransmissionMaterial
        thickness={0.5}
        roughness={0}
        transmission={1}
        ior={1.5}
        chromaticAberration={0.03}
        backside={true}
        backsideThickness={0.3}
        anisotropy={0.3}
        distortion={0.1}
        distortionScale={0.2}
        temporalDistortion={0.1}
      />
    </mesh>
  );
};

// ガラス球
const GlassSphere3D = ({ position, scale, progress, wobbleOffset = 0, frame }: {
  position: [number, number, number];
  scale: number;
  progress: number;
  wobbleOffset?: number;
  frame: number;
}) => {
  const wobble = Math.sin((frame + wobbleOffset) * 0.05) * 0.15;

  return (
    <mesh
      position={[position[0], position[1] + wobble, position[2]]}
      scale={scale * progress}
    >
      <sphereGeometry args={[0.5, 64, 64]} />
      <MeshTransmissionMaterial
        thickness={1}
        roughness={0}
        transmission={1}
        ior={1.8}
        chromaticAberration={0.05}
        backside={true}
        backsideThickness={0.5}
        distortion={0.2}
        distortionScale={0.3}
      />
    </mesh>
  );
};

// 背景のカラフルな球とテキスト（ガラス越しに歪んで見える）
const BackgroundElements = ({ frame }: { frame: number }) => {
  const wobble1 = Math.sin(frame * 0.03) * 0.3;
  const wobble2 = Math.cos(frame * 0.025) * 0.4;

  return (
    <>
      {/* カラフルな球 */}
      <mesh position={[-2.5, 1 + wobble1, -2]}>
        <sphereGeometry args={[0.8, 32, 32]} />
        <meshStandardMaterial color="#a78bfa" emissive="#a78bfa" emissiveIntensity={0.3} />
      </mesh>
      <mesh position={[2.5, -0.8 + wobble2, -2]}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshStandardMaterial color="#f472b6" emissive="#f472b6" emissiveIntensity={0.3} />
      </mesh>
      <mesh position={[0, 2, -3]}>
        <sphereGeometry args={[0.6, 32, 32]} />
        <meshStandardMaterial color="#60a5fa" emissive="#60a5fa" emissiveIntensity={0.3} />
      </mesh>
      <mesh position={[-1.2, -1.5, -1.5]}>
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshStandardMaterial color="#34d399" emissive="#34d399" emissiveIntensity={0.3} />
      </mesh>

      {/* 背景テキスト（ガラス越しに歪む） */}
      <Text
        position={[0, 0, -1.5]}
        fontSize={0.8}
        color="#ffffff"
        anchorX="center"
        anchorY="middle"
        font="https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuGKYAZ9hiJ-Ek-_EeA.woff2"
      >
        PREMIUM
      </Text>
      <Text
        position={[0, -0.8, -1.5]}
        fontSize={1.2}
        color="#ffffff"
        anchorX="center"
        anchorY="middle"
        font="https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuI6YAZ9hiJ-Ek-_EeA.woff2"
        fontWeight={700}
      >
        Glass
      </Text>
    </>
  );
};

// メインシーン
const GlassScene3D = ({ frame, progress }: {
  frame: number;
  progress: number;
}) => {
  const { camera } = useThree();

  const rotateY = Math.sin(frame * 0.02) * 0.2 - 0.2;
  const rotateX = Math.sin(frame * 0.015) * 0.1 + 0.15;
  const floatY = Math.sin(frame * 0.04) * 0.08;

  useEffect(() => {
    camera.position.set(0, 0, 5);
    camera.lookAt(0, 0, 0);
  }, [camera]);

  return (
    <>
      {/* 環境マップ（これが重要！） */}
      <Environment preset="city" />
      
      {/* ライティング */}
      <ambientLight intensity={0.5} />
      <directionalLight position={[5, 5, 5]} intensity={2} />
      <directionalLight position={[-3, 2, 4]} intensity={1} color="#f0abfc" />

      {/* 背景要素（ガラス越しに見える） */}
      <BackgroundElements frame={frame} />

      {/* メインのガラスボックス */}
      <GlassBox3D
        position={[0, floatY, 0]}
        rotation={[rotateX, rotateY, 0]}
        scale={1}
        progress={progress}
      />

      {/* 浮遊するガラス球（大） */}
      <GlassSphere3D
        position={[2.2, 1.2, 0.8]}
        scale={0.9}
        progress={progress}
        wobbleOffset={0}
        frame={frame}
      />

      {/* 浮遊するガラス球（小） */}
      <GlassSphere3D
        position={[-2, -0.8, 0.6]}
        scale={0.6}
        progress={progress}
        wobbleOffset={50}
        frame={frame}
      />
    </>
  );
};

export const Theme3DGlassThreeJS = ({ startDelay = 0 }: {
  startDelay?: number;
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const progress = spring({
    frame: frame - startDelay,
    fps,
    config: { damping: 15, stiffness: 80 },
  });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
      }}
    >
      <ThreeCanvas
        width={width}
        height={height}
        camera={{
          fov: 50,
          near: 0.1,
          far: 100,
          position: [0, 0, 5],
        }}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 1.2,
        }}
        style={{ background: "transparent" }}
      >
        <Suspense fallback={null}>
          <GlassScene3D frame={frame - startDelay} progress={progress} />
        </Suspense>
      </ThreeCanvas>

      {/* ラベル */}
      <div
        style={{
          position: "absolute",
          left: 60,
          bottom: 60,
          fontFamily: font,
          fontSize: 12,
          color: "rgba(255, 255, 255, 0.6)",
          letterSpacing: 2,
          opacity: progress,
        }}
      >
        THREE.JS 3D GLASS
      </div>
    </AbsoluteFill>
  );
};
