import type { SearchResult } from "../../../shared/api/client";

type Props = {
  results: SearchResult[];
  selectedId: number | null;
  onSelect: (result: SearchResult) => void;
  videoNames?: Record<number, string>;
};

export function SearchResults({ results, selectedId, onSelect, videoNames }: Props) {
  if (results.length === 0) {
    return <div className="no-results"><h3>No strong matches found.</h3><p className="muted">Try a simpler visual description or remove an object filter.</p></div>;
  }

  return (
    <ul className="results">
      {results.map((r) => (
        <li key={r.object_id}>
          <button
            type="button"
            className={selectedId === r.object_id ? "result active" : "result"}
            aria-pressed={selectedId === r.object_id}
            onClick={() => onSelect(r)}
          >
            <span className="result-time">
              {r.start_label} – {r.end_label}
            </span>
            <span className="result-main">
              {r.track_id < 0 ? "Scene match" : r.class_name}
            </span>
            <span className="result-score" title="Visual similarity score, not a probability">{r.score.toFixed(3)}</span>
            {videoNames && <span className="result-filename">{videoNames[r.video_id] ?? `Video ${r.video_id}`}</span>}
          </button>
        </li>
      ))}
    </ul>
  );
}
