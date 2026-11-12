import { useRef, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Environment, Html } from '@react-three/drei';
import { Vector3, Mesh } from 'three';

interface FloatingBoxProps {
  position?: Vector3;
  color?: string;
  size?: number;
}

function BoxComponent({ position, color, size = 1 }: FloatingBoxProps) {
  const ref = useRef<Mesh>(null!);

  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.x = Math.sin(state.clock.getElapsedTime() * 0.5) * 0.3;
      ref.current.rotation.y += 0.01;
    }
  });

  const pos = position || new Vector3(0, 0, 0);

  return (
    <mesh ref={ref} position={pos}>
      <boxGeometry args={[size, size, size]} />
      <meshStandardMaterial color={color} roughness={0.1} metalness={0.8} />
    </mesh>
  );
}

export function FloatingBoxScene({ primaryColor = '#0ea5e9', secondaryColor = '#7c3aed' }: { primaryColor?: string; secondaryColor?: string }) {
  const boxes: FloatingBoxProps[] = [
    { position: new Vector3(0, 0, 0), color: primaryColor, size: 1.5 },
    { position: new Vector3(-2, 1, -1), color: secondaryColor, size: 1 },
    { position: new Vector3(1.5, -0.5, 0.5), color: '#8b5cf6', size: 0.8 },
  ];

  return (
    <Canvas
      camera={{ position: new Vector3(0, 0, 8), fov: 50 }}
      style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
    >
      <color attach="background" args={['transparent']} />
      <ambientLight intensity={0.5} />
      <directionalLight position={new Vector3(5, 5, 5)} intensity={1} />
      <spotLight position={new Vector3(-5, -5, -5)} intensity={0.5} />

      <Suspense fallback={<Html center>Loading...</Html>}>
        <Environment preset="city" />
        {boxes.map((box, i) => (
          <Float key={i} speed={1 + i * 0.5} rotationIntensity={0.3} floatIntensity={0.5}>
            <BoxComponent
              position={box.position}
              color={box.color}
              size={box.size}
            />
          </Float>
        ))}
      </Suspense>
    </Canvas>
  );
}

interface OrbProps {
  position: Vector3;
  color?: string;
  radius?: number;
}

function Orb({ position, color = '#0ea5e9', radius = 0.5 }: OrbProps) {
  const ref = useRef<Mesh>(null!);

  useFrame((state) => {
    if (ref.current) {
      ref.current.position.y = position.y + Math.sin(state.clock.getElapsedTime() * 1.5) * 0.2;
      ref.current.rotation.x = state.clock.getElapsedTime() * 0.3;
      ref.current.rotation.y = state.clock.getElapsedTime() * 0.2;
    }
  });

  return (
    <mesh ref={ref} position={position}>
      <sphereGeometry args={[radius, 32, 32]} />
      <meshStandardMaterial color={color} roughness={0.2} metalness={0.7} />
    </mesh>
  );
}

export function FloatingOrbs({ count = 5 }: { count?: number }) {
  const colors = ['#0ea5e9', '#7c3aed', '#8b5cf6', '#f59e0b', '#10b981'];

  return (
    <div className="absolute inset-0 pointer-events-none">
      <Canvas camera={{ position: new Vector3(0, 0, 10), fov: 50 }}>
        <color attach="background" args={['transparent']} />
        <ambientLight intensity={0.7} />
        <directionalLight position={new Vector3(10, 10, 10)} intensity={0.8} />

        <Suspense fallback={null}>
          <Environment preset="dawn" />
          {Array.from({ length: count }).map((_, i) => {
            const pos = new Vector3(
              (Math.random() - 0.5) * 10,
              (Math.random() - 0.5) * 6,
              (Math.random() - 0.5) * 5
            );
            return (
              <Float key={i} speed={0.5 + i * 0.2} rotationIntensity={0.3} floatIntensity={0.5}>
                <Orb
                  position={pos}
                  color={colors[i % colors.length]}
                  radius={0.3 + Math.random() * 0.4}
                />
              </Float>
            );
          })}
        </Suspense>
      </Canvas>
    </div>
  );
}

export function MiniSphere({ position }: { position: Vector3 }) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[0.15, 16, 16]} />
      <meshBasicMaterial color="#ffffff" />
    </mesh>
  );
}