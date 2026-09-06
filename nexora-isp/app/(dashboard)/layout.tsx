"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import AppSidebar from "@/components/layout/AppSidebar";
import TopCommandBar from "@/components/layout/TopCommandBar";
import PageLoader from "@/components/ui/PageLoader";

import { getCurrentSession } from "@/services/auth.service";
import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
} from "@/services/auth-storage";

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const router = useRouter();
  const pathname = usePathname();

  const [sessionReady, setSessionReady] = useState(false);
  const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Initialize collapsed preference from localStorage
  useEffect(() => {
    try {
      const stored = window.localStorage.getItem("nexora_sidebar_collapsed");
      if (stored !== null) {
        setSidebarCollapsed(stored === "true");
      }
    } catch {
      // Ignore
    }
  }, []);

  // Close mobile sidebar on route change
  useEffect(() => {
    setSidebarMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      const accessToken = getAccessToken();
      const refreshToken = getRefreshToken();

      if (!accessToken && !refreshToken) {
        clearAuthTokens();
        router.replace("/");
        return;
      }

      try {
        await getCurrentSession();

        if (active) {
          setSessionReady(true);
        }
      } catch (error) {
        console.error("Failed to restore authenticated session:", error);
        clearAuthTokens();

        if (active) {
          router.replace("/");
        }
      }
    }

    restoreSession();

    return () => {
      active = false;
    };
  }, [router]);

  const handleToggleSidebar = () => {
    if (typeof window !== "undefined" && window.innerWidth < 1024) {
      setSidebarMobileOpen((prev) => !prev);
    } else {
      setSidebarCollapsed((prev) => {
        const next = !prev;
        try {
          window.localStorage.setItem("nexora_sidebar_collapsed", String(next));
        } catch {
          // Ignore
        }
        return next;
      });
    }
  };

  const handleToggleCollapse = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem("nexora_sidebar_collapsed", String(next));
      } catch {
        // Ignore
      }
      return next;
    });
  };

  if (!sessionReady) {
    return (
      <PageLoader
        message="Restoring secure operator session..."
        subtext="Validating tenant cryptographic context and telemetry permissions"
        fullscreen={true}
      />
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--background)]">
      {/* Navigation Sidebar */}
      <AppSidebar
        isOpen={sidebarMobileOpen}
        onClose={() => setSidebarMobileOpen(false)}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={handleToggleCollapse}
      />

      {/* Main Workspace Area */}
      <div className="flex min-w-0 flex-1 flex-col">
        <TopCommandBar
          onMenuClick={handleToggleSidebar}
        />

        <main className="nexora-scrollbar min-h-0 flex-1 overflow-y-auto bg-[#070A0F] p-5">
          <div className="mx-auto w-full max-w-[1600px] min-w-0">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}