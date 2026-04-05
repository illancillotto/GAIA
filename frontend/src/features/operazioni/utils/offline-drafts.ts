/** Offline draft storage using IndexedDB for mini-app operators. */

const DB_NAME = "gaia-operazioni-drafts";
const DB_VERSION = 1;
const STORE_DRAFTS = "drafts";

interface DraftRecord {
  id: string;
  type: "activity" | "report";
  data: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  syncStatus: "draft" | "pending" | "synced" | "error";
  syncError?: string;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_DRAFTS)) {
        const store = db.createObjectStore(STORE_DRAFTS, { keyPath: "id" });
        store.createIndex("type", "type", { unique: false });
        store.createIndex("syncStatus", "syncStatus", { unique: false });
        store.createIndex("updatedAt", "updatedAt", { unique: false });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** Save or update a draft. */
export async function saveDraft(draft: Omit<DraftRecord, "createdAt" | "updatedAt" | "syncStatus">): Promise<void> {
  const db = await openDB();
  const now = new Date().toISOString();
  const tx = db.transaction(STORE_DRAFTS, "readwrite");
  const store = tx.objectStore(STORE_DRAFTS);

  const existing = await new Promise<DraftRecord | undefined>((resolve) => {
    const req = store.get(draft.id);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => resolve(undefined);
  });

  const record: DraftRecord = {
    ...draft,
    createdAt: existing?.createdAt || now,
    updatedAt: now,
    syncStatus: existing?.syncStatus || "draft",
  };

  store.put(record);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

/** Get a single draft by ID. */
export async function getDraft(id: string): Promise<DraftRecord | null> {
  const db = await openDB();
  const tx = db.transaction(STORE_DRAFTS, "readonly");
  const store = tx.objectStore(STORE_DRAFTS);
  return new Promise((resolve, reject) => {
    const req = store.get(id);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

/** Get all drafts, optionally filtered by type or sync status. */
export async function getAllDrafts(filter?: {
  type?: "activity" | "report";
  syncStatus?: DraftRecord["syncStatus"];
}): Promise<DraftRecord[]> {
  const db = await openDB();
  const tx = db.transaction(STORE_DRAFTS, "readonly");
  const store = tx.objectStore(STORE_DRAFTS);

  return new Promise((resolve, reject) => {
    const req = store.getAll();
    req.onsuccess = () => {
      let results = req.result as DraftRecord[];
      if (filter?.type) {
        results = results.filter((d) => d.type === filter.type);
      }
      if (filter?.syncStatus) {
        results = results.filter((d) => d.syncStatus === filter.syncStatus);
      }
      resolve(results.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)));
    };
    req.onerror = () => reject(req.error);
  });
}

/** Mark a draft as pending sync. */
export async function markDraftPending(id: string): Promise<void> {
  const db = await openDB();
  const tx = db.transaction(STORE_DRAFTS, "readwrite");
  const store = tx.objectStore(STORE_DRAFTS);
  const draft = await new Promise<DraftRecord | undefined>((resolve) => {
    const req = store.get(id);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => resolve(undefined);
  });
  if (draft) {
    draft.syncStatus = "pending";
    draft.updatedAt = new Date().toISOString();
    store.put(draft);
  }
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

/** Mark a draft as synced or error. */
export async function updateDraftSyncStatus(
  id: string,
  status: "synced" | "error",
  errorMessage?: string,
): Promise<void> {
  const db = await openDB();
  const tx = db.transaction(STORE_DRAFTS, "readwrite");
  const store = tx.objectStore(STORE_DRAFTS);
  const draft = await new Promise<DraftRecord | undefined>((resolve) => {
    const req = store.get(id);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => resolve(undefined);
  });
  if (draft) {
    draft.syncStatus = status;
    draft.updatedAt = new Date().toISOString();
    if (errorMessage) draft.syncError = errorMessage;
    store.put(draft);
  }
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

/** Delete a draft. */
export async function deleteDraft(id: string): Promise<void> {
  const db = await openDB();
  const tx = db.transaction(STORE_DRAFTS, "readwrite");
  const store = tx.objectStore(STORE_DRAFTS);
  store.delete(id);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

/** Get count of pending drafts. */
export async function getPendingCount(): Promise<number> {
  const drafts = await getAllDrafts({ syncStatus: "pending" });
  return drafts.length;
}

/** Generate a unique client-side ID for offline drafts. */
export function generateDraftId(): string {
  return `draft-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}
