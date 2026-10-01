"use client";
import { useRef, useState } from "react";
import { updatePresenzeDailyRecord } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { PresenzeDailyRecord } from "@/types/api";

type Props = { record: PresenzeDailyRecord; disabled: boolean; onSaved: (record: PresenzeDailyRecord) => void };
export function MealVoucherControl({ record, disabled, onSaved }: Props) {
  const busy = useRef(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  async function toggle(enabled: boolean) {
    const token = getStoredAccessToken();
    if (!token || disabled || busy.current) return;
    busy.current = true;
    setSaving(true);
    setError("");
    try {
      onSaved(await updatePresenzeDailyRecord(token, record.id, { meal_voucher_manual: enabled }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Buono pasto non salvato");
    } finally {
      busy.current = false;
      setSaving(false);
    }
  }
  return <div className="rounded border p-2 text-sm">
    <p>Buono pasto: {record.meal_voucher_count ?? 0} · {record.meal_voucher_sources?.join(" + ") || "non riconosciuto"}</p>
    <label><input type="checkbox" aria-label="Buono pasto manuale" checked={record.meal_voucher_manual === true} disabled={disabled || saving} onChange={event => void toggle(event.target.checked)} /> Buono pasto manuale</label>
    {saving && <p role="status">Salvataggio…</p>}
    {error && <p role="alert">{error}</p>}
    {record.meal_voucher_automatic && <p className="text-xs">Il buono automatico rimane riconosciuto anche rimuovendo quello manuale.</p>}
  </div>;
}
