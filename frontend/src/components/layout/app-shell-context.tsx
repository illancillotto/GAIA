"use client";

import { createContext, useContext } from "react";

import type { CurrentUser } from "@/types/api";

type AppShellContextValue = {
  currentUser: CurrentUser | null;
  grantedSectionKeys: string[];
};

const AppShellContext = createContext<AppShellContextValue>({
  currentUser: null,
  grantedSectionKeys: [],
});

export function AppShellProvider({
  children,
  currentUser,
  grantedSectionKeys,
}: AppShellContextValue & { children: React.ReactNode }) {
  return (
    <AppShellContext.Provider value={{ currentUser, grantedSectionKeys }}>
      {children}
    </AppShellContext.Provider>
  );
}

export function useAppShellContext(): AppShellContextValue {
  return useContext(AppShellContext);
}
