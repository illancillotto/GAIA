"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getApiBaseUrl } from "@/lib/api";

type ActivationInfo = {
  user_id: number;
  username: string;
  email: string;
  full_name: string | null;
  already_activated: boolean;
};

async function fetchActivationInfo(token: string): Promise<ActivationInfo> {
  const res = await fetch(`${getApiBaseUrl()}/auth/user-invite/${token}`, { cache: "no-store" });
  if (!res.ok) {
    const payload = await res.json().catch(() => null);
    throw new Error(String(payload?.detail ?? res.statusText ?? "Errore"));
  }
  return res.json() as Promise<ActivationInfo>;
}

async function submitActivation(token: string, password: string) {
  const res = await fetch(`${getApiBaseUrl()}/auth/user-invite/${token}/activate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
    cache: "no-store",
  });
  const payload = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(String(payload?.detail ?? res.statusText ?? "Errore"));
  }
  return payload as { user_id: number; username: string; message: string };
}

export default function AccountActivationPage() {
  const params = useParams();
  const router = useRouter();
  const token = typeof params.token === "string" ? params.token : Array.isArray(params.token) ? params.token[0] : "";

  const [info, setInfo] = useState<ActivationInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) return;
    fetchActivationInfo(token)
      .then(setInfo)
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : "Errore"));
  }, [token]);

  async function handleSubmit(event: React.FormEvent) {
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
      await submitActivation(token, password);
      setDone(true);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Errore durante l'attivazione");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-[#f5f7f4] p-6">
        <div className="w-full max-w-sm rounded-[28px] border border-emerald-100 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-semibold text-gray-900">Account attivato</h1>
          <p className="mt-2 text-sm text-gray-600">Puoi ora accedere a GAIA con password o Google.</p>
          <button
            onClick={() => router.push("/login")}
            className="mt-6 w-full rounded-full bg-[#1D4E35] py-3 text-sm font-semibold text-white transition hover:bg-[#163d2a]"
          >
            Vai al login
          </button>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-[#f5f7f4] p-6">
        <div className="w-full max-w-sm rounded-[28px] border border-rose-100 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-semibold text-gray-900">Link non valido</h1>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </div>
      </div>
    );
  }

  if (info?.already_activated) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-[#f5f7f4] p-6">
        <div className="w-full max-w-sm rounded-[28px] border border-gray-200 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-semibold text-gray-900">Account già attivato</h1>
          <p className="mt-2 text-sm text-gray-600">Questo link non è più utilizzabile. Accedi normalmente.</p>
          <button
            onClick={() => router.push("/login")}
            className="mt-6 w-full rounded-full bg-[#1D4E35] py-3 text-sm font-semibold text-white transition hover:bg-[#163d2a]"
          >
            Vai al login
          </button>
        </div>
      </div>
    );
  }

  if (!info) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f5f7f4]">
        <p className="text-sm text-gray-500">Caricamento in corso...</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#f5f7f4] p-6">
      <div className="w-full max-w-sm rounded-[28px] border border-[#e6ebe5] bg-white p-8 shadow-sm">
        <div className="mb-6 text-center">
          <h1 className="text-xl font-semibold text-gray-900">Attiva il tuo account GAIA</h1>
          <p className="mt-1 text-sm text-gray-500">
            Username <strong>{info.username}</strong> • {info.email}
          </p>
        </div>

        <form onSubmit={(event) => void handleSubmit(event)} className="space-y-4">
          <div>
            <label className="label-caption mb-1 block">Nuova password</label>
            <input
              type="password"
              className="form-control w-full"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimo 8 caratteri"
              required
              autoComplete="new-password"
            />
          </div>
          <div>
            <label className="label-caption mb-1 block">Conferma password</label>
            <input
              type="password"
              className="form-control w-full"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Ripeti la password"
              required
              autoComplete="new-password"
            />
          </div>

          {submitError ? (
            <p className="rounded-[14px] border border-rose-100 bg-rose-50 px-3 py-2 text-xs text-rose-700">
              {submitError}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-full bg-[#1D4E35] py-3 text-sm font-semibold text-white transition hover:bg-[#163d2a] disabled:opacity-50"
          >
            {submitting ? "Attivazione in corso..." : "Attiva account"}
          </button>
        </form>
      </div>
    </div>
  );
}
