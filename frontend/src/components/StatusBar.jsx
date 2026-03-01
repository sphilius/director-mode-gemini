/**
 * StatusBar — shows connection state, live mode indicator, and scene count.
 */
export default function StatusBar({
  isConnected,
  isLive,
  isStreaming,
  isMicActive,
  sceneCount,
  onReset,
}) {
  const statusText = () => {
    if (isMicActive) return "Listening…";
    if (isStreaming) return "Directing…";
    if (isLive) return "Live";
    if (isConnected) return "Connected";
    return "Disconnected";
  };

  return (
    <div className="status-bar">
      <span className={`connection-dot ${isConnected ? "connected" : ""}`} />
      <span className="status-label">{statusText()}</span>
      {isLive && <span className="live-badge">LIVE</span>}
      <span className="scene-count">
        {sceneCount} scene{sceneCount !== 1 ? "s" : ""}
      </span>
      <button className="reset-btn" onClick={onReset} title="Reset session">
        Reset
      </button>
    </div>
  );
}
