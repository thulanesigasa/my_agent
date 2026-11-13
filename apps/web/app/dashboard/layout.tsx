import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dashboard | my_agent",
  description: "Secure outreach management, vector memory inspector, and human approval queue for my_agent.",
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
