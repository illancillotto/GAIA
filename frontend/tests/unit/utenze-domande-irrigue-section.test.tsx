import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  UtenzeDomandeIrrigueSection,
  contextLabel,
  detailKey,
  domandaStatusClassName,
  formatDomandaArea,
  formatDomandaMoney,
  parseDomandaDecimal,
  summarizeSubjectDomandeIrrigue,
  yearsLabel,
} from "@/components/utenze/utenze-domande-irrigue-section";
import type { CatDomandaIrrigua, CatDomandaIrriguaParticella, CatDomandeIrrigueListResponse } from "@/types/catasto";

const mocks = vi.hoisted(() => ({
  listSubjectDomandeIrrigue: vi.fn(),
}));

vi.mock("@/lib/catasto-domande-irrigue-subject-api", () => ({
  listSubjectDomandeIrrigue: (...args: unknown[]) => mocks.listSubjectDomandeIrrigue(...args),
}));

function buildDetail(overrides: Partial<CatDomandaIrriguaParticella> = {}): CatDomandaIrriguaParticella {
  return {
    id: overrides.id ?? crypto.randomUUID(),
    domanda_id: overrides.domanda_id ?? "domanda-1",
    external_id: overrides.external_id ?? null,
    unit_id: overrides.unit_id ?? null,
    segment_id: overrides.segment_id ?? null,
    particella_id: overrides.particella_id ?? null,
    utenza_id: overrides.utenza_id ?? null,
    occupancy_id: overrides.occupancy_id ?? null,
    localita: overrides.localita ?? null,
    comizio: overrides.comizio ?? null,
    foglio: Object.prototype.hasOwnProperty.call(overrides, "foglio") ? overrides.foglio! : "12",
    particella: Object.prototype.hasOwnProperty.call(overrides, "particella") ? overrides.particella! : "34",
    sub: Object.prototype.hasOwnProperty.call(overrides, "sub") ? overrides.sub! : null,
    sup_cat_mq: overrides.sup_cat_mq ?? "1000.00",
    sup_irr_mq: overrides.sup_irr_mq ?? "750.50",
    coltura: Object.prototype.hasOwnProperty.call(overrides, "coltura") ? overrides.coltura! : "RISO",
    part_pvc: Object.prototype.hasOwnProperty.call(overrides, "part_pvc") ? overrides.part_pvc! : "097",
    part_com: Object.prototype.hasOwnProperty.call(overrides, "part_com") ? overrides.part_com! : "179",
    part_cco: Object.prototype.hasOwnProperty.call(overrides, "part_cco") ? overrides.part_cco! : "000001001",
    part_fra: Object.prototype.hasOwnProperty.call(overrides, "part_fra") ? overrides.part_fra! : "16",
    part_ccs: Object.prototype.hasOwnProperty.call(overrides, "part_ccs") ? overrides.part_ccs! : "00000",
    ruolo_bon: overrides.ruolo_bon ?? null,
    ruolo_irr: overrides.ruolo_irr ?? "12.50",
    ruolo_var: overrides.ruolo_var ?? null,
    note: overrides.note ?? null,
  };
}

function buildDomanda(overrides: Partial<CatDomandaIrrigua> = {}): CatDomandaIrrigua {
  const id = overrides.id ?? crypto.randomUUID();
  return {
    id,
    external_id: overrides.external_id ?? null,
    anno: overrides.anno ?? 2026,
    domanda_numero: Object.prototype.hasOwnProperty.call(overrides, "domanda_numero") ? overrides.domanda_numero! : "5013",
    cco: Object.prototype.hasOwnProperty.call(overrides, "cco") ? overrides.cco! : "000001001",
    com: Object.prototype.hasOwnProperty.call(overrides, "com") ? overrides.com! : "179",
    pvc: Object.prototype.hasOwnProperty.call(overrides, "pvc") ? overrides.pvc! : "097",
    fra: Object.prototype.hasOwnProperty.call(overrides, "fra") ? overrides.fra! : "16",
    ccs: Object.prototype.hasOwnProperty.call(overrides, "ccs") ? overrides.ccs! : "00000",
    idxana: overrides.idxana ?? null,
    source_row_id: overrides.source_row_id ?? null,
    source_denominazione: overrides.source_denominazione ?? "Utente Demo",
    source_patrimonio: overrides.source_patrimonio ?? "ABCD",
    patrimonio_has_domanda_hint: overrides.patrimonio_has_domanda_hint ?? true,
    comune: Object.prototype.hasOwnProperty.call(overrides, "comune") ? overrides.comune! : "SAN VERO MILIS",
    subject_id: overrides.subject_id ?? "subject-1",
    utenza_id: overrides.utenza_id ?? null,
    occupancy_id: overrides.occupancy_id ?? null,
    stato: Object.prototype.hasOwnProperty.call(overrides, "stato") ? overrides.stato! : "Aperta",
    stato_codice: overrides.stato_codice ?? "1",
    tipo: Object.prototype.hasOwnProperty.call(overrides, "tipo") ? overrides.tipo! : "I Coltura",
    tipo_codice: overrides.tipo_codice ?? "1",
    tipo_scheda_codice: overrides.tipo_scheda_codice ?? null,
    tipo_scheda: overrides.tipo_scheda ?? null,
    autorinnovo: overrides.autorinnovo ?? false,
    ruolo_irr: Object.prototype.hasOwnProperty.call(overrides, "ruolo_irr") ? overrides.ruolo_irr! : "33.40",
    tot_sup_cat_mq: overrides.tot_sup_cat_mq ?? "1000.00",
    tot_sup_irr_mq: Object.prototype.hasOwnProperty.call(overrides, "tot_sup_irr_mq") ? overrides.tot_sup_irr_mq! : "750.50",
    tot_sup_servita_mq: overrides.tot_sup_servita_mq ?? null,
    tot_sup_richiesta_mq: Object.prototype.hasOwnProperty.call(overrides, "tot_sup_richiesta_mq") ? overrides.tot_sup_richiesta_mq! : "800.00",
    tot_sup_malus_mq: Object.prototype.hasOwnProperty.call(overrides, "tot_sup_malus_mq") ? overrides.tot_sup_malus_mq! : "5.00",
    tot_sup_bonus_mq: Object.prototype.hasOwnProperty.call(overrides, "tot_sup_bonus_mq") ? overrides.tot_sup_bonus_mq! : "10.00",
    data_ins: Object.prototype.hasOwnProperty.call(overrides, "data_ins") ? overrides.data_ins! : "2026-04-20T08:00:00Z",
    data_agg: Object.prototype.hasOwnProperty.call(overrides, "data_agg") ? overrides.data_agg! : "2026-05-08T09:00:00Z",
    data_rett: overrides.data_rett ?? null,
    data_sosp: overrides.data_sosp ?? null,
    data_chius: overrides.data_chius ?? null,
    note: overrides.note ?? null,
    particelle: overrides.particelle ?? [buildDetail({ domanda_id: id })],
  };
}

function payload(items: CatDomandaIrrigua[], total = items.length): CatDomandeIrrigueListResponse {
  return {
    items,
    total,
    limit: 120,
    offset: 0,
  };
}

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve;
  });
  return { promise, resolve };
}

describe("UtenzeDomandeIrrigueSection helpers", () => {
  test("formats values, statuses and labels", () => {
    expect(parseDomandaDecimal(null)).toBeNull();
    expect(parseDomandaDecimal("")).toBeNull();
    expect(parseDomandaDecimal("12,50")).toBe(12.5);
    expect(parseDomandaDecimal("abc")).toBeNull();
    expect(formatDomandaArea(null)).toBe("-");
    expect(formatDomandaArea(1234.56)).toBe("1234,56 mq");
    expect(formatDomandaMoney(undefined)).toBe("-");
    expect(formatDomandaMoney("12.5")).toContain("12,50");
    expect(domandaStatusClassName("Aperta aggiornata")).toContain("emerald");
    expect(domandaStatusClassName("Rettificata")).toContain("amber");
    expect(domandaStatusClassName("Annullata chiusa")).toContain("slate");
    expect(domandaStatusClassName(null)).toContain("sky");
    expect(detailKey(buildDetail({ foglio: "1", particella: "2", sub: "3" }))).toBe("1/2/3");
    expect(detailKey(buildDetail({ foglio: null, particella: null, sub: null }))).toBe("-/-/-");
    expect(contextLabel(buildDomanda())).toBe("000001001 / 179 / 097 / 16 / 00000");
    expect(contextLabel(buildDomanda({ cco: null, com: null, pvc: null, fra: null, ccs: null }))).toBe("-");
    expect(yearsLabel([])).toBe("N/D");
    expect(yearsLabel([2026, 2025])).toBe("2026, 2025");
  });

  test("summarizes domande irrigue with valid, empty and invalid values", () => {
    expect(summarizeSubjectDomandeIrrigue([])).toEqual({
      domandeCount: 0,
      particelleCount: 0,
      totalSupIrrMq: null,
      totalSupRichiestaMq: null,
      totalBonusMq: null,
      totalMalusMq: null,
      availableYears: [],
      latestActivityAt: null,
    });

    const summary = summarizeSubjectDomandeIrrigue([
      buildDomanda({ anno: 2025, data_agg: "not-a-date" }),
      buildDomanda({
        anno: 2026,
        tot_sup_irr_mq: null,
        tot_sup_richiesta_mq: null,
        tot_sup_bonus_mq: null,
        tot_sup_malus_mq: null,
        data_agg: null,
        data_rett: "2026-06-01T10:00:00Z",
        data_ins: null,
        particelle: [],
      }),
      buildDomanda({
        anno: 2024,
        data_agg: null,
        data_rett: null,
        data_ins: "2024-03-01T10:00:00Z",
        tot_sup_irr_mq: null,
        tot_sup_richiesta_mq: null,
        tot_sup_bonus_mq: null,
        tot_sup_malus_mq: null,
        particelle: [],
      }),
    ]);

    expect(summary.domandeCount).toBe(3);
    expect(summary.particelleCount).toBe(1);
    expect(summary.totalSupIrrMq).toBe(750.5);
    expect(summary.totalSupRichiestaMq).toBe(800);
    expect(summary.totalBonusMq).toBe(10);
    expect(summary.totalMalusMq).toBe(5);
    expect(summary.availableYears).toEqual([2026, 2025, 2024]);
    expect(summary.latestActivityAt).toBe("2026-06-01T10:00:00.000Z");
  });
});

describe("UtenzeDomandeIrrigueSection", () => {
  beforeEach(() => {
    mocks.listSubjectDomandeIrrigue.mockReset();
  });

  test("shows loading state while domande are pending", () => {
    const deferred = createDeferred<CatDomandeIrrigueListResponse>();
    mocks.listSubjectDomandeIrrigue.mockReturnValue(deferred.promise);

    render(<UtenzeDomandeIrrigueSection subjectId="subject-1" token="token" />);

    expect(screen.getByText("Caricamento domande irrigue del soggetto...")).toBeInTheDocument();
    expect(mocks.listSubjectDomandeIrrigue).toHaveBeenCalledWith("token", "subject-1", { utenzaId: null, limit: 120, offset: 0 });
  });

  test("loads and renders data scoped to a specific utenza", async () => {
    const deferred = createDeferred<CatDomandeIrrigueListResponse>();
    mocks.listSubjectDomandeIrrigue.mockReturnValue(deferred.promise);

    render(<UtenzeDomandeIrrigueSection subjectId="subject-1" token="token" utenzaId="utenza-1" />);

    expect(screen.getByText("Caricamento domande irrigue dell'utenza...")).toBeInTheDocument();
    expect(mocks.listSubjectDomandeIrrigue).toHaveBeenCalledWith("token", "subject-1", { utenzaId: "utenza-1", limit: 120, offset: 0 });
    deferred.resolve(payload([buildDomanda()]));

    expect(await screen.findByText("Domande irrigue Capacitas dell'utenza")).toBeInTheDocument();
    expect(screen.getByText(/Domande collegate alla specifica utenza consortile/)).toBeInTheDocument();
  });

  test("renders cards, rows, empty details and limit warning", async () => {
    const manyDetails = Array.from({ length: 9 }, (_, index) =>
      buildDetail({
        id: `detail-${index}`,
        domanda_id: "domanda-many",
        foglio: "12",
        particella: String(30 + index),
        sub: index === 0 ? null : String(index),
        coltura: index === 0 ? null : "RISO",
        part_cco: index === 0 ? null : "000001001",
        part_com: index === 0 ? null : "179",
        part_pvc: index === 0 ? null : "097",
        part_fra: index === 0 ? null : "16",
        part_ccs: index === 0 ? null : "00000",
      }),
    );
    mocks.listSubjectDomandeIrrigue.mockResolvedValue(
      payload(
        [
          buildDomanda({ id: "domanda-many", autorinnovo: true, particelle: manyDetails }),
          buildDomanda({
            id: "domanda-empty",
            domanda_numero: null,
            external_id: "EXT-2",
            stato: "Rettificata",
            tipo: null,
            comune: null,
            cco: null,
            com: null,
            pvc: null,
            fra: null,
            ccs: null,
            ruolo_irr: null,
            data_agg: null,
            data_rett: null,
            data_ins: null,
            particelle: [],
          }),
        ],
        3,
      ),
    );

    render(<UtenzeDomandeIrrigueSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText("Domande irrigue Capacitas")).toBeInTheDocument();
    expect(screen.getByText("Visualizzate 2 domande su 3. Apri il registro Catasto per una consultazione paginata completa.")).toBeInTheDocument();
    expect(screen.getByText("Autorinnovo")).toBeInTheDocument();
    expect(screen.getByText("Domanda 5013")).toBeInTheDocument();
    expect(screen.getByText("Domanda EXT-2")).toBeInTheDocument();
    expect(screen.getByText("Tipo non indicato / Comune non indicato / Contesto -")).toBeInTheDocument();
    expect(screen.getByText("Nessun dettaglio particella importato per questa domanda.")).toBeInTheDocument();
    expect(screen.getByText("Mostrate 8 particelle su 9. Usa il registro Catasto per il dettaglio completo.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Apri registro domande/ })).toHaveAttribute("href", "/catasto/domande-irrigue");
  });

  test("renders non-limited data without warning", async () => {
    mocks.listSubjectDomandeIrrigue.mockResolvedValue(
      payload([
        buildDomanda({
          id: "domanda-id-only",
          domanda_numero: null,
          external_id: null,
          stato: null,
          data_agg: null,
          data_rett: null,
          data_ins: null,
        }),
      ]),
    );

    render(<UtenzeDomandeIrrigueSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText("Stato non indicato")).toBeInTheDocument();
    expect(screen.getByText("Domanda domanda-id-only")).toBeInTheDocument();
    expect(screen.queryByText(/Visualizzate/)).not.toBeInTheDocument();
  });

  test("renders empty state", async () => {
    mocks.listSubjectDomandeIrrigue.mockResolvedValue(payload([]));

    render(<UtenzeDomandeIrrigueSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText("Nessuna domanda irrigua importata risulta collegata a questo soggetto.")).toBeInTheDocument();
  });

  test("renders empty state for a specific utenza", async () => {
    mocks.listSubjectDomandeIrrigue.mockResolvedValue(payload([]));

    render(<UtenzeDomandeIrrigueSection subjectId="subject-1" token="token" utenzaId="utenza-1" />);

    expect(await screen.findByText("Nessuna domanda irrigua importata risulta collegata a questa utenza.")).toBeInTheDocument();
  });

  test("renders empty state for a null response payload", async () => {
    mocks.listSubjectDomandeIrrigue.mockResolvedValue(null);

    render(<UtenzeDomandeIrrigueSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText("Nessuna domanda irrigua importata risulta collegata a questo soggetto.")).toBeInTheDocument();
  });

  test("renders module access error", async () => {
    mocks.listSubjectDomandeIrrigue.mockRejectedValue(new Error("403 Module access"));

    render(<UtenzeDomandeIrrigueSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText(/Il modulo Catasto non e accessibile/)).toBeInTheDocument();
  });

  test("renders generic string load error", async () => {
    mocks.listSubjectDomandeIrrigue.mockRejectedValue("remote failure");

    render(<UtenzeDomandeIrrigueSection subjectId="subject-1" token="token" />);

    await waitFor(() => {
      expect(screen.getByText("Errore caricamento domande irrigue")).toBeInTheDocument();
    });
  });

  test("renders generic Error load error", async () => {
    mocks.listSubjectDomandeIrrigue.mockRejectedValue(new Error("Errore remoto"));

    render(<UtenzeDomandeIrrigueSection subjectId="subject-1" token="token" />);

    expect(await screen.findByText("Errore remoto")).toBeInTheDocument();
  });
});
