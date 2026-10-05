import { request } from "./core";
import type { PresenzeDailyRecord } from "@/types/api";

export type ShiftWorkerType = "none" | "acquaiolo" | "telecontrollo";
export type ShiftWorkerAssignment = { shift_worker_type: ShiftWorkerType; date_from: string; date_to: string | null };

export async function assignPresenzeShiftWorker(token: string, recordId: string, assignment: ShiftWorkerAssignment) {
  return request<PresenzeDailyRecord>(`/presenze/giornaliere/${encodeURIComponent(recordId)}/turnista`, {
    method: "POST", headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(assignment)
  });
}
