"use client";

import React, { useState, useEffect, useRef } from "react";
import SiriOrb from "@/components/ui/siri-orb";
import { AudioStreamManager, SiriOrbState } from "@/lib/audio";

export default function Demo() {
  const [orbState, setOrbState] = useState<SiriOrbState>("idle");
  const [transcription, setTranscription] = useState("");
  const [responseText, setResponseText] = useState("");
  const audioManagerRef = useRef<AudioStreamManager | null>(null);

  useEffect(() => {
    // Initialize real-time WebSocket audio manager
    const manager = new AudioStreamManager({
      onStateChange: (state) => setOrbState(state),
      onTranscription: (text) => setTranscription(text),
      onResponseText: (text) => setResponseText(text),
      onError: (err) => console.error("Stream error:", err),
    });

    manager.connect();
    audioManagerRef.current = manager;

    return () => {
      manager.disconnect();
    };
  }, []);

  const handleOrbClick = async () => {
    if (orbState === "idle") {
      const started = await audioManagerRef.current?.startStreaming();
      if (!started) setOrbState("idle");
    } else if (orbState === "listening") {
      audioManagerRef.current?.stopStreaming();
    }
  };

  // Dynamic prop adjustments based on real-time agent state
  const orbSize = orbState === "idle" ? "192px" : orbState === "listening" ? "240px" : "210px";
  const animDuration =
    orbState === "listening"
      ? 4
      : orbState === "processing"
      ? 2.5
      : orbState === "speaking"
      ? 3.5
      : 15;

  return (
    <main className="h-screen w-screen flex flex-col items-center justify-center bg-white m-0 p-0 overflow-hidden select-none">
      <div className="flex flex-col items-center justify-center gap-6">
        <div onClick={handleOrbClick} className="cursor-pointer">
          <SiriOrb
            size={orbSize}
            animationDuration={animDuration}
            className="drop-shadow-2xl transition-all duration-500"
          />
        </div>

        {/* Live Status Indicator */}
        <div className="flex flex-col items-center gap-1.5 text-center max-w-md px-6">
          <span
            className={`text-xs font-semibold uppercase tracking-widest ${
              orbState === "listening"
                ? "text-cyan-600 animate-pulse"
                : orbState === "processing"
                ? "text-purple-600 animate-pulse"
                : orbState === "speaking"
                ? "text-pink-600"
                : "text-slate-400"
            }`}
          >
            {orbState === "idle"
              ? "Click Orb to Speak"
              : orbState === "listening"
              ? "Listening... Click to Finish"
              : orbState === "processing"
              ? "Thinking (LangGraph)..."
              : "Speaking (Edge-TTS)..."}
          </span>

          {transcription && (
            <p className="text-xs text-slate-500 italic mt-1 max-w-sm">
              "{transcription}"
            </p>
          )}

          {responseText && (
            <p className="text-sm font-medium text-slate-800 leading-snug mt-2">
              {responseText}
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
