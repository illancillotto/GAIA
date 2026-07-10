import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { RuoloReconciliationCard } from "@/components/catasto/indici/ruolo-reconciliation-card";
import type { CatIndiceRuoloReconciliation } from "@/types/catasto";

function makeReconciliation(overrides: Partial<CatIndiceRuoloReconciliation> = {}): CatIndiceRuoloReconciliation {
  return {
    righe_ruolo_totali_count: 99848,
    particelle_ruolo_totali_count: 89967,
    righe_ruolo_incluse_count: 91349,
    particelle_ruolo_incluse_count: 82124,
    righe_ruolo_escluse_count: 8499,
    particelle_ruolo_escluse_count: 7843,
    importo_ruolo_totale: "2400529.15",
    importo_ruolo_incluso: "2231321.46",
    importo_ruolo_escluso: "169207.69",
    importo_ruolo_escluso_manutenzione: "67022.22",
    importo_ruolo_escluso_irrigazione: "55627.81",
    importo_ruolo_escluso_istituzionale: "46557.66",
    superficie_irrigata_esclusa_ha: "1006.8259",
    coverage_percent: "92.951231",
    reasons: [
      {
        key: "senza_distretto",
        label: "Particella corrente senza distretto",
        description: "La particella esiste nel catasto AE corrente, ma non ha num_distretto.",
        righe_ruolo_count: 5577,
        particelle_ruolo_distinte_count: 5028,
        cat_particelle_count: 4615,
        superficie_irrigata_ha: "529.9372",
        importo_ruolo: "103317.11",
        importo_ruolo_manutenzione: "45897.64",
        importo_ruolo_irrigazione: "26251.86",
        importo_ruolo_istituzionale: "31167.61",
      },
      {
        key: "non_collegata",
        label: "Ruolo non collegato al catasto corrente",
        description: "Righe ruolo senza un aggancio sicuro a cat_particelle.",
        righe_ruolo_count: 2922,
        particelle_ruolo_distinte_count: 2815,
        cat_particelle_count: 0,
        superficie_irrigata_ha: "476.8887",
        importo_ruolo: "65890.58",
        importo_ruolo_manutenzione: "21124.58",
        importo_ruolo_irrigazione: "29375.95",
        importo_ruolo_istituzionale: "15390.05",
      },
    ],
    ...overrides,
  };
}

describe("RuoloReconciliationCard", () => {
  test("renders nothing while reconciliation is unavailable", () => {
    const { container } = render(<RuoloReconciliationCard reconciliation={null} anno={2025} />);

    expect(container).toBeEmptyDOMElement();
  });

  test("explains included and excluded role amounts with reason breakdown", () => {
    render(<RuoloReconciliationCard reconciliation={makeReconciliation()} anno={2025} />);

    expect(screen.getByText("Riconciliazione ruolo")).toBeInTheDocument();
    expect(screen.getByText("Perché il totale ruolo non coincide sempre con gli indici")).toBeInTheDocument();
    expect(screen.getByText("Anno ruolo 2025")).toBeInTheDocument();
    expect(screen.getAllByText(/ruolo_particelle/).length).toBeGreaterThan(0);
    expect(screen.getByText(/catasto corrente Agenzia Entrate/)).toBeInTheDocument();
    expect(screen.getByText(/2\.231\.321\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/169\.208\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/2\.400\.529\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/1\.?006,8 ha/)).toBeInTheDocument();
    expect(screen.getByText(/82.124 particelle ruolo · 93,0% del totale/)).toBeInTheDocument();
    expect(screen.getByText(/7\.?843 particelle ruolo · 7,0% del totale/)).toBeInTheDocument();
    expect(screen.getByText(/99.848 righe ruolo da ruolo_particelle/)).toBeInTheDocument();
    expect(screen.getByText("Particella corrente senza distretto")).toBeInTheDocument();
    expect(screen.getByText("Ruolo non collegato al catasto corrente")).toBeInTheDocument();
    expect(screen.getByText(/103\.317\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/65\.891\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/manutenzione\s*67\.022\s*€/)).toBeInTheDocument();
  });

  test("renders the no-exclusions state and defensive percent fallbacks", () => {
    render(
      <RuoloReconciliationCard
        anno={null}
        reconciliation={makeReconciliation({
          righe_ruolo_totali_count: 0,
          particelle_ruolo_totali_count: 0,
          righe_ruolo_incluse_count: 0,
          particelle_ruolo_incluse_count: 0,
          righe_ruolo_escluse_count: 0,
          particelle_ruolo_escluse_count: 0,
          importo_ruolo_totale: "0",
          importo_ruolo_incluso: "0",
          importo_ruolo_escluso: "0",
          superficie_irrigata_esclusa_ha: "0",
          coverage_percent: null,
          reasons: [],
        })}
      />,
    );

    expect(screen.getByText("Anno ruolo —")).toBeInTheDocument();
    expect(screen.getByText("Nessuna riga ruolo esclusa dagli indici.")).toBeInTheDocument();
    expect(screen.getAllByText(/0 particelle ruolo · — del totale/)).toHaveLength(2);
    expect(screen.getByText("0,0 ha")).toBeInTheDocument();
  });
});
