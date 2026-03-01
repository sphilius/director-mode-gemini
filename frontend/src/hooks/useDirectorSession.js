import { useCallback, useEffect, useRef, useState } from "react";

const WS_BASE =
  import.meta.env.VITE_WS_URL ??
  `ws://${window.location.hostname}:8000`;

const API_BASE =
  import.meta.env.VITE_API_URL ??
  `http://${window.location.hostname}:8000`;

/**
 * useDirectorSession — manages the bidirectional Live API connection.
 *
 * Handles:
 * - AudioWorklet mic capture → PCM 16-bit 16kHz → WebSocket binary frames
 * - WebSocket binary frames (24kHz PCM) → AudioContext playback
 * - JSON control messages (text, state_update, transcript, turn_complete)
 */
export default function useDirectorSession(sessionId) {
  const [story, setStory] = useState(null);
  const [narration, setNarration] = useState("");
  const [transcriptIn, setTranscriptIn] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const [isMicActive, setIsMicActive] = useState(false);

  const wsRef = useRef(null);
  const audioCtxRef = useRef(null);
  const workletNodeRef = useRef(null);
  const streamRef = useRef(null);
  const playbackQueueRef = useRef([]);
  const isPlayingRef = useRef(false);

  // ----- Audio playback (24kHz PCM from server) -----

  const getAudioContext = useCallback(() => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000,
      });
    }
    return audioCtxRef.current;
  }, []);

  const enqueueAudio = useCallback((pcmBytes) => {
    playbackQueueRef.current.push(pcmBytes);
    drainPlaybackQueue();
  }, []);

  const drainPlaybackQueue = useCallback(() => {
    if (isPlayingRef.current || playbackQueueRef.current.length === 0) return;
    isPlayingRef.current = true;

    const ctx = getAudioContext();
    const pcm = playbackQueueRef.current.shift();
    const int16 = new Int16Array(pcm.buffer, pcm.byteOffset, pcm.byteLength / 2);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768;
    }

    const buffer = ctx.createBuffer(1, float32.length, 24000);
    buffer.getChannelData(0).set(float32);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.onended = () => {
      isPlayingRef.current = false;
      drainPlaybackQueue();
    };
    source.start();
  }, [getAudioContext]);

  // ----- WebSocket connection -----

  const connectLive = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_BASE}/ws/live/${sessionId}`);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsLive(false);
      setIsStreaming(false);
    };

    ws.onerror = () => {
      setIsConnected(false);
      setIsLive(false);
    };

    ws.onmessage = (event) => {
      // Binary frame → audio playback
      if (event.data instanceof ArrayBuffer) {
        setIsStreaming(true);
        enqueueAudio(new Uint8Array(event.data));
        return;
      }

      // Text frame → JSON message
      const msg = JSON.parse(event.data);

      switch (msg.type) {
        case "connected":
          setIsLive(true);
          break;
        case "text":
        case "token":
          setNarration((prev) => prev + msg.data);
          setIsStreaming(true);
          break;
        case "transcript_in":
          setTranscriptIn(msg.data);
          break;
        case "transcript_out":
          setNarration((prev) => prev + msg.data);
          break;
        case "state_update":
          // State updates applied; full story comes on turn_complete
          break;
        case "turn_complete":
        case "done":
          setStory(msg.data);
          setIsStreaming(false);
          break;
        case "error":
          console.error("Live session error:", msg.data);
          setIsStreaming(false);
          break;
      }
    };

    wsRef.current = ws;
  }, [sessionId, enqueueAudio]);

  // Auto-connect on mount
  useEffect(() => {
    connectLive();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (workletNodeRef.current) {
        workletNodeRef.current.disconnect();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, [connectLive]);

  // ----- Microphone capture via AudioWorklet -----

  const startMic = useCallback(async () => {
    if (isMicActive) return;

    const ctx = getAudioContext();
    if (ctx.state === "suspended") await ctx.resume();

    // Load the AudioWorklet processor
    try {
      await ctx.audioWorklet.addModule("/audio-processor.js");
    } catch {
      // Already loaded — ignore
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    streamRef.current = stream;

    const source = ctx.createMediaStreamSource(stream);
    const worklet = new AudioWorkletNode(ctx, "audio-capture-processor");

    worklet.port.onmessage = (e) => {
      if (e.data.type === "audio" && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(e.data.pcm);
      }
    };

    source.connect(worklet);
    workletNodeRef.current = worklet;
    setIsMicActive(true);
  }, [isMicActive, getAudioContext]);

  const stopMic = useCallback(() => {
    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setIsMicActive(false);
  }, []);

  const toggleMic = useCallback(() => {
    if (isMicActive) {
      stopMic();
    } else {
      startMic();
    }
  }, [isMicActive, startMic, stopMic]);

  // ----- Send text directive -----

  const sendDirective = useCallback(
    (prompt) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
      setNarration("");
      setTranscriptIn("");
      setIsStreaming(true);

      if (isLive) {
        // Send via Live API text channel
        wsRef.current.send(JSON.stringify({ type: "text", data: prompt }));
      } else {
        // Fallback: send as standard streaming directive
        wsRef.current.send(JSON.stringify({ prompt }));
      }
    },
    [isLive],
  );

  // ----- Interrupt -----

  const interruptGeneration = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "interrupt" }));
    // Clear playback queue
    playbackQueueRef.current = [];
    setIsStreaming(false);
  }, []);

  // ----- Reset session -----

  const resetSession = useCallback(async () => {
    stopMic();
    await fetch(`${API_BASE}/api/session/${sessionId}/reset`, { method: "POST" });
    setStory(null);
    setNarration("");
    setTranscriptIn("");
    playbackQueueRef.current = [];
  }, [sessionId, stopMic]);

  return {
    story,
    narration,
    transcriptIn,
    isStreaming,
    isConnected,
    isLive,
    isMicActive,
    sendDirective,
    toggleMic,
    interruptGeneration,
    resetSession,
  };
}
