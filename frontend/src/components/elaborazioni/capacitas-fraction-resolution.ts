import type { CapacitasFrazioneCandidate, CapacitasParticellaAnomalia, CapacitasResolveFragioneResult } from "@/types/api";

export type FractionResolutionState = {
  particella: CapacitasParticellaAnomalia;
  selectedFrazioneId: string;
  busy: boolean;
  error: string | null;
  success: boolean;
};

type FractionResolutionEventPayloads = {
  selected: CapacitasFrazioneCandidate;
  started: undefined;
  synchronized: undefined;
  unsuccessful: CapacitasResolveFragioneResult;
  rejected: unknown;
};

type FractionResolutionPolicy = {
  [EventName in keyof FractionResolutionEventPayloads]: (
    payload: FractionResolutionEventPayloads[EventName],
  ) => Partial<Omit<FractionResolutionState, "particella">>;
};

const fractionResolutionPolicy: FractionResolutionPolicy = {
  selected: (candidate) => ({ selectedFrazioneId: candidate.frazione_id }),
  started: () => ({ busy: true, error: null }),
  synchronized: () => ({ busy: false, success: true }),
  unsuccessful: (result) => ({ busy: false, error: result.error ?? "Errore sync" }),
  rejected: (error) => ({ busy: false, error: error instanceof Error ? error.message : "Errore" }),
};

export function transitionFractionResolution<EventName extends keyof FractionResolutionEventPayloads>(
  state: FractionResolutionState | null,
  eventName: EventName,
  payload: FractionResolutionEventPayloads[EventName],
): FractionResolutionState | null {
  if (state === null) return state;
  return { ...state, ...fractionResolutionPolicy[eventName](payload) };
}
