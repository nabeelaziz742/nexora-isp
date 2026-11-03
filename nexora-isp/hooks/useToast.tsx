"use client";

import { toast as sonnerToast } from "sonner";

export interface ToastContextValue {
  toast: typeof sonnerToast;
  success: (message: string, title?: string) => void;
  error: (message: string, title?: string) => void;
  warning: (message: string, title?: string) => void;
  info: (message: string, title?: string) => void;
}

// One shared instance, so components can list it in hook dependencies
// without re-running effects on every render.
const toastApi: ToastContextValue = {
  toast: sonnerToast,
  success: (message: string, title?: string) => {
    sonnerToast.success(title ? `${title}: ${message}` : message);
  },
  error: (message: string, title?: string) => {
    sonnerToast.error(title ? `${title}: ${message}` : message);
  },
  warning: (message: string, title?: string) => {
    sonnerToast.warning(title ? `${title}: ${message}` : message);
  },
  info: (message: string, title?: string) => {
    sonnerToast.info(title ? `${title}: ${message}` : message);
  },
};

export function useToast(): ToastContextValue {
  return toastApi;
}

export const toast = sonnerToast;
