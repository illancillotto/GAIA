export const BLOCK_PREFIX = "GAIA-BLOCKS/1\n";
export const BLOCK_LABELS = { logo: "Logo ufficiale", title: "Titolo", paragraph: "Paragrafo", list: "Elenco", link: "Link", button: "Pulsante" };
export type BlockKind = keyof typeof BLOCK_LABELS;
export type TemplateBlock = { kind: BlockKind; text?: string; url?: string };

export function readBlocks(body: string): TemplateBlock[] | null {
  if (!body.startsWith(BLOCK_PREFIX)) return null;
  try {
    const blocks: unknown = JSON.parse(body.slice(BLOCK_PREFIX.length));
    if (!Array.isArray(blocks) || !blocks.length || blocks.length > 60) return null;
    if (!blocks.every((block) => block && Object.hasOwn(BLOCK_LABELS, block.kind))) return null;
    return blocks;
  } catch { return null; }
}

export function writeBlocks(blocks: TemplateBlock[]): string {
  return BLOCK_PREFIX + JSON.stringify(blocks);
}

export function safeLink(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && Boolean(url.hostname) && !url.username && !url.password && !/[\s<>"\\\x00-\x1f\x7f]|\{\{/.test(value);
  } catch { return false; }
}
