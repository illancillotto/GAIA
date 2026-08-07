import { describe, expect, test } from "vitest";

import { formatDateTime, formatDuration, getPermissionLevel } from "@/lib/presentation";

describe("formatDateTime", () => {
  test("returns em dash for empty values", () => {
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime("")).toBe("—");
  });

  test("returns raw value when parsing fails", () => {
    expect(formatDateTime("not-a-date")).toBe("not-a-date");
  });

  test("formats valid ISO timestamps in Italian locale", () => {
    const formatted = formatDateTime("2026-05-16T14:30:00.000Z");
    expect(formatted).toMatch(/\d/);
    expect(formatted).not.toBe("—");
  });
});

describe("formatDuration", () => {
  test("returns em dash for null", () => {
    expect(formatDuration(null)).toBe("—");
  });

  test("formats sub-second durations in milliseconds", () => {
    expect(formatDuration(250)).toBe("250 ms");
    expect(formatDuration(999)).toBe("999 ms");
  });

  test("formats longer durations in seconds", () => {
    expect(formatDuration(1000)).toBe("1.0 s");
    expect(formatDuration(1530)).toBe("1.5 s");
  });
});

describe("getPermissionLevel", () => {
  test("maps permission flags to levels", () => {
    expect(getPermissionLevel({ is_denied: true, can_read: true, can_write: true })).toBe("deny");
    expect(getPermissionLevel({ is_denied: false, can_read: true, can_write: true })).toBe("rw");
    expect(getPermissionLevel({ is_denied: false, can_read: true, can_write: false })).toBe("read");
    expect(getPermissionLevel({ is_denied: false, can_read: false, can_write: false })).toBe("none");
  });
});
