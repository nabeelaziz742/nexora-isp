"use client";

import { useState } from "react";

import AppSidebar from "@/components/layout/AppSidebar";
import TopCommandBar from "@/components/layout/TopCommandBar";

interface DashboardShellProps {
  children: React.ReactNode;
}

export default function DashboardShell({
  children,
}: DashboardShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  function openSidebar() {
    setSidebarOpen(true);
  }

  function closeSidebar() {
    setSidebarOpen(false);
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#070A0F]">
      <AppSidebar
        isOpen={sidebarOpen}
        onClose={closeSidebar}
      />

      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={closeSidebar}
          className="fixed inset-0 z-40 bg-black/70 lg:hidden"
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <TopCommandBar onMenuClick={openSidebar} />

        <main className="nexora-scrollbar min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[1920px] p-4 sm:p-5 lg:p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}