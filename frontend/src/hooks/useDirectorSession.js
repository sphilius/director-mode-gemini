import { useCallback, useEffect, useRef, useState } from "react";

// Point directly to the Uvicorn backend port to bypass the Vite proxy entirely
const WS_BASE = "ws://127.0.0.1:8000";

/**
 * useDirectorSession — manages WebSocket connection and story state
 * for a single directing session.
 */
export default function useDirectorSession(sessionId) {
  const [story, setStory] = useState(null);
  const [narration, setNarration] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);

  // Connect WebSocket
  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/direct/${sessionId}`);

    ws.onopen = () => setIsConnected(true);
    ws.onerror = (error) => {
      console.error("WebSocket connection error:", error);
      setIsConnected(false);
    };

    ws.onclose = (event) => {
      console.warn("WebSocket closed", event.code, event.reason);
      setIsConnected(false);
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      switch (msg.type) {
        case "token":
          setNarration((prev) => prev + msg.data);
          break;
        case "scene_updated":
          setStory((prevStory) => {
            const newScene = msg.data.scene;
            const newTimelineEntry = {
              title: newScene.title,
              mood: newScene.mood,
            };

            // Initialize story if it doesn't exist
            if (!prevStory) {
              return {
                characters: [],
                scenes: [newScene],
                timeline: [newTimelineEntry],
                contextSummary: "",
              };
            }

            return {
              ...prevStory,
              scenes: [...prevStory.scenes.slice(0, -1), newScene],
              timeline: [...prevStory.timeline.slice(0, -1), newTimelineEntry],
            };
          });
          break;

        case "character_introduced":
          setStory((prevStory) => {
            const newCharacter = msg.data.character;

            // Initialize story if it doesn't exist
            if (!prevStory) {
              return {
                characters: [newCharacter],
                scenes: [],
                timeline: [],
                contextSummary: "",
              };
            }

            return {
              ...prevStory,
              characters: [...prevStory.characters, newCharacter],
            };
          });
          break;
        case "done":
          setStory(msg.data);
          setIsStreaming(false);
          break;
      }
    };

    wsRef.current = ws;

    return () => {
      // Prevent React's Strict Mode cleanup from dumping a 1006 error into the console
      ws.onerror = null;
      ws.onclose = null;
      ws.close();
    };
  }, [sessionId]);

  const sendDirective = useCallback(
    (prompt) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
      setNarration("");
      setIsStreaming(true);
      wsRef.current.send(JSON.stringify({ prompt }));
    },
    [],
  );

  const resetSession = useCallback(async () => {
    await fetch(`/api/session/${sessionId}/reset`, { method: "POST" });
    setStory(null);
    setNarration("");
  }, [sessionId]);

  return { story, narration, isStreaming, isConnected, sendDirective, resetSession };
}
