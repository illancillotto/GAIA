import { useCallback, useEffect, useState } from "react";

import { searchAnagraficaSubjects } from "@/lib/api";
import {
  capacitasGetRptCertificatoLink,
  catastoGetParticella,
  catastoGetParticellaAnomalie,
  catastoGetParticellaConsorzio,
  catastoGetParticellaHistory,
  catastoGetParticellaUtenze,
  catastoSyncParticellaCapacitas,
  catastoUpdateAnomalia,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  CatAnomalia,
  CatParticellaConsorzio,
  CatParticellaDetail,
  CatParticellaHistory,
  CatUtenzaIrrigua,
} from "@/types/catasto";

import { normalizeIdentifier, resolveUtenzaCertContext } from "./particella-detail-helpers";

type ParticellaData = {
  item: CatParticellaDetail | null;
  consorzio: CatParticellaConsorzio | null;
  history: CatParticellaHistory[];
  utenze: CatUtenzaIrrigua[];
  anomalie: CatAnomalia[];
};

type RelatedData = Omit<ParticellaData, "item">;

async function fetchRelatedData(token: string, particellaId: string, anno: number): Promise<RelatedData> {
  const [consorzio, history, utenze, anomalie] = await Promise.all([
    catastoGetParticellaConsorzio(token, particellaId),
    catastoGetParticellaHistory(token, particellaId),
    catastoGetParticellaUtenze(token, particellaId, { anno }),
    catastoGetParticellaAnomalie(token, particellaId, { anno }),
  ]);
  return { consorzio, history, utenze, anomalie };
}

async function fetchParticellaData(token: string, particellaId: string, anno: number): Promise<ParticellaData> {
  const [item, related] = await Promise.all([
    catastoGetParticella(token, particellaId),
    fetchRelatedData(token, particellaId, anno),
  ]);
  return { item, ...related };
}

function latestAvailableYear(utenze: CatUtenzaIrrigua[], anomalie: CatAnomalia[]): number | null {
  const years = [...utenze, ...anomalie]
    .map((entry) => entry.anno_campagna)
    .filter((year): year is number => typeof year === "number" && Number.isFinite(year));
  const latest = Math.max(...years, -Infinity);
  return Number.isFinite(latest) ? latest : null;
}

async function findFallbackYear(token: string, particellaId: string): Promise<number | null> {
  const [utenze, anomalie] = await Promise.all([
    catastoGetParticellaUtenze(token, particellaId),
    catastoGetParticellaAnomalie(token, particellaId),
  ]);
  return latestAvailableYear(utenze, anomalie);
}

function useParticellaData(particellaId: string) {
  const [data, setData] = useState<ParticellaData>({
    item: null,
    consorzio: null,
    history: [],
    utenze: [],
    anomalie: [],
  });
  const [anno, setAnno] = useState(new Date().getFullYear());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;
      setIsLoading(true);
      try {
        const nextData = await fetchParticellaData(token, particellaId, anno);
        const currentYear = new Date().getFullYear();
        if (anno === currentYear && nextData.utenze.length === 0 && nextData.anomalie.length === 0) {
          const fallbackYear = await findFallbackYear(token, particellaId);
          if (fallbackYear !== null && fallbackYear !== anno) {
            setAnno(fallbackYear);
            return;
          }
        }
        setData(nextData);
        setError(null);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Errore caricamento particella");
      } finally {
        setIsLoading(false);
      }
    }
    void load();
  }, [anno, particellaId]);

  const setRelatedData = useCallback((related: RelatedData) => {
    setData((current) => ({ ...current, ...related }));
  }, []);
  const setItem = useCallback((item: CatParticellaDetail) => {
    setData((current) => ({ ...current, item }));
  }, []);
  const setAnomalie = useCallback((anomalie: CatAnomalia[]) => {
    setData((current) => ({ ...current, anomalie }));
  }, []);

  return { ...data, anno, error, isLoading, setAnno, setAnomalie, setError, setItem, setRelatedData };
}

function useCapacitasActions(particellaId: string, data: ReturnType<typeof useParticellaData>) {
  const [syncBusy, setSyncBusy] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [capacitasLinkBusy, setCapacitasLinkBusy] = useState(false);
  const [capacitasLinkError, setCapacitasLinkError] = useState<string | null>(null);

  async function syncParticella(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setSyncBusy(true);
    setSyncMessage(null);
    data.setError(null);
    try {
      const response = await catastoSyncParticellaCapacitas(token, particellaId);
      data.setItem(response.particella);
      setSyncMessage(response.message);
      data.setRelatedData(await fetchRelatedData(token, particellaId, data.anno));
    } catch (cause) {
      data.setError(cause instanceof Error ? cause.message : "Errore sync particella Capacitas");
    } finally {
      setSyncBusy(false);
    }
  }

  const openCapacitasCertificato = useCallback(async (utenza: CatUtenzaIrrigua): Promise<void> => {
    const token = getStoredAccessToken();
    const cco = utenza.cco?.trim();
    if (!token || !cco) return;
    setCapacitasLinkBusy(true);
    setCapacitasLinkError(null);
    try {
      const context = resolveUtenzaCertContext(data.consorzio, utenza);
      const { url } = await capacitasGetRptCertificatoLink(token, cco, context);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (cause) {
      setCapacitasLinkError(cause instanceof Error ? cause.message : "Errore generazione link Capacitas");
    } finally {
      setCapacitasLinkBusy(false);
    }
  }, [data.consorzio]);

  return { capacitasLinkBusy, capacitasLinkError, openCapacitasCertificato, syncBusy, syncMessage, syncParticella };
}

function useSubjectQuickView() {
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [subjectLookupBusyId, setSubjectLookupBusyId] = useState<string | null>(null);
  const [subjectLookupError, setSubjectLookupError] = useState<string | null>(null);

  const openSubjectQuickView = useCallback(async (utenza: CatUtenzaIrrigua): Promise<void> => {
    if (utenza.subject_id) {
      setSubjectLookupError(null);
      setSelectedSubjectId(utenza.subject_id);
      return;
    }
    const token = getStoredAccessToken();
    const identifier = normalizeIdentifier(utenza.codice_fiscale);
    if (!token || !identifier) {
      setSubjectLookupError("Nessun soggetto GAIA collegato a questa utenza.");
      return;
    }
    setSubjectLookupBusyId(utenza.id);
    setSubjectLookupError(null);
    try {
      const result = await searchAnagraficaSubjects(token, identifier, 20);
      const matches = result.items.filter((item) =>
        [item.codice_fiscale, item.partita_iva].some((value) => normalizeIdentifier(value) === identifier),
      );
      if (matches.length === 1) setSelectedSubjectId(matches[0].id);
      else if (matches.length > 1) setSubjectLookupError("Identificatore fiscale associato a piu soggetti GAIA. Apri la scheda utenze per disambiguare.");
      else setSubjectLookupError("Nessun soggetto GAIA trovato per questo identificatore fiscale.");
    } catch (cause) {
      setSubjectLookupError(cause instanceof Error ? cause.message : "Errore apertura dettaglio soggetto");
    } finally {
      setSubjectLookupBusyId(null);
    }
  }, []);

  return { openSubjectQuickView, selectedSubjectId, setSelectedSubjectId, subjectLookupBusyId, subjectLookupError };
}

export function useParticellaDetailController(particellaId: string) {
  const data = useParticellaData(particellaId);
  const capacitas = useCapacitasActions(particellaId, data);
  const subject = useSubjectQuickView();
  const { anno, setAnomalie } = data;

  const updateAnomalia = useCallback(async (id: string, status: string): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token) return;
    await catastoUpdateAnomalia(token, id, { status });
    setAnomalie(await catastoGetParticellaAnomalie(token, particellaId, { anno }));
  }, [anno, particellaId, setAnomalie]);

  return { ...data, ...capacitas, ...subject, updateAnomalia };
}

export type ParticellaDetailController = ReturnType<typeof useParticellaDetailController>;
