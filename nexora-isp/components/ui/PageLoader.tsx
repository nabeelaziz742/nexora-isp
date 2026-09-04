import React from "react";
import { RadioTower } from "lucide-react";

interface PageLoaderProps {
  message?: string;
  subtext?: string;
  fullscreen?: boolean;
}

export default function PageLoader({
  message = "Loading NEXORA Operations...",
  subtext = "Authenticating secure session and telemetry",
  fullscreen = true,
}: PageLoaderProps) {
  const containerClass = fullscreen
    ? "fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#070A0F]/95 backdrop-blur-sm"
    : "flex min-h-[380px] w-full flex-col items-center justify-center bg-[#0D1117]/60 p-8";

  return (
    <div className={containerClass} role="status" aria-live="polite">
      <div className="relative flex flex-col items-center">
        {/* Radar beacon animation rings */}
        <div className="relative flex h-20 w-20 items-center justify-center">
          <div className="absolute h-full w-full animate-ping rounded-full bg-blue-500/15" />
          <div className="absolute h-14 w-14 animate-pulse rounded-full border border-blue-500/30 bg-blue-500/10" />
          <div className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-blue-500/50 bg-blue-600 shadow-lg shadow-blue-500/25">
            <RadioTower className="h-5 w-5 text-white" />
          </div>
        </div>

        {/* Loading textual status */}
        <div className="mt-5 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-100">
            NEXORA ISP
          </p>
          <p className="mt-1.5 text-xs text-blue-400 font-medium">
            {message}
          </p>
          {subtext && (
            <p className="mt-1 text-[11px] text-slate-500 max-w-xs">
              {subtext}
            </p>
          )}
        </div>

        {/* Indeterminate linear loading bar */}
        <div className="mt-5 h-0.5 w-44 overflow-hidden rounded-full bg-[#1A2230]">
          <div className="h-full w-1/3 animate-[indeterminate_1.5s_infinite_ease-in-out] bg-gradient-to-r from-blue-600 via-blue-400 to-cyan-400 rounded-full" />
        </div>
      </div>
    </div>
  );
}
