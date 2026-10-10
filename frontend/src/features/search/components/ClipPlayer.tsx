import { useEffect, useState } from "react";
import { fetchClipBlob, type SearchResult } from "../../../shared/api/client";

type Props = {
  result: SearchResult | null;
};

export function ClipPlayer({ result }: Props) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;

    async function load() {
      setSrc(null);
      setError(null);
      if (!result) {
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        objectUrl = await fetchClipBlob(result.clip_url);
        if (cancelled) {
          URL.revokeObjectURL(objectUrl);
          objectUrl = null;
        } else {
          setSrc(objectUrl);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Clip load failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [result, attempt]);

  if (!result) {
    return <div className="player empty-player">Select a result to play its clip</div>;
  }

  return (
    <div className="player">
      <div className="player-meta">
        <span>
          {result.start_label} → {result.end_label}
        </span>
        <span>
          {result.class_name} · score {result.score.toFixed(3)}
        </span>
      </div>
      {loading && <p>Loading clip…</p>}
      {error && <p className="error">{error} <button type="button" onClick={() => setAttempt((value) => value + 1)}>Retry clip</button></p>}
      {src && <video key={src} src={src} controls autoPlay playsInline
        onError={() => setError("This clip could not be played.")}
      />}
    </div>
  );
}
