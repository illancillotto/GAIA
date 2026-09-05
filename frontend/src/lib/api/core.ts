const DEFAULT_API_BASE_URL = "/api";
export const SESSION_BOOTSTRAP_TIMEOUT_MS = 8_000;
export const SESSION_BOOTSTRAP_TIMEOUT_MESSAGE =
  "Timeout durante la verifica della sessione. Ricarica la pagina o ripeti il login.";
export class ApiError extends Error {
  status?: number;
  detailData: unknown;

  constructor(message: string, detailData?: unknown, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detailData = detailData;
  }
}

type ApiRequestInit = RequestInit & {
  timeoutMs?: number;
};

export function isAuthError(error: unknown): error is ApiError {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
  const value = raw.replace(/\/+$/, "");

  // Always keep a non-empty base URL.
  if (!value) {
    return DEFAULT_API_BASE_URL;
  }

  // In browser we require a relative base (e.g. "/api") so nginx can proxy correctly.
  // If a previous build/runtime leaks an absolute URL (e.g. "http://localhost"),
  // fall back to the safe default.
  if (typeof window !== "undefined" && !value.startsWith("/")) {
    return DEFAULT_API_BASE_URL;
  }

  return value;
}

export async function request<T>(path: string, init?: ApiRequestInit): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const { timeoutMs, signal, ...fetchInit } = init ?? {};
  const controller = timeoutMs ? new AbortController() : null;
  let timedOut = false;
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  if (controller && signal) {
    if (signal.aborted) {
      controller.abort(signal.reason);
    } else {
      signal.addEventListener("abort", () => controller.abort(signal.reason), { once: true });
    }
  }

  if (controller && timeoutMs) {
    timeoutId = setTimeout(() => {
      timedOut = true;
      controller.abort(new Error(SESSION_BOOTSTRAP_TIMEOUT_MESSAGE));
    }, timeoutMs);
  }

  let response: Response;

  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      ...fetchInit,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(fetchInit.headers ?? {}),
      },
      cache: "no-store",
      signal: controller?.signal ?? signal,
    });
  } catch (error) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    if (timedOut) {
      throw new ApiError(SESSION_BOOTSTRAP_TIMEOUT_MESSAGE);
    }
    throw error;
  }

  if (timeoutId) {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    let detail = "Request failed";
    let detailData: unknown;

    try {
      const payload = (await response.json()) as { detail?: unknown };
      detailData = payload.detail;

      if (typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (
        payload.detail &&
        typeof payload.detail === "object" &&
        "message" in payload.detail &&
        typeof payload.detail.message === "string"
      ) {
        detail = payload.detail.message;
      } else if (payload.detail != null) {
        detail = JSON.stringify(payload.detail);
      }
    } catch {
      detail = response.statusText || detail;
    }

    throw new ApiError(detail, detailData, response.status);
  }

  if (response.status === 204 || response.status === 205) {
    return undefined as T;
  }

  const contentLength = response.headers.get("content-length");
  if (contentLength === "0") {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type");
  if (!contentType) {
    const text = await response.text();
    if (!text) {
      return undefined as T;
    }
    return JSON.parse(text) as T;
  }

  return (await response.json()) as T;
}

export async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = "Request failed";

    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      detail = response.statusText || detail;
    }

    throw new ApiError(detail, undefined, response.status);
  }

  return response.blob();
}

export async function requestFormDataWithUploadProgress<T>(
  path: string,
  formData: FormData,
  token: string,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return await new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${getApiBaseUrl()}${path}`);
    xhr.responseType = "json";
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) {
        return;
      }
      const percent = Math.min(100, Math.max(0, Math.round((event.loaded / event.total) * 100)));
      onProgress?.(percent);
    });

    xhr.addEventListener("load", () => {
      const responseData = xhr.response;
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress?.(100);
        resolve(responseData as T);
        return;
      }

      const payload = typeof responseData === "object" && responseData !== null ? (responseData as { detail?: unknown }) : undefined;
      let detail = "Request failed";
      const detailData: unknown = payload?.detail;

      if (typeof payload?.detail === "string") {
        detail = payload.detail;
      } else if (
        payload?.detail &&
        typeof payload.detail === "object" &&
        "message" in payload.detail &&
        typeof payload.detail.message === "string"
      ) {
        detail = payload.detail.message;
      } else if (payload?.detail != null) {
        detail = JSON.stringify(payload.detail);
      } else if (xhr.statusText) {
        detail = xhr.statusText;
      }

      reject(new ApiError(detail, detailData, xhr.status));
    });

    xhr.addEventListener("error", () => {
      reject(new ApiError("Errore di rete durante upload CSV"));
    });

    xhr.send(formData);
  });
}

export function createQueryString(params: Record<string, string | undefined>): string {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value && value.trim().length > 0) {
      searchParams.set(key, value.trim());
    }
  });

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export function getWebSocketBaseUrl(): string {
  const apiBaseUrl = getApiBaseUrl();

  if (apiBaseUrl.startsWith("https://")) {
    return apiBaseUrl.replace("https://", "wss://");
  }

  if (apiBaseUrl.startsWith("http://")) {
    return apiBaseUrl.replace("http://", "ws://");
  }

  if (typeof window === "undefined") {
    return apiBaseUrl;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${apiBaseUrl}`;
}
