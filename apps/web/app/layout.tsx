import type { Metadata, Viewport } from "next";
import "./globals.css";

export const viewport: Viewport = {
  themeColor: "#ffffff",
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  metadataBase: new URL("https://agent.enterprise.io"),
  title: {
    default: "Efferd Admin & Autonomous Agent Infrastructure",
    template: "%s | Efferd Platform",
  },
  description: "Production-grade autonomous AI multi-agent platform, continuous vector memory, and cold outreach management system.",
  keywords: [
    "AI Agent Platform",
    "LangGraph",
    "FastAPI",
    "Supabase pgvector",
    "Outreach Automation",
    "Admin Command Dashboard",
    "Voice AI Agent",
  ],
  authors: [{ name: "Enterprise AI Security Team" }],
  creator: "Efferd AI Engine",
  publisher: "Efferd Platform Inc.",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  icons: {
    icon: [
      { url: "/favicon.png", type: "image/png" },
      { url: "/icon.png", type: "image/png" },
    ],
    shortcut: ["/favicon.png"],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
  manifest: "/site.webmanifest",
  openGraph: {
    title: "Efferd Admin & Autonomous Agent Infrastructure",
    description: "Production-grade autonomous AI multi-agent platform and command dashboard.",
    url: "https://agent.enterprise.io",
    siteName: "Efferd Platform",
    images: [
      {
        url: "/favicon.png",
        width: 512,
        height: 512,
        alt: "Efferd Platform Logo",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Efferd Admin & Autonomous Agent Platform",
    description: "Production-grade autonomous AI agent & outreach command dashboard.",
    images: ["/favicon.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-white text-slate-900 antialiased min-h-screen m-0 p-0">
        {children}
      </body>
    </html>
  );
}
