import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Admin Dashboard – Agent Platform",
  description: "Email outreach command centre and agent monitoring dashboard.",
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
        background: "#0f1117",
        color: "#fff",
        fontFamily:
          "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}
