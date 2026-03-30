"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AlertBanner } from "@/components/ui/alert-banner";
import {
  CheckIcon,
  DocumentIcon,
  EyeIcon,
  EyeOffIcon,
  FolderIcon,
  GridIcon,
  LockIcon,
  ServerIcon,
  UserIcon,
  UsersIcon,
} from "@/components/ui/icons";
import { login } from "@/lib/api";
import { getStoredAccessToken, setStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";

const modules = [
  {
    name: "GAIA NAS Control",
    subtitle: "Controllo accessi, share e permessi Synology",
    status: "Operativo",
    tone: "active" as const,
    icon: FolderIcon,
  },
  {
    name: "GAIA Catasto",
    subtitle: "Workflow visure, ZIP, CAPTCHA e documenti",
    status: "Operativo",
    tone: "active" as const,
    icon: DocumentIcon,
  },
  {
    name: "GAIA Rete",
    subtitle: "Monitoraggio LAN, alert e mappe operative",
    status: "Operativo",
    tone: "active" as const,
    icon: ServerIcon,
  },
  {
    name: "GAIA Anagrafica",
    subtitle: "Ricerca soggetti, documenti e import da archivio",
    status: "Operativo",
    tone: "active" as const,
    icon: UsersIcon,
  },
  {
    name: "GAIA Inventario",
    subtitle: "Registro asset IT, garanzie e CSV",
    status: "In sviluppo",
    tone: "coming" as const,
    icon: GridIcon,
  },
];

const platformBullets = [
  "Un unico accesso per i domini operativi GAIA.",
  "Sessione autenticata con instradamento immediato alla dashboard.",
  "Stesso linguaggio visivo della home e stati applicativi coerenti.",
];

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [didAttemptSubmit, setDidAttemptSubmit] = useState(false);

  useEffect(() => {
    if (getStoredAccessToken()) {
      router.replace("/");
    }
  }, [router]);

  const usernameHasError = didAttemptSubmit && username.trim().length === 0;
  const passwordHasError = didAttemptSubmit && password.trim().length === 0;
  const hasFieldError = usernameHasError || passwordHasError;

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setDidAttemptSubmit(true);
    setError(null);

    if (!username.trim() || !password.trim()) {
      setError("Compila username o email e password per continuare.");
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await login(username.trim(), password);
      setStoredAccessToken(response.access_token);
      router.push("/");
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Accesso non riuscito");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-shell px-4 py-5 sm:px-6 lg:px-8">
      <section className="grid w-full max-w-[1220px] overflow-hidden rounded-[32px] border border-[#dce7df] bg-white/55 shadow-[0_40px_120px_rgba(17,45,31,0.12)] backdrop-blur-sm lg:grid-cols-[1.08fr_0.92fr]">
        <aside className="relative overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(122,179,138,0.18),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(10,46,31,0.65),transparent_30%),linear-gradient(180deg,#173627_0%,#12281d_48%,#0c1913_100%)] px-6 py-7 text-white sm:px-8 sm:py-8 lg:px-10 lg:py-10">
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.04)_0%,transparent_38%,transparent_62%,rgba(255,255,255,0.03)_100%)]" />
          <div className="relative flex h-full flex-col">
            <div className="flex flex-wrap items-center gap-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-[#d6f4dd]">
                <GridIcon className="h-4 w-4" />
                GAIA
              </div>
              <p className="text-sm font-medium text-white/80">Consorzio di Bonifica dell&apos;Oristanese</p>
            </div>

            <div className="mt-8 max-w-2xl">
              <p className="inline-flex rounded-full bg-[rgba(216,244,223,0.12)] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-[#d6f4dd] ring-1 ring-white/10">
                Accesso unificato
              </p>
              <h1 className="mt-6 max-w-xl font-serif text-[2.55rem] font-semibold leading-[0.95] tracking-[-0.045em] text-white sm:text-[3.15rem]">
                Entra nella piattaforma GAIA
              </h1>
              <div className="mt-6 space-y-3">
                {platformBullets.map((item) => (
                  <div key={item} className="flex items-start gap-3 text-sm leading-6 text-white/78 sm:text-[15px]">
                    <span className="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full bg-white/10 text-[#ccefd3] ring-1 ring-white/10">
                      <CheckIcon className="h-3.5 w-3.5" />
                    </span>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-8 grid gap-3">
              {modules.map((moduleItem) => {
                const Icon = moduleItem.icon;
                const isActive = moduleItem.tone === "active";

                return (
                  <div
                    key={moduleItem.name}
                    className={cn(
                      "group flex items-center gap-4 rounded-[24px] border px-4 py-4 transition duration-200",
                      isActive
                        ? "border-[#2b5e45]/55 bg-[linear-gradient(180deg,rgba(29,78,53,0.36)_0%,rgba(19,46,33,0.28)_100%)] hover:-translate-y-0.5 hover:border-[#8ec39d]/38 hover:bg-[linear-gradient(180deg,rgba(34,89,59,0.44)_0%,rgba(19,46,33,0.34)_100%)]"
                        : "border-dashed border-[#8b7d56]/45 bg-[linear-gradient(180deg,rgba(255,255,255,0.05)_0%,rgba(255,255,255,0.03)_100%)]",
                    )}
                  >
                    <div
                      className={cn(
                        "flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ring-1",
                        isActive
                          ? "bg-white/10 text-white ring-white/10"
                          : "bg-[#f3ecdd]/8 text-[#f3d59a] ring-[#cfb778]/35",
                      )}
                    >
                      <Icon className="h-5 w-5" />
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-base font-semibold text-white">{moduleItem.name}</p>
                        <span
                          className={cn(
                            "inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold",
                            isActive
                              ? "bg-[#d9f5df] text-[#12402d]"
                              : "bg-[#f2e3c3]/15 text-[#f1d498] ring-1 ring-[#cfb778]/35",
                          )}
                        >
                          <span
                            className={cn(
                              "h-2 w-2 rounded-full",
                              isActive ? "bg-[#1a8f53] shadow-[0_0_0_4px_rgba(26,143,83,0.18)]" : "bg-[#d0a64d]",
                            )}
                          />
                          {moduleItem.status}
                        </span>
                      </div>
                      <p className={cn("mt-1 text-sm leading-6", isActive ? "text-white/70" : "text-white/62")}>
                        {moduleItem.subtitle}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-auto pt-8">
              <div className="grid gap-4 rounded-[28px] border border-white/10 bg-white/[0.06] p-5 backdrop-blur sm:grid-cols-2">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-white/46">Identità piattaforma</p>
                  <p className="mt-3 text-sm leading-6 text-white/78">
                    GAIA riunisce NAS, rete, servizi catastali e anagrafica in una sola cabina applicativa.
                  </p>
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-white/46">Modalità di accesso</p>
                  <p className="mt-3 text-sm leading-6 text-white/78">
                    Login applicativo con sessione protetta, redirect alla dashboard e navigazione coerente tra moduli.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <section className="flex items-center bg-[radial-gradient(circle_at_top_right,rgba(160,87,38,0.08),transparent_28%),linear-gradient(180deg,#fcfcf8_0%,#f6f7f2_100%)] px-5 py-6 sm:px-8 sm:py-8 lg:px-10 lg:py-10">
          <div
            className={cn(
              "auth-card w-full max-w-none rounded-[28px] border border-[#e3e8e1] bg-white/92 p-6 shadow-[0_24px_70px_rgba(17,45,31,0.08)] backdrop-blur-sm sm:p-8",
              error ? "animate-login-shake" : "",
            )}
          >
            <p className="inline-flex rounded-full bg-[#e1f0e4] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#1b5a3f]">
              Login applicativo
            </p>

            <div className="mt-5">
              <h2 className="font-serif text-[2rem] font-semibold leading-[1.02] tracking-[-0.04em] text-[#173627] sm:text-[2.15rem]">
                Accedi a GAIA
              </h2>
              <p className="mt-3 max-w-lg text-sm leading-7 text-[#607164] sm:text-[15px]">
                Inserisci credenziali valide per entrare nella dashboard operativa e aprire subito i moduli attivi del Consorzio.
              </p>
            </div>

            {error ? (
              <div className="mt-5">
                <AlertBanner variant="danger" title="Accesso non riuscito">
                  {error}
                </AlertBanner>
              </div>
            ) : null}

            <form className="mt-6 space-y-5" onSubmit={(event) => void handleSubmit(event)} noValidate>
              <div>
                <label className="mb-2 block text-sm font-medium text-[#234334]" htmlFor="username">
                  Username o email
                </label>
                <div
                  className={cn(
                    "flex items-center gap-3 rounded-2xl border bg-white px-4 py-3 shadow-[0_1px_0_rgba(17,45,31,0.03)] transition",
                    usernameHasError
                      ? "border-[#cf4e4e] ring-4 ring-[#cf4e4e]/10"
                      : "border-[#d5ddd5] focus-within:border-[#1d4e35] focus-within:ring-4 focus-within:ring-[#1d4e35]/10",
                  )}
                >
                  <UserIcon className={cn("h-5 w-5 shrink-0", usernameHasError ? "text-[#cf4e4e]" : "text-[#6b7d70]")} />
                  <input
                    aria-describedby={usernameHasError ? "username-error" : undefined}
                    aria-invalid={usernameHasError}
                    className="h-7 w-full border-0 bg-transparent p-0 text-sm text-[#15211b] outline-none placeholder:text-[#9cac9f]"
                    id="username"
                    name="username"
                    type="text"
                    placeholder="utente@ente.local"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                  />
                </div>
                {usernameHasError ? (
                  <p className="mt-2 text-sm text-[#b93f3f]" id="username-error">
                    Inserisci username o email.
                  </p>
                ) : null}
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-[#234334]" htmlFor="password">
                  Password
                </label>
                <div
                  className={cn(
                    "flex items-center gap-3 rounded-2xl border bg-white px-4 py-3 shadow-[0_1px_0_rgba(17,45,31,0.03)] transition",
                    passwordHasError
                      ? "border-[#cf4e4e] ring-4 ring-[#cf4e4e]/10"
                      : "border-[#d5ddd5] focus-within:border-[#1d4e35] focus-within:ring-4 focus-within:ring-[#1d4e35]/10",
                  )}
                >
                  <LockIcon className={cn("h-5 w-5 shrink-0", passwordHasError ? "text-[#cf4e4e]" : "text-[#6b7d70]")} />
                  <input
                    aria-describedby={passwordHasError ? "password-error" : "login-helper"}
                    aria-invalid={passwordHasError}
                    className="h-7 w-full border-0 bg-transparent p-0 text-sm text-[#15211b] outline-none placeholder:text-[#9cac9f]"
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                  <button
                    type="button"
                    className="inline-flex h-9 w-9 items-center justify-center rounded-full text-[#607164] transition hover:bg-[#eff5ef] hover:text-[#173627] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1d4e35]/20"
                    onClick={() => setShowPassword((current) => !current)}
                    aria-label={showPassword ? "Nascondi password" : "Mostra password"}
                  >
                    {showPassword ? <EyeOffIcon className="h-4.5 w-4.5" /> : <EyeIcon className="h-4.5 w-4.5" />}
                  </button>
                </div>
                {passwordHasError ? (
                  <p className="mt-2 text-sm text-[#b93f3f]" id="password-error">
                    Inserisci la password.
                  </p>
                ) : null}
              </div>

              <button
                className={cn(
                  "inline-flex w-full items-center justify-center gap-3 rounded-2xl bg-[linear-gradient(180deg,#1d4e35_0%,#143826_100%)] px-5 py-3.5 text-sm font-semibold text-white shadow-[0_16px_34px_rgba(23,54,39,0.16)] transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#1d4e35]/28 disabled:cursor-not-allowed disabled:opacity-70",
                  isSubmitting ? "translate-y-0" : "hover:-translate-y-0.5 hover:shadow-[0_22px_44px_rgba(23,54,39,0.22)]",
                  hasFieldError ? "ring-2 ring-[#cf4e4e]/12" : "",
                )}
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <span className="h-4.5 w-4.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Accesso in corso...
                  </>
                ) : (
                  "Accedi alla piattaforma"
                )}
              </button>
            </form>

            <div
              className="mt-5 rounded-[22px] border border-[#e6ece4] bg-[#f7faf6] px-4 py-4 text-sm leading-6 text-[#67786b]"
              id="login-helper"
            >
              Dopo il login verrai indirizzato alla <span className="font-semibold text-[#173627]">home GAIA</span>, con accesso immediato ai moduli operativi e alla sessione utente centralizzata.
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}
