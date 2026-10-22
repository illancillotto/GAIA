"use client";

import Link from "next/link";

import { downloadStepDocumentoPdf } from "@/lib/api";
import type { StepContribuenteDetail, StepDocumento, StepPagamento, StepRuoloLink } from "@/types/step";

import { LINK_STATUS_LABELS, formatDate, formatEuro } from "./step-format";

type DetailProps = {
  token: string;
  detail: StepContribuenteDetail;
  onError: (message: string) => void;
};

function LinkBadge({ link }: { link: StepRuoloLink }) {
  const label = `${link.codice_cnc ?? link.reference_key}${link.anno_rif ? ` (${link.anno_rif})` : ""}`;
  if (link.status === "linked" && link.ruolo_avviso_id) {
    return (
      <Link className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700" href={`/ruolo/avvisi/${link.ruolo_avviso_id}`}>
        Avviso {label}
      </Link>
    );
  }
  return (
    <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700" title={LINK_STATUS_LABELS[link.status]}>
      {label} · {LINK_STATUS_LABELS[link.status]}
    </span>
  );
}

async function openPdf(token: string, documento: StepDocumento): Promise<void> {
  const blob = await downloadStepDocumentoPdf(token, documento.id);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = documento.pdf_original_filename ?? `${documento.num_doc}.pdf`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function DocumentoCard({ token, documento, onError }: { token: string; documento: StepDocumento; onError: (message: string) => void }) {
  function handlePdf(): void {
    openPdf(token, documento).catch((error: unknown) => onError(error instanceof Error ? error.message : "Download PDF STEP non riuscito"));
  }

  return (
    <div className="rounded-2xl border border-gray-200 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-gray-900">Documento {documento.num_doc}</p>
          <p className="text-xs text-gray-500">
            {documento.section ?? "—"} · anni {documento.anno_rif ?? "—"} · notifica {formatDate(documento.data_notifica)}
          </p>
          <p className="mt-1 text-sm text-gray-700">
            Carico {formatEuro(documento.imp_carico)} · pagato {formatEuro(documento.tot_pagato)} · residuo {formatEuro(documento.residuo)}
          </p>
        </div>
        {documento.pdf_status === "downloaded" ? (
          <button className="btn-secondary" onClick={handlePdf} type="button">
            PDF
          </button>
        ) : (
          <span className="text-xs text-gray-500">PDF non disponibile</span>
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {documento.links.map((link) => (
          <LinkBadge key={link.id} link={link} />
        ))}
      </div>
      <table className="mt-3 min-w-full text-xs">
        <tbody className="divide-y divide-gray-100">
          {documento.tributi.map((tributo) => (
            <tr key={tributo.position}>
              <td className="py-1 pr-3">{tributo.anno_rif ?? "—"}</td>
              <td className="py-1 pr-3">{tributo.cod_tributo}</td>
              <td className="py-1 pr-3">{tributo.des_tributo}</td>
              <td className="py-1 pr-3 text-right">{formatEuro(tributo.imp_carico)}</td>
              <td className="py-1 text-right">{formatEuro(tributo.imp_carico_pagato)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PagamentiTable({ pagamenti }: { pagamenti: StepPagamento[] }) {
  if (pagamenti.length === 0) return <p className="text-sm text-gray-500">Nessun pagamento registrato su STEP.</p>;
  return (
    <table className="min-w-full text-xs">
      <tbody className="divide-y divide-gray-100">
        {pagamenti.map((pagamento, index) => (
          <tr key={`${pagamento.num_quietanza}-${index}`} className={pagamento.annullato ? "text-gray-400 line-through" : undefined}>
            <td className="py-1 pr-3">{formatDate(pagamento.data_pagamento)}</td>
            <td className="py-1 pr-3">{pagamento.modalita ?? "—"}</td>
            <td className="py-1 pr-3">{pagamento.riferimento ?? "—"}</td>
            <td className="py-1 pr-3">{pagamento.stato ?? ""}</td>
            <td className="py-1 text-right">{formatEuro(pagamento.importo)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function StepContribuenteDetailPanel({ token, detail, onError }: DetailProps) {
  return (
    <div className="space-y-4">
      <div>
        <p className="text-lg font-semibold text-gray-900">{detail.denominazione ?? detail.codice_fiscale}</p>
        <p className="text-sm text-gray-600">
          {detail.codice_fiscale} · residuo {formatEuro(detail.residuo)} · {detail.stato_documenti ?? "—"}
        </p>
      </div>
      {detail.documenti.map((documento) => (
        <DocumentoCard key={documento.id} documento={documento} onError={onError} token={token} />
      ))}
      <div>
        <p className="mb-2 text-sm font-semibold text-gray-900">Pagamenti STEP</p>
        <PagamentiTable pagamenti={detail.pagamenti} />
      </div>
    </div>
  );
}
