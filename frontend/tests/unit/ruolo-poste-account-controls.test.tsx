import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { AccountSelector, LegacyAccountBinding, UploadAudit } from "@/components/ruolo/poste-dispatch/account-controls";
import type { PosteDispatchItem } from "@/types/ruolo-poste-dispatch";

const api = vi.hoisted(() => ({ listPosteAccounts: vi.fn(), bindPosteAccount: vi.fn() }));
vi.mock("@/lib/ruolo-poste-dispatch-api", () => api);
const accounts = [{ id: 1, label: "Primo", username: "first", active: true }, { id: 2, label: "Storico", username: "second", active: false }];
beforeEach(() => { vi.resetAllMocks(); api.listPosteAccounts.mockResolvedValue(accounts); });
afterEach(cleanup);

it("requires an explicit active account while filters also include old accounts", async () => {
  const changed = vi.fn();
  const view = render(<AccountSelector token="t" label="Account" value={null} onChange={changed} />);
  expect(await screen.findByRole("option", { name: "Primo · first" })).toBeVisible();
  expect(screen.queryByRole("option", { name: "Storico · second" })).toBeNull();
  expect(screen.getByLabelText("Account")).toHaveValue("");
  fireEvent.change(screen.getByLabelText("Account"), { target: { value: "1" } });
  expect(changed).toHaveBeenLastCalledWith(1);
  view.rerender(<AccountSelector token="t" label="Account" value={1} onChange={changed} filter />);
  expect(screen.getByRole("option", { name: "Storico · second" })).toBeVisible();
  expect(screen.getByRole("option", { name: "Tutti gli account" })).toBeVisible();
  fireEvent.change(screen.getByLabelText("Account"), { target: { value: "" } });
  expect(changed).toHaveBeenLastCalledWith(null);
});

it.each([[new Error("non disponibile"), "non disponibile"], ["offline", "Account Poste non caricati"]])("shows account loading errors (%s)", async (error, message) => {
  api.listPosteAccounts.mockRejectedValue(error);
  render(<AccountSelector token="t" label="Account" value={null} onChange={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent(message);
});

it.each([false, true])("ignores stale account responses after unmount (reject=%s)", async (reject) => {
  let resolve!: (value: unknown) => void;
  let fail!: (value: unknown) => void;
  api.listPosteAccounts.mockReturnValue(new Promise((yes, no) => { resolve = yes; fail = no; }));
  const view = render(<AccountSelector token="t" label="Account" value={null} onChange={vi.fn()} />);
  view.unmount();
  await act(async () => { if (reject) fail(new Error("stale")); else resolve(accounts); });
  expect(screen.queryByRole("alert")).toBeNull();
});

it("binds a historical lot to the chosen account and waits for completion", async () => {
  let resolve!: (value: unknown) => void;
  api.bindPosteAccount.mockReturnValue(new Promise((yes) => { resolve = yes; }));
  const changed = vi.fn();
  render(<LegacyAccountBinding token="t" lotId="legacy" onChanged={changed} />);
  const button = screen.getByRole("button", { name: "Associa account" });
  expect(button).toBeDisabled();
  await screen.findByRole("option", { name: "Primo · first" });
  fireEvent.change(screen.getByLabelText("Account del lotto storico"), { target: { value: "1" } });
  fireEvent.click(button);
  expect(button).toBeDisabled();
  expect(api.bindPosteAccount).toHaveBeenCalledWith("t", "legacy", 1);
  await act(async () => resolve({}));
  expect(changed).toHaveBeenCalledOnce();
  expect(button).not.toBeDisabled();
});

it.each([[new Error("account diverso"), "account diverso"], ["offline", "Account non associato"]])("reports a refused historical binding (%s)", async (error, message) => {
  api.bindPosteAccount.mockRejectedValue(error);
  render(<LegacyAccountBinding token="t" lotId="legacy" onChanged={vi.fn()} />);
  await screen.findByRole("option", { name: "Primo · first" });
  fireEvent.change(screen.getByLabelText("Account del lotto storico"), { target: { value: "1" } });
  fireEvent.click(screen.getByRole("button", { name: "Associa account" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(message);
  await waitFor(() => expect(screen.getByRole("button", { name: "Associa account" })).not.toBeDisabled());
});

it("distinguishes a known upload operator from an unattributed historical upload", () => {
  const view = render(<UploadAudit item={{ upload_requested_by_username: null } as PosteDispatchItem} />);
  expect(screen.getByText(/non ancora attribuito/)).toBeVisible();
  view.rerender(<UploadAudit item={{ upload_requested_by_username: "alessandro", upload_job_id: 15 } as PosteDispatchItem} />);
  expect(screen.getByText(/Caricamento avviato da alessandro · operazione 15/)).toBeVisible();
});
