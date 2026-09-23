"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import {
  getApplicationUserQgisDesktopAccess,
  provisionApplicationUserQgisDesktopAccess,
  revokeApplicationUserQgisDesktopAccess,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { ApplicationUser, QgisDesktopAccessStatus, QgisDesktopCredentials } from "@/types/api";

type UserQgisDesktopAccessPanelProps = {
  user: Pick<ApplicationUser, "id" | "username" | "is_active" | "module_gis">;
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Operazione QGIS Desktop non riuscita.";
}

export function UserQgisDesktopAccessPanel({
  user,
}: UserQgisDesktopAccessPanelProps) {
  const { access, credentials, error, busy, enableAccess, disableAccess, hideCredentials } =
    useQgisDesktopAccess(user);
  const canEnable = user.is_active && user.module_gis;

  return (
    <section className="rounded-2xl border border-[#dfe7dc] bg-[#f8fbf8] p-4 lg:col-span-12">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-gray-800">QGIS Desktop / PostGIS</p>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-gray-500">
            Credenziale PostGIS personale in sola lettura. I grant seguono i layer visibili all&apos;utente in GAIA.
          </p>
        </div>
        <AccessBadge access={access} />
      </div>

      {!canEnable ? (
        <p className="mt-3 rounded-xl border border-white bg-white px-3 py-2 text-xs leading-5 text-gray-500">
          Attiva e salva prima l&apos;account e il modulo GIS per abilitare QGIS Desktop.
        </p>
      ) : (
        <AccessActions
          access={access}
          busy={busy}
          onEnable={enableAccess}
          onDisable={disableAccess}
        />
      )}

      {credentials ? (
        <QgisCredentialsNotice credentials={credentials} onHide={hideCredentials} />
      ) : null}
      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
    </section>
  );
}

function useQgisDesktopAccess(user: UserQgisDesktopAccessPanelProps["user"]) {
  const [access, setAccess] = useState<QgisDesktopAccessStatus | null>(null);
  const [credentials, setCredentials] = useState<QgisDesktopCredentials | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setAccess(null);
    setCredentials(null);
    setError(null);
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione GAIA non disponibile.");
      return () => {
        cancelled = true;
      };
    }
    void getApplicationUserQgisDesktopAccess(token, user.id)
      .then((result) => {
        if (!cancelled) setAccess(result);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) setError(errorMessage(loadError));
      });
    return () => {
      cancelled = true;
    };
  }, [user.id, user.is_active, user.module_gis]);

  async function enableAccess() {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione GAIA non disponibile.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await provisionApplicationUserQgisDesktopAccess(token, user.id);
      setAccess(result);
      setCredentials(result);
    } catch (provisionError) {
      setError(errorMessage(provisionError));
    } finally {
      setBusy(false);
    }
  }

  async function disableAccess() {
    if (!window.confirm(`Disabilitare l'accesso QGIS Desktop per ${user.username}?`)) return;
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione GAIA non disponibile.");
      return;
    }
    setBusy(true);
    setError(null);
    setCredentials(null);
    try {
      setAccess(await revokeApplicationUserQgisDesktopAccess(token, user.id));
    } catch (revokeError) {
      setError(errorMessage(revokeError));
    } finally {
      setBusy(false);
    }
  }

  return {
    access,
    credentials,
    error,
    busy,
    enableAccess,
    disableAccess,
    hideCredentials: () => setCredentials(null),
  };
}

function AccessBadge({ access }: { access: QgisDesktopAccessStatus | null }) {
  if (!access) return <Badge variant="neutral">Verifica accesso...</Badge>;
  return (
    <Badge variant={access.enabled ? "success" : "neutral"}>
      {access.enabled ? `Abilitato · ${access.layer_count} layer` : "Disabilitato"}
    </Badge>
  );
}

function AccessActions({
  access,
  busy,
  onEnable,
  onDisable,
}: {
  access: QgisDesktopAccessStatus | null;
  busy: boolean;
  onEnable: () => Promise<void>;
  onDisable: () => Promise<void>;
}) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      <button
        className="btn-secondary disabled:cursor-not-allowed disabled:opacity-60"
        disabled={busy || !access}
        onClick={() => void onEnable()}
        type="button"
      >
        {busy ? "Aggiornamento..." : access?.enabled ? "Ruota password QGIS" : "Abilita QGIS Desktop"}
      </button>
      {access?.enabled ? (
        <button
          className="btn-secondary disabled:cursor-not-allowed disabled:opacity-60"
          disabled={busy}
          onClick={() => void onDisable()}
          type="button"
        >
          Disabilita QGIS Desktop
        </button>
      ) : null}
    </div>
  );
}

function QgisCredentialsNotice({
  credentials,
  onHide,
}: {
  credentials: QgisDesktopCredentials;
  onHide: () => void;
}) {
  return (
    <div className="mt-4 rounded-xl border border-emerald-200 bg-white p-3 text-sm">
      <p className="font-semibold text-emerald-900">Password mostrata solo ora</p>
      <p className="mt-1 text-xs leading-5 text-gray-600">
        Inserisci queste credenziali nella connessione PostgreSQL di QGIS e conservale nel gestore credenziali QGIS.
        Per mostrarne una nuova usa “Ruota password QGIS”.
      </p>
      <dl className="mt-3 grid gap-2 sm:grid-cols-2">
        <div>
          <dt className="text-xs text-gray-500">Utente</dt>
          <dd className="select-all font-mono">{credentials.username}</dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">Password</dt>
          <dd className="select-all break-all font-mono">{credentials.password}</dd>
        </div>
      </dl>
      <button
        className="mt-3 text-xs font-semibold text-emerald-800 underline"
        onClick={onHide}
        type="button"
      >
        Nascondi credenziali
      </button>
    </div>
  );
}
