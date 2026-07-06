import { afterEach, describe, expect, test, vi } from "vitest";

import { request } from "@/lib/api";

describe("api request helper", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("returns undefined for 204 no content responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, {
        status: 204,
        statusText: "No Content",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(request<void>("/presenze/sync/jobs/job-1", { method: "DELETE" })).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
