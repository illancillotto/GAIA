"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";

import { createUtenzeSubject, previewLookupUtenzeAnprByCf } from "@/lib/api";
import type { UtenzeSubjectCreateInput } from "@/types/api";

function normalizeCfForAnpr(value: string): string {
  return value.replace(/\s+/g, "").toUpperCase();
}

function normalizeIdentifierPart(value: string): string {
  return value
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^A-Za-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .replace(/_+/g, "_");
}

function deriveArchiveLetter(value: string): string {
  const normalized = value
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase();
  const firstLetter = normalized.match(/[A-Z]/);
  return firstLetter?.[0] ?? "";
}

function buildSourceNameRaw(
  createType: "person" | "company",
  values: {
    personSurname: string;
    personName: string;
    personCf: string;
    companyName: string;
    companyVat: string;
  },
): string {
  const parts = createType === "person"
    ? [values.personSurname, values.personName, values.personCf]
    : [values.companyName, values.companyVat];

  return parts.map(normalizeIdentifierPart).filter(Boolean).join("_");
}

function strOrNull(raw: string): string | null {
  const t = raw.trim();
  return t || null;
}

const ANPR_STATO_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "Non impostato" },
  { value: "alive", label: "Presente / vivente" },
  { value: "deceased", label: "Decesso" },
  { value: "not_found_anpr", label: "Non trovato ANPR" },
  { value: "cancelled_anpr", label: "Annullato ANPR" },
  { value: "error", label: "Errore verifica" },
  { value: "unknown", label: "Non noto" },
];

function FormSection({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-[#dfe8df] bg-[#f9fbf9] px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#6B8A78]">{title}</p>
      {subtitle ? <p className="mt-1 text-xs text-gray-500">{subtitle}</p> : null}
      <div className="mt-4 space-y-4">{children}</div>
    </section>
  );
}

function FieldGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid gap-4 md:grid-cols-2">{children}</div>;
}

type UtenzeCreateSubjectTriggerProps = {
  token: string;
  onCreated?: () => void | Promise<void>;
  variant?: "primary" | "secondary";
  buttonClassName?: string;
  buttonContent?: ReactNode;
};

export function UtenzeCreateSubjectTrigger({
  token,
  onCreated,
  variant = "primary",
  buttonClassName = "",
  buttonContent,
}: UtenzeCreateSubjectTriggerProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [createType, setCreateType] = useState<"person" | "company">("person");

  const [sourceExternalId, setSourceExternalId] = useState("");
  const [requiresReview, setRequiresReview] = useState(false);
  const [sourceNameRawOverride, setSourceNameRawOverride] = useState("");

  const [personSurname, setPersonSurname] = useState("");
  const [personName, setPersonName] = useState("");
  const [personCf, setPersonCf] = useState("");
  const [personBirthDate, setPersonBirthDate] = useState("");
  const [personComuneNascita, setPersonComuneNascita] = useState("");
  const [personIndirizzo, setPersonIndirizzo] = useState("");
  const [personComuneResidenza, setPersonComuneResidenza] = useState("");
  const [personCap, setPersonCap] = useState("");
  const [personEmail, setPersonEmail] = useState("");
  const [personTelefono, setPersonTelefono] = useState("");
  const [personNote, setPersonNote] = useState("");
  const [resolvedAnprId, setResolvedAnprId] = useState<string | null>(null);
  const [anprLookupMessage, setAnprLookupMessage] = useState<string | null>(null);
  const [anprLookupLoading, setAnprLookupLoading] = useState(false);
  const [personStatoAnpr, setPersonStatoAnpr] = useState("");
  const [personDataDecesso, setPersonDataDecesso] = useState("");
  const [personLuogoDecesso, setPersonLuogoDecesso] = useState("");

  const [companyName, setCompanyName] = useState("");
  const [companyVat, setCompanyVat] = useState("");
  const [companyCf, setCompanyCf] = useState("");
  const [companyFormaGiuridica, setCompanyFormaGiuridica] = useState("");
  const [companySedeLegale, setCompanySedeLegale] = useState("");
  const [companyComuneSede, setCompanyComuneSede] = useState("");
  const [companyCap, setCompanyCap] = useState("");
  const [companyEmailPec, setCompanyEmailPec] = useState("");
  const [companyTelefono, setCompanyTelefono] = useState("");
  const [companyNote, setCompanyNote] = useState("");

  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [duplicateCfMessage, setDuplicateCfMessage] = useState<string | null>(null);

  const derivedLetter = useMemo(
    () => deriveArchiveLetter(createType === "person" ? personSurname : companyName),
    [companyName, createType, personSurname],
  );

  const derivedSourceNameRaw = useMemo(
    () =>
      buildSourceNameRaw(createType, {
        personSurname,
        personName,
        personCf,
        companyName,
        companyVat,
      }),
    [companyName, companyVat, createType, personCf, personName, personSurname],
  );

  const effectiveSourceNameRaw = useMemo(() => {
    const o = sourceNameRawOverride.trim();
    return o || derivedSourceNameRaw;
  }, [derivedSourceNameRaw, sourceNameRawOverride]);

  useEffect(() => {
    if (!modalOpen && !duplicateCfMessage) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;

      if (duplicateCfMessage) {
        setDuplicateCfMessage(null);
        return;
      }

      if (modalOpen) {
        setModalOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [duplicateCfMessage, modalOpen]);

  function resetFormFields() {
    setSourceExternalId("");
    setRequiresReview(false);
    setSourceNameRawOverride("");
    setPersonSurname("");
    setPersonName("");
    setPersonCf("");
    setPersonBirthDate("");
    setPersonComuneNascita("");
    setPersonIndirizzo("");
    setPersonComuneResidenza("");
    setPersonCap("");
    setPersonEmail("");
    setPersonTelefono("");
    setPersonNote("");
    setResolvedAnprId(null);
    setAnprLookupMessage(null);
    setAnprLookupLoading(false);
    setPersonStatoAnpr("");
    setPersonDataDecesso("");
    setPersonLuogoDecesso("");
    setCompanyName("");
    setCompanyVat("");
    setCompanyCf("");
    setCompanyFormaGiuridica("");
    setCompanySedeLegale("");
    setCompanyComuneSede("");
    setCompanyCap("");
    setCompanyEmailPec("");
    setCompanyTelefono("");
    setCompanyNote("");
    setSaveError(null);
  }

  function openModal() {
    setSaveError(null);
    setDuplicateCfMessage(null);
    setModalOpen(true);
  }

  async function fetchAnprPreview() {
    const cfNorm = normalizeCfForAnpr(personCf);
    if (cfNorm.length < 14) {
      setAnprLookupMessage("Completa il codice fiscale prima di interrogare ANPR (16 caratteri per CF italiano).");
      return;
    }
    setAnprLookupLoading(true);
    setAnprLookupMessage(null);
    try {
      const res = await previewLookupUtenzeAnprByCf(token, cfNorm);
      setResolvedAnprId(res.anpr_id?.trim() || null);
      if (res.stato_anpr) {
        setPersonStatoAnpr(res.stato_anpr);
      }
      if (res.data_decesso) {
        const raw = res.data_decesso;
        setPersonDataDecesso(raw.length >= 10 ? raw.slice(0, 10) : raw);
      }
      const suffix =
        typeof res.calls_made === "number" && res.calls_made > 0 ? ` · ${res.calls_made} chiamata/e PDND` : "";
      setAnprLookupMessage(`${res.message}${suffix}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Errore interrogazione ANPR";
      setAnprLookupMessage(message);
      setResolvedAnprId(null);
    } finally {
      setAnprLookupLoading(false);
    }
  }

  async function submit() {
    if (!effectiveSourceNameRaw || !derivedLetter) {
      setSaveError("Compila i dati principali dell'utente (nome/cognome o ragione sociale e identificativi) prima del salvataggio.");
      setDuplicateCfMessage(null);
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setDuplicateCfMessage(null);

    const payload: UtenzeSubjectCreateInput = {
      subject_type: createType,
      source_name_raw: effectiveSourceNameRaw,
      source_external_id: strOrNull(sourceExternalId),
      nas_folder_letter: derivedLetter || null,
      requires_review: requiresReview,
    };

    if (createType === "person") {
      payload.person = {
        cognome: personSurname,
        nome: personName,
        codice_fiscale: personCf,
        data_nascita: strOrNull(personBirthDate),
        comune_nascita: strOrNull(personComuneNascita),
        indirizzo: strOrNull(personIndirizzo),
        comune_residenza: strOrNull(personComuneResidenza),
        cap: strOrNull(personCap),
        email: strOrNull(personEmail),
        telefono: strOrNull(personTelefono),
        note: strOrNull(personNote),
        anpr_id: resolvedAnprId?.trim() || null,
        stato_anpr: strOrNull(personStatoAnpr),
        data_decesso: strOrNull(personDataDecesso),
        luogo_decesso_comune: strOrNull(personLuogoDecesso),
      };
    } else {
      payload.company = {
        ragione_sociale: companyName,
        partita_iva: companyVat,
        codice_fiscale: strOrNull(companyCf),
        forma_giuridica: strOrNull(companyFormaGiuridica),
        sede_legale: strOrNull(companySedeLegale),
        comune_sede: strOrNull(companyComuneSede),
        cap: strOrNull(companyCap),
        email_pec: strOrNull(companyEmailPec),
        telefono: strOrNull(companyTelefono),
        note: strOrNull(companyNote),
      };
    }

    try {
      await createUtenzeSubject(token, payload);
      setModalOpen(false);
      resetFormFields();
      await onCreated?.();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Errore creazione utente";
      if (message.toLowerCase().includes("codice fiscale")) {
        setDuplicateCfMessage(message);
      } else {
        setSaveError(message);
      }
    } finally {
      setIsSaving(false);
    }
  }

  const btnClass = `${variant === "primary" ? "btn-primary" : "btn-secondary"} ${buttonClassName}`.trim();

  return (
    <>
      <button className={btnClass} type="button" onClick={openModal}>
        {buttonContent ?? "Crea nuovo utente"}
      </button>

      {modalOpen ? (
        <div className="fixed inset-0 z-50 overscroll-contain bg-gray-950/35 backdrop-blur-[1px]">
          {/* Backdrop: separato dal contenuto così clic su card non chiude in bubble verso questo layer */}
          <button aria-label="Chiudi finestra nuovo utente" className="fixed inset-0 z-0" onClick={() => setModalOpen(false)} type="button" />
          <div className="relative z-10 flex min-h-full w-full items-start justify-center overflow-y-auto px-3 py-6 sm:items-center sm:px-4 sm:py-8">
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="utenze-create-subject-title"
              className="relative z-[1] my-auto mb-14 grid max-h-[min(88dvh,920px)] w-full max-w-4xl grid-rows-[auto_minmax(0,1fr)_auto] gap-0 overflow-hidden rounded-3xl border border-[#d9dfd6] bg-white shadow-2xl sm:mb-auto"
              onMouseDown={(e) => e.stopPropagation()}
              onPointerDown={(e) => e.stopPropagation()}
              onClick={(e) => e.stopPropagation()}
            >
            <div className="border-b border-[#edf2ed] px-5 py-4 sm:px-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="section-title" id="utenze-create-subject-title">
                    Nuovo utente
                  </p>
                  <p className="section-copy mt-1">
                    Campi allineati a <code className="rounded bg-gray-100 px-1 text-xs">ana_subjects</code>,{" "}
                    <code className="rounded bg-gray-100 px-1 text-xs">ana_persons</code> e{" "}
                    <code className="rounded bg-gray-100 px-1 text-xs">ana_companies</code>.
                  </p>
                </div>
                <button className="btn-secondary shrink-0" type="button" onClick={() => setModalOpen(false)}>
                  Chiudi
                </button>
              </div>
              {saveError ? <p className="mt-3 text-sm text-red-600">{saveError}</p> : null}
            </div>

            <div className="min-h-0 min-w-0 overflow-x-hidden overflow-y-auto overscroll-contain px-5 py-4 sm:px-6">
              <div className="space-y-5">
                <FormSection title="Soggetto (ana_subjects)" subtitle="Metadati scheda e collegamento archivio.">
                  <FieldGrid>
                    <label className="block text-sm font-medium text-gray-700">
                      Tipo anagrafica
                      <select
                        className="form-control mt-1"
                        value={createType}
                        onChange={(event) => {
                          const next = event.target.value as "person" | "company";
                          setCreateType(next);
                          if (next === "company") {
                            setResolvedAnprId(null);
                            setAnprLookupMessage(null);
                            setAnprLookupLoading(false);
                          }
                        }}
                      >
                        <option value="person">Persona fisica</option>
                        <option value="company">Persona giuridica</option>
                      </select>
                    </label>
                    <label className="flex flex-col gap-2 text-sm font-medium text-gray-700">
                      <span>Richiede revisione</span>
                      <span className="flex items-center gap-2 font-normal">
                        <input type="checkbox" checked={requiresReview} onChange={(e) => setRequiresReview(e.target.checked)} className="h-4 w-4 rounded border-gray-300" />
                        Segna la scheda per controllo operatore
                      </span>
                    </label>
                    <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                      ID esterno sorgente (source_external_id)
                      <input
                        className="form-control mt-1"
                        value={sourceExternalId}
                        onChange={(event) => setSourceExternalId(event.target.value)}
                        placeholder="Opzionale — es. codice gestionale esterno"
                        maxLength={128}
                      />
                    </label>
                    <p className="rounded-xl border border-[#dfe8df] bg-white px-3 py-2.5 text-xs leading-relaxed text-gray-600 md:col-span-2">
                      <span className="font-semibold text-gray-800">Percorso NAS ({`nas_folder_path`}): </span>
                      compilato dal backend come{" "}
                      <code className="rounded bg-[#f0f4f0] px-1 font-mono text-[11px]">
                        {"{UTENZE_NAS_ARCHIVE_ROOT o ANAGRAFICA_NAS_ARCHIVE_ROOT}/{lettera}/{source_name_raw}"}
                      </code>
                      , allineato alla struttura usata dall&apos;import archivio. Se manca la root in configurazione o lettera/nome cartella non sono validi,
                      il percorso resta vuoto e potrà essere valorizzato in seguito (es. job NAS).
                    </p>
                    <label className="block text-sm font-medium text-gray-700">
                      Lettera archivio (derivata)
                      <input className="form-control mt-1 bg-gray-50 text-gray-600" value={derivedLetter} readOnly placeholder="Auto" />
                    </label>
                    <label className="block text-sm font-medium text-gray-700">
                      Source name raw (generato)
                      <input className="form-control mt-1 bg-gray-50 text-gray-600" value={derivedSourceNameRaw} readOnly />
                    </label>
                    <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                      Source name raw — override manuale
                      <input
                        className="form-control mt-1"
                        value={sourceNameRawOverride}
                        onChange={(event) => setSourceNameRawOverride(event.target.value)}
                        placeholder="Lascia vuoto per usare il valore generato sopra"
                        maxLength={512}
                      />
                    </label>
                  </FieldGrid>
                </FormSection>

                {createType === "person" ? (
                  <>
                    <FormSection title="Anagrafica base (ana_persons)" subtitle="Dati anagrafici obbligatori e contatti.">
                      <FieldGrid>
                        <label className="block text-sm font-medium text-gray-700">
                          Cognome
                          <input className="form-control mt-1" value={personSurname} onChange={(event) => setPersonSurname(event.target.value)} maxLength={255} />
                        </label>
                        <label className="block text-sm font-medium text-gray-700">
                          Nome
                          <input className="form-control mt-1" value={personName} onChange={(event) => setPersonName(event.target.value)} maxLength={255} />
                        </label>
                        <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                          Codice fiscale
                          <input
                            className="form-control mt-1"
                            value={personCf}
                            onChange={(event) => {
                              const next = event.target.value.toUpperCase();
                              setPersonCf(next);
                              setResolvedAnprId(null);
                              setAnprLookupMessage(null);
                            }}
                            maxLength={32}
                          />
                        </label>
                        <label className="block text-sm font-medium text-gray-700">
                          Data di nascita
                          <input className="form-control mt-1" type="date" value={personBirthDate} onChange={(event) => setPersonBirthDate(event.target.value)} />
                        </label>
                        <label className="block text-sm font-medium text-gray-700">
                          Comune di nascita
                          <input className="form-control mt-1" value={personComuneNascita} onChange={(event) => setPersonComuneNascita(event.target.value)} maxLength={255} />
                        </label>
                        <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                          Indirizzo di residenza
                          <input className="form-control mt-1" value={personIndirizzo} onChange={(event) => setPersonIndirizzo(event.target.value)} maxLength={255} />
                        </label>
                        <label className="block text-sm font-medium text-gray-700">
                          Comune di residenza
                          <input className="form-control mt-1" value={personComuneResidenza} onChange={(event) => setPersonComuneResidenza(event.target.value)} maxLength={255} />
                        </label>
                        <label className="block text-sm font-medium text-gray-700">
                          CAP
                          <input className="form-control mt-1" value={personCap} onChange={(event) => setPersonCap(event.target.value)} maxLength={16} />
                        </label>
                        <label className="block text-sm font-medium text-gray-700">
                          Email
                          <input type="email" className="form-control mt-1" value={personEmail} onChange={(event) => setPersonEmail(event.target.value)} maxLength={255} />
                        </label>
                        <label className="block text-sm font-medium text-gray-700">
                          Telefono
                          <input className="form-control mt-1" value={personTelefono} onChange={(event) => setPersonTelefono(event.target.value)} maxLength={64} />
                        </label>
                        <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                          Note
                          <textarea className="form-control mt-1 min-h-[72px] resize-y" value={personNote} onChange={(event) => setPersonNote(event.target.value)} rows={3} />
                        </label>
                      </FieldGrid>
                    </FormSection>

                    <FormSection
                      title="ANPR e stato di vita"
                      subtitle="«Recupera dati» interroga PDND su questo codice fiscale e salva l&apos;id soggetto in automatico alla creazione. Richiede ruolo reviewer/admin/super_admin. Stato, data decesso e luogo restano modificabili a mano se serve."
                    >
                      <FieldGrid>
                        <div className="flex flex-wrap items-center gap-3 md:col-span-2">
                          <button
                            className="btn-secondary shrink-0"
                            disabled={
                              anprLookupLoading || isSaving || normalizeCfForAnpr(personCf).length < 14
                            }
                            type="button"
                            onClick={() => void fetchAnprPreview()}
                          >
                            {anprLookupLoading ? "Recupero in corso…" : "Recupera dati"}
                          </button>
                          {resolvedAnprId ? (
                            <span className="text-xs text-gray-600">
                              Id soggetto ANPR acquisito: <span className="font-mono text-gray-900">{resolvedAnprId}</span>
                            </span>
                          ) : (
                            <span className="text-xs text-gray-500">L&apos;id ANPR non è editabile: viene valorizzato solo dal recupero o lasciato vuoto.</span>
                          )}
                        </div>
                        {anprLookupMessage ? (
                          <p className="rounded-lg border border-[#dfe8df] bg-white px-3 py-2 text-xs text-gray-700 md:col-span-2">
                            {anprLookupMessage}
                          </p>
                        ) : null}
                        <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                          Stato ANPR (stato_anpr)
                          <select className="form-control mt-1" value={personStatoAnpr} onChange={(event) => setPersonStatoAnpr(event.target.value)}>
                            {ANPR_STATO_OPTIONS.map((opt, idx) => (
                              <option key={`${idx}-${opt.value}`} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="block text-sm font-medium text-gray-700">
                          Data decesso
                          <input className="form-control mt-1" type="date" value={personDataDecesso} onChange={(event) => setPersonDataDecesso(event.target.value)} />
                        </label>
                        <label className="block text-sm font-medium text-gray-700">
                          Comune decesso / luogo
                          <input className="form-control mt-1" value={personLuogoDecesso} onChange={(event) => setPersonLuogoDecesso(event.target.value)} maxLength={100} />
                        </label>
                      </FieldGrid>
                    </FormSection>
                  </>
                ) : (
                  <FormSection title="Società (ana_companies)" subtitle="Tutti i campi valorizzabili sulla persona giuridica.">
                    <FieldGrid>
                      <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                        Ragione sociale
                        <input className="form-control mt-1" value={companyName} onChange={(event) => setCompanyName(event.target.value)} maxLength={255} />
                      </label>
                      <label className="block text-sm font-medium text-gray-700">
                        Partita IVA
                        <input className="form-control mt-1" value={companyVat} onChange={(event) => setCompanyVat(event.target.value)} maxLength={32} />
                      </label>
                      <label className="block text-sm font-medium text-gray-700">
                        Codice fiscale società
                        <input className="form-control mt-1" value={companyCf} onChange={(event) => setCompanyCf(event.target.value.toUpperCase())} maxLength={32} />
                      </label>
                      <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                        Forma giuridica
                        <input className="form-control mt-1" value={companyFormaGiuridica} onChange={(event) => setCompanyFormaGiuridica(event.target.value)} maxLength={128} />
                      </label>
                      <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                        Sede legale (indirizzo)
                        <input className="form-control mt-1" value={companySedeLegale} onChange={(event) => setCompanySedeLegale(event.target.value)} maxLength={255} />
                      </label>
                      <label className="block text-sm font-medium text-gray-700">
                        Comune sede
                        <input className="form-control mt-1" value={companyComuneSede} onChange={(event) => setCompanyComuneSede(event.target.value)} maxLength={255} />
                      </label>
                      <label className="block text-sm font-medium text-gray-700">
                        CAP
                        <input className="form-control mt-1" value={companyCap} onChange={(event) => setCompanyCap(event.target.value)} maxLength={16} />
                      </label>
                      <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                        Email / PEC
                        <input type="email" className="form-control mt-1" value={companyEmailPec} onChange={(event) => setCompanyEmailPec(event.target.value)} maxLength={255} />
                      </label>
                      <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                        Telefono
                        <input className="form-control mt-1" value={companyTelefono} onChange={(event) => setCompanyTelefono(event.target.value)} maxLength={64} />
                      </label>
                      <label className="block text-sm font-medium text-gray-700 md:col-span-2">
                        Note
                        <textarea className="form-control mt-1 min-h-[72px] resize-y" value={companyNote} onChange={(event) => setCompanyNote(event.target.value)} rows={3} />
                      </label>
                    </FieldGrid>
                  </FormSection>
                )}
              </div>
            </div>

            <div className="border-t border-[#edf2ed] bg-white px-5 py-4 sm:px-6">
              <div className="flex flex-wrap justify-end gap-3">
                <button className="btn-secondary" type="button" onClick={() => setModalOpen(false)}>
                  Annulla
                </button>
                <button className="btn-primary" onClick={() => void submit()} type="button" disabled={isSaving}>
                  {isSaving ? "Salvataggio..." : "Crea utente"}
                </button>
              </div>
            </div>
          </div>
        </div>
        </div>
      ) : null}

      {duplicateCfMessage ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 px-4 py-6">
          <button aria-label="Chiudi avviso duplicato" className="absolute inset-0" onClick={() => setDuplicateCfMessage(null)} type="button" />
          <div className="relative z-10 w-full max-w-lg rounded-[28px] border border-red-100 bg-white p-6 shadow-[0_24px_64px_rgba(15,25,19,0.18)]">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-500">Codice fiscale duplicato</p>
            <h3 className="mt-2 text-xl font-medium text-gray-900">Utente gia presente nel registro</h3>
            <p className="mt-3 text-sm text-gray-600">{duplicateCfMessage}</p>
            <div className="mt-5 flex justify-end">
              <button className="btn-secondary" onClick={() => setDuplicateCfMessage(null)} type="button">
                Chiudi
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
