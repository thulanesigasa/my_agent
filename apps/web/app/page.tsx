"use client";

import React, { useState, useEffect, useRef } from "react";
import SiriOrb from "@/components/ui/siri-orb";
import { AudioStreamManager, SiriOrbState } from "@/lib/audio";

const settings = { selectedSize: "192px", animationDuration: 5 };

export default function Demo(props: Partial<typeof settings>) {
  const s = { ...settings, ...props };
  const [orbState, setOrbState] = useState<SiriOrbState>("idle");
  const [transcription, setTranscription] = useState("");
  const [responseText, setResponseText] = useState("");
  const audioManagerRef = useRef<AudioStreamManager | null>(null);

  useEffect(() => {
    const manager = new AudioStreamManager({
      onStateChange: (state) => setOrbState(state),
      onTranscription: (text) => setTranscription(text),
      onResponseText: (text) => setResponseText(text),
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

  const animDuration =
    orbState === "listening"
      ? 4
      : orbState === "processing"
      ? 2.5
      : orbState === "speaking"
      ? 3.5
      : s.animationDuration;

  return (
    <main className="h-screen w-screen flex flex-col items-center justify-center bg-white m-0 p-0 overflow-hidden select-none text-center">
      <div className="flex flex-col items-center justify-center gap-4 text-center w-full max-w-lg mx-auto">
        <div onClick={handleOrbClick} className="cursor-pointer flex flex-col items-center justify-center w-full mx-auto">
          <SiriOrb
            size={s.selectedSize}
            animationDuration={animDuration}
            className="drop-shadow-2xl"
          />
        </div>

        <div className="flex flex-col items-center justify-center text-center w-full mx-auto" style={{ transform: "translateX(100px)" }}>
          <span className="text-xs font-semibold tracking-wide text-slate-600 text-center block w-full">
            {orbState === "idle"
              ? "Click Orb to Speak"
              : orbState === "listening"
              ? "Listening... Click to Finish"
              : orbState === "processing"
              ? "Thinking..."
              : "Speaking..."}
          </span>

          {transcription && (
            <p className="text-xs text-slate-400 italic mt-1 text-center w-full max-w-sm">
              "{transcription}"
            </p>
          )}

          {responseText && (
            <p className="text-sm font-medium text-slate-800 leading-snug mt-2 text-center w-full">
              {responseText}
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
