"use client";

import { useEffect, useState } from "react";

import { checkRegisteredMailReferences, updateTributiRegisteredMailAssociation } from "@/lib/registered-mail-api";
import type { RegisteredMailCampaignItem } from "@/types/registered-mail-campaign";
import { normalizeIdentity, workbookEvidence, type OperatorWorkbook, type OperatorWorkbookRow } from "./registered-mail-workbook";

function useReferenceCheck(token: string, mailId: string, evidence: OperatorWorkbookRow | null) {
  const [check, setCheck] = useState<{ key: string; verified: boolean; reason: string } | null>(null);
  const key = evidence ? `${evidence.ref2022}:${evidence.ref2023}` : "";
  useEffect(() => {
    if (!evidence) return;
    let active = true;
    void checkRegisteredMailReferences(token, mailId, evidence.ref2022, evidence.ref2023)
      .then((result) => { if (active) setCheck({ key, ...result }); })
      .catch((cause) => { if (active) setCheck({ key, verified: false, reason: cause instanceof Error ? cause.message : "Verifica inCASS non disponibile" }); });
    return () => { active = false; };
  }, [token, mailId, evidence, key]);
  return check?.key === key ? check : null;
}

function PosteEvidence({ item }: { item: RegisteredMailCampaignItem }) {
  return <div>
    <h4 className="text-xs font-bold uppercase tracking-wider text-[#1D4E35]">Poste</h4>
    <p className="mt-2 font-semibold">{item.recipient_name ?? "Destinatario non letto"}</p>
    <p className="text-sm text-gray-600">{item.recipient_address ?? "Indirizzo assente"}</p>
    <p className="mt-2 text-xs text-gray-500">Invio {item.source_shipment_id} - tracking {item.tracking_number ?? "-"}</p>
  </div>;
}

function WorkbookEvidence({ item, evidence, check }: {
  item: RegisteredMailCampaignItem;
  evidence: OperatorWorkbookRow | null;
  check: { verified: boolean; reason: string } | null;
}) {
  if (!evidence) return <div><h4 className="text-xs font-bold uppercase tracking-wider text-[#1D4E35]">Foglio operatori</h4><p className="mt-2 text-sm text-amber-800">Nessuna riga cumulativa univoca trovata.</p></div>;
  const nameMatches = normalizeIdentity(evidence.name) === normalizeIdentity(item.recipient_name);
  return <div>
    <h4 className="text-xs font-bold uppercase tracking-wider text-[#1D4E35]">Foglio operatori</h4>
    <p className="mt-2 font-semibold">Riga {evidence.row} - cumulativo {evidence.cumulativeNumber}</p>
    <p className="text-sm text-gray-600">{evidence.name} - {evidence.address} - {evidence.city}</p>
    <p className="mt-2 text-xs">2022: {evidence.ref2022} - 2023: {evidence.ref2023}</p>
    <p className={`mt-2 text-xs font-semibold ${nameMatches ? "text-emerald-700" : "text-amber-800"}`}>
      {nameMatches ? "Nominativo concordante" : "Nominativo da controllare"}
    </p>
    <p className={`mt-1 text-xs font-semibold ${check?.verified ? "text-emerald-700" : "text-amber-800"}`}>
      {check?.reason ?? "Verifica inCASS in corso..."}
    </p>
  </div>;
}

function CandidateEvidence({ item, canPropose, saving, confirmed, setConfirmed, save, error }: {
  item: RegisteredMailCampaignItem;
  canPropose: boolean;
  saving: boolean;
  confirmed: boolean;
  setConfirmed: (value: boolean) => void;
  save: () => void;
  error: string | null;
}) {
  return <div>
    <h4 className="text-xs font-bold uppercase tracking-wider text-[#1D4E35]">Avvisi candidati</h4>
    {item.candidate_notices.map((notice) => <p className="mt-2 text-sm" key={notice.avviso_id}>
      <strong>{notice.tax_year}</strong> - CNC {notice.codice_cnc} - {notice.nominativo ?? "Nominativo assente"}
    </p>)}
    <p className="mt-3 text-xs text-amber-800">Il foglio non contiene l&apos;ID invio Poste. Verificare l&apos;identita della spedizione; l&apos;associazione non certifica la notifica.</p>
    {canPropose ? <>
      <label className="mt-3 flex items-start gap-2 text-sm">
        <input checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} type="checkbox" />
        Ho verificato che questo invio riguarda entrambi gli avvisi.
      </label>
      <button className="btn-primary mt-3" disabled={!confirmed || saving} onClick={save} type="button">
        {saving ? "Salvataggio..." : "Associa entrambi gli avvisi"}
      </button>
    </> : null}
    {error ? <p className="mt-2 text-sm text-red-700" role="alert">{error}</p> : null}
  </div>;
}

export function RegisteredMailReviewDetail({ item, workbook, token, onSaved }: {
  item: RegisteredMailCampaignItem;
  workbook: OperatorWorkbook | null;
  token: string;
  onSaved: () => void;
}) {
  const [confirmed, setConfirmed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const evidence = workbook ? workbookEvidence(item, workbook.rows) : null;
  const check = useReferenceCheck(token, item.mail_id, evidence);
  const years = new Set(item.candidate_notices.map((notice) => notice.tax_year));
  const canPropose = item.classification === "proposed_pair" && item.candidate_notices.length === 2 && years.has(2022) && years.has(2023) && evidence !== null && check?.verified === true;

  async function save(reviewedRow: OperatorWorkbookRow, reviewedWorkbook: OperatorWorkbook): Promise<void> {
    setSaving(true);
    setError(null);
    try {
      await updateTributiRegisteredMailAssociation(token, item.mail_id, {
        avviso_ids: item.candidate_notices.map((notice) => notice.avviso_id),
        review_evidence: {
          source_sha256: reviewedWorkbook.sha256, sheet: "Dati", row: reviewedRow.row,
          ref_2022: reviewedRow.ref2022, ref_2023: reviewedRow.ref2023,
        },
      });
      setConfirmed(false);
      onSaved();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Associazione non salvata");
    } finally {
      setSaving(false);
    }
  }

  return <div className="grid gap-4 border-t border-[#d8dfd3] bg-[#fbfcf9] p-5 lg:grid-cols-3">
    <PosteEvidence item={item} />
    <WorkbookEvidence check={check} evidence={evidence} item={item} />
    <CandidateEvidence canPropose={canPropose} confirmed={confirmed} error={error} item={item} save={() => void save(evidence!, workbook!)} saving={saving} setConfirmed={setConfirmed} />
  </div>;
}
