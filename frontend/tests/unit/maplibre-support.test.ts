import { GPUInitializationError } from "maplibre-gl";
import { afterEach, describe, expect, test, vi } from "vitest";

import {
  WEBGL2_REQUIRED_MESSAGE,
  canCreateWebGL2Context,
  isGPUInitializationError,
  mapInitializationErrorMessage,
  registerMapGPUErrorHandler,
} from "@/lib/maplibre-support";

describe("MapLibre browser support", () => {
  afterEach(() => vi.restoreAllMocks());

  test("accepts only a WebGL2 context", () => {
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, "getContext");
    getContext.mockReturnValueOnce({} as WebGL2RenderingContext);
    expect(canCreateWebGL2Context()).toBe(true);

    getContext.mockReturnValueOnce(null);
    expect(canCreateWebGL2Context()).toBe(false);
  });

  test("reports an unavailable canvas as unsupported", () => {
    vi.spyOn(document, "createElement").mockImplementationOnce(() => {
      throw new Error("canvas blocked");
    });
    expect(canCreateWebGL2Context()).toBe(false);
  });

  test("formats GPU, generic and unknown initialization errors", () => {
    const gpuError = new GPUInitializationError({}, null);
    expect(isGPUInitializationError(gpuError)).toBe(true);
    expect(isGPUInitializationError(new Error("other"))).toBe(false);
    expect(mapInitializationErrorMessage(gpuError, "fallback")).toBe(gpuError.message);
    Object.defineProperty(gpuError, "statusMessage", { value: "driver unavailable" });
    expect(mapInitializationErrorMessage(gpuError, "fallback")).toBe("driver unavailable");
    const emptyGpuError = new GPUInitializationError({}, null);
    Object.defineProperties(emptyGpuError, {
      statusMessage: { value: "" },
      message: { value: "" },
    });
    expect(mapInitializationErrorMessage(emptyGpuError, "fallback")).toBe(WEBGL2_REQUIRED_MESSAGE);
    expect(mapInitializationErrorMessage(new Error("generic"), "fallback")).toBe("generic");
    expect(mapInitializationErrorMessage(null, "fallback")).toBe("fallback");
    expect(WEBGL2_REQUIRED_MESSAGE).toContain("WebGL2");
  });

  test("forwards only GPU initialization errors from a map", () => {
    let listener: ((event: { error: Error }) => void) | undefined;
    const map = {
      on: vi.fn((_type: string, callback: typeof listener) => { listener = callback; }),
    } as never;
    const onError = vi.fn();
    registerMapGPUErrorHandler(map, onError, "fallback");

    listener?.({ error: new Error("source") });
    expect(onError).not.toHaveBeenCalled();
    const gpuError = new GPUInitializationError({}, null);
    listener?.({ error: gpuError });
    expect(onError).toHaveBeenCalledWith(gpuError.message);
  });
});
