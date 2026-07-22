import { describe, expect, test } from "vitest";

import { getDocumentPreviewKind, getExtensionFromFilename, isPdfFilename } from "@/lib/document-preview";

describe("document preview helpers", () => {
  test("extracts lowercase filename extensions", () => {
    expect(getExtensionFromFilename("ricevuta.EML")).toBe(".eml");
    expect(getExtensionFromFilename("senza-estensione")).toBeNull();
  });

  test("detects PDF filenames", () => {
    expect(isPdfFilename("avviso.PDF")).toBe(true);
    expect(isPdfFilename("ricevuta.eml")).toBe(false);
  });

  test("classifies supported inline preview formats", () => {
    expect(getDocumentPreviewKind({ filename: "ricevuta.eml" })).toBe("text");
    expect(getDocumentPreviewKind({ filename: "avviso.txt" })).toBe("text");
    expect(getDocumentPreviewKind({ filename: "foto.png" })).toBe("image");
    expect(getDocumentPreviewKind({ filename: "foglio.xlsx" })).toBe("spreadsheet");
    expect(getDocumentPreviewKind({ filename: "foglio.xls" })).toBe("spreadsheet");
    expect(getDocumentPreviewKind({ filename: "relazione.docx" })).toBe("docx");
    expect(getDocumentPreviewKind({ filename: "forzato.bin", isPdf: true })).toBe("pdf");
    expect(getDocumentPreviewKind({ filename: "nome-errato.bin", extension: ".pdf", isPdf: false })).toBe("pdf");
    expect(getDocumentPreviewKind({ filename: "archivio.zip" })).toBe("download");
    expect(getDocumentPreviewKind({ filename: "senza-estensione", extension: null })).toBe("download");
  });
});
