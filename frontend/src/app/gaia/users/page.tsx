"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { DataTable } from "@/components/table/data-table";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { MetricCard } from "@/components/ui/metric-card";
import {
  createApplicationUser,
  deleteApplicationUser,
  getCurrentUser,
  listApplicationUsers,
  updateApplicationUser,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { ApplicationUser, CurrentUser } from "@/types/api";

type GaiaUserRow = {
  id: number;
  username: string;
  email: string;
  role: string;
  isActive: boolean;
  modulesLabel: string;
  item: ApplicationUser;
};

type UserFormState = {
  username: string;
  email: string;
  password: string;
  role: string;
  isActive: boolean;
  moduleAccessi: boolean;
  moduleRete: boolean;
  moduleInventario: boolean;
  moduleCatasto: boolean;
};

const emptyFormState: UserFormState = {
  username: "",
  email: "",
  password: "",
  role: "viewer",
  isActive: true,
  moduleAccessi: true,
  moduleRete: false,
  moduleInventario: false,
  moduleCatasto: false,
};

const roleOptions = [
  { value: "viewer", label: "Viewer" },
  { value: "reviewer", label: "Reviewer" },
  { value: "admin", label: "Admin" },
  { value: "super_admin", label: "Super Admin" },
];

function formatModules(user: ApplicationUser): string {
  const labels: string[] = [];

  if (user.module_accessi) {
    labels.push("NAS Control");
  }
  if (user.module_rete) {
    labels.push("Rete");
  }
  if (user.module_inventario) {
    labels.push("Inventario");
  }
  if (user.module_catasto) {
    labels.push("Catasto");
  }

  return labels.length > 0 ? labels.join(", ") : "Nessun modulo";
}

export default function GaiaUsersPage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [users, setUsers] = useState<ApplicationUser[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [formState, setFormState] = useState<UserFormState>(emptyFormState);
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const deferredSearchTerm = useDeferredValue(searchTerm);
  const selectedUser = users.find((user) => user.id === selectedUserId) ?? null;
  const isEditMode = selectedUser !== null;

  useEffect(() => {
    async function loadPage() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const [sessionUser, response] = await Promise.all([
          getCurrentUser(token),
          listApplicationUsers(token),
        ]);
        setCurrentUser(sessionUser);
        setUsers(response.items);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento utenti GAIA");
      }
    }

    void loadPage();
  }, []);

  useEffect(() => {
    if (!selectedUser) {
      setFormState(emptyFormState);
      return;
    }

    setFormState({
      username: selectedUser.username,
      email: selectedUser.email,
      password: "",
      role: selectedUser.role,
      isActive: selectedUser.is_active,
      moduleAccessi: selectedUser.module_accessi,
      moduleRete: selectedUser.module_rete,
      moduleInventario: selectedUser.module_inventario,
      moduleCatasto: selectedUser.module_catasto,
    });
  }, [selectedUser]);

  const rows = useMemo<GaiaUserRow[]>(
    () =>
      users.map((user) => ({
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role,
        isActive: user.is_active,
        modulesLabel: formatModules(user),
        item: user,
      })),
    [users],
  );

  const filteredRows = useMemo(() => {
    const normalizedSearch = deferredSearchTerm.trim().toLowerCase();

    return rows.filter((row) => {
      if (roleFilter !== "all" && row.role !== roleFilter) {
        return false;
      }
      if (statusFilter === "active" && !row.isActive) {
        return false;
      }
      if (statusFilter === "inactive" && row.isActive) {
        return false;
      }
      if (!normalizedSearch) {
        return true;
      }

      return [row.username, row.email, row.modulesLabel]
        .some((value) => value.toLowerCase().includes(normalizedSearch));
    });
  }, [rows, deferredSearchTerm, roleFilter, statusFilter]);

  const columns = useMemo<ColumnDef<GaiaUserRow>[]>(
    () => [
      {
        header: "Utente GAIA",
        accessorKey: "username",
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            <Avatar label={row.original.username} />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-[#1D4E35]">{row.original.username}</p>
              <p className="truncate text-xs text-gray-400">{row.original.email}</p>
            </div>
          </div>
        ),
      },
      {
        header: "Ruolo",
        accessorKey: "role",
        cell: ({ row }) => (
          <Badge variant={row.original.role === "super_admin" ? "danger" : row.original.role === "admin" ? "warning" : "info"}>
            {row.original.role}
          </Badge>
        ),
      },
      {
        header: "Stato",
        accessorKey: "isActive",
        cell: ({ row }) => (
          <Badge variant={row.original.isActive ? "success" : "neutral"}>
            {row.original.isActive ? "Attivo" : "Inattivo"}
          </Badge>
        ),
      },
      {
        header: "Moduli",
        accessorKey: "modulesLabel",
        cell: ({ row }) => <span className="text-sm text-gray-600">{row.original.modulesLabel}</span>,
      },
    ],
    [],
  );

  function updateFormState<K extends keyof UserFormState>(key: K, value: UserFormState[K]) {
    setFormState((current) => ({
      ...current,
      [key]: value,
    }));
  }

  async function reloadUsers() {
    const token = getStoredAccessToken();
    if (!token) return;

    const response = await listApplicationUsers(token);
    setUsers(response.items);
  }

  async function handleSubmit() {
    const token = getStoredAccessToken();
    if (!token) return;

    setIsSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      if (isEditMode && selectedUser) {
        await updateApplicationUser(token, selectedUser.id, {
          email: formState.email,
          password: formState.password.trim().length > 0 ? formState.password : undefined,
          role: formState.role,
          is_active: formState.isActive,
          module_accessi: formState.moduleAccessi,
          module_rete: formState.moduleRete,
          module_inventario: formState.moduleInventario,
          module_catasto: formState.moduleCatasto,
        });
        setSuccessMessage(`Utente ${selectedUser.username} aggiornato.`);
      } else {
        await createApplicationUser(token, {
          username: formState.username,
          email: formState.email,
          password: formState.password,
          role: formState.role,
          is_active: formState.isActive,
          module_accessi: formState.moduleAccessi,
          module_rete: formState.moduleRete,
          module_inventario: formState.moduleInventario,
          module_catasto: formState.moduleCatasto,
        });
        setSuccessMessage(`Utente ${formState.username} creato.`);
      }

      await reloadUsers();
      if (!isEditMode) {
        setFormState(emptyFormState);
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Operazione non riuscita");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!selectedUser || !currentUser) return;
    if (currentUser.role !== "super_admin" || selectedUser.id === currentUser.id) return;

    const token = getStoredAccessToken();
    if (!token) return;

    setIsSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await deleteApplicationUser(token, selectedUser.id);
      setSuccessMessage(`Utente ${selectedUser.username} eliminato.`);
      setSelectedUserId(null);
      setFormState(emptyFormState);
      await reloadUsers();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Eliminazione non riuscita");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ProtectedPage
      title="Utenti GAIA"
      description="Gestione degli utenti applicativi di GAIA, con ruoli, stato account e moduli abilitati."
      breadcrumb="Amministrazione"
      requiredRoles={["admin", "super_admin"]}
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {successMessage ? <p className="text-sm text-[#1D4E35]">{successMessage}</p> : null}

      <div className="surface-grid">
        <MetricCard label="Utenti GAIA" value={users.length} sub="Account applicativi censiti" />
        <MetricCard label="Attivi" value={users.filter((user) => user.is_active).length} sub="Account abilitati al login" variant="success" />
        <MetricCard label="Admin" value={users.filter((user) => user.role === "admin" || user.role === "super_admin").length} sub="Profili amministrativi" />
        <MetricCard label="NAS Control" value={users.filter((user) => user.module_accessi).length} sub="Utenti con modulo NAS abilitato" />
        <MetricCard label="Catasto" value={users.filter((user) => user.module_catasto).length} sub="Utenti con modulo Catasto abilitato" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <article className="panel-card">
          <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="section-title">Directory utenti applicativi</p>
              <p className="section-copy">Elenco degli account che possono accedere a GAIA.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <label className="text-xs font-medium uppercase tracking-[0.14em] text-gray-400">
                Cerca
                <input
                  className="form-control mt-1 min-w-[12rem]"
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Username o email"
                />
              </label>
              <label className="text-xs font-medium uppercase tracking-[0.14em] text-gray-400">
                Ruolo
                <select className="form-control mt-1" value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)}>
                  <option value="all">Tutti</option>
                  {roleOptions.map((role) => (
                    <option key={role.value} value={role.value}>
                      {role.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs font-medium uppercase tracking-[0.14em] text-gray-400">
                Stato
                <select className="form-control mt-1" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                  <option value="all">Tutti</option>
                  <option value="active">Attivi</option>
                  <option value="inactive">Inattivi</option>
                </select>
              </label>
            </div>
          </div>

          <DataTable
            data={filteredRows}
            columns={columns}
            initialPageSize={10}
            onRowClick={(row) => {
              setSelectedUserId(row.id);
              setSuccessMessage(null);
            }}
            emptyTitle="Nessun utente GAIA"
            emptyDescription="Non risultano account coerenti con i filtri correnti."
          />
        </article>

        <article className="panel-card">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <p className="section-title">{isEditMode ? "Modifica utente GAIA" : "Nuovo utente GAIA"}</p>
              <p className="section-copy">
                {isEditMode
                  ? "Aggiorna ruolo, stato, password e moduli dell’account selezionato."
                  : "Crea un nuovo account applicativo con i moduli GAIA autorizzati."}
              </p>
            </div>
            {isEditMode ? (
              <button
                className="btn-secondary"
                onClick={() => {
                  setSelectedUserId(null);
                  setFormState(emptyFormState);
                  setSuccessMessage(null);
                }}
                type="button"
              >
                Nuovo
              </button>
            ) : null}
          </div>

          <div className="space-y-4">
            <label className="block text-sm font-medium text-gray-700">
              Username
              <input
                className="form-control mt-1"
                value={formState.username}
                onChange={(event) => updateFormState("username", event.target.value)}
                disabled={isEditMode}
                placeholder="nome.cognome"
              />
            </label>

            <label className="block text-sm font-medium text-gray-700">
              Email
              <input
                className="form-control mt-1"
                value={formState.email}
                onChange={(event) => updateFormState("email", event.target.value)}
                placeholder="utente@ente.local"
              />
            </label>

            <label className="block text-sm font-medium text-gray-700">
              {isEditMode ? "Nuova password" : "Password"}
              <input
                className="form-control mt-1"
                type="password"
                value={formState.password}
                onChange={(event) => updateFormState("password", event.target.value)}
                placeholder={isEditMode ? "Lascia vuoto per non cambiarla" : "Minimo 8 caratteri"}
              />
            </label>

            <label className="block text-sm font-medium text-gray-700">
              Ruolo
              <select className="form-control mt-1" value={formState.role} onChange={(event) => updateFormState("role", event.target.value)}>
                {roleOptions
                  .filter((role) => currentUser?.role === "super_admin" || role.value !== "super_admin")
                  .map((role) => (
                    <option key={role.value} value={role.value}>
                      {role.label}
                    </option>
                  ))}
              </select>
            </label>

            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-sm font-medium text-gray-800">Moduli abilitati</p>
              <div className="mt-3 space-y-3 text-sm text-gray-600">
                <label className="flex items-center gap-3">
                  <input type="checkbox" checked={formState.moduleAccessi} onChange={(event) => updateFormState("moduleAccessi", event.target.checked)} />
                  NAS Control
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" checked={formState.moduleRete} onChange={(event) => updateFormState("moduleRete", event.target.checked)} />
                  Rete
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" checked={formState.moduleInventario} onChange={(event) => updateFormState("moduleInventario", event.target.checked)} />
                  Inventario
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" checked={formState.moduleCatasto} onChange={(event) => updateFormState("moduleCatasto", event.target.checked)} />
                  Catasto
                </label>
                <label className="flex items-center gap-3 pt-2">
                  <input type="checkbox" checked={formState.isActive} onChange={(event) => updateFormState("isActive", event.target.checked)} />
                  Account attivo
                </label>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button className="btn-primary" disabled={isSubmitting} onClick={() => void handleSubmit()} type="button">
                {isSubmitting ? "Salvataggio..." : isEditMode ? "Salva modifiche" : "Crea utente"}
              </button>
              {isEditMode && currentUser?.role === "super_admin" && selectedUser && selectedUser.id !== currentUser.id ? (
                <button className="btn-secondary" disabled={isSubmitting} onClick={() => void handleDelete()} type="button">
                  Elimina utente
                </button>
              ) : null}
            </div>
          </div>
        </article>
      </div>
    </ProtectedPage>
  );
}
