import type { PresenzeSyncJob } from "@/types/api";
export function relevantInazJobs(jobs: PresenzeSyncJob[], month: string, employeeCode?: string): PresenzeSyncJob[] {
  return jobs.filter(job => {
    const codes = job.params_json?.employee_codes;
    const includesPerson = !employeeCode || !Array.isArray(codes) || codes.length === 0 || codes.includes(employeeCode);
    return job.credential_id != null && job.period_start.slice(0, 7) <= month && job.period_end.slice(0, 7) >= month && includesPerson;
  });
}
export function lastSuccessfulInazJob(jobs: PresenzeSyncJob[]): PresenzeSyncJob | undefined {
  return jobs.filter(job => job.status === "completed" && job.records_errors === 0 && job.finished_at).sort((a, b) => b.finished_at!.localeCompare(a.finished_at!))[0];
}
