"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";

import { login } from "@/lib/api/platform";
import { isAuthError } from "@/lib/api/core";
import { clearStoredAccessToken, getClientDeviceLabel, getStoredAccessToken, getStoredClientDeviceId, setStoredAccessToken } from "@/lib/auth";
import { decideMCPConsent, loadMCPConsent, returnToMCPClient, type MCPConsentDetails } from "./mcp-consent-api";

const SCOPE_LABELS: Record<string, string> = {
  "utenze.read": "Utenze: lettura dei soggetti sintetici",
  "catasto.read": "Catasto: lettura dei dati sintetici",
  "ruolo.read": "Ruolo: lettura degli avvisi sintetici",
};

export function useMCPConsent(requestId: string, active: boolean) {
  const [token, setToken] = useState<string | null>(null);
  const [details, setDetails] = useState<MCPConsentDetails | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async (session: string) => {
    setBusy(true);
    setError("");
    setDetails(null);
    try {
      setDetails(await loadMCPConsent(session, requestId));
      setToken(session);
    } catch (failure) {
      if (isAuthError(failure)) {
        clearStoredAccessToken();
        setToken(null);
      }
      setError("Richiesta non disponibile o sessione scaduta. Accedi oppure riaprila dal connettore.");
    } finally {
      setBusy(false);
    }
  }, [requestId]);
  useEffect(() => {
    const stored = getStoredAccessToken();
    if (active && stored) void load(stored);
  }, [active, load]);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = new FormData(form);
    setBusy(true);
    setError("");
    try {
      const session = await login(String(input.get("username")), String(input.get("password")), {
        deviceId: getStoredClientDeviceId(), deviceLabel: getClientDeviceLabel(),
      });
      setStoredAccessToken(session.access_token);
      await load(session.access_token);
    } catch {
      setError("Accesso GAIA non riuscito. Verifica le credenziali e lo stato del dispositivo.");
    } finally {
      form.reset();
      setBusy(false);
    }
  }

  async function decide(allowed: boolean) {
    if (!token || !details) return;
    setBusy(true);
    setError("");
    try {
      const result = await decideMCPConsent(token, requestId, allowed);
      returnToMCPClient(result.redirect_url, details.redirect_uri);
    } catch {
      setError("Consenso non completato. Riapri la richiesta dal connettore.");
      setBusy(false);
    }
  }
  return { token, details, busy, error, signIn, decide };
}

export function MCPConsent({ enabled }: { enabled: boolean }) {
  const search = useSearchParams();
  const requestId = search.get("request_id") ?? "";
  const valid = /^[A-Za-z0-9_-]{32,128}$/.test(requestId);
  if (!enabled) return <main className="p-8"><h1>Connettore MCP non attivo</h1><p>L’attivazione richiede la validazione HTTPS e l’approvazione del CED.</p></main>;
  if (!valid) return <main className="p-8"><h1>Richiesta di consenso non valida</h1><p>Apri una nuova richiesta dal connettore.</p></main>;
  return <ConsentFlow key={requestId} requestId={requestId} />;
}

function ConsentFlow({ requestId }: { requestId: string }) {
  const consent = useMCPConsent(requestId, true);
  return (
    <main className="mx-auto max-w-xl space-y-5 p-8">
      <h1 className="text-2xl font-semibold">Autorizza il connettore MCP</h1>
      <p>Usa il tuo account GAIA. Username e password restano su GAIA: non vengono inviati al connettore o al modello.</p>
      <p className="rounded border p-3">Solo dati sintetici, in sola lettura. Documenti reali, Docs e log di audit non sono accessibili al connettore.</p>
      {consent.error && <p role="alert">{consent.error}</p>}
      {consent.busy && <p role="status">Operazione in corso…</p>}
      {!consent.token && <form method="post" onSubmit={consent.signIn} className="space-y-3">
        <label className="block">Username GAIA<input name="username" autoComplete="username" required className="block w-full rounded border p-2" /></label>
        <label className="block">Password GAIA<input name="password" type="password" autoComplete="current-password" required className="block w-full rounded border p-2" /></label>
        <button type="submit" disabled={consent.busy} className="rounded border px-4 py-2">Accedi a GAIA</button>
      </form>}
      {consent.details && <section className="space-y-3" aria-label="Permessi richiesti">
        <h2 className="font-semibold">{consent.details.client_name}</h2>
        <p>Endpoint: {consent.details.resource}</p>
        <ul>{consent.details.scopes.map(scope => <li key={scope}>{SCOPE_LABELS[scope] ?? scope}</li>)}</ul>
        <p>Concedi questi permessi al connettore? Nessuna autorizzazione viene concessa automaticamente.</p>
        <button disabled={consent.busy} onClick={() => void consent.decide(true)} className="mr-3 rounded border px-4 py-2">Autorizza</button>
        <button disabled={consent.busy} onClick={() => void consent.decide(false)} className="rounded border px-4 py-2">Rifiuta</button>
      </section>}
    </main>
  );
}
