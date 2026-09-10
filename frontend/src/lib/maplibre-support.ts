import { GPUInitializationError, type Map as MapLibreMap } from "maplibre-gl";

export const WEBGL2_REQUIRED_MESSAGE =
  "WebGL2 non e disponibile in questo browser o in questa sessione. Il GIS richiede WebGL2 attivo.";

export function canCreateWebGL2Context(): boolean {
  try {
    const canvas = window.document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2"));
  } catch {
    return false;
  }
}

export function mapInitializationErrorMessage(error: unknown, fallback: string): string {
  if (isGPUInitializationError(error)) {
    return error.statusMessage || error.message || WEBGL2_REQUIRED_MESSAGE;
  }
  return error instanceof Error ? error.message : fallback;
}

export function isGPUInitializationError(error: unknown): error is GPUInitializationError {
  return error instanceof GPUInitializationError;
}

export function registerMapGPUErrorHandler(
  map: MapLibreMap,
  onError: (message: string) => void,
  fallback: string,
): void {
  map.on("error", (event) => {
    if (isGPUInitializationError(event.error)) {
      onError(mapInitializationErrorMessage(event.error, fallback));
    }
  });
}
