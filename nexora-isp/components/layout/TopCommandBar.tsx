"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  Bell,
  ChevronDown,
  ChevronRight,
  LogOut,
  Menu,
  Search,
  ShieldCheck,
} from "lucide-react";

import { clearAuthTokens } from "@/services/auth-storage";
import CommandPalette from "@/components/layout/CommandPalette";

interface TopCommandBarProps {
  onMenuClick?: () => void;
}

interface StoredUser {
  first_name?: string;
  last_name?: string;
  email?: string;
}

interface StoredOrganization {
  name?: string;
  code?: string;
}

interface BreadcrumbItem {
  label: string;
  href?: string;
}

function resolveBreadcrumbs(pathname: string): BreadcrumbItem[] {
  // Command
  if (pathname === "/command-center") {
    return [{ label: "Command Center" }];
  }

  // Operations - Customers
  if (pathname === "/customers") {
    return [{ label: "Operations" }, { label: "Customers" }];
  }
  if (pathname === "/customers/new") {
    return [
      { label: "Operations" },
      { label: "Customers", href: "/customers" },
      { label: "New Customer Activation" },
    ];
  }
  if (pathname.startsWith("/customers/")) {
    return [
      { label: "Operations" },
      { label: "Customers", href: "/customers" },
      { label: "Subscriber 360°" },
    ];
  }

  // Operations - Inquiries & Leads
  if (pathname === "/inquiries") {
    return [{ label: "Operations" }, { label: "Inquiries & Leads" }];
  }
  if (pathname.startsWith("/inquiries/")) {
    return [
      { label: "Operations" },
      { label: "Inquiries", href: "/inquiries" },
      { label: "Lead Feasibility" },
    ];
  }

  // Operations - Operators & Recovery
  if (pathname === "/operators") {
    return [{ label: "Operations" }, { label: "Operators & Recovery" }];
  }

  // Operations - Dealers
  if (pathname === "/dealers") {
    return [{ label: "Operations" }, { label: "Dealers & Sub-ISPs" }];
  }
  if (pathname.startsWith("/dealers/")) {
    return [
      { label: "Operations" },
      { label: "Dealers", href: "/dealers" },
      { label: "Dealer 360°" },
    ];
  }

  // Operations - Packages & Areas
  if (pathname === "/packages") {
    return [{ label: "Operations" }, { label: "Packages & Plans" }];
  }
  if (pathname === "/areas") {
    return [{ label: "Operations" }, { label: "Areas & Hierarchy" }];
  }

  // Operations - Network & Support & Field Ops
  if (pathname === "/network") {
    return [{ label: "Operations" }, { label: "Network Operations & POPs" }];
  }
  if (pathname === "/support") {
    return [{ label: "Operations" }, { label: "Support & Incidents" }];
  }
  if (pathname === "/field-operations") {
    return [{ label: "Operations" }, { label: "Field Operations" }];
  }

  // Finance - Billing & Invoices & Collections
  if (pathname === "/billing") {
    return [{ label: "Finance" }, { label: "Billing Overview" }];
  }
  if (pathname === "/invoices") {
    return [{ label: "Finance" }, { label: "Invoices Management" }];
  }
  if (pathname === "/collections") {
    return [{ label: "Finance" }, { label: "Collections & Receipts" }];
  }
  if (pathname === "/defaulters") {
    return [{ label: "Finance" }, { label: "Defaulter Accounts" }];
  }
  if (pathname === "/allocations") {
    return [{ label: "Finance" }, { label: "Recovery Allocations" }];
  }
  if (pathname === "/promises") {
    return [{ label: "Finance" }, { label: "Promises to Pay (PTP)" }];
  }
  if (pathname === "/suspensions") {
    return [{ label: "Finance" }, { label: "Suspensions & Policy" }];
  }
  if (pathname === "/accounting") {
    return [{ label: "Finance" }, { label: "Accounting & General Ledger" }];
  }
  if (pathname === "/expenses") {
    return [{ label: "Finance" }, { label: "Operating Expenses" }];
  }

  // Resources & POS
  if (pathname === "/inventory") {
    return [{ label: "Resources" }, { label: "Inventory Assets" }];
  }
  if (pathname === "/pos") {
    return [{ label: "Resources" }, { label: "POS Terminal" }];
  }
  if (pathname === "/pos/sales") {
    return [
      { label: "Resources" },
      { label: "POS Terminal", href: "/pos" },
      { label: "Sales Register" },
    ];
  }

  // Communications
  if (pathname === "/communications") {
    return [{ label: "Communications" }, { label: "Communication Center" }];
  }
  if (pathname === "/communications/templates/create") {
    return [
      { label: "Communications" },
      { label: "Templates", href: "/communications/templates" },
      { label: "Create Template" },
    ];
  }
  if (pathname.startsWith("/communications/templates/")) {
    return [
      { label: "Communications" },
      { label: "Templates", href: "/communications/templates" },
      { label: "Edit Template" },
    ];
  }
  if (pathname === "/communications/templates") {
    return [
      { label: "Communications" },
      { label: "Templates" },
    ];
  }
  if (pathname === "/communications/automations/create") {
    return [
      { label: "Communications" },
      { label: "Automations", href: "/communications/automations" },
      { label: "Create Automation" },
    ];
  }
  if (pathname.startsWith("/communications/automations/")) {
    return [
      { label: "Communications" },
      { label: "Automations", href: "/communications/automations" },
      { label: "Edit Automation" },
    ];
  }
  if (pathname === "/communications/automations") {
    return [
      { label: "Communications" },
      { label: "Automations" },
    ];
  }
  if (pathname === "/communications/broadcast") {
    return [
      { label: "Communications" },
      { label: "Broadcast Dispatch" },
    ];
  }
  if (pathname === "/communications/logs") {
    return [
      { label: "Communications" },
      { label: "Delivery Logs" },
    ];
  }
  if (pathname === "/communications/providers") {
    return [
      { label: "Communications" },
      { label: "Gateway Providers" },
    ];
  }
  if (pathname === "/communications/schedules") {
    return [
      { label: "Communications" },
      { label: "Scheduled Triggers" },
    ];
  }
  if (pathname === "/communications/settings") {
    return [
      { label: "Communications" },
      { label: "Channel Settings" },
    ];
  }

  // Intelligence
  if (pathname === "/intelligence") {
    return [{ label: "Intelligence" }, { label: "AI Copilot" }];
  }
  if (pathname === "/intelligence/revenue") {
    return [
      { label: "Intelligence", href: "/intelligence" },
      { label: "Revenue Intelligence" },
    ];
  }
  if (pathname === "/reports") {
    return [{ label: "Intelligence" }, { label: "Reports Center" }];
  }

  // System
  if (pathname === "/notifications") {
    return [{ label: "System" }, { label: "Notification Operations" }];
  }
  if (pathname === "/staff") {
    return [{ label: "System" }, { label: "Staff Management" }];
  }
  if (pathname === "/staff/add") {
    return [
      { label: "System" },
      { label: "Staff Management", href: "/staff" },
      { label: "Add Staff Member" },
    ];
  }
  if (pathname === "/audit-logs") {
    return [{ label: "System" }, { label: "Security Audit Trail" }];
  }
  if (pathname === "/settings") {
    return [{ label: "System" }, { label: "ISP Settings" }];
  }

  return [{ label: "NEXORA ISP" }];
}

function getInitials(firstName?: string, lastName?: string) {
  const initials = `${firstName?.charAt(0) ?? ""}${lastName?.charAt(0) ?? ""}`;
  return initials.toUpperCase() || "NX";
}

export default function TopCommandBar({ onMenuClick }: TopCommandBarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const profileRef = useRef<HTMLDivElement>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [user, setUser] = useState<StoredUser | null>(null);
  const [organization, setOrganization] = useState<StoredOrganization | null>(null);
  const [role, setRole] = useState("");
  const [shortcutKey, setShortcutKey] = useState("Ctrl+K");

  const breadcrumbs = resolveBreadcrumbs(pathname);

  // Platform detection for Command key (Cmd+K on Mac, Ctrl+K on Windows/Linux)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const isMac =
        navigator.platform?.toUpperCase().indexOf("MAC") >= 0 ||
        navigator.userAgent?.toUpperCase().indexOf("MAC") >= 0;
      setShortcutKey(isMac ? "Cmd+K" : "Ctrl+K");
    }
  }, []);

  // Global Keyboard Listener for Command Palette
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    try {
      const storedUser = window.localStorage.getItem("nexora_user");
      const storedOrganization = window.localStorage.getItem("nexora_organization");
      const storedRole = window.localStorage.getItem("nexora_role");

      if (storedUser) setUser(JSON.parse(storedUser));
      if (storedOrganization) setOrganization(JSON.parse(storedOrganization));
      setRole(storedRole ?? "");
    } catch {
      setUser(null);
      setOrganization(null);
      setRole("");
    }
  }, []);

  useEffect(() => {
    function handleOutsideClick(event: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setProfileOpen(false);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  function handleLogout() {
    clearAuthTokens();
    window.localStorage.removeItem("nexora_user");
    window.localStorage.removeItem("nexora_organization");
    window.localStorage.removeItem("nexora_role");
    setProfileOpen(false);
    router.replace("/");
  }

  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(" ");
  const initials = getInitials(user?.first_name, user?.last_name);

  return (
    <>
      <header className="flex h-16 shrink-0 items-center justify-between border-b border-[#202938] bg-[#0D1117] px-4 lg:px-6">
        {/* Left side: Mobile menu toggle + Breadcrumbs */}
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={onMenuClick}
            aria-label="Toggle navigation menu"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-slate-400 transition hover:bg-[#121821] hover:text-slate-100 lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Dynamic Breadcrumbs */}
          <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs">
            {breadcrumbs.map((crumb, index) => {
              const isLast = index === breadcrumbs.length - 1;

              return (
                <div key={index} className="flex items-center gap-1.5">
                  {index > 0 && (
                    <ChevronRight className="h-3 w-3 shrink-0 text-slate-600" />
                  )}
                  {isLast ? (
                    <span className="font-semibold text-slate-100 truncate max-w-[200px] sm:max-w-xs">
                      {crumb.label}
                    </span>
                  ) : crumb.href ? (
                    <button
                      type="button"
                      onClick={() => crumb.href && router.push(crumb.href)}
                      className="text-slate-500 hover:text-slate-300 transition-colors"
                    >
                      {crumb.label}
                    </button>
                  ) : (
                    <span className="text-slate-500">{crumb.label}</span>
                  )}
                </div>
              );
            })}
          </nav>
        </div>

        {/* Middle: Interactive Quick search bar that opens Command Palette */}
        <div className="hidden min-w-0 max-w-md flex-1 px-4 xl:block">
          <button
            type="button"
            onClick={() => setCommandPaletteOpen(true)}
            aria-label="Open Command Palette"
            className="group relative flex h-9 w-full items-center justify-between rounded-lg border border-[#202938] bg-[#070A0F] px-3 text-xs text-slate-500 transition-all hover:border-blue-500/50 hover:bg-[#0A0E15]"
          >
            <div className="flex items-center gap-2">
              <Search className="h-3.5 w-3.5 text-slate-500 group-hover:text-blue-400 transition-colors" />
              <span className="group-hover:text-slate-300 transition-colors">
                Search commands, subscribers, invoices...
              </span>
            </div>
            <kbd className="rounded border border-[#202938] bg-[#121821] px-1.5 py-0.5 font-mono text-[10px] text-slate-400 group-hover:border-slate-700">
              {shortcutKey}
            </kbd>
          </button>
        </div>

        {/* Right side: Notifications + Search on mobile + User Profile */}
        <div className="flex items-center gap-2">
          {/* Mobile search button */}
          <button
            type="button"
            onClick={() => setCommandPaletteOpen(true)}
            aria-label="Open Command Search"
            className="flex h-9 w-9 items-center justify-center rounded-md text-slate-400 transition hover:bg-[#121821] hover:text-slate-200 xl:hidden"
          >
            <Search className="h-4 w-4" />
          </button>

          <button
            type="button"
            onClick={() => router.push("/notifications")}
            aria-label="View notifications"
            className="relative flex h-9 w-9 items-center justify-center rounded-md text-slate-400 transition hover:bg-[#121821] hover:text-slate-200"
          >
            <Bell className="h-4 w-4" />
          </button>

          {/* User Profile dropdown */}
          <div ref={profileRef} className="relative">
            <button
              type="button"
              onClick={() => setProfileOpen((prev) => !prev)}
              aria-expanded={profileOpen}
              aria-label="User account menu"
              className="flex items-center gap-2.5 rounded-lg border border-transparent p-1.5 transition hover:border-[#202938] hover:bg-[#121821]"
            >
              <div className="hidden text-right sm:block">
                <p className="truncate text-xs font-semibold text-slate-200 max-w-[130px]">
                  {organization?.name ?? "NEXORA Organization"}
                </p>
                <div className="flex items-center justify-end gap-1 text-[10px] text-slate-500">
                  <span className="truncate max-w-[110px]">
                    {fullName || user?.email || "User"}
                  </span>
                  <span className="rounded-xs bg-blue-500/15 px-1 py-0.2 font-mono text-[8px] font-bold text-blue-400">
                    {role || "STAFF"}
                  </span>
                </div>
              </div>

              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-blue-600 text-xs font-bold text-white shadow-xs">
                {initials}
              </div>

              <ChevronDown
                className={`hidden h-3.5 w-3.5 text-slate-500 transition-transform sm:block ${
                  profileOpen ? "rotate-180 text-slate-300" : ""
                }`}
              />
            </button>

            {profileOpen && (
              <div className="absolute right-0 top-full z-50 mt-1.5 w-60 rounded-lg border border-[#202938] bg-[#0D1117] p-1.5 shadow-2xl shadow-black/60">
                <div className="border-b border-[#202938] px-3 py-2.5">
                  <p className="text-xs font-semibold text-slate-100 truncate">
                    {fullName || "NEXORA Operator"}
                  </p>
                  <p className="text-[11px] text-slate-500 truncate mt-0.5">
                    {user?.email}
                  </p>
                  <div className="mt-2 flex items-center gap-1.5 text-[10px] text-emerald-400">
                    <ShieldCheck className="h-3 w-3 shrink-0" />
                    <span>Verified Tenant Session</span>
                  </div>
                </div>

                <div className="p-1">
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-xs font-medium text-red-400 transition hover:bg-red-500/10 hover:text-red-300"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                    <span>Sign Out of Session</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Global Interactive Command Palette */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
      />
    </>
  );
}
