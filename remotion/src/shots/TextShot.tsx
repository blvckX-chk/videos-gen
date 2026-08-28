import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import type { Shot } from "../types";
import type { Template } from "../templates";
import { enter } from "./common";

// Point clé affiché en gros sur fond neutre, avec liseret d'accent.
export const TextShot: React.FC<{ shot: Shot; template: Template }> = ({ shot, template }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { opacity, translateY } = enter(frame, fps);

  return (
    <AbsoluteFill style={{ background: template.bg, padding: "180px 100px", justifyContent: "center" }}>
      <div
        style={{
          width: 8,
          height: 90,
          background: template.accent,
          borderRadius: 4,
          marginBottom: 42,
          opacity,
          transform: `scaleY(${Math.min(1, frame / (fps * 0.4))})`,
          transformOrigin: "top",
        }}
      />
      <div
        style={{
          fontFamily: template.fontDisplay,
          color: template.fg,
          fontSize: 78,
          fontWeight: 700,
          lineHeight: 1.15,
          letterSpacing: "-0.015em",
          opacity,
          transform: `translateY(${translateY}px)`,
        }}
      >
        {shot.text}
      </div>
    </AbsoluteFill>
  );
};
