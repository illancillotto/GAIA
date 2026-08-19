import { Blob as NodeBlob } from "node:buffer";

import "@testing-library/jest-dom/vitest";

// undici 7.29 Response(Blob) needs Node's Blob.stream(); jsdom FormData still
// requires its own Blob, so convert on append.
const JsdomBlob = globalThis.Blob;
globalThis.Blob = NodeBlob as unknown as typeof Blob;

const originalFormDataAppend = FormData.prototype.append;
FormData.prototype.append = function append(
  this: FormData,
  name: string,
  value: string | Blob,
  fileName?: string,
) {
  const normalizedValue =
    typeof value !== "string" && value instanceof NodeBlob && !(value instanceof JsdomBlob)
      ? new JsdomBlob([value], { type: (value as NodeBlob).type })
      : value;
  if (fileName === undefined) {
    originalFormDataAppend.call(this, name, normalizedValue);
    return;
  }
  originalFormDataAppend.call(this, name, normalizedValue, fileName);
} as typeof FormData.prototype.append;
