"use client";

import { createContext, useContext } from "react";

import type { CurrentUser } from "@/types/api";

type AppShellContextValue = {
  currentUser: CurrentUser | null;
  grantedSectionKeys: string[];
  reviewBadge: number;
  userBadge: number;
  openMobileSidebar: () => void;
  onLogout: () => void;
};

const noop = () => undefined;

const AppShellContext = createContext<AppShellContextValue>({
  currentUser: null,
  grantedSectionKeys: [],
  reviewBadge: 0,
  userBadge: 0,
  openMobileSidebar: noop,
  onLogout: noop,
});

export function AppShellProvider({
  children,
  currentUser,
  grantedSectionKeys,
  reviewBadge = 0,
  userBadge = 0,
  openMobileSidebar = noop,
  onLogout = noop,
}: {
  currentUser: CurrentUser | null;
  grantedSectionKeys: string[];
  reviewBadge?: number;
  userBadge?: number;
  children: React.ReactNode;
  openMobileSidebar?: () => void;
  onLogout?: () => void;
}) {
  return (
    <AppShellContext.Provider
      value={{ currentUser, grantedSectionKeys, reviewBadge, userBadge, openMobileSidebar, onLogout }}
    >
      {children}
    </AppShellContext.Provider>
  );
}

export function useAppShellContext(): AppShellContextValue {
  return useContext(AppShellContext);
}
