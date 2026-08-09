import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Autonomous AI Agent Platform",
  description: "Continuous learning voice & multi-agent platform powered by LangGraph, Supabase pgvector, Groq, and Gemini Pro.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#08090d] text-gray-100 antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
