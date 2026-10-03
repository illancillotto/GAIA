import { Suspense } from "react";
import type { Metadata } from "next";
import { MCPConsent } from "@/features/wiki/mcp-consent";

export const metadata: Metadata = { referrer: "no-referrer", robots: { index: false, follow: false } };

export default function MCPConsentPage() {
  return <Suspense fallback={<p>Caricamento richiesta…</p>}><MCPConsent enabled={process.env.NEXT_PUBLIC_GAIA_MCP_CONNECTOR_ENABLED === "true"} /></Suspense>;
}
