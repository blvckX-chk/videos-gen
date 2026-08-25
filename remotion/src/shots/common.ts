// Petits helpers partagés par les shots.
import { interpolate, spring } from "remotion";

/** Interpolation clampée entre `from` et `to` sur `[a,b]`. */
export const lerp = (frame: number, a: number, b: number, from: number, to: number) =>
  interpolate(frame, [a, b], [from, to], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

/** Progression 0→1 sur [a,b]. */
export const progress = (frame: number, a: number, b: number) => lerp(frame, a, b, 0, 1);

/** Fade in + slide up subtil pour un carton texte. */
export const enter = (frame: number, fps: number) => {
  const s = spring({ frame, fps, config: { damping: 22, stiffness: 90, mass: 0.6 } });
  return { opacity: Math.min(1, s), translateY: (1 - s) * 24 };
};
