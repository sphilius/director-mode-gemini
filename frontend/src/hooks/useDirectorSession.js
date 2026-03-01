import { useCallback, useEffect, useRef, useState } from "react";

const WS_BASE =
  import.meta.env.VITE_WS_URL ??
  `ws://${window.location.hostname}:8000`;

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
    ws.onclose = () => setIsConnected(false);
    ws.onerror = () => setIsConnected(false);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      switch (msg.type) {
        case "token":
          setNarration((prev) => prev + msg.data);
          break;
        case "state_update":
          // Individual state mutation — handled on "done" with full story
          break;
        case "done":
          setStory(msg.data);
          setIsStreaming(false);
          break;
      }
    };

    wsRef.current = ws;

    return () => {
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
