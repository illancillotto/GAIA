"use client";

import type { PresenzeDailyRecord } from "@/types/api";
import { MealVoucherControl } from "./meal-voucher-control";
import { ShiftWorkerControl } from "./shift-worker-control";

type Props = {
  record: PresenzeDailyRecord;
  canEdit: boolean;
  canViewAll: boolean | undefined;
  onSaved: (record: PresenzeDailyRecord) => void;
  onRangeSaved: () => void;
};

/** Daily voucher edits and employee-wide shift ranges have distinct permissions. */
export function DailyOperationalControls({ record, canEdit, canViewAll, onSaved, onRangeSaved }: Props) {
  function handleShiftSaved(updated: PresenzeDailyRecord) {
    onSaved(updated);
    onRangeSaved();
  }
  return <>
    <MealVoucherControl record={record} disabled={!canEdit} onSaved={onSaved} />
    <ShiftWorkerControl key={record.id} record={record} disabled={!canEdit || !canViewAll} onSaved={handleShiftSaved} />
  </>;
}
