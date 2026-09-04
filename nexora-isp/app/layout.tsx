import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "NEXORA ISP — Unified Telecom & Billing Operating System",
    template: "%s | NEXORA ISP",
  },
  description: "Enterprise multi-tenant ISP operations, automated billing, NOC monitoring, and field workforce management.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${geistSans.variable} ${geistMono.variable}`}>
      <body className={`${geistSans.className} min-h-screen bg-[var(--background)] font-sans text-[var(--foreground)] antialiased`}>
        {children}
        <Toaster richColors position="top-right" theme="dark" closeButton />
      </body>
    </html>
  );
}