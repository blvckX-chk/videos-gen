import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import type { Shot } from "../types";
import type { Template } from "../templates";
import { enter, progress } from "./common";

// Carton titre : gros type animé, léger scale de fond pour donner du mouvement.
export const TitleShot: React.FC<{ shot: Shot; template: Template }> = ({ shot, template }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { opacity, translateY } = enter(frame, fps);
  const bgScale = 1 + progress(frame, 0, fps * 3) * 0.06;

  return (
    <AbsoluteFill style={{ background: template.bg }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(60% 45% at 50% 45%, ${template.bgAccent} 0%, transparent 70%)`,
          transform: `scale(${bgScale})`,
        }}
      />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: "0 90px" }}>
        <div
          style={{
            fontFamily: template.fontDisplay,
            color: template.fg,
            fontSize: 110,
            fontWeight: 800,
            lineHeight: 1.05,
            textAlign: "center",
            letterSpacing: "-0.02em",
            opacity,
            transform: `translateY(${translateY}px)`,
          }}
        >
          {shot.text ?? "Sans titre"}
        </div>
        <div
          style={{
            marginTop: 40,
            height: 6,
            width: 120,
            background: template.accent,
            borderRadius: 999,
            opacity,
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
