"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";

import { sendPresenceHeartbeat } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getCurrentPresenceActionLabel, getPresenceActionChangedEventName } from "@/lib/presence-actions";
import { resolvePresenceRouteMeta } from "@/lib/presence";

export function usePresenceHeartbeat({ enabled = true }: { enabled?: boolean }) {
  const pathname = usePathname();
  const normalizedPathname = pathname || "/";
  const { moduleKey, routeLabel } = resolvePresenceRouteMeta(normalizedPathname);

  useEffect(() => {
    if (!enabled || typeof window === "undefined") {
      return;
    }

    async function pushHeartbeat() {
      const token = getStoredAccessToken();
      if (!token) {
        return;
      }

      try {
        await sendPresenceHeartbeat(token, {
          path: normalizedPathname,
          route_label: routeLabel,
          module_key: moduleKey,
          action_label: getCurrentPresenceActionLabel(),
          visible: document.visibilityState === "visible",
        });
      } catch (error) {
        if (process.env.NODE_ENV !== "test") {
          console.warn("Presence heartbeat failed", error);
        }
      }
    }

    void pushHeartbeat();

    const intervalId = window.setInterval(() => {
      if (document.visibilityState !== "visible") {
        return;
      }
      void pushHeartbeat();
    }, 60_000);

    const handleVisibilityChange = () => {
      void pushHeartbeat();
    };
    const handleActionChanged = () => {
      void pushHeartbeat();
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("focus", handleVisibilityChange);
    window.addEventListener(getPresenceActionChangedEventName(), handleActionChanged);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("focus", handleVisibilityChange);
      window.removeEventListener(getPresenceActionChangedEventName(), handleActionChanged);
    };
  }, [enabled, moduleKey, normalizedPathname, routeLabel]);
}
