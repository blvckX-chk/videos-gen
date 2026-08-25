import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import type { Storyboard, Shot } from "./types";
import { pickTemplate } from "./templates";
import { TitleShot } from "./shots/TitleShot";
import { TextShot } from "./shots/TextShot";
import { PageShot } from "./shots/PageShot";
import { PanelShot } from "./shots/PanelShot";
import { OutroShot } from "./shots/OutroShot";
import type { Template } from "./templates";

const RENDERERS: Record<
  string,
  React.FC<{ shot: Shot; template: Template }>
> = {
  title: TitleShot,
  text: TextShot,
  page: PageShot,
  panel: PanelShot,
  outro: OutroShot,
  // Fallbacks : quote/stat/broll s'appuient sur des composants existants en
  // attendant leur propre design.
  quote: TextShot,
  stat: TextShot,
  broll: PageShot,
};

// Rendu principal : chaque shot est monté dans une Sequence de longueur = durée.
export const VideoComp: React.FC<{ storyboard: Storyboard }> = ({ storyboard }) => {
  const { fps } = useVideoConfig();
  const template = pickTemplate(storyboard.template);

  const shots: Shot[] = storyboard.scenes.flatMap((s) => s.shots);
  let cursor = 0;

  return (
    <AbsoluteFill style={{ background: template.bg }}>
      {shots.map((shot, i) => {
        const durationInFrames = Math.max(1, Math.round(shot.duration * fps));
        const from = cursor;
        cursor += durationInFrames;
        const R = RENDERERS[shot.type] ?? TextShot;
        return (
          <Sequence key={i} from={from} durationInFrames={durationInFrames}>
            <R shot={shot} template={template} />
          </Sequence>
        );
      })}

      {/* Watermark permanent, discret en bas. */}
      <div
        style={{
          position: "absolute",
          bottom: 44,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            fontFamily: template.fontBody,
            color: template.muted,
            fontSize: 22,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            padding: "8px 18px",
            borderRadius: 999,
            background: "rgba(0,0,0,0.35)",
            border: `1px solid ${template.accent}66`,
          }}
        >
          {storyboard.brand?.watermark ?? template.brandName}
        </div>
      </div>
    </AbsoluteFill>
  );
};
