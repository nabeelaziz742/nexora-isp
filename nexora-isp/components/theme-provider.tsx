"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";

// Dark is the default; the user's choice is remembered in localStorage.
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="dark"
      themes={["dark", "light"]}
      enableSystem={false}
      disableTransitionOnChange
      storageKey="nexora_theme"
    >
      {children}
    </NextThemesProvider>
  );
}
