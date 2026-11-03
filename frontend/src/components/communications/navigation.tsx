import Link from "next/link";
import type { Channel } from "@/types/communications";

export function SollecitiNavigation({ tab, onChange }: { tab: "generati" | "poste"; onChange: (tab: "generati" | "poste") => void }) {
  return <div role="tablist" aria-label="Invio solleciti" className="flex flex-wrap gap-2">
    <button role="tab" aria-selected={tab === "generati"} className={tab === "generati" ? "btn-primary" : "btn-secondary"} onClick={() => onChange("generati")}>Solleciti generati</button>
    <button role="tab" aria-selected={tab === "poste"} className={tab === "poste" ? "btn-primary" : "btn-secondary"} onClick={() => onChange("poste")}>Posta Online</button>
    <Link className="btn-secondary" href="/ruolo/tributi/solleciti/pec">Invio PEC</Link>
    <Link className="btn-secondary" href="/ruolo/tributi/solleciti/email">Invio Email</Link>
  </div>;
}

export function CommunicationsNavigation({ channel }: { channel: Channel }) {
  return <nav aria-label="Invio solleciti" className="flex flex-wrap gap-2">
    <Link className="btn-secondary" href="/ruolo/tributi/solleciti">Solleciti generati</Link>
    <Link className="btn-secondary" href="/ruolo/tributi/solleciti/poste">Posta Online</Link>
    <Link className={channel === "pec" ? "btn-primary" : "btn-secondary"} aria-current={channel === "pec" ? "page" : undefined} href="/ruolo/tributi/solleciti/pec">Invio PEC</Link>
    <Link className={channel === "email" ? "btn-primary" : "btn-secondary"} aria-current={channel === "email" ? "page" : undefined} href="/ruolo/tributi/solleciti/email">Invio Email</Link>
  </nav>;
}
