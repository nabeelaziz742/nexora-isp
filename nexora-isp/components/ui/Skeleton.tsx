import React from "react";

interface SkeletonProps {
  className?: string;
  count?: number;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-md bg-[#1A2230]/70 ${className}`}
      aria-hidden="true"
    />
  );
}

export function SkeletonMetricCard() {
  return (
    <div className="rounded-lg border border-[#202938] bg-[#0D1117] p-4 animate-pulse">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="h-2.5 w-20 bg-[#1A2230] rounded-md" />
          <div className="h-6 w-28 bg-[#202938] rounded-md" />
        </div>
        <div className="h-8 w-8 bg-[#1A2230] rounded-md" />
      </div>
      <div className="mt-3 border-t border-[#202938] pt-2.5">
        <div className="h-2 w-32 bg-[#1A2230] rounded-md" />
      </div>
    </div>
  );
}

export function SkeletonTable({
  columns = 5,
  rows = 5,
}: {
  columns?: number;
  rows?: number;
}) {
  return (
    <div className="w-full rounded-lg border border-[#202938] bg-[#0D1117] animate-pulse overflow-hidden">
      {/* Table Header Skeleton */}
      <div className="flex border-b border-[#202938] bg-[#0A0E14] px-4 py-3">
        {Array.from({ length: columns }).map((_, i) => (
          <div key={i} className="flex-1 px-2">
            <div className="h-2.5 w-16 bg-[#1A2230] rounded-md" />
          </div>
        ))}
      </div>

      {/* Table Rows Skeleton */}
      <div className="divide-y divide-[#182131]">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="flex items-center px-4 py-3.5">
            {Array.from({ length: columns }).map((_, colIndex) => (
              <div key={colIndex} className="flex-1 px-2">
                <div
                  className="h-3 bg-[#182131] rounded-md"
                  style={{ width: `${Math.max(40, (colIndex + 1) * 20)}%` }}
                />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonCard({ className = "" }: SkeletonProps) {
  return (
    <div className={`rounded-lg border border-[#202938] bg-[#0D1117] p-5 animate-pulse space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="h-4 w-32 bg-[#202938] rounded-md" />
        <div className="h-3 w-16 bg-[#1A2230] rounded-md" />
      </div>
      <div className="space-y-2.5">
        <div className="h-3 w-full bg-[#1A2230] rounded-md" />
        <div className="h-3 w-4/5 bg-[#1A2230] rounded-md" />
        <div className="h-3 w-2/3 bg-[#1A2230] rounded-md" />
      </div>
    </div>
  );
}

export default Skeleton;

