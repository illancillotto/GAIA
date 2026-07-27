"use client";

import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { AlertBanner } from "@/components/ui/alert-banner";
import { confirmPasswordReset, getPasswordResetInfo } from "@/lib/password-reset-api";
import type { PasswordResetInfo } from "@/types/api";

export default function ResetPasswordPage() {
  const params = useParams();
  const router = useRouter();
  const token = typeof params.token === "string" ? params.token : Array.isArray(params.token) ? params.token[0] : "";

  const [info, setInfo] = useState<PasswordResetInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) return;
    getPasswordResetInfo(token)
      .then(setInfo)
      .catch((error: unknown) => setLoadError(error instanceof Error ? error.message : "Link non valido"));
  }, [token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);
    if (password !== confirmPassword) {
      setSubmitError("Le password non coincidono");
      return;
    }
    if (password.length < 8) {
      setSubmitError("La password deve essere di almeno 8 caratteri");
      return;
    }

    setSubmitting(true);
    try {
      await confirmPasswordReset(token, password);
      setDone(true);
    } catch (error: unknown) {
      setSubmitError(error instanceof Error ? error.message : "Ripristino non riuscito");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f5f7f4] p-6">
        <section className="w-full max-w-sm rounded-[28px] border border-emerald-100 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-semibold text-gray-900">Password aggiornata</h1>
          <p className="mt-2 text-sm text-gray-600">Puoi ora accedere a GAIA con la nuova password.</p>
          <button
            className="mt-6 w-full rounded-full bg-[#1D4E35] py-3 text-sm font-semibold text-white transition hover:bg-[#163d2a]"
            onClick={() => router.push("/login")}
            type="button"
          >
            Vai al login
          </button>
        </section>
      </main>
    );
  }

  if (loadError) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f5f7f4] p-6">
        <section className="w-full max-w-sm rounded-[28px] border border-rose-100 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-semibold text-gray-900">Link non valido</h1>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
          <a className="mt-6 block rounded-full bg-[#1D4E35] py-3 text-sm font-semibold text-white" href="/auth/password-dimenticata">
            Richiedi un nuovo link
          </a>
        </section>
      </main>
    );
  }

  if (!info) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f5f7f4]">
        <p className="text-sm text-gray-500">Verifica link in corso...</p>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f5f7f4] px-6 py-12">
      <section className="w-full max-w-md rounded-[28px] border border-[#e6ebe5] bg-white p-8 shadow-sm">
        <div className="mb-6 text-center">
          <span className="font-label mb-2 block text-[10px] font-semibold uppercase tracking-[0.2em] text-gray-400">
            Ripristino accesso
          </span>
          <h1 className="text-2xl font-semibold text-[#1D4E35]">Imposta nuova password</h1>
          <p className="mt-2 text-sm text-gray-500">
            Account <strong>{info.username}</strong> - {info.email}
          </p>
        </div>

        <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)} noValidate>
          <label className="block text-sm font-medium text-gray-700">
            Nuova password
            <input
              className="form-control mt-2 w-full"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimo 8 caratteri"
              autoComplete="new-password"
            />
          </label>

          <label className="block text-sm font-medium text-gray-700">
            Conferma password
            <input
              className="form-control mt-2 w-full"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Ripeti la password"
              autoComplete="new-password"
            />
          </label>

          {submitError ? (
            <AlertBanner variant="danger" title="Ripristino non riuscito">
              {submitError}
            </AlertBanner>
          ) : null}

          <button
            className="w-full rounded-full bg-[#1D4E35] py-3 text-sm font-semibold text-white transition hover:bg-[#163d2a] disabled:opacity-50"
            disabled={submitting}
            type="submit"
          >
            {submitting ? "Aggiornamento in corso..." : "Aggiorna password"}
          </button>
        </form>
      </section>
    </main>
  );
}
