"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  ChevronRightIcon,
  DocumentIcon,
  FolderIcon,
  GridIcon,
  ServerIcon,
  UserIcon,
  UsersIcon,
} from "@/components/ui/icons";
import { getCurrentUser, getDashboardSummary, getMyPermissions, isAuthError } from "@/lib/api";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { hasSectionAccess } from "@/lib/section-access";
import type { CurrentUser, DashboardSummary } from "@/types/api";

type ModuleStatus = "active" | "warming" | "coming";
type ModuleId = "accessi" | "rete" | "inventario" | "catasto" | "anagrafica";

type HomeModuleMetric = {
  label: string;
  value: string | number;
  tone?: "default" | "accent" | "muted";
};

type HomeModule = {
  id: ModuleId;
  title: string;
  subtitle: string;
  description: string;
  href: string;
  status: ModuleStatus;
  statusLabel: string;
  eyebrow: string;
  icon: typeof FolderIcon;
  accent: string;
  surfaceClassName: string;
  metricCardsClassName: string;
  actionLabel: string;
  metrics: HomeModuleMetric[];
};

const emptySummary: DashboardSummary = {
  nas_users: 0,
  nas_groups: 0,
  shares: 0,
  reviews: 0,
  snapshots: 0,
  sync_runs: 0,
};

function resolveModuleKey(id: ModuleId): string {
  switch (id) {
    case "accessi":
      return "accessi";
    case "rete":
      return "rete";
    case "inventario":
      return "inventario";
    case "catasto":
      return "catasto";
    case "anagrafica":
      return "anagrafica";
    default:
      return id;
  }
}

function formatCompactValue(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

function HomePageSkeleton({ loadError }: { loadError: string | null }) {
  return (
    <main className="auth-shell">
      <section className="auth-card">
        <p className="mb-2 inline-flex rounded-full bg-[#EAF3E8] px-3 py-1 text-xs font-medium text-[#1D4E35]">
          Reindirizzamento
        </p>
        <h1 className="page-heading">Verifica sessione</h1>
        <p className="mt-2 text-sm text-gray-500">Controllo credenziali locali e connessione al backend.</p>
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
    return <HomePageSkeleton loadError={loadError} />;
  }

  const canManageGaiaUsers =
    (currentUser.role === "admin" || currentUser.role === "super_admin")
    && currentUser.enabled_modules.includes("accessi")
    && hasSectionAccess(grantedSectionKeys, "accessi.users");

  const modules: HomeModule[] = [
    {
      id: "accessi",
      title: "GAIA NAS Control",
      subtitle: "Controllo accessi e permessi",
      eyebrow: "Dominio operativo",
      description:
        "Utenti, gruppi, cartelle condivise, permessi effettivi e workflow di review del NAS Synology in un’unica cabina di regia.",
      href: "/nas-control",
      status: "active",
      statusLabel: "Operativo",
      icon: FolderIcon,
      accent: "#1a3d2e",
      surfaceClassName:
        "border-[#24553f]/30 bg-[radial-gradient(circle_at_top_left,rgba(155,211,167,0.2),transparent_30%),linear-gradient(180deg,#1c4633_0%,#163526_100%)] text-white shadow-[0_28px_80px_rgba(18,54,39,0.34)]",
      metricCardsClassName: "border-white/10 bg-black/10 text-white",
      actionLabel: "Apri NAS Control",
      metrics: [
        { label: "Share monitorate", value: formatCompactValue(summary.shares), tone: "accent" },
        { label: "Sync run", value: formatCompactValue(summary.sync_runs), tone: "default" },
        { label: "Review aperte", value: formatCompactValue(summary.reviews), tone: "muted" },
      ],
    },
    {
      id: "rete",
      title: "GAIA Rete",
      subtitle: "Monitoraggio LAN",
      eyebrow: "Dominio operativo",
      description:
        "Scansione dispositivi, mappa per piano, alert operativi e controllo dello stato rete con visualizzazioni immediate.",
      href: "/network",
      status: "active",
      statusLabel: "Operativo",
      icon: ServerIcon,
      accent: "#0b6b61",
      surfaceClassName:
        "border-[#84d5c7]/40 bg-[radial-gradient(circle_at_top_left,rgba(11,107,97,0.1),transparent_28%),linear-gradient(180deg,#fbfffe_0%,#edf9f5_100%)] text-gray-900 shadow-[0_24px_64px_rgba(12,102,92,0.12)]",
      metricCardsClassName: "border-[#cdebe3] bg-white/80 text-gray-900",
      actionLabel: "Apri GAIA Rete",
      metrics: [
        { label: "Asset attesi", value: "LAN", tone: "accent" },
        { label: "Vista", value: "Alert + mappe", tone: "default" },
        { label: "Modalità", value: "Live monitor", tone: "muted" },
      ],
    },
    {
      id: "inventario",
      title: "GAIA Inventario",
      subtitle: "Registro asset IT",
      eyebrow: "Roadmap applicativa",
      description:
        "Registro centralizzato di device, garanzie, assegnazioni e import da CSV. Struttura pronta, attivazione funzionale in corso.",
      href: "/inventory",
      status: "coming",
      statusLabel: "In sviluppo",
      icon: GridIcon,
      accent: "#8d6c2e",
      surfaceClassName:
        "border-dashed border-[#d6c28d] bg-[linear-gradient(135deg,rgba(255,248,231,0.95),rgba(255,255,255,0.96))] text-gray-900 shadow-[0_16px_40px_rgba(141,108,46,0.08)]",
      metricCardsClassName: "border-[#eadcbc] bg-white/85 text-gray-900",
      actionLabel: "Disponibile prossimamente",
      metrics: [
        { label: "Stato", value: "Scaffold pronto", tone: "accent" },
        { label: "Output", value: "Asset + garanzie", tone: "default" },
      ],
    },
    {
      id: "catasto",
      title: "GAIA Catasto",
      subtitle: "Servizi Agenzia Entrate",
      eyebrow: "Dominio operativo",
      description:
        "Batch CSV, visure singole, CAPTCHA, ZIP e archivio documentale con una pipeline costruita per l’operatività quotidiana.",
      href: "/catasto",
      status: "active",
      statusLabel: "Operativo",
      icon: DocumentIcon,
      accent: "#a14f14",
      surfaceClassName:
        "border-[#f0c9aa]/40 bg-[radial-gradient(circle_at_top_left,rgba(161,79,20,0.12),transparent_28%),linear-gradient(180deg,#fffaf6_0%,#fff1e6_100%)] text-gray-900 shadow-[0_24px_64px_rgba(161,79,20,0.1)]",
      metricCardsClassName: "border-[#f1d9c5] bg-white/85 text-gray-900",
      actionLabel: "Apri GAIA Catasto",
      metrics: [
        { label: "Flusso", value: "Batch + singole", tone: "accent" },
        { label: "Output", value: "PDF e ZIP", tone: "default" },
        { label: "Ambiente", value: "SISTER", tone: "muted" },
      ],
    },
    {
      id: "anagrafica",
      title: "GAIA Anagrafica",
      subtitle: "Registro soggetti e documenti",
      eyebrow: "Attivazione controllata",
      description:
        "Gestione soggetti, documenti collegati al NAS e correlazioni con Catasto. Modulo pronto all’uso con rollout progressivo.",
      href: "/anagrafica",
      status: "warming",
      statusLabel: "In attivazione",
      icon: UsersIcon,
      accent: "#325c72",
      surfaceClassName:
        "border-[#c7deea]/50 bg-[radial-gradient(circle_at_top_left,rgba(50,92,114,0.12),transparent_28%),linear-gradient(180deg,#f7fbfd_0%,#eef6fa_100%)] text-gray-900 shadow-[0_24px_64px_rgba(50,92,114,0.1)]",
      metricCardsClassName: "border-[#d7e8f0] bg-white/85 text-gray-900",
      actionLabel: "Apri GAIA Anagrafica",
      metrics: [
        { label: "Dominio", value: "Soggetti + NAS", tone: "accent" },
        { label: "Ricerca", value: "Operativa", tone: "default" },
        { label: "Stato", value: "Rollout", tone: "muted" },
      ],
    },
  ];

  const visibleModules = modules.filter((moduleItem) => {
    if (moduleItem.status === "coming") {
      return true;
    }
    return currentUser.enabled_modules.includes(resolveModuleKey(moduleItem.id));
  });

  const liveModules = visibleModules.filter((moduleItem) => moduleItem.status === "active").length;
  const highlightedStats = [
    { label: "Share presidiate", value: formatCompactValue(summary.shares), copy: "Domini e cartelle condivise monitorate" },
    { label: "Sync run", value: formatCompactValue(summary.sync_runs), copy: "Ultime esecuzioni del connettore NAS" },
    { label: "Review aperte", value: formatCompactValue(summary.reviews), copy: "Richieste che richiedono una decisione" },
  ];

  const statusClassName: Record<ModuleStatus, string> = {
    active: "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-200",
    warming: "bg-amber-100 text-amber-800 ring-1 ring-amber-200",
    coming: "bg-slate-200 text-slate-700 ring-1 ring-slate-300",
  };

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f6fbf7_0%,#eef4ef_46%,#f7f6f2_100%)] text-[#15211b]">
      <div className="mx-auto flex min-h-screen max-w-[1440px] flex-col px-5 py-5 sm:px-8 lg:px-10 xl:px-12">
        <header className="relative overflow-hidden rounded-[36px] border border-[#d8e7dc] bg-[radial-gradient(circle_at_top_left,rgba(92,164,116,0.2),transparent_26%),linear-gradient(135deg,#173627_0%,#204a35_52%,#10271d_100%)] px-6 py-7 text-white shadow-[0_36px_120px_rgba(17,45,31,0.22)] sm:px-8 sm:py-8 lg:px-10">
          <div className="absolute right-0 top-0 h-48 w-48 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.14),transparent_68%)]" />
          <div className="relative flex flex-col gap-8 xl:flex-row xl:items-start xl:justify-between">
            <div className="max-w-4xl">
              <div className="inline-flex items-center gap-3 rounded-full border border-white/15 bg-white/8 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.28em] text-[#d8f4df]">
                <span className="h-2 w-2 rounded-full bg-[#9bd3a7]" />
                GAIA
              </div>
              <h1 className="mt-6 max-w-4xl font-serif text-4xl font-semibold leading-[0.96] tracking-[-0.04em] text-white sm:text-5xl lg:text-6xl">
                Gestione Apparati Informativi
              </h1>
              <p className="mt-5 max-w-3xl text-sm leading-7 text-white/76 sm:text-base">
                Piattaforma IT governance del Consorzio di Bonifica dell&apos;Oristanese. NAS, servizi catastali,
                monitoraggio rete, inventario e anagrafica convergono in una home unica, leggibile e operativa.
              </p>

              <div className="mt-8 grid gap-4 sm:grid-cols-3">
                {highlightedStats.map((item) => (
                  <div
                    key={item.label}
                    className="rounded-[24px] border border-white/10 bg-white/8 px-4 py-4 backdrop-blur-sm"
                  >
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-white/55">{item.label}</p>
                    <p className="mt-3 text-4xl font-semibold tracking-[-0.05em] text-white sm:text-[2.7rem]">{item.value}</p>
                    <p className="mt-2 text-xs leading-5 text-white/65">{item.copy}</p>
                  </div>
                ))}
              </div>
            </div>

            <aside className="w-full max-w-[360px] rounded-[30px] border border-white/12 bg-[linear-gradient(180deg,rgba(255,255,255,0.12),rgba(255,255,255,0.05))] p-5 backdrop-blur xl:p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-white/45">Sessione attiva</p>
                  <p className="mt-3 text-xl font-semibold text-white">{currentUser.username}</p>
                  <p className="mt-1 break-all text-sm text-white/64">{currentUser.email}</p>
                </div>
                <button
                  className="rounded-full border border-white/15 bg-white/5 px-3 py-2 text-xs font-medium text-white transition hover:border-white/30 hover:bg-white/12 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/35"
                  onClick={handleLogout}
                  type="button"
                >
                  Logout
                </button>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <div className="rounded-[22px] border border-white/10 bg-black/10 p-4">
                  <p className="text-[10px] uppercase tracking-[0.22em] text-white/45">Ente</p>
                  <p className="mt-2 text-sm font-medium text-white">Consorzio di Bonifica</p>
                  <p className="text-sm text-white/72">dell&apos;Oristanese</p>
                </div>
                <div className="rounded-[22px] border border-white/10 bg-black/10 p-4">
                  <p className="text-[10px] uppercase tracking-[0.22em] text-white/45">Ruolo</p>
                  <p className="mt-2 text-sm font-medium text-white">{currentUser.role}</p>
                  <p className="text-sm text-white/72">{liveModules} moduli operativi visibili</p>
                </div>
              </div>

              {canManageGaiaUsers ? (
                <Link
                  href="/gaia/users"
                  className="mt-5 inline-flex w-full items-center justify-between rounded-[22px] border border-white/12 bg-white px-4 py-4 text-sm font-medium text-[#173627] transition hover:bg-[#f3fbf5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/35"
                >
                  <span>
                    Utenti applicativi
                    <span className="mt-1 block text-xs text-[#4e6858]">Gestione account, ruoli e abilitazioni</span>
                  </span>
                  <ChevronRightIcon className="h-4 w-4" />
                </Link>
              ) : null}
            </aside>
          </div>
        </header>

        <section className="pt-8">
          <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#5f7669]">Pannello moduli</p>
              <h2 className="mt-2 font-serif text-3xl font-semibold tracking-[-0.04em] text-[#1b2b22] sm:text-[2.45rem]">
                Seleziona il dominio operativo
              </h2>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#d4e3d8] bg-white px-4 py-2 text-sm text-[#446254] shadow-[0_10px_30px_rgba(28,64,43,0.06)]">
              <span className="h-2 w-2 rounded-full bg-[#1a8f53]" />
              {liveModules} moduli operativi disponibili · {summary.reviews} review aperte
            </div>
          </div>

          {canManageGaiaUsers ? (
            <section className="mb-6 overflow-hidden rounded-[32px] border border-[#d9e8de] bg-[radial-gradient(circle_at_top_right,rgba(26,61,46,0.08),transparent_30%),linear-gradient(180deg,#ffffff_0%,#f6fbf7_100%)] p-6 shadow-[0_24px_70px_rgba(24,61,46,0.08)] sm:p-7">
              <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
                <div className="max-w-3xl">
                  <div className="inline-flex items-center gap-2 rounded-full bg-[#eaf3ed] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#29533d]">
                    <UserIcon className="h-3.5 w-3.5" />
                    Amministrazione GAIA
                  </div>
                  <h3 className="mt-4 font-serif text-3xl font-semibold tracking-[-0.04em] text-[#183526]">
                    Utenti applicativi e permessi piattaforma
                  </h3>
                  <p className="mt-3 max-w-2xl text-sm leading-7 text-[#577061]">
                    Area distinta dal dominio NAS. Qui governi accessi interni, ruoli, abilitazioni di sezione e ciclo di vita degli utenti applicativi.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[360px]">
                  <div className="rounded-[24px] border border-[#d8e6dd] bg-white p-4">
                    <p className="text-[10px] uppercase tracking-[0.22em] text-[#78917f]">Governance</p>
                    <p className="mt-2 text-lg font-semibold text-[#163627]">Ruoli, moduli e visibilità</p>
                  </div>
                  <Link
                    href="/gaia/users"
                    className="inline-flex items-center justify-between rounded-[24px] border border-[#204a35] bg-[#173627] px-5 py-4 text-sm font-medium text-white transition hover:bg-[#10291d] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#173627]/30"
                  >
                    <span>Apri utenti GAIA</span>
                    <ChevronRightIcon className="h-4 w-4" />
                  </Link>
                </div>
              </div>
            </section>
          ) : null}

          <div className="grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
            {visibleModules.map((moduleItem) => {
              const Icon = moduleItem.icon;
              const isInteractive = moduleItem.status !== "coming";
              const isDarkSurface = moduleItem.id === "accessi";
              const cardContent = (
                <article
                  className={cn(
                    "relative flex h-full min-h-[380px] flex-col overflow-hidden rounded-[30px] border px-6 py-6 transition duration-300",
                    moduleItem.surfaceClassName,
                    isInteractive
                      ? "cursor-pointer hover:-translate-y-1.5 hover:shadow-[0_32px_90px_rgba(17,45,31,0.16)] focus-visible:outline-none"
                      : "cursor-default",
                  )}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p
                        className={cn(
                          "inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em]",
                          moduleItem.status === "active"
                            ? "bg-white/10 text-inherit"
                            : "bg-white/70 text-[#4b5f54]",
                        )}
                      >
                        {moduleItem.eyebrow}
                      </p>
                      <div className="mt-5 flex items-start gap-4">
                        <div
                          className={cn(
                            "flex h-14 w-14 shrink-0 items-center justify-center rounded-[18px] ring-1",
                            moduleItem.status === "active"
                              ? "bg-white/10 ring-white/10"
                              : "bg-white/80 ring-black/5",
                          )}
                        >
                          <Icon className="h-7 w-7" />
                        </div>
                        <div className="min-w-0">
                          <p className={cn("text-sm font-medium", moduleItem.status === "active" ? "text-white/68" : "text-[#5c7064]")}>
                            {moduleItem.subtitle}
                          </p>
                          <h3 className="mt-1 font-serif text-[2rem] font-semibold leading-[1] tracking-[-0.045em]">
                            {moduleItem.title}
                          </h3>
                        </div>
                      </div>
                    </div>

                    <span className={cn("shrink-0 rounded-full px-3 py-1 text-xs font-semibold", statusClassName[moduleItem.status])}>
                      {moduleItem.statusLabel}
                    </span>
                  </div>

                  <p className={cn("mt-6 text-sm leading-7", moduleItem.status === "active" ? "text-white/76" : "text-[#596e62]")}>
                    {moduleItem.description}
                  </p>

                  <div className="mt-7 grid gap-3 sm:grid-cols-2">
                    {moduleItem.metrics.map((metric) => (
                      <div
                        key={`${moduleItem.id}-${metric.label}`}
                        className={cn(
                          "min-h-[112px] rounded-[22px] border p-4",
                          moduleItem.metricCardsClassName,
                          metric.tone === "accent"
                            ? moduleItem.status === "active"
                              ? "shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]"
                              : "shadow-[0_10px_30px_rgba(12,35,22,0.04)]"
                            : "",
                        )}
                      >
                        <p
                          className={cn(
                            "text-[10px] font-semibold uppercase tracking-[0.22em]",
                            isDarkSurface ? "text-white/50" : "text-[#72877a]",
                          )}
                        >
                          {metric.label}
                        </p>
                        <p
                          className={cn(
                            "mt-3 text-2xl font-semibold tracking-[-0.04em]",
                            isDarkSurface
                              ? metric.tone === "accent"
                                ? "text-white"
                                : "text-white/88"
                              : metric.tone === "accent"
                                ? "text-[#173627]"
                                : "text-[#345144]",
                          )}
                        >
                          {metric.value}
                        </p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-auto pt-8">
                    <div
                      className={cn(
                        "inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium",
                        isInteractive
                          ? "bg-[rgb(160,87,38)] text-white"
                          : "border border-dashed border-[#cdbd90] bg-white/80 text-[#75653a]",
                      )}
                    >
                      <span>{moduleItem.actionLabel}</span>
                      <span aria-hidden="true">{isInteractive ? "→" : "·"}</span>
                    </div>
                  </div>
                </article>
              );

              if (!isInteractive) {
                return <div key={moduleItem.id}>{cardContent}</div>;
              }

              return (
                <Link
                  key={moduleItem.id}
                  href={moduleItem.href}
                  className="block h-full rounded-[30px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#173627]/30"
                >
                  {cardContent}
                </Link>
              );
            })}
          </div>
        </section>

        <footer className="mt-10 flex flex-col gap-2 border-t border-[#dbe7de] pt-6 text-xs text-[#61786c] sm:flex-row sm:items-center sm:justify-between">
          <p>© GAIA platform · Consorzio di Bonifica dell&apos;Oristanese</p>
          <p>Versione NAS Control v0.1.0</p>
        </footer>
      </div>
    </main>
  );
}
