"use client";

import { useEffect, useRef, useState } from "react";

import { getElaborazioneCredentialTest, testElaborazioneCredentials } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { testSisterCredentialPool, type SisterCredentialTestProgress } from "@/lib/sister-credential-tests";
import type { ElaborazioneCredential, ElaborazioneCredentialTestResult } from "@/types/api";

export type PoolRunStatus = "idle" | "running" | "stopping" | "completed" | "cancelled";

type SingleTestOptions = {
  onSelectCredential: (credential: ElaborazioneCredential) => void;
  onTestResult: (result: ElaborazioneCredentialTestResult) => void;
  onTestError: (message: string) => void;
  onClearFeedback: () => void;
};

type BulkTestOptions = {
  credentials: ElaborazioneCredential[];
  onTestResult: (result: ElaborazioneCredentialTestResult) => void;
  onTestError: (message: string) => void;
  onClearFeedback: () => void;
  onRefreshCredentials: () => Promise<void>;
  onBulkBusyChange: (busy: boolean) => void;
};

type BulkRunOptions = BulkTestOptions & {
  token: string;
  signal: AbortSignal;
  mountedRef: React.MutableRefObject<boolean>;
  setProgressById: React.Dispatch<React.SetStateAction<Record<string, SisterCredentialTestProgress>>>;
};

function queuedProgress(credentials: ElaborazioneCredential[]): Record<string, SisterCredentialTestProgress> {
  return Object.fromEntries(
    credentials.map((credential) => [
      credential.id,
      {
        credentialId: credential.id,
        phase: "queued" as const,
        message: "In attesa del turno di verifica.",
        result: null,
      },
    ]),
  );
}

async function runBulkTest(options: BulkRunOptions) {
  return testSisterCredentialPool({
    credentials: options.credentials,
    signal: options.signal,
    startTest: (credentialId) => testElaborazioneCredentials(options.token, { credential_id: credentialId }),
    getTest: (testId) => getElaborazioneCredentialTest(options.token, testId),
    onProgress: (progress) => {
      if (options.mountedRef.current) {
        options.setProgressById((current) => ({ ...current, [progress.credentialId]: progress }));
      }
    },
    onTerminalResult: options.onTestResult,
  });
}

export function useSingleCredentialTest(options: SingleTestOptions) {
  const [singleTestingId, setSingleTestingId] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => () => {
    mountedRef.current = false;
  }, []);

  async function testCredential(credential: ElaborazioneCredential): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setSingleTestingId(credential.id);
    options.onSelectCredential(credential);
    options.onClearFeedback();
    try {
      const result = await testElaborazioneCredentials(token, { credential_id: credential.id });
      options.onTestResult(result);
    } catch (error) {
      options.onTestError(error instanceof Error ? error.message : "Errore test connessione SISTER");
    } finally {
      if (mountedRef.current) setSingleTestingId(null);
    }
  }

  return { singleTestingId, testCredential };
}

export function useBulkCredentialTest(options: BulkTestOptions) {
  const [runStatus, setRunStatus] = useState<PoolRunStatus>("idle");
  const [progressById, setProgressById] = useState<Record<string, SisterCredentialTestProgress>>({});
  const abortControllerRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => () => {
    mountedRef.current = false;
    abortControllerRef.current?.abort();
  }, []);

  async function testAll(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || options.credentials.length === 0) return;

    const controller = new AbortController();
    abortControllerRef.current = controller;
    setProgressById(queuedProgress(options.credentials));
    setRunStatus("running");
    options.onBulkBusyChange(true);
    options.onClearFeedback();

    try {
      const result = await runBulkTest({ ...options, token, signal: controller.signal, mountedRef, setProgressById });
      if (mountedRef.current) {
        setRunStatus(result.cancelled ? "cancelled" : "completed");
        await options.onRefreshCredentials();
      }
    } catch (error) {
      if (mountedRef.current) {
        setRunStatus("cancelled");
        options.onTestError(error instanceof Error ? error.message : "Errore durante la verifica del pool SISTER");
      }
    } finally {
      if (mountedRef.current) {
        abortControllerRef.current = null;
        options.onBulkBusyChange(false);
      }
    }
  }

  function cancel(): void {
    setRunStatus("stopping");
    abortControllerRef.current?.abort();
  }

  return {
    bulkRunning: runStatus === "running" || runStatus === "stopping",
    cancel,
    progressById,
    runStatus,
    testAll,
  };
}
