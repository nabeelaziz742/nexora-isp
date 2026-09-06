"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
  RadioTower,
  Signal,
  Wrench,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getNavigationForRole, NavigationRole } from "@/config/navigation";

interface AppSidebarProps {
  isOpen?: boolean; // Mobile drawer open
  onClose?: () => void; // Mobile drawer close
  isCollapsed?: boolean; // Desktop collapsed
  onToggleCollapse?: () => void; // Toggle desktop collapsed
}

export default function AppSidebar({
  isOpen = false,
  onClose,
  isCollapsed = false,
  onToggleCollapse,
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

  const handleNavClick = () => {
    if (onClose) {
      onClose();
    }
  };

  if (!roleLoaded) {
    return (
      <aside
        className={`fixed inset-y-0 left-0 z-40 border-r border-[#202938] bg-[#0D1117] transition-[width] duration-200 ease-in-out lg:static ${
          isCollapsed ? "w-[64px]" : "w-[236px]"
        }`}
      >
        <div className="h-14 border-b border-[#202938]" />
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
          fixed inset-y-0 left-0 z-50 flex shrink-0 flex-col
          border-r border-[#202938] bg-[#0D1117] shadow-2xl shadow-black/40
          transition-[width,transform] duration-200 ease-in-out
          lg:static lg:z-auto lg:translate-x-0 lg:shadow-none
          ${isOpen ? "translate-x-0 w-[240px]" : "-translate-x-full lg:translate-x-0"}
          ${isCollapsed ? "lg:w-[64px]" : "lg:w-[236px]"}
        `}
      >
        {/* Top Brand Header */}
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-[#202938] px-3">
          <Link
            href={isTechnician ? "/field-operations" : "/command-center"}
            onClick={handleNavClick}
            className={`flex min-w-0 items-center gap-2.5 transition hover:opacity-90 ${
              isCollapsed ? "lg:justify-center lg:w-full" : ""
            }`}
            title="Nexora Command Portal"
          >
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-blue-600 shadow-xs shadow-blue-500/20">
              {isTechnician ? (
                <Wrench className="h-3.5 w-3.5 text-white" />
              ) : (
                <RadioTower className="h-3.5 w-3.5 text-white" />
              )}
            </div>

            {(!isCollapsed || isOpen) && (
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <p className="truncate text-xs font-bold tracking-[0.1em] text-slate-100">
                    NEXORA
                  </p>
                  <span className="rounded-xs bg-blue-500/20 px-1 py-0.2 text-[8px] font-bold text-blue-400">
                    {role ?? "OPERATOR"}
                  </span>
                </div>
                <p className="truncate text-[9px] uppercase tracking-[0.05em] text-slate-500">
                  {isTechnician ? "Field Technician" : "ISP Console"}
                </p>
              </div>
            )}
          </Link>

          {/* Desktop collapse toggle button in expanded header */}
          {!isCollapsed && onToggleCollapse && (
            <button
              type="button"
              onClick={onToggleCollapse}
              aria-label="Collapse sidebar"
              title="Collapse sidebar"
              className="hidden h-7 w-7 items-center justify-center rounded-md text-slate-500 transition hover:bg-[#121821] hover:text-slate-200 lg:flex"
            >
              <PanelLeftClose className="h-3.5 w-3.5" />
            </button>
          )}

          {/* Mobile close button */}
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
        <nav className="nexora-scrollbar min-h-0 flex-1 overflow-y-auto px-2 py-2.5">
          {isTechnician ? (
            <div>
              {(!isCollapsed || isOpen) && (
                <p className="px-2 text-[9px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Assigned Work
                </p>
              )}

              <div className="mt-1">
                <Link
                  href="/field-operations"
                  onClick={handleNavClick}
                  title="My Field Jobs"
                  className={`
                    relative flex h-8.5 items-center rounded-md text-xs font-medium transition-all
                    ${isCollapsed && !isOpen ? "justify-center px-0 w-9 mx-auto" : "gap-2.5 px-2.5"}
                    ${
                      isRouteActive("/field-operations")
                        ? "bg-blue-600/15 text-blue-400 shadow-xs"
                        : "text-slate-400 hover:bg-[#121821] hover:text-slate-200"
                    }
                  `}
                >
                  {isRouteActive("/field-operations") && (
                    <span className="absolute left-0 h-3.5 w-0.5 rounded-r bg-blue-500" />
                  )}

                  <Wrench className="h-4 w-4 shrink-0 text-blue-400" />
                  {(!isCollapsed || isOpen) && (
                    <>
                      <span className="min-w-0 flex-1 truncate">My Field Jobs</span>
                      <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                    </>
                  )}
                </Link>
              </div>
            </div>
          ) : (
            <div className={isCollapsed && !isOpen ? "space-y-1.5" : "space-y-3"}>
              {roleNavigation.map((group, groupIdx) => {
                const isGroupCollapsed = !!collapsedGroups[group.label];

                return (
                  <div key={group.label} className={isCollapsed && !isOpen ? "pt-1" : ""}>
                    {/* Collapsed mode divider between groups */}
                    {isCollapsed && !isOpen && groupIdx > 0 && (
                      <div className="my-1.5 border-t border-[#202938]/60" />
                    )}

                    {/* Expanded mode group header */}
                    {(!isCollapsed || isOpen) && (
                      <button
                        type="button"
                        onClick={() => toggleGroup(group.label)}
                        className="flex w-full items-center justify-between px-2 py-1 text-left text-[9px] font-semibold uppercase tracking-[0.12em] text-slate-500 hover:text-slate-400"
                      >
                        <span>{group.label}</span>
                        <ChevronDown
                          className={`h-3 w-3 transition-transform duration-150 ${
                            isGroupCollapsed ? "-rotate-90 text-slate-600" : "text-slate-500"
                          }`}
                        />
                      </button>
                    )}

                    {(!isGroupCollapsed || (isCollapsed && !isOpen)) && (
                      <div className="mt-0.5 space-y-0.5">
                        {group.items.map((item) => {
                          const active = isRouteActive(item.href);
                          const Icon = item.icon;

                          return (
                            <Link
                              key={item.href}
                              href={item.href}
                              onClick={handleNavClick}
                              title={item.title}
                              className={`
                                relative flex h-8 items-center rounded-md text-xs font-medium transition-all
                                ${
                                  isCollapsed && !isOpen
                                    ? "justify-center px-0 w-9 mx-auto"
                                    : "gap-2.5 px-2.5"
                                }
                                ${
                                  active
                                    ? "bg-blue-600/15 text-blue-400 font-semibold"
                                    : "text-slate-400 hover:bg-[#121821] hover:text-slate-200"
                                }
                              `}
                            >
                              {active && (
                                <span className="absolute left-0 h-3 w-0.5 rounded-r bg-blue-500" />
                              )}

                              <Icon
                                className={`h-4 w-4 shrink-0 transition-colors ${
                                  active ? "text-blue-400" : "text-slate-400"
                                }`}
                              />

                              {(!isCollapsed || isOpen) && (
                                <>
                                  <span className="min-w-0 flex-1 truncate">
                                    {item.title}
                                  </span>

                                  {active && (
                                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500 shadow-xs shadow-blue-400" />
                                  )}
                                </>
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

        {/* Footer telemetry & collapse toggle */}
        <div className="shrink-0 border-t border-[#202938] p-2">
          {(!isCollapsed || isOpen) ? (
            <div className="flex items-center justify-between rounded-md border border-[#202938]/60 bg-[#121821] p-2">
              <div className="flex min-w-0 items-center gap-2">
                <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-sm bg-emerald-500/10">
                  {isTechnician ? (
                    <Wrench className="h-2.5 w-2.5 text-amber-400" />
                  ) : (
                    <Signal className="h-2.5 w-2.5 text-emerald-400" />
                  )}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-[10px] font-medium text-slate-200">
                    {isTechnician ? "Field Node" : "Core Live"}
                  </p>
                  <p className="truncate text-[8px] text-slate-500">
                    Telemetry OK
                  </p>
                </div>
              </div>

              {onToggleCollapse && (
                <button
                  type="button"
                  onClick={onToggleCollapse}
                  title="Collapse sidebar"
                  className="hidden h-6 w-6 items-center justify-center rounded text-slate-500 hover:bg-[#202938] hover:text-slate-200 lg:flex"
                >
                  <PanelLeftClose className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center gap-1">
              <div
                className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-400"
                title="Telemetry Live"
              >
                <Signal className="h-3.5 w-3.5" />
              </div>
              {onToggleCollapse && (
                <button
                  type="button"
                  onClick={onToggleCollapse}
                  title="Expand sidebar"
                  aria-label="Expand sidebar"
                  className="flex h-7 w-7 items-center justify-center rounded-md text-slate-500 transition hover:bg-[#121821] hover:text-slate-200"
                >
                  <PanelLeftOpen className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}