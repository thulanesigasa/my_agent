import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SiriOrb Platform",
  description: "Continuous learning voice & multi-agent platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-white text-slate-900 antialiased min-h-screen m-0 p-0 flex items-center justify-center">
        {children}
      </body>
    </html>
  );
}
