import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { renderSnapshot, type RenderSession } from "@/components/communications/pdf-renderer";
import { part } from "./fixtures";
const pdf = vi.hoisted(() => ({ getDocument: vi.fn(), GlobalWorkerOptions: { workerSrc: "" } }));
vi.mock("pdfjs-dist", () => pdf);
beforeEach(() => vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as CanvasRenderingContext2D));
afterEach(() => vi.restoreAllMocks());
function document(total = 3) {
  const page = { getViewport: vi.fn(({ scale }) => ({ width: 595 * scale, height: 842 * scale })), render: vi.fn(() => ({ promise: Promise.resolve() })), cleanup: vi.fn() };
  const doc = { numPages: total, getPage: vi.fn().mockResolvedValue(page) };
  pdf.getDocument.mockReturnValue({ promise: Promise.resolve(doc) });
  return { doc, page };
}
it("renders every page, fits width, bounds canvas pixels and preserves navigation labels", async () => {
  const { doc, page } = document();
  const host = window.document.createElement("div");
  Object.defineProperty(host, "clientWidth", { value: 900 });
  await renderSnapshot(new ArrayBuffer(4), part, host, { zoom: 1, pixelBudget: 64e6, total: 3 }, { disposed: false } as RenderSession);
  expect(doc.getPage.mock.calls).toEqual([[1], [2], [3]]);
  expect(host.querySelectorAll("canvas")).toHaveLength(3);
  expect(host.children[2].getAttribute("aria-label")).toBe("Pagina 3 di 3");
  expect(page.cleanup).toHaveBeenCalledTimes(3);
  expect(host.children[0]).toHaveStyle({ width: "100%", maxWidth: "100%" });
  await renderSnapshot(new ArrayBuffer(4), part, host, { zoom: 3, pixelBudget: 100, total: 3 }, { disposed: false });
  expect(host.children[0]).toHaveStyle({ maxWidth: "none" });
  expect((host.children[0] as HTMLCanvasElement).width).toBeLessThan(20);
});
it("rejects missing canvas and mismatched or excessive page counts; stops disposed work", async () => {
  const host = window.document.createElement("div");
  document(2);
  await expect(renderSnapshot(new ArrayBuffer(0), part, host, { zoom: 1, pixelBudget: 1, total: 3 }, { disposed: false })).rejects.toThrow("Numero pagine");
  document(201);
  await expect(renderSnapshot(new ArrayBuffer(0), { ...part, pages: 201 }, host, { zoom: 1, pixelBudget: 1, total: 201 }, { disposed: false })).rejects.toThrow("Numero pagine");
  const { doc } = document();
  await renderSnapshot(new ArrayBuffer(0), part, host, { zoom: 1, pixelBudget: 1, total: 3 }, { disposed: true });
  expect(doc.getPage).not.toHaveBeenCalled();
  vi.mocked(HTMLCanvasElement.prototype.getContext).mockReturnValue(null);
  await expect(renderSnapshot(new ArrayBuffer(0), part, host, { zoom: 1, pixelBudget: 1, total: 3 }, { disposed: false })).rejects.toThrow("non disponibile");
});
