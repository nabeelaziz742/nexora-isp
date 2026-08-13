"use client";

import { useEffect, useRef, useState } from "react";
import {
  usePathname,
  useRouter,
} from "next/navigation";
import {
  Bell,
  ChevronDown,
  LogOut,
  Menu,
  Search,
  Signal,
} from "lucide-react";

import { clearAuthTokens } from "@/services/auth-storage";

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

const pageTitles: Record<string, string> = {
  "/command-center": "Command Center",
  "/customers": "Customers",
  "/network": "Network Operations",
  "/support": "Support & Incidents",
  "/field-operations": "Field Operations",
  "/billing": "Billing & Payments",
  "/inventory": "Inventory",
  "/intelligence": "AI ISP Copilot",
  "/intelligence/revenue": "Revenue Intelligence",
  "/reports": "Reports",
  "/settings": "Settings",
  "/notifications": "Notification Operations",
};

function resolvePageTitle(pathname: string) {
  if (pathname === "/customers/new") {
    return "Customer Activation";
  }

  if (pathname.startsWith("/customers/")) {
    return "Customer 360";
  }

  const exactTitle = pageTitles[pathname];

  if (exactTitle) {
    return exactTitle;
  }

  const matchedRoute = Object.keys(pageTitles)
    .sort((a, b) => b.length - a.length)
    .find((route) =>
      pathname.startsWith(`${route}/`),
    );

  return matchedRoute
    ? pageTitles[matchedRoute]
    : "NEXORA ISP";
}

function getInitials(
  firstName?: string,
  lastName?: string,
) {
  const firstInitial = firstName?.charAt(0) ?? "";
  const lastInitial = lastName?.charAt(0) ?? "";

  return (
    `${firstInitial}${lastInitial}`.toUpperCase() ||
    "NX"
  );
}

export default function TopCommandBar({
  onMenuClick,
}: TopCommandBarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const profileRef = useRef<HTMLDivElement>(null);

  const [profileOpen, setProfileOpen] =
    useState(false);

  const [user, setUser] =
    useState<StoredUser | null>(null);

  const [organization, setOrganization] =
    useState<StoredOrganization | null>(null);

  const [role, setRole] = useState("");

  const pageTitle = resolvePageTitle(pathname);

  useEffect(() => {
    try {
      const storedUser =
        window.localStorage.getItem("nexora_user");

      const storedOrganization =
        window.localStorage.getItem(
          "nexora_organization",
        );

      const storedRole =
        window.localStorage.getItem("nexora_role");

      if (storedUser) {
        setUser(JSON.parse(storedUser));
      }

      if (storedOrganization) {
        setOrganization(
          JSON.parse(storedOrganization),
        );
      }

      setRole(storedRole ?? "");
    } catch (error) {
      console.error(
        "Failed to load stored session profile:",
        error,
      );
    }
  }, []);

  useEffect(() => {
    function handleOutsideClick(event: MouseEvent) {
      if (
        profileRef.current &&
        !profileRef.current.contains(
          event.target as Node,
        )
      ) {
        setProfileOpen(false);
      }
    }

    document.addEventListener(
      "mousedown",
      handleOutsideClick,
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleOutsideClick,
      );
    };
  }, []);

  function handleLogout() {
    clearAuthTokens();

    window.localStorage.removeItem("nexora_user");
    window.localStorage.removeItem(
      "nexora_organization",
    );
    window.localStorage.removeItem("nexora_role");

    setProfileOpen(false);

    router.replace("/");
  }

  const fullName = [
    user?.first_name,
    user?.last_name,
  ]
    .filter(Boolean)
    .join(" ");

  const initials = getInitials(
    user?.first_name,
    user?.last_name,
  );

  return (
    <header className="flex h-16 shrink-0 items-center border-b border-[#202938] bg-[#0D1117] px-3 sm:px-4 lg:px-5">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="Open navigation"
          className="flex h-9 w-9 shrink-0 items-center justify-center text-slate-400 transition hover:bg-[#121821] hover:text-slate-100 lg:hidden"
        >
          <Menu className="h-4 w-4" />
        </button>

        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-100">
            {pageTitle}
          </p>

          <p className="hidden text-[10px] uppercase tracking-[0.08em] text-slate-600 sm:block">
            NEXORA ISP
          </p>
        </div>
      </div>

      <div className="hidden min-w-0 flex-1 justify-center xl:flex">
        <button
          type="button"
          className="flex h-9 w-full max-w-xl items-center gap-3 border border-[#202938] bg-[#070A0F] px-3 text-left transition hover:border-[#2B3545]"
        >
          <Search className="h-3.5 w-3.5 shrink-0 text-slate-600" />

          <span className="min-w-0 flex-1 truncate text-xs text-slate-600">
            Search customers, nodes, tickets...
          </span>

          <span className="border border-[#202938] bg-[#121821] px-1.5 py-0.5 font-mono text-[9px] text-slate-600">
            ⌘ K
          </span>
        </button>
      </div>

      <div className="flex min-w-0 flex-1 items-center justify-end gap-1 sm:gap-2">
        <button
          type="button"
          aria-label="Global search"
          className="flex h-9 w-9 items-center justify-center text-slate-500 transition hover:bg-[#121821] hover:text-slate-200 xl:hidden"
        >
          <Search className="h-4 w-4" />
        </button>

        <div className="hidden items-center gap-2 border-r border-[#202938] pr-3 lg:flex">
          <Signal className="h-3.5 w-3.5 text-emerald-400" />

          <div>
            <p className="text-[10px] text-slate-600">
              Network Status
            </p>

            <p className="text-[11px] font-medium text-emerald-400">
              Operational
            </p>
          </div>
        </div>

        <button
          type="button"
          aria-label="Notifications"
          className="relative flex h-9 w-9 items-center justify-center text-slate-500 transition hover:bg-[#121821] hover:text-slate-200"
        >
          <Bell className="h-4 w-4" />

          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-red-500" />
        </button>

        <div
          ref={profileRef}
          className="relative"
        >
          <button
            type="button"
            onClick={() =>
              setProfileOpen((current) => !current)
            }
            aria-expanded={profileOpen}
            className="flex min-w-0 items-center gap-2 px-2 py-1.5 transition hover:bg-[#121821]"
          >
            <div className="hidden min-w-0 text-right sm:block">
              <p className="max-w-28 truncate text-[11px] font-medium text-slate-200">
                {organization?.name ?? "NEXORA ISP"}
              </p>

              <p className="max-w-28 truncate text-[10px] text-slate-600">
                {fullName || user?.email || "User"}
                {role
                  ? ` · ${role.toLowerCase()}`
                  : ""}
              </p>
            </div>

            <div className="flex h-8 w-8 shrink-0 items-center justify-center bg-blue-600 text-[11px] font-semibold text-white">
              {initials}
            </div>

            <ChevronDown
              className={`hidden h-3.5 w-3.5 text-slate-600 transition-transform sm:block ${
                profileOpen ? "rotate-180" : ""
              }`}
            />
          </button>

          {profileOpen && (
            <div className="absolute right-0 top-full z-50 mt-2 w-56 border border-[#202938] bg-[#0D1117] shadow-2xl">
              <div className="border-b border-[#202938] px-4 py-3">
                <p className="truncate text-xs font-medium text-slate-200">
                  {fullName || "NEXORA User"}
                </p>

                <p className="mt-1 truncate text-[10px] text-slate-600">
                  {user?.email}
                </p>
              </div>

              <button
                type="button"
                onClick={handleLogout}
                className="flex w-full items-center gap-2 px-4 py-3 text-left text-xs text-red-400 transition hover:bg-red-500/10"
              >
                <LogOut className="h-4 w-4" />

                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}