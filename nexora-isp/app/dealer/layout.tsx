"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Handshake, Loader2, LogOut } from "lucide-react";

import ThemeToggle from "@/components/layout/ThemeToggle";
import { getCurrentSession } from "@/services/auth.service";
import { clearAuthTokens, getAccessToken, getRefreshToken } from "@/services/auth-storage";

const NAV = [
  { href: "/dealer", label: "My Customers" },
  { href: "/dealer/collections", label: "Collections" },
];

function signOut() {
  clearAuthTokens();
  window.localStorage.removeItem("nexora_user");
  window.localStorage.removeItem("nexora_organization");
  window.localStorage.removeItem("nexora_role");
}

export default function DealerLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [orgName, setOrgName] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    async function restore() {
      if (!getAccessToken() && !getRefreshToken()) {
        router.replace("/");
        return;
      }
      try {
        const session = await getCurrentSession();
        if (!active) return;
        if (session.role !== "DEALER") {
          // Staff accounts use the main workspace, not the dealer portal.
          router.replace("/command-center");
          return;
        }
        setOrgName(session.organization.name);
        setReady(true);
      } catch {
        signOut();
        if (active) router.replace("/");
      }
    }
    void restore();
    return () => {
      active = false;
    };
  }, [router]);

  if (!ready) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070A0F]">
        <Loader2 className="h-7 w-7 animate-spin text-blue-500" />
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[#070A0F] text-slate-100">
      <header className="sticky top-0 z-30 border-b border-[#1C2431] bg-[#0D1117]">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4">
          <div className="flex min-w-0 items-center gap-2">
            <Handshake className="h-5 w-5 shrink-0 text-blue-400" />
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-white">Dealer Portal</p>
              <p className="truncate text-[11px] text-slate-500">{orgName}</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <button
              onClick={() => {
                signOut();
                router.replace("/");
              }}
              className="flex h-9 items-center gap-1.5 rounded-md px-2 text-xs text-slate-400 hover:bg-[#121821] hover:text-slate-200"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-6xl gap-1 px-4">
          {NAV.map((item) => {
            const active = item.href === "/dealer" ? pathname === "/dealer" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`border-b-2 px-3 py-2 text-sm ${
                  active ? "border-blue-500 font-semibold text-white" : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-5">{children}</main>
    </div>
  );
}
