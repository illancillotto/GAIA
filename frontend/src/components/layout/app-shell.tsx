"use client";

import Link from "next/link";
import { PropsWithChildren } from "react";

import { clearStoredAccessToken } from "@/lib/auth";
import type { CurrentUser } from "@/types/api";

type AppShellProps = PropsWithChildren<{
  currentUser?: CurrentUser | null;
  onLogout?: () => void;
}>;

export function AppShell({ children, currentUser, onLogout }: AppShellProps) {
  function handleLogout(): void {
    clearStoredAccessToken();
    onLogout?.();
  }

  if (!currentUser) {
    return <main className="content content-public">{children}</main>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>NAS Access Audit</h1>
        <p>
          Workspace iniziale per audit accessi, snapshot, review e reporting
          operativo.
        </p>
        <nav>
          <Link href="/">Dashboard</Link>
          <Link href="/users">Utenti</Link>
          <Link href="/groups">Gruppi</Link>
          <Link href="/shares">Share</Link>
          <Link href="/reviews">Review</Link>
          <Link href="/sync">Sync</Link>
          <Link href="/effective-permissions">Permessi</Link>
        </nav>
        <div className="sidebar-footer">
          <small>Sessione attiva</small>
          <strong>{currentUser.username}</strong>
          <span>{currentUser.role}</span>
          <button className="button button-secondary" onClick={handleLogout} type="button">
            Logout
          </button>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
