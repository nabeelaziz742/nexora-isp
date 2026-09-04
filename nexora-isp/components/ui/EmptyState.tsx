import React from "react";
import { FolderOpen, LucideIcon, Plus } from "lucide-react";
import Link from "next/link";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  actionLabel?: string;
  actionHref?: string;
  onActionClick?: () => void;
  className?: string;
}

export default function EmptyState({
  title,
  description,
  icon: Icon = FolderOpen,
  actionLabel,
  actionHref,
  onActionClick,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`flex min-h-[280px] w-full flex-col items-center justify-center rounded-lg border border-[#202938] bg-[#0D1117] p-8 text-center ${className}`}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-[#202938] bg-[#121821] text-slate-500 shadow-inner">
        <Icon className="h-6 w-6 text-slate-400" />
      </div>

      <h3 className="mt-4 text-sm font-semibold text-slate-100">{title}</h3>

      <p className="mt-1.5 max-w-sm text-xs leading-relaxed text-slate-400">
        {description}
      </p>

      {actionLabel && (
        <div className="mt-5">
          {actionHref ? (
            <Link
              href={actionHref}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white transition hover:bg-blue-500 shadow-sm"
            >
              <Plus className="h-3.5 w-3.5" />
              {actionLabel}
            </Link>
          ) : onActionClick ? (
            <button
              type="button"
              onClick={onActionClick}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-xs font-medium text-white transition hover:bg-blue-500 shadow-sm"
            >
              <Plus className="h-3.5 w-3.5" />
              {actionLabel}
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}
