import type { PDFDocumentProxy, PDFPageProxy, RenderTask } from "pdfjs-dist";
import type { Attachment } from "@/types/communications";

export type RenderSession = { disposed: boolean; document?: PDFDocumentProxy; task?: RenderTask };
type Options = { zoom: number; pixelBudget: number; total: number };

export async function renderSnapshot(content: ArrayBuffer, part: Attachment, host: HTMLDivElement, options: Options, session: RenderSession) {
  const pdfjs = await import("pdfjs-dist");
  pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();
  const pdf = await pdfjs.getDocument({ data: new Uint8Array(content), isEvalSupported: false }).promise;
  session.document = pdf;
  if (pdf.numPages !== part.pages || part.pages > 200) throw new Error("Numero pagine non verificato");
  host.replaceChildren();
  for (let index = 1; index <= pdf.numPages; index++) {
    if (session.disposed) return;
    const page = await pdf.getPage(index);
    await renderPage(page, index, host, options, session);
    page.cleanup();
  }
}

async function renderPage(page: PDFPageProxy, index: number, host: HTMLDivElement, options: Options, session: RenderSession) {
  const base = page.getViewport({ scale: 1 });
  const width = Math.min(1600, host.clientWidth || 800);
  const desired = width / base.width * options.zoom;
  const scale = Math.min(desired, Math.sqrt(Math.min(4_000_000, options.pixelBudget / options.total) / (base.width * base.height)));
  const viewport = page.getViewport({ scale });
  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil(viewport.width); canvas.height = Math.ceil(viewport.height);
  canvas.style.width = options.zoom === 1 ? "100%" : `${Math.round(base.width * desired)}px`;
  canvas.style.maxWidth = options.zoom === 1 ? "100%" : "none";
  canvas.setAttribute("aria-label", `Pagina ${index} di ${options.total}`);
  canvas.dataset.page = String(index);
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Rendering PDF non disponibile nel browser");
  host.append(canvas);
  session.task = page.render({ canvasContext: context, canvas, viewport });
  await session.task.promise;
}
