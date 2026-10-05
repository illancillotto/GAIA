"use client";

import { useEffect, useState } from "react";

import {
  downloadRegisteredMailCard, listRegisteredMailCards, uploadRegisteredMailCard,
  type RegisteredMailCard,
} from "@/lib/registered-mail-documents-api";
import type { RuoloTributiRegisteredMailResponse } from "@/types/ruolo";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Operazione cartolina non riuscita";
}

function canUploadCard(mail: RuoloTributiRegisteredMailResponse, canEdit: boolean): boolean {
  return canEdit && mail.match_status === "matched" && Boolean(mail.avviso_id && mail.subject_id) && !mail.anomaly_key;
}

function CardPreview({ token, mailId, card }: { token: string; mailId: string; card: RegisteredMailCard }) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    setUrl(null);
    setError(null);
    downloadRegisteredMailCard(token, mailId, card.id).then((blob) => {
      if (!active) return;
      objectUrl = URL.createObjectURL(blob);
      setUrl(objectUrl);
    }).catch((failure: unknown) => {
      if (active) setError(errorMessage(failure));
    });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [token, mailId, card.id]);
  if (error) return <p role="alert">{error}</p>;
  if (!url) return <p role="status">Caricamento anteprima...</p>;
  return <div>
    <a className="font-semibold text-[#1D4E35] underline" download={card.filename} href={url}>Scarica {card.filename}</a>
    <iframe className="mt-3 h-[65vh] w-full border" src={url} title={`Cartolina ${card.filename}`} />
  </div>;
}

function useCardUpload(token: string, mail: RuoloTributiRegisteredMailResponse, onSaved: (card: RegisteredMailCard) => void) {
  const [file, setFile] = useState<File | null>(null);
  const [scannedOn, setScannedOn] = useState("");
  const [verified, setVerified] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function save(): Promise<void> {
    if (!file || !scannedOn || !verified) return;
    setSaving(true);
    setError(null);
    try {
      const card = await uploadRegisteredMailCard(token, mail.id, file, mail.tracking_number ?? "", scannedOn);
      onSaved(card);
      setVerified(false);
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setSaving(false);
    }
  }
  return { file, setFile, scannedOn, setScannedOn, verified, setVerified, saving, error, save };
}

function CardUploadForm({ token, mail, loading, onSaved }: {
  token: string; mail: RuoloTributiRegisteredMailResponse; loading: boolean; onSaved: (card: RegisteredMailCard) => void;
}) {
  const upload = useCardUpload(token, mail, onSaved);
  return <form className="my-4 grid gap-3 rounded-xl border p-4" onSubmit={(event) => { event.preventDefault(); void upload.save(); }}>
    {upload.error ? <p className="text-red-700" role="alert">{upload.error}</p> : null}
    <label>PDF cartolina (massimo 20 MiB)<input accept="application/pdf,.pdf" onChange={(event) => upload.setFile(event.target.files?.[0] ?? null)} type="file" /></label>
    <label>Data di scansione<input onChange={(event) => upload.setScannedOn(event.target.value)} type="date" value={upload.scannedOn} /></label>
    <label><input checked={upload.verified} onChange={(event) => upload.setVerified(event.target.checked)} type="checkbox" /> Ho verificato tracking e contribuente sulla cartolina</label>
    <button className="btn-primary" disabled={upload.saving || loading || !upload.file || !upload.scannedOn || !upload.verified} type="submit">{upload.saving ? "Salvataggio..." : "Salva cartolina"}</button>
  </form>;
}

function CardsDialog({ token, mail, canEdit, onClose }: {
  token: string; mail: RuoloTributiRegisteredMailResponse; canEdit: boolean; onClose: () => void;
}) {
  const [cards, setCards] = useState<RegisteredMailCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<RegisteredMailCard | null>(null);
  const canUpload = canUploadCard(mail, canEdit);
  useEffect(() => {
    let active = true;
    listRegisteredMailCards(token, mail.id).then((items) => {
      if (active) setCards(items);
    }).catch((failure: unknown) => {
      if (active) setError(errorMessage(failure));
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [token, mail.id]);
  function saved(card: RegisteredMailCard): void {
    setCards((current) => [...current.filter((item) => item.id !== card.id), card]);
    setSelected(card);
  }
  return <div className="fixed inset-0 z-50 overflow-y-auto bg-black/40 p-6">
    <section aria-label="Cartoline della raccomandata" aria-modal="true" className="mx-auto max-w-5xl rounded-2xl bg-white p-6 shadow-xl" role="dialog">
      <div className="flex justify-between gap-4">
        <h2 className="text-xl font-semibold">Cartoline · {mail.recipient_name}</h2>
        <button className="btn-secondary" onClick={onClose} type="button">Chiudi cartoline</button>
      </div>
      <p className="my-3 text-sm text-gray-600">Tracking {mail.tracking_number ?? "-"}. Stesso documento visibile in Utenze. La scansione non determina consegna o annualità.</p>
      {loading ? <p role="status">Caricamento cartoline...</p> : <ul>
        {cards.map((card) => <li key={card.id}><button className="my-1 text-[#1D4E35] underline" onClick={() => setSelected(card)} type="button">{card.filename} · scansione {card.scanned_on}</button></li>)}
      </ul>}
      {!loading && cards.length === 0 ? <p>Nessuna cartolina salvata.</p> : null}
      {error ? <p className="my-3 text-red-700" role="alert">{error}</p> : null}
      {canUpload ? <CardUploadForm loading={loading} mail={mail} onSaved={saved} token={token} /> : <p className="my-3 text-sm">Il caricamento richiede permessi di modifica e un contribuente associato senza anomalie.</p>}
      {selected ? <CardPreview card={selected} mailId={mail.id} token={token} /> : null}
    </section>
  </div>;
}

export function RegisteredMailCards({ token, mail, canEdit }: {
  token: string | null; mail: RuoloTributiRegisteredMailResponse; canEdit: boolean;
}) {
  const [open, setOpen] = useState(false);
  if (!token) return null;
  return <>
    <button className="mt-2 block text-xs font-semibold text-[#1D4E35] hover:underline" onClick={() => setOpen(true)} type="button">Cartoline scansionate</button>
    {open ? <CardsDialog canEdit={canEdit} mail={mail} onClose={() => setOpen(false)} token={token} /> : null}
  </>;
}
