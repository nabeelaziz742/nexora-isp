"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import AppSidebar from "@/components/layout/AppSidebar";
import TopCommandBar from "@/components/layout/TopCommandBar";

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

  const [sessionReady, setSessionReady] = useState(false);

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
        console.error(
          "Failed to restore authenticated session:",
          error,
        );

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
      <div className="flex h-screen items-center justify-center bg-[var(--background)]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="size-5 animate-spin text-blue-400" />

          <p className="text-[11px] text-[var(--text-muted)]">
            Restoring secure session...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--background)]">
      <AppSidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopCommandBar />

        <main className="nexora-scrollbar min-h-0 flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}