/**
 * StatusBar — shows connection state, streaming indicator, and scene count.
 */
export default function StatusBar({
  isConnected,
  isStreaming,
  sceneCount,
  onReset,
}) {
  return (
    <div className="status-bar">
      <span className={`connection-dot ${isConnected ? "connected" : ""}`} />
      <span className="status-label">
        {isStreaming
          ? "Directing…"
          : isConnected
            ? "Connected"
            : "Disconnected"}
      </span>
      <span className="scene-count">
        {sceneCount} scene{sceneCount !== 1 ? "s" : ""}
      </span>
      <button className="reset-btn" onClick={onReset} title="Reset session">
        Reset
      </button>
    </div>
  );
}
