import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StepAvvisoCard } from "@/components/ruolo/step-avviso-card";
import type { StepAvvisoLink } from "@/types/step";

const api = vi.hoisted(() => ({ listStepLinksForAvviso: vi.fn() }));
vi.mock("@/lib/api/step", () => api);

function link(overrides: Partial<StepAvvisoLink> = {}): StepAvvisoLink {
  return {
    contribuente_id: "c1",
    codice_fiscale: "RSSMRA80A01G113X",
    denominazione: "ROSSI MARIO",
    documento_id: "d1",
    num_doc: "20241421500000003",
    data_notifica: "2024-11-16",
    pdf_status: "downloaded",
    link: {
      id: "l1",
      documento_id: "d1",
      reference_key: "020190006018040",
      codice_cnc: "020190006018040",
      anno_rif: 2019,
      status: "linked",
      ruolo_avviso_id: "a1",
      candidate_avviso_ids: null,
      tributi_count: 3,
      imp_carico: "50.00",
      imp_carico_pagato: "10.00",
      imp_discaricato: "0.00",
    },
    ...overrides,
  };
}

describe("StepAvvisoCard", () => {
  beforeEach(() => api.listStepLinksForAvviso.mockReset());

  it("waits for a token before loading", () => {
    render(<StepAvvisoCard token={null} avvisoId="a1" />);
    expect(screen.getByText("Caricamento dati STEP...")).toBeInTheDocument();
    expect(api.listStepLinksForAvviso).not.toHaveBeenCalled();
  });

  it("lists linked STEP documents", async () => {
    api.listStepLinksForAvviso.mockResolvedValue([link(), link({ denominazione: null, link: { ...link().link, id: "l2" } })]);
    render(<StepAvvisoCard token="t" avvisoId="a1" />);
    expect(await screen.findByText("Documento 20241421500000003 · ROSSI MARIO")).toBeInTheDocument();
    expect(screen.getByText("Documento 20241421500000003 · RSSMRA80A01G113X")).toBeInTheDocument();
    expect(api.listStepLinksForAvviso).toHaveBeenCalledWith("t", "a1");
    expect(screen.getAllByRole("link", { name: "Apri archivio STEP" })[0]).toHaveAttribute("href", "/elaborazioni/step");
  });

  it("shows empty and unavailable states", async () => {
    api.listStepLinksForAvviso.mockResolvedValueOnce([]);
    const { unmount } = render(<StepAvvisoCard token="t" avvisoId="a1" />);
    expect(await screen.findByText("Nessun documento STEP collegato.")).toBeInTheDocument();
    unmount();
    api.listStepLinksForAvviso.mockRejectedValueOnce(new Error("403"));
    render(<StepAvvisoCard token="t" avvisoId="a2" />);
    expect(await screen.findByText("Dati STEP non disponibili.")).toBeInTheDocument();
  });

  it("ignores responses after unmount", async () => {
    let resolve: (value: StepAvvisoLink[]) => void = () => undefined;
    api.listStepLinksForAvviso.mockReturnValue(new Promise((done) => { resolve = done; }));
    const { unmount } = render(<StepAvvisoCard token="t" avvisoId="a1" />);
    unmount();
    resolve([link()]);
    await Promise.resolve();
    expect(api.listStepLinksForAvviso).toHaveBeenCalledTimes(1);
  });
});
