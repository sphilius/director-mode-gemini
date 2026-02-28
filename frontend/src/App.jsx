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
    isStreaming,
    isConnected,
    sendDirective,
    resetSession,
  } = useDirectorSession(sessionId);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Director Mode</h1>
        <span className="subtitle">Powered by Gemini</span>
      </header>

      <main className="app-main">
        <DirectorCanvas narration={narration} isStreaming={isStreaming} />

        <aside className="app-sidebar">
          <StoryTimeline scenes={story?.scenes ?? []} />
        </aside>
      </main>

      <footer className="app-footer">
        <VoiceControls
          onDirective={sendDirective}
          disabled={isStreaming}
        />
        <StatusBar
          isConnected={isConnected}
          isStreaming={isStreaming}
          sceneCount={story?.scenes?.length ?? 0}
          onReset={resetSession}
        />
      </footer>
    </div>
  );
}
