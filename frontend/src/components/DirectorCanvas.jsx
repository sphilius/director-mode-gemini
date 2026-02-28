import { useEffect, useRef } from "react";

/**
 * DirectorCanvas — the main stage area that displays the AI narration.
 * Text streams in token-by-token when connected via WebSocket.
 */
export default function DirectorCanvas({ narration, isStreaming }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [narration]);

  return (
    <section className="director-canvas">
      <div className="canvas-inner">
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
