import React from "react";
import { AlertTriangle, RefreshCw, ShieldAlert, WifiOff } from "lucide-react";

export type ErrorType = "general" | "network" | "permission" | "validation";

interface ErrorStateProps {
  title?: string;
  message: string;
  errorType?: ErrorType;
  onRetry?: () => void;
  className?: string;
  compact?: boolean;
}

export default function ErrorState({
  title,
  message,
  errorType = "general",
  onRetry,
  className = "",
  compact = false,
}: ErrorStateProps) {
  const getIcon = () => {
    switch (errorType) {
      case "network":
        return WifiOff;
      case "permission":
        return ShieldAlert;
      default:
        return AlertTriangle;
    }
  };

  const Icon = getIcon();

  if (compact) {
    return (
      <div
        className={`flex items-center justify-between gap-3 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-xs text-red-400 ${className}`}
        role="alert"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <Icon className="h-4 w-4 shrink-0 text-red-400" />
          <span className="truncate">{message}</span>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex shrink-0 items-center gap-1.5 font-medium underline hover:text-red-300"
          >
            <RefreshCw className="h-3 w-3" />
            Retry
          </button>
        )}
      </div>
    );
  }

  const defaultTitle =
    errorType === "network"
      ? "Network Connection Lost"
      : errorType === "permission"
      ? "Access Restricted"
      : "Unable to Load Data";

  return (
    <div
      className={`flex min-h-[280px] w-full flex-col items-center justify-center rounded-lg border border-red-500/20 bg-[#0D1117] p-8 text-center ${className}`}
      role="alert"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-red-500/30 bg-red-500/10 text-red-400 shadow-inner">
        <Icon className="h-6 w-6 text-red-400" />
      </div>

      <h3 className="mt-4 text-sm font-semibold text-slate-100">
        {title || defaultTitle}
      </h3>

      <p className="mt-1.5 max-w-sm text-xs leading-relaxed text-slate-400">
        {message}
      </p>

      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-5 inline-flex items-center gap-2 rounded-md border border-[#202938] bg-[#121821] px-4 py-2 text-xs font-medium text-slate-200 transition hover:border-blue-500 hover:text-blue-400 shadow-sm"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Try Again
        </button>
      )}
    </div>
  );
}
