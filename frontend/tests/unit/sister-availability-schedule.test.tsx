import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import {
  defaultSisterSchedule,
  nextSisterAvailability,
  sisterCredentialIsAvailable,
  SisterAvailabilityScheduleEditor,
} from "@/components/elaborazioni/sister-availability-schedule";
import { SisterCredentialPoolView } from "@/components/elaborazioni/sister-credential-pool-view";

describe("Sister availability schedule", () => {
  test("evaluates daytime, overnight and disabled schedules in Europe/Rome", () => {
    const schedule = defaultSisterSchedule();
    expect(sisterCredentialIsAvailable(false, null, new Date("2026-08-24T10:00:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-24T17:00:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-25T05:59:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-25T06:00:00Z"))).toBe(false);
    expect(sisterCredentialIsAvailable(true, schedule, new Date("2026-08-29T10:00:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, null, new Date("2026-08-24T10:00:00Z"))).toBe(false);
    const daytime = { timezone: "Europe/Rome" as const, weekly: { "0": [{ start: "10:00", end: "12:00" }] } };
    expect(sisterCredentialIsAvailable(true, daytime, new Date("2026-08-24T09:00:00Z"))).toBe(true);
    expect(sisterCredentialIsAvailable(true, daytime, new Date("2026-08-24T11:00:00Z"))).toBe(false);
  });

  test("finds the next opening and handles schedules without openings", () => {
    const schedule = defaultSisterSchedule();
    const reference = new Date("2026-08-24T15:58:00Z");
    expect(nextSisterAvailability(true, schedule, reference)?.toISOString()).toBe("2026-08-24T16:00:00.000Z");
    expect(nextSisterAvailability(false, null, reference)).toBe(reference);
    expect(nextSisterAvailability(true, { timezone: "Europe/Rome", weekly: {} }, reference)).toBeNull();
    expect(nextSisterAvailability(true, { timezone: "Europe/Rome", weekly: { "7": [{ start: "bad", end: "bad" }] } }, reference)).toBeNull();
    expect(nextSisterAvailability(true, { timezone: "Europe/Rome", weekly: { "0": [{ start: "99:99", end: "bad" }] } }, reference)).toBeNull();
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
    expect(onScheduleChange).toHaveBeenLastCalledWith(expect.objectContaining({ weekly: expect.objectContaining({ "1": [{ start: "19:00", end: "08:00" }] }) }));
    fireEvent.change(screen.getByLabelText("Martedi alle"), { target: { value: "07:00" } });
    expect(onScheduleChange).toHaveBeenLastCalledWith(expect.objectContaining({ weekly: expect.objectContaining({ "1": [{ start: "18:00", end: "07:00" }] }) }));

    const scheduleWithClosedMonday = defaultSisterSchedule();
    scheduleWithClosedMonday.weekly["0"] = [];
    rerender(<SisterAvailabilityScheduleEditor enabled onEnabledChange={onEnabledChange} onScheduleChange={onScheduleChange} schedule={scheduleWithClosedMonday} />);
    fireEvent.click(screen.getByRole("checkbox", { name: "Lunedi disponibile" }));
    expect(onScheduleChange).toHaveBeenLastCalledWith(expect.objectContaining({ weekly: expect.objectContaining({ "0": [{ start: "18:00", end: "08:00" }] }) }));
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
