"""Extract browser-compatible WebM clips with FFmpeg."""
from __future__ import annotations

import math
import shutil
import subprocess
import uuid
from pathlib import Path

from app.config import CLIPS_DIR
from app.database.connection import db_session
from app.database import models
from app.services.storage import get_storage
from app.utils.video import probe_duration


def ffmpeg_executable() -> str:
    installed = shutil.which("ffmpeg")
    if installed:
        return installed
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


class ClipService:
    def extract_clip(self, video_id: int, start: float, end: float) -> Path:
        if not math.isfinite(start) or not math.isfinite(end) or end <= start:
            raise ValueError("end must be greater than start and both times must be finite")
        storage = get_storage()
        with db_session() as conn:
            video = models.get_video(conn, video_id)
            if video is None:
                raise FileNotFoundError(f"Video {video_id} not found")
            source = storage.local_path(video.stored_path, "videos")
            if not source.exists():
                raise FileNotFoundError(f"Video file missing: {source}")
        duration = probe_duration(str(source))
        if duration is not None:
            end = min(end, duration)
        start = max(0.0, start)
        if end <= start:
            raise ValueError("Clip range falls outside the video")

        # New cache format avoids reusing the old, browser-incompatible mp4v clips.
        out_path = CLIPS_DIR / f"video{video_id}_webm_v1_{start:.3f}_{end:.3f}.webm"
        if out_path.exists() and out_path.stat().st_size > 0:
            return out_path
        CLIPS_DIR.mkdir(parents=True, exist_ok=True)
        temporary = CLIPS_DIR / f"{out_path.stem}_{uuid.uuid4().hex}.webm"
        try:
            subprocess.run([
                ffmpeg_executable(), "-nostdin", "-y", "-ss", f"{start:.3f}",
                "-i", str(source), "-t", f"{end - start:.3f}",
                "-map", "0:v:0", "-map", "0:a:0?",
                "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p",
                "-crf", "32", "-b:v", "0", "-deadline", "realtime",
                "-cpu-used", "5", "-row-mt", "1", "-threads", "2",
                "-c:a", "libopus", str(temporary),
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120)
            if not temporary.exists() or temporary.stat().st_size == 0:
                raise RuntimeError("FFmpeg produced an empty clip")
            temporary.replace(out_path)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("Could not encode a browser-compatible clip") from exc
        finally:
            temporary.unlink(missing_ok=True)
        return out_path


clip_extract_service = ClipService()
