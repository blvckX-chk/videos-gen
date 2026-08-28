import React from "react";
import { Composition, getInputProps } from "remotion";
import { VideoComp } from "./Video";
import type { Storyboard } from "./types";

const DEFAULT_STORY: Storyboard = {
  id: "demo",
  document_id: "demo",
  fps: 30,
  formats: ["9:16"],
  template: "default",
  language: "fr",
  scenes: [
    { index: 0, title: "Intro", shots: [{ index: 0, type: "title", duration: 2.5, text: "videos-gen" }] },
    { index: 1, title: "Corps", shots: [{ index: 0, type: "text", duration: 3, text: "Un moteur vidéo à base de prompts et de PDF." }] },
    { index: 2, title: "Outro", shots: [{ index: 0, type: "outro", duration: 2.5, text: "blvckUnlimited" }] },
  ],
};

// La durée totale et le ratio sont calculés en fonction des props effectives à
// l'appel du rendu (calculateMetadata) — ça permet un même Composition pour
// 9:16 / 1:1 / 16:9 et pour n'importe quel storyboard.
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Video"
        component={VideoComp}
        defaultProps={{ storyboard: DEFAULT_STORY }}
        durationInFrames={300}
        fps={30}
        width={1080}
        height={1920}
        calculateMetadata={async ({ props }) => {
          const sb = (props?.storyboard ?? DEFAULT_STORY) as Storyboard;
          const fps = sb.fps || 30;
          const totalSec = sb.scenes.reduce(
            (a, sc) => a + sc.shots.reduce((b, sh) => b + sh.duration, 0),
            0
          );
          const format = sb.formats?.[0] ?? "9:16";
          const [w, h] = dimsFor(format);
          return {
            durationInFrames: Math.max(30, Math.round(totalSec * fps)),
            fps,
            width: w,
            height: h,
            props,
          };
        }}
      />
    </>
  );
};

function dimsFor(fmt: string): [number, number] {
  switch (fmt) {
    case "16:9":
      return [1920, 1080];
    case "1:1":
      return [1080, 1080];
    case "9:16":
    default:
      return [1080, 1920];
  }
}
