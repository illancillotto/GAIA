"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { AppShell } from "@/components/layout/app-shell";
import { getCurrentUser, getDashboardSummary } from "@/lib/api";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import type { CurrentUser, DashboardSummary } from "@/types/api";

const emptySummary: DashboardSummary = {
  nas_users: 0,
  nas_groups: 0,
  shares: 0,
  reviews: 0,
  snapshots: 0,
  sync_runs: 0,
};

export default function HomePage() {
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [statusMessage, setStatusMessage] = useState("Accedi per caricare i dati reali dal backend.");
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboard() {
      const token = getStoredAccessToken();

      if (!token) {
        setSummary(emptySummary);
        setCurrentUser(null);
        setLoadError(null);
        setStatusMessage("Accedi per caricare i dati reali dal backend.");
        return;
      }

      try {
        const [user, dashboardSummary] = await Promise.all([
          getCurrentUser(token),
          getDashboardSummary(token),
        ]);

        setCurrentUser(user);
        setSummary(dashboardSummary);
        setLoadError(null);
        setStatusMessage("Dashboard collegata al backend FastAPI.");
      } catch (error) {
        clearStoredAccessToken();
        setCurrentUser(null);
        setSummary(emptySummary);
        setLoadError(error instanceof Error ? error.message : "Errore imprevisto");
        setStatusMessage("Sessione non valida o backend non raggiungibile.");
      }
    }

    void loadDashboard();
  }, []);

  const dashboardCards = [
    { title: "Utenti NAS", value: String(summary.nas_users), note: "Utenti sincronizzati o seedati nel backend" },
    { title: "Gruppi", value: String(summary.nas_groups), note: "Gruppi NAS attualmente persistiti" },
    { title: "Share", value: String(summary.shares), note: "Cartelle condivise presenti nel dominio audit" },
    { title: "Review", value: String(summary.reviews), note: "Review registrate nella piattaforma" },
    { title: "Snapshot", value: String(summary.snapshots), note: "Fotografie disponibili per audit e sync" },
    { title: "Sync Run", value: String(summary.sync_runs), note: "Esecuzioni sync registrate con audit trail" },
  ];

  function handleLogout(): void {
    setCurrentUser(null);
    setSummary(emptySummary);
    setLoadError(null);
    setStatusMessage("Sessione chiusa. Accedi di nuovo per ricaricare i dati.");
  }

  return (
    <AppShell currentUser={currentUser} onLogout={handleLogout}>
      <div className="topbar">
        <div>
          <p className="badge">{currentUser ? "Backend collegato" : "Ambiente bootstrap"}</p>
        </div>
        <div className="badge">API target: /api</div>
      </div>

      <section className="hero">
        <h2>Controllo centralizzato degli accessi NAS</h2>
        <p>
          La dashboard ora e predisposta per mostrare dati reali del backend. Il
          primo step operativo e il login applicativo, che carica utente corrente
          e riepilogo audit.
        </p>
      </section>

      <section className="stack">
        <article className="panel">
          <h3>Stato sessione</h3>
          <p className={`status-note${loadError ? " error-text" : ""}`}>{loadError ?? statusMessage}</p>
          {!currentUser ? (
            <p className="status-note">
              Vai alla <Link href="/login">pagina di login</Link> per usare il backend reale.
            </p>
          ) : null}
        </article>

        <section className="panel-grid">
          {dashboardCards.map((card) => (
            <article className="panel" key={card.title}>
              <small>{card.title}</small>
              <div className="metric">{card.value}</div>
              <p>{card.note}</p>
            </article>
          ))}
        </section>
      </section>
    </AppShell>
  );
}
