import { useRef, Suspense } from 'react';
import { motion } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float } from '@react-three/drei';
import { Mesh, Vector3 } from 'three';
import { ShieldCheck, ArrowRight, CheckCircle2, Zap, Database } from 'lucide-react';

function GlowingTechCore() {
  const meshRef = useRef<Mesh>(null!);
  const ringRef = useRef<Mesh>(null!);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.x = state.clock.getElapsedTime() * 0.25;
      meshRef.current.rotation.y = state.clock.getElapsedTime() * 0.35;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z = -state.clock.getElapsedTime() * 0.2;
      ringRef.current.rotation.x = Math.sin(state.clock.getElapsedTime() * 0.5) * 0.3;
    }
  });

  return (
    <group position={[0, 0, 0]}>
      {/* Central multifaceted tech orb */}
      <mesh ref={meshRef} scale={1.1}>
        <icosahedronGeometry args={[1, 2]} />
        <meshStandardMaterial
          color="#0284c7"
          wireframe
          roughness={0.1}
          metalness={0.9}
        />
      </mesh>

      {/* Outer luminous ring */}
      <mesh ref={ringRef} scale={1.8}>
        <torusGeometry args={[1, 0.04, 16, 100]} />
        <meshStandardMaterial color="#9333ea" roughness={0.2} metalness={0.8} />
      </mesh>

      {/* Floating accent geometries */}
      <Float speed={2} rotationIntensity={0.6} floatIntensity={0.8}>
        <mesh position={[-3.2, 1.8, -1]} scale={0.45}>
          <octahedronGeometry args={[1]} />
          <meshStandardMaterial color="#10b981" roughness={0.1} metalness={0.7} />
        </mesh>
      </Float>

      <Float speed={2.5} rotationIntensity={0.5} floatIntensity={0.6}>
        <mesh position={[3.4, -1.5, -0.5]} scale={0.5}>
          <dodecahedronGeometry args={[1]} />
          <meshStandardMaterial color="#06b6d4" roughness={0.1} metalness={0.8} />
        </mesh>
      </Float>
    </group>
  );
}

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center pt-24 pb-16 overflow-hidden bg-gradient-to-b from-sky-50/60 via-white to-indigo-50/40 bg-grid-pattern">
      {/* Ambient background light orbs */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-gradient-to-tr from-cyan-400/15 via-primary-500/15 to-purple-500/15 blur-3xl pointer-events-none rounded-full" />
      <div className="absolute bottom-10 right-10 w-96 h-96 bg-purple-400/10 blur-3xl pointer-events-none rounded-full" />
      <div className="absolute top-20 left-10 w-80 h-80 bg-cyan-400/10 blur-3xl pointer-events-none rounded-full" />

      {/* 3D Canvas Background */}
      <div className="absolute inset-0 pointer-events-none opacity-45">
        <Canvas camera={{ position: new Vector3(0, 0, 6), fov: 60 }}>
          <ambientLight intensity={0.8} />
          <directionalLight position={new Vector3(10, 10, 5)} intensity={1.5} color="#38bdf8" />
          <pointLight position={new Vector3(-10, -10, -5)} intensity={1.2} color="#c084fc" />
          <pointLight position={new Vector3(5, -5, 5)} intensity={1} color="#34d399" />
          <Suspense fallback={null}>
            <GlowingTechCore />
          </Suspense>
        </Canvas>
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Top Feature Pill Badge */}
        <motion.div
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/90 border border-primary-200/80 shadow-md shadow-primary-500/5 backdrop-blur-md mb-8"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span className="flex h-2.5 w-2.5 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span className="text-xs sm:text-sm font-semibold text-slate-800">
            Real-Time Freshness Verification for LLM Gateways
          </span>
          <span className="hidden sm:inline-block text-xs font-bold text-primary-700 bg-primary-100/80 px-2 py-0.5 rounded-full">
            Tavily + Bifrost
          </span>
        </motion.div>

        {/* Main Title */}
        <motion.h1
          className="text-4xl sm:text-6xl lg:text-7xl font-black text-slate-900 tracking-tight leading-[1.1] mb-6"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut', delay: 0.1 }}
        >
          Stop Stale AI Answers{' '}
          <span className="block mt-2">
            <span className="gradient-text">Before They Reach Production.</span>
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          className="text-lg sm:text-xl text-slate-700 max-w-3xl mx-auto font-normal leading-relaxed mb-10"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut', delay: 0.2 }}
        >
          FreshGuard verifies time-sensitive LLM claims using live web evidence and protects Bifrost semantic caches from outdated or contradicted responses.
        </motion.p>

        {/* Call to Actions */}
        <motion.div
          className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut', delay: 0.3 }}
        >
          <motion.a
            href="/dashboard/verify"
            className="w-full sm:w-auto px-8 py-4 bg-gradient-to-r from-cyan-600 via-primary-600 to-purple-600 text-white rounded-xl font-bold text-lg shadow-xl shadow-primary-500/30 hover:shadow-primary-500/50 flex items-center justify-center gap-2 group transition-all"
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
          >
            <span>Try Live Demo</span>
            <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
          </motion.a>

          <motion.a
            href="/dashboard"
            className="w-full sm:w-auto px-8 py-4 bg-white hover:bg-slate-50 text-slate-800 border-2 border-slate-300 hover:border-primary-500 rounded-xl font-bold text-lg shadow-sm hover:text-primary-600 transition-all flex items-center justify-center gap-2"
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
          >
            <ShieldCheck className="h-5 w-5 text-primary-600" />
            <span>Explore Dashboard</span>
          </motion.a>
        </motion.div>

        {/* Feature Highlights Pills */}
        <motion.div
          className="flex flex-wrap justify-center items-center gap-4 sm:gap-8 text-sm font-medium text-slate-700 mb-14"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
        >
          <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm px-3.5 py-1.5 rounded-full border border-slate-200 shadow-sm">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span>Zero Hallucinated Prices</span>
          </div>
          <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm px-3.5 py-1.5 rounded-full border border-slate-200 shadow-sm">
            <Zap className="h-4 w-4 text-amber-500" />
            <span>5-20ms Interception</span>
          </div>
          <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm px-3.5 py-1.5 rounded-full border border-slate-200 shadow-sm">
            <Database className="h-4 w-4 text-purple-600" />
            <span>Semantic Cache Shield</span>
          </div>
        </motion.div>

        {/* Metrics Grid */}
        <motion.div
          className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5 }}
        >
          <div className="bg-white/90 backdrop-blur-md p-5 rounded-2xl border border-rose-200/80 shadow-lg shadow-rose-500/5 hover:shadow-rose-500/15 transition-all text-center group">
            <div className="text-3xl sm:text-4xl font-black gradient-text-rose mb-1.5">$2.3M+</div>
            <div className="text-xs sm:text-sm font-bold text-slate-900">Pricing Errors Prevented</div>
            <div className="text-[11px] text-slate-500 mt-1">Based on enterprise tests</div>
          </div>

          <div className="bg-white/90 backdrop-blur-md p-5 rounded-2xl border border-emerald-200/80 shadow-lg shadow-emerald-500/5 hover:shadow-emerald-500/15 transition-all text-center group">
            <div className="text-3xl sm:text-4xl font-black gradient-text-emerald mb-1.5">99.7%</div>
            <div className="text-xs sm:text-sm font-bold text-slate-900">Verification Accuracy</div>
            <div className="text-[11px] text-slate-500 mt-1">Tavily web evidence</div>
          </div>

          <div className="bg-white/90 backdrop-blur-md p-5 rounded-2xl border border-cyan-200/80 shadow-lg shadow-cyan-500/5 hover:shadow-cyan-500/15 transition-all text-center group">
            <div className="text-3xl sm:text-4xl font-black gradient-text mb-1.5">&lt; 20ms</div>
            <div className="text-xs sm:text-sm font-bold text-slate-900">Pipeline Latency</div>
            <div className="text-[11px] text-slate-500 mt-1">Lightweight Go plugin</div>
          </div>

          <div className="bg-white/90 backdrop-blur-md p-5 rounded-2xl border border-purple-200/80 shadow-lg shadow-purple-500/5 hover:shadow-purple-500/15 transition-all text-center group">
            <div className="text-3xl sm:text-4xl font-black gradient-text mb-1.5">100%</div>
            <div className="text-xs sm:text-sm font-bold text-slate-900">Cache Invalidation</div>
            <div className="text-[11px] text-slate-500 mt-1">Protects Bifrost entries</div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
