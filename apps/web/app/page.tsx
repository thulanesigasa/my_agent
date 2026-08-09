"use client";

import SiriOrb from "@/components/ui/siri-orb";

const settings = { selectedSize: "192px", animationDuration: 5 };

export default function Demo(props: Partial<typeof settings>) {
  const s = { ...settings, ...props };
  return (
    <main className="h-screen w-screen flex items-center justify-center bg-white m-0 p-0 overflow-hidden">
      <SiriOrb
        size={s.selectedSize}
        animationDuration={s.animationDuration}
        className="drop-shadow-2xl"
      />
    </main>
  );
}
