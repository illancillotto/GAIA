"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { PropsWithChildren, useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { getCurrentUser } from "@/lib/api";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import type { CurrentUser } from "@/types/api";

type ProtectedPageProps = PropsWithChildren<{
  title: string;
  description: string;
}>;

export function ProtectedPage({ title, description, children }: ProtectedPageProps) {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [statusMessage, setStatusMessage] = useState("Accedi per caricare dati dal backend.");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  useEffect(() => {
    async function loadSession() {
      const token = getStoredAccessToken();

      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        const user = await getCurrentUser(token);
        setCurrentUser(user);
        setLoadError(null);
        setStatusMessage("Sessione backend attiva.");
      } catch (error) {
        clearStoredAccessToken();
        setCurrentUser(null);
        setLoadError(error instanceof Error ? error.message : "Errore imprevisto");
        setStatusMessage("Sessione non valida o backend non raggiungibile.");
        router.replace("/login");
      } finally {
        setIsCheckingSession(false);
      }
    }

    void loadSession();
  }, [router]);

  function handleLogout(): void {
    setCurrentUser(null);
    setLoadError(null);
    setStatusMessage("Sessione chiusa. Effettua di nuovo il login.");
    router.replace("/login");
  }

  if (isCheckingSession || !currentUser) {
    return (
      <main className="login-wrap">
        <section className="login-card">
          <p className="badge">Accesso richiesto</p>
          <h1>{title}</h1>
          <p>{description}</p>
          <p className={`status-note${loadError ? " error-text" : ""}`}>{loadError ?? statusMessage}</p>
          <Link className="button" href="/login">
            Vai al login
          </Link>
        </section>
      </main>
    );
  }

  return (
    <AppShell currentUser={currentUser} onLogout={handleLogout}>
      <div className="topbar">
        <div className="badge">{currentUser ? "Backend collegato" : "Sessione richiesta"}</div>
        <div className="badge">API target: /api</div>
      </div>

      <section className="hero">
        <h2>{title}</h2>
        <p>{description}</p>
      </section>

      <section className="stack">
        <article className="panel">
          <h3>Stato accesso</h3>
          <p className={`status-note${loadError ? " error-text" : ""}`}>{loadError ?? statusMessage}</p>
          {!currentUser ? (
            <p className="status-note">
              Vai alla <Link href="/login">pagina di login</Link> per usare il backend reale.
            </p>
          ) : children}
        </article>
      </section>
    </AppShell>
  );
}
