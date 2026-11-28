"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BookOpen,
  Building2,
  Handshake,
  Home,
  Info,
  KeyRound,
  Landmark,
  Loader2,
  LogOut,
  MapPin,
  Menu,
  MessageSquare,
  MessageSquareText,
  MessageSquareWarning,
  Package,
  Receipt,
  UserCog,
  Users,
  Wallet,
  X,
  type LucideIcon,
} from "lucide-react";

import { DealerMeContext, canSeeCustomers } from "@/components/dealers/DealerMeContext";
import ThemeToggle from "@/components/layout/ThemeToggle";
import ChangePasswordModal from "@/components/ui/ChangePasswordModal";
import { changePassword, getCurrentSession } from "@/services/auth.service";
import { clearAuthTokens, getAccessToken, getRefreshToken } from "@/services/auth-storage";
import { dealerPortalService, type DealerMe } from "@/services/dealer-portal.service";
import { getJumpBanner, popJumpSession, signOutAllStackedSessions } from "@/services/jump-session";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  show: (me: DealerMe) => boolean;
}

// Left side menu in exact required order; later-phase items are added when built.
const NAV: NavItem[] = [
  { href: "/dealer", label: "Home", icon: Home, show: () => true },
  {
    href: "/dealer/customers",
    label: "Customers",
    icon: Users,
    show: (me) =>
      canSeeCustomers(me.rights) ||
      me.rights.can_request_customers ||
      me.rights.can_import_customers ||
      me.rights.can_export_customers ||
      me.rights.can_edit_customers ||
      me.rights.can_deactivate_customers ||
      me.rights.can_view_ledger,
  },
  {
    href: "/dealer/collections",
    label: "Collection",
    icon: Wallet,
    show: (me) => me.rights.can_view_collections || me.rights.can_view_all_collections,
  },
  {
    href: "/dealer/complaints",
    label: "Complaint",
    icon: MessageSquareWarning,
    show: (me) => me.is_dealer || me.rights.can_manage_complaints,
  },
  {
    href: "/dealer/employees",
    label: "Employees",
    icon: UserCog,
    show: (me) => me.is_dealer || me.rights.can_manage_employees,
  },
  {
    href: "/dealer/packages",
    label: "Packages",
    icon: Package,
    show: (me) => me.rights.can_view_packages,
  },
  {
    href: "/dealer/areas",
    label: "Areas",
    icon: MapPin,
    show: (me) => me.rights.can_view_areas || me.rights.can_manage_areas,
  },
  {
    href: "/dealer/sms-templates",
    label: "SMS Templates",
    icon: MessageSquareText,
    show: (me) => me.is_dealer || me.rights.can_manage_sms_templates,
  },
  {
    href: "/dealer/sms-log",
    label: "SMS Log",
    icon: MessageSquare,
    show: (me) =>
      me.is_dealer || me.rights.can_view_sms_log || me.rights.can_send_sms || me.rights.can_broadcast_sms,
  },
  {
    href: "/dealer/accounts",
    label: "Accounts",
    icon: Landmark,
    show: (me) => me.is_dealer || me.rights.can_view_accounts,
  },
  {
    href: "/dealer/journal",
    label: "Journal",
    icon: BookOpen,
    show: (me) => me.is_dealer || me.rights.can_view_journal || me.rights.can_add_journal_entries,
  },
  { href: "/dealer/expenses", label: "Expenses", icon: Receipt, show: () => true },
  { href: "/dealer/company-info", label: "Company Info", icon: Building2, show: () => true },
  { href: "/dealer/about", label: "About", icon: Info, show: () => true },
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [returningHome, setReturningHome] = useState(false);
  const [jumpBanner, setJumpBanner] = useState<{ viewerLabel: string; returnTo: string } | null>(null);

  useEffect(() => {
    setJumpBanner(getJumpBanner());
  }, [pathname]);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

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

  const visibleNav = NAV.filter((item) => item.show(me));
  const isJumped = Boolean(jumpBanner || me.impersonated_by);
  const viewingText = jumpBanner?.viewerLabel || `Viewing as ${me.name}`;

  async function handleBackToHome() {
    setReturningHome(true);
    const returnTo = await popJumpSession();
    window.location.href = returnTo;
  }

  const isNavActive = (href: string) => {
    if (href === "/dealer") return pathname === "/dealer";
    if (href === "/dealer/customers" && pathname === "/dealer/requests") return true;
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <div className="flex min-h-screen bg-[#070A0F] text-slate-100">
      {mobileMenuOpen && (
        <div
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-60 shrink-0 flex-col border-r border-[#1C2431] bg-[#0D1117] transition-transform duration-200 lg:static lg:z-auto lg:translate-x-0 ${
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-14 items-center justify-between border-b border-[#1C2431] px-4">
          <div className="flex min-w-0 items-center gap-2.5">
            <Handshake className="h-5 w-5 shrink-0 text-blue-400" />
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-white">Dealer Portal</p>
              <p className="truncate text-[11px] text-slate-500">
                {orgName}
                {!me.is_dealer && ` · ${me.name}`}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close menu"
            className="rounded-md p-1 text-slate-400 hover:bg-[#121821] hover:text-white lg:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-2.5 py-3">
          {visibleNav.map((item) => {
            const Icon = item.icon;
            const active = isNavActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition ${
                  active
                    ? "bg-blue-600/15 font-semibold text-white ring-1 ring-inset ring-blue-500/30"
                    : "text-slate-400 hover:bg-[#121821] hover:text-slate-200"
                }`}
              >
                <Icon className={`h-4 w-4 shrink-0 ${active ? "text-blue-400" : "text-slate-500"}`} />
                <span className="truncate">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-[#1C2431] p-3 text-xs text-slate-500">
          <p className="truncate font-medium text-slate-300">{me.name}</p>
          <p className="truncate text-[11px] text-slate-500">{me.is_dealer ? "Dealer account" : "Employee"}</p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {isJumped && (
          <div className="sticky top-0 z-40 flex flex-wrap items-center justify-between gap-2 border-b border-amber-500/40 bg-amber-500/15 px-4 py-2 text-xs text-amber-100">
            <span className="font-medium">{viewingText}</span>
            <button
              type="button"
              onClick={() => void handleBackToHome()}
              disabled={returningHome}
              className="inline-flex h-7 items-center gap-1.5 rounded-md bg-amber-500 px-3 text-xs font-semibold text-slate-950 hover:bg-amber-400 disabled:opacity-60"
            >
              {returningHome && <Loader2 className="h-3 w-3 animate-spin" />}
              Back to Home
            </button>
          </div>
        )}
        <header className="sticky top-0 z-30 border-b border-[#1C2431] bg-[#0D1117]">
          <div className="flex h-14 items-center justify-between gap-2 px-4">
            <div className="flex min-w-0 items-center gap-2">
              <button
                type="button"
                onClick={() => setMobileMenuOpen(true)}
                aria-label="Open menu"
                className="flex h-9 w-9 items-center justify-center rounded-md border border-[#263142] text-slate-300 hover:bg-[#121821] lg:hidden"
              >
                <Menu className="h-4 w-4" />
              </button>
              <div className="min-w-0 lg:hidden">
                <p className="truncate text-sm font-bold text-white">Dealer Portal</p>
                <p className="truncate text-[11px] text-slate-500">{orgName}</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <ThemeToggle />
              {!isJumped && (
                <button
                  onClick={() => setChangingPassword(true)}
                  aria-label="Change password"
                  title="Change password"
                  className="flex h-9 items-center gap-1.5 rounded-md px-2 text-xs text-slate-400 hover:bg-[#121821] hover:text-slate-200"
                >
                  <KeyRound className="h-4 w-4" />
                  <span className="hidden min-[400px]:inline">Change Password</span>
                </button>
              )}
              <button
                onClick={() => {
                  void signOutAllStackedSessions().finally(() => {
                    router.replace("/");
                  });
                }}
                className="flex h-9 items-center gap-1.5 rounded-md px-2 text-xs text-slate-400 hover:bg-[#121821] hover:text-slate-200"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl min-w-0 flex-1 px-4 py-5">
          <DealerMeContext.Provider value={me}>
            {children}
          </DealerMeContext.Provider>
        </main>
      </div>

      {changingPassword && (
        <ChangePasswordModal onClose={() => setChangingPassword(false)} submit={changePassword} />
      )}
    </div>
  );
}
