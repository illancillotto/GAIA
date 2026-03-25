"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AlertBanner } from "@/components/ui/alert-banner";
import { GridIcon, ServerIcon } from "@/components/ui/icons";
import { login } from "@/lib/api";
import { getStoredAccessToken, setStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";

const modules = [
  {
    name: "GAIA Accessi",
    subtitle: "NAS Audit",
    status: "Operativo",
    tone: "active" as const,
  },
  {
    name: "GAIA Catasto",
    subtitle: "Servizi AdE",
    status: "Operativo",
    tone: "active" as const,
  },
  {
    name: "GAIA Rete",
    subtitle: "Network Monitor",
    status: "In sviluppo",
    tone: "coming" as const,
  },
  {
    name: "GAIA Inventario",
    subtitle: "IT Inventory",
    status: "In sviluppo",
    tone: "coming" as const,
  },
];

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (getStoredAccessToken()) {
      router.replace("/");
    }
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await login(username, password);
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
    <main className="auth-shell">
      <section className="grid w-full max-w-6xl gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-[2rem] border border-[#1D4E35]/10 bg-[#0F1913] p-8 text-white shadow-[0_30px_80px_rgba(15,25,19,0.18)] lg:p-10">
          <div className="flex h-full flex-col">
            <div className="flex flex-wrap items-center gap-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/8 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-[#A8D5B2]">
                <GridIcon className="h-4 w-4" />
                GAIA Platform
              </div>
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/6 px-3 py-1.5 text-xs text-white/65">
                <ServerIcon className="h-3.5 w-3.5" />
                Consorzio di Bonifica dell&apos;Oristanese
              </div>
            </div>

            <div className="mt-8 max-w-2xl">
              <p className="text-sm font-medium uppercase tracking-[0.22em] text-[#7AB38A]">
                Accesso unificato
              </p>
              <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight lg:text-[3.25rem]">
                Entra nella piattaforma GAIA
              </h1>
              <p className="mt-5 max-w-xl text-base leading-7 text-white/72">
                Un unico punto di ingresso per audit accessi, servizi catastali, monitoraggio rete e inventario IT.
                I moduli GAIA Accessi e GAIA Catasto sono operativi; gli altri moduli sono gia predisposti nello scaffold applicativo.
              </p>
            </div>

            <div className="mt-10 grid gap-3">
              {modules.map((moduleItem) => (
                <div
                  key={moduleItem.name}
                  className={cn(
                    "flex items-center justify-between rounded-2xl border px-4 py-4",
                    moduleItem.tone === "active"
                      ? "border-[#1D4E35]/30 bg-[#1D4E35]/22"
                      : "border-white/8 bg-white/[0.04]",
                  )}
                >
                  <div>
                    <p className="text-base font-semibold text-white">{moduleItem.name}</p>
                    <p className="mt-1 text-sm text-white/62">{moduleItem.subtitle}</p>
                  </div>
                  <span
                    className={cn(
                      "rounded-full px-3 py-1 text-xs font-medium",
                      moduleItem.tone === "active"
                        ? "bg-[#9BD3A7] text-[#0F1913]"
                        : "bg-white/10 text-white/68",
                    )}
                  >
                    {moduleItem.status}
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-auto grid gap-4 pt-8 sm:grid-cols-2">
              <div className="rounded-2xl border border-white/8 bg-white/[0.04] p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-white/45">Identità</p>
                <p className="mt-2 text-sm leading-6 text-white/76">
                  Gestione Apparati Informativi e Accessi in un’unica piattaforma IT governance.
                </p>
              </div>
              <div className="rounded-2xl border border-white/8 bg-white/[0.04] p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-white/45">Modalità</p>
                <p className="mt-2 text-sm leading-6 text-white/76">
                  Accesso autenticato con sessione JWT e navigazione applicativa centralizzata.
                </p>
              </div>
            </div>
          </div>
        </div>

        <section className="auth-card border-white/70 bg-white/92 backdrop-blur">
          <p className="mb-2 inline-flex rounded-full bg-[#EAF3E8] px-3 py-1 text-xs font-medium text-[#1D4E35]">
            Login applicativo
          </p>
          <h2 className="page-heading">Accedi a GAIA</h2>
          <p className="mt-2 text-sm leading-6 text-gray-500">
            Inserisci credenziali applicative valide per accedere alla piattaforma e aprire il modulo operativo.
          </p>

          {error ? (
            <div className="mt-5">
              <AlertBanner variant="danger" title="Accesso non riuscito">
                {error}
              </AlertBanner>
            </div>
          ) : null}

          <form className="mt-6 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
            <label className="block text-sm font-medium text-gray-700" htmlFor="username">
              Username o email
              <input
                className="form-control mt-1"
                id="username"
                name="username"
                type="text"
                placeholder="utente@ente.local"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </label>

            <label className="block text-sm font-medium text-gray-700" htmlFor="password">
              Password
              <input
                className="form-control mt-1"
                id="password"
                name="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>

            <button className="btn-primary mt-2 w-full" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Accesso in corso..." : "Accedi alla piattaforma"}
            </button>
          </form>

          <div className="mt-6 rounded-2xl border border-gray-100 bg-[#F6F7F2] px-4 py-3 text-xs leading-5 text-gray-500">
            Dopo il login verrai indirizzato alla <span className="font-semibold text-[#1D4E35]">home GAIA</span>,
            da cui potrai aprire i moduli operativi Accessi e Catasto.
          </div>
        </section>
      </section>
    </main>
  );
}
