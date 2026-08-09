"use client";

import React, { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Mic, MicOff, Sparkles, Volume2, Cpu } from "lucide-react";

export type SiriOrbState = "idle" | "listening" | "processing" | "speaking";

interface SiriOrbProps {
  state: SiriOrbState;
  audioLevel?: number; // Normalized 0.0 to 1.0
  onClick?: () => void;
  className?: string;
  size?: number;
}

export const SiriOrb: React.FC<SiriOrbProps> = ({
  state = "idle",
  audioLevel = 0.2,
  onClick,
  className = "",
  size = 220,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Dynamic fluid particle canvas animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;

    const render = () => {
      time += 0.03;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const baseRadius = (size / 2) * 0.55;

      // Reactivity modulation based on state and audio level
      let speedMultiplier = 1;
      let waveAmplitude = 8;
      let primaryColor = "rgba(99, 102, 241, "; // Indigo
      let secondaryColor = "rgba(6, 182, 212, "; // Cyan
      let tertiaryColor = "rgba(236, 72, 153, "; // Pink

      if (state === "listening") {
        speedMultiplier = 2.5;
        waveAmplitude = 14 + audioLevel * 25;
        primaryColor = "rgba(6, 182, 212, "; // Cyan
        secondaryColor = "rgba(16, 185, 129, "; // Emerald
      } else if (state === "processing") {
        speedMultiplier = 3.5;
        waveAmplitude = 18;
        primaryColor = "rgba(168, 85, 247, "; // Purple
        secondaryColor = "rgba(236, 72, 153, "; // Pink
      } else if (state === "speaking") {
        speedMultiplier = 2.0;
        waveAmplitude = 12 + Math.sin(time * 4) * 15;
        primaryColor = "rgba(236, 72, 153, "; // Pink
        secondaryColor = "rgba(99, 102, 241, "; // Indigo
      }

      // Draw multi-layered organic fluid wave circles
      for (let layer = 0; layer < 3; layer++) {
        ctx.beginPath();
        const points = 36;
        for (let i = 0; i <= points; i++) {
          const angle = (i / points) * Math.PI * 2;
          const offset =
            Math.sin(angle * (3 + layer) + time * speedMultiplier + layer) *
            waveAmplitude;
          const r = baseRadius + offset;
          const x = centerX + Math.cos(angle) * r;
          const y = centerY + Math.sin(angle) * r;

          if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.closePath();

        const grad = ctx.createRadialGradient(
          centerX,
          centerY,
          5,
          centerX,
          centerY,
          baseRadius * 1.4
        );
        const alpha = 0.35 - layer * 0.08;

        if (layer === 0) {
          grad.addColorStop(0, primaryColor + alpha + ")");
          grad.addColorStop(1, secondaryColor + "0)");
        } else if (layer === 1) {
          grad.addColorStop(0, secondaryColor + alpha + ")");
          grad.addColorStop(1, tertiaryColor + "0)");
        } else {
          grad.addColorStop(0, tertiaryColor + alpha + ")");
          grad.addColorStop(1, primaryColor + "0)");
        }

        ctx.fillStyle = grad;
        ctx.fill();
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [state, audioLevel, size]);

  // Status badges
  const stateLabel = {
    idle: "Tap to Speak",
    listening: "Listening...",
    processing: "Thinking (LangGraph)...",
    speaking: "Speaking (Edge-TTS)...",
  }[state];

  const stateIcon = {
    idle: <Mic className="w-6 h-6 text-indigo-400" />,
    listening: <Mic className="w-6 h-6 text-cyan-400 animate-pulse" />,
    processing: <Cpu className="w-6 h-6 text-purple-400 animate-spin" />,
    speaking: <Volume2 className="w-6 h-6 text-pink-400 animate-bounce" />,
  }[state];

  return (
    <div
      className={`relative flex flex-col items-center justify-center select-none cursor-pointer group ${className}`}
      onClick={onClick}
    >
      {/* Outer Glowing Aura Ring */}
      <motion.div
        animate={{
          scale: state === "listening" ? [1, 1.08, 1] : [1, 1.03, 1],
          opacity: state === "idle" ? 0.4 : 0.8,
        }}
        transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
        className="absolute rounded-full pointer-events-none filter blur-2xl transition-all duration-700"
        style={{
          width: size * 1.3,
          height: size * 1.3,
          background:
            state === "listening"
              ? "radial-gradient(circle, rgba(6, 182, 212, 0.4) 0%, rgba(99, 102, 241, 0) 70%)"
              : state === "processing"
              ? "radial-gradient(circle, rgba(168, 85, 247, 0.4) 0%, rgba(236, 72, 153, 0) 70%)"
              : state === "speaking"
              ? "radial-gradient(circle, rgba(236, 72, 153, 0.45) 0%, rgba(99, 102, 241, 0) 70%)"
              : "radial-gradient(circle, rgba(99, 102, 241, 0.25) 0%, rgba(6, 182, 212, 0) 70%)",
        }}
      />

      {/* Fluid Dynamic Canvas */}
      <div className="relative flex items-center justify-center">
        <canvas
          ref={canvasRef}
          width={size * 1.5}
          height={size * 1.5}
          className="pointer-events-none transition-transform duration-500 transform group-hover:scale-105"
        />

        {/* Center Icon Overlay */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-16 h-16 rounded-full glass-panel flex items-center justify-center shadow-xl border border-white/10 group-hover:border-white/30 transition-all duration-300">
            {stateIcon}
          </div>
        </div>
      </div>

      {/* Real-time State Badge */}
      <motion.div
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-3 inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass-pill text-xs font-medium tracking-wide border border-white/10 shadow-lg"
      >
        <Sparkles className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
        <span
          className={
            state === "listening"
              ? "text-cyan-300 font-semibold"
              : state === "processing"
              ? "text-purple-300 font-semibold"
              : state === "speaking"
              ? "text-pink-300 font-semibold"
              : "text-gray-300"
          }
        >
          {stateLabel}
        </span>
      </motion.div>
    </div>
  );
};
