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
          <Link href="/login">Login</Link>
          <Link href="/shares">Share</Link>
          <Link href="/reviews">Review</Link>
          <Link href="/sync">Sync</Link>
          <Link href="/effective-permissions">Permessi</Link>
        </nav>
        <div className="sidebar-footer">
          {currentUser ? (
            <>
              <small>Sessione attiva</small>
              <strong>{currentUser.username}</strong>
              <span>{currentUser.role}</span>
              <button className="button button-secondary" onClick={handleLogout} type="button">
                Logout
              </button>
            </>
          ) : (
            <>
              <small>Sessione</small>
              <strong>Nessun login</strong>
              <span>Accedi per vedere dati backend reali</span>
            </>
          )}
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
