"use client";

import {
  type ChangeEvent,
  type Dispatch,
  type SetStateAction,
  useEffect,
  useState,
} from "react";

import { listAllApplicationUsers } from "@/lib/api";
import {
  listGisLayerPermissions,
  revokeGisLayerPermission,
  upsertGisLayerPermission,
} from "@/lib/api/gis";
import type { ApplicationUser } from "@/types/api";
import type {
  GisCatalogAccessLevel,
  GisCatalogLayer,
  GisCatalogLayerPermission,
} from "@/types/gis";

import { ConfirmationDialog } from "../catalogo/catalog-dialog";

type PrincipalType = "role" | "user";

const applicationRoles = [
  ["viewer", "Consultazione"],
  ["operator", "Operatore"],
  ["reviewer", "Revisore"],
  ["hr_manager", "Responsabile personale"],
  ["admin", "Amministratore"],
  ["super_admin", "Super amministratore"],
] as const;

const accessLevels: Array<[GisCatalogAccessLevel, string]> = [
  ["viewer", "Può consultare"],
  ["annotator", "Può consultare e aggiungere note"],
  ["editor", "Può proporre modifiche"],
  ["approver", "Può approvare modifiche"],
  ["admin", "Può amministrare la mappa"],
];

const roleLabels = Object.fromEntries(applicationRoles);
const accessLabels = Object.fromEntries(accessLevels);

function userLabel(user: ApplicationUser): string {
  const identity = user.full_name?.trim() || user.username;
  return `${identity} · ${user.email}`;
}

function principalLabel(
  permission: GisCatalogLayerPermission,
  users: ApplicationUser[],
): string {
  if (permission.principal_type === "role") {
    return `Ruolo: ${roleLabels[permission.principal_key] ?? permission.principal_key}`;
  }
  const user = users.find((item) => String(item.id) === permission.principal_key);
  return user ? `Utente: ${userLabel(user)}` : `Utente non più disponibile (${permission.principal_key})`;
}

function errorText(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function GisPermissionsPanel({
  token,
  layers,
}: {
  token: string;
  layers: GisCatalogLayer[];
}) {
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const context = usePermissionContext(token, layers, setError);
  const permissionState = useLayerPermissions(token, context.layerId, setError);

  return (
    <section className="rounded-[28px] border border-[#d9dfd6] bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#526a59]">Accessi alle mappe</p>
      <h3 className="mt-2 text-xl font-semibold text-gray-950">Chi può consultare o modificare</h3>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-600">
        Scegli una persona per nome oppure assegna lo stesso permesso a un ruolo. Gli identificativi tecnici non devono essere inseriti manualmente.
      </p>
      {notice ? <p className="mt-4 rounded-2xl border border-[#bcd6c2] bg-[#edf8ef] px-4 py-3 text-sm font-semibold text-[#1D4E35]" role="status" aria-live="polite">{notice}</p> : null}
      {error ? <p className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700" role="alert">{error}</p> : null}
      {context.manageableLayers.length === 0 ? (
        <p className="mt-4 text-sm text-gray-600">Non ci sono mappe amministrabili con questa utenza.</p>
      ) : (
        <>
          <PermissionEditor
            token={token}
            layerSelection={context}
            users={context.selectableUsers}
            onReload={permissionState.setPermissions}
            onError={setError}
            onNotice={setNotice}
          />
          <PermissionList
            token={token}
            users={context.users}
            permissions={permissionState.permissions}
            loading={permissionState.loading}
            error={error}
            onRevoked={permissionState.removePermission}
            onError={setError}
            onNotice={setNotice}
          />
        </>
      )}
    </section>
  );
}

type MessageSetter = Dispatch<SetStateAction<string | null>>;

function usePermissionContext(token: string, layers: GisCatalogLayer[], setError: MessageSetter) {
  const manageableLayers = layers.filter((layer) => layer.can_manage);
  const [layerId, setLayerId] = useState("");
  const [users, setUsers] = useState<ApplicationUser[]>([]);

  useEffect(() => {
    const firstLayer = layers.find((layer) => layer.can_manage);
    setLayerId((current) =>
      layers.some((layer) => layer.can_manage && layer.id === current)
        ? current
        : (firstLayer?.id ?? ""),
    );
  }, [layers]);

  useEffect(() => {
    let cancelled = false;
    void listAllApplicationUsers(token)
      .then((items) => {
        if (!cancelled) setUsers(items);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(errorText(loadError, "Elenco utenti non disponibile"));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [setError, token]);

  return {
    manageableLayers,
    layerId,
    setLayerId,
    selectedLayer: manageableLayers.find((layer) => layer.id === layerId) ?? null,
    users,
    selectableUsers: users.filter((user) => user.is_active && user.module_gis),
  };
}

function useLayerPermissions(token: string, layerId: string, setError: MessageSetter) {
  const [permissions, setPermissions] = useState<GisCatalogLayerPermission[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!layerId) {
      setPermissions([]);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    void listGisLayerPermissions(token, layerId)
      .then((items) => {
        if (!cancelled) setPermissions(items);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setPermissions([]);
          setError(errorText(loadError, "Permessi non disponibili"));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [layerId, setError, token]);

  return {
    permissions,
    loading,
    setPermissions,
    removePermission(permissionId: string) {
      setPermissions((items) => items.filter((item) => item.id !== permissionId));
    },
  };
}

type LayerSelection = ReturnType<typeof usePermissionContext>;

async function savePermission({
  token,
  layer,
  principalType,
  principalKey,
  accessLevel,
  onBusy,
  onReload,
  onError,
  onNotice,
}: {
  token: string;
  layer: GisCatalogLayer | null;
  principalType: PrincipalType;
  principalKey: string;
  accessLevel: GisCatalogAccessLevel;
  onBusy: (busy: boolean) => void;
  onReload: Dispatch<SetStateAction<GisCatalogLayerPermission[]>>;
  onError: MessageSetter;
  onNotice: MessageSetter;
}) {
  if (!layer || !principalKey) {
    onError("Scegli una mappa e una persona o un ruolo.");
    return;
  }
  onBusy(true);
  onError(null);
  try {
    await upsertGisLayerPermission(token, layer.id, { principalType, principalKey, accessLevel });
    onReload(await listGisLayerPermissions(token, layer.id));
    onNotice(`Permesso salvato per ${layer.title}.`);
  } catch (saveError) {
    onError(errorText(saveError, "Salvataggio permesso non riuscito"));
  } finally {
    onBusy(false);
  }
}

function usePermissionEditor(users: ApplicationUser[]) {
  const [principalType, setPrincipalType] = useState<PrincipalType>("role");
  const [principalKey, setPrincipalKey] = useState("viewer");
  const [accessLevel, setAccessLevel] = useState<GisCatalogAccessLevel>("viewer");
  function changePrincipalType(nextType: PrincipalType) {
    setPrincipalType(nextType);
    setPrincipalKey(nextType === "role" ? "viewer" : String(users[0]?.id ?? ""));
  }
  function changePrincipalKey(event: ChangeEvent<HTMLSelectElement>) {
    setPrincipalKey(event.target.value);
  }
  return {
    principalType,
    principalKey,
    accessLevel,
    setAccessLevel,
    changePrincipalType,
    changePrincipalKey,
  };
}

type PermissionEditorProps = {
  token: string;
  layerSelection: LayerSelection;
  users: ApplicationUser[];
  onReload: Dispatch<SetStateAction<GisCatalogLayerPermission[]>>;
  onError: MessageSetter;
  onNotice: MessageSetter;
};

function PermissionEditor(props: PermissionEditorProps) {
  const editor = usePermissionEditor(props.users);
  const [busy, setBusy] = useState(false);

  return (
    <>
      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label className="text-sm font-semibold text-gray-800">Mappa
          <select className="form-control mt-2 text-base" value={props.layerSelection.layerId} onChange={(event) => props.layerSelection.setLayerId(event.target.value)}>
            {props.layerSelection.manageableLayers.map((layer) => <option key={layer.id} value={layer.id}>{layer.title} · {layer.workspace}</option>)}
          </select>
        </label>
        <label className="text-sm font-semibold text-gray-800">Assegna a
          <select className="form-control mt-2 text-base" value={editor.principalType} onChange={(event) => editor.changePrincipalType(event.target.value as PrincipalType)}>
            <option value="role">Un ruolo</option><option value="user">Una persona</option>
          </select>
        </label>
        {editor.principalType === "role" ? (
          <label className="text-sm font-semibold text-gray-800">Ruolo
            <select className="form-control mt-2 text-base" value={editor.principalKey} onChange={editor.changePrincipalKey}>
              {applicationRoles.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
        ) : (
          <label className="text-sm font-semibold text-gray-800">Persona
            <select className="form-control mt-2 text-base" value={editor.principalKey} onChange={editor.changePrincipalKey}>
              <option value="">Scegli una persona</option>{props.users.map((user) => <option key={user.id} value={user.id}>{userLabel(user)}</option>)}
            </select>
          </label>
        )}
        <label className="text-sm font-semibold text-gray-800">Cosa può fare
          <select className="form-control mt-2 text-base" value={editor.accessLevel} onChange={(event) => editor.setAccessLevel(event.target.value as GisCatalogAccessLevel)}>
            {accessLevels.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
      </div>
      <button className="btn-primary mt-4" type="button" disabled={busy} onClick={() => void savePermission({
        token: props.token, layer: props.layerSelection.selectedLayer, principalType: editor.principalType,
        principalKey: editor.principalKey, accessLevel: editor.accessLevel,
        onBusy: setBusy, onReload: props.onReload, onError: props.onError, onNotice: props.onNotice,
      })}>{busy ? "Salvataggio..." : "Salva permesso"}</button>
    </>
  );
}

async function revokePermission({
  token,
  permission,
  onBusy,
  onRevoked,
  onError,
  onNotice,
  onClose,
}: {
  token: string;
  permission: GisCatalogLayerPermission;
  onBusy: (busy: boolean) => void;
  onRevoked: (id: string) => void;
  onError: MessageSetter;
  onNotice: MessageSetter;
  onClose: () => void;
}) {
  onBusy(true);
  onError(null);
  try {
    await revokeGisLayerPermission(token, permission.layer_id, permission.id);
    onRevoked(permission.id);
    onClose();
    onNotice("Permesso revocato.");
  } catch (revokeError) {
    onError(errorText(revokeError, "Revoca permesso non riuscita"));
  } finally {
    onBusy(false);
  }
}

function PermissionList({ token, users, permissions, loading, error, onRevoked, onError, onNotice }: {
  token: string; users: ApplicationUser[]; permissions: GisCatalogLayerPermission[];
  loading: boolean; error: string | null; onRevoked: (id: string) => void;
  onError: MessageSetter; onNotice: MessageSetter;
}) {
  const [pending, setPending] = useState<GisCatalogLayerPermission | null>(null);
  const [busy, setBusy] = useState(false);
  const closePending = () => setPending(null);
  return (
    <>
      <div className="mt-6 grid gap-3">
        {loading ? <p className="text-sm text-gray-600" role="status">Caricamento permessi...</p> : null}
        {!loading && permissions.length === 0 ? <p className="text-sm text-gray-600">Nessun permesso esplicito configurato.</p> : null}
        {permissions.map((permission) => <article key={permission.id} className="flex flex-col gap-3 rounded-2xl border border-[#e2e9e3] bg-[#f8faf8] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div><p className="font-semibold text-gray-950">{principalLabel(permission, users)}</p><p className="mt-1 text-sm text-gray-600">{accessLabels[permission.access_level] ?? permission.access_level}</p></div>
          <button className="btn-secondary" type="button" onClick={() => setPending(permission)}>Revoca</button>
        </article>)}
      </div>
      {pending ? <ConfirmationDialog
        title="Revocare questo permesso?" description={principalLabel(pending, users)}
        consequences={["La persona o il ruolo potrebbe perdere subito l'accesso alla mappa.", "La revoca sarà registrata nello storico GIS."]}
        confirmLabel="Conferma revoca" busy={busy} error={error} tone="destructive"
        onCancel={closePending} onConfirm={() => void revokePermission({
          token, permission: pending, onBusy: setBusy, onRevoked, onError, onNotice,
          onClose: closePending,
        })}
      /> : null}
    </>
  );
}
