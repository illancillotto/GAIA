"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AlertBanner } from "@/components/ui/alert-banner";
import { login } from "@/lib/api";
import { getStoredAccessToken, setStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";

const modules = [
  { name: "GAIA NAS Control", icon: "storage", status: "Operativo", active: true },
  { name: "GAIA Catasto", icon: "account_balance", status: "Operativo", active: true },
  { name: "GAIA Rete", icon: "hub", status: "Operativo", active: true },
  { name: "GAIA Utenze", icon: "badge", status: "Operativo", active: true },
  { name: "GAIA Inventario", icon: "inventory_2", status: "In sviluppo", active: false },
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
    <div className="min-h-screen flex flex-col bg-surface text-on-surface font-body">
      {/* TopAppBar */}
      <header className="bg-surface fixed top-0 w-full z-50">
        <div className="flex justify-between items-center w-full px-8 py-4 max-w-screen-2xl mx-auto">
          <span className="font-headline text-2xl font-bold tracking-tight text-primary">GAIA</span>
          <nav className="hidden md:flex gap-8 items-center">
            <span className="font-body font-medium text-outline">home GAIA</span>
            <span className="font-body font-medium text-outline">Moduli</span>
            <span className="font-body font-medium text-outline">Supporto</span>
            <span className="font-body font-medium text-outline">Documentazione</span>
            <span className="bg-primary text-on-primary px-6 py-2 rounded-lg font-medium text-sm">
              Accesso 
            </span>
          </nav>
        </div>
        <div className="bg-surface-container h-[1px] w-full" />
      </header>

      {/* Main */}
      <main className="flex-grow flex items-stretch pt-[73px]">
        {/* Left panel: modules showcase */}
        <section className="hidden lg:flex w-5/12 bg-surface-container-low flex-col justify-center px-16 relative overflow-hidden">
          {/* Decorative texture */}
          <div className="absolute inset-0 opacity-10 pointer-events-none" aria-hidden>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              className="w-full h-full object-cover"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuA6M5oi-qG40LeL5NWjBJwibCrQ8BXn8LGKkMwotR_pdSguPPpMSgoKdzBleRVbhSRxzxadlrtTPFCJAznIqeZAg1NVhaMd2-NcTe12Cdg-ZkOamN_HIMAPq5D_4-ko3BgsCLGoCZpg3ouo4BmuTbegh4egXQp8JERy-CZiBr5BWxhdZGDTr6fqBaxVcOHb-pk6nDgdfUHJKnGEQ2nwZWmt7Jnft00SN3AUvZNM4hnDb7vHsiSVVGFO1fZSfqqePPMHyR1GdeOguEJs"
              alt=""
            />
          </div>

          <div className="relative z-10">
            <h2 className="font-headline text-5xl font-bold text-primary mb-6 leading-tight">
              Ecosistema Integrato
            </h2>
            <p className="text-on-surface-variant text-lg mb-12 max-w-md font-light leading-relaxed">
              GAIA centralizza la governance IT del Consorzio in moduli integrati, accessibili da un&apos;unica
              interfaccia dopo il login.
            </p>

            <div className="space-y-6">
              {modules.map((mod) => (
                <div key={mod.name} className="flex items-center justify-between group">
                  <div className="flex items-center gap-4">
                    <span className="material-symbols-outlined text-outline text-3xl group-hover:text-primary transition-colors">
                      {mod.icon}
                    </span>
                    <span className="font-headline text-xl text-primary font-medium">{mod.name}</span>
                  </div>
                  <span
                    className={cn(
                      "px-3 py-1 rounded-full text-[10px] tracking-widest uppercase font-bold",
                      mod.active
                        ? "bg-primary-fixed text-on-primary-fixed"
                        : "bg-tertiary-fixed-dim text-on-tertiary-fixed-variant",
                    )}
                  >
                    {mod.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Right panel: login form */}
        <section className="flex-grow flex flex-col justify-center items-center px-6 bg-surface">
          <div className="w-full max-w-md">
            <div className="mb-12 text-center lg:text-left">
              <span className="font-label text-[10px] tracking-[0.2em] uppercase text-outline font-semibold mb-2 block">
                Identità e Accesso
              </span>
              <h1 className="font-headline text-4xl font-bold text-primary mb-4 tracking-tight">
                Accesso
              </h1>
              <p className="text-on-surface-variant font-light">
                Inserisci le tue credenziali autorizzate per accedere al sistema di governance.
              </p>
            </div>

            {error ? (
              <div className="mb-6">
                <AlertBanner variant="danger" title="Accesso non riuscito">
                  {error}
                </AlertBanner>
              </div>
            ) : null}

            <form
              className={cn("space-y-8", error ? "animate-login-shake" : "")}
              onSubmit={(event) => void handleSubmit(event)}
              noValidate
            >
              {/* Username */}
              <div className="space-y-2">
                <label
                  className="font-label text-[10px] tracking-widest uppercase text-outline font-bold"
                  htmlFor="username"
                >
                  Username o email
                </label>
                <div className="relative group">
                  <input
                    id="username"
                    name="username"
                    type="text"
                    placeholder="m.rossi@consorzio.it"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    aria-invalid={usernameHasError}
                    className={cn(
                      "w-full bg-surface-container-lowest border-0 ring-1 py-4 px-4 pr-12 rounded transition-all text-on-surface outline-none",
                      usernameHasError
                        ? "ring-error focus:ring-2 focus:ring-error"
                        : "ring-outline-variant/30 focus:ring-2 focus:ring-primary",
                    )}
                  />
                  <span
                    className="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-outline group-focus-within:text-primary transition-colors select-none pointer-events-none"
                    aria-hidden
                  >
                    alternate_email
                  </span>
                </div>
                {usernameHasError ? (
                  <p className="text-sm text-error">Inserisci username o email.</p>
                ) : null}
              </div>

              {/* Password */}
              <div className="space-y-2">
                <label
                  className="font-label text-[10px] tracking-widest uppercase text-outline font-bold"
                  htmlFor="password"
                >
                  Password
                </label>
                <div className="relative group">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    aria-invalid={passwordHasError}
                    className={cn(
                      "w-full bg-surface-container-lowest border-0 ring-1 py-4 px-4 pr-12 rounded transition-all text-on-surface outline-none",
                      passwordHasError
                        ? "ring-error focus:ring-2 focus:ring-error"
                        : "ring-outline-variant/30 focus:ring-2 focus:ring-primary",
                    )}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Nascondi password" : "Mostra password"}
                    className="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-outline hover:text-primary transition-colors"
                  >
                    {showPassword ? "visibility_off" : "visibility"}
                  </button>
                </div>
                {passwordHasError ? (
                  <p className="text-sm text-error">Inserisci la password.</p>
                ) : null}
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-primary text-on-primary py-4 rounded font-medium text-sm tracking-wide transition hover:opacity-90 active:opacity-80 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-3"
              >
                {isSubmitting ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Accesso in corso...
                  </>
                ) : (
                  "Accedi alla piattaforma"
                )}
              </button>
            </form>
          </div>
        </section>
      </main>
    </div>
  );
}
