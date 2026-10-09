import type { Locator, Page } from "@playwright/test";

export function hasFocusedParcelAtCenter(pixels: number[]): boolean {
  if (pixels.length !== 20 * 20 * 4) return false;
  for (let offset = 0; offset < pixels.length; offset += 4) {
    const [red, green, blue, alpha] = pixels.slice(offset, offset + 4);
    if (alpha !== 255 || red < 190 || green > 130 || blue < 140 || red - green < 70 || blue - green < 40) return false;
  }
  return true;
}

export async function focusedParcelCoversCanvasCenter(page: Page, canvas: Locator): Promise<boolean> {
  const screenshot = await canvas.screenshot({ animations: "allow", scale: "css", timeout: 5000 });
  const pixels = await page.evaluate(async (encoded) => {
    const bytes = Uint8Array.from(atob(encoded), (character) => character.charCodeAt(0));
    const bitmap = await createImageBitmap(new Blob([bytes], { type: "image/png" }));
    try {
      if (bitmap.width < 20 || bitmap.height < 20) return [];
      const sample = document.createElement("canvas");
      sample.width = 20;
      sample.height = 20;
      const context = sample.getContext("2d");
      if (!context) throw new Error("Canvas screenshot sampling requires a 2D context");
      context.drawImage(bitmap, Math.floor(bitmap.width / 2) - 10, Math.floor(bitmap.height / 2) - 10, 20, 20, 0, 0, 20, 20);
      return Array.from(context.getImageData(0, 0, 20, 20).data);
    } finally {
      bitmap.close();
    }
  }, screenshot.toString("base64"));
  return hasFocusedParcelAtCenter(pixels);
}
