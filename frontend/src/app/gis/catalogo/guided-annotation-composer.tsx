"use client";

import { useState } from "react";
import type { RefObject } from "react";

import type {
  GisCatalogAnnotation,
  GisCatalogAnnotationSaveInput,
  GisCatalogLayer,
  GisCatalogLayerFeature,
} from "@/types/gis";

import { FeatureSelector } from "./feature-selector";
import {
  useWizardStepFocus,
  WizardSteps,
  type WizardStep,
} from "./guided-workflow-shell";

type GuidedAnnotationComposerProps = {
  token: string;
  layer: GisCatalogLayer;
  annotation?: GisCatalogAnnotation | null;
  busy: boolean;
  onSubmit: (input: GisCatalogAnnotationSaveInput) => Promise<boolean>;
  onCancel?: () => void;
};

type AnnotationTargetStepProps = {
  headingRef: RefObject<HTMLHeadingElement>;
  token: string;
  layer: GisCatalogLayer;
  featureId: string;
  annotation?: GisCatalogAnnotation | null;
  onSelect: (feature: GisCatalogLayerFeature | null) => void;
  onContinue: () => void;
  onCancel?: () => void;
};

type AnnotationDetailsStepProps = {
  headingRef: RefObject<HTMLHeadingElement>;
  title: string;
  body: string;
  error: string | null;
  editing: boolean;
  onTitleChange: (value: string) => void;
  onBodyChange: (value: string) => void;
  onBack: () => void;
  onReview: () => void;
  onCancel?: () => void;
};

function AnnotationCancelButton({
  editing,
  onCancel,
}: {
  editing: boolean;
  onCancel?: () => void;
}) {
  if (!editing || !onCancel) return null;
  return (
    <button className="btn-secondary" type="button" onClick={onCancel}>
      Annulla modifica
    </button>
  );
}

function AnnotationTargetStep({
  headingRef,
  token,
  layer,
  featureId,
  annotation,
  onSelect,
  onContinue,
  onCancel,
}: AnnotationTargetStepProps) {
  const editing = Boolean(annotation);
  return (
    <>
      <h4 ref={headingRef} tabIndex={-1} className="text-lg font-semibold text-gray-950">
        Dove vuoi lasciare la nota?
      </h4>
      <p className="mt-1 text-sm text-gray-600">
        Puoi scegliere un elemento oppure lasciare una nota generale sulla
        mappa.
      </p>
      <div className="mt-4">
        <FeatureSelector
          token={token}
          layer={layer}
          selectedId={featureId}
          initialFeatureId={annotation?.feature_id ?? undefined}
          allowWholeLayer
          disabled={editing}
          onSelect={onSelect}
        />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button className="btn-primary" type="button" onClick={onContinue}>
          Continua
        </button>
        <AnnotationCancelButton editing={editing} onCancel={onCancel} />
      </div>
    </>
  );
}

function AnnotationDetailsFields({
  title,
  body,
  onTitleChange,
  onBodyChange,
}: Pick<
  AnnotationDetailsStepProps,
  "title" | "body" | "onTitleChange" | "onBodyChange"
>) {
  return (
    <>
      <label className="mt-4 block text-sm font-semibold text-gray-800">
        Titolo breve
        <input
          className="form-control mt-2 text-base"
          value={title}
          onChange={(event) => onTitleChange(event.target.value)}
          placeholder="Es. Verificare condotta"
        />
      </label>
      <label className="mt-4 block text-sm font-semibold text-gray-800">
        Descrizione
        <textarea
          className="form-control mt-2 min-h-28 text-base"
          value={body}
          onChange={(event) => onBodyChange(event.target.value)}
          placeholder="Spiega cosa hai rilevato e cosa dovrebbe essere controllato."
        />
      </label>
    </>
  );
}

function AnnotationDetailsActions({
  editing,
  onBack,
  onReview,
  onCancel,
}: Pick<
  AnnotationDetailsStepProps,
  "editing" | "onBack" | "onReview" | "onCancel"
>) {
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      <button className="btn-secondary" type="button" onClick={onBack}>
        Indietro
      </button>
      <button className="btn-primary" type="button" onClick={onReview}>
        Rivedi nota
      </button>
      <AnnotationCancelButton editing={editing} onCancel={onCancel} />
    </div>
  );
}

function AnnotationDetailsStep(props: AnnotationDetailsStepProps) {
  return (
    <>
      <h4 ref={props.headingRef} tabIndex={-1} className="text-lg font-semibold text-gray-950">
        Descrivi quello che hai osservato
      </h4>
      <AnnotationDetailsFields {...props} />
      {props.error ? (
        <p className="mt-3 text-sm font-medium text-red-700" role="alert">
          {props.error}
        </p>
      ) : null}
      <AnnotationDetailsActions {...props} />
    </>
  );
}

function AnnotationReviewSummary({
  featureLabel,
  title,
  body,
}: {
  featureLabel: string;
  title: string;
  body: string;
}) {
  return (
    <dl className="mt-4 grid gap-3 rounded-2xl bg-[#f7faf7] p-4 text-sm">
      <div>
        <dt className="font-semibold text-gray-500">Elemento</dt>
        <dd className="mt-1 text-gray-900">{featureLabel}</dd>
      </div>
      <div>
        <dt className="font-semibold text-gray-500">Titolo</dt>
        <dd className="mt-1 text-gray-900">{title.trim()}</dd>
      </div>
      <div>
        <dt className="font-semibold text-gray-500">Descrizione</dt>
        <dd className="mt-1 whitespace-pre-wrap text-gray-900">{body.trim()}</dd>
      </div>
    </dl>
  );
}

function annotationSubmitLabel(busy: boolean, editing: boolean): string {
  if (busy) return "Salvataggio...";
  return editing ? "Conferma aggiornamento" : "Conferma e crea nota";
}

function AnnotationReviewActions({
  busy,
  editing,
  onBack,
  onSubmit,
}: {
  busy: boolean;
  editing: boolean;
  onBack: () => void;
  onSubmit: () => void;
}) {
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      <button
        className="btn-secondary"
        type="button"
        disabled={busy}
        onClick={onBack}
      >
        Correggi
      </button>
      <button
        className="btn-primary"
        type="button"
        disabled={busy}
        onClick={onSubmit}
      >
        {annotationSubmitLabel(busy, editing)}
      </button>
    </div>
  );
}

function AnnotationReviewStep({
  headingRef,
  featureLabel,
  title,
  body,
  busy,
  editing,
  onBack,
  onSubmit,
}: {
  headingRef: RefObject<HTMLHeadingElement>;
  featureLabel: string;
  title: string;
  body: string;
  busy: boolean;
  editing: boolean;
  onBack: () => void;
  onSubmit: () => void;
}) {
  return (
    <div aria-live="polite">
      <h4 ref={headingRef} tabIndex={-1} className="text-lg font-semibold text-gray-950">
        Controlla prima di inviare
      </h4>
      <AnnotationReviewSummary
        featureLabel={featureLabel}
        title={title}
        body={body}
      />
      <p className="mt-3 text-sm text-gray-600">
        La nota sara registrata nello storico GIS e potra essere presa in carico
        dagli operatori autorizzati.
      </p>
      <AnnotationReviewActions
        busy={busy}
        editing={editing}
        onBack={onBack}
        onSubmit={onSubmit}
      />
    </div>
  );
}

function annotationFeatureLabel(
  feature: GisCatalogLayerFeature | null,
  featureId: string,
): string {
  return feature?.label || featureId || "Intera mappa";
}

function annotationSaveInput(
  featureId: string,
  title: string,
  body: string,
): GisCatalogAnnotationSaveInput {
  return {
    featureId,
    title: title.trim(),
    body: body.trim(),
    attachmentRefs: [],
  };
}

function useGuidedAnnotationState({
  annotation,
  onSubmit,
}: Pick<GuidedAnnotationComposerProps, "annotation" | "onSubmit">) {
  const [step, setStep] = useState<WizardStep>(1);
  const headingRef = useWizardStepFocus(step);
  const [feature, setFeature] = useState<GisCatalogLayerFeature | null>(null);
  const [featureId, setFeatureId] = useState(annotation?.feature_id ?? "");
  const [title, setTitle] = useState(annotation?.title ?? "");
  const [body, setBody] = useState(annotation?.body ?? "");
  const [error, setError] = useState<string | null>(null);

  function selectFeature(selected: GisCatalogLayerFeature | null) {
    setFeature(selected);
    setFeatureId(selected?.feature_id ?? "");
  }

  function review() {
    if (!title.trim() || !body.trim()) {
      setError("Inserisci un titolo breve e descrivi la nota.");
      return;
    }
    setError(null);
    setStep(3);
  }

  async function submit() {
    const saved = await onSubmit(annotationSaveInput(featureId, title, body));
    if (!saved || annotation) return;
    setFeature(null);
    setFeatureId("");
    setTitle("");
    setBody("");
    setStep(1);
  }

  return {
    body,
    error,
    featureId,
    featureLabel: annotationFeatureLabel(feature, featureId),
    headingRef,
    review,
    selectFeature,
    setBody,
    setStep,
    setTitle,
    step,
    submit,
    title,
  };
}

export function GuidedAnnotationComposer(props: GuidedAnnotationComposerProps) {
  const { token, layer, annotation, busy, onCancel } = props;
  const state = useGuidedAnnotationState(props);
  const editing = Boolean(annotation);

  return (
    <div className="mt-4 rounded-2xl border border-[#dce8de] bg-white p-4">
      <WizardSteps step={state.step} />
      {state.step === 1 ? (
        <AnnotationTargetStep
          headingRef={state.headingRef}
          token={token}
          layer={layer}
          featureId={state.featureId}
          annotation={annotation}
          onSelect={state.selectFeature}
          onContinue={() => state.setStep(2)}
          onCancel={onCancel}
        />
      ) : null}
      {state.step === 2 ? (
        <AnnotationDetailsStep
          headingRef={state.headingRef}
          title={state.title}
          body={state.body}
          error={state.error}
          editing={editing}
          onTitleChange={state.setTitle}
          onBodyChange={state.setBody}
          onBack={() => state.setStep(1)}
          onReview={state.review}
          onCancel={onCancel}
        />
      ) : null}
      {state.step === 3 ? (
        <AnnotationReviewStep
          headingRef={state.headingRef}
          featureLabel={state.featureLabel}
          title={state.title}
          body={state.body}
          busy={busy}
          editing={editing}
          onBack={() => state.setStep(2)}
          onSubmit={() => void state.submit()}
        />
      ) : null}
    </div>
  );
}
