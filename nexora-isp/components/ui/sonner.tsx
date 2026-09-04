"use client";

import { Toaster as Sonner, type ToasterProps } from "sonner";
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, OctagonXIcon, Loader2Icon } from "lucide-react";

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="dark"
      className="toaster group"
      icons={{
        success: <CircleCheckIcon className="size-4 text-emerald-400" />,
        info: <InfoIcon className="size-4 text-blue-400" />,
        warning: <TriangleAlertIcon className="size-4 text-amber-400" />,
        error: <OctagonXIcon className="size-4 text-rose-400" />,
        loading: <Loader2Icon className="size-4 animate-spin text-blue-400" />,
      }}
      toastOptions={{
        className:
          "group toast group-[.toaster]:bg-[#0D1117] group-[.toaster]:text-[#F8FAFC] group-[.toaster]:border-[#202938] group-[.toaster]:shadow-2xl group-[.toaster]:shadow-black/50 group-[.toaster]:rounded-lg text-xs",
        descriptionClassName: "group-[.toast]:text-slate-400 text-xs",
      }}
      {...props}
    />
  );
};

export { Toaster };
