import type { RegisterDetail } from "@/types/notice-register";
import { JsonDetails, NOTIFICATIONS, panelClass } from "./presentation";

export function DocumentComparison({ document }: { document: RegisterDetail }) {
  return <section aria-label="Documento di confronto" className={`${panelClass} space-y-2 text-sm`}>
    <h4 className="break-all font-semibold">{document.document_number}</h4>
    <p>CF: {document.tax_code ?? "Assente"} | Emesso: {document.issued_on ?? "Data assente"}</p>
    <p>Origine: {document.source_system} | Versione: {document.version}</p>
    <p>Notifica: {NOTIFICATIONS[document.notification_state]}</p>
    <ul>{document.positions.map((p) => <li key={p.id} className="break-all">{p.tax_year} | {p.source_namespace}: {p.source_reference}</li>)}</ul>
    <JsonDetails title="Originale del documento esistente" value={document.original_json} />
  </section>;
}
