import { beforeEach, describe, expect, test, vi } from "vitest";

import { listSubjectDomandeIrrigue } from "@/lib/catasto-domande-irrigue-subject-api";

const request = vi.fn();

vi.mock("@/lib/api", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/api")>();
  return {
    ...actual,
    request: (...args: unknown[]) => request(...args),
  };
});

describe("listSubjectDomandeIrrigue", () => {
  beforeEach(() => {
    request.mockReset();
    request.mockResolvedValue({ items: [], total: 0, limit: 120, offset: 0 });
  });

  test("calls domande irrigue list filtered by subject", async () => {
    await listSubjectDomandeIrrigue("token", "subject-1");

    expect(request).toHaveBeenCalledWith("/catasto/domande-irrigue?subject_id=subject-1", {
      headers: { Authorization: "Bearer token" },
    });
  });

  test("serializes optional list params", async () => {
    await listSubjectDomandeIrrigue("token", "subject-1", {
      anno: 2026,
      stato: " Aperta ",
      utenzaId: "utenza-1",
      limit: 50,
      offset: 25,
    });

    expect(request).toHaveBeenCalledWith(
      "/catasto/domande-irrigue?subject_id=subject-1&utenza_id=utenza-1&anno=2026&stato=Aperta&limit=50&offset=25",
      {
        headers: { Authorization: "Bearer token" },
      },
    );
  });
});
