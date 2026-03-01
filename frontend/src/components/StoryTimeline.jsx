/**
 * StoryTimeline — vertical list of scenes showing the story progression.
 */
export default function StoryTimeline({ scenes }) {
  if (!scenes.length) {
    return (
      <div className="story-timeline empty">
        <p>No scenes yet.</p>
      </div>
    );
  }

  return (
    <div className="story-timeline">
      <h2>Timeline</h2>
      <ol className="timeline-list">
        {scenes.map((scene, i) => (
          <li key={scene.id ?? i} className="timeline-item">
            <span className={`mood-badge mood-${scene.mood}`}>
              {scene.mood}
            </span>
            <strong>{scene.title}</strong>
            <p>{scene.description?.slice(0, 120)}…</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
