import type { ReactNode } from "react";

import type {
  RuoloCapacitasCheckComuneItemResponse,
  RuoloCapacitasCheckItemResponse,
  RuoloCapacitasCheckStatus,
} from "@/types/ruolo";

export function getRuoloCapacitasCheckStatusDescription(status: RuoloCapacitasCheckStatus): string {
  switch (status) {
    case "amount_mismatch":
      return "Il soggetto esiste in entrambi i dataset, ma gli importi 0648 e/o 0985 non coincidono.";
    case "only_in_ruolo":
      return "Il soggetto compare nel ruolo importato ma non risulta nel dataset Capacitas dell'anno selezionato.";
    case "only_in_capacitas":
      return "Il soggetto compare nel dataset Capacitas dell'anno selezionato ma non risulta nel ruolo importato.";
    case "matched":
      return "I valori del soggetto risultano allineati tra ruolo e Capacitas.";
    default:
      return status;
  }
}

export function getRuoloCapacitasCheckVerificationHint(status: RuoloCapacitasCheckStatus): string {
  switch (status) {
    case "amount_mismatch":
      return "Confronta gli avvisi del ruolo con i valori Capacitas del medesimo CF/P.IVA e verifica se mancano righe, import o bonifiche.";
    case "only_in_ruolo":
      return "Verifica se il soggetto e stato escluso da Capacitas, ha un CF/P.IVA non normalizzato o appartiene a un perimetro non ancora importato.";
    case "only_in_capacitas":
      return "Verifica se il soggetto ha avvisi mancanti nel ruolo, e se il CF/P.IVA e corretto o presente solo nell'anagrafica Capacitas.";
    case "matched":
      return "Nessuna azione operativa richiesta: il soggetto quadra sui tributi confrontabili.";
    default:
      return "Verifica manualmente la riga confrontando ruolo e Capacitas.";
  }
}

export function getRuoloCapacitasComuneExplanation(item: RuoloCapacitasCheckComuneItemResponse): string {
  const absDelta = Math.abs(item.delta_totale_confrontabile);
  if (absDelta < 0.01) {
    return "Il comune risulta sostanzialmente allineato: usa il drill-down solo per controlli puntuali.";
  }
  return "Il delta e aggregato su tutti i soggetti del comune: apri gli avvisi del territorio per isolare le posizioni che generano lo scostamento.";
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

export function getRuoloCapacitasPositionLine(item: RuoloCapacitasCheckItemResponse): string {
  const ruolo = item.ruolo_display_name ?? "assente";
  const capacitas = item.capacitas_display_name ?? "assente";
  return `Ruolo: ${ruolo} · Capacitas: ${capacitas}`;
}
