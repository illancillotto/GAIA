"use client";

import { PropsWithChildren, useCallback, useState } from "react";

import { clearStoredAccessToken } from "@/lib/auth";
import { usePresenceHeartbeat } from "@/lib/use-presence-heartbeat";
import type { CurrentUser } from "@/types/api";
import { AppShellProvider } from "@/components/layout/app-shell-context";
import { MobileSidebarDrawer, Sidebar } from "@/components/layout/sidebar";

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
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const openMobileSidebar = useCallback(() => setIsMobileSidebarOpen(true), []);
  const closeMobileSidebar = useCallback(() => setIsMobileSidebarOpen(false), []);

  usePresenceHeartbeat({ enabled: Boolean(currentUser) });

  function handleLogout(): void {
    clearStoredAccessToken();
    closeMobileSidebar();
    onLogout?.();
  }

  if (!currentUser) {
    return (
      <AppShellProvider currentUser={null} grantedSectionKeys={[]} reviewBadge={0} userBadge={0}>
        <main className="page-shell">{children}</main>
      </AppShellProvider>
    );
  }

  return (
    <AppShellProvider
      currentUser={currentUser}
      grantedSectionKeys={grantedSectionKeys}
      reviewBadge={reviewBadge}
      userBadge={userBadge}
      openMobileSidebar={openMobileSidebar}
      onLogout={handleLogout}
    >
      <div className="page-shell flex min-h-screen overflow-x-clip">
        <Sidebar
          currentUser={currentUser}
          onLogout={handleLogout}
          reviewBadge={reviewBadge}
          userBadge={userBadge}
          grantedSectionKeys={grantedSectionKeys}
        />
        <MobileSidebarDrawer
          currentUser={currentUser}
          onLogout={handleLogout}
          reviewBadge={reviewBadge}
          userBadge={userBadge}
          grantedSectionKeys={grantedSectionKeys}
          isOpen={isMobileSidebarOpen}
          onClose={closeMobileSidebar}
        />
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </AppShellProvider>
  );
}
