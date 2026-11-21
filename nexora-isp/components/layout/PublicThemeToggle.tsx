"use client";

import { usePathname } from "next/navigation";

import ThemeToggle from "@/components/layout/ThemeToggle";

// Signed-in areas have the toggle in their own header; these public pages have no header.
const PUBLIC_PAGES = ["/", "/signup", "/forgot-password", "/reset-password"];
const PUBLIC_PREFIXES = ["/apply/", "/registration/"];

export default function PublicThemeToggle() {
  const pathname = usePathname() ?? "";
  const isPublic = PUBLIC_PAGES.includes(pathname) || PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  if (!isPublic) return null;
  return (
    <div className="fixed right-3 top-3 z-50 rounded-lg border border-[#202938] bg-[#0D1117]/90 shadow-lg backdrop-blur">
      <ThemeToggle />
    </div>
  );
}
