"use client";

import { PropsWithChildren } from "react";

import { clearStoredAccessToken } from "@/lib/auth";
import type { CurrentUser } from "@/types/api";
import { Sidebar } from "@/components/layout/sidebar";

type AppShellProps = PropsWithChildren<{
  currentUser?: CurrentUser | null;
  onLogout?: () => void;
  reviewBadge?: number;
  userBadge?: number;
}>;

export function AppShell({
  children,
  currentUser,
  onLogout,
  reviewBadge = 0,
  userBadge = 0,
}: AppShellProps) {
  function handleLogout(): void {
    clearStoredAccessToken();
    onLogout?.();
  }

  if (!currentUser) {
    return <main className="page-shell">{children}</main>;
  }

  return (
    <div className="page-shell flex min-h-screen">
      <Sidebar
        currentUser={currentUser}
        onLogout={handleLogout}
        reviewBadge={reviewBadge}
        userBadge={userBadge}
      />
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}
