import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { AnomaliaStatusBadge } from "@/components/catasto/AnomaliaStatusBadge";
import { AnomaliaStatusPill } from "@/components/catasto/AnomaliaStatusPill";
import { BatchProgress } from "@/components/catasto/batch-progress";
import { CfBadge } from "@/components/catasto/CfBadge";
import { ImportStatusBadge } from "@/components/catasto/ImportStatusBadge";
import { KpiCard } from "@/components/catasto/KpiCard";
import { CatastoOperationMessage } from "@/components/catasto/operation-message";
import { CatastoStatusBadge } from "@/components/catasto/status-badge";
import type { ElaborazioneBatch } from "@/types/api";

function buildBatch(overrides: Partial<ElaborazioneBatch> = {}): ElaborazioneBatch {
  return {
    id: "batch-1",
    user_id: 1,
    name: "Batch test",
    status: "processing",
    total_items: 10,
    completed_items: 4,
    failed_items: 1,
    skipped_items: 1,
    not_found_items: 0,
    source_filename: null,
    current_operation: "Elaborazione particelle",
    report_json_path: null,
    report_md_path: null,
    created_at: "2026-06-01T10:00:00Z",
    started_at: "2026-06-01T10:01:00Z",
    completed_at: null,
    ...overrides,
  };
}

describe("KpiCard", () => {
  test("delegates to MetricCard", () => {
    render(<KpiCard label="Particelle" value={12} sub="Oggi" variant="info" />);
    expect(screen.getByText("Particelle")).toBeInTheDocument();
    expect(screen.getByText("12")).toHaveClass("text-blue-700");
  });
});

describe("CfBadge", () => {
  test("renders placeholder when codice fiscale is empty", () => {
    render(<CfBadge codiceFiscale="  " isValid={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  test("renders placeholder when codice fiscale is missing", () => {
    render(<CfBadge codiceFiscale={undefined} isValid={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  test("renders valid and invalid tones", () => {
    const { rerender } = render(<CfBadge codiceFiscale="RSSMRA80A01H501U" isValid />);
    expect(screen.getByText("RSSMRA80A01H501U")).toHaveClass("font-mono");

    rerender(<CfBadge codiceFiscale="INVALID" isValid={false} />);
    expect(screen.getByText("INVALID")).toBeInTheDocument();
  });

  test("renders unknown validity tone", () => {
    render(<CfBadge codiceFiscale="RSSMRA80A01H501U" isValid={null} />);
    expect(screen.getByText("RSSMRA80A01H501U")).toBeInTheDocument();
  });
});

describe("AnomaliaStatusPill", () => {
  test("maps known statuses and falls back for unknown values", () => {
    const { rerender } = render(<AnomaliaStatusPill status="aperta" />);
    expect(screen.getByText("Aperta")).toBeInTheDocument();

    rerender(<AnomaliaStatusPill status="custom_status" />);
    expect(screen.getByText("custom_status")).toBeInTheDocument();
  });
});

describe("AnomaliaStatusBadge", () => {
  test("maps severity and falls back to raw value", () => {
    const { rerender } = render(<AnomaliaStatusBadge severita="error" />);
    expect(screen.getByText("Errore")).toBeInTheDocument();

    rerender(<AnomaliaStatusBadge severita="custom" />);
    expect(screen.getByText("custom")).toBeInTheDocument();
  });
});

describe("ImportStatusBadge", () => {
  test("maps import status and falls back to raw value", () => {
    const { rerender } = render(<ImportStatusBadge status="processing" />);
    expect(screen.getByText("In lavorazione")).toBeInTheDocument();

    rerender(<ImportStatusBadge status="queued" />);
    expect(screen.getByText("queued")).toBeInTheDocument();
  });
});

describe("CatastoStatusBadge", () => {
  test("renders configured status label", () => {
    render(<CatastoStatusBadge status="awaiting_captcha" />);
    expect(screen.getByText("Attende CAPTCHA")).toBeInTheDocument();
  });
});

describe("BatchProgress", () => {
  test("computes progress percentage and shows counters", () => {
    render(<BatchProgress batch={buildBatch()} />);

    expect(screen.getByText("6/10 · 60%")).toBeInTheDocument();
    expect(screen.getByText("Elaborazione particelle")).toBeInTheDocument();
    expect(screen.getByText("4", { selector: "span.font-medium.text-emerald-700" })).toBeInTheDocument();
  });

  test("shows zero percent when batch has no items", () => {
    render(<BatchProgress batch={buildBatch({ total_items: 0, completed_items: 0, failed_items: 0, skipped_items: 0, current_operation: null })} />);
    expect(screen.getByText("0/0 · 0%")).toBeInTheDocument();
    expect(screen.getByText("In attesa del worker Catasto")).toBeInTheDocument();
  });
});

describe("CatastoOperationMessage", () => {
  test("renders dash for empty value", () => {
    render(<CatastoOperationMessage value={null} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  test("renders plain message", () => {
    render(<CatastoOperationMessage value="Operazione completata" className="msg" />);
    expect(screen.getByText("Operazione completata")).toHaveClass("msg");
  });

  test("shows SISTER locked diagnostics toggle", () => {
    render(
      <CatastoOperationMessage value="Errore https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp" />,
    );

    expect(screen.getByText(/Utente SISTER bloccato/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apri diagnostica" }));
    expect(screen.getByText(/Il worker ha gia/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Nascondi diagnostica" }));
    expect(screen.queryByText(/Il worker ha gia/)).not.toBeInTheDocument();
  });
});
