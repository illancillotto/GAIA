"use client";

import { PropsWithChildren } from "react";

import { clearStoredAccessToken } from "@/lib/auth";
import { usePresenceHeartbeat } from "@/lib/use-presence-heartbeat";
import type { CurrentUser } from "@/types/api";
import { AppShellProvider } from "@/components/layout/app-shell-context";
import { Sidebar } from "@/components/layout/sidebar";

type AppShellProps = PropsWithChildren<{
  currentUser?: CurrentUser | null;
  onLogout?: () => void;
  reviewBadge?: number;
  userBadge?: number;
  grantedSectionKeys?: string[];
}>;

export function AppShell({
  children,
  currentUser,
  onLogout,
  reviewBadge = 0,
  userBadge = 0,
  grantedSectionKeys = [],
}: AppShellProps) {
  usePresenceHeartbeat({ enabled: Boolean(currentUser) });

  function handleLogout(): void {
    clearStoredAccessToken();
    onLogout?.();
  }

  if (!currentUser) {
    return (
      <AppShellProvider currentUser={null} grantedSectionKeys={[]}>
        <main className="page-shell">{children}</main>
      </AppShellProvider>
    );
  }

  return (
    <AppShellProvider currentUser={currentUser} grantedSectionKeys={grantedSectionKeys}>
      <div className="page-shell flex min-h-screen">
        <Sidebar
          currentUser={currentUser}
          onLogout={handleLogout}
          reviewBadge={reviewBadge}
          userBadge={userBadge}
          grantedSectionKeys={grantedSectionKeys}
        />
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </AppShellProvider>
  );
}
