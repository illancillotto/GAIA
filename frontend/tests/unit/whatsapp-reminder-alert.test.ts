import { createElement } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/presenze/whatsapp-manual-message", () => ({ WhatsAppManualMessage: () => createElement("span", null, "Invio manuale") }));

import {
  isWhatsAppReminderCandidate,
  WhatsAppReminderAlert,
} from "@/components/presenze/whatsapp-reminder-alert";
import type { PresenzeDailyRecord } from "@/types/api";

function record(overrides: Partial<PresenzeDailyRecord> = {}): PresenzeDailyRecord {
  return {
    work_date: new Date(Date.now() - 2 * 86400000).toISOString().slice(0, 10),
    validation_status: "pending",
    punches: [{ entry_time: "08:00", exit_time: null }],
    ...overrides,
  } as PresenzeDailyRecord;
}

describe("WhatsApp reminder alert candidate", () => {
  it("includes a past day with an open entry", () => {
    expect(isWhatsAppReminderCandidate(record())).toBe(true);
  });

  it("includes a past day with an orphan exit", () => {
    expect(isWhatsAppReminderCandidate(record({ punches: [{ entry_time: null, exit_time: "17:00" }] }))).toBe(true);
  });

  it("excludes validated and future days", () => {
    expect(isWhatsAppReminderCandidate(record({ validation_status: "validated" }))).toBe(false);
    expect(isWhatsAppReminderCandidate(record({ work_date: "2099-01-01" }))).toBe(false);
  });

  it("excludes complete punches and empty days", () => {
    expect(isWhatsAppReminderCandidate(record({ punches: [{ entry_time: "08:00", exit_time: "17:00" }] }))).toBe(false);
    expect(isWhatsAppReminderCandidate(record({ punches: [] }))).toBe(false);
  });

  it("renders the operational warning and dashboard link for a candidate", () => {
    render(createElement(WhatsAppReminderAlert, { record: record() }));

    expect(screen.getByRole("status")).toHaveTextContent("può entrare nel prossimo invio");
    expect(screen.getByRole("link", { name: "Gestisci WhatsApp" })).toHaveAttribute(
      "href",
      "/presenze/whatsapp",
    );
  });

  it("renders nothing when the day is not a candidate", () => {
    const { container } = render(
      createElement(WhatsAppReminderAlert, {
        record: record({ punches: [{ entry_time: "08:00", exit_time: "17:00" }] }),
      }),
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("offers manual anomalies and empty expected days but not validated days", () => {
    const view = render(createElement(WhatsAppReminderAlert, { record: record({ punches: [], detail_anomalies: [{ col_1: "Ore mancanti" }] }) }));
    expect(screen.getByText("Invio manuale")).toBeInTheDocument();
    view.rerender(createElement(WhatsAppReminderAlert, { record: record({ punches: [], teo_minutes: 480 }) }));
    expect(screen.getByText("Invio manuale")).toBeInTheDocument();
    view.rerender(createElement(WhatsAppReminderAlert, { record: record({ validation_status: "validated" }) }));
    expect(view.container).toBeEmptyDOMElement();
  });
});
