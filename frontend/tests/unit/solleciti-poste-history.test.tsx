import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import { PosteHistory } from "@/components/ruolo/solleciti/poste-history";
import type { BatchPosteDispatch } from "@/lib/ruolo-batch-overview-api";

afterEach(cleanup);

const sent: BatchPosteDispatch = {
  id: "attempt-1", notice_number: "020210012345678", status: "sent",
  poste_draft_id: "POSTE-123", poste_status: "Accettato", draft_created_at: "2026-11-02T10:00:00Z",
  sent_at: "2026-11-03T10:00:00Z", tracking_number: "TRACK-123",
  upload_requested_by_username: "synthetic-operator", poste_username: "synthetic-account",
  updated_at: "2026-11-04T10:00:00Z",
};

it("shows the stored shipment ID, dates, tracking, account and operator", () => {
  render(<PosteHistory dispatches={[sent]} />);
  const history = screen.getByRole("region", { name: "Storico Posta Online" });
  expect(within(history).getByText("Spedito")).toBeVisible();
  for (const value of ["POSTE-123", "TRACK-123", "synthetic-operator", "synthetic-account", "Accettato"]) expect(within(history).getByText(value)).toBeVisible();
  expect(within(history).getByText(/^02\/11\/26/)).toBeVisible();
  expect(within(history).getByText(/^03\/11\/26/)).toBeVisible();
  expect(within(history).getByText(/^04\/11\/26/)).toBeVisible();
});

it("keeps a priced draft distinct from a shipment and explains missing historical metadata", () => {
  render(<PosteHistory dispatches={[{ ...sent, status: "draft_priced", poste_draft_id: null, poste_status: null, draft_created_at: null, sent_at: null, tracking_number: null, poste_username: null, upload_requested_by_username: null }]} />);
  expect(screen.getByText("Bozza prezzata")).toBeVisible();
  expect(screen.queryByText("Spedito", { exact: true })).toBeNull();
  expect(screen.getAllByText("Non disponibile")).toHaveLength(3);
  expect(screen.getAllByText("Non registrato")).toHaveLength(2);
  expect(screen.getAllByText("-")).toHaveLength(2);
});

it("does not show a shipment section without stored attempts", () => {
  const { container, rerender } = render(<PosteHistory dispatches={[]} />);
  expect(container).toBeEmptyDOMElement();
  rerender(<PosteHistory />);
  expect(container).toBeEmptyDOMElement();
});

it("keeps distinct attempts visible, including a cancelled one", () => {
  render(<PosteHistory dispatches={[sent, { ...sent, id: "attempt-2", status: "cancelled", poste_draft_id: "OLD-POSTE", sent_at: null }]} />);
  expect(screen.getAllByRole("article")).toHaveLength(2);
  expect(screen.getByText("Annullato")).toBeVisible();
  expect(screen.getByText("OLD-POSTE")).toBeVisible();
});
