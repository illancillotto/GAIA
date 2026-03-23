"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AlertBanner } from "@/components/ui/alert-banner";
import { ServerIcon } from "@/components/ui/icons";
import { login } from "@/lib/api";
import { getStoredAccessToken, setStoredAccessToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (getStoredAccessToken()) {
      router.replace("/accessi");
    }
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await login(username, password);
      setStoredAccessToken(response.access_token);
      router.push("/accessi");
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Accesso non riuscito");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="grid w-full max-w-5xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="hidden rounded-3xl bg-[#1D4E35] p-10 text-white shadow-panel lg:block">
          <div className="flex h-full flex-col justify-between">
            <div>
              <div className="mb-6 flex w-fit items-center gap-2 rounded-lg bg-white/10 px-3 py-2">
                <ServerIcon className="h-4 w-4" />
                <span className="text-xs font-medium tracking-wide">NAS AUDIT</span>
              </div>
              <h1 className="text-3xl font-medium leading-tight">
                Audit centralizzato degli accessi al NAS Synology
              </h1>
              <p className="mt-4 max-w-md text-sm leading-6 text-white/80">
                Piattaforma interna per controllo permessi, review responsabili di settore e tracciamento delle sincronizzazioni.
              </p>
            </div>
            <div className="grid gap-4">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-wide text-white/60">Contesto</p>
                <p className="mt-2 text-sm text-white/85">Consorzio di Bonifica dell&apos;Oristanese</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-wide text-white/60">Modalità</p>
                <p className="mt-2 text-sm text-white/85">Accesso in sola lettura con sessione JWT</p>
              </div>
            </div>
          </div>
        </div>

        <section className="auth-card">
          <p className="mb-2 inline-flex rounded-full bg-[#EAF3E8] px-3 py-1 text-xs font-medium text-[#1D4E35]">
            Login applicativo
          </p>
          <h2 className="page-heading">Accesso piattaforma</h2>
          <p className="mt-2 text-sm text-gray-500">
            Inserisci credenziali applicative valide per ottenere un token JWT e accedere al frontend amministrativo.
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

            <button className="btn-primary w-full" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Accesso in corso..." : "Accedi"}
            </button>
          </form>
        </section>
      </section>
    </main>
  );
}
