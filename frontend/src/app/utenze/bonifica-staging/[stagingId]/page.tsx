"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { UtenzeModulePage } from "@/components/utenze/utenze-module-page";
import { CheckIcon, RefreshIcon } from "@/components/ui/icons";
import {
  approveUtenzeBonificaStagingItem,
  getUtenzeBonificaStagingItem,
  rejectUtenzeBonificaStagingItem,
} from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { BonificaUserStaging } from "@/types/api";

export default function UtenzeBonificaStagingDetailPage() {
  const params = useParams<{ stagingId: string }>();
  const stagingId = params?.stagingId ?? "";

  return (
    <UtenzeModulePage
      title="Dettaglio staging consorziato"
      description="Revisione record importato da WhiteCompany prima dell'import verso Utenze."
      breadcrumb="Utenze / Staging consorziati"
    >
      {({ token }) => <Detail token={token} stagingId={stagingId} />}
    </UtenzeModulePage>
  );
}

function Detail({ token, stagingId }: { token: string; stagingId: string }) {
  const router = useRouter();
  const [item, setItem] = useState<BonificaUserStaging | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(): Promise<void> {
    setLoading(true);
    try {
      const response = await getUtenzeBonificaStagingItem(token, stagingId);
      setItem(response);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore caricamento dettaglio staging");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!stagingId) return;
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stagingId]);

  async function handleApprove(): Promise<void> {
    if (!stagingId) return;
    setBusy(true);
    try {
      await approveUtenzeBonificaStagingItem(token, stagingId);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function handleReject(): Promise<void> {
    if (!stagingId) return;
    setBusy(true);
    try {
      await rejectUtenzeBonificaStagingItem(token, stagingId);
      await load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-body">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2">
          <button className="btn-secondary" type="button" onClick={() => router.push("/utenze/bonifica-staging")}>
            ← Torna alla lista
          </button>
          <button className="btn-secondary" type="button" onClick={() => void load()} disabled={loading}>
            <RefreshIcon className="mr-2 inline h-4 w-4" />
            Aggiorna
          </button>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" type="button" onClick={() => void handleReject()} disabled={busy || loading}>
            Rifiuta
          </button>
          <button className="btn-primary" type="button" onClick={() => void handleApprove()} disabled={busy || loading}>
            <CheckIcon className="mr-2 inline h-4 w-4" />
            {item?.matched_subject_id ? "Aggiorna da WhiteCompany" : "Importa in anagrafica"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      ) : null}

      {loading ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-5 text-sm text-gray-500">Caricamento dettaglio...</div>
      ) : !item ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-5 text-sm text-gray-500">Record non disponibile.</div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-gray-100 bg-white p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Anagrafica</p>
            <div className="mt-3 grid gap-2 text-sm text-gray-700">
              <Row label="Nome" value={[item.last_name, item.first_name].filter(Boolean).join(" ") || item.business_name || "—"} />
              <Row label="CF/PIVA" value={item.tax ?? "—"} />
              <Row label="Email" value={item.email ?? "—"} />
              <Row label="Telefono" value={item.phone ?? "—"} />
              <Row label="Mobile" value={item.mobile ?? "—"} />
              <Row label="Ruolo" value={item.role ?? "—"} />
              <Row label="Enabled" value={item.enabled ? "Si" : "No"} />
            </div>
          </div>
          <div className="rounded-2xl border border-gray-100 bg-white p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Stato</p>
            <div className="mt-3 grid gap-2 text-sm text-gray-700">
              <Row label="review_status" value={item.review_status} />
              <Row label="wc_id" value={String(item.wc_id)} />
              <Row label="Synced at" value={formatDateTime(item.wc_synced_at)} />
              <Row label="Reviewed at" value={formatDateTime(item.reviewed_at)} />
              <Row label="Matched subject" value={item.matched_subject_display_name ?? "—"} />
            </div>
          </div>
          <div className="rounded-2xl border border-gray-100 bg-white p-5 lg:col-span-2">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Mismatch fields</p>
            <pre className="mt-3 overflow-x-auto rounded-xl border border-gray-100 bg-gray-50 p-4 text-xs text-gray-700">
              {item.mismatch_fields ? JSON.stringify(item.mismatch_fields, null, 2) : "—"}
            </pre>
          </div>
        </div>
      )}
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-3">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  );
}
