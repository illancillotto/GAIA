"use client";

import Link from "next/link";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { MeterReadingsTable } from "@/components/catasto/meter-readings-table";

export default function CatastoMeterReadingsPage() {
  return (
    <CatastoPage
      title="Contatori irrigui"
      description="Consultazione e dettaglio delle letture contatori importate nel modulo Catasto."
      breadcrumb="Catasto / Contatori irrigui"
      requiredModule="catasto"
    >
      <div className="page-stack">
        <section className="rounded-[2rem] border border-emerald-100 bg-[#f5faf7] p-6 shadow-sm">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="inline-flex rounded-full border border-emerald-200 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                Letture contatori irrigui
              </div>
              <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">Registro letture Catasto</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                Unifica import Excel, linking anagrafico e consultazione per punto di consegna, anno e soggetto.
              </p>
            </div>
            <Link className="btn-primary" href="/catasto/letture-contatori/import">
              Import Excel
            </Link>
          </div>
        </section>

        <MeterReadingsTable />
      </div>
    </CatastoPage>
  );
}
