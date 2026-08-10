const ACCESS_TOKEN_KEY = "gaia.access_token";
const CLIENT_DEVICE_ID_KEY = "gaia.client_device_id";

export function getStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setStoredAccessToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearStoredAccessToken(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
}

function createClientDeviceId(): string {
  if (typeof window !== "undefined" && window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }

  return `gaia-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

export function getStoredClientDeviceId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  let deviceId = window.localStorage.getItem(CLIENT_DEVICE_ID_KEY);
  if (!deviceId) {
    deviceId = createClientDeviceId();
    window.localStorage.setItem(CLIENT_DEVICE_ID_KEY, deviceId);
  }
  return deviceId;
}

export function getClientDeviceLabel(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  const platform = window.navigator.platform || "dispositivo";
  const language = window.navigator.language || "lingua n/d";
  return `${platform} · ${language}`;
}
