import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import type { Shot } from "../types";
import type { Template } from "../templates";
import { enter } from "./common";

// Outro : nom de marque en gros + call to action discret.
export const OutroShot: React.FC<{ shot: Shot; template: Template }> = ({ shot, template }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { opacity, translateY } = enter(frame, fps);

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(70% 50% at 50% 50%, ${template.bgAccent} 0%, ${template.bg} 80%)`,
        alignItems: "center",
        justifyContent: "center",
        padding: "0 80px",
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontFamily: template.fontDisplay,
          color: template.fg,
          fontSize: 120,
          fontWeight: 800,
          letterSpacing: "-0.02em",
          opacity,
          transform: `translateY(${translateY}px)`,
        }}
      >
        {shot.text ?? template.brandName}
      </div>
      <div
        style={{
          marginTop: 30,
          fontFamily: template.fontBody,
          color: template.muted,
          fontSize: 32,
          opacity,
        }}
      >
        {shot.narration ?? "Suivez-nous"}
      </div>
    </AbsoluteFill>
  );
};
