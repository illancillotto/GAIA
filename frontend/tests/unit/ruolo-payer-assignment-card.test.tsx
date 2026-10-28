import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { PayerAssignmentCard } from "@/app/ruolo/tributi/payer-assignment-card";
import type { RuoloPayerAssignment } from "@/types/ruolo-payer";

const auth = vi.hoisted(() => ({ token: "token" as string | null }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => auth.token }));

const heir: RuoloPayerAssignment = {
  id: "a1",
  reason: "decesso",
  reason_label: "Decesso: paga l'erede",
  notes: "erede unico",
  payer_subject_id: "s1",
  payer_tax_code: "FLRFRZ68C17F272I",
  payer_name: "FLORIS FABRIZIO",
  payer_address: "VIA POLA N 1 09030 SARDARA",
  created_at: "2026-10-27T08:00:00Z",
  voided_at: null,
};
const voided = { ...heir, id: "a0", notes: null, payer_address: null, payer_name: null, voided_at: "2026-10-27T09:00:00Z" };

function reply(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

const fetchMock = vi.fn();

beforeEach(() => {
  auth.token = "token";
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("payer assignment card", () => {
  test("does not load without a session or save after the session expires", async () => {
    auth.token = null;
    const view = render(<PayerAssignmentCard avvisoId="av1" />);
    expect(fetchMock).not.toHaveBeenCalled();
    view.unmount();

    auth.token = "token";
    fetchMock.mockResolvedValueOnce(reply({ active: null, history: [] }));
    render(<PayerAssignmentCard avvisoId="av1" />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    auth.token = null;
    fireEvent.change(screen.getByLabelText("CF / P.IVA di chi paga"), { target: { value: heir.payer_tax_code } });
    fireEvent.click(screen.getByRole("button", { name: "Collega pagatore" }));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  test("links a payer, shows the history and removes it", async () => {
    fetchMock
      .mockResolvedValueOnce(reply({ active: null, history: [] }))
      .mockResolvedValueOnce(reply({ active: heir, history: [heir, voided] }))
      .mockResolvedValueOnce(reply({ active: null, history: [{ ...heir, voided_at: "2026-10-27T10:00:00Z" }, voided] }));
    render(<PayerAssignmentCard avvisoId="av1" />);
    expect(await screen.findByText("Paga l'intestatario dell'avviso.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Collega pagatore" }));
    expect(screen.getByRole("status")).toHaveTextContent("Indica il codice fiscale");
    expect(fetchMock).toHaveBeenCalledTimes(1);

    fireEvent.change(screen.getByLabelText("CF / P.IVA di chi paga"), { target: { value: " flrfrz68c17f272i " } });
    fireEvent.change(screen.getByLabelText("Nota"), { target: { value: "erede unico" } });
    fireEvent.click(screen.getByRole("button", { name: "Collega pagatore" }));
    expect(await screen.findByText(/Paga: FLORIS FABRIZIO/)).toBeInTheDocument();
    expect(screen.getByText("VIA POLA N 1 09030 SARDARA")).toBeInTheDocument();
    expect(screen.getByText(/erede unico/)).toBeInTheDocument();
    expect(screen.getByText("Storico (1)")).toBeInTheDocument();
    expect(screen.getByText(/^- \(FLRFRZ68C17F272I\)/)).toBeInTheDocument();
    const [url, init] = fetchMock.mock.calls[1];
    expect(url).toContain("/ruolo/tributi/avvisi/av1/payer");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body)).toEqual({ payer_tax_code: "FLRFRZ68C17F272I", reason: "decesso", notes: "erede unico" });

    fireEvent.click(screen.getByRole("button", { name: "Rimuovi pagatore" }));
    expect(await screen.findByText("Pagatore rimosso: paga l'intestatario.")).toBeInTheDocument();
    expect(fetchMock.mock.calls[2][1].method).toBe("DELETE");
    expect(screen.getByText("Storico (2)")).toBeInTheDocument();
  });

  test("shows a missing payer address and API errors", async () => {
    fetchMock
      .mockResolvedValueOnce(reply({ active: { ...heir, notes: null, payer_address: null, payer_name: null }, history: [] }))
      .mockResolvedValueOnce(reply({ detail: "MRENRC69M15L321N non e presente in anagrafica" }, 422));
    render(<PayerAssignmentCard avvisoId="av2" />);
    expect(await screen.findByText("Indirizzo non presente in anagrafica")).toBeInTheDocument();
    expect(screen.getByText(/Paga: -/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("CF / P.IVA di chi paga"), { target: { value: "MRENRC69M15L321N" } });
    fireEvent.change(screen.getByLabelText("Motivo"), { target: { value: "vendita" } });
    fireEvent.click(screen.getByRole("button", { name: "Sostituisci pagatore" }));
    expect(await screen.findByText(/non e presente in anagrafica/)).toBeInTheDocument();
  });

  test("reports a failed load and a non-error rejection", async () => {
    fetchMock.mockRejectedValueOnce("offline");
    render(<PayerAssignmentCard avvisoId="av3" />);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Operazione non riuscita"));
  });
});
