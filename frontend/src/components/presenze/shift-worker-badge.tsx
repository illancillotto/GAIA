import type { PresenzeDailyRecord } from "@/types/api";
export function ShiftWorkerBadge({ record }: { record: PresenzeDailyRecord }) {
  const labels = { acquaiolo: "Turnista acquaiolo", telecontrollo: "Turnista telecontrollo", tecnico_turnista: "Tecnico/Turnista" };
  const label = labels[record.shift_worker_type as keyof typeof labels];
  if (!label) return null;
  return <span className="ml-1 rounded bg-indigo-100 px-1 text-indigo-700" title={label}>T</span>;
}
