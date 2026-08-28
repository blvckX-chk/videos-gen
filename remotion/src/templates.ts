// Templates visuels : tokens de style par pôle / type de contenu.
// Un template = palette + typographies + accents. Le rendu applique le template
// choisi par le storyboard (backend). Ajouter un template = ajouter une entrée.

export type Template = {
  bg: string;         // fond principal
  bgAccent: string;   // couleur d'accent en fond (cartons)
  fg: string;         // texte principal
  muted: string;      // texte secondaire
  accent: string;     // couleur d'accent (bordures, mots emphasés)
  fontDisplay: string;
  fontBody: string;
  radius: number;
  brandName: string;
};

const BASE_STACK = "system-ui, -apple-system, Segoe UI, Roboto, sans-serif";

export const TEMPLATES: Record<string, Template> = {
  default: {
    bg: "#0B0D12",
    bgAccent: "#151922",
    fg: "#F1EBE0",
    muted: "#AC9F8C",
    accent: "#E4A93E",
    fontDisplay: `"Bricolage Grotesque", ${BASE_STACK}`,
    fontBody: BASE_STACK,
    radius: 22,
    brandName: "blvckUnlimited",
  },
  corporate: {
    bg: "#0F1420",
    bgAccent: "#182033",
    fg: "#F4F6FB",
    muted: "#95A3BF",
    accent: "#5CC8FF",
    fontDisplay: BASE_STACK,
    fontBody: BASE_STACK,
    radius: 16,
    brandName: "blvckUnlimited",
  },
  explainer: {
    bg: "#141110",
    bgAccent: "#1D1917",
    fg: "#F5EFE7",
    muted: "#B5A796",
    accent: "#F2B84B",
    fontDisplay: BASE_STACK,
    fontBody: BASE_STACK,
    radius: 20,
    brandName: "blvckUnlimited",
  },
  deck: {
    bg: "#101010",
    bgAccent: "#1C1C1C",
    fg: "#FFFFFF",
    muted: "#B0B0B0",
    accent: "#FF7B54",
    fontDisplay: BASE_STACK,
    fontBody: BASE_STACK,
    radius: 12,
    brandName: "blvckUnlimited",
  },
  motion_comic: {
    bg: "#0A0A0F",
    bgAccent: "#141420",
    fg: "#FFF7E6",
    muted: "#B9A97F",
    accent: "#FFC93C",
    fontDisplay: `"Bangers", "Bricolage Grotesque", ${BASE_STACK}`,
    fontBody: BASE_STACK,
    radius: 8,
    brandName: "blvckUnlimited",
  },
};

export function pickTemplate(name?: string): Template {
  if (name && TEMPLATES[name]) return TEMPLATES[name];
  return TEMPLATES.default;
}
