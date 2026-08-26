"use client";

import type { RefObject } from "react";

import type {
  GisCatalogChangeRequestType,
  GisCatalogLayer,
  GisCatalogLayerFeature,
} from "@/types/gis";

import { FeatureSelector } from "./feature-selector";
import { readableValue, type GuidedChangeDraft } from "./guided-workflow";

const changeTypeLabels: Record<GisCatalogChangeRequestType, string> = {
  attribute_update: "Correggi un dato",
  geometry_update: "Correggi la posizione o la forma",
  feature_create: "Aggiungi un nuovo elemento",
  feature_delete: "Chiedi di eliminare un elemento",
};

type HeadingRef = RefObject<HTMLHeadingElement>;
type DraftFieldChange = (key: keyof GuidedChangeDraft, value: string) => void;
type ChangeTypeStepProps = {
  headingRef: HeadingRef;
  token: string;
  layer: GisCatalogLayer;
  draft: GuidedChangeDraft;
  error: string | null;
  initialFeatureId?: string;
  editing: boolean;
  onChangeType: (changeType: GisCatalogChangeRequestType) => void;
  onSelectFeature: (feature: GisCatalogLayerFeature | null) => void;
  onContinue: () => void;
  onCancel?: () => void;
};
type ChangeDetailsStepProps = {
  headingRef: HeadingRef;
  draft: GuidedChangeDraft;
  fields: string[];
  beforeValue: unknown;
  selectedLabel: string;
  error: string | null;
  editing: boolean;
  onFieldChange: DraftFieldChange;
  onBack: () => void;
  onReview: () => void;
  onCancel?: () => void;
};

function WizardError({ error }: { error: string | null }) {
  if (!error) return null;
  return (
    <p className="mt-3 text-sm font-medium text-red-700" role="alert">
      {error}
    </p>
  );
}

function EditCancelButton({
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

function ChangeTypeField({
  changeType,
  onChange,
}: {
  changeType: GisCatalogChangeRequestType;
  onChange: (changeType: GisCatalogChangeRequestType) => void;
}) {
  return (
    <label className="mt-4 block text-sm font-semibold text-gray-800">
      Tipo di correzione
      <select
        className="form-control mt-2 text-base"
        value={changeType}
        onChange={(event) =>
          onChange(event.target.value as GisCatalogChangeRequestType)
        }
      >
        {Object.entries(changeTypeLabels).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}

function FeatureChoice({
  token,
  layer,
  draft,
  initialFeatureId,
  onSelect,
}: {
  token: string;
  layer: GisCatalogLayer;
  draft: GuidedChangeDraft;
  initialFeatureId?: string;
  onSelect: (feature: GisCatalogLayerFeature | null) => void;
}) {
  if (draft.changeType === "feature_create") {
    return (
      <p className="mt-4 rounded-2xl bg-[#f4f0d0] p-4 text-sm text-[#59612f]">
        Il nuovo elemento sara creato solo dopo approvazione e applicazione da
        parte di un responsabile.
      </p>
    );
  }
  return (
    <div className="mt-4">
      <FeatureSelector
        token={token}
        layer={layer}
        selectedId={draft.featureId}
        initialFeatureId={initialFeatureId}
        onSelect={onSelect}
      />
    </div>
  );
}

export function ChangeTypeStep({
  headingRef,
  token,
  layer,
  draft,
  error,
  initialFeatureId,
  editing,
  onChangeType,
  onSelectFeature,
  onContinue,
  onCancel,
}: ChangeTypeStepProps) {
  return (
    <>
      <h4 ref={headingRef} tabIndex={-1} className="text-lg font-semibold text-gray-950">
        Che tipo di correzione vuoi proporre?
      </h4>
      <ChangeTypeField
        changeType={draft.changeType}
        onChange={onChangeType}
      />
      <FeatureChoice
        token={token}
        layer={layer}
        draft={draft}
        initialFeatureId={initialFeatureId}
        onSelect={onSelectFeature}
      />
      <WizardError error={error} />
      <div className="mt-4 flex flex-wrap gap-2">
        <button className="btn-primary" type="button" onClick={onContinue}>
          Continua
        </button>
        <EditCancelButton editing={editing} onCancel={onCancel} />
      </div>
    </>
  );
}

function AttributeUpdateFields({
  draft,
  fields,
  beforeValue,
  onFieldChange,
}: {
  draft: GuidedChangeDraft;
  fields: string[];
  beforeValue: unknown;
  onFieldChange: DraftFieldChange;
}) {
  if (draft.changeType !== "attribute_update") return null;
  return (
    <div className="mt-4 grid gap-4 md:grid-cols-2">
      <label className="text-sm font-semibold text-gray-800">
        Dato da correggere
        <select
          className="form-control mt-2 text-base"
          value={draft.fieldName}
          onChange={(event) => onFieldChange("fieldName", event.target.value)}
        >
          <option value="">Scegli un campo</option>
          {fields.map((field) => (
            <option key={field} value={field}>
              {field}
            </option>
          ))}
        </select>
      </label>
      <div className="rounded-2xl bg-gray-50 p-4 text-sm">
        <p className="font-semibold text-gray-500">Valore attuale</p>
        <p className="mt-2 text-gray-950">{readableValue(beforeValue)}</p>
      </div>
      <label className="text-sm font-semibold text-gray-800 md:col-span-2">
        Nuovo valore
        <input
          className="form-control mt-2 text-base"
          value={draft.newValue}
          onChange={(event) => onFieldChange("newValue", event.target.value)}
        />
      </label>
    </div>
  );
}

function FeatureCreateFields({
  draft,
  onFieldChange,
}: {
  draft: GuidedChangeDraft;
  onFieldChange: DraftFieldChange;
}) {
  if (draft.changeType !== "feature_create") return null;
  return (
    <div className="mt-4 grid gap-4 md:grid-cols-2">
      <label className="text-sm font-semibold text-gray-800">
        Nome del dato
        <input
          className="form-control mt-2 text-base"
          value={draft.propertyName}
          onChange={(event) => onFieldChange("propertyName", event.target.value)}
          placeholder="Es. nome"
        />
      </label>
      <label className="text-sm font-semibold text-gray-800">
        Valore
        <input
          className="form-control mt-2 text-base"
          value={draft.propertyValue}
          onChange={(event) => onFieldChange("propertyValue", event.target.value)}
        />
      </label>
    </div>
  );
}

function GeometryFields({
  draft,
  onFieldChange,
}: {
  draft: GuidedChangeDraft;
  onFieldChange: DraftFieldChange;
}) {
  if (!["geometry_update", "feature_create"].includes(draft.changeType)) {
    return null;
  }
  return (
    <label className="mt-4 block text-sm font-semibold text-gray-800">
      Coordinate X e Y
      <textarea
        className="form-control mt-2 min-h-32 font-mono text-sm"
        value={draft.coordinates}
        onChange={(event) => onFieldChange("coordinates", event.target.value)}
        placeholder={"8.4001, 39.9001\n8.4010, 39.9010"}
      />
      <span className="mt-2 block font-normal text-gray-500">
        Inserisci una coppia per riga. Per linee servono almeno due righe, per
        poligoni almeno tre.
      </span>
    </label>
  );
}

function DeletionNotice({
  changeType,
  selectedLabel,
}: {
  changeType: GisCatalogChangeRequestType;
  selectedLabel: string;
}) {
  if (changeType !== "feature_delete") return null;
  return (
    <p className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
      Stai proponendo l&apos;eliminazione di {selectedLabel}. L&apos;elemento non
      sara eliminato finche un responsabile non approva e applica la richiesta.
    </p>
  );
}

function JustificationField({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="mt-4 block text-sm font-semibold text-gray-800">
      Motivazione
      <textarea
        className="form-control mt-2 min-h-24 text-base"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Indica il rilievo, il documento o il motivo della correzione."
      />
    </label>
  );
}

function ChangeDetailsActions({
  editing,
  onBack,
  onReview,
  onCancel,
}: {
  editing: boolean;
  onBack: () => void;
  onReview: () => void;
  onCancel?: () => void;
}) {
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      <button className="btn-secondary" type="button" onClick={onBack}>
        Indietro
      </button>
      <button className="btn-primary" type="button" onClick={onReview}>
        Rivedi richiesta
      </button>
      <EditCancelButton editing={editing} onCancel={onCancel} />
    </div>
  );
}

export function ChangeDetailsStep({
  headingRef,
  draft,
  fields,
  beforeValue,
  selectedLabel,
  error,
  editing,
  onFieldChange,
  onBack,
  onReview,
  onCancel,
}: ChangeDetailsStepProps) {
  return (
    <>
      <h4 ref={headingRef} tabIndex={-1} className="text-lg font-semibold text-gray-950">
        Descrivi la correzione
      </h4>
      <AttributeUpdateFields
        draft={draft}
        fields={fields}
        beforeValue={beforeValue}
        onFieldChange={onFieldChange}
      />
      <FeatureCreateFields draft={draft} onFieldChange={onFieldChange} />
      <GeometryFields draft={draft} onFieldChange={onFieldChange} />
      <DeletionNotice
        changeType={draft.changeType}
        selectedLabel={selectedLabel}
      />
      <JustificationField
        value={draft.justification}
        onChange={(value) => onFieldChange("justification", value)}
      />
      <WizardError error={error} />
      <ChangeDetailsActions
        editing={editing}
        onBack={onBack}
        onReview={onReview}
        onCancel={onCancel}
      />
    </>
  );
}

function AttributeChangeReview({
  draft,
  beforeValue,
}: {
  draft: GuidedChangeDraft;
  beforeValue: unknown;
}) {
  if (draft.changeType !== "attribute_update") return null;
  return (
    <>
      <div>
        <dt className="font-semibold text-gray-500">Prima</dt>
        <dd className="mt-1 text-gray-950">
          {draft.fieldName}: {readableValue(beforeValue)}
        </dd>
      </div>
      <div>
        <dt className="font-semibold text-gray-500">Dopo</dt>
        <dd className="mt-1 text-gray-950">
          {draft.fieldName}: {draft.newValue.trim()}
        </dd>
      </div>
    </>
  );
}

function changeSubmitLabel(busy: boolean, editing: boolean): string {
  if (busy) return "Invio...";
  return editing ? "Conferma aggiornamento" : "Conferma e invia";
}

function ChangeReviewSummary({
  draft,
  beforeValue,
  selectedLabel,
}: {
  draft: GuidedChangeDraft;
  beforeValue: unknown;
  selectedLabel: string;
}) {
  return (
    <dl className="mt-4 grid gap-3 rounded-2xl bg-[#f7faf7] p-4 text-sm">
      <div>
        <dt className="font-semibold text-gray-500">Operazione</dt>
        <dd className="mt-1 text-gray-950">
          {changeTypeLabels[draft.changeType]}
        </dd>
      </div>
      <div>
        <dt className="font-semibold text-gray-500">Elemento</dt>
        <dd className="mt-1 text-gray-950">{selectedLabel}</dd>
      </div>
      <AttributeChangeReview draft={draft} beforeValue={beforeValue} />
      <div>
        <dt className="font-semibold text-gray-500">Motivazione</dt>
        <dd className="mt-1 whitespace-pre-wrap text-gray-950">
          {draft.justification.trim()}
        </dd>
      </div>
    </dl>
  );
}

function ChangeReviewActions({
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
        {changeSubmitLabel(busy, editing)}
      </button>
    </div>
  );
}

export function ChangeReviewStep({
  headingRef,
  draft,
  beforeValue,
  selectedLabel,
  busy,
  editing,
  onBack,
  onSubmit,
}: {
  headingRef: HeadingRef;
  draft: GuidedChangeDraft;
  beforeValue: unknown;
  selectedLabel: string;
  busy: boolean;
  editing: boolean;
  onBack: () => void;
  onSubmit: () => void;
}) {
  return (
    <div aria-live="polite">
      <h4 ref={headingRef} tabIndex={-1} className="text-lg font-semibold text-gray-950">
        Controlla le conseguenze
      </h4>
      <ChangeReviewSummary
        draft={draft}
        beforeValue={beforeValue}
        selectedLabel={selectedLabel}
      />
      <p className="mt-3 text-sm text-gray-600">
        L&apos;invio non modifica subito il dato ufficiale. Un responsabile dovra
        esaminare e approvare la richiesta.
      </p>
      <ChangeReviewActions
        busy={busy}
        editing={editing}
        onBack={onBack}
        onSubmit={onSubmit}
      />
    </div>
  );
}
