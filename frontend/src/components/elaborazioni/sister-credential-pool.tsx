"use client";

import { useState } from "react";

import {
  useBulkCredentialTest,
  useSingleCredentialTest,
} from "@/components/elaborazioni/sister-credential-pool-controller";
import { SisterCredentialPoolView } from "@/components/elaborazioni/sister-credential-pool-view";
import { updateElaborazioneCredential } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { ElaborazioneCredential, ElaborazioneCredentialTestResult } from "@/types/api";

type SisterCredentialPoolProps = {
  credentials: ElaborazioneCredential[];
  selectedCredentialId: string | null;
  currentTestResult: ElaborazioneCredentialTestResult | null;
  embedded: boolean;
  externalBusy: boolean;
  releaseBusy: boolean;
  resumeReleasedBusy: boolean;
  releasedBatchesCount: number;
  onSelectCredential: (credential: ElaborazioneCredential) => void;
  onMakeDefault: (credential: ElaborazioneCredential) => Promise<void>;
  onDeleteCredential: (credential: ElaborazioneCredential) => void;
  onTestResult: (result: ElaborazioneCredentialTestResult) => void;
  onTestError: (message: string) => void;
  onClearFeedback: () => void;
  onRefreshCredentials: () => Promise<void>;
  onBulkBusyChange: (busy: boolean) => void;
  onReleaseSessions: () => Promise<void>;
  onResumeReleasedBatch: () => Promise<void>;
};

export function SisterCredentialPool(props: SisterCredentialPoolProps) {
  const single = useSingleCredentialTest(props);
  const bulk = useBulkCredentialTest(props);
  const [releasingCredentialId, setReleasingCredentialId] = useState<string | null>(null);
  const controlsDisabled = props.externalBusy || bulk.bulkRunning || single.singleTestingId != null || releasingCredentialId != null;

  async function releaseCredential(credential: ElaborazioneCredential): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    props.onClearFeedback();
    setReleasingCredentialId(credential.id);
    try {
      await updateElaborazioneCredential(token, credential.id, { active: false });
      await props.onRefreshCredentials();
    } catch (error) {
      props.onTestError(error instanceof Error ? error.message : "Errore rilascio sessione SISTER");
    } finally {
      setReleasingCredentialId(null);
    }
  }

  return (
    <SisterCredentialPoolView
      {...props}
      bulkRunning={bulk.bulkRunning}
      controlsDisabled={controlsDisabled}
      onCancel={bulk.cancel}
      onReleaseCredential={releaseCredential}
      onTestAll={bulk.testAll}
      onTestCredential={single.testCredential}
      progressById={bulk.progressById}
      runStatus={bulk.runStatus}
      singleTestingId={single.singleTestingId}
    />
  );
}
