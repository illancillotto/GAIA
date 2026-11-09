"use client";

import { useEffect, useState } from "react";
import { getSollecitiWorkspace, prepareSolleciti, reconcileSollecitiAccount, type WorkspaceFilters, type WorkspaceResult } from "@/lib/ruolo-solleciti-workspace-api";
import { requestPosteJob } from "@/lib/ruolo-poste-dispatch-api";
import { errorMessage } from "@/components/ruolo/poste-dispatch/labels";

export function usePosteWorkspace(token: string) {
  const [filters, setFilters] = useState<WorkspaceFilters>({ q: "", year: "2021", account: "all", stage: "all", page: 1 });
  const [data, setData] = useState<WorkspaceResult | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [version, setVersion] = useState(0);
  const reload = () => setVersion((value) => value + 1);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    getSollecitiWorkspace(token, filters)
      .then((value) => { if (!cancelled) setData(value); })
      .catch((err) => { if (!cancelled) setError(errorMessage(err, "Avvisi non caricati")); });
    return () => { cancelled = true; };
  }, [token, filters, version]);

  useEffect(() => {
    setData(null); setSelected([]); setDetailId(null); setNotice(null);
  }, [token]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") setVersion((value) => value + 1);
    }, 30_000);
    return () => window.clearInterval(timer);
  }, []);

  function filter(change: Partial<WorkspaceFilters>) {
    setData(null); setNotice(null);
    setSelected([]);
    setDetailId(null);
    setFilters((current) => ({ ...current, page: 1, ...change }));
  }

  function toggle(id: string) {
    setSelected((ids) => ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id].slice(0, 50));
  }

  async function prepare(credentialId: number) {
    setBusy(true); setError(null); setNotice(null);
    try {
      await prepareSolleciti(token, selected, credentialId);
      setSelected([]);
      setNotice("Preparazione avviata. Segui lo stato degli avvisi nell’elenco. INVIA resta manuale su Poste.");
      reload();
    } catch (err) { setError(errorMessage(err, "Preparazione non avviata")); }
    finally { setBusy(false); }
  }

  async function reconcile(lotId: string) {
    setBusy(true); setError(null); setNotice(null);
    try {
      await requestPosteJob(token, lotId, "reconcile");
      setNotice("Controllo Poste accodato. Lo stato verrà aggiornato al termine della lettura.");
      reload();
    } catch (err) { setError(errorMessage(err, "Controllo Poste non avviato")); }
    finally { setBusy(false); }
  }

  async function reconcileAccount() {
    setBusy(true); setError(null); setNotice(null);
    try {
      const result = await reconcileSollecitiAccount(token, Number(filters.account), filters.year ? Number(filters.year) : null);
      setNotice(`Controlli accodati: ${result.queued_jobs.length}. Operazioni già in corso: ${result.busy_lots}. La lettura aggiorna lo stato senza caricare o spedire avvisi.`);
      reload();
    } catch (err) { setError(errorMessage(err, "Controllo account non avviato")); }
    finally { setBusy(false); }
  }

  return { filters, filter, data, selected, toggle, detailId, setDetailId, error, notice, busy,
    prepare, reconcile, reconcileAccount, reload, detail: data?.items.find((row) => row.item_id === detailId) };
}
