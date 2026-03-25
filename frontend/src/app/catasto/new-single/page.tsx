"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { ProtectedPage } from "@/components/app/protected-page";
import { createCatastoSingleVisura, getCatastoComuni } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatastoComune, CatastoSingleVisuraPayload } from "@/types/api";

const DEFAULT_VALUES: CatastoSingleVisuraPayload = {
  comune: "",
  catasto: "Terreni e Fabbricati",
  sezione: "",
  foglio: "",
  particella: "",
  subalterno: "",
  tipo_visura: "Sintetica",
};

export default function CatastoNewSinglePage() {
  const router = useRouter();
  const [comuni, setComuni] = useState<CatastoComune[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CatastoSingleVisuraPayload>({
    defaultValues: DEFAULT_VALUES,
  });

  useEffect(() => {
    async function loadComuni(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const result = await getCatastoComuni(token);
        setComuni(result);
        setError(null);
        if (result[0]) {
          reset({ ...DEFAULT_VALUES, comune: result[0].nome });
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento comuni");
      }
    }

    void loadComuni();
  }, [reset]);

  async function onSubmit(values: CatastoSingleVisuraPayload): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setBusy(true);
    try {
      const batch = await createCatastoSingleVisura(token, {
        ...values,
        sezione: values.sezione?.trim() || undefined,
        subalterno: values.subalterno?.trim() || undefined,
      });
      setError(null);
      router.push(`/catasto/batches/${batch.id}`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Errore avvio visura singola");
      setBusy(false);
    }
  }

  return (
    <ProtectedPage
      title="Visura singola"
      description="Compila una richiesta puntuale, valida i dati catastali e avvia subito il worker."
      breadcrumb="Catasto / Visura singola"
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <form className="panel-card" onSubmit={(event) => void handleSubmit(onSubmit)(event)}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label className="space-y-2 xl:col-span-2">
            <span className="label-caption">Comune</span>
            <select className="form-control" {...register("comune", { required: "Seleziona un comune" })}>
              <option value="">Seleziona comune</option>
              {comuni.map((comune) => (
                <option key={comune.id} value={comune.nome}>
                  {comune.nome}
                </option>
              ))}
            </select>
            {errors.comune ? <p className="text-xs text-red-600">{errors.comune.message}</p> : null}
          </label>

          <label className="space-y-2">
            <span className="label-caption">Catasto</span>
            <select className="form-control" {...register("catasto", { required: true })}>
              <option value="Terreni">Terreni</option>
              <option value="Terreni e Fabbricati">Terreni e Fabbricati</option>
            </select>
          </label>

          <label className="space-y-2">
            <span className="label-caption">Foglio</span>
            <input
              className="form-control"
              inputMode="numeric"
              placeholder="Es. 5"
              {...register("foglio", {
                required: "Foglio obbligatorio",
                pattern: { value: /^\d+$/, message: "Inserisci un valore numerico" },
              })}
            />
            {errors.foglio ? <p className="text-xs text-red-600">{errors.foglio.message}</p> : null}
          </label>

          <label className="space-y-2">
            <span className="label-caption">Particella</span>
            <input
              className="form-control"
              inputMode="numeric"
              placeholder="Es. 120"
              {...register("particella", {
                required: "Particella obbligatoria",
                pattern: { value: /^\d+$/, message: "Inserisci un valore numerico" },
              })}
            />
            {errors.particella ? <p className="text-xs text-red-600">{errors.particella.message}</p> : null}
          </label>

          <label className="space-y-2">
            <span className="label-caption">Subalterno</span>
            <input
              className="form-control"
              inputMode="numeric"
              placeholder="Opzionale"
              {...register("subalterno", {
                pattern: { value: /^\d*$/, message: "Solo valori numerici" },
              })}
            />
            {errors.subalterno ? <p className="text-xs text-red-600">{errors.subalterno.message}</p> : null}
          </label>

          <label className="space-y-2">
            <span className="label-caption">Sezione</span>
            <input className="form-control" placeholder="Opzionale" {...register("sezione")} />
          </label>

          <label className="space-y-2">
            <span className="label-caption">Tipo visura</span>
            <select className="form-control" {...register("tipo_visura", { required: true })}>
              <option value="Sintetica">Sintetica</option>
              <option value="Completa">Completa</option>
            </select>
          </label>
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button className="btn-primary" disabled={busy || comuni.length === 0} type="submit">
            {busy ? "Avvio in corso..." : "Avvia visura singola"}
          </button>
          <p className="text-xs text-gray-400">
            La richiesta crea un batch da una sola riga e parte subito se le credenziali SISTER sono presenti.
          </p>
        </div>
      </form>
    </ProtectedPage>
  );
}
