#!/usr/bin/env node
/**
 * Generates app/light-theme.css: light-mode overrides for the dark color
 * classes used across the app (e.g. bg-[#0D1117], text-slate-300).
 *
 * The UI was designed dark-first with hard-coded colors, so instead of
 * rewriting every component, each dark class gets a light equivalent that
 * applies only under <html class="light">. Re-run after adding new colors:
 *
 *   npm run theme:light
 */
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const SOURCE_DIRS = ["app", "components"];
const OUTPUT = join(root, "app", "light-theme.css");

// --- Light equivalents ------------------------------------------------------

const DARK_BG = {
  "#070A0F": "#F1F5F9",
  "#080B10": "#FFFFFF",
  "#090D12": "#FFFFFF",
  "#090D13": "#FFFFFF",
  "#000000": "#F8FAFC",
  "#0A0E14": "#F8FAFC",
  "#0A0E15": "#F1F5F9",
  "#0D1017": "#EFF6FF",
  "#0D1410": "#F0FDF4",
  "#140D0D": "#FEF2F2",
  "#14120D": "#FFFBEB",
  "#151D27": "#F1F5F9",
  "#161F2E": "#F1F5F9",
  "#0D1117": "#FFFFFF",
  "#101720": "#FFFFFF",
  "#111827": "#F1F5F9",
  "#121821": "#F1F5F9",
  "#161B22": "#F8FAFC",
  "#182131": "#E2E8F0",
  "#1A2230": "#E2E8F0",
  "#1C2431": "#E2E8F0",
  "#202938": "#E2E8F0",
  "#263142": "#CBD5E1",
  "#2B3545": "#CBD5E1",
  "#303E55": "#CBD5E1",
};

const DARK_BORDER = {
  "#0D1117": "#E2E8F0",
  "#121821": "#E2E8F0",
  "#182131": "#E2E8F0",
  "#1C2431": "#E2E8F0",
  "#202938": "#E2E8F0",
  "#263142": "#CBD5E1",
  "#2B3545": "#CBD5E1",
  "#303E55": "#94A3B8",
};

const TEXT_HEX = {
  "#F8FAFC": "#0F172A",
  "#E2E8F0": "#1E293B",
  "#CBD5E1": "#334155",
  "#94A3B8": "#475569",
  "#475569": "#94A3B8",
  // Bright accents are too light on white; use deeper shades.
  "#3B82F6": "#2563EB",
  "#60A5FA": "#2563EB",
  "#38BDF8": "#0284C7",
  "#22C55E": "#16A34A",
  "#EF4444": "#DC2626",
  "#F59E0B": "#B45309",
  "#A78BFA": "#7C3AED",
  "#8B5CF6": "#7C3AED",
};

const SLATE_TEXT = {
  white: "var(--color-slate-900)",
  "slate-50": "var(--color-slate-900)",
  "slate-100": "var(--color-slate-900)",
  "slate-200": "var(--color-slate-800)",
  "slate-300": "var(--color-slate-700)",
  "slate-400": "var(--color-slate-600)",
  "slate-600": "var(--color-slate-400)",
  "zinc-300": "var(--color-zinc-700)",
  "zinc-400": "var(--color-zinc-600)",
};

const SLATE_BG = {
  "slate-950": "#FFFFFF",
  "slate-900": "#FFFFFF",
  "slate-800": "var(--color-slate-100)",
  "slate-700": "var(--color-slate-200)",
};

const SLATE_BORDER = {
  "slate-800": "var(--color-slate-200)",
  "slate-700": "var(--color-slate-300)",
  "slate-600": "var(--color-slate-300)",
};

const ACCENTS = [
  "blue", "sky", "cyan", "teal", "emerald", "green", "lime", "yellow", "amber",
  "orange", "red", "rose", "pink", "fuchsia", "purple", "violet", "indigo",
];

// White text stays white on solid colored backgrounds (buttons, badges).
const SOLID_BG_SHADES = ["500", "600", "700", "800"];

// --- Scan --------------------------------------------------------------------

function* sourceFiles(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) {
      yield* sourceFiles(path);
    } else if (/\.(tsx|ts|jsx|js)$/.test(name)) {
      yield path;
    }
  }
}

const TOKEN_RE = /(?:^|[\s"'`{])((?:hover:|focus:|group-hover:|placeholder:|file:)?(?:bg|text|border|divide|placeholder|from|via|to)-(?:\[#[0-9A-Fa-f]{3,8}\]|white|black|(?:slate|zinc|gray|neutral|[a-z]+)-\d{2,3})(?:\/[\d.[\]]+)?)(?=[\s"'`}])/g;

const tokens = new Set();
for (const dir of SOURCE_DIRS) {
  for (const file of sourceFiles(join(root, dir))) {
    const text = readFileSync(file, "utf8");
    for (const match of text.matchAll(TOKEN_RE)) {
      tokens.add(match[1]);
    }
  }
}

// --- Map tokens to rules -----------------------------------------------------

function escapeClass(cls) {
  return cls.replace(/([[\]#:/.()%,!])/g, "\\$1");
}

// Anything inside .keep-dark (e.g. the login brand panel) keeps its dark look.
const KEEP_DARK = ":not(.keep-dark, .keep-dark *)";

function selectorFor(token, extra = "") {
  const variantMatch = token.match(/^(hover|focus|group-hover|placeholder|file):/);
  const variant = variantMatch ? variantMatch[1] : "";
  const cls = `.${escapeClass(token)}${extra}${KEEP_DARK}`;
  if (variant === "hover") return `${cls}:hover`;
  if (variant === "focus") return `${cls}:focus`;
  if (variant === "group-hover") return `.group:hover ${cls}`;
  if (variant === "placeholder") return `${cls}::placeholder`;
  if (variant === "file") return `${cls}::file-selector-button`;
  return cls;
}

// Dark tints of an accent (e.g. bg-amber-950/20) become pale tints in light mode.
function darkAccent(color, shades) {
  const m = color.match(/^([a-z]+)-(\d{3})$/);
  return m && ACCENTS.includes(m[1]) && shades.includes(m[2]) ? m[1] : null;
}

function lightValue(utility, color) {
  const hex = color.startsWith("[") ? color.slice(1, -1).toUpperCase() : null;
  if (utility === "bg" || utility === "from" || utility === "via" || utility === "to") {
    if (hex) return DARK_BG[hex];
    const accent = darkAccent(color, ["900", "950"]);
    if (accent) return `var(--color-${accent}-50)`;
    if (["zinc-900", "zinc-950", "gray-900", "gray-950", "neutral-900"].includes(color)) return "#FFFFFF";
    return SLATE_BG[color];
  }
  if (utility === "border" || utility === "divide") {
    if (hex) return DARK_BORDER[hex];
    const accent = darkAccent(color, ["800", "900", "950"]);
    if (accent) return `var(--color-${accent}-200)`;
    if (["zinc-800", "zinc-900", "gray-800"].includes(color)) return "var(--color-slate-200)";
    return SLATE_BORDER[color];
  }
  if (utility === "text" || utility === "placeholder") {
    if (hex) return TEXT_HEX[hex];
    if (SLATE_TEXT[color]) return SLATE_TEXT[color];
    const accent = color.match(/^([a-z]+)-(200|300|400)$/);
    if (accent && ACCENTS.includes(accent[1])) {
      return `var(--color-${accent[1]}-700)`;
    }
  }
  return null;
}

const solidBackgrounds = [];
for (const accent of ACCENTS) {
  for (const shade of SOLID_BG_SHADES) solidBackgrounds.push(`bg-${accent}-${shade}`);
}
for (const hex of Object.keys(TEXT_HEX)) {
  if (!DARK_BG[hex]) solidBackgrounds.push(`bg-[${hex}]`);
}
const keepWhite = solidBackgrounds.map((cls) => `:not([class~="${cls}"])`).join("");

const rules = [];
for (const token of [...tokens].sort()) {
  const bare = token.replace(/^(hover|focus|group-hover|placeholder|file):/, "");
  // file:text-white sits on a solid file:bg-* button; leave it white.
  if (token === "file:text-white") continue;
  const match = bare.match(/^(bg|text|border|divide|placeholder|from|via|to)-(.+?)(?:\/[\d.[\]]+)?$/);
  if (!match) continue;
  const [, utility, color] = match;
  const value = lightValue(utility, color);
  if (!value) continue;

  const isWhiteText = utility === "text" && ["white", "slate-50", "slate-100"].includes(color);
  const selector = selectorFor(token, isWhiteText ? keepWhite : "");

  if (utility === "from" || utility === "via" || utility === "to") {
    rules.push(`html.light ${selector} { --tw-gradient-${utility}: ${value}; }`);
  } else if (utility === "divide") {
    rules.push(`html.light ${selector} > :not(:last-child) { border-color: ${value}; }`);
  } else if (utility === "bg") {
    rules.push(`html.light ${selector} { background-color: ${value}; }`);
  } else if (utility === "border") {
    rules.push(`html.light ${selector} { border-color: ${value}; }`);
  } else {
    rules.push(`html.light ${selector} { color: ${value}; }`);
  }
}

const header = `/*
 * GENERATED by scripts/generate-light-theme.mjs. Do not edit by hand.
 * Light-mode overrides for dark color classes; run \`npm run theme:light\`
 * after adding new colors.
 */
`;
writeFileSync(OUTPUT, `${header}\n${rules.join("\n")}\n`);
console.log(`Wrote ${rules.length} light-theme rules to app/light-theme.css`);
