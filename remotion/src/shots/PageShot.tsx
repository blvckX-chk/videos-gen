import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, useVideoConfig } from "remotion";
import type { Shot } from "../types";
import type { Template } from "../templates";
import { progress } from "./common";

// Ken Burns doux sur une page réelle du document (l'asset a été rasterisé côté
// backend et exposé via /assets/…). C'est le pilier "fidélité au document".
export const PageShot: React.FC<{ shot: Shot; template: Template }> = ({ shot, template }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const p = progress(frame, 0, durationInFrames);
  const scale = 1.06 + p * 0.12;
  const tx = (p - 0.5) * 60;
  const ty = (p - 0.5) * 40;
  const fadeIn = progress(frame, 0, fps * 0.35);

  return (
    <AbsoluteFill style={{ background: template.bg }}>
      <AbsoluteFill style={{ opacity: fadeIn }}>
        {shot.asset_url ? (
          <Img
            src={shot.asset_url}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              transform: `translate(${tx}px, ${ty}px) scale(${scale})`,
              transformOrigin: "center",
            }}
          />
        ) : (
          <div style={{ color: template.muted, alignSelf: "center", justifySelf: "center", margin: "auto" }}>
            Page indisponible
          </div>
        )}
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, transparent 60%, ${template.bg} 100%)`,
          pointerEvents: "none",
        }}
      />
      {shot.text && (
        <div
          style={{
            position: "absolute",
            left: 60,
            right: 60,
            bottom: 140,
            fontFamily: template.fontDisplay,
            color: template.fg,
            fontSize: 56,
            fontWeight: 700,
            lineHeight: 1.15,
            opacity: fadeIn,
            textShadow: "0 2px 12px rgba(0,0,0,0.6)",
          }}
        >
          {shot.text}
        </div>
      )}
    </AbsoluteFill>
  );
};
