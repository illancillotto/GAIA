"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { applyLiveSync, applySync, getSyncCapabilities, getSyncRuns, previewSync } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { SyncApplyResult, SyncCapabilities, SyncPreview, SyncRun } from "@/types/api";

export default function SyncPage() {
  const [capabilities, setCapabilities] = useState<SyncCapabilities | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<SyncPreview | null>(null);
  const [applyResult, setApplyResult] = useState<SyncApplyResult | null>(null);
  const [syncRuns, setSyncRuns] = useState<SyncRun[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [passwdText, setPasswdText] = useState("");
  const [groupText, setGroupText] = useState("");
  const [sharesText, setSharesText] = useState("");
  const [aclTexts, setAclTexts] = useState("");

  useEffect(() => {
    void loadSyncContext();
  }, []);

  async function loadSyncContext(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const [capabilitiesResult, syncRunsResult] = await Promise.all([
        getSyncCapabilities(token),
        getSyncRuns(token),
      ]);
      setCapabilities(capabilitiesResult);
      setSyncRuns(syncRunsResult);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento sync");
    }
  }

  function buildPayload() {
    return {
      passwd_text: passwdText,
      group_text: groupText,
      shares_text: sharesText,
      acl_texts: aclTexts
        .split("\n---\n")
        .map((item) => item.trim())
        .filter(Boolean),
    };
  }

  async function handlePreview(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setIsSubmitting(true);
    try {
      const result = await previewSync(token, buildPayload());
      setPreview(result);
      setApplyResult(null);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Errore preview sync");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleApply(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setIsSubmitting(true);
    try {
      const previewResult = await previewSync(token, buildPayload());
      const applySyncResult = await applySync(token, buildPayload());
      const syncRunsResult = await getSyncRuns(token);
      setPreview(previewResult);
      setApplyResult(applySyncResult);
      setSyncRuns(syncRunsResult);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Errore apply sync");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLiveApply(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setIsSubmitting(true);
    try {
      const result = await applyLiveSync(token);
      const syncRunsResult = await getSyncRuns(token);
      setApplyResult(result);
      setSyncRuns(syncRunsResult);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Errore live apply sync");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <ProtectedPage
      title="Sync NAS"
      description="Stato reale del connector NAS configurato nel backend, con preview/apply da testo e live apply via SSH."
    >
      {error ? <p className="status-note error-text">{error}</p> : null}
      {capabilities ? (
        <article className="panel">
          <div className="panel-header">
            <div>
              <h3>Capability Connector</h3>
              <p className="status-note">
                Host <span className="mono">{capabilities.host}</span>, autenticazione <span className="mono">{capabilities.auth_mode}</span>, retry <span className="mono">{capabilities.retry_strategy}</span>.
              </p>
            </div>
            <button className="button button-secondary-light" type="button" onClick={() => void loadSyncContext()}>
              Refresh
            </button>
          </div>
          <div className="panel-grid">
            <article className="panel">
              <small>SSH</small>
              <div className={`status-pill ${capabilities.ssh_configured ? "status-ok" : "status-warn"}`}>
                {capabilities.ssh_configured ? "Configurato" : "Assente"}
              </div>
              <p>{capabilities.username}@{capabilities.host}:{capabilities.port}</p>
            </article>
            <article className="panel">
              <small>Live Sync</small>
              <div className={`status-pill ${capabilities.supports_live_sync ? "status-ok" : "status-warn"}`}>
                {capabilities.supports_live_sync ? "Attivo" : "Disabilitato"}
              </div>
              <p>Timeout {capabilities.timeout_seconds}s</p>
            </article>
            <article className="panel">
              <small>Retry</small>
              <div className="metric metric-compact">{capabilities.retry_max_attempts}</div>
              <p>
                base {capabilities.retry_base_delay_seconds}s, max {capabilities.retry_max_delay_seconds}s
              </p>
              <p>
                jitter {capabilities.retry_jitter_enabled ? "on" : "off"} ({Math.round(capabilities.retry_jitter_ratio * 100)}%)
              </p>
            </article>
          </div>
        </article>
      ) : (
        <p className="status-note">Nessuna capability disponibile.</p>
      )}

      <article className="panel">
        <h3>Payload Sync</h3>
        <p className="status-note">
          Usa un blocco ACL per ogni share, nello stesso ordine delle righe in elenco share. Separatore blocchi: <span className="mono">---</span>
        </p>
        <div className="form-grid">
          <label>
            Passwd
            <textarea
              className="textarea-input mono"
              rows={6}
              value={passwdText}
              onChange={(event) => setPasswdText(event.target.value)}
            />
          </label>
          <label>
            Group
            <textarea
              className="textarea-input mono"
              rows={6}
              value={groupText}
              onChange={(event) => setGroupText(event.target.value)}
            />
          </label>
          <label>
            Share Listing
            <textarea
              className="textarea-input mono"
              rows={4}
              value={sharesText}
              onChange={(event) => setSharesText(event.target.value)}
            />
          </label>
          <label>
            ACL Texts
            <textarea
              className="textarea-input mono"
              rows={10}
              value={aclTexts}
              onChange={(event) => setAclTexts(event.target.value)}
            />
          </label>
        </div>
        <div className="action-row">
          <button className="button" type="button" onClick={() => void handlePreview()} disabled={isSubmitting}>
            Preview Sync
          </button>
          <button className="button" type="button" onClick={() => void handleApply()} disabled={isSubmitting}>
            Apply Sync
          </button>
          <button className="button" type="button" onClick={() => void handleLiveApply()} disabled={isSubmitting}>
            Live Apply
          </button>
        </div>
      </article>

      {preview ? (
        <article className="panel">
          <h3>Preview Risultato</h3>
          <div className="panel-grid">
            <article className="panel">
              <small>Utenti</small>
              <div className="metric">{preview.users.length}</div>
            </article>
            <article className="panel">
              <small>Gruppi</small>
              <div className="metric">{preview.groups.length}</div>
            </article>
            <article className="panel">
              <small>Share</small>
              <div className="metric">{preview.shares.length}</div>
            </article>
            <article className="panel">
              <small>ACL</small>
              <div className="metric">{preview.acl_entries.length}</div>
            </article>
          </div>
        </article>
      ) : null}

      {applyResult ? (
        <article className="panel">
          <h3>Apply Risultato</h3>
          <p className="status-note">
            Snapshot <span className="mono">#{applyResult.snapshot_id}</span> creato con checksum <span className="mono">{applyResult.snapshot_checksum.slice(0, 12)}</span>.
          </p>
          <div className="panel-grid">
            <article className="panel">
              <small>Permission Entries</small>
              <div className="metric">{applyResult.persisted_permission_entries}</div>
            </article>
            <article className="panel">
              <small>Effective Permissions</small>
              <div className="metric">{applyResult.persisted_effective_permissions}</div>
            </article>
            <article className="panel">
              <small>Share/ACL Pairs</small>
              <div className="metric">{applyResult.share_acl_pairs_used}</div>
            </article>
          </div>
        </article>
      ) : null}

      {syncRuns.length > 0 ? (
        <article className="panel">
          <div className="panel-header">
            <div>
              <h3>Storico Sync</h3>
              <p className="status-note">Ultime esecuzioni ordinate per completamento.</p>
            </div>
            <div className="badge">Totale run: {syncRuns.length}</div>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Mode</th>
                <th>Trigger</th>
                <th>Source</th>
                <th>Actor</th>
                <th>Status</th>
                <th>Tentativi</th>
                <th>Durata</th>
                <th>Snapshot</th>
                <th>Fine</th>
              </tr>
            </thead>
            <tbody>
              {syncRuns.map((syncRun) => (
                <tr key={syncRun.id}>
                  <td className="mono">{syncRun.id}</td>
                  <td>{syncRun.mode}</td>
                  <td>{syncRun.trigger_type}</td>
                  <td>{syncRun.source_label ?? "-"}</td>
                  <td>{syncRun.initiated_by ?? "-"}</td>
                  <td>
                    <span className={`status-pill ${syncRun.status === "succeeded" ? "status-ok" : "status-warn"}`}>
                      {syncRun.status}
                    </span>
                  </td>
                  <td>{syncRun.attempts_used}</td>
                  <td className="mono">{syncRun.duration_ms ?? "-"} ms</td>
                  <td className="mono">{syncRun.snapshot_id ?? "-"}</td>
                  <td className="mono">{syncRun.completed_at ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      ) : null}
    </ProtectedPage>
  );
}
