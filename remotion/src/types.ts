// Types miroir du storyboard backend. À maintenir en cohérence avec
// backend/app/storyboard/schema.py — schéma volontairement plat pour que la
// désérialisation côté Remotion reste triviale.

export type ShotType =
  | "title"
  | "text"
  | "page"
  | "panel"
  | "stat"
  | "quote"
  | "outro"
  | "broll";

export type Shot = {
  index: number;
  type: ShotType;
  duration: number; // secondes
  text?: string | null;
  narration?: string | null;
  source_page?: number | null;
  source_panel?: number | null;
  transition_in?: string | null;
  emphasis?: string | null;
  // URL locale d'un asset pré-rasterisé (page ou case) — rempli par le backend
  // avant l'appel Remotion, jamais par le LLM.
  asset_url?: string | null;
};

export type Scene = {
  index: number;
  title?: string | null;
  shots: Shot[];
};

export type Storyboard = {
  id: string;
  document_id: string;
  fps: number;
  formats: string[];
  template: string;
  language: string;
  scenes: Scene[];
  // Métadonnées visuelles ajoutées par le backend au moment du rendu.
  brand?: {
    name: string;
    watermark?: string;
  };
};
