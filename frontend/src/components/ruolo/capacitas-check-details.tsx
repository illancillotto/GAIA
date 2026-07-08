import type { ReactNode } from "react";

import type {
  RuoloCapacitasDiagnosis,
  RuoloCapacitasCheckComuneItemResponse,
  RuoloCapacitasCheckItemResponse,
  RuoloCapacitasCheckStatus,
} from "@/types/ruolo";

export function getRuoloCapacitasCheckStatusDescription(status: RuoloCapacitasCheckStatus): string {
  switch (status) {
    case "amount_mismatch":
      return "Il soggetto esiste nel ruolo e nel batch Capacitas attivo, ma il ricalcolo GAIA 0648 e/o 0985 non coincide col ruolo.";
    case "only_in_ruolo":
      return "Il soggetto compare nel ruolo importato ma non risulta nel batch Capacitas attivo dell'anno selezionato.";
    case "only_in_capacitas":
      return "Il soggetto compare nel batch Capacitas attivo dell'anno selezionato ma non risulta nel ruolo importato.";
    case "matched":
      return "I valori del soggetto risultano allineati tra ruolo inCASS e calcolo GAIA sul batch Capacitas attivo.";
    default:
      return status;
  }
}

export function getRuoloCapacitasCheckVerificationHint(status: RuoloCapacitasCheckStatus): string {
  switch (status) {
    case "amount_mismatch":
      return "Confronta il ruolo inCASS con il calcolo GAIA del batch Capacitas attivo e usa l'Excel Capacitas come riferimento di supporto.";
    case "only_in_ruolo":
      return "Verifica se il soggetto e stato escluso dal batch Capacitas attivo, ha un CF/P.IVA non normalizzato o appartiene a un perimetro non importato.";
    case "only_in_capacitas":
      return "Verifica se il soggetto ha avvisi mancanti nel ruolo e se il batch Capacitas attivo contiene righe senza controparte pubblicata.";
    case "matched":
      return "Nessuna azione operativa richiesta: il soggetto quadra sui tributi confrontabili.";
    default:
      return "Verifica manualmente la riga confrontando ruolo e Capacitas.";
  }
}

export function formatRuoloCapacitasDiagnosis(diagnosis: RuoloCapacitasDiagnosis): string {
  switch (diagnosis) {
    case "problema_ruolo":
      return "Priorita ruolo";
    case "problema_ricalcolo_gaia":
      return "Priorita GAIA";
    case "problema_snapshot_excel":
      return "Priorita Excel";
    case "allineato":
      return "Allineato";
    default:
      return diagnosis;
  }
}

export function getRuoloCapacitasDiagnosisDescription(diagnosis: RuoloCapacitasDiagnosis): string {
  switch (diagnosis) {
    case "problema_ruolo":
      return "Il primo controllo operativo va fatto sul ruolo inCASS, cioe sui dati raccolti dal partitario del ruolo pubblicato.";
    case "problema_ricalcolo_gaia":
      return "Il primo controllo operativo va fatto sul ricalcolo GAIA: imponibile, aliquote, coltura ed ettari.";
    case "problema_snapshot_excel":
      return "Il primo controllo operativo va fatto sull'Excel Capacitas importato nel batch attivo.";
    case "allineato":
      return "Nessuna anomalia prioritaria rilevata.";
    default:
      return diagnosis;
  }
}

export function getRuoloCapacitasDiagnosisBadgeClassName(diagnosis: RuoloCapacitasDiagnosis): string {
  switch (diagnosis) {
    case "problema_ruolo":
      return "bg-amber-50 text-amber-800 border border-amber-200";
    case "problema_ricalcolo_gaia":
      return "bg-sky-50 text-sky-800 border border-sky-200";
    case "problema_snapshot_excel":
      return "bg-fuchsia-50 text-fuchsia-800 border border-fuchsia-200";
    default:
      return "bg-gray-100 text-gray-700 border border-gray-200";
  }
}

export function getRuoloCapacitasEvaluationSummary(item: RuoloCapacitasCheckItemResponse): string {
  if (item.anomaly_driven_case) {
    return "Il gap GAIA risulta quasi interamente spiegato da righe gia marcate anomale: conviene partire da quelle particelle.";
  }
  switch (item.diagnosis) {
    case "problema_ruolo":
      return "GAIA ed Excel sono piu coerenti del ruolo: il caso va valutato prima sul lato avviso/partitario.";
    case "problema_ricalcolo_gaia":
      return "Il ruolo inCASS e piu vicino all'Excel Capacitas che al calcolo GAIA: conviene verificare imponibile, ettari, coltura e aliquote.";
    case "problema_snapshot_excel":
      return "Ruolo e GAIA sono piu vicini dello snapshot importato: conviene rivalutare il batch Excel o l'import storico.";
    default:
      return "Il caso non mostra segnali prioritari aggiuntivi.";
  }
}

export function getRuoloCapacitasEvidenceLines(item: RuoloCapacitasCheckItemResponse): string[] {
  const lines: string[] = [];
  const ruoloVsGaia = Math.abs(item.delta_totale_confrontabile);
  const gaiaVsExcel = Math.abs(item.delta_gaia_excel_totale_confrontabile);

  if (item.status === "only_in_ruolo") {
    lines.push("Presente nel ruolo ma assente nel batch Capacitas attivo.");
  }
  if (item.status === "only_in_capacitas") {
    lines.push("Presente nel batch Capacitas attivo ma senza controparte nel ruolo.");
  }
  if (item.status === "amount_mismatch") {
    lines.push(`Delta ruolo/GAIA: ${formatEuro(item.delta_totale_confrontabile)}.`);
    lines.push(`Delta GAIA/Excel: ${formatEuro(item.delta_gaia_excel_totale_confrontabile)}.`);
    if (item.anomalous_rows_count > 0) {
      lines.push(
        `Righe anomale ${item.anomalous_rows_count}, righe pulite ${item.clean_rows_count}, copertura gap ${formatPercent(item.anomaly_gap_share)}.`,
      );
    }
    if (gaiaVsExcel <= 1) {
      lines.push("GAIA ed Excel sono sostanzialmente allineati.");
    } else if (gaiaVsExcel >= ruoloVsGaia) {
      lines.push("Lo scostamento principale nasce tra calcolo GAIA ed Excel Capacitas.");
    } else {
      lines.push("Il ruolo resta il riferimento piu distante rispetto agli altri due valori.");
    }
  }
  return lines;
}

export function getRuoloCapacitasComuneExplanation(item: RuoloCapacitasCheckComuneItemResponse): string {
  const absDelta = Math.abs(item.delta_totale_confrontabile);
  const sourceNames = new Set([...(item.source_comuni_ruolo ?? []), ...(item.source_comuni_capacitas ?? [])]);
  if (sourceNames.size > 1) {
    return "Aggregato su denominazioni territoriali normalizzate: controlla le etichette sorgenti sotto il nome comune prima di leggere il delta.";
  }
  if (absDelta < 0.01) {
    return "Il comune risulta sostanzialmente allineato: usa il drill-down solo per controlli puntuali.";
  }
  return "Il delta e aggregato su tutti i soggetti del comune: confronta ruolo inCASS e calcolo GAIA, poi usa l'Excel Capacitas come supporto diagnostico.";
}

export function RuoloCapacitasAmountStack({
  amount0648,
  amount0985,
  total,
  tone = "neutral",
}: {
  amount0648: number;
  amount0985: number;
  total: number;
  tone?: "neutral" | "ruolo" | "capacitas" | "delta";
}) {
  const toneClassName =
    tone === "ruolo"
      ? "text-[#183325]"
      : tone === "capacitas"
        ? "text-sky-900"
        : tone === "delta"
          ? "text-amber-900"
          : "text-gray-800";

  return (
    <div className={`space-y-1 text-xs ${toneClassName}`}>
      <p>0648: <span className="font-semibold">{formatEuro(amount0648)}</span></p>
      <p>0985: <span className="font-semibold">{formatEuro(amount0985)}</span></p>
      <p>Totale confrontabile: <span className="font-semibold">{formatEuro(total)}</span></p>
    </div>
  );
}

export function RuoloCapacitasDetailList({ children }: { children: ReactNode }) {
  return <div className="mt-2 space-y-1 text-xs leading-5 text-gray-500">{children}</div>;
}

function formatEuro(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function formatPercent(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { maximumFractionDigits: 1 }).format(value) + "%";
}

export function getRuoloCapacitasPositionLine(item: RuoloCapacitasCheckItemResponse): string {
  const ruolo = item.ruolo_display_name ?? "assente";
  const capacitas = item.capacitas_display_name ?? "assente";
  return `Ruolo: ${ruolo} · Batch Capacitas attivo: ${capacitas}`;
}
