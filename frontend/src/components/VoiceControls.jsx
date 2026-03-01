import { useState } from "react";

/**
 * VoiceControls — text input + live mic toggle for the Gemini Live API.
 *
 * When live mode is active, the mic button streams PCM audio directly
 * to Gemini via WebSocket. Text input works as a fallback in both modes.
 */
export default function VoiceControls({
  onDirective,
  onToggleMic,
  onInterrupt,
  isMicActive,
  isStreaming,
  isLive,
}) {
  const [text, setText] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    onDirective(trimmed);
    setText("");
  };

  return (
    <form className="voice-controls" onSubmit={handleSubmit}>
      <input
        className="directive-input"
        type="text"
        placeholder={isMicActive ? "Listening… speak your direction" : "Direct the scene…"}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={isMicActive}
      />

      {/* Live mic toggle — streams audio to Gemini */}
      {isLive && (
        <button
          type="button"
          className={`mic-btn ${isMicActive ? "listening" : ""}`}
          onClick={onToggleMic}
          title={isMicActive ? "Stop microphone" : "Start microphone"}
        >
          {isMicActive ? "⏹" : "🎤"}
        </button>
      )}

      {/* Interrupt button — stop current generation */}
      {isStreaming && (
        <button
          type="button"
          className="mic-btn"
          onClick={onInterrupt}
          title="Stop generation"
        >
          ✋
        </button>
      )}

      <button
        type="submit"
        className="send-btn"
        disabled={!text.trim() || isMicActive}
      >
        Direct
      </button>
    </form>
  );
}
