import { request } from "@/lib/api/core";

export type MCPConsentDetails = {
  client_name: string;
  scopes: string[];
  resource: string;
  redirect_uri: string;
};

const ENDPOINT = "/wiki/mcp/connector/oauth/consent";

export function loadMCPConsent(token: string, requestId: string): Promise<MCPConsentDetails> {
  return request(`${ENDPOINT}?request_id=${encodeURIComponent(requestId)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function decideMCPConsent(token: string, requestId: string, allowed: boolean): Promise<{ redirect_url: string }> {
  return request(ENDPOINT, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ request_id: requestId, allowed }),
  });
}

export function returnToMCPClient(target: string, registered: string): void {
  const redirect = new URL(target);
  const approved = new URL(registered);
  if (redirect.protocol !== "https:" || redirect.origin !== approved.origin ||
      redirect.pathname !== approved.pathname || redirect.username || redirect.password || redirect.hash) {
    throw new Error("Redirect del connettore non valido");
  }
  globalThis.location.assign(redirect.href);
}
