"use client";
import { useState } from "react";
import { communications } from "@/lib/communications-api";
import { useCandidates } from "./use-candidates";
import type { Candidate, Channel, Communication } from "@/types/communications";

export function useCommunicationsWorkspace(token: string, channel: Channel, canEdit: boolean) {
  const candidates = useCandidates(token, channel, canEdit);
  const selection = useCommunicationSelection(token, channel, candidates.reload);
  return { ...candidates, ...selection,
    status: { loading: candidates.loading, busy: selection.busy, error: selection.error || candidates.loadError } };
}

function useCommunicationSelection(token: string, channel: Channel, reload: () => void) {
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [compose, setCompose] = useState({ recipient: "", account_id: "", template_id: "", subject: "", body: "", expected_source_sha256: "" });
  const [message, setMessage] = useState<Communication | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function open(candidate: Candidate, fresh = false) {
    setBusy(true); setError("");
    setSelected(null); setMessage(null);
    try {
      if (candidate.message_id && !fresh) setMessage(await communications<Communication>(token, `/messages/${candidate.message_id}`));
      else { setSelected(candidate); setCompose({ recipient: candidate[channel] || "", account_id: "", template_id: "", subject: "", body: "", expected_source_sha256: "" }); }
    } catch (failure) { setError(errorText(failure)); } finally { setBusy(false); }
  }
  async function create() {
    if (!selected) return;
    setBusy(true); setError("");
    try {
      setMessage(await communications<Communication>(token, "/messages", { ...creationPayload(selected, channel, compose), expected_source_sha256: compose.expected_source_sha256 }));
      setSelected(null); reload();
    } catch (failure) { setError(errorText(failure)); }
    setBusy(false);
  }
  async function refresh() {
    reload();
    if (message) {
      try { setMessage(await communications<Communication>(token, `/messages/${message.id}`)); }
      catch (failure) { setError(errorText(failure)); }
    }
  }
  return { selected, setSelected, compose, setCompose, message, setMessage, busy, error, open, create, refresh };
}

function errorText(error: unknown) { return error instanceof Error ? error.message : "Operazione fallita"; }

function creationPayload(selected: Candidate, channel: Channel, compose: Record<string, string>) {
  return { source_entity_id: selected.id, channel, recipient: compose.recipient, account_id: compose.account_id || null,
    template_id: compose.template_id || null, subject: compose.subject || null, body: compose.body || null,
    purpose: channel === "email" ? "courtesy" : "pec_notice" };
}
