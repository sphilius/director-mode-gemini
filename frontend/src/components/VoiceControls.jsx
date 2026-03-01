import { useState, useRef } from "react";

/**
 * VoiceControls — text input with optional speech-to-text.
 * Falls back gracefully when the Web Speech API is unavailable.
 */
export default function VoiceControls({ onDirective, disabled }) {
  const [text, setText] = useState("");
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);

  const supportsVoice =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  const toggleListening = () => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setText((prev) => (prev ? `${prev} ${transcript}` : transcript));
      setListening(false);
    };

    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onDirective(trimmed);
    setText("");
  };

  return (
    <form className="voice-controls" onSubmit={handleSubmit}>
      <input
        className="directive-input"
        type="text"
        placeholder="Direct the scene…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
      />
      {supportsVoice && (
        <button
          type="button"
          className={`mic-btn ${listening ? "listening" : ""}`}
          onClick={toggleListening}
          disabled={disabled}
          title="Voice input"
        >
          {listening ? "⏹" : "🎤"}
        </button>
      )}
      <button
        type="submit"
        className="send-btn"
        disabled={disabled || !text.trim()}
      >
        Direct
      </button>
    </form>
  );
}
