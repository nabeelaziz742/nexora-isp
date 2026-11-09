"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Building2,
  CalendarClock,
  KeyRound,
  LayoutDashboard,
  Loader2,
  LogOut,
  Menu,
  ReceiptText,
  Settings,
  ShieldCheck,
  X,
} from "lucide-react";

import ThemeToggle from "@/components/layout/ThemeToggle";
import ChangePasswordModal from "@/components/ui/ChangePasswordModal";
import { changeSuperAdminPassword } from "@/services/onboarding.service";

const NAV = [
  { href: "/superadmin", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { href: "/superadmin/verifications", label: "Payment Verification", icon: ReceiptText },
  { href: "/superadmin/isps", label: "All ISPs", icon: Building2 },
  { href: "/superadmin/subscriptions", label: "Subscriptions", icon: CalendarClock },
  { href: "/superadmin/settings", label: "Payment Settings", icon: Settings },
];

export function clearSuperAdminSession() {
  localStorage.removeItem("nexora_superadmin_access");
  localStorage.removeItem("nexora_superadmin_refresh");
}

export default function SuperAdminShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const isLogin = pathname === "/superadmin/login";

  useEffect(() => {
    if (isLogin) return;
    if (!localStorage.getItem("nexora_superadmin_access")) {
      router.replace("/superadmin/login");
      return;
    }
    // Only known after mount: the token lives in localStorage.
    setReady(true);
  }, [isLogin, router]);

  if (isLogin) return <>{children}</>;

  if (!ready) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#070A0F]">
        <Loader2 className="h-7 w-7 animate-spin text-blue-500" />
      </main>
    );
  }

  function logout() {
    clearSuperAdminSession();
    router.replace("/superadmin/login");
  }

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);

  const nav = (
    <nav className="space-y-1">
      {NAV.map(({ href, label, icon: Icon, exact }) => (
        <Link
          key={href}
          href={href}
          onClick={() => setMenuOpen(false)}
          className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
            isActive(href, exact)
              ? "bg-blue-600 font-semibold text-white"
              : "text-slate-400 hover:bg-[#121821] hover:text-slate-200"
          }`}
        >
          <Icon className="h-4 w-4" />
          {label}
        </Link>
      ))}
    </nav>
  );

  return (
    <div className="flex min-h-screen bg-[#070A0F] text-slate-100">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-[#1C2431] bg-[#0D1117] p-4 lg:flex">
        <div className="mb-6 flex items-center gap-2 px-2">
          <ShieldCheck className="h-6 w-6 text-blue-400" />
          <div>
            <p className="text-sm font-bold text-white">Nexora Super Admin</p>
            <p className="text-[11px] text-slate-500">Platform control</p>
          </div>
        </div>
        {nav}
        <button
          onClick={logout}
          className="mt-auto flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400 hover:bg-[#121821] hover:text-slate-200"
        >
          <LogOut className="h-4 w-4" /> Sign out
        </button>
      </aside>

      {menuOpen && (
        <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setMenuOpen(false)}>
          <aside
            className="flex h-full w-64 flex-col border-r border-[#1C2431] bg-[#0D1117] p-4"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-6 flex items-center justify-between px-2">
              <p className="text-sm font-bold text-white">Nexora Super Admin</p>
              <button onClick={() => setMenuOpen(false)} aria-label="Close menu">
                <X className="h-5 w-5 text-slate-400" />
              </button>
            </div>
            {nav}
            <button
              onClick={logout}
              className="mt-auto flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400"
            >
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-[#1C2431] bg-[#0D1117] px-4">
          <button className="lg:hidden" onClick={() => setMenuOpen(true)} aria-label="Open menu">
            <Menu className="h-5 w-5 text-slate-400" />
          </button>
          <span className="text-xs text-slate-500 lg:invisible">Nexora Super Admin</span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setChangingPassword(true)}
              aria-label="Change password"
              title="Change password"
              className="flex h-9 w-9 items-center justify-center rounded-md text-slate-400 hover:bg-[#121821] hover:text-slate-200"
            >
              <KeyRound className="h-4 w-4" />
            </button>
            <ThemeToggle />
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">{children}</main>
      </div>
      {changingPassword && (
        <ChangePasswordModal onClose={() => setChangingPassword(false)} submit={changeSuperAdminPassword} />
      )}
    </div>
  );
}
