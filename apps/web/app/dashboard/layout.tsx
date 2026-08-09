import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Admin Command Centre – Efferd Agent Platform",
  description: "Secure outreach management, vector memory inspector, and human approval queue.",
  robots: {
    index: false,
    follow: false,
    nocache: true,
    noarchive: true,
    googleBot: {
      index: false,
      follow: false,
      noimageindex: true,
    },
  },
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "#ffffff",
        color: "#111111",
        fontFamily:
          "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}
