"use client";

import { useEffect, useRef } from "react";

interface UsePollingOptions {
  /** When false the timer is torn down and nothing runs. */
  enabled: boolean;
  /** Interval between ticks, in milliseconds. */
  intervalMs: number;
  /** Re-run the callback as soon as the tab becomes visible again. Default true. */
  refetchOnVisible?: boolean;
}

/**
 * Interval polling that is safe under load:
 * - skips ticks while the tab is hidden (Page Visibility API);
 * - never lets a new tick start while the previous invocation is still running,
 *   so a slow backend cannot pile up overlapping requests;
 * - optionally fires once immediately when the tab regains focus.
 *
 * The callback identity does not need to be stable: the latest one is always used.
 */
export function usePolling(callback: () => void | Promise<void>, options: UsePollingOptions): void {
  const { enabled, intervalMs, refetchOnVisible = true } = options;
  const callbackRef = useRef(callback);
  const runningRef = useRef(false);

  useEffect(() => {
    callbackRef.current = callback;
  });

  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    let cancelled = false;

    const tick = async (): Promise<void> => {
      if (cancelled || runningRef.current) {
        return;
      }
      if (typeof document !== "undefined" && document.visibilityState === "hidden") {
        return;
      }
      runningRef.current = true;
      try {
        await callbackRef.current();
      } finally {
        runningRef.current = false;
      }
    };

    const timer = window.setInterval(() => void tick(), intervalMs);

    const handleVisibility = (): void => {
      if (refetchOnVisible && document.visibilityState === "visible") {
        void tick();
      }
    };
    if (refetchOnVisible) {
      document.addEventListener("visibilitychange", handleVisibility);
    }

    return () => {
      cancelled = true;
      window.clearInterval(timer);
      if (refetchOnVisible) {
        document.removeEventListener("visibilitychange", handleVisibility);
      }
    };
  }, [enabled, intervalMs, refetchOnVisible]);
}
