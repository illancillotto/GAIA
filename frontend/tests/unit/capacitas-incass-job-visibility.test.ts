import { describe, expect, test } from "vitest";

import {
  getVisibleCapacitasInCassJobs,
  INCASS_JOB_COLLAPSED_LIMIT,
  isCapacitasInCassActiveJobStatus,
  isCapacitasInCassRunningJobStatus,
} from "@/lib/capacitas-incass-job-visibility";

type Job = {
  id: number;
  status: string;
};

function job(id: number, status: string): Job {
  return { id, status };
}

describe("capacitas incass job visibility", () => {
  test("classifies active and running statuses", () => {
    expect(isCapacitasInCassActiveJobStatus("pending")).toBe(true);
    expect(isCapacitasInCassActiveJobStatus("processing")).toBe(true);
    expect(isCapacitasInCassActiveJobStatus("queued_resume")).toBe(true);
    expect(isCapacitasInCassActiveJobStatus("succeeded")).toBe(false);

    expect(isCapacitasInCassRunningJobStatus("processing")).toBe(true);
    expect(isCapacitasInCassRunningJobStatus("queued_resume")).toBe(true);
    expect(isCapacitasInCassRunningJobStatus("pending")).toBe(false);
  });

  test("returns every job when expanded", () => {
    const jobs = [job(1, "pending"), job(2, "processing"), job(3, "succeeded")];

    expect(getVisibleCapacitasInCassJobs(jobs, true)).toEqual({
      items: jobs,
      hiddenCount: 0,
    });
  });

  test("prioritises running jobs and hides overflow in collapsed mode", () => {
    const jobs = [
      job(384, "pending"),
      job(383, "pending"),
      job(173, "processing"),
      job(172, "succeeded"),
      job(171, "completed_with_errors"),
    ];

    const result = getVisibleCapacitasInCassJobs(jobs, false, 3);

    expect(result.items.map((item) => item.id)).toEqual([173, 384, 383]);
    expect(result.hiddenCount).toBe(2);
  });

  test("does not report hidden jobs when the collapsed list fits the limit", () => {
    const jobs = Array.from({ length: INCASS_JOB_COLLAPSED_LIMIT }, (_, index) => job(index + 1, "pending"));

    const result = getVisibleCapacitasInCassJobs(jobs, false);

    expect(result.items).toHaveLength(INCASS_JOB_COLLAPSED_LIMIT);
    expect(result.hiddenCount).toBe(0);
  });
});
