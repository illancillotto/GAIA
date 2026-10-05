import type { PresenzeDailyRecord } from "@/types/api";
export function ShiftWorkerBadge({ record }: { record: PresenzeDailyRecord }) {
  if (record.shift_worker_type !== "acquaiolo" && record.shift_worker_type !== "telecontrollo") return null;
  const label = record.shift_worker_type === "acquaiolo" ? "Turnista acquaiolo" : "Turnista telecontrollo";
  return <span className="ml-1 rounded bg-indigo-100 px-1 text-indigo-700" title={label}>T</span>;
}
