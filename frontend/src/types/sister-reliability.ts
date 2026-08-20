export type SisterRequestReliability = {
  attempts: number;
  sister_credential_id: string | null;
  sister_remote_request_id: string | null;
  sister_remote_state: string | null;
  retry_not_before: string | null;
  last_error_code: string | null;
};

export type SisterDocumentReliability = {
  sha256?: string | null;
};
