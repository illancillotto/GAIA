"use client";

import { FormEvent, useState } from "react";

import { AlertBanner } from "@/components/ui/alert-banner";
import { requestPasswordReset } from "@/lib/password-reset-api";

export default function ForgotPasswordPage() {
  const [identifier, setIdentifier] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    if (!identifier.trim()) {
      setError("Inserisci username o email.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await requestPasswordReset(identifier.trim());
      setMessage(response.message);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Richiesta non riuscita");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f5f7f4] px-6 py-12">
      <section className="w-full max-w-md rounded-[28px] border border-[#e6ebe5] bg-white p-8 shadow-sm">
        <div className="mb-8 text-center">
          <span className="font-label mb-2 block text-[10px] font-semibold uppercase tracking-[0.2em] text-gray-400">
            Identita GAIA
          </span>
          <h1 className="text-2xl font-semibold text-[#1D4E35]">Ripristina password</h1>
          <p className="mt-3 text-sm leading-6 text-gray-500">
            Indica username o email. Se l&apos;account esiste ed e attivo, riceverai un link temporaneo.
          </p>
        </div>

        {message ? (
          <div className="mb-6">
            <AlertBanner variant="info" title="Controlla la mail">
              {message}
            </AlertBanner>
          </div>
        ) : null}

        {error ? (
          <div className="mb-6">
            <AlertBanner variant="danger" title="Richiesta non riuscita">
              {error}
            </AlertBanner>
          </div>
        ) : null}

        <form className="space-y-5" onSubmit={(event) => void handleSubmit(event)} noValidate>
          <label className="block text-sm font-medium text-gray-700">
            Username o email
            <input
              className="form-control mt-2 w-full"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              placeholder="m.rossi@consorzio.it"
              autoComplete="username"
            />
          </label>

          <button
            className="w-full rounded-full bg-[#1D4E35] py-3 text-sm font-semibold text-white transition hover:bg-[#163d2a] disabled:opacity-50"
            disabled={submitting}
            type="submit"
          >
            {submitting ? "Invio in corso..." : "Invia link di ripristino"}
          </button>
        </form>

        <a className="mt-6 block text-center text-sm font-medium text-[#1D4E35] transition hover:opacity-80" href="/login">
          Torna al login
        </a>
      </section>
    </main>
  );
}
