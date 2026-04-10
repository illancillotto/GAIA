"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { formatRiordinoDate, formatRiordinoLabel } from "@/components/riordino/shared/format";
import { BellIcon } from "@/components/ui/icons";
import { checkRiordinoDeadlines, listRiordinoNotifications, markRiordinoNotificationRead } from "@/lib/riordino-api";
import { cn } from "@/lib/cn";
import type { RiordinoNotification } from "@/types/riordino";

type RiordinoNotificationBellProps = {
  token: string;
};

export function RiordinoNotificationBell({ token }: RiordinoNotificationBellProps) {
  const [items, setItems] = useState<RiordinoNotification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshNotifications = useCallback(async () => {
    try {
      const notifications = await listRiordinoNotifications(token);
      setItems(notifications);
      setError(null);
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile caricare le notifiche");
    }
  }, [token]);

  useEffect(() => {
    void refreshNotifications();
  }, [refreshNotifications]);

  const unreadCount = useMemo(() => items.filter((item) => !item.is_read).length, [items]);

  async function handleMarkRead(notificationId: string) {
    setBusy(true);
    try {
      await markRiordinoNotificationRead(token, notificationId);
      await refreshNotifications();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile aggiornare la notifica");
    } finally {
      setBusy(false);
    }
  }

  async function handleCheckDeadlines() {
    setBusy(true);
    try {
      await checkRiordinoDeadlines(token);
      await refreshNotifications();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile verificare le scadenze");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        className={cn(
          "relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-600 transition hover:border-[#8CB39D] hover:text-[#1D4E35]",
          isOpen ? "border-[#8CB39D] text-[#1D4E35]" : undefined,
        )}
        onClick={() => setIsOpen((current) => !current)}
        aria-label="Notifiche riordino"
      >
        <BellIcon className="h-4 w-4" />
        {unreadCount > 0 ? (
          <span className="absolute -right-1 -top-1 inline-flex min-h-5 min-w-5 items-center justify-center rounded-full bg-[#C84C2A] px-1 text-[10px] font-semibold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div className="absolute right-0 top-11 z-20 w-[360px] rounded-2xl border border-gray-100 bg-white p-3 shadow-xl">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-gray-900">Notifiche riordino</p>
              <p className="text-xs text-gray-500">{unreadCount} non lette</p>
            </div>
            <button className="btn-secondary" disabled={busy} onClick={() => void handleCheckDeadlines()} type="button">
              Verifica scadenze
            </button>
          </div>

          {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}

          <div className="max-h-[420px] space-y-2 overflow-y-auto">
            {items.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-center text-sm text-gray-500">
                Nessuna notifica disponibile.
              </div>
            ) : (
              items.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    "rounded-xl border px-3 py-3",
                    item.is_read ? "border-gray-100 bg-white" : "border-[#D4E6DA] bg-[#F5FBF7]",
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900">{item.message}</p>
                      <p className="mt-1 text-xs text-gray-500">
                        {formatRiordinoLabel(item.type)} • {formatRiordinoDate(item.created_at, true)}
                      </p>
                    </div>
                    {!item.is_read ? (
                      <button
                        className="text-xs font-medium text-[#1D4E35] transition hover:text-[#163A28]"
                        disabled={busy}
                        onClick={() => void handleMarkRead(item.id)}
                        type="button"
                      >
                        Segna letta
                      </button>
                    ) : null}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
