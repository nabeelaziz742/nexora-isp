"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ChevronDown,
  RadioTower,
  Signal,
  Wrench,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getNavigationForRole, NavigationRole } from "@/config/navigation";

interface AppSidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export default function AppSidebar({
  isOpen = false,
  onClose,
}: AppSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const [role, setRole] = useState<string | null>(null);
  const [roleLoaded, setRoleLoaded] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});

  useEffect(() => {
    try {
      const storedRole = window.localStorage.getItem("nexora_role");
      setRole(storedRole);
    } catch {
      setRole(null);
    } finally {
      setRoleLoaded(true);
    }
  }, []);

  const isTechnician = role === "TECHNICIAN";

  const roleNavigation = useMemo(() => {
    return getNavigationForRole(role as NavigationRole | null);
  }, [role]);

  const navigationHrefs = useMemo(() => {
    return roleNavigation.flatMap((group) => group.items.map((item) => item.href));
  }, [roleNavigation]);

  // Enforce technician route boundary
  useEffect(() => {
    if (!roleLoaded || !isTechnician) {
      return;
    }

    if (
      pathname !== "/field-operations" &&
      !pathname.startsWith("/field-operations/")
    ) {
      router.replace("/field-operations");
    }
  }, [isTechnician, pathname, roleLoaded, router]);

  function isRouteActive(href: string) {
    if (href === "/command-center") {
      return pathname === "/command-center";
    }

    if (pathname === href) return true;

    const matchingRoutes = navigationHrefs
      .filter(
        (navigationHref) =>
          pathname === navigationHref ||
          pathname.startsWith(`${navigationHref}/`),
      )
      .sort((a, b) => b.length - a.length);

    return matchingRoutes[0] === href;
  }

  function toggleGroup(label: string) {
    setCollapsedGroups((prev) => ({
      ...prev,
      [label]: !prev[label],
    }));
  }

  if (!roleLoaded) {
    return (
      <aside className="fixed inset-y-0 left-0 z-40 w-[260px] border-r border-[#202938] bg-[#0D1117] lg:static">
        <div className="h-16 border-b border-[#202938]" />
      </aside>
    );
  }

  return (
    <>
      {/* Mobile backdrop overlay */}
      {isOpen && (
        <div
          onClick={onClose}
          aria-hidden="true"
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-xs transition-opacity lg:hidden"
        />
      )}

      <aside
        className={`
          fixed inset-y-0 left-0 z-50 flex w-[260px] shrink-0 flex-col
          border-r border-[#202938] bg-[#0D1117] shadow-2xl shadow-black/40
          transition-transform duration-200 ease-out
          lg:static lg:z-auto lg:translate-x-0 lg:shadow-none
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        {/* Top Brand Header */}
        <div className="flex h-16 shrink-0 items-center justify-between border-b border-[#202938] px-4">
          <Link
            href={isTechnician ? "/field-operations" : "/command-center"}
            onClick={onClose}
            className="flex min-w-0 items-center gap-2.5 transition hover:opacity-90"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-blue-600 shadow-sm shadow-blue-500/20">
              {isTechnician ? (
                <Wrench className="h-4 w-4 text-white" />
              ) : (
                <RadioTower className="h-4 w-4 text-white" />
              )}
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <p className="truncate text-xs font-bold tracking-[0.12em] text-slate-100">
                  NEXORA
                </p>
                <span className="rounded-xs bg-blue-500/20 px-1 py-0.2 text-[8px] font-bold text-blue-400">
                  {role ?? "OPERATOR"}
                </span>
              </div>

              <p className="truncate text-[9px] uppercase tracking-[0.06em] text-slate-500">
                {isTechnician ? "Field Technician OS" : "ISP Command Portal"}
              </p>
            </div>
          </Link>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation sidebar"
            className="flex h-7 w-7 items-center justify-center rounded-md text-slate-500 transition hover:bg-[#121821] hover:text-slate-200 lg:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Navigation Item Tree */}
        <nav className="nexora-scrollbar min-h-0 flex-1 overflow-y-auto px-2.5 py-3">
          {isTechnician ? (
            <div>
              <p className="px-2.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                Assigned Work
              </p>

              <div className="mt-1.5">
                <Link
                  href="/field-operations"
                  onClick={onClose}
                  className={`
                    relative flex h-9 items-center gap-2.5 rounded-md px-2.5
                    text-xs font-medium transition-all
                    ${
                      isRouteActive("/field-operations")
                        ? "bg-blue-600/15 text-blue-400 shadow-xs"
                        : "text-slate-400 hover:bg-[#121821] hover:text-slate-200"
                    }
                  `}
                >
                  {isRouteActive("/field-operations") && (
                    <span className="absolute left-0 h-4 w-0.5 rounded-r bg-blue-500" />
                  )}

                  <Wrench className="h-4 w-4 shrink-0 text-blue-400" />
                  <span className="min-w-0 flex-1 truncate">My Field Jobs</span>
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                </Link>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {roleNavigation.map((group) => {
                const isCollapsed = !!collapsedGroups[group.label];

                return (
                  <div key={group.label}>
                    <button
                      type="button"
                      onClick={() => toggleGroup(group.label)}
                      className="flex w-full items-center justify-between px-2.5 py-1 text-left text-[9px] font-semibold uppercase tracking-[0.14em] text-slate-500 hover:text-slate-400"
                    >
                      <span>{group.label}</span>
                      <ChevronDown
                        className={`h-3 w-3 transition-transform duration-150 ${
                          isCollapsed ? "-rotate-90 text-slate-600" : "text-slate-500"
                        }`}
                      />
                    </button>

                    {!isCollapsed && (
                      <div className="mt-1 space-y-0.5">
                        {group.items.map((item) => {
                          const active = isRouteActive(item.href);
                          const Icon = item.icon;

                          return (
                            <Link
                              key={item.href}
                              href={item.href}
                              onClick={onClose}
                              className={`
                                relative flex h-8.5 items-center gap-2.5 rounded-md px-2.5
                                text-xs font-medium transition-all
                                ${
                                  active
                                    ? "bg-blue-600/15 text-blue-400"
                                    : "text-slate-400 hover:bg-[#121821] hover:text-slate-200"
                                }
                              `}
                            >
                              {active && (
                                <span className="absolute left-0 h-3.5 w-0.5 rounded-r bg-blue-500" />
                              )}

                              <Icon
                                className={`h-4 w-4 shrink-0 transition-colors ${
                                  active ? "text-blue-400" : "text-slate-500"
                                }`}
                              />

                              <span className="min-w-0 flex-1 truncate">
                                {item.title}
                              </span>

                              {active && (
                                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500 shadow-xs shadow-blue-400" />
                              )}
                            </Link>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </nav>

        {/* Footer telemetry indicator */}
        <div className="shrink-0 border-t border-[#202938] p-2.5">
          <div className="flex items-center gap-2.5 rounded-md border border-[#202938]/60 bg-[#121821] p-2.5">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-sm bg-emerald-500/10">
              {isTechnician ? (
                <Wrench className="h-3 w-3 text-amber-400" />
              ) : (
                <Signal className="h-3 w-3 text-emerald-400" />
              )}
            </div>

            <div className="min-w-0">
              <p className="truncate text-[10px] font-medium text-slate-200">
                {isTechnician ? "Technician Node Active" : "Operational Core Live"}
              </p>
              <p className="truncate text-[9px] text-slate-500">
                {isTechnician ? "Restricted work queue" : "All services telemetry OK"}
              </p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}