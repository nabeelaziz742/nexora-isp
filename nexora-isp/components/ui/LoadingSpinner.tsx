import React from "react";
import { Loader2 } from "lucide-react";

export type SpinnerSize = "xs" | "sm" | "md" | "lg" | "xl";
export type SpinnerTone = "primary" | "secondary" | "white" | "success" | "warning" | "danger";

interface LoadingSpinnerProps {
  size?: SpinnerSize;
  tone?: SpinnerTone;
  className?: string;
  label?: string;
}

const sizeClasses: Record<SpinnerSize, string> = {
  xs: "h-3 w-3",
  sm: "h-4 w-4",
  md: "h-5 w-5",
  lg: "h-6 w-6",
  xl: "h-8 w-8",
};

const toneClasses: Record<SpinnerTone, string> = {
  primary: "text-blue-400",
  secondary: "text-slate-400",
  white: "text-white",
  success: "text-emerald-400",
  warning: "text-amber-400",
  danger: "text-red-400",
};

export default function LoadingSpinner({
  size = "md",
  tone = "primary",
  className = "",
  label,
}: LoadingSpinnerProps) {
  return (
    <div className={`inline-flex items-center gap-2 ${className}`} role="status" aria-label={label || "Loading"}>
      <Loader2 className={`animate-spin shrink-0 ${sizeClasses[size]} ${toneClasses[tone]}`} />
      {label && <span className="text-xs text-slate-400">{label}</span>}
      <span className="sr-only">{label || "Loading..."}</span>
    </div>
  );
}
