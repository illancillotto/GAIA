"use client";

import { useState } from "react";

import { request } from "@/lib/api/core";
import { getStoredAccessToken } from "@/lib/auth";

type Catalog = { dataset_version: string; entities: { name: string; count: number }[]; audit_enabled: boolean };
type Records = { results: Record<string, unknown>[]; total: number; next_offset: number | null };
type Call = { id: number; event: { timestamp: string; tool_name: string; status: string; duration_ms: number; principal: string }; filters: Record<string, unknown>; response: Record<string, unknown> };
type History = { results: Call[]; next_before: number | null; retention_limit: number; visibility: string };

async function inspect<T>(kind: string, token: string, params = ""): Promise<T> {
  return request<T>(`/wiki/mcp/console/${kind}${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

function RecordsPanel({ entity, records, busy, load }: { entity: string; records: Records; busy: boolean; load: (kind: string, position: number) => Promise<void> }) {
  return <section className="panel-card" aria-label="Dati sintetici">
    <h2 className="text-lg font-semibold">{entity} · {records.total} record</h2>
    <div className="overflow-auto"><table className="w-full text-sm"><thead><tr><th>UUID</th><th>Dati</th></tr></thead><tbody>{records.results.map((row) => (
      <tr key={String(row.id)}><td className="p-2 align-top">{String(row.id)}</td><td><pre className="whitespace-pre-wrap p-2">{JSON.stringify(row, null, 2)}</pre></td></tr>
    ))}</tbody></table></div>
    {records.next_offset !== null && <button className="btn-secondary" disabled={busy} onClick={() => void load(entity, records.next_offset!)}>Record successivi</button>}
  </section>;
}

function MCPRequestHistory({ history, busy, load }: { history: History; busy: boolean; load: (kind: string, position?: number) => Promise<void> }) {
  return <section className="panel-card" aria-label="Storico chiamate">
    <h2 className="text-lg font-semibold">Richieste e log</h2>
    <p>{history.visibility === "own" ? "Le tue chiamate" : "Chiamate nei domini autorizzati, incluse quelle locali"} · Ultime {history.retention_limit} chiamate conservate sul server.</p>
    <p>Testo libero, cursor, domande e credenziali sono omessi. Apri una richiesta per analizzare filtri, risultati sintetici e provenance.</p>
    {history.results.length === 0 && <p>Nessuna chiamata registrata.</p>}
    {history.results.map((call) => <details key={call.id} className="mt-3 rounded border p-3">
      <summary>{call.event.timestamp} · {call.event.tool_name} · {call.event.status} · {call.event.duration_ms} ms</summary>
      <p className="break-all">Principal pseudonimizzato: {call.event.principal}</p>
      <pre className="overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify({ filters: call.filters, response: call.response }, null, 2)}</pre>
    </details>)}
    <button className="btn-secondary mt-3" disabled={busy} onClick={() => void load("calls")}>Aggiorna richieste</button>
    {history.next_before !== null && <button className="btn-secondary mt-3" disabled={busy} onClick={() => void load("calls", history.next_before!)}>Richieste precedenti</button>}
  </section>;
}

export function MCPConsole() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [records, setRecords] = useState<Records | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [entity, setEntity] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load(kind = "catalog", position = 0) {
    const token = getStoredAccessToken();
    setError("");
    if (!token) {
      setCatalog(null);
      setRecords(null);
      setHistory(null);
      setError("Sessione assente: accedi a GAIA.");
      return;
    }
    setBusy(true);
    try {
      if (kind === "catalog") {
        setRecords(null);
        setHistory(null);
        setEntity("");
        const nextCatalog = await inspect<Catalog>("catalog", token);
        setCatalog(nextCatalog);
        if (nextCatalog.audit_enabled) setHistory(await inspect<History>("calls", token));
      } else if (kind === "calls") {
        setHistory(await inspect<History>("calls", token, `?before=${position}`));
      } else {
        setRecords(null);
        setEntity(kind);
        setRecords(await inspect<Records>(kind, token, `?offset=${position}`));
      }
    } catch {
      setCatalog(null);
      setRecords(null);
      setHistory(null);
      setError("Dati MCP non disponibili o accesso negato. Ricarica dopo aver verificato i permessi.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="panel-card">
        <h2 className="text-lg font-semibold">Catalogo sintetico</h2>
        <p>Solo dati generati. I documenti Docs sono esclusi. Le entità visibili rispettano i permessi attuali.</p>
        <button className="btn-primary mt-3" disabled={busy} onClick={() => void load()}>{busy ? "Caricamento…" : "Carica dati e richieste"}</button>
        {error && <p role="alert" className="mt-3 text-red-700">{error}</p>}
        {catalog && <>
          <p className="mt-3 break-all">Dataset: {catalog.dataset_version}</p>
          <div className="mt-3 flex flex-wrap gap-2">{catalog.entities.map((item) => (
            <button key={item.name} className="btn-secondary" disabled={busy} onClick={() => void load(item.name)}>{item.name} ({item.count})</button>
          ))}</div>
          {catalog.entities.length === 0 && <p>Nessuna entità autorizzata.</p>}
          {!catalog.audit_enabled && <p>Storico non configurato sul server MCP.</p>}
        </>}
      </section>
      {records && <RecordsPanel entity={entity} records={records} busy={busy} load={load} />}
      {history && <MCPRequestHistory history={history} busy={busy} load={load} />}
      <section className="panel-card">
        <h2 className="text-lg font-semibold">Collegamenti</h2>
        <p>Claude Desktop/Code: server locale gaia-synthetic, soli tool Data. Le chiamate locali sono visibili agli amministratori nei domini autorizzati.</p>
        <p>ChatGPT: collegamento successivo, tramite endpoint HTTPS autenticato o Secure MCP Tunnel. Nessun servizio pubblico viene esposto da questa pagina.</p>
      </section>
    </div>
  );
}
