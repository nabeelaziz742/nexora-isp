"use client";

import Link from "next/link";
import {
  usePathname,
  useRouter,
} from "next/navigation";
import {
  RadioTower,
  Signal,
  Wrench,
  X,
} from "lucide-react";
import {
  useEffect,
  useState,
} from "react";

import { getNavigationForRole } from "@/config/navigation";

interface AppSidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

type NavigationRole =
  | "OWNER"
  | "STAFF"
  | "TECHNICIAN";

export default function AppSidebar({
  isOpen = false,
  onClose,
}: AppSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const [role, setRole] = useState<string | null>(
    null,
  );
  const [roleLoaded, setRoleLoaded] = useState(false);

  useEffect(() => {
    const storedRole = window.localStorage.getItem(
      "nexora_role",
    );

    setRole(storedRole);
    setRoleLoaded(true);
  }, []);

  const isTechnician = role === "TECHNICIAN";

  const roleNavigation = getNavigationForRole(
    role as NavigationRole | null,
  );

  const navigationHrefs = roleNavigation.flatMap(
    (group) =>
      group.items.map((item) => item.href),
  );

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
  }, [
    isTechnician,
    pathname,
    roleLoaded,
    router,
  ]);

  function isRouteActive(href: string) {
    const matchingRoutes = navigationHrefs
      .filter(
        (navigationHref) =>
          pathname === navigationHref ||
          pathname.startsWith(
            `${navigationHref}/`,
          ),
      )
      .sort(
        (firstRoute, secondRoute) =>
          secondRoute.length - firstRoute.length,
      );

    return matchingRoutes[0] === href;
  }

  if (!roleLoaded) {
    return (
      <aside className="fixed inset-y-0 left-0 z-50 w-[264px] border-r border-[#202938] bg-[#0D1117] lg:static">
        <div className="h-16 border-b border-[#202938]" />
      </aside>
    );
  }

  return (
    <aside
      className={`
        fixed inset-y-0 left-0 z-50 flex w-[264px] shrink-0 flex-col
        border-r border-[#202938] bg-[#0D1117]
        transition-transform duration-200 ease-out
        lg:static lg:z-auto lg:translate-x-0
        ${
          isOpen
            ? "translate-x-0"
            : "-translate-x-full"
        }
      `}
    >
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-[#202938] px-4">
        <Link
          href={
            isTechnician
              ? "/field-operations"
              : "/command-center"
          }
          onClick={onClose}
          className="flex min-w-0 items-center gap-3"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center bg-blue-600">
            {isTechnician ? (
              <Wrench className="h-4 w-4 text-white" />
            ) : (
              <RadioTower className="h-4 w-4 text-white" />
            )}
          </div>

          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-[0.08em] text-slate-50">
              NEXORA
            </p>

            <p className="truncate text-[10px] uppercase tracking-[0.08em] text-slate-500">
              {isTechnician
                ? "Technician Operations"
                : "ISP Command Center"}
            </p>
          </div>
        </Link>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close navigation"
          className="flex h-8 w-8 items-center justify-center text-slate-500 transition hover:bg-[#121821] hover:text-slate-200 lg:hidden"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <nav className="nexora-scrollbar min-h-0 flex-1 overflow-y-auto px-3 py-4">
        {isTechnician ? (
          <div>
            <p className="px-3 text-[9px] font-semibold uppercase tracking-[0.14em] text-slate-600">
              Technician
            </p>

            <div className="mt-2">
              <Link
                href="/field-operations"
                onClick={onClose}
                className={`
                  relative flex h-9 items-center gap-3 px-3
                  text-xs font-medium transition
                  ${
                    isRouteActive(
                      "/field-operations",
                    )
                      ? "bg-blue-500/10 text-blue-400"
                      : "text-slate-400 hover:bg-[#121821] hover:text-slate-200"
                  }
                `}
              >
                {isRouteActive(
                  "/field-operations",
                ) && (
                  <span className="absolute left-0 h-4 w-0.5 bg-blue-500" />
                )}

                <Wrench className="h-4 w-4 shrink-0 text-blue-400" />

                <span className="min-w-0 flex-1 truncate">
                  My Work Orders
                </span>

                {isRouteActive(
                  "/field-operations",
                ) && (
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                )}
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            {roleNavigation.map((group) => (
              <div key={group.label}>
                <p className="px-3 text-[9px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                  {group.label}
                </p>

                <div className="mt-2 space-y-1">
                  {group.items.map((item) => {
                    const active = isRouteActive(
                      item.href,
                    );
                    const Icon = item.icon;

                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={onClose}
                        className={`
                          relative flex h-9 items-center gap-3 px-3
                          text-xs font-medium transition
                          ${
                            active
                              ? "bg-blue-500/10 text-blue-400"
                              : "text-slate-400 hover:bg-[#121821] hover:text-slate-200"
                          }
                        `}
                      >
                        {active && (
                          <span className="absolute left-0 h-4 w-0.5 bg-blue-500" />
                        )}

                        <Icon
                          className={`h-4 w-4 shrink-0 ${
                            active
                              ? "text-blue-400"
                              : "text-slate-500"
                          }`}
                        />

                        <span className="min-w-0 flex-1 truncate">
                          {item.title}
                        </span>

                        {active && (
                          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                        )}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </nav>

      <div className="shrink-0 border-t border-[#202938] p-3">
        <div className="bg-[#121821] p-3">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center bg-emerald-500/10">
              {isTechnician ? (
                <Wrench className="h-3.5 w-3.5 text-amber-400" />
              ) : (
                <Signal className="h-3.5 w-3.5 text-emerald-400" />
              )}
            </div>

            <div className="min-w-0">
              <p className="text-[11px] font-medium text-slate-200">
                {isTechnician
                  ? "Technician Access"
                  : "Network Operational"}
              </p>

              <p className="mt-0.5 text-[10px] text-slate-600">
                {isTechnician
                  ? "Assigned work orders only"
                  : "Monitoring systems active"}
              </p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}