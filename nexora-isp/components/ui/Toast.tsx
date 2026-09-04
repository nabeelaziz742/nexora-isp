import React, { useEffect } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastItem {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  durationMs?: number;
}

interface ToastProps {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}

const typeStyles: Record<
  ToastType,
  {
    border: string;
    bg: string;
    icon: typeof CheckCircle2;
    iconColor: string;
    titleColor: string;
  }
> = {
  success: {
    border: "border-emerald-500/30",
    bg: "bg-[#0D1410]",
    icon: CheckCircle2,
    iconColor: "text-emerald-400",
    titleColor: "text-emerald-300",
  },
  error: {
    border: "border-red-500/30",
    bg: "bg-[#140D0D]",
    icon: AlertCircle,
    iconColor: "text-red-400",
    titleColor: "text-red-300",
  },
  warning: {
    border: "border-amber-500/30",
    bg: "bg-[#14120D]",
    icon: AlertTriangle,
    iconColor: "text-amber-400",
    titleColor: "text-amber-300",
  },
  info: {
    border: "border-blue-500/30",
    bg: "bg-[#0D1017]",
    icon: Info,
    iconColor: "text-blue-400",
    titleColor: "text-blue-300",
  },
};

export function ToastMessage({ toast, onDismiss }: ToastProps) {
  const { border, bg, icon: Icon, iconColor, titleColor } = typeStyles[toast.type];

  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss(toast.id);
    }, toast.durationMs ?? 4500);

    return () => clearTimeout(timer);
  }, [toast.id, toast.durationMs, onDismiss]);

  return (
    <div
      role="alert"
      className={`pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-lg border ${border} ${bg} p-4 shadow-xl shadow-black/40 backdrop-blur-sm animate-[toastSlideIn_0.2s_ease-out]`}
    >
      <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${iconColor}`} />

      <div className="min-w-0 flex-1">
        {toast.title && (
          <p className={`text-xs font-semibold ${titleColor}`}>
            {toast.title}
          </p>
        )}
        <p className="text-xs leading-relaxed text-slate-300">
          {toast.message}
        </p>
      </div>

      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss notification"
        className="shrink-0 text-slate-500 transition hover:text-slate-300"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export function ToastContainer({
  toasts,
  onDismiss,
}: {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="assertive"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2.5 sm:bottom-6 sm:right-6"
    >
      {toasts.map((toast) => (
        <ToastMessage key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
