"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { applyLiveSync, applySync, getSyncCapabilities, getSyncRuns, previewSync } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { SyncApplyResult, SyncCapabilities, SyncPreview, SyncRun } from "@/types/api";

const samplePasswdText = [
  "mrossi:x:1001:100:Mario Rossi:/var/services/homes/mrossi:/sbin/nologin",
  "lbianchi:x:1002:100:Laura Bianchi:/var/services/homes/lbianchi:/sbin/nologin",
].join("\n");

const sampleGroupText = [
  "amministrazione:x:2001:mrossi",
  "direzione:x:2002:lbianchi",
].join("\n");

const sampleSharesText = ["contabilita", "direzione"].join("\n");

const sampleAclTexts = [
  "allow: group:amministrazione:read,write\ndeny: user:ospite:read",
  "allow: group:direzione:write",
];

export default function SyncPage() {
  const [capabilities, setCapabilities] = useState<SyncCapabilities | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<SyncPreview | null>(null);
  const [applyResult, setApplyResult] = useState<SyncApplyResult | null>(null);
  const [syncRuns, setSyncRuns] = useState<SyncRun[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [passwdText, setPasswdText] = useState(samplePasswdText);
  const [groupText, setGroupText] = useState(sampleGroupText);
  const [sharesText, setSharesText] = useState(sampleSharesText);
  const [aclTexts, setAclTexts] = useState(sampleAclTexts.join("\n---\n"));

  useEffect(() => {
    async function loadCapabilities() {
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

    void loadCapabilities();
  }, []);

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
        <table className="data-table">
          <tbody>
            <tr>
              <th>Host</th>
              <td>{capabilities.host}</td>
            </tr>
            <tr>
              <th>Porta</th>
              <td>{capabilities.port}</td>
            </tr>
            <tr>
              <th>Username</th>
              <td>{capabilities.username}</td>
            </tr>
            <tr>
              <th>SSH configurato</th>
              <td>{capabilities.ssh_configured ? "Si" : "No"}</td>
            </tr>
            <tr>
              <th>Live sync</th>
              <td>{capabilities.supports_live_sync ? "Attivo" : "Non ancora implementato"}</td>
            </tr>
            <tr>
              <th>Auth mode</th>
              <td>{capabilities.auth_mode}</td>
            </tr>
          </tbody>
        </table>
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
          <h3>Storico Sync</h3>
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
                  <td>{syncRun.status}</td>
                  <td>{syncRun.attempts_used}</td>
                  <td className="mono">{syncRun.duration_ms ?? "-"} ms</td>
                  <td className="mono">{syncRun.snapshot_id ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      ) : null}
    </ProtectedPage>
  );
}
