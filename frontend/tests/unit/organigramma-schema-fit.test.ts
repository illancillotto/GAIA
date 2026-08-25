import { describe, expect, test, vi } from "vitest";

import { fitScrollableContentToViewport, scheduleScrollableContentFit } from "@/lib/organigramma";

function sizedElement(metrics: {
  clientWidth?: number;
  clientHeight?: number;
  scrollWidth?: number;
  scrollHeight?: number;
}): HTMLElement {
  const element = document.createElement("div");
  Object.defineProperties(element, {
    clientWidth: { configurable: true, value: metrics.clientWidth ?? 0 },
    clientHeight: { configurable: true, value: metrics.clientHeight ?? 0 },
    scrollWidth: { configurable: true, value: metrics.scrollWidth ?? 0 },
    scrollHeight: { configurable: true, value: metrics.scrollHeight ?? 0 },
  });
  return element;
}

function immediateFrameApi() {
  let frameId = 0;
  return {
    requestAnimationFrame: vi.fn((callback: FrameRequestCallback) => {
      frameId += 1;
      callback(frameId);
      return frameId;
    }),
    cancelAnimationFrame: vi.fn(),
  };
}

describe("fitScrollableContentToViewport", () => {
  test("scales and centers a scrollable schema", () => {
    const viewport = sizedElement({ clientWidth: 1000, clientHeight: 520 });
    const content = sizedElement({ scrollWidth: 4000, scrollHeight: 900 });
    const setScale = vi.fn();
    const frameApi = immediateFrameApi();

    expect(fitScrollableContentToViewport(viewport, content, setScale, frameApi)).toBe(true);

    expect(setScale).toHaveBeenCalledWith(0.45);
    expect(viewport.scrollLeft).toBe(400);
    expect(viewport.scrollTop).toBe(0);
  });

  test("does not fit until viewport and content are measurable", () => {
    const setScale = vi.fn();
    const frameApi = immediateFrameApi();

    expect(fitScrollableContentToViewport(null, sizedElement({ scrollWidth: 100, scrollHeight: 100 }), setScale, frameApi)).toBe(false);
    expect(fitScrollableContentToViewport(sizedElement({ clientWidth: 100, clientHeight: 100 }), null, setScale, frameApi)).toBe(false);
    expect(
      fitScrollableContentToViewport(
        sizedElement({ clientWidth: 100, clientHeight: 0 }),
        sizedElement({ scrollWidth: 100, scrollHeight: 100 }),
        setScale,
        frameApi,
      ),
    ).toBe(false);

    expect(setScale).not.toHaveBeenCalled();
    expect(frameApi.requestAnimationFrame).not.toHaveBeenCalled();
  });
});

describe("scheduleScrollableContentFit", () => {
  test("runs the fit callback for the requested number of frames", () => {
    const onFit = vi.fn();
    const onComplete = vi.fn();
    const frameApi = immediateFrameApi();

    scheduleScrollableContentFit(onFit, 3, onComplete, frameApi);

    expect(onFit).toHaveBeenCalledTimes(3);
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(frameApi.requestAnimationFrame).toHaveBeenCalledTimes(3);
  });

  test("uses a no-op completion callback by default", () => {
    const onFit = vi.fn();
    const frameApi = immediateFrameApi();

    expect(() => scheduleScrollableContentFit(onFit, 1, undefined, frameApi)).not.toThrow();
    expect(onFit).toHaveBeenCalledTimes(1);
  });

  test("cancels queued frames", () => {
    const callbacks: FrameRequestCallback[] = [];
    const frameApi = {
      requestAnimationFrame: vi.fn((callback: FrameRequestCallback) => {
        callbacks.push(callback);
        return callbacks.length;
      }),
      cancelAnimationFrame: vi.fn(),
    };
    const onFit = vi.fn();

    const cancel = scheduleScrollableContentFit(onFit, 2, undefined, frameApi);
    cancel();
    callbacks[0]?.(1);

    expect(onFit).not.toHaveBeenCalled();
    expect(frameApi.cancelAnimationFrame).toHaveBeenCalledWith(1);
  });
});
