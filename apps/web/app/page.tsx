"use client";

import SiriOrb from "@/components/ui/siri-orb";

const settings = { selectedSize: "192px", animationDuration: 5 };

export default function Demo(props: Partial<typeof settings>) {
  const s = { ...settings, ...props };
  return (
    <div className="h-screen w-screen flex items-center justify-center bg-white">
      <SiriOrb
        size={s.selectedSize}
        animationDuration={s.animationDuration}
        className="drop-shadow-2xl"
      />
    </div>
  );
}
