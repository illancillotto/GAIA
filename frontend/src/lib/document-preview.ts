export type DocumentPreviewKind = "pdf" | "image" | "docx" | "spreadsheet" | "text" | "download";

const IMAGE_EXTENSIONS = new Set([".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"]);
const SPREADSHEET_EXTENSIONS = new Set([".xls", ".xlsx"]);
const TEXT_EXTENSIONS = new Set([".txt", ".csv", ".log", ".md", ".json", ".xml", ".eml"]);

export function getExtensionFromFilename(filename: string): string | null {
  const dotIndex = filename.lastIndexOf(".");
  return dotIndex >= 0 ? filename.slice(dotIndex).toLowerCase() : null;
}

export function isPdfFilename(filename: string): boolean {
  return getExtensionFromFilename(filename) === ".pdf";
}

export function getDocumentPreviewKind(document: {
  filename: string;
  extension?: string | null;
  isPdf?: boolean | null;
}): DocumentPreviewKind {
  const extension = (document.extension ?? getExtensionFromFilename(document.filename))?.toLowerCase() ?? null;

  if (document.isPdf === true || extension === ".pdf") {
    return "pdf";
  }

  if (extension != null && IMAGE_EXTENSIONS.has(extension)) {
    return "image";
  }

  if (extension === ".docx") {
    return "docx";
  }

  if (extension != null && SPREADSHEET_EXTENSIONS.has(extension)) {
    return "spreadsheet";
  }

  if (extension != null && TEXT_EXTENSIONS.has(extension)) {
    return "text";
  }

  return "download";
}
