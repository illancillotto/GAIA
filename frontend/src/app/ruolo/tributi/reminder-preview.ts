import { downloadTributiReminderDocument } from "@/lib/ruolo-api";
import type { RuoloTributiReminderBatchItemResponse, RuoloTributiReminderBatchResponse } from "@/types/ruolo";

export async function loadReminderPreview(token: string, batch: RuoloTributiReminderBatchResponse, templateLabel: string) {
  const item = batch.items.find((candidate) => candidate.status === "generated" && candidate.download_url)
    ?? batch.items.find((candidate) => candidate.status === "draft")
    ?? batch.items[0];
  if (!item) throw new Error(`PDF sollecito non disponibile per la preview ${templateLabel}.`);
  const isDraft = item.status === "draft";
  const url = isDraft
    ? `/ruolo/tributi/solleciti/batches/${batch.id}/items/${item.id}/preview`
    : item.download_url;
  if (!url) throw new Error(item.error_detail || `PDF sollecito non disponibile per la preview ${templateLabel}.`);
  const blob = await downloadTributiReminderDocument(token, url);
  return { item, blob, label: isDraft ? `${templateLabel} · BOZZA - NON VALIDA PER INVIO` : templateLabel };
}

export function reminderPreviewFilename(item: RuoloTributiReminderBatchItemResponse) {
  if (item.status === "draft") return `bozza-${item.codice_fiscale}_avviso_sollecito.pdf`;
  return item.generated_document_path?.split("/").pop() || `${item.codice_fiscale}_avviso_sollecito.pdf`;
}
