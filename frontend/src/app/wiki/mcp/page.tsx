"use client";

import { useState, type FormEvent } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { request } from "@/lib/api/core";
import { getStoredAccessToken } from "@/lib/auth";

const QUESTIONS = [
  "Cerca il soggetto sintetico con identificativo SYN-SUBJECT-0001.",
  "Cerca il soggetto sintetico con identificativo SYN-NOT-EXISTENT.",
];

type MCPAnswer = {
  answer: string;
  found: boolean;
  provenance: { source: string; entity: string; record_id: string; dataset_version: string }[];
  tool_calls: number;
  evidence_tokens: number;
};

export default function WikiMCPPreview() {
  const [question, setQuestion] = useState(QUESTIONS[0]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<MCPAnswer | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setResult(null);
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione assente: accedi a GAIA.");
      return;
    }
    setBusy(true);
    try {
      const answer = await request<MCPAnswer>("/wiki/mcp/chat", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: JSON.stringify({ question }),
        timeoutMs: 180_000,
      });
      setResult(answer);
    } catch {
      setError("Agente non disponibile o accesso negato. Verifica sessione e configurazione MCP.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ProtectedPage title="Wiki MCP — preview sintetica" description="gpt-reserve via codex-lb, solo Data sintetici." breadcrumb="GAIA / Wiki / MCP">
      <p>Nessun documento reale. Nessun testo libero o allegato. La chat Wiki legacy resta separata.</p>
      <form onSubmit={submit}>
        <label htmlFor="synthetic-question">Domanda sintetica</label>
        <select id="synthetic-question" value={question} onChange={(event) => setQuestion(event.target.value)} disabled={busy}>
          {QUESTIONS.map((item) => <option key={item}>{item}</option>)}
        </select>
        <button type="submit" disabled={busy}>{busy ? "Ricerca in corso…" : "Interroga Data MCP"}</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {result && (
        <section aria-label="Risposta sintetica">
          <p>{result.answer}</p>
          <p>{result.found ? "Evidenze trovate" : "Nessuna evidenza"} · Tool: {result.tool_calls} · Token evidenze: {result.evidence_tokens}</p>
          <ul>{result.provenance.map((source, index) => (
            <li key={`${source.entity}:${source.record_id}:${index}`}>
              {source.source} / {source.entity} / {source.record_id} · Dataset {source.dataset_version}
            </li>
          ))}</ul>
        </section>
      )}
    </ProtectedPage>
  );
}
