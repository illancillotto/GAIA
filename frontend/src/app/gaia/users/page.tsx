"use client";

import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import {
  buildEditableSectionCatalog,
  buildSectionDraftFromOverrides,
  computeSectionOverrideChanges,
  filterEditableSections,
  groupSectionsByModule,
  hasUnsavedSectionDraftChanges,
  type SectionOverrideValue,
} from "./section-permissions";
import { ProtectedPage } from "@/components/app/protected-page";
import { DataTable } from "@/components/table/data-table";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { MetricCard } from "@/components/ui/metric-card";
import { cn } from "@/lib/cn";
import {
  createApplicationUser,
  deleteApplicationUser,
  deleteApplicationUserPermissionOverride,
  getApplicationUserPermissions,
  getCurrentUser,
  listSectionCatalog,
  listAllApplicationUsers,
  sendApplicationUserInvite,
  updateApplicationUser,
  updateApplicationUserPermissions,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { ApplicationUser, CurrentUser, SectionResponse, UserPermissionsAdminView } from "@/types/api";

type GaiaUserRow = {
  id: number;
  username: string;
  email: string;
  role: string;
  isActive: boolean;
  modulesLabel: string;
  lastLoginAt: string | null;
  lastLoginIp: string | null;
  loginCount: number;
  item: ApplicationUser;
};

type ToastState = {
  tone: "success" | "danger";
  message: string;
} | null;

type UserFormState = {
  username: string;
  email: string;
  password: string;
  role: string;
  isActive: boolean;
  sendInviteEmail: boolean;
  moduleAccessi: boolean;
  moduleRete: boolean;
  moduleInventario: boolean;
  moduleCatasto: boolean;
  moduleUtenze: boolean;
  moduleOperazioni: boolean;
  moduleRiordino: boolean;
  moduleRuolo: boolean;
  modulePresenze: boolean;
};

type ModuleOption = {
  key:
    | "moduleAccessi"
    | "moduleRete"
    | "moduleInventario"
    | "moduleCatasto"
    | "moduleUtenze"
    | "moduleOperazioni"
    | "moduleRiordino"
    | "moduleRuolo"
    | "modulePresenze";
  moduleKey: string;
  label: string;
  description: string;
};

const emptyFormState: UserFormState = {
  username: "",
  email: "",
  password: "",
  role: "viewer",
  isActive: true,
  sendInviteEmail: true,
  moduleAccessi: false,
  moduleRete: false,
  moduleInventario: false,
  moduleCatasto: false,
  moduleUtenze: false,
  moduleOperazioni: false,
  moduleRiordino: false,
  moduleRuolo: false,
  modulePresenze: false,
};

const roleOptions = [
  { value: "operator", label: "Operatore" },
  { value: "viewer", label: "Viewer" },
  { value: "reviewer", label: "Reviewer" },
  { value: "hr_manager", label: "HR Manager" },
  { value: "admin", label: "Admin" },
  { value: "super_admin", label: "Super Admin" },
];

function getRoleLabel(role: string): string {
  return roleOptions.find((option) => option.value === role)?.label ?? role;
}

const moduleOptions: ModuleOption[] = [
  { key: "moduleAccessi", moduleKey: "accessi", label: "NAS Control", description: "Utenti, gruppi, share e permessi." },
  { key: "moduleRete", moduleKey: "rete", label: "Rete", description: "Dispositivi, alert e tracking di rete." },
  { key: "moduleInventario", moduleKey: "inventario", label: "Inventario", description: "Asset e schede inventariali." },
  { key: "moduleCatasto", moduleKey: "catasto", label: "Catasto", description: "GIS, particelle, anomalie e archivio." },
  { key: "moduleUtenze", moduleKey: "utenze", label: "Utenze", description: "Anagrafica soggetti e import." },
  { key: "moduleOperazioni", moduleKey: "operazioni", label: "Operazioni", description: "Operatori, mezzi, attività e pratiche." },
  { key: "moduleRiordino", moduleKey: "riordino", label: "Riordino", description: "Workflow pratiche e configurazione." },
  { key: "moduleRuolo", moduleKey: "ruolo", label: "Ruolo", description: "Avvisi, particelle e import ruolo." },
  { key: "modulePresenze", moduleKey: "presenze", label: "Giornaliere", description: "Collaboratori, giornaliere e organigramma." },
];

function formatDateTimeLabel(value: string | null): string {
  if (!value) return "Mai";
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatGateMobileConsoleRoleLabel(role: string | null | undefined): string {
  if (role === "console_admin") return "Console admin";
  if (role === "device_manager") return "Device manager";
  if (role === "viewer") return "Viewer";
  return "Ruolo non assegnato";
}

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
  if (user.module_utenze) {
    labels.push("Utenze");
  }
  if (user.module_operazioni) {
    labels.push("Operazioni");
  }
  if (user.module_riordino) {
    labels.push("Riordino");
  }
  if (user.module_ruolo) {
    labels.push("Ruolo");
  }
  if (user.module_presenze) {
    labels.push("Giornaliere");
  }

  return labels.length > 0 ? labels.join(", ") : "Nessun modulo";
}

function countEnabledModules(user: ApplicationUser): number {
  return [
    user.module_accessi,
    user.module_rete,
    user.module_inventario,
    user.module_catasto,
    user.module_utenze,
    user.module_operazioni,
    user.module_riordino,
    user.module_ruolo,
    user.module_presenze,
  ].filter(Boolean).length;
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
  const [toast, setToast] = useState<ToastState>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [permissionsView, setPermissionsView] = useState<UserPermissionsAdminView | null>(null);
  const [permissionsLoading, setPermissionsLoading] = useState(false);
  const [sectionCatalog, setSectionCatalog] = useState<SectionResponse[]>([]);
  const [sectionDraft, setSectionDraft] = useState<Record<number, SectionOverrideValue>>({});
  const [sectionSaving, setSectionSaving] = useState(false);
  const [sectionSearchTerm, setSectionSearchTerm] = useState("");
  const [sectionOverrideOnly, setSectionOverrideOnly] = useState(false);
  const [shouldScrollToSectionPermissions, setShouldScrollToSectionPermissions] = useState(false);
  const [componentModalModuleKey, setComponentModalModuleKey] = useState<string | null>(null);
  const sectionPermissionsRef = useRef<HTMLDivElement | null>(null);

  const deferredSearchTerm = useDeferredValue(searchTerm);
  const deferredSectionSearchTerm = useDeferredValue(sectionSearchTerm);
  const selectedUser = users.find((user) => user.id === selectedUserId) ?? null;
  const isEditMode = selectedUser !== null;
  useEffect(() => {
    async function loadPage() {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const sessionUser = await getCurrentUser(token);
        setCurrentUser(sessionUser);
        if ((sessionUser.role === "admin" || sessionUser.role === "super_admin") && sessionUser.enabled_modules.includes("accessi")) {
          const [items, sections] = await Promise.all([
            listAllApplicationUsers(token),
            listSectionCatalog(token, { activeOnly: true }),
          ]);
          setUsers(items);
          setSectionCatalog(sections);
        } else {
          setUsers([]);
          setSectionCatalog([]);
        }
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento utenti GAIA");
      }
    }

    void loadPage();
  }, []);

  useEffect(() => {
    if (!successMessage && !error) {
      return;
    }

    setToast(
      successMessage
        ? { tone: "success", message: successMessage }
        : error
          ? { tone: "danger", message: error }
          : null,
    );
  }, [error, successMessage]);

  useEffect(() => {
    if (!toast) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setToast(null);
      setError(null);
      setSuccessMessage(null);
    }, 3500);

    return () => window.clearTimeout(timeoutId);
  }, [toast]);

  useEffect(() => {
    setShowPassword(false);

    if (!selectedUser) {
      setFormState(emptyFormState);
      setSectionSearchTerm("");
      setSectionOverrideOnly(false);
      return;
    }

    setFormState({
      username: selectedUser.username,
      email: selectedUser.email,
      password: "",
      role: selectedUser.role,
      isActive: selectedUser.is_active,
      sendInviteEmail: false,
      moduleAccessi: selectedUser.module_accessi,
      moduleRete: selectedUser.module_rete,
      moduleInventario: selectedUser.module_inventario,
      moduleCatasto: selectedUser.module_catasto,
      moduleUtenze: selectedUser.module_utenze,
      moduleOperazioni: selectedUser.module_operazioni,
      moduleRiordino: selectedUser.module_riordino,
      moduleRuolo: selectedUser.module_ruolo,
      modulePresenze: selectedUser.module_presenze,
    });
  }, [selectedUser]);

  useEffect(() => {
    if (!selectedUser) {
      setComponentModalModuleKey(null);
      return;
    }
  }, [selectedUser]);

  useEffect(() => {
    if (!isEditMode) {
      setComponentModalModuleKey(null);
    }
  }, [isEditMode]);

  useEffect(() => {
    if (!shouldScrollToSectionPermissions || !isEditMode) return;

    const id = window.requestAnimationFrame(() => {
      sectionPermissionsRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
      setShouldScrollToSectionPermissions(false);
    });

    return () => window.cancelAnimationFrame(id);
  }, [isEditMode, shouldScrollToSectionPermissions]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || !selectedUserId) {
      setPermissionsView(null);
      setSectionDraft({});
      return;
    }

    let cancelled = false;
    setPermissionsLoading(true);
    void getApplicationUserPermissions(token, selectedUserId)
      .then((response) => {
        if (!cancelled) {
          setPermissionsView(response);
          setSectionDraft(buildSectionDraftFromOverrides(response.overrides));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPermissionsView(null);
          setSectionDraft({});
        }
      })
      .finally(() => {
        if (!cancelled) {
          setPermissionsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedUserId]);

  const rows = useMemo<GaiaUserRow[]>(
    () =>
      users.map((user) => ({
        id: user.id,
        username: user.username,
        email: user.email,
        role: user.role,
        isActive: user.is_active,
        modulesLabel: formatModules(user),
        lastLoginAt: user.last_login_at,
        lastLoginIp: user.last_login_ip,
        loginCount: user.login_count,
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

  const activeUsersCount = useMemo(() => users.filter((user) => user.is_active).length, [users]);
  const adminUsersCount = useMemo(
    () => users.filter((user) => user.role === "admin" || user.role === "super_admin").length,
    [users],
  );
  const recentLoginUsersCount = useMemo(() => users.filter((user) => Boolean(user.last_login_at)).length, [users]);
  const selectedModules = useMemo(
    () => moduleOptions.filter((option) => formState[option.key]),
    [formState],
  );
  const sectionOverridesById = useMemo(
    () => new Map((permissionsView?.overrides ?? []).map((override) => [override.section_id, override])),
    [permissionsView],
  );
  const grantedSectionCount = permissionsView?.resolved.filter((item) => item.is_granted).length ?? 0;
  const deniedSectionCount = permissionsView?.resolved.filter((item) => !item.is_granted).length ?? 0;
  const effectiveSectionsPreview = useMemo(
    () => (permissionsView?.resolved ?? []).filter((item) => item.is_granted).slice(0, 8),
    [permissionsView],
  );
  const sectionOverridesPreview = useMemo(() => permissionsView?.overrides ?? [], [permissionsView]);
  const editableSections = useMemo(() => {
    const enabledModuleKeys = selectedModules.map((option) => option.moduleKey);
    if (formState.modulePresenze) {
      enabledModuleKeys.push("organigramma");
    }
    return buildEditableSectionCatalog({
      sectionCatalog,
      enabledModuleKeys,
      overriddenSectionIds: new Set(sectionOverridesById.keys()),
    });
  }, [formState.modulePresenze, sectionCatalog, sectionOverridesById, selectedModules]);
  const allCatalogSectionsByModule = useMemo(
    () => new Map(groupSectionsByModule(sectionCatalog)),
    [sectionCatalog],
  );
  const visibleCatalogSections = useMemo(
    () => filterEditableSections({
      sections: sectionCatalog,
      draft: sectionDraft,
      searchTerm: deferredSectionSearchTerm,
      overrideOnly: sectionOverrideOnly,
    }),
    [deferredSectionSearchTerm, sectionCatalog, sectionDraft, sectionOverrideOnly],
  );
  const visibleCatalogSectionsByModule = useMemo(
    () => new Map(groupSectionsByModule(visibleCatalogSections)),
    [visibleCatalogSections],
  );
  const canEditSectionOverrides = Boolean(
    currentUser
    && selectedUser
    && (currentUser.role === "super_admin" || selectedUser.role !== "super_admin")
    && !(currentUser.role === "admin" && (selectedUser.role === "admin" || selectedUser.role === "super_admin")),
  );
  const activeComponentModule = useMemo(
    () => moduleOptions.find((option) => option.moduleKey === componentModalModuleKey) ?? null,
    [componentModalModuleKey],
  );
  const activeComponentModuleSectionKeys = useMemo(
    () => (activeComponentModule ? getModuleSectionKeys(activeComponentModule.moduleKey) : []),
    [activeComponentModule],
  );
  const activeComponentModuleSections = useMemo(
    () => activeComponentModuleSectionKeys.flatMap((moduleKey) => allCatalogSectionsByModule.get(moduleKey) ?? []),
    [activeComponentModuleSectionKeys, allCatalogSectionsByModule],
  );
  const visibleActiveComponentModuleSections = useMemo(
    () => activeComponentModuleSectionKeys.flatMap((moduleKey) => visibleCatalogSectionsByModule.get(moduleKey) ?? []),
    [activeComponentModuleSectionKeys, visibleCatalogSectionsByModule],
  );
  const hasUnsavedActiveComponentChanges = useMemo(
    () => activeComponentModuleSections.length > 0 && hasUnsavedSectionDraftChanges({
      sectionIds: activeComponentModuleSections.map((section) => section.id),
      draft: sectionDraft,
      overrides: permissionsView?.overrides ?? [],
    }),
    [activeComponentModuleSections, permissionsView?.overrides, sectionDraft],
  );

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
            {getRoleLabel(row.original.role)}
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
        cell: ({ row }) => (
          <div className="space-y-1">
            <div className="flex flex-wrap gap-1.5">
              {row.original.modulesLabel === "Nessun modulo" ? (
                <Badge variant="neutral">Nessun modulo</Badge>
              ) : (
                row.original.modulesLabel.split(", ").map((moduleLabel) => (
                  <Badge key={moduleLabel} variant="neutral">
                    {moduleLabel}
                  </Badge>
                ))
              )}
            </div>
            <p className="text-xs text-gray-400">{countEnabledModules(row.original.item)} moduli abilitati</p>
          </div>
        ),
      },
      {
        header: "Ultimo accesso",
        accessorKey: "lastLoginAt",
        cell: ({ row }) => (
          <div className="text-sm text-gray-600">
            <p>{formatDateTimeLabel(row.original.lastLoginAt)}</p>
            <p className="text-xs text-gray-400">{row.original.lastLoginIp || "IP n/d"}</p>
          </div>
        ),
      },
      {
        header: "Accessi",
        accessorKey: "loginCount",
        cell: ({ row }) => <span className="text-sm font-medium text-gray-700">{row.original.loginCount}</span>,
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

  function getModuleSectionKeys(moduleKey: string): string[] {
    return moduleKey === "presenze" ? ["presenze", "organigramma"] : [moduleKey];
  }

  async function reloadUsers() {
    const token = getStoredAccessToken();
    if (!token) return;

    const items = await listAllApplicationUsers(token);
    setUsers(items);
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
          module_utenze: formState.moduleUtenze,
          module_operazioni: formState.moduleOperazioni,
          module_riordino: formState.moduleRiordino,
          module_ruolo: formState.moduleRuolo,
          module_presenze: formState.modulePresenze,
        });
        setSuccessMessage(`Utente ${selectedUser.username} aggiornato.`);
      } else {
        const createdUser = await createApplicationUser(token, {
          username: formState.username,
          email: formState.email,
          password: formState.password.trim().length > 0 ? formState.password : undefined,
          role: formState.role,
          is_active: formState.isActive,
          module_accessi: formState.moduleAccessi,
          module_rete: formState.moduleRete,
          module_inventario: formState.moduleInventario,
          module_catasto: formState.moduleCatasto,
          module_utenze: formState.moduleUtenze,
          module_operazioni: formState.moduleOperazioni,
          module_riordino: formState.moduleRiordino,
          module_ruolo: formState.moduleRuolo,
          module_presenze: formState.modulePresenze,
        });
        if (formState.sendInviteEmail) {
          await sendApplicationUserInvite(token, createdUser.id);
        }
        setSelectedUserId(createdUser.id);
        setShouldScrollToSectionPermissions(true);
        setSuccessMessage(
          formState.sendInviteEmail
            ? `Utente ${createdUser.username} creato e mail di attivazione inviata.`
            : `Utente ${createdUser.username} creato. Ora puoi configurare anche le singole sezioni del modulo.`,
        );
      }

      await reloadUsers();
      if (!isEditMode) {
        setShowPassword(false);
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

  async function handleSendInvite() {
    const token = getStoredAccessToken();
    if (!token || !selectedUser) return;

    setIsSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await sendApplicationUserInvite(token, selectedUser.id);
      setSuccessMessage(`Mail di accesso inviata a ${response.email}.`);
    } catch (inviteError) {
      setError(inviteError instanceof Error ? inviteError.message : "Invio mail non riuscito");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSaveSectionOverrides() {
    const token = getStoredAccessToken();
    if (!token || !selectedUser || !canEditSectionOverrides) return;

    setSectionSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const { toDelete, toUpsert } = computeSectionOverrideChanges(sectionDraft, permissionsView?.overrides ?? []);

      await Promise.all(toDelete.map((sectionId) => deleteApplicationUserPermissionOverride(token, selectedUser.id, sectionId)));
      const nextPermissions = toUpsert.length
        ? await updateApplicationUserPermissions(token, selectedUser.id, toUpsert)
        : await getApplicationUserPermissions(token, selectedUser.id);

      setPermissionsView(nextPermissions);
      setSectionDraft(buildSectionDraftFromOverrides(nextPermissions.overrides));
      setSuccessMessage(`Permessi di sezione aggiornati per ${selectedUser.username}.`);
    } catch (sectionError) {
      setError(sectionError instanceof Error ? sectionError.message : "Aggiornamento permessi sezione non riuscito");
    } finally {
      setSectionSaving(false);
    }
  }

  function renderUserEditor(className?: string) {
    return (
      <article className={cn("panel-card", className)}>
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
              Chiudi
            </button>
          ) : null}
        </div>

        {isEditMode && selectedUser ? (
          <div className="mb-4 rounded-2xl border border-[#dfe7dc] bg-[#f8fbf8] p-4">
            <div className="flex items-center gap-3">
              <Avatar label={selectedUser.username} />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-[#112418]">{selectedUser.username}</p>
                <p className="truncate text-xs text-gray-500">{selectedUser.email}</p>
              </div>
              <div className="ml-auto flex flex-wrap gap-2">
                <Badge variant={selectedUser.is_active ? "success" : "neutral"}>{selectedUser.is_active ? "Attivo" : "Inattivo"}</Badge>
                <Badge variant={selectedUser.role === "super_admin" ? "danger" : selectedUser.role === "admin" ? "warning" : "info"}>
                  {getRoleLabel(selectedUser.role)}
                </Badge>
              </div>
            </div>
          </div>
        ) : null}

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
            <div className="relative mt-1">
              <input
                className="form-control pr-10"
                type={showPassword ? "text" : "password"}
                value={formState.password}
                onChange={(event) => updateFormState("password", event.target.value)}
                placeholder={isEditMode ? "Lascia vuoto per non cambiarla" : "Minimo 8 caratteri"}
              />
              <button
                type="button"
                onClick={() => setShowPassword((current) => !current)}
                aria-label={showPassword ? "Nascondi password" : "Mostra password"}
                className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 transition hover:text-[#1D4E35]"
              >
                {showPassword ? "visibility_off" : "visibility"}
              </button>
            </div>
            {!isEditMode ? (
              <p className="mt-2 text-xs text-gray-500">
                Se lasci vuoto e invii la mail di attivazione, l&apos;utente imposterà la password dal link ricevuto.
              </p>
            ) : null}
          </label>

          {!isEditMode ? (
            <label className="flex items-start gap-3 rounded-2xl border border-[#dfe7dc] bg-[#f8fbf8] p-4 text-sm text-gray-700">
              <input
                className="mt-1"
                type="checkbox"
                checked={formState.sendInviteEmail}
                onChange={(event) => updateFormState("sendInviteEmail", event.target.checked)}
              />
              <span>
                Invia mail di attivazione
                <span className="mt-1 block text-xs text-gray-500">
                  L&apos;utente potrà impostare la password dal link e usare anche Google se l&apos;email coincide.
                </span>
              </span>
            </label>
          ) : null}

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

          {isEditMode && selectedUser ? (
            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-sm font-medium text-gray-800">Storico accessi</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-3 text-sm text-gray-600">
                <div>
                  <p className="text-xs uppercase tracking-[0.14em] text-gray-400">Ultimo accesso</p>
                  <p className="mt-1 font-medium text-gray-900">{formatDateTimeLabel(selectedUser.last_login_at)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.14em] text-gray-400">IP ultimo accesso</p>
                  <p className="mt-1 font-medium text-gray-900">{selectedUser.last_login_ip || "n/d"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.14em] text-gray-400">Numero accessi</p>
                  <p className="mt-1 font-medium text-gray-900">{selectedUser.login_count}</p>
                </div>
              </div>
              <div className="mt-4">
                <button className="btn-secondary" type="button" onClick={() => void handleSendInvite()} disabled={isSubmitting}>
                  Invia mail di accesso
                </button>
              </div>
            </div>
          ) : null}

          {isEditMode && selectedUser ? (
            <div className="rounded-2xl border border-[#dfe7dc] bg-[#f8fbf8] p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-800">GaTe Mobile</p>
                  <p className="mt-1 text-xs leading-5 text-gray-500">
                    Stato readonly ereditato dall&apos;operatore collegato in Operazioni. La modifica resta nel dominio Operazioni.
                  </p>
                </div>
                {selectedUser.gate_mobile_console ? (
                  <Badge variant={selectedUser.gate_mobile_console.enabled ? "success" : "neutral"}>
                    {selectedUser.gate_mobile_console.enabled ? "Enabled" : "Disabled"}
                  </Badge>
                ) : (
                  <Badge variant="neutral">Non collegato</Badge>
                )}
              </div>

              {selectedUser.gate_mobile_console ? (
                <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="text-sm text-gray-600">
                    <p>
                      <span className="font-medium text-gray-900">Ruolo console:</span>{" "}
                      {formatGateMobileConsoleRoleLabel(selectedUser.gate_mobile_console.role)}
                    </p>
                    <p className="mt-1">
                      <span className="font-medium text-gray-900">Operatore linked:</span>{" "}
                      {selectedUser.gate_mobile_console.operator_id}
                    </p>
                  </div>
                  <a
                    className="btn-secondary text-center"
                    href={`/operazioni/operatori?operatorId=${encodeURIComponent(selectedUser.gate_mobile_console.operator_id)}&from=gaia-users`}
                  >
                    Gestisci in Operazioni
                  </a>
                </div>
              ) : (
                <p className="mt-4 text-sm text-gray-500">
                  Nessun operatore Operazioni collegato a questo utente GAIA.
                </p>
              )}
            </div>
          ) : null}

          {isEditMode ? (
            <div ref={sectionPermissionsRef} className="rounded-2xl border border-[#dfe7dc] bg-[#f8fbf8] p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-800">Sezioni abilitate</p>
                  <p className="mt-1 text-xs leading-5 text-gray-500">
                    Sì: GAIA supporta già permessi più granulari del solo modulo. Questa pagina oggi modifica i moduli;
                    il dettaglio sotto mostra le sezioni effettivamente concesse all&apos;utente selezionato.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge variant="success">{grantedSectionCount} sezioni abilitate</Badge>
                  <Badge variant="neutral">{deniedSectionCount} non abilitate</Badge>
                </div>
              </div>

              {permissionsLoading ? (
                <p className="mt-4 text-sm text-gray-500">Caricamento permessi sezione...</p>
              ) : permissionsView ? (
                <>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {effectiveSectionsPreview.length ? (
                      effectiveSectionsPreview.map((section) => (
                        <Badge key={section.section_key} variant={section.source === "user_override" ? "warning" : "info"}>
                          {section.section_label}
                        </Badge>
                      ))
                    ) : (
                      <Badge variant="neutral">Nessuna sezione concessa</Badge>
                    )}
                  </div>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2 text-xs text-gray-500">
                    <div className="rounded-2xl border border-white bg-white px-3 py-3 shadow-sm">
                      <p className="font-semibold uppercase tracking-[0.14em] text-gray-400">Ruolo base</p>
                      <p className="mt-2 text-sm font-medium text-gray-800">{getRoleLabel(permissionsView.role)}</p>
                    </div>
                    <div className="rounded-2xl border border-white bg-white px-3 py-3 shadow-sm">
                      <p className="font-semibold uppercase tracking-[0.14em] text-gray-400">Override utente</p>
                      <p className="mt-2 text-sm font-medium text-gray-800">{sectionOverridesPreview.length}</p>
                    </div>
                  </div>
                </>
              ) : (
                <p className="mt-4 text-sm text-gray-500">Anteprima permessi sezione non disponibile.</p>
              )}
            </div>
          ) : (
            <div className="rounded-2xl border border-[#dfe7dc] bg-[#f8fbf8] p-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-800">Permessi per componente</p>
                  <p className="mt-1 text-xs leading-5 text-gray-500">
                    Qui sopra stai scegliendo solo i moduli principali. I singoli componenti o sezioni del modulo
                    si configurano dopo aver creato l&apos;utente, quando compare il pannello “Sezioni abilitate”.
                  </p>
                </div>
                <Badge variant="info">Disponibile dopo la creazione</Badge>
              </div>
            </div>
          )}

          <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-sm font-medium text-gray-800">Moduli abilitati</p>
                <p className="mt-1 text-xs text-gray-500">
                  Seleziona i moduli necessari. Per ogni modulo puoi aprire i componenti e definire i permessi di dettaglio.
                </p>
              </div>
              <Badge variant="neutral">{selectedModules.length} moduli selezionati</Badge>
            </div>

            {isEditMode ? (
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-500">
                <Badge variant="neutral">{editableSections.length} componenti disponibili</Badge>
                <Badge variant={canEditSectionOverrides ? "warning" : "neutral"}>
                  {canEditSectionOverrides ? "Permessi modificabili" : "Sola lettura"}
                </Badge>
              </div>
            ) : null}

            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {moduleOptions.map((option) => {
                const moduleSectionKeys = getModuleSectionKeys(option.moduleKey);
                const moduleSections = moduleSectionKeys
                  .flatMap((moduleKey) => allCatalogSectionsByModule.get(moduleKey) ?? []);
                const enabled = formState[option.key];
                const overriddenSections = moduleSections.filter((section) => sectionOverridesById.has(section.id)).length;
                return (
                  <div
                    key={option.key}
                    className={cn(
                      "rounded-[22px] border px-3 py-3 shadow-sm transition",
                      enabled
                        ? "border-[#bfe5d6] bg-[linear-gradient(180deg,#ffffff,#f7fcf8)] shadow-[0_14px_32px_rgba(29,78,53,0.08)]"
                        : "border-white bg-white hover:border-[#dfe7dc]",
                    )}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        className="mt-1"
                        type="checkbox"
                        checked={enabled}
                        onChange={(event) => {
                          updateFormState(option.key, event.target.checked);
                        }}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="block text-sm font-medium text-gray-800">{option.label}</span>
                              <Badge variant={enabled ? "success" : "neutral"}>
                                {enabled ? "Abilitato" : "Disattivato"}
                              </Badge>
                            </div>
                            <span className="mt-1 block text-xs leading-5 text-gray-500">{option.description}</span>
                            <div className="mt-2 flex flex-wrap gap-2">
                              <Badge variant="neutral">
                                {moduleSections.length} componenti
                              </Badge>
                              {isEditMode && overriddenSections ? (
                                <Badge variant="warning">{overriddenSections} override</Badge>
                              ) : null}
                            </div>
                          </div>
                          {moduleSections.length ? (
                            <button
                              type="button"
                              className={cn(
                                "rounded-full border px-3 py-1 text-[11px] font-semibold transition",
                                "border-[#d6dfef] bg-[#f8fbff] text-[#2f5da8] hover:bg-[#eef3fb]",
                              )}
                              onClick={() => setComponentModalModuleKey(option.moduleKey)}
                            >
                              {`Apri componenti (${moduleSections.length})`}
                            </button>
                          ) : null}
                        </div>

                        {!isEditMode && enabled ? (
                          <p className="mt-3 rounded-xl border border-[#e6ebe5] bg-[#f8fbf8] px-3 py-2 text-xs leading-5 text-gray-500">
                            I componenti di dettaglio di questo modulo si configurano dopo la creazione dell&apos;utente.
                          </p>
                        ) : null}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 border-t border-gray-200 pt-4">
              <label className="flex items-center gap-3 text-sm font-medium text-gray-700">
                <input type="checkbox" checked={formState.isActive} onChange={(event) => updateFormState("isActive", event.target.checked)} />
                Account attivo
              </label>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button className="btn-primary" disabled={isSubmitting} onClick={() => void handleSubmit()} type="button">
              {isSubmitting ? "Salvataggio..." : isEditMode ? "Salva modifiche" : "Crea e apri permessi sezione"}
            </button>
            {isEditMode && currentUser?.role === "super_admin" && selectedUser && selectedUser.id !== currentUser.id ? (
              <button className="btn-secondary" disabled={isSubmitting} onClick={() => void handleDelete()} type="button">
                Elimina utente
              </button>
            ) : null}
          </div>
        </div>
      </article>
    );
  }

  return (
    <ProtectedPage
      title="Utenti GAIA"
      description="Gestione degli utenti applicativi di GAIA, con ruoli, stato account e moduli abilitati."
      breadcrumb="Amministrazione"
      requiredModule="accessi"
      requiredRoles={["admin", "super_admin"]}
    >
      {toast ? (
        <div className="pointer-events-none fixed inset-x-0 top-1/2 z-[80] flex -translate-y-1/2 justify-center px-4">
          <div
            className={cn(
              "pointer-events-auto w-full max-w-xl rounded-2xl border px-5 py-4 text-sm shadow-[0_24px_80px_rgba(15,23,42,0.22)] backdrop-blur-sm",
              toast.tone === "success"
                ? "border-emerald-200 bg-emerald-50/95 text-emerald-800"
                : "border-red-200 bg-red-50/95 text-red-800",
            )}
          >
            <div className="flex items-start gap-3">
              <span className="material-symbols-outlined mt-0.5 text-[20px]">
                {toast.tone === "success" ? "check_circle" : "error"}
              </span>
              <p className="flex-1 text-sm font-medium">{toast.message}</p>
              <button
                type="button"
                onClick={() => {
                  setToast(null);
                  setError(null);
                  setSuccessMessage(null);
                }}
                className="material-symbols-outlined text-base text-current/70 transition hover:text-current"
                aria-label="Chiudi notifica"
              >
                close
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <section className="rounded-[28px] border border-[#dfe7dc] bg-[linear-gradient(135deg,#f7fbf8_0%,#ffffff_45%,#f3f7f5_100%)] p-6 shadow-[0_20px_45px_rgba(15,23,42,0.06)]">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#5f6d61]">Accessi · Amministrazione</p>
            <h2 className="mt-2 font-serif text-[28px] font-semibold leading-tight text-[#112418]">Directory utenti applicativi</h2>
            <p className="mt-2 text-sm leading-6 text-[#5f6d61]">
              Qui gestisci account, ruoli e moduli abilitati. L&apos;organigramma operativo ora vive in
              {" "}
              <a className="font-semibold text-[#1D4E35] underline underline-offset-2" href="/presenze/organigramma">Giornaliere / Organigramma</a>
              {" "}
              per evitare duplicazioni tra aree amministrative.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-[#dfe7dc] bg-white/80 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Utenti filtrati</p>
              <p className="mt-2 text-2xl font-semibold text-[#112418]">{filteredRows.length}</p>
            </div>
            <div className="rounded-2xl border border-[#dfe7dc] bg-white/80 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Attivi</p>
              <p className="mt-2 text-2xl font-semibold text-[#112418]">{activeUsersCount}</p>
            </div>
            <div className="rounded-2xl border border-[#dfe7dc] bg-white/80 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Admin</p>
              <p className="mt-2 text-2xl font-semibold text-[#112418]">{adminUsersCount}</p>
            </div>
          </div>
        </div>
      </section>

      <div className="surface-grid">
        <MetricCard label="Utenti GAIA" value={users.length} sub="Account applicativi censiti" />
        <MetricCard label="Attivi" value={activeUsersCount} sub="Account abilitati al login" variant="success" />
        <MetricCard label="Accessi registrati" value={users.reduce((total, user) => total + user.login_count, 0)} sub="Login applicativi storicizzati" />
        <MetricCard label="Admin" value={adminUsersCount} sub="Profili amministrativi" />
        <MetricCard label="Accessi recenti" value={recentLoginUsersCount} sub="Utenti che hanno già effettuato login" variant="info" />
        <MetricCard label="NAS Control" value={users.filter((user) => user.module_accessi).length} sub="Utenti con modulo NAS abilitato" />
        <MetricCard label="Catasto" value={users.filter((user) => user.module_catasto).length} sub="Utenti con modulo Catasto abilitato" />
        <MetricCard label="Utenze" value={users.filter((user) => user.module_utenze).length} sub="Utenti con modulo Utenze abilitato" />
        <MetricCard label="Riordino" value={users.filter((user) => user.module_riordino).length} sub="Utenti con modulo Riordino abilitato" />
        <MetricCard label="Ruolo" value={users.filter((user) => user.module_ruolo).length} sub="Utenti con modulo Ruolo abilitato" />
        <MetricCard label="Giornaliere" value={users.filter((user) => user.module_presenze).length} sub="Utenti con modulo Giornaliere abilitato" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <article className="panel-card">
          <div className="mb-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(32rem,40rem)] xl:items-start">
            <div className="min-w-0">
              <p className="section-title">Directory utenti applicativi</p>
              <p className="max-w-xl text-sm leading-6 text-[#5f6d61]">
                Seleziona un account per modificarlo oppure filtra la directory per ruolo, stato e testo.
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                <Badge variant="neutral">{filteredRows.length} risultati</Badge>
                {roleFilter !== "all" ? <Badge variant="info">Ruolo: {getRoleLabel(roleFilter)}</Badge> : null}
                {statusFilter !== "all" ? <Badge variant="info">Stato: {statusFilter === "active" ? "attivi" : "inattivi"}</Badge> : null}
                {deferredSearchTerm.trim() ? <Badge variant="warning">Ricerca: {deferredSearchTerm.trim()}</Badge> : null}
              </div>
            </div>
            <div className="grid gap-3 rounded-2xl border border-[#e6ebe5] bg-[#fbfcfa] p-3 sm:grid-cols-[minmax(0,1.4fr)_minmax(10rem,0.8fr)_minmax(10rem,0.8fr)]">
              <label className="text-xs font-medium uppercase tracking-[0.14em] text-gray-400">
                Cerca
                <input
                  className="form-control mt-1 w-full"
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

        {isEditMode ? (
          <article className="panel-card border-dashed bg-[#fbfcfb]">
            <p className="section-title">Nuovo utente GAIA</p>
            <p className="section-copy">
              La modifica dell&apos;utente selezionato si apre in una modal. Chiudi la modal per tornare alla creazione di un nuovo account.
            </p>
          </article>
        ) : renderUserEditor()}
      </div>
      {isEditMode ? (
        <UserEditorModal onClose={() => {
          setSelectedUserId(null);
          setFormState(emptyFormState);
          setSuccessMessage(null);
        }}>
          {renderUserEditor("max-h-[88vh] overflow-y-auto")}
        </UserEditorModal>
      ) : null}
      {isEditMode && activeComponentModule ? (
        <ModuleComponentsModal
          canEditSectionOverrides={canEditSectionOverrides}
          enabled={formState[activeComponentModule.key]}
          moduleLabel={activeComponentModule.label}
          moduleDescription={activeComponentModule.description}
          onClose={() => setComponentModalModuleKey(null)}
          onSave={() => void handleSaveSectionOverrides()}
          overrideOnly={sectionOverrideOnly}
          permissionsLoading={permissionsLoading}
          resolvedPermissions={permissionsView?.resolved ?? []}
          saving={sectionSaving}
          searchTerm={sectionSearchTerm}
          sections={activeComponentModuleSections}
          sectionDraft={sectionDraft}
          sectionOverridesById={sectionOverridesById}
          showUnsavedChanges={hasUnsavedActiveComponentChanges}
          setOverrideOnly={setSectionOverrideOnly}
          setSearchTerm={setSectionSearchTerm}
          setSectionDraft={setSectionDraft}
          visibleSections={visibleActiveComponentModuleSections}
        />
      ) : null}
    </ProtectedPage>
  );
}

function UserEditorModal({
  children,
  onClose,
}: {
  children: React.ReactNode;
  onClose: () => void;
}) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/45 px-3 py-5 backdrop-blur-sm xl:px-5">
      <button aria-label="Chiudi modifica utente" className="absolute inset-0" type="button" onClick={onClose} />
      <div className="relative z-10 max-h-[95vh] w-full max-w-[min(1600px,98vw)] overflow-y-auto">
        {children}
      </div>
    </div>
  );
}

type ModuleComponentsModalProps = {
  canEditSectionOverrides: boolean;
  enabled: boolean;
  moduleLabel: string;
  moduleDescription: string;
  onClose: () => void;
  onSave: () => void;
  overrideOnly: boolean;
  permissionsLoading: boolean;
  resolvedPermissions: UserPermissionsAdminView["resolved"];
  saving: boolean;
  searchTerm: string;
  sections: SectionResponse[];
  sectionDraft: Record<number, SectionOverrideValue>;
  sectionOverridesById: Map<number, UserPermissionsAdminView["overrides"][number]>;
  showUnsavedChanges: boolean;
  setOverrideOnly: (value: boolean) => void;
  setSearchTerm: (value: string) => void;
  setSectionDraft: React.Dispatch<React.SetStateAction<Record<number, SectionOverrideValue>>>;
  visibleSections: SectionResponse[];
};

function ModuleComponentsModal({
  canEditSectionOverrides,
  enabled,
  moduleLabel,
  moduleDescription,
  onClose,
  onSave,
  overrideOnly,
  permissionsLoading,
  resolvedPermissions,
  saving,
  searchTerm,
  sections,
  sectionDraft,
  sectionOverridesById,
  showUnsavedChanges,
  setOverrideOnly,
  setSearchTerm,
  setSectionDraft,
  visibleSections,
}: ModuleComponentsModalProps) {
  const requestClose = useCallback(() => {
    onClose();
  }, [onClose]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        requestClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [requestClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0f1720]/40 px-4 py-8">
      <button aria-label="Chiudi componenti modulo" className="absolute inset-0" type="button" onClick={requestClose} />
      <div className="relative z-10 flex max-h-[88vh] w-full max-w-5xl flex-col overflow-hidden rounded-[28px] border border-[#dfe7dc] bg-white shadow-[0_32px_80px_rgba(15,23,32,0.22)]">
        <div className="border-b border-[#e7eee5] bg-[linear-gradient(180deg,#f8fbf8,#ffffff)] px-6 py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Componenti modulo</p>
              <h3 className="mt-1 text-2xl font-semibold text-[#1D4E35]">{moduleLabel}</h3>
              <p className="mt-2 max-w-2xl text-sm text-gray-600">{moduleDescription}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant={enabled ? "success" : "neutral"}>
                {enabled ? "Modulo abilitato" : "Modulo disattivato"}
              </Badge>
              <Badge variant="neutral">{sections.length} componenti</Badge>
              {showUnsavedChanges ? <Badge variant="warning">Modifiche non salvate</Badge> : null}
              <Badge variant={canEditSectionOverrides ? "warning" : "neutral"}>
                {canEditSectionOverrides ? "Permessi modificabili" : "Sola lettura"}
              </Badge>
              <button className="btn-secondary" type="button" onClick={requestClose}>
                Chiudi
              </button>
              <button
                className="btn-primary"
                type="button"
                disabled={!canEditSectionOverrides || !showUnsavedChanges || saving || permissionsLoading}
                onClick={onSave}
              >
                {saving ? "Salvataggio..." : "Salva"}
              </button>
            </div>
          </div>

          <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <label className="text-xs font-medium uppercase tracking-[0.14em] text-gray-400">
              Cerca componente
              <input
                className="form-control mt-1"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Label, chiave o modulo"
              />
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-gray-100 bg-white px-3 py-3 text-sm font-medium text-gray-700">
              <input
                type="checkbox"
                checked={overrideOnly}
                onChange={(event) => setOverrideOnly(event.target.checked)}
              />
              Mostra solo override
            </label>
          </div>

          <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-500">
            <Badge variant="neutral">{visibleSections.length} componenti visibili</Badge>
            {overrideOnly ? <Badge variant="warning">Solo override</Badge> : null}
            {searchTerm.trim() ? <Badge variant="info">Ricerca: {searchTerm.trim()}</Badge> : null}
            {!enabled ? <Badge variant="neutral">Attiva il modulo per rendere effettivi i permessi</Badge> : null}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          {permissionsLoading ? (
            <p className="text-sm text-gray-500">Caricamento permessi in corso...</p>
          ) : !visibleSections.length ? (
            <div className="rounded-2xl border border-dashed border-[#d9e3d7] bg-[#fbfcfb] px-4 py-5 text-sm text-gray-500">
              Nessun componente visibile con i filtri attivi per questo modulo.
            </div>
          ) : (
            <div className="grid gap-3 lg:grid-cols-2">
              {visibleSections.map((section) => {
                const currentValue = sectionDraft[section.id] ?? "inherit";
                const resolved = resolvedPermissions.find((item) => item.section_key === section.key);
                return (
                  <div
                    key={section.id}
                    className={cn(
                      "rounded-2xl border px-4 py-4",
                      sectionOverridesById.has(section.id)
                        ? "border-[#f1d7a8] bg-[#fffaf1]"
                        : "border-gray-100 bg-gray-50",
                    )}
                  >
                    <div className="flex flex-col gap-3">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-800">{section.label}</p>
                        <p className="mt-1 text-xs leading-5 text-gray-500">{section.description || section.key}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <Badge variant={resolved?.is_granted ? "success" : "neutral"}>
                            {resolved?.is_granted ? "Effettiva: concessa" : "Effettiva: non concessa"}
                          </Badge>
                          {sectionOverridesById.has(section.id) ? (
                            <Badge variant="warning">Override utente</Badge>
                          ) : (
                            <Badge variant="info">Ereditata da ruolo</Badge>
                          )}
                        </div>
                      </div>
                      <label className="text-xs font-medium uppercase tracking-[0.14em] text-gray-400">
                        Permesso
                        <select
                          className="form-control mt-1"
                          value={currentValue}
                          disabled={!canEditSectionOverrides || saving || !enabled}
                          onChange={(event) =>
                            setSectionDraft((current) => ({
                              ...current,
                              [section.id]: event.target.value as SectionOverrideValue,
                            }))
                          }
                        >
                          <option value="inherit">Ereditato</option>
                          <option value="grant">Consenti</option>
                          <option value="deny">Nega</option>
                        </select>
                      </label>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="border-t border-[#e7eee5] bg-[#fcfdfc] px-6 py-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-gray-500">
              {showUnsavedChanges
                ? "Ci sono modifiche locali non ancora salvate."
                : "Nessuna modifica locale in sospeso."}
            </p>
            <div className="flex flex-wrap gap-3">
              <button className="btn-secondary" type="button" onClick={requestClose}>
                Chiudi
              </button>
              <button
                className="btn-secondary"
                disabled={saving || permissionsLoading}
                onClick={() => setSectionDraft(buildSectionDraftFromOverrides(Array.from(sectionOverridesById.values())))}
                type="button"
              >
                Ripristina draft
              </button>
              <button
                className="btn-primary"
                type="button"
                disabled={!canEditSectionOverrides || !showUnsavedChanges || saving || permissionsLoading}
                onClick={onSave}
              >
                {saving ? "Salvataggio..." : "Salva"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
