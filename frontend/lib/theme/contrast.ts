/** Pisos WCAG 2.2 AA. */
export const AA_TEXT_MIN = 4.5;
export const AA_UI_MIN = 3;

export type Rgb = readonly [number, number, number];

export type ContrastPair = {
  name: string;
  fg: Rgb;
  bg: Rgb;
  minRatio: number;
};

function channelToLinear(channel: number): number {
  const c = channel / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

/** Luminância relativa sRGB (WCAG). */
export function relativeLuminance(r: number, g: number, b: number): number {
  return (
    0.2126 * channelToLinear(r) +
    0.7152 * channelToLinear(g) +
    0.0722 * channelToLinear(b)
  );
}

export function contrastRatio(l1: number, l2: number): number {
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Pares críticos alinhados a `globals.css` (neutros oklch → sRGB aproximado).
 * Light muted-foreground usa L≈0.45 (~#595959) para margem AA em texto auxiliar.
 */
export const criticalThemePairs: ContrastPair[] = [
  {
    name: "light: foreground on background",
    fg: [23, 23, 23],
    bg: [255, 255, 255],
    minRatio: AA_TEXT_MIN,
  },
  {
    name: "light: muted-foreground on background",
    fg: [89, 89, 89],
    bg: [255, 255, 255],
    minRatio: AA_TEXT_MIN,
  },
  {
    name: "light: primary-foreground on primary",
    fg: [250, 250, 250],
    bg: [46, 46, 46],
    minRatio: AA_TEXT_MIN,
  },
  {
    name: "light: destructive on background",
    fg: [185, 28, 28],
    bg: [255, 255, 255],
    minRatio: AA_TEXT_MIN,
  },
  {
    name: "dark: foreground on background",
    fg: [250, 250, 250],
    bg: [23, 23, 23],
    minRatio: AA_TEXT_MIN,
  },
  {
    name: "dark: muted-foreground on background",
    fg: [184, 184, 184],
    bg: [23, 23, 23],
    minRatio: AA_TEXT_MIN,
  },
  {
    name: "dark: primary-foreground on primary",
    fg: [46, 46, 46],
    bg: [229, 229, 229],
    minRatio: AA_TEXT_MIN,
  },
  {
    name: "light: ring on background (focus UI)",
    fg: [115, 115, 115],
    bg: [255, 255, 255],
    minRatio: AA_UI_MIN,
  },
  {
    name: "dark: ring on background (focus UI)",
    fg: [115, 115, 115],
    bg: [23, 23, 23],
    minRatio: AA_UI_MIN,
  },
];
