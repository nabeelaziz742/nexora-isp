"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Handshake, KeyRound, Loader2, LogOut } from "lucide-react";

import { DealerMeContext, canSeeCustomers } from "@/components/dealers/DealerMeContext";
import ThemeToggle from "@/components/layout/ThemeToggle";
import ChangePasswordModal from "@/components/ui/ChangePasswordModal";
import { changePassword, getCurrentSession } from "@/services/auth.service";
import { clearAuthTokens, getAccessToken, getRefreshToken } from "@/services/auth-storage";
import { dealerPortalService, type DealerMe } from "@/services/dealer-portal.service";

// Each tab shows only when the signed-in person may use it.
const NAV: { href: string; label: string; show: (me: DealerMe) => boolean }[] = [
  { href: "/dealer", label: "My Customers", show: () => true },
  { href: "/dealer/requests", label: "New Customer", show: (me) => me.rights.can_request_customers },
  { href: "/dealer/collections", label: "Collections", show: (me) => me.rights.can_view_collections },
  { href: "/dealer/expenses", label: "Expenses", show: () => true },
  { href: "/dealer/employees", label: "Employees", show: (me) => me.is_dealer },
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
  const [me, setMe] = useState<DealerMe | null>(null);
  const [ready, setReady] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

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
        const summary = await dealerPortalService.getSummary();
        if (!active) return;
        setMe(summary.me);
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

  if (!ready || !me) {
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
              <p className="truncate text-[11px] text-slate-500">
                {orgName}
                {!me.is_dealer && ` · ${me.name}`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <button
              onClick={() => setChangingPassword(true)}
              aria-label="Change password"
              title="Change password"
              className="flex h-9 w-9 items-center justify-center rounded-md text-slate-400 hover:bg-[#121821] hover:text-slate-200"
            >
              <KeyRound className="h-4 w-4" />
            </button>
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
          {NAV.filter((item) => item.show(me)).map((item) => {
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
      <main className="mx-auto max-w-6xl px-4 py-5">
        <DealerMeContext.Provider value={me}>
          {pathname === "/dealer" && !canSeeCustomers(me.rights) ? (
            <div className="rounded-xl border border-[#1C2431] bg-[#0D1117] p-8 text-center text-sm text-slate-400">
              Welcome, {me.name}. Use the tabs above for the work your dealer has given you.
            </div>
          ) : (
            children
          )}
        </DealerMeContext.Provider>
      </main>
      {changingPassword && (
        <ChangePasswordModal onClose={() => setChangingPassword(false)} submit={changePassword} />
      )}
    </div>
  );
}
