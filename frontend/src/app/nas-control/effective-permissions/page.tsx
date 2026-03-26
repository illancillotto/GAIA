"use client";

import { FormEvent, useDeferredValue, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { DataTable } from "@/components/table/data-table";
import { TableFilters } from "@/components/table/table-filters";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { PermissionBadge } from "@/components/ui/permission-badge";
import { SourceTag } from "@/components/ui/source-tag";
import { SearchIcon } from "@/components/ui/icons";
import { useDomainData } from "@/hooks/use-domain-data";
import { calculatePermissionPreview, getEffectivePermissions } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getPermissionLevel } from "@/lib/presentation";
import type { EffectivePermission, EffectivePermissionPreview } from "@/types/api";

type AccessFilter = "all" | "read" | "write" | "denied";

type PermissionRow = {
  id: number;
  nasUser: string;
  share: string;
  canRead: boolean;
  canWrite: boolean;
  isDenied: boolean;
  sourceSummary: string;
};

export default function EffectivePermissionsPage() {
  const [permissions, setPermissions] = useState<EffectivePermission[]>([]);
  const [previewResults, setPreviewResults] = useState<EffectivePermissionPreview[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [accessFilter, setAccessFilter] = useState<AccessFilter>("all");
  const [username, setUsername] = useState("");
  const [groupsInput, setGroupsInput] = useState("");
  const [shareName, setShareName] = useState("");
  const [subjectType, setSubjectType] = useState("group");
  const [subjectName, setSubjectName] = useState("");
  const [permissionLevel, setPermissionLevel] = useState("write");
  const [isDeny, setIsDeny] = useState(false);
  const { users, groups, shares, error: domainError } = useDomainData();

  const deferredSearchTerm = useDeferredValue(searchTerm);

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

  useEffect(() => {
    if (!username && users[0]?.username) {
      setUsername(users[0].username);
    }
    if (!shareName && shares[0]?.name) {
      setShareName(shares[0].name);
    }
    if (!groupsInput && groups[0]?.name) {
      setGroupsInput(groups[0].name);
    }
  }, [users, shares, groups, username, shareName, groupsInput]);

  useEffect(() => {
    const candidates = subjectType === "group" ? groups.map((group) => group.name) : users.map((user) => user.username);
    if (!subjectName && candidates[0]) {
      setSubjectName(candidates[0]);
    } else if (subjectName && !candidates.includes(subjectName) && candidates[0]) {
      setSubjectName(candidates[0]);
    }
  }, [subjectType, users, groups, subjectName]);

  const userLabelMap = useMemo(
    () => new Map(users.map((user) => [user.id, user.username])),
    [users],
  );

  const shareLabelMap = useMemo(
    () => new Map(shares.map((share) => [share.id, share.name])),
    [shares],
  );

  const rows = useMemo<PermissionRow[]>(
    () =>
      permissions.map((permission) => ({
        id: permission.id,
        nasUser: userLabelMap.get(permission.nas_user_id) ?? String(permission.nas_user_id),
        share: shareLabelMap.get(permission.share_id) ?? String(permission.share_id),
        canRead: permission.can_read,
        canWrite: permission.can_write,
        isDenied: permission.is_denied,
        sourceSummary: permission.source_summary,
      })),
    [permissions, userLabelMap, shareLabelMap],
  );

  const filteredRows = useMemo(() => {
    const normalizedSearch = deferredSearchTerm.trim().toLowerCase();

    return rows.filter((row) => {
      if (accessFilter === "read" && !row.canRead) return false;
      if (accessFilter === "write" && !row.canWrite) return false;
      if (accessFilter === "denied" && !row.isDenied) return false;

      if (!normalizedSearch) return true;

      return [row.nasUser, row.share, row.sourceSummary].some((value) =>
        value.toLowerCase().includes(normalizedSearch),
      );
    });
  }, [rows, deferredSearchTerm, accessFilter]);

  async function handlePreview(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const token = getStoredAccessToken();

    if (!token) {
      setPreviewError("Accedi prima di eseguire una preview.");
      return;
    }

    try {
      const result = await calculatePermissionPreview(
        token,
        [
          {
            username,
            groups: groupsInput
              .split(",")
              .map((value) => value.trim())
              .filter(Boolean),
          },
        ],
        [
          {
            share_name: shareName,
            subject_type: subjectType,
            subject_name: subjectName,
            permission_level: permissionLevel,
            is_deny: isDeny,
          },
        ],
      );

      setPreviewResults(result);
      setPreviewError(null);
    } catch (loadError) {
      setPreviewError(loadError instanceof Error ? loadError.message : "Errore preview permessi");
    }
  }

  const columns = useMemo<ColumnDef<PermissionRow>[]>(
    () => [
      {
        header: "Utente NAS",
        accessorKey: "nasUser",
      },
      {
        header: "Cartella",
        accessorKey: "share",
      },
      {
        header: "Permesso",
        accessorKey: "sourceSummary",
        cell: ({ row }) => (
          <PermissionBadge
            level={row.original.isDenied ? "deny" : row.original.canWrite ? "rw" : row.original.canRead ? "read" : "none"}
          />
        ),
      },
      {
        header: "Read",
        accessorKey: "canRead",
        cell: ({ row }) => (
          <span className={row.original.canRead ? "font-medium text-green-600" : "text-gray-300"}>
            {row.original.canRead ? "✓" : "—"}
          </span>
        ),
      },
      {
        header: "Write",
        accessorKey: "canWrite",
        cell: ({ row }) => (
          <span className={row.original.canWrite ? "font-medium text-green-600" : "text-gray-300"}>
            {row.original.canWrite ? "✓" : "—"}
          </span>
        ),
      },
      {
        header: "Deny",
        accessorKey: "isDenied",
        cell: ({ row }) => (
          <span className={row.original.isDenied ? "font-medium text-red-500" : "text-gray-300"}>
            {row.original.isDenied ? "✗" : "—"}
          </span>
        ),
      },
      {
        header: "Origine",
        accessorKey: "sourceSummary",
        cell: ({ row }) => <SourceTag source={row.original.sourceSummary} />,
      },
    ],
    [],
  );

  return (
    <ProtectedPage
      title="Permessi effettivi"
      description="Ultimo snapshot persistito e simulazione guidata del motore di calcolo permessi."
      breadcrumb="NAS Control"
    >
      {error || domainError ? <p className="text-sm text-red-600">{error ?? domainError}</p> : null}

      <div className="surface-grid">
        <MetricCard label="Permessi totali" value={permissions.length} sub="Record persistiti nell’ultimo snapshot" />
        <MetricCard label="Con lettura" value={permissions.filter((item) => item.can_read).length} sub="Utenti con accesso in lettura" variant="info" />
        <MetricCard label="Con scrittura" value={permissions.filter((item) => item.can_write).length} sub="Utenti con accesso in scrittura" variant="success" />
        <MetricCard label="Negati" value={permissions.filter((item) => item.is_denied).length} sub="Record con deny esplicito" variant="danger" />
      </div>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Filtri</p>
          <p className="section-copy">Ricerca su utente, cartella e origine con filtro sul tipo di accesso.</p>
        </div>
        <TableFilters>
          <label className="text-sm font-medium text-gray-700">
            Cerca
            <input
              className="form-control mt-1"
              type="text"
              placeholder="Es. administrators, EmailSaver, deny"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </label>
          <label className="text-sm font-medium text-gray-700">
            Accesso
            <select
              className="form-control mt-1"
              value={accessFilter}
              onChange={(event) => setAccessFilter(event.target.value as AccessFilter)}
            >
              <option value="all">Tutti</option>
              <option value="read">Solo lettura</option>
              <option value="write">Con scrittura</option>
              <option value="denied">Solo deny</option>
            </select>
          </label>
        </TableFilters>
      </article>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Permessi persistiti</p>
          <p className="section-copy">Tabella filtrabile dei permessi effettivi calcolati e persistiti nel backend.</p>
        </div>
        <DataTable
          data={filteredRows}
          columns={columns}
          emptyTitle="Nessun permesso trovato"
          emptyDescription="Nessun permesso effettivo corrisponde ai filtri selezionati."
          initialPageSize={12}
        />
      </article>

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Preview guidata</p>
          <p className="section-copy">Simula una regola puntuale senza scrivere nulla nel backend.</p>
        </div>
        <form className="space-y-4" onSubmit={(event) => void handlePreview(event)}>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <label className="text-sm font-medium text-gray-700">
              Utente
              <select className="form-control mt-1" value={username} onChange={(event) => setUsername(event.target.value)}>
                {users.map((user) => (
                  <option key={user.id} value={user.username}>
                    {user.username}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm font-medium text-gray-700">
              Gruppi utente
              <input
                className="form-control mt-1"
                list="available-groups"
                value={groupsInput}
                onChange={(event) => setGroupsInput(event.target.value)}
              />
            </label>

            <label className="text-sm font-medium text-gray-700">
              Cartella
              <select className="form-control mt-1" value={shareName} onChange={(event) => setShareName(event.target.value)}>
                {shares.map((share) => (
                  <option key={share.id} value={share.name}>
                    {share.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm font-medium text-gray-700">
              Tipo soggetto
              <select className="form-control mt-1" value={subjectType} onChange={(event) => setSubjectType(event.target.value)}>
                <option value="group">Gruppo</option>
                <option value="user">Utente</option>
              </select>
            </label>

            <label className="text-sm font-medium text-gray-700">
              Soggetto
              <select className="form-control mt-1" value={subjectName} onChange={(event) => setSubjectName(event.target.value)}>
                {(subjectType === "group" ? groups.map((group) => group.name) : users.map((user) => user.username)).map(
                  (value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ),
                )}
              </select>
            </label>

            <label className="text-sm font-medium text-gray-700">
              Livello permesso
              <select className="form-control mt-1" value={permissionLevel} onChange={(event) => setPermissionLevel(event.target.value)}>
                <option value="read">Lettura</option>
                <option value="write">Read + Write</option>
              </select>
            </label>
          </div>

          <label className="inline-flex items-center gap-2 text-sm text-gray-700">
            <input checked={isDeny} onChange={(event) => setIsDeny(event.target.checked)} type="checkbox" />
            Applica come deny
          </label>

          <datalist id="available-groups">
            {groups.map((group) => (
              <option key={group.id} value={group.name} />
            ))}
          </datalist>

          {previewError ? <p className="text-sm text-red-600">{previewError}</p> : null}

          <button className="btn-primary" type="submit">
            Calcola preview
          </button>
        </form>

        <div className="mt-5">
          {previewResults.length === 0 ? (
            <EmptyState
              icon={SearchIcon}
              title="Nessuna preview disponibile"
              description="Compila il form e avvia il calcolo per simulare una regola puntuale."
            />
          ) : (
            <div className="overflow-hidden rounded-xl border border-gray-100">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Utente</th>
                    <th>Cartella</th>
                    <th>Permesso</th>
                    <th>Origine</th>
                  </tr>
                </thead>
                <tbody>
                  {previewResults.map((result) => (
                    <tr key={`${result.username}-${result.share_name}-${result.source_summary}`}>
                      <td>{result.username}</td>
                      <td>{result.share_name}</td>
                      <td>
                        <PermissionBadge level={getPermissionLevel(result)} />
                      </td>
                      <td>
                        <SourceTag source={result.source_summary} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </article>
    </ProtectedPage>
  );
}
