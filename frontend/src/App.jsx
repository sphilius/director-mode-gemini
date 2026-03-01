import { useState } from "react";
import DirectorCanvas from "./components/DirectorCanvas";
import VoiceControls from "./components/VoiceControls";
import StatusBar from "./components/StatusBar";
import StoryTimeline from "./components/StoryTimeline";
import useDirectorSession from "./hooks/useDirectorSession";

export default function App() {
  const [sessionId] = useState("default");
  const {
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
  } = useDirectorSession(sessionId);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Director Mode</h1>
        <span className="subtitle">Powered by Gemini</span>
      </header>

      <main className="app-main">
        <DirectorCanvas
          narration={narration}
          transcriptIn={transcriptIn}
          isStreaming={isStreaming}
        />

        <aside className="app-sidebar">
          <StoryTimeline scenes={story?.scenes ?? []} />
        </aside>
      </main>

      <footer className="app-footer">
        <VoiceControls
          onDirective={sendDirective}
          onToggleMic={toggleMic}
          onInterrupt={interruptGeneration}
          isMicActive={isMicActive}
          isStreaming={isStreaming}
          isLive={isLive}
        />
        <StatusBar
          isConnected={isConnected}
          isLive={isLive}
          isStreaming={isStreaming}
          isMicActive={isMicActive}
          sceneCount={story?.scenes?.length ?? 0}
          onReset={resetSession}
        />
      </footer>
    </div>
  );
}
