import type { Metadata, Viewport } from "next";
import "./globals.css";

export const viewport: Viewport = {
  themeColor: "#ffffff",
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  metadataBase: new URL("https://my-agent.enterprise.io"),
  title: {
    default: "my_agent",
    template: "%s | my_agent",
  },
  description: "my_agent – Continuous learning voice, multi-agent platform, and outreach command system.",
  keywords: [
    "my_agent",
    "AI Agent",
    "LangGraph",
    "FastAPI",
    "Supabase pgvector",
    "Voice AI",
    "Outreach Automation",
    "Dashboard",
  ],
  authors: [{ name: "my_agent Team" }],
  creator: "my_agent Engine",
  publisher: "my_agent Inc.",
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
      { url: "/apple-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
  manifest: "/site.webmanifest",
  openGraph: {
    title: "my_agent",
    description: "my_agent – Autonomous AI agent infrastructure & voice platform.",
    url: "https://my-agent.enterprise.io",
    siteName: "my_agent",
    images: [
      {
        url: "/favicon.png",
        width: 512,
        height: 512,
        alt: "my_agent Logo",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "my_agent",
    description: "my_agent – Autonomous AI agent infrastructure & voice platform.",
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
      <head>
        <link rel="icon" href="/favicon.png" type="image/png" />
        <link rel="shortcut icon" href="/favicon.png" type="image/png" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="apple-touch-startup-image" href="/apple-touch-icon.png" />
      </head>
      <body className="bg-white text-slate-900 antialiased min-h-screen m-0 p-0">
        {children}
      </body>
    </html>
  );
}
