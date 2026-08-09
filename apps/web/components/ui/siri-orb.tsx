"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { Mic, Cpu, Volume2, Sparkles } from "lucide-react";

export type SiriOrbState = "idle" | "listening" | "processing" | "speaking";

interface SiriOrbProps {
  size?: string | number;
  className?: string;
  colors?: {
    bg?: string;
    c1?: string;
    c2?: string;
    c3?: string;
  };
  animationDuration?: number;
  state?: SiriOrbState;
  audioLevel?: number;
  onClick?: () => void;
}

export const SiriOrb: React.FC<SiriOrbProps> = ({
  size = "192px",
  className,
  colors,
  animationDuration = 20,
  state = "idle",
  audioLevel = 0.2,
  onClick,
}) => {
  const defaultColors = {
    bg: "transparent",
    c1: "oklch(75% 0.15 350)",
    c2: "oklch(80% 0.12 200)",
    c3: "oklch(78% 0.14 280)",
  };

  // State-driven dynamic color and speed overrides
  let stateColors = defaultColors;
  let dynamicDuration = animationDuration;

  if (state === "listening") {
    stateColors = {
      bg: "transparent",
      c1: "oklch(78% 0.18 190)",
      c2: "oklch(82% 0.16 160)",
      c3: "oklch(75% 0.17 210)",
    };
    dynamicDuration = Math.max(2, 6 - audioLevel * 4);
  } else if (state === "processing") {
    stateColors = {
      bg: "transparent",
      c1: "oklch(75% 0.20 300)",
      c2: "oklch(78% 0.18 340)",
      c3: "oklch(72% 0.19 280)",
    };
    dynamicDuration = 3;
  } else if (state === "speaking") {
    stateColors = {
      bg: "transparent",
      c1: "oklch(78% 0.19 340)",
      c2: "oklch(76% 0.18 260)",
      c3: "oklch(80% 0.17 380)",
    };
    dynamicDuration = 4;
  }

  const finalColors = { ...stateColors, ...colors };
  
  // Safely parse size as string or number
  const sizeValue = typeof size === "number" ? size : parseInt(String(size).replace("px", ""), 10) || 192;
  const sizeFormatted = `${sizeValue}px`;

  const blurAmount = Math.max(sizeValue * 0.08, 8);
  const contrastAmount = Math.max(sizeValue * 0.003, 1.8);

  const stateLabel = {
    idle: "Tap to Speak",
    listening: "Listening...",
    processing: "Thinking...",
    speaking: "Speaking...",
  }[state];

  const stateIcon = {
    idle: <Mic className="w-6 h-6 text-indigo-400" />,
    listening: <Mic className="w-6 h-6 text-cyan-400 animate-pulse" />,
    processing: <Cpu className="w-6 h-6 text-purple-400 animate-spin" />,
    speaking: <Volume2 className="w-6 h-6 text-pink-400 animate-bounce" />,
  }[state];

  return (
    <div
      onClick={onClick}
      className={cn(
        "relative flex flex-col items-center justify-center select-none cursor-pointer group",
        className
      )}
    >
      <div
        className={cn("siri-orb transition-transform duration-500 group-hover:scale-105")}
        style={
          {
            width: sizeFormatted,
            height: sizeFormatted,
            "--bg": finalColors.bg,
            "--c1": finalColors.c1,
            "--c2": finalColors.c2,
            "--c3": finalColors.c3,
            "--animation-duration": `${dynamicDuration}s`,
            "--blur-amount": `${blurAmount}px`,
            "--contrast-amount": contrastAmount,
          } as React.CSSProperties
        }
      >
        {/* Center Icon Overlay */}
        <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
          <div className="w-14 h-14 rounded-full glass-panel flex items-center justify-center shadow-xl border border-white/20 group-hover:border-white/40 transition-all duration-300">
            {stateIcon}
          </div>
        </div>

        <style jsx>{`
          @property --angle {
            syntax: "<angle>";
            inherits: false;
            initial-value: 0deg;
          }

          .siri-orb {
            display: grid;
            grid-template-areas: "stack";
            overflow: hidden;
            border-radius: 50%;
            position: relative;
            background: radial-gradient(
              circle,
              rgba(0, 0, 0, 0.08) 0%,
              rgba(0, 0, 0, 0.03) 30%,
              transparent 70%
            );
          }

          /* override for dark mode */
          .dark .siri-orb {
            background: radial-gradient(
              circle,
              rgba(255, 255, 255, 0.08) 0%,
              rgba(255, 255, 255, 0.02) 30%,
              transparent 70%
            );
          }

          .siri-orb::before {
            content: "";
            display: block;
            grid-area: stack;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background:
              conic-gradient(
                from calc(var(--angle) * 1.2) at 30% 65%,
                var(--c3) 0deg,
                transparent 45deg 315deg,
                var(--c3) 360deg
              ),
              conic-gradient(
                from calc(var(--angle) * 0.8) at 70% 35%,
                var(--c2) 0deg,
                transparent 60deg 300deg,
                var(--c2) 360deg
              ),
              conic-gradient(
                from calc(var(--angle) * -1.5) at 65% 75%,
                var(--c1) 0deg,
                transparent 90deg 270deg,
                var(--c1) 360deg
              ),
              conic-gradient(
                from calc(var(--angle) * 2.1) at 25% 25%,
                var(--c2) 0deg,
                transparent 30deg 330deg,
                var(--c2) 360deg
              ),
              conic-gradient(
                from calc(var(--angle) * -0.7) at 80% 80%,
                var(--c1) 0deg,
                transparent 45deg 315deg,
                var(--c1) 360deg
              ),
              radial-gradient(
                ellipse 120% 80% at 40% 60%,
                var(--c3) 0%,
                transparent 50%
              );
            filter: blur(var(--blur-amount)) contrast(var(--contrast-amount))
              saturate(1.2);
            animation: rotate var(--animation-duration) linear infinite;
            transform: translateZ(0);
            will-change: transform;
          }

          .siri-orb::after {
            content: "";
            display: block;
            grid-area: stack;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: radial-gradient(
              circle at 45% 55%,
              rgba(255, 255, 255, 0.1) 0%,
              rgba(255, 255, 255, 0.05) 30%,
              transparent 60%
            );
            mix-blend-mode: overlay;
          }

          @keyframes rotate {
            from {
              --angle: 0deg;
            }
            to {
              --angle: 360deg;
            }
          }

          @media (prefers-reduced-motion: reduce) {
            .siri-orb::before {
              animation: none;
            }
          }
        `}</style>
      </div>

      {/* Real-time State Badge */}
      <div className="mt-3 inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass-pill text-xs font-medium tracking-wide border border-white/10 shadow-lg">
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
      </div>
    </div>
  );
};

export default SiriOrb;
