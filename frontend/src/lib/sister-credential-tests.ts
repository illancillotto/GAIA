import type { ElaborazioneCredential, ElaborazioneCredentialTestResult } from "@/types/api";

const RUNNING_STATUSES = new Set<ElaborazioneCredentialTestResult["status"]>(["pending", "processing"]);

export type SisterCredentialTestPhase = "queued" | "running" | "success" | "warning" | "error" | "stopped";

export type SisterCredentialTestProgress = {
  credentialId: string;
  phase: SisterCredentialTestPhase;
  message: string;
  result: ElaborazioneCredentialTestResult | null;
};

type SisterCredentialPoolTestOptions = {
  credentials: ElaborazioneCredential[];
  startTest: (credentialId: string) => Promise<ElaborazioneCredentialTestResult>;
  getTest: (testId: string) => Promise<ElaborazioneCredentialTestResult>;
  onProgress: (progress: SisterCredentialTestProgress) => void;
  onTerminalResult?: (result: ElaborazioneCredentialTestResult) => void;
  signal?: AbortSignal;
  pollIntervalMs?: number;
  maxPollAttempts?: number;
  wait?: (delayMs: number) => Promise<void>;
};

export type SisterCredentialPoolTestResult = {
  cancelled: boolean;
  processed: number;
};

export function isSisterCredentialTestRunning(status: ElaborazioneCredentialTestResult["status"]): boolean {
  return RUNNING_STATUSES.has(status);
}

export function shouldRefreshSisterCredentialAfterTest(
  hasTransientCredentials: boolean,
  status: ElaborazioneCredentialTestResult["status"],
): boolean {
  return !hasTransientCredentials && !isSisterCredentialTestRunning(status);
}

export function classifySisterCredentialTest(
  credentialId: string,
  result: ElaborazioneCredentialTestResult,
): SisterCredentialTestProgress {
  if (isSisterCredentialTestRunning(result.status)) {
    return {
      credentialId,
      phase: "running",
      message: result.message ?? "Verifica in corso sul worker SISTER.",
      result,
    };
  }

  if (result.authenticated) {
    return {
      credentialId,
      phase: "success",
      message: result.message ?? "Autenticazione SISTER confermata.",
      result,
    };
  }

  if (result.success || result.reachable) {
    return {
      credentialId,
      phase: "warning",
      message: result.message ?? "Portale raggiungibile, autenticazione non confermata.",
      result,
    };
  }

  return {
    credentialId,
    phase: "error",
    message: result.message ?? "Test credenziale SISTER fallito.",
    result,
  };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Errore imprevisto durante il test SISTER.";
}

function defaultWait(delayMs: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, delayMs));
}

function stopRemainingCredentials(
  credentials: ElaborazioneCredential[],
  fromIndex: number,
  onProgress: SisterCredentialPoolTestOptions["onProgress"],
): void {
  for (const credential of credentials.slice(fromIndex)) {
    onProgress({
      credentialId: credential.id,
      phase: "stopped",
      message: "Test non eseguito: verifica del pool interrotta.",
      result: null,
    });
  }
}

export async function testSisterCredentialPool(
  options: SisterCredentialPoolTestOptions,
): Promise<SisterCredentialPoolTestResult> {
  const pollIntervalMs = options.pollIntervalMs ?? 1500;
  const maxPollAttempts = options.maxPollAttempts ?? 120;
  const wait = options.wait ?? defaultWait;
  let processed = 0;

  for (const [index, credential] of options.credentials.entries()) {
    if (options.signal?.aborted) {
      stopRemainingCredentials(options.credentials, index, options.onProgress);
      return { cancelled: true, processed };
    }

    options.onProgress({
      credentialId: credential.id,
      phase: "running",
      message: "Avvio del test sul worker SISTER.",
      result: null,
    });

    try {
      let result = await options.startTest(credential.id);
      let pollAttempts = 0;
      options.onProgress(classifySisterCredentialTest(credential.id, result));

      while (isSisterCredentialTestRunning(result.status) && pollAttempts < maxPollAttempts) {
        await wait(pollIntervalMs);
        if (options.signal?.aborted) {
          stopRemainingCredentials(options.credentials, index, options.onProgress);
          return { cancelled: true, processed };
        }
        result = await options.getTest(result.id);
        pollAttempts += 1;
        options.onProgress(classifySisterCredentialTest(credential.id, result));
      }

      if (isSisterCredentialTestRunning(result.status)) {
        options.onProgress({
          credentialId: credential.id,
          phase: "error",
          message: "Timeout: il worker non ha concluso il test entro il tempo previsto.",
          result,
        });
      } else {
        options.onTerminalResult?.(result);
      }
    } catch (error) {
      if (options.signal?.aborted) {
        stopRemainingCredentials(options.credentials, index, options.onProgress);
        return { cancelled: true, processed };
      }
      options.onProgress({
        credentialId: credential.id,
        phase: "error",
        message: errorMessage(error),
        result: null,
      });
    }

    processed += 1;
  }

  return { cancelled: false, processed };
}
