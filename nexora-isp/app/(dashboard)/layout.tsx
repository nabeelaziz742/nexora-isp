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
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Close mobile sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
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
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Workspace Area */}
      <div className="flex min-w-0 flex-1 flex-col">
        <TopCommandBar
          onMenuClick={() => setSidebarOpen((prev) => !prev)}
        />

        <main className="nexora-scrollbar min-h-0 flex-1 overflow-y-auto bg-[#070A0F]">
          {children}
        </main>
      </div>
    </div>
  );
}