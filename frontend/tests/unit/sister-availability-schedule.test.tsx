import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, test, vi } from "vitest";

import {
  defaultSisterSchedule,
  formatSisterSchedule,
  nextSisterAvailability,
  OUTSIDE_OFFICE_SCHEDULE,
  SisterAvailabilityScheduleEditor,
  sisterCredentialIsAvailable,
} from "@/components/elaborazioni/sister-availability-schedule";
import { SisterCredentialPoolView } from "@/components/elaborazioni/sister-credential-pool-view";
import type { SisterCredentialAvailabilitySchedule } from "@/types/api";

function EditorHarness({ initial }: { initial: SisterCredentialAvailabilitySchedule }) {
  const [enabled, setEnabled] = useState(true);
  const [schedule, setSchedule] = useState(initial);
  return <SisterAvailabilityScheduleEditor
    enabled={enabled}
    onEnabledChange={setEnabled}
    onScheduleChange={setSchedule}
    schedule={schedule}
  />;
}

describe("SisterAvailabilityScheduleEditor", () => {
  test("formats disabled, missing, empty and multi-window schedules", () => {
    const schedule: SisterCredentialAvailabilitySchedule = {
      timezone: "Europe/Rome",
      weekly: {
        "0": [{ start: "08:00", end: "12:00" }, { start: "14:00", end: "18:00" }],
        "2": [{ start: "18:00", end: "08:00" }],
      },
    };

    expect(formatSisterSchedule(false, schedule)).toBe("Sempre disponibile");
    expect(formatSisterSchedule(true, null)).toBe("Nessuna fascia configurata");
    expect(formatSisterSchedule(true, { timezone: "Europe/Rome", weekly: {} })).toBe("Nessuna fascia configurata");
    expect(formatSisterSchedule(true, schedule)).toBe("Lun 08:00-12:00, 14:00-18:00 · Mer 18:00-08:00");
    expect(formatSisterSchedule(true, {
      timezone: "Europe/Rome",
      weekly: {},
      exceptions: [
        { kind: "nth_weekday_of_month", weekday: 5, occurrence: 1, windows: [{ start: "14:00", end: "00:00" }] },
        { kind: "nth_weekday_of_month", weekday: 9, occurrence: 1, windows: [{ start: "10:00", end: "12:00" }] },
        { kind: "nth_weekday_of_month", weekday: 5, occurrence: 2, windows: [] },
      ],
    })).toBe("1° Sab 14:00-00:00 · 1° Giorno 10:00-12:00");
  });

  test("adds, edits, removes and restores independent daily windows", () => {
    render(<EditorHarness initial={{
      timezone: "Europe/Rome",
      weekly: {
        "0": [{ start: "08:00", end: "12:00" }, { start: "14:00", end: "18:00" }],
        "2": [
          { start: "00:00", end: "00:00" },
          { start: "08:00", end: "09:00" },
          { start: "10:00", end: "11:00" },
          { start: "12:00", end: "13:00" },
        ],
      },
    }} />);

    expect(screen.getByLabelText("Lunedi dalle")).toHaveValue("08:00");
    expect(screen.getByLabelText("Lunedi fascia 2 dalle")).toHaveValue("14:00");
    expect(screen.getByText("Tutto il giorno")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aggiungi fascia Mercoledi" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Lunedi dalle"), { target: { value: "07:30" } });
    expect(screen.getByLabelText("Lunedi dalle")).toHaveValue("07:30");
    fireEvent.change(screen.getByLabelText("Lunedi fascia 2 alle"), { target: { value: "19:30" } });
    expect(screen.getByLabelText("Lunedi fascia 2 alle")).toHaveValue("19:30");
    fireEvent.click(screen.getByRole("button", { name: "Rimuovi fascia 1 Lunedi" }));
    expect(screen.getByLabelText("Lunedi dalle")).toHaveValue("14:00");

    fireEvent.click(screen.getByRole("checkbox", { name: "Lunedi disponibile" }));
    expect(screen.queryByLabelText("Lunedi dalle")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: "Lunedi disponibile" }));
    expect(screen.getByLabelText("Lunedi dalle")).toHaveValue("15:00");

    fireEvent.click(screen.getByRole("checkbox", { name: "Martedi disponibile" }));
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi fascia Martedi" }));
    expect(screen.getByLabelText("Martedi fascia 2 dalle")).toHaveValue("15:00");
    fireEvent.click(screen.getByRole("button", { name: "Rimuovi fascia 2 Martedi" }));
    expect(screen.queryByLabelText("Martedi fascia 2 dalle")).not.toBeInTheDocument();
  });

  test("toggles scheduling and applies a fresh office-hours preset", () => {
    const initial = defaultSisterSchedule();
    initial.weekly["0"][0].start = "21:00";
    render(<EditorHarness initial={initial} />);

    fireEvent.click(screen.getByRole("checkbox", { name: /Usa solo fuori dall/ }));
    expect(screen.queryByLabelText("Lunedi dalle")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: /Usa solo fuori dall/ }));
    fireEvent.click(screen.getByRole("button", { name: "Applica fuori orario ufficio" }));

    expect(screen.getByLabelText("Lunedi dalle")).toHaveValue("15:00");
    expect(screen.getByLabelText("Lunedi alle")).toHaveValue("07:30");
    expect(screen.getByLabelText("Sabato dalle")).toHaveValue("00:00");
    expect(screen.getByLabelText("Primo sabato dalle")).toHaveValue("14:00");
    fireEvent.click(screen.getByRole("checkbox", { name: "Primo sabato del mese diverso" }));
    expect(screen.queryByLabelText("Primo sabato dalle")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: "Primo sabato del mese diverso" }));
    fireEvent.change(screen.getByLabelText("Primo sabato dalle"), { target: { value: "13:00" } });
    expect(screen.getByLabelText("Primo sabato dalle")).toHaveValue("13:00");
    fireEvent.change(screen.getByLabelText("Primo sabato alle"), { target: { value: "23:00" } });
    expect(screen.getByLabelText("Primo sabato alle")).toHaveValue("23:00");
  });

  test("enables the first-Saturday exception on a weekly-only schedule", () => {
    render(<EditorHarness initial={{
      timezone: "Europe/Rome",
      weekly: { "5": [{ start: "00:00", end: "00:00" }] },
    }} />);
    fireEvent.click(screen.getByRole("checkbox", { name: "Primo sabato del mese diverso" }));
    expect(screen.getByLabelText("Primo sabato dalle")).toHaveValue("14:00");
    fireEvent.click(screen.getByRole("checkbox", { name: "Primo sabato del mese diverso" }));
    expect(screen.queryByLabelText("Primo sabato dalle")).not.toBeInTheDocument();
  });

  test("computes current and next availability across normal and overnight windows", () => {
    const schedule: SisterCredentialAvailabilitySchedule = {
      timezone: "Europe/Rome",
      weekly: { "0": [{ start: "18:00", end: "08:00" }], "1": [{ start: "10:00", end: "12:00" }] },
    };
    const mondayEvening = new Date("2026-08-24T17:00:00Z");
    const tuesdayMorning = new Date("2026-08-25T05:30:00Z");
    const tuesdayBeforeWindow = new Date("2026-08-25T07:59:00Z");

    expect(sisterCredentialIsAvailable(false, null, mondayEvening)).toBe(true);
    expect(sisterCredentialIsAvailable(true, schedule, mondayEvening)).toBe(true);
    expect(sisterCredentialIsAvailable(true, schedule, tuesdayMorning)).toBe(true);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-25T09:00:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-25T11:00:00Z"))).toBe(false);
    expect(sisterCredentialIsAvailable(true, null, tuesdayMorning)).toBe(false);
    expect(nextSisterAvailability(false, null, mondayEvening)).toBe(mondayEvening);
    expect(nextSisterAvailability(true, schedule, tuesdayBeforeWindow)).toEqual(new Date("2026-08-25T08:00:00Z"));
    expect(nextSisterAvailability(true, { timezone: "Europe/Rome", weekly: {} }, tuesdayBeforeWindow)).toBeNull();
    expect(nextSisterAvailability(true, {
      timezone: "Europe/Rome",
      weekly: { "7": [{ start: "08:00", end: "09:00" }], "0": [{ start: "bad", end: "09:00" }] },
    }, tuesdayBeforeWindow)).toBeNull();
  });
});

describe("Sister availability schedule legacy characterization", () => {
  test("evaluates daytime, overnight and disabled schedules in Europe/Rome", () => {
    const schedule = defaultSisterSchedule();
    expect(sisterCredentialIsAvailable(false, null, new Date("2026-08-24T10:00:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-24T17:00:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-25T05:29:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-25T05:30:00Z"))).toBe(false);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-29T10:00:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, null, new Date("2026-08-24T10:00:00Z"))).toBe(false);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-01T08:00:00Z"))).toBe(false);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-01T05:00:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-01T12:00:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-08T08:00:00Z"))).toBe(true);
    expect(nextSisterAvailability(true, schedule, new Date("2026-08-01T08:00:00Z"))?.toISOString()).toBe("2026-08-01T12:00:00.000Z");
    expect(nextSisterAvailability(true, {
      timezone: "Europe/Rome",
      weekly: {},
      exceptions: [{ kind: "nth_weekday_of_month", weekday: 5, occurrence: 1, windows: [{ start: "14:00", end: "00:00" }] }],
    }, new Date("2026-08-01T08:00:00Z"))?.toISOString()).toBe("2026-08-01T12:00:00.000Z");
    const daytime = { timezone: "Europe/Rome" as const, weekly: { "0": [{ start: "10:00", end: "12:00" }] } };
    expect(sisterCredentialIsAvailable(true, daytime, new Date("2026-08-24T09:00:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, daytime, new Date("2026-08-24T11:00:00Z"))).toBe(false);
  });

  test("finds the next opening and handles schedules without openings", () => {
    const schedule = defaultSisterSchedule();
    const reference = new Date("2026-08-24T12:58:00Z");
    expect(nextSisterAvailability(true, schedule, reference)?.toISOString()).toBe("2026-08-24T13:00:00.000Z");
    expect(nextSisterAvailability(false, null, reference)).toBe(reference);
    expect(nextSisterAvailability(true, { timezone: "Europe/Rome", weekly: {} }, reference)).toBeNull();
    expect(nextSisterAvailability(true, { timezone: "Europe/Rome", weekly: { "7": [{ start: "bad", end: "bad" }] } }, reference)).toBeNull();
    expect(nextSisterAvailability(true, { timezone: "Europe/Rome", weekly: { "0": [{ start: "99:99", end: "bad" }] } }, reference)).toBeNull();
    expect(nextSisterAvailability(true, null, reference)).toBeNull();
    const storedExceptions = OUTSIDE_OFFICE_SCHEDULE.exceptions;
    delete (OUTSIDE_OFFICE_SCHEDULE as { exceptions?: unknown }).exceptions;
    try {
      expect(defaultSisterSchedule().exceptions).toEqual([]);
    } finally {
      OUTSIDE_OFFICE_SCHEDULE.exceptions = storedExceptions;
    }
    expect(nextSisterAvailability(true, {
      timezone: "Europe/Rome",
      weekly: {},
      exceptions: [{ kind: "other" as "nth_weekday_of_month", weekday: 5, occurrence: 1, windows: [{ start: "14:00", end: "00:00" }] }],
    }, reference)).toBeNull();
    expect(sisterCredentialIsAvailable(true, {
      timezone: "Europe/Rome",
      weekly: { "5": [{ start: "00:00", end: "00:00" }] },
      exceptions: [{ kind: "nth_weekday_of_month", weekday: 5, occurrence: 1, windows: undefined as unknown as [] }],
    }, new Date("2026-08-01T08:00:00Z"))).toBe(false);
  });

  test("edits activation, preset, days and overnight hours", () => {
    const onEnabledChange = vi.fn();
    const onScheduleChange = vi.fn();
    const { rerender } = render(
      <SisterAvailabilityScheduleEditor enabled={false} onEnabledChange={onEnabledChange} onScheduleChange={onScheduleChange} schedule={defaultSisterSchedule()} />,
    );
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Applica fuori orario ufficio" }));
    expect(onEnabledChange).toHaveBeenCalledWith(true);
    expect(onScheduleChange).toHaveBeenCalled();

    rerender(<SisterAvailabilityScheduleEditor enabled onEnabledChange={onEnabledChange} onScheduleChange={onScheduleChange} schedule={defaultSisterSchedule()} />);
    fireEvent.click(screen.getByRole("checkbox", { name: "Lunedi disponibile" }));
    expect(onScheduleChange).toHaveBeenLastCalledWith(expect.objectContaining({ weekly: expect.objectContaining({ "0": [] }) }));
    fireEvent.change(screen.getByLabelText("Martedi dalle"), { target: { value: "19:00" } });
    expect(onScheduleChange).toHaveBeenLastCalledWith(expect.objectContaining({ weekly: expect.objectContaining({ "1": [{ start: "19:00", end: "07:30" }] }) }));
    fireEvent.change(screen.getByLabelText("Martedi alle"), { target: { value: "07:00" } });
    expect(onScheduleChange).toHaveBeenLastCalledWith(expect.objectContaining({ weekly: expect.objectContaining({ "1": [{ start: "15:00", end: "07:00" }] }) }));

    const scheduleWithClosedMonday = defaultSisterSchedule();
    scheduleWithClosedMonday.weekly["0"] = [];
    rerender(<SisterAvailabilityScheduleEditor enabled onEnabledChange={onEnabledChange} onScheduleChange={onScheduleChange} schedule={scheduleWithClosedMonday} />);
    fireEvent.click(screen.getByRole("checkbox", { name: "Lunedi disponibile" }));
    expect(onScheduleChange).toHaveBeenLastCalledWith(expect.objectContaining({ weekly: expect.objectContaining({ "0": [{ start: "15:00", end: "07:30" }] }) }));
  });

  test("renders pool warning and error totals even without credentials", () => {
    const noop = vi.fn();
    render(
      <SisterCredentialPoolView
        bulkRunning={false}
        controlsDisabled={false}
        credentials={[]}
        currentTestResult={null}
        embedded
        onCancel={noop}
        onDeleteCredential={noop}
        onMakeDefault={async () => undefined}
        onReleaseCredential={async () => undefined}
        onReleaseSessions={async () => undefined}
        onResumeReleasedBatch={async () => undefined}
        onSelectCredential={noop}
        onTestAll={async () => undefined}
        onTestCredential={async () => undefined}
        progressById={{
          warning: { credentialId: "warning", phase: "warning", message: "warning", result: null },
          error: { credentialId: "error", phase: "error", message: "error", result: null },
        }}
        releaseBusy={false}
        releasedBatchesCount={0}
        resumeReleasedBusy={false}
        runStatus="completed"
        selectedCredentialId={null}
        singleTestingId={null}
      />,
    );
    expect(screen.getByText("1 da controllare")).toBeInTheDocument();
    expect(screen.getByText("1 falliti")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "2");
  });
});
