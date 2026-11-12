import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useCandidates } from "@/components/communications/use-candidates";
import { candidate, account, template } from "./fixtures";

const api = vi.hoisted(() => vi.fn());
vi.mock("@/lib/communications-api", () => ({ communications: api }));
beforeEach(() => {
  api.mockReset();
  api.mockImplementation((_token, path) => Promise.resolve(path.includes("candidates?") ? { items: [candidate], total: 30 } : path === "/accounts" ? [account] : [template]));
});
afterEach(() => { cleanup(); vi.useRealTimers(); });

it("debounces typing, aborts obsolete requests and reuses catalogs across search and pagination", async () => {
  const { result } = renderHook(() => useCandidates("token", "pec", true));
  await waitFor(() => expect(result.current.loading).toBe(false));
  const originalSignal = api.mock.calls.find(call => call[1].includes("candidates?"))![4] as AbortSignal;
  vi.useFakeTimers();
  for (const q of ["m", "mon", "montisci"]) act(() => result.current.setFilters(value => ({ ...value, q })));
  expect(result.current.loading).toBe(true);
  expect(api.mock.calls.filter(call => call[1].includes("candidates?"))).toHaveLength(1);
  await act(async () => vi.advanceTimersByTimeAsync(300));
  expect(api.mock.calls.filter(call => call[1].includes("candidates?"))).toHaveLength(2);
  expect(api.mock.calls.at(-1)![1]).toContain("q=montisci");
  expect(originalSignal.aborted).toBe(true);
  expect(result.current.loading).toBe(false);
  await act(async () => result.current.setPage(2));
  expect(api.mock.calls.at(-1)![1]).toContain("page=2");
  expect(api.mock.calls.filter(call => call[1] === "/accounts")).toHaveLength(1);
  expect(api.mock.calls.filter(call => call[1] === "/templates")).toHaveLength(1);
  await act(async () => result.current.reload());
  expect(api.mock.calls.filter(call => call[1] === "/accounts")).toHaveLength(2);
  expect(api.mock.calls.filter(call => call[1] === "/templates")).toHaveLength(2);
});

it("shows candidates while catalogs are pending, then reports independent catalog errors", async () => {
  let rejectCatalog!: (error: Error) => void;
  api.mockImplementation((_token, path) => path.includes("candidates?") ? Promise.resolve({ items: [candidate], total: 1 }) : new Promise((_resolve, reject) => { rejectCatalog = reject; }));
  const { result } = renderHook(() => useCandidates("token", "pec", true));
  await waitFor(() => expect(result.current.data.items).toEqual([candidate]));
  expect(result.current.loading).toBe(false);
  await act(async () => rejectCatalog(new Error("Catalogo non disponibile")));
  expect(result.current.loadError).toBe("Catalogo non disponibile");
  expect(result.current.data.items).toEqual([candidate]);
});

it("ignores late success and errors after a filter change or unmount", async () => {
  let resolveList!: (value: unknown) => void;
  let rejectList!: (error: Error) => void;
  api.mockImplementation((_token, path) => path.includes("candidates?") ? new Promise((resolve, reject) => { resolveList = resolve; rejectList = reject; }) : Promise.resolve([]));
  const { result, unmount } = renderHook(() => useCandidates("token", "pec", false));
  const oldResolve = resolveList;
  const oldReject = rejectList;
  await act(async () => result.current.setPage(2));
  await act(async () => oldResolve({ items: [candidate], total: 99 }));
  expect(result.current.data.items).toEqual([]);
  expect(result.current.loading).toBe(true);
  const pendingReject = rejectList;
  unmount();
  await act(async () => { pendingReject(new Error("Aborted")); oldReject(new Error("Old")); });
});
