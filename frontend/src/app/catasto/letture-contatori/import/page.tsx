"use client";

import Link from "next/link";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { MeterReadingImportPanel } from "@/components/catasto/meter-reading-import-panel";

export default function CatastoMeterReadingsImportPage() {
  return (
    <CatastoPage
      title="Import letture contatori"
      description="Validazione e import dei file Excel distrettuali delle letture contatori irrigui."
      breadcrumb="Catasto / Contatori irrigui / Import"
      requiredModule="catasto"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="page-stack">
        <div className="flex justify-end">
          <Link className="btn-secondary" href="/catasto/letture-contatori">
            Torna al registro
          </Link>
        </div>
        <MeterReadingImportPanel />
      </div>
    </CatastoPage>
  );
}
