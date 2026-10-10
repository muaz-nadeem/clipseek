import { useEffect, useState } from "react";
import type { VideoStatus } from "../../../shared/api/client";
import { getVideo } from "../../../shared/api/client";

type Props = {
  videoId: number | null;
  onCompleted?: (video: VideoStatus) => void;
};

export function VideoStatusPoll({ videoId, onCompleted }: Props) {
  const [video, setVideo] = useState<VideoStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setVideo(null);
    setError(null);
    if (videoId == null) return;
    let cancelled = false;
    let timer: number | undefined;

    const tick = async () => {
      try {
        const v = await getVideo(videoId);
        if (cancelled) return;
        setVideo(v);
        setError(null);
        if (v.status === "completed" || v.status === "failed") {
          if (v.status === "completed") onCompleted?.(v);
          return;
        }
        timer = window.setTimeout(tick, 2000);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Status check failed");
        timer = window.setTimeout(tick, 3000);
      }
    };

    tick();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [videoId, onCompleted]);

  if (videoId == null) return null;

  return (
    <div className="status-panel">
      <p className="status-label">Video #{videoId}</p>
      {error && <p className="error">{error}</p>}
      {video && (
        <>
          <p className="status-filename">{video.filename}</p>
          <p className={`status-pill status-${video.status}`}>
            {video.status === "processing" ? "Upload complete · AI indexing" :
              video.status === "queued" ? "Upload complete · Waiting to index" :
              video.status === "completed" ? "Ready to search" : video.status}
          </p>
          {(video.status === "queued" || video.status === "processing") && (
            <div className="progress-track" aria-label="Indexing progress">
              <div
                className="progress-fill"
                style={{ width: `${Math.round((video.progress || 0) * 100)}%` }}
              />
            </div>
          )}
          <p className="muted">
            {video.status === "processing" ? `Indexing ${Math.round((video.progress || 0) * 100)}%` :
              video.status === "completed" ? "Indexing complete" : ""}
            {video.object_count ? ` · ${video.object_count} indexed appearances` : ""}
          </p>
          {video.error_message && <p className="error">{video.error_message}</p>}
        </>
      )}
    </div>
  );
}
