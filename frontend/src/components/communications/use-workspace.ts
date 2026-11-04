"use client";
import { useCallback, useEffect, useState } from "react";
import { communications } from "@/lib/communications-api";
import type { Account, Candidate, Channel, Communication, Template } from "@/types/communications";

export function useCommunicationsWorkspace(token: string, channel: Channel, canEdit: boolean) {
  const candidates = useCandidates(token, channel, canEdit);
  const selection = useCommunicationSelection(token, channel, candidates.reload);
  return { ...candidates, ...selection,
    status: { loading: candidates.loading, busy: selection.busy, error: selection.error || candidates.loadError } };
}

function useCandidates(token: string, channel: Channel, canEdit: boolean) {
  const [filters, setFilters] = useState({ q: "", has_contact: "", state: "", date_from: "", date_to: "", account_id: "", batch_id: "", payment_state: "", notification_state: "", has_pec: "", has_email: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ items: Candidate[]; total: number; accounts: Account[]; templates: Template[] }>({ items: [], total: 0, accounts: [], templates: [] });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision((value) => value + 1), []);
  useEffect(() => {
    let disposed = false;
    setLoading(true); setLoadError("");
    const query = new URLSearchParams({ channel, year: "2021", page: String(page), page_size: "25" });
    for (const [key, value] of Object.entries(filters)) if (value) query.set(key, value);
    Promise.all([
      communications<{ items: Candidate[]; total: number }>(token, `/ruolo/candidates?${query}`),
      canEdit ? communications<Account[]>(token, "/accounts") : Promise.resolve([]),
      communications<Template[]>(token, "/templates"),
    ]).then(([list, accounts, templates]) => {
      if (!disposed) { setData({ ...list, accounts, templates }); setLoading(false); }
    }).catch((error: Error) => { if (!disposed) { setLoading(false); setLoadError(error.message); } });
    return () => { disposed = true; };
  }, [token, channel, filters, page, canEdit, revision]);
  return { filters, setFilters, page, setPage, data, loading, loadError, reload };
}

function useCommunicationSelection(token: string, channel: Channel, reload: () => void) {
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [compose, setCompose] = useState({ recipient: "", account_id: "", template_id: "", subject: "", body: "" });
  const [message, setMessage] = useState<Communication | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function open(candidate: Candidate, fresh = false) {
    setBusy(true); setError("");
    setSelected(null); setMessage(null);
    try {
      if (candidate.message_id && !fresh) setMessage(await communications<Communication>(token, `/messages/${candidate.message_id}`));
      else { setSelected(candidate); setCompose({ recipient: candidate[channel] || "", account_id: "", template_id: "", subject: "", body: "" }); }
    } catch (failure) { setError(errorText(failure)); }
    setBusy(false);
  }
  async function create() {
    if (!selected) return;
    setBusy(true); setError("");
    try {
      setMessage(await communications<Communication>(token, "/messages", creationPayload(selected, channel, compose)));
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
