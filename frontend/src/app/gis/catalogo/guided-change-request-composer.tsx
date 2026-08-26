"use client";

import { useState } from "react";

import type {
  GisCatalogChangeRequest,
  GisCatalogChangeRequestSaveInput,
  GisCatalogChangeRequestType,
  GisCatalogLayer,
  GisCatalogLayerFeature,
} from "@/types/gis";

import {
  ChangeDetailsStep,
  ChangeReviewStep,
  ChangeTypeStep,
} from "./guided-change-request-steps";
import {
  buildGuidedChangeInput,
  coordinatesTextFromGeometry,
  emptyGuidedChangeDraft,
  guidedChangeValidation,
  guidedDraftFromChangeRequest,
  type GuidedChangeDraft,
} from "./guided-workflow";
import {
  useWizardStepFocus,
  WizardSteps,
  type WizardStep,
} from "./guided-workflow-shell";

type GuidedChangeRequestComposerProps = {
  token: string;
  layer: GisCatalogLayer;
  changeRequest?: GisCatalogChangeRequest | null;
  busy: boolean;
  onSubmit: (input: GisCatalogChangeRequestSaveInput) => Promise<boolean>;
  onCancel?: () => void;
};

function updateDraft(
  draft: GuidedChangeDraft,
  key: keyof GuidedChangeDraft,
  value: string,
): GuidedChangeDraft {
  return { ...draft, [key]: value };
}

function draftForChangeType(
  current: GuidedChangeDraft,
  changeType: GisCatalogChangeRequestType,
): GuidedChangeDraft {
  return {
    ...current,
    changeType,
    featureId: changeType === "feature_create" ? "" : current.featureId,
  };
}

function draftForSelectedFeature(
  current: GuidedChangeDraft,
  selected: GisCatalogLayerFeature | null,
  featureIdColumn: string | null | undefined,
): GuidedChangeDraft {
  return {
    ...current,
    featureId: selected?.feature_id ?? "",
    fieldName:
      current.fieldName ||
      Object.keys(selected?.attributes ?? {}).find(
        (field) => field !== featureIdColumn,
      ) ||
      "",
    coordinates:
      current.coordinates || coordinatesTextFromGeometry(selected?.geometry),
  };
}

function selectableFields(
  draft: GuidedChangeDraft,
  feature: GisCatalogLayerFeature | null,
  featureIdColumn: string | null | undefined,
): string[] {
  return Array.from(
    new Set([
      ...Object.keys(feature?.attributes ?? {}).filter(
        (field) => field !== featureIdColumn,
      ),
      ...(draft.fieldName ? [draft.fieldName] : []),
    ]),
  );
}

function currentFeatureValue(
  draft: GuidedChangeDraft,
  feature: GisCatalogLayerFeature | null,
  changeRequest?: GisCatalogChangeRequest | null,
): unknown {
  return (
    feature?.attributes[draft.fieldName] ??
    (changeRequest?.payload.before as Record<string, unknown> | undefined)?.[
      draft.fieldName
    ]
  );
}

function selectedFeatureLabel(
  draft: GuidedChangeDraft,
  feature: GisCatalogLayerFeature | null,
): string {
  return feature?.label || draft.featureId || "Nuovo elemento";
}

function useGuidedChangeRequestState({
  layer,
  changeRequest,
  onSubmit,
}: Pick<GuidedChangeRequestComposerProps, "layer" | "changeRequest" | "onSubmit">) {
  const [step, setStep] = useState<WizardStep>(1);
  const headingRef = useWizardStepFocus(step);
  const [draft, setDraft] = useState(() =>
    guidedDraftFromChangeRequest(changeRequest),
  );
  const [feature, setFeature] = useState<GisCatalogLayerFeature | null>(null);
  const [error, setError] = useState<string | null>(null);

  function changeType(nextType: GisCatalogChangeRequestType) {
    setDraft((current) => draftForChangeType(current, nextType));
  }

  function changeField(key: keyof GuidedChangeDraft, value: string) {
    setDraft((current) => updateDraft(current, key, value));
  }

  function selectFeature(selected: GisCatalogLayerFeature | null) {
    setFeature(selected);
    setDraft((current) =>
      draftForSelectedFeature(current, selected, layer.feature_id_column),
    );
  }

  function continueToDetails() {
    if (draft.changeType !== "feature_create" && !draft.featureId) {
      setError("Seleziona l'elemento della mappa da correggere.");
      return;
    }
    setError(null);
    setStep(2);
  }

  function review() {
    const validationError = guidedChangeValidation(draft, layer, feature);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    setStep(3);
  }

  async function submit() {
    const saved = await onSubmit(
      buildGuidedChangeInput(draft, layer, feature, changeRequest),
    );
    if (!saved || changeRequest) return;
    setDraft(emptyGuidedChangeDraft);
    setFeature(null);
    setStep(1);
  }

  return {
    beforeValue: currentFeatureValue(draft, feature, changeRequest),
    changeField,
    changeType,
    continueToDetails,
    draft,
    error,
    fields: selectableFields(draft, feature, layer.feature_id_column),
    headingRef,
    review,
    selectFeature,
    selectedLabel: selectedFeatureLabel(draft, feature),
    setStep,
    step,
    submit,
  };
}

export function GuidedChangeRequestComposer(
  props: GuidedChangeRequestComposerProps,
) {
  const { token, layer, changeRequest, busy, onCancel } = props;
  const state = useGuidedChangeRequestState(props);
  const editing = Boolean(changeRequest);

  return (
    <div className="mt-4 rounded-2xl border border-[#dce8de] bg-white p-4">
      <WizardSteps step={state.step} />
      {state.step === 1 ? (
        <ChangeTypeStep
          headingRef={state.headingRef}
          token={token}
          layer={layer}
          draft={state.draft}
          error={state.error}
          initialFeatureId={changeRequest?.feature_id ?? undefined}
          editing={editing}
          onChangeType={state.changeType}
          onSelectFeature={state.selectFeature}
          onContinue={state.continueToDetails}
          onCancel={onCancel}
        />
      ) : null}
      {state.step === 2 ? (
        <ChangeDetailsStep
          headingRef={state.headingRef}
          draft={state.draft}
          fields={state.fields}
          beforeValue={state.beforeValue}
          selectedLabel={state.selectedLabel}
          error={state.error}
          editing={editing}
          onFieldChange={state.changeField}
          onBack={() => state.setStep(1)}
          onReview={state.review}
          onCancel={onCancel}
        />
      ) : null}
      {state.step === 3 ? (
        <ChangeReviewStep
          headingRef={state.headingRef}
          draft={state.draft}
          beforeValue={state.beforeValue}
          selectedLabel={state.selectedLabel}
          busy={busy}
          editing={editing}
          onBack={() => state.setStep(2)}
          onSubmit={() => void state.submit()}
        />
      ) : null}
    </div>
  );
}
