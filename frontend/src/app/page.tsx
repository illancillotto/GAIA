"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser, getDashboardSummary, getMyPermissions, isAuthError } from "@/lib/api";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { hasSectionAccess } from "@/lib/section-access";
import type { CurrentUser, DashboardSummary } from "@/types/api";

type ModuleStatus = "active" | "coming";

type HomeModule = {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  href: string;
  status: ModuleStatus;
  statusLabel: string;
  accentClassName: string;
};

const modules: HomeModule[] = [
  {
    id: "accessi",
    title: "GAIA NAS Control",
    subtitle: "NAS Control",
    description:
      "Controllo del NAS Synology. Utenti, gruppi, cartelle condivise, permessi effettivi e workflow di review per i responsabili di settore.",
    href: "/nas-control",
    status: "active",
    statusLabel: "Operativo",
    accentClassName: "border-[#1D4E35]/20 bg-[#1D4E35] text-white shadow-[0_24px_64px_rgba(29,78,53,0.22)]",
  },
  {
    id: "rete",
    title: "GAIA Rete",
    subtitle: "Network Monitor",
    description:
      "Monitoraggio della rete LAN. Scansione dispositivi, mappa interattiva per piano e alert per dispositivi nuovi o non raggiungibili.",
    href: "/network",
    status: "active",
    statusLabel: "Operativo",
    accentClassName: "border-[#0F766E]/20 bg-[#ECFDF5] text-gray-900 shadow-[0_24px_64px_rgba(15,118,110,0.12)]",
  },
  {
    id: "inventario",
    title: "GAIA Inventario",
    subtitle: "IT Inventory",
    description:
      "Registro centralizzato dei dispositivi IT. Anagrafica, garanzie, assegnazioni utenti e import da CSV.",
    href: "/inventory",
    status: "coming",
    statusLabel: "In sviluppo",
    accentClassName: "border-[#E07A5F]/20 bg-white/65 text-gray-900",
  },
  {
    id: "catasto",
    title: "GAIA Catasto",
    subtitle: "Servizi AdE",
    description:
      "Integrazione con SISTER per download visure catastali, batch CSV, gestione CAPTCHA e archivio documentale.",
    href: "/catasto",
    status: "active",
    statusLabel: "Operativo",
    accentClassName: "border-[#7A3E0B]/20 bg-[#FFF7ED] text-gray-900 shadow-[0_24px_64px_rgba(122,62,11,0.12)]",
  },
];

const emptySummary: DashboardSummary = {
  nas_users: 0,
  nas_groups: 0,
  shares: 0,
  reviews: 0,
  snapshots: 0,
  sync_runs: 0,
};

export default function HomePage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [grantedSectionKeys, setGrantedSectionKeys] = useState<string[]>([]);

  useEffect(() => {
    async function loadHome() {
      const token = getStoredAccessToken();

      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        const [user, dashboardSummary, permissionSummary] = await Promise.all([
          getCurrentUser(token),
          getDashboardSummary(token),
          getMyPermissions(token),
        ]);

        setCurrentUser(user);
        setSummary(dashboardSummary);
        setGrantedSectionKeys(permissionSummary.granted_keys);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore imprevisto");
        if (isAuthError(error)) {
          clearStoredAccessToken();
          setCurrentUser(null);
          setSummary(emptySummary);
          setGrantedSectionKeys([]);
          router.replace("/login");
        }
      } finally {
        setIsCheckingSession(false);
      }
    }

    void loadHome();
  }, [router]);

  function handleLogout(): void {
    clearStoredAccessToken();
    setCurrentUser(null);
    setSummary(emptySummary);
    setGrantedSectionKeys([]);
    router.replace("/login");
  }

  if (isCheckingSession || !currentUser) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <p className="mb-2 inline-flex rounded-full bg-[#EAF3E8] px-3 py-1 text-xs font-medium text-[#1D4E35]">
            Reindirizzamento
          </p>
          <h1 className="page-heading">Verifica sessione</h1>
          <p className="mt-2 text-sm text-gray-500">
            Controllo credenziali locali e connessione al backend.
          </p>
          <p className={`mt-4 text-sm ${loadError ? "text-red-600" : "text-gray-500"}`}>
            {loadError ?? "Accedi per caricare i dati reali dal backend."}
          </p>
          <Link className="btn-primary mt-6" href="/login">
            Vai al login
          </Link>
        </section>
      </main>
    );
  }

  const canAccessUsersSection = hasSectionAccess(grantedSectionKeys, "accessi.users");
  const canManageGaiaUsers =
    (currentUser.role === "admin" || currentUser.role === "super_admin")
    && currentUser.enabled_modules.includes("accessi");
  const visibleModules = modules.filter((moduleItem) => {
    if (moduleItem.status !== "active") {
      return true;
    }

    const moduleKey =
      moduleItem.id === "accessi"
        ? "accessi"
        : moduleItem.id === "rete"
          ? "rete"
          : moduleItem.id === "inventario"
            ? "inventario"
            : moduleItem.id === "catasto"
              ? "catasto"
              : moduleItem.id;

    return currentUser.enabled_modules.includes(moduleKey);
  });
  const activeVisibleModulesCount = visibleModules.filter((moduleItem) => moduleItem.status === "active").length;

  return (
    <main className="min-h-screen bg-[#0E1712] text-white">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-6 py-6 sm:px-8 lg:px-10">
        <header className="flex flex-col gap-6 border-b border-white/10 pb-8 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="inline-flex items-center rounded-full border border-[#1D4E35]/50 bg-[#1D4E35]/15 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.24em] text-[#9BD3A7]">
              GAIA
            </div>
            <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl">
              Gestione Apparati Informativi
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-white/70 sm:text-base">
              Piattaforma IT governance del Consorzio di Bonifica dell&apos;Oristanese. Un unico punto di ingresso
              per controllo NAS, servizi catastali, monitoraggio rete e inventario dispositivi.
            </p>
          </div>

          <div className="w-full max-w-sm rounded-3xl border border-white/10 bg-white/5 p-5 backdrop-blur sm:w-auto">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-white/45">Sessione</p>
                <p className="mt-2 text-lg font-medium text-white">{currentUser.username}</p>
                <p className="text-sm text-white/55">{currentUser.email}</p>
              </div>
              <button
                className="rounded-full border border-white/15 px-3 py-1.5 text-xs font-medium text-white/80 transition hover:border-white/25 hover:bg-white/5 hover:text-white"
                onClick={handleLogout}
                type="button"
              >
                Logout
              </button>
            </div>
            <p className="mt-4 text-xs text-white/45">Consorzio di Bonifica dell&apos;Oristanese</p>
            {canManageGaiaUsers ? (
              <Link
                href="/gaia/users"
                className="mt-4 inline-flex w-full items-center justify-center rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/15"
              >
                Apri Utenti GAIA
              </Link>
            ) : null}
          </div>
        </header>

        <section className="flex flex-1 items-center py-12 sm:py-16">
          <div className="w-full">
            <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/45">Moduli disponibili</p>
                <h2 className="mt-2 text-2xl font-semibold text-white sm:text-3xl">Seleziona il dominio operativo</h2>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/70">
                Moduli operativi: <span className="font-semibold text-white">{activeVisibleModulesCount}</span>
                {" · "}
                Review aperte: <span className="font-semibold text-white">{summary.reviews}</span>
              </div>
            </div>

            {canManageGaiaUsers ? (
              <section className="mb-6 rounded-[28px] border border-white/10 bg-white/5 p-6 backdrop-blur">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-white/45">Amministrazione GAIA</p>
                    <h3 className="mt-2 text-2xl font-semibold text-white">Utenti applicativi e permessi piattaforma</h3>
                    <p className="mt-3 max-w-3xl text-sm leading-6 text-white/70">
                      Sezione distinta dai moduli NAS. Qui gestisci gli utenti interni di GAIA, i ruoli applicativi e gli accessi alle sezioni della piattaforma.
                    </p>
                  </div>
                  <Link
                    href="/gaia/users"
                    className="inline-flex items-center justify-center rounded-2xl border border-white/15 bg-white/10 px-5 py-3 text-sm font-medium text-white transition hover:bg-white/15"
                  >
                    Apri utenti GAIA
                  </Link>
                </div>
              </section>
            ) : null}

            <div className="grid gap-5 lg:grid-cols-3">
              {visibleModules.map((moduleItem) => {
                const isActive = moduleItem.status === "active";
                const cardContent = (
                  <article
                    className={cn(
                      "flex h-full min-h-[320px] flex-col rounded-[28px] border p-7 transition duration-200",
                      moduleItem.accentClassName,
                      isActive ? "cursor-pointer hover:-translate-y-1" : "cursor-not-allowed opacity-70",
                    )}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p
                          className={cn(
                            "inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]",
                            isActive ? "bg-white/15 text-white/85" : "bg-black/5 text-gray-500",
                          )}
                        >
                          {moduleItem.subtitle}
                        </p>
                        <h3 className="mt-5 text-3xl font-semibold tracking-tight">{moduleItem.title}</h3>
                      </div>
                      <span
                        className={cn(
                          "rounded-full px-3 py-1 text-xs font-medium",
                          isActive ? "bg-[#9BD3A7] text-[#0E1712]" : "bg-gray-200 text-gray-600",
                        )}
                      >
                        {moduleItem.statusLabel}
                      </span>
                    </div>

                    <p className={cn("mt-6 text-sm leading-6", isActive ? "text-white/78" : "text-gray-600")}>
                      {moduleItem.description}
                    </p>

                    {moduleItem.id === "accessi" ? (
                      <div className="mt-8 space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
                            <p className="text-xs uppercase tracking-[0.16em] text-white/55">Share</p>
                            <p className="mt-2 text-2xl font-semibold text-white">{summary.shares}</p>
                          </div>
                          <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
                            <p className="text-xs uppercase tracking-[0.16em] text-white/55">Sync run</p>
                            <p className="mt-2 text-2xl font-semibold text-white">{summary.sync_runs}</p>
                          </div>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
                          <p className="text-xs uppercase tracking-[0.16em] text-white/55">Dominio</p>
                          <p className="mt-2 text-sm font-semibold text-white">
                            {canAccessUsersSection ? "Utenti, gruppi e share NAS" : "Gruppi, share e review NAS"}
                          </p>
                        </div>
                      </div>
                    ) : moduleItem.id === "catasto" ? (
                      <div className="mt-8 grid grid-cols-2 gap-3">
                        <div className="rounded-2xl border border-[#7A3E0B]/10 bg-white/70 p-4">
                          <p className="text-xs uppercase tracking-[0.16em] text-[#7A3E0B]/70">Flusso</p>
                          <p className="mt-2 text-sm font-semibold text-[#7A3E0B]">Batch e visure singole</p>
                        </div>
                        <div className="rounded-2xl border border-[#7A3E0B]/10 bg-white/70 p-4">
                          <p className="text-xs uppercase tracking-[0.16em] text-[#7A3E0B]/70">Output</p>
                          <p className="mt-2 text-sm font-semibold text-[#7A3E0B]">PDF, ZIP e archivio</p>
                        </div>
                      </div>
                    ) : (
                      <div className="mt-8 rounded-2xl border border-dashed border-black/10 bg-black/5 p-4 text-sm text-gray-500">
                        Modulo predisposto nello scaffold GAIA, non ancora attivato in produzione.
                      </div>
                    )}

                    <div className="mt-auto pt-8">
                      {moduleItem.id === "accessi" ? (
                        <Link
                          href={moduleItem.href}
                          className="inline-flex items-center gap-2 text-sm font-medium text-white"
                        >
                          Apri modulo
                          <span aria-hidden="true">→</span>
                        </Link>
                      ) : (
                        <span
                          className={cn(
                            "inline-flex items-center gap-2 text-sm font-medium",
                            isActive ? "text-white" : "text-gray-500",
                          )}
                        >
                          {isActive ? "Apri modulo" : "Disponibile prossimamente"}
                          <span aria-hidden="true">{isActive ? "→" : "·"}</span>
                        </span>
                      )}
                    </div>
                  </article>
                );

                if (!isActive) {
                  return <div key={moduleItem.id}>{cardContent}</div>;
                }

                if (moduleItem.id === "accessi") {
                  return (
                    <div key={moduleItem.id} className="block h-full">
                      {cardContent}
                    </div>
                  );
                }

                return (
                  <Link key={moduleItem.id} href={moduleItem.href} className="block h-full">
                    {cardContent}
                  </Link>
                );
              })}
            </div>
          </div>
        </section>

        <footer className="flex flex-col gap-2 border-t border-white/10 pt-6 text-xs text-white/45 sm:flex-row sm:items-center sm:justify-between">
          <p>GAIA platform · Consorzio di Bonifica dell&apos;Oristanese</p>
          <p>Versione NAS Control v0.1.0</p>
        </footer>
      </div>
    </main>
  );
}
