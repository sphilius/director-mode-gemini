import { useEffect, useRef } from "react";

/**
 * DirectorCanvas — the main stage area that displays the AI narration.
 * In live mode, narration comes from output transcription of audio.
 * Also shows the input transcription (what the user said).
 */
export default function DirectorCanvas({ narration, transcriptIn, isStreaming }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [narration]);

  return (
    <section className="director-canvas">
      <div className="canvas-inner">
        {transcriptIn && (
          <p className="transcript-in">You: {transcriptIn}</p>
        )}
        {narration ? (
          <p className="narration-text">
            {narration}
            {isStreaming && <span className="cursor" />}
          </p>
        ) : (
          <p className="placeholder">
            Give your first direction to begin the scene&hellip;
          </p>
        )}
        <div ref={endRef} />
      </div>
    </section>
  );
}
