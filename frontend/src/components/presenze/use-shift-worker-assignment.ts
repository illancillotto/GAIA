"use client";
import { useRef, useState } from "react";
import { assignPresenzeShiftWorker, type ShiftWorkerType } from "@/lib/api/presenze-shift-workers";
import { getStoredAccessToken } from "@/lib/auth";
import type { PresenzeDailyRecord } from "@/types/api";

export function useShiftWorkerAssignment(record: PresenzeDailyRecord, disabled: boolean, onSaved: (record: PresenzeDailyRecord) => void) {
  const [kind, setKind] = useState<ShiftWorkerType>(record.shift_worker_type ?? "none");
  const [from, setFrom] = useState(record.work_date);
  const [to, setTo] = useState(record.work_date);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const busy = useRef(false);
  const month = record.work_date.slice(0, 7);
  const first = month + "-01";
  const last = new Date(Date.UTC(Number(month.slice(0, 4)), Number(month.slice(5, 7)), 0)).toISOString().slice(0, 10);
  const locked = record.shift_worker_source === "gate";
  async function save() {
    const token = getStoredAccessToken();
    if (!token || disabled || locked || busy.current) return;
    if (!from || !to || from > to || from.slice(0, 7) !== month || to.slice(0, 7) !== month) {
      setError("Selezionare un intervallo ordinato nello stesso mese"); return;
    }
    busy.current = true; setSaving(true); setError("");
    try { onSaved(await assignPresenzeShiftWorker(token, record.id, { shift_worker_type: kind, date_from: from, date_to: to })); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Assegnazione non salvata"); }
    finally { busy.current = false; setSaving(false); }
  }
  return { kind, setKind, from, setFrom, to, setTo, error, saving, first, last, locked, save };
}
