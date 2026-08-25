import React from "react";
import { AbsoluteFill, Img, useCurrentFrame, useVideoConfig } from "remotion";
import type { Shot } from "../types";
import type { Template } from "../templates";
import { progress } from "./common";

// Case de BD en motion comic : arrive avec un léger "slam" (scale down + fade),
// puis micro-Ken-Burns pour donner de la vie à une image statique.
export const PanelShot: React.FC<{ shot: Shot; template: Template }> = ({ shot, template }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const slam = progress(frame, 0, fps * 0.35);
  const life = progress(frame, 0, durationInFrames);
  const scale = 1.15 - slam * 0.1 + life * 0.05;
  const rotate = (1 - slam) * 2;

  return (
    <AbsoluteFill style={{ background: template.bgAccent }}>
      <AbsoluteFill
        style={{
          padding: 40,
          alignItems: "center",
          justifyContent: "center",
          opacity: slam,
          transform: `scale(${scale}) rotate(${rotate}deg)`,
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            border: `6px solid ${template.fg}`,
            borderRadius: template.radius,
            background: template.bg,
            overflow: "hidden",
            boxShadow: `0 20px 60px rgba(0,0,0,0.6), 0 0 0 3px ${template.accent}`,
          }}
        >
          {shot.asset_url ? (
            <Img
              src={shot.asset_url}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          ) : (
            <div style={{ color: template.muted, textAlign: "center", padding: 80 }}>
              Case indisponible
            </div>
          )}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
