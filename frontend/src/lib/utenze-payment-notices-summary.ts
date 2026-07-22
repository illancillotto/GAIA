import type { AnagraficaPaymentNotice } from "@/types/api";

export type PaymentNoticeStatus = "paid" | "partial" | "unpaid";

export type PaymentNoticeSummary = {
  totalResiduo: number;
  paidCount: number;
  partialCount: number;
  unpaidCount: number;
  noticesCount: number;
  status: PaymentNoticeStatus;
  label: string;
  description: string;
};

export function parseNoticeAmount(value: string | null | undefined): number | null {
  if (!value) return null;
  const raw = String(value).trim().replace(/[^\d,.-]/g, "");
  if (!raw) return null;

  let normalized = raw;
  if (raw.includes(",")) {
    normalized = raw.replace(/\./g, "").replace(",", ".");
  } else if (raw.includes(".")) {
    const parts = raw.split(".");
    if (parts.length > 2) {
      const decimalLike = parts[parts.length - 1]?.length !== 3;
      normalized = decimalLike ? `${parts.slice(0, -1).join("")}.${parts.at(-1)}` : parts.join("");
    }
  }

  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export function isPaidLikeStatus(value: string | null | undefined): boolean {
  if (!value) return false;
  const normalized = value.trim().toLowerCase();
  if (normalized.startsWith("non pagato") || normalized.includes("parzialmente") || normalized.includes("in parte") || normalized.includes("senza pagamenti")) {
    return false;
  }
  return normalized.includes("pagato") && !normalized.startsWith("non pagato");
}

export function getPaymentNoticeStatus(notice: AnagraficaPaymentNotice): PaymentNoticeStatus {
  if (notice.payment_status === "paid" || notice.payment_status === "partial" || notice.payment_status === "unpaid") {
    return notice.payment_status;
  }
  const residuo = parseNoticeAmount(notice.importo_residuo);
  const riscosso = parseNoticeAmount(notice.importo_riscosso) ?? 0;
  const carico = parseNoticeAmount(notice.importo_carico);
  if ((residuo != null && residuo <= 0) || notice.data_pagamento || isPaidLikeStatus(notice.stato_label)) {
    return "paid";
  }
  if (riscosso > 0 || (carico != null && residuo != null && residuo > 0 && residuo < carico)) {
    return "partial";
  }
  return "unpaid";
}

export function buildPaymentNoticeSummary(notices: AnagraficaPaymentNotice[]): PaymentNoticeSummary {
  const totalResiduo = notices.reduce((sum, notice) => sum + (parseNoticeAmount(notice.importo_residuo) ?? 0), 0);
  const statuses = notices.map(getPaymentNoticeStatus);
  const paidCount = statuses.filter((status) => status === "paid").length;
  const partialCount = statuses.filter((status) => status === "partial").length;
  const unpaidCount = statuses.filter((status) => status === "unpaid").length;
  const hasOpenDebt = totalResiduo > 0.005;
  const status: PaymentNoticeStatus = !hasOpenDebt && notices.length > 0 ? "paid" : partialCount > 0 || paidCount > 0 ? "partial" : "unpaid";
  const label = notices.length === 0 ? "Nessun avviso" : status === "paid" ? "Pagatore regolare" : status === "partial" ? "Pagamenti parziali" : "Non pagatore";
  const description = notices.length === 0
    ? "Nessun avviso inCASS sincronizzato."
    : status === "paid"
      ? "Nessun residuo aperto sugli avvisi sincronizzati."
      : `${unpaidCount} non pagati, ${partialCount} parziali, ${paidCount} pagati.`;
  return {
    totalResiduo,
    paidCount,
    partialCount,
    unpaidCount,
    noticesCount: notices.length,
    status,
    label,
    description,
  };
}
