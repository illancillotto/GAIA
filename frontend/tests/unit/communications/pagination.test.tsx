import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { CommunicationsAccess } from "@/components/communications/workspace";
import { candidate, session } from "./fixtures";

const mocks = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("@/lib/communications-api", () => ({ communications: mocks.api }));
vi.mock("@/lib/use-session-bootstrap", () => ({ useSessionBootstrap: () => session }));
vi.mock("@/components/ruolo/module-page", () => ({ RuoloModulePage: ({ children }: { children: React.ReactNode }) => <main>{children}</main> }));
vi.mock("@/components/communications/composer", () => ({ CommunicationComposer: () => null }));
vi.mock("@/components/communications/source-preview", () => ({ SourcePreview: () => null }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

it.each([
  ["pec", 230, 10],
  ["email", 140, 6],
] as const)("navigates all %s candidate pages beyond page three and back without losing filters", async (channel, total, pages) => {
  const requested: number[] = [];
  mocks.api.mockImplementation((_token: string, path: string) => {
    if (!path.includes("/ruolo/candidates?")) return Promise.resolve([]);
    const query = new URL(path, "http://localhost").searchParams;
    expect(query.get(`has_${channel}`)).toBe("true");
    const page = Number(query.get("page"));
    requested.push(page);
    const start = (page - 1) * 25;
    return Promise.resolve({ total, items: Array.from({ length: Math.min(25, total - start) }, (_, index) => ({
      ...candidate, id: `candidate-${start + index + 1}`, notice_number: `${start + index + 1}/2021`,
    })) });
  });
  render(<CommunicationsAccess channel={channel} />);
  const nav = screen.getByRole("navigation", { name: "Paginazione candidati" });
  const previous = within(nav).getByRole("button", { name: "Precedente" });
  const next = within(nav).getByRole("button", { name: "Successiva" });
  async function expectPage(page: number) {
    await waitFor(() => expect(screen.queryByText("Caricamento candidati 2021...")).not.toBeInTheDocument());
    expect(within(nav).getByText(`${page} / ${pages}`)).toBeInTheDocument();
    const first = (page - 1) * 25 + 1;
    expect(screen.getByRole("row", { name: `Apri avviso ${first}/2021` })).toBeInTheDocument();
    expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(1 + Math.min(25, total - first + 1));
  }
  await expectPage(1);
  expect(previous).toBeDisabled();
  for (let page = 2; page <= pages; page++) {
    expect(next).toBeEnabled();
    fireEvent.click(next);
    await expectPage(page);
  }
  expect(next).toBeDisabled();
  for (let page = pages - 1; page >= 1; page--) {
    expect(previous).toBeEnabled();
    fireEvent.click(previous);
    await expectPage(page);
  }
  expect(previous).toBeDisabled();
  expect(requested).toEqual([
    ...Array.from({ length: pages }, (_, i) => i + 1),
    ...Array.from({ length: pages - 1 }, (_, i) => pages - i - 1),
  ]);
});

it("ignores an older slow candidate response after the operator has selected a later page", async () => {
  const pending = new Map<number, (value: unknown) => void>();
  mocks.api.mockImplementation((_token: string, path: string) => {
    if (!path.includes("/ruolo/candidates?")) return Promise.resolve([]);
    const page = Number(new URL(path, "http://localhost").searchParams.get("page"));
    return new Promise((resolve) => pending.set(page, resolve));
  });
  const response = (page: number) => ({ total: 230, items: [{ ...candidate, id: `page-${page}`, notice_number: `${page}/2021` }] });
  render(<CommunicationsAccess channel="pec" />);
  await act(async () => pending.get(1)!(response(1)));
  const nav = screen.getByRole("navigation", { name: "Paginazione candidati" });
  const next = within(nav).getByRole("button", { name: "Successiva" });
  fireEvent.click(next);
  fireEvent.click(next);
  fireEvent.click(next);
  await act(async () => pending.get(4)!(response(4)));
  expect(within(nav).getByText("4 / 10")).toBeInTheDocument();
  expect(screen.getByRole("row", { name: "Apri avviso 4/2021" })).toBeInTheDocument();
  await act(async () => {
    pending.get(3)!(response(3));
    pending.get(2)!(response(2));
  });
  expect(within(nav).getByText("4 / 10")).toBeInTheDocument();
  expect(screen.getByRole("row", { name: "Apri avviso 4/2021" })).toBeInTheDocument();
});
