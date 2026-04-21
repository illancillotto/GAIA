"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getApiBaseUrl } from "@/lib/api";

type ActivationInfo = {
  wc_operator_id: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  suggested_username: string | null;
  already_activated: boolean;
};

async function fetchActivationInfo(token: string): Promise<ActivationInfo> {
  const res = await fetch(`${getApiBaseUrl()}/auth/invite/${token}`, { cache: "no-store" });
  if (!res.ok) {
    const payload = await res.json().catch(() => null);
    const msg = payload?.detail ?? res.statusText ?? "Errore";
    throw new Error(String(msg));
  }
  return res.json() as Promise<ActivationInfo>;
}

async function submitActivation(token: string, username: string, password: string) {
  const res = await fetch(`${getApiBaseUrl()}/auth/invite/${token}/activate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
    cache: "no-store",
  });
  const payload = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(String(payload?.detail ?? res.statusText ?? "Errore"));
  }
  return payload as { user_id: number; username: string; message: string };
}

export default function ActivationPage() {
  const params = useParams();
  const router = useRouter();
  const token = typeof params.token === "string" ? params.token : Array.isArray(params.token) ? params.token[0] : "";

  const [info, setInfo] = useState<ActivationInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) return;
    fetchActivationInfo(token)
      .then((data) => {
        setInfo(data);
        if (data.suggested_username) setUsername(data.suggested_username);
      })
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : "Errore"));
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
      await submitActivation(token, username, password);
      setDone(true);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Errore durante l'attivazione");
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-[#f5f7f4] p-6">
        <div className="w-full max-w-sm rounded-[28px] border border-emerald-100 bg-white p-8 shadow-sm text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50">
            <span className="text-2xl text-emerald-600">✓</span>
          </div>
          <h1 className="text-xl font-semibold text-gray-900">Account attivato</h1>
          <p className="mt-2 text-sm text-gray-600">
            Puoi ora accedere a GAIA con le tue credenziali.
          </p>
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
        <div className="w-full max-w-sm rounded-[28px] border border-rose-100 bg-white p-8 shadow-sm text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-rose-50">
            <span className="text-2xl text-rose-500">!</span>
          </div>
          <h1 className="text-xl font-semibold text-gray-900">Link non valido</h1>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </div>
      </div>
    );
  }

  if (info?.already_activated) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-[#f5f7f4] p-6">
        <div className="w-full max-w-sm rounded-[28px] border border-gray-200 bg-white p-8 shadow-sm text-center">
          <h1 className="text-xl font-semibold text-gray-900">Account già attivato</h1>
          <p className="mt-2 text-sm text-gray-600">Questo link è già stato usato. Accedi normalmente.</p>
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

  const fullName = [info.first_name, info.last_name].filter(Boolean).join(" ") || "Operatore";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#f5f7f4] p-6">
      <div className="w-full max-w-sm rounded-[28px] border border-[#e6ebe5] bg-white p-8 shadow-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full border border-[#d5e2d8] bg-[#edf5f0]">
            <span className="text-xl font-bold text-[#1D4E35]">
              {fullName.split(" ").map((p) => p[0]).join("").slice(0, 2).toUpperCase()}
            </span>
          </div>
          <h1 className="text-xl font-semibold text-gray-900">Benvenuto, {fullName}</h1>
          <p className="mt-1 text-sm text-gray-500">Scegli username e password per attivare il tuo account GAIA.</p>
        </div>

        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div>
            <label className="label-caption block mb-1">Username</label>
            <input
              type="text"
              className="form-control w-full"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="es. mario.rossi"
              required
              autoComplete="username"
            />
          </div>
          <div>
            <label className="label-caption block mb-1">Password</label>
            <input
              type="password"
              className="form-control w-full"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimo 8 caratteri"
              required
              autoComplete="new-password"
            />
          </div>
          <div>
            <label className="label-caption block mb-1">Conferma password</label>
            <input
              type="password"
              className="form-control w-full"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Ripeti la password"
              required
              autoComplete="new-password"
            />
          </div>

          {submitError && (
            <p className="rounded-[14px] border border-rose-100 bg-rose-50 px-3 py-2 text-xs text-rose-700">
              {submitError}
            </p>
          )}

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
