"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { getEffectivePermissions } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { EffectivePermission } from "@/types/api";

export default function EffectivePermissionsPage() {
  const [permissions, setPermissions] = useState<EffectivePermission[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPermissions() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        setPermissions(await getEffectivePermissions(token));
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento permessi");
      }
    }

    void loadPermissions();
  }, []);

  return (
    <ProtectedPage
      title="Permessi Effettivi"
      description="Vista reale dei permessi effettivi già persistiti nel backend."
    >
      {error ? <p className="status-note error-text">{error}</p> : null}
      <table className="data-table">
        <thead>
          <tr>
            <th>Utente NAS</th>
            <th>Share</th>
            <th>Read</th>
            <th>Write</th>
            <th>Deny</th>
            <th>Fonte</th>
          </tr>
        </thead>
        <tbody>
          {permissions.map((permission) => (
            <tr key={permission.id}>
              <td>{permission.nas_user_id}</td>
              <td>{permission.share_id}</td>
              <td>{permission.can_read ? "Si" : "No"}</td>
              <td>{permission.can_write ? "Si" : "No"}</td>
              <td>{permission.is_denied ? "Si" : "No"}</td>
              <td>{permission.source_summary}</td>
            </tr>
          ))}
          {permissions.length === 0 ? (
            <tr>
              <td colSpan={6}>Nessun permesso effettivo persistito nel backend.</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </ProtectedPage>
  );
}
