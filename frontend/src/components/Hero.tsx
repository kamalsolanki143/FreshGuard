import { useRef, Suspense } from 'react';
import { motion } from 'framer-motion';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float } from '@react-three/drei';
import { Mesh, Vector3 } from 'three';
import { ShieldCheck, ArrowRight, CheckCircle2, Zap, Database, Globe } from 'lucide-react';
import { Link } from 'react-router-dom';

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
          color="#0ea5e9"
          wireframe
          roughness={0.1}
          metalness={0.9}
        />
      </mesh>

      {/* Outer luminous ring */}
      <mesh ref={ringRef} scale={1.8}>
        <torusGeometry args={[1, 0.04, 16, 100]} />
        <meshStandardMaterial color="#8b5cf6" roughness={0.2} metalness={0.8} />
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
    <section className="relative min-h-screen flex items-center justify-center pt-28 pb-20 overflow-hidden bg-slate-950 text-slate-100 bg-grid-pattern">
      {/* Ambient background light orbs */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[650px] h-[380px] bg-gradient-to-tr from-cyan-500/20 via-primary-600/20 to-purple-600/20 blur-3xl pointer-events-none rounded-full" />
      <div className="absolute bottom-10 right-10 w-96 h-96 bg-purple-600/15 blur-3xl pointer-events-none rounded-full" />
      <div className="absolute top-20 left-10 w-80 h-80 bg-cyan-500/15 blur-3xl pointer-events-none rounded-full" />

      {/* 3D Canvas Background strictly isolated behind content */}
      <div className="absolute inset-0 pointer-events-none opacity-30 z-0">
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
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-slate-900/90 border border-slate-700/80 shadow-lg shadow-cyan-500/10 backdrop-blur-md mb-8"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span className="flex h-2.5 w-2.5 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span className="text-xs sm:text-sm font-semibold text-slate-200">
            Real-Time Freshness Verification for LLM Gateways
          </span>
          <span className="hidden sm:inline-block text-xs font-bold text-cyan-300 bg-cyan-950/90 border border-cyan-800/80 px-2 py-0.5 rounded-full">
            Tavily + Bifrost
          </span>
        </motion.div>

        {/* Main Title - High Contrast White & Vibrant Gradient */}
        <motion.h1
          className="text-4xl sm:text-6xl lg:text-7xl font-black text-white tracking-tight leading-[1.12] mb-6 drop-shadow-sm"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut', delay: 0.1 }}
        >
          Stop Stale AI Answers{' '}
          <span className="block mt-2">
            <span className="gradient-text">Before They Reach Production.</span>
          </span>
        </motion.h1>

        {/* Subtitle - High-contrast readable text */}
        <motion.p
          className="text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto font-normal leading-relaxed mb-10"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut', delay: 0.2 }}
        >
          FreshGuard verifies time-sensitive LLM claims using live web evidence and protects Bifrost semantic caches from outdated or contradicted responses.
        </motion.p>

        {/* Call to Actions */}
        <motion.div
          className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-14"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut', delay: 0.3 }}
        >
          <Link
            to="/dashboard/verify"
            className="w-full sm:w-auto px-8 py-4 bg-gradient-to-r from-cyan-500 via-primary-600 to-purple-600 text-white rounded-xl font-bold text-lg shadow-xl shadow-cyan-500/25 hover:shadow-cyan-500/40 hover:opacity-95 flex items-center justify-center gap-2 group transition-all"
          >
            <span>Try Live Demo</span>
            <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
          </Link>

          <Link
            to="/dashboard"
            className="w-full sm:w-auto px-8 py-4 bg-slate-900/90 hover:bg-slate-800 text-slate-100 border-2 border-slate-700 hover:border-cyan-500/80 rounded-xl font-bold text-lg shadow-lg hover:text-white transition-all flex items-center justify-center gap-2"
          >
            <ShieldCheck className="h-5 w-5 text-cyan-400" />
            <span>Explore Dashboard</span>
          </Link>

          <Link
            to="/login"
            className="w-full sm:w-auto px-6 py-4 bg-slate-950/80 hover:bg-slate-900 text-slate-300 hover:text-white border border-slate-800 hover:border-slate-700 rounded-xl font-semibold text-base transition-all flex items-center justify-center"
          >
            <span>Sign In</span>
          </Link>
        </motion.div>

        {/* Feature Highlights Pills */}
        <motion.div
          className="flex flex-wrap justify-center items-center gap-3 sm:gap-6 text-sm font-medium text-slate-300 mb-14"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
        >
          <div className="flex items-center gap-2 bg-slate-900/90 backdrop-blur-sm px-4 py-2 rounded-full border border-slate-800 shadow-md">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span>Pricing &amp; Version Guard</span>
          </div>
          <div className="flex items-center gap-2 bg-slate-900/90 backdrop-blur-sm px-4 py-2 rounded-full border border-slate-800 shadow-md">
            <Zap className="h-4 w-4 text-amber-400" />
            <span>Sub-20ms Interception</span>
          </div>
          <div className="flex items-center gap-2 bg-slate-900/90 backdrop-blur-sm px-4 py-2 rounded-full border border-slate-800 shadow-md">
            <Database className="h-4 w-4 text-purple-400" />
            <span>Bifrost Cache Shield</span>
          </div>
          <div className="flex items-center gap-2 bg-slate-900/90 backdrop-blur-sm px-4 py-2 rounded-full border border-slate-800 shadow-md">
            <Globe className="h-4 w-4 text-cyan-400" />
            <span>Live Tavily Evidence</span>
          </div>
        </motion.div>

        {/* Metrics Grid - Verified Technical Capabilities */}
        <motion.div
          className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5 }}
        >
          <div className="bg-slate-900/90 backdrop-blur-md p-5 rounded-2xl border border-cyan-800/60 shadow-xl shadow-cyan-950/40 hover:border-cyan-500/60 transition-all text-center group">
            <div className="text-3xl sm:text-4xl font-black text-cyan-400 mb-1.5">3 Domains</div>
            <div className="text-xs sm:text-sm font-bold text-white">Targeted Verification</div>
            <div className="text-[11px] text-slate-400 mt-1">Pricing, Versions, Leadership</div>
          </div>

          <div className="bg-slate-900/90 backdrop-blur-md p-5 rounded-2xl border border-emerald-800/60 shadow-xl shadow-emerald-950/40 hover:border-emerald-500/60 transition-all text-center group">
            <div className="text-3xl sm:text-4xl font-black text-emerald-400 mb-1.5">Real-Time</div>
            <div className="text-xs sm:text-sm font-bold text-white">Live Web Evidence</div>
            <div className="text-[11px] text-slate-400 mt-1">Tavily API search grounding</div>
          </div>

          <div className="bg-slate-900/90 backdrop-blur-md p-5 rounded-2xl border border-primary-800/60 shadow-xl shadow-primary-950/40 hover:border-primary-500/60 transition-all text-center group">
            <div className="text-3xl sm:text-4xl font-black text-primary-400 mb-1.5">&lt; 20ms</div>
            <div className="text-xs sm:text-sm font-bold text-white">Plugin Middleware</div>
            <div className="text-[11px] text-slate-400 mt-1">Ultra-low Go interception</div>
          </div>

          <div className="bg-slate-900/90 backdrop-blur-md p-5 rounded-2xl border border-purple-800/60 shadow-xl shadow-purple-950/40 hover:border-purple-500/60 transition-all text-center group">
            <div className="text-3xl sm:text-4xl font-black text-purple-400 mb-1.5">100%</div>
            <div className="text-xs sm:text-sm font-bold text-white">Cache Invalidation</div>
            <div className="text-[11px] text-slate-400 mt-1">Purges contradicted entries</div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}