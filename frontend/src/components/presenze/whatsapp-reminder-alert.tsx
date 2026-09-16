import Link from "next/link";

import type { PresenzeDailyRecord } from "@/types/api";

function isPastWorkDate(value: string): boolean {
  const today = new Date();
  const current = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return value < current;
}

export function isWhatsAppReminderCandidate(record: PresenzeDailyRecord): boolean {
  if (!isPastWorkDate(record.work_date) || record.validation_status === "validated") return false;
  const visible = record.punches.filter((punch) => punch.entry_time || punch.exit_time);
  const openEntries = visible.filter((punch) => punch.entry_time && !punch.exit_time);
  const orphanExit = visible.some((punch) => punch.exit_time && !punch.entry_time);
  return openEntries.length > 0 || orphanExit;
}

export function WhatsAppReminderAlert({ record }: { record: PresenzeDailyRecord }) {
  if (!isWhatsAppReminderCandidate(record)) return null;
  return (
    <div className="mt-4 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sky-950" role="status">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">Avviso promemoria WhatsApp</p>
          <p className="mt-1 text-sm font-medium">Questa giornata presenta una timbratura incompleta e può entrare nel prossimo invio.</p>
          <p className="mt-1 text-xs text-sky-800">Il messaggio parte solo per giornate chiuse non validate, con utente GAIA collegato e numero valido, se il provider WhatsApp è abilitato.</p>
        </div>
        <Link className="btn-secondary shrink-0 border-sky-300 bg-white text-sky-800 hover:bg-sky-100" href="/presenze/whatsapp">
          Gestisci WhatsApp
        </Link>
      </div>
    </div>
  );
}
