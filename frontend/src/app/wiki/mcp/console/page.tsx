"use client";

import Link from "next/link";

import { ProtectedPage } from "@/components/app/protected-page";
import { MCPConsole } from "@/features/wiki/mcp-console";

export default function MCPConsolePage() {
  return (
    <ProtectedPage title="MCP — dati e richieste" description="Dataset sintetico e storico delle chiamate autorizzate." breadcrumb="GAIA / Wiki / MCP">
      <Link href="/wiki/mcp" className="btn-secondary">Apri agente sintetico</Link>
      <MCPConsole />
    </ProtectedPage>
  );
}
