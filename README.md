# Clipseek

**Find the moment, not the filename.**

Clipseek turns uploaded videos into a searchable visual library. Describe an object, color, or scene—such as **“a person wearing a red jacket”**—and jump to a relevant clip without manually scrubbing through the recording.

Built with **React, TypeScript, FastAPI, PostgreSQL, YOLOv8, ByteTrack, and CLIP**. The project combines a full-stack user workflow with a background computer-vision pipeline, semantic retrieval, and on-demand video export.

## What it delivers

- **Natural-language video search:** compare text queries with indexed object crops and whole-frame scenes.
- **Account-scoped libraries:** registration, login, refresh tokens, password reset, upload history, and video deletion.
- **Background indexing:** queued/processing/completed/failed states, progress reporting, and recovery of interrupted local jobs.
- **Timestamped results:** rank visual matches, suppress nearby repeated appearances, and play clips with five seconds of context on either side.
- **Flexible infrastructure:** local or S3-compatible storage; a local worker thread or Redis/RQ; pgvector or a PostgreSQL array fallback.

This repository contains the application and tests. A public hosted demo is not currently provided. Sample footage, trained weights, credentials, and uploaded media are excluded from Git.

## Performance experiment

An initial developer-run comparison used the same sample video, approximately **5 sampled frames/second**, and **CLIP batches of 8**:

| Environment | Measured pipeline time |
| --- | ---: |
| Local machine, one baseline run | 96.226 s |
| Colab GPU, run 1 | 22.895 s |
| Colab GPU, run 2 | 22.558 s |
| Colab GPU, run 3 | 21.037 s |
| **Colab GPU median** | **22.558 s** |

The remote median was **4.27× faster**, a **76.6% reduction** relative to the local baseline. The local run computed 803 image embeddings and selected 355 entries for storage.

**Scope:** these are reported development measurements, not a controlled hardware study or production latency guarantee. The benchmark includes decoding, detection, tracking, image preparation, embedding, and filtering; it mocks database operations and excludes upload, queue wait, explicit model warmup, and clip export. Exact hardware and dependency versions were not captured with these results, and remote embedding counts were not recorded here. A reproducible comparison should record these details and evaluate output quality as well as time.

## Architecture

```mermaid
flowchart TD
    A[React upload] --> B[FastAPI validates and saves video]
    B --> C[Video record and queued job]
    C --> D[Worker samples frames with OpenCV]
    D --> E[YOLO detects objects]
    E --> F[ByteTrack assigns track IDs]
    F --> G[Crop objects and skip repeated appearances]
    D --> H[Periodic whole-frame images]
    G --> I[Batch CLIP image embeddings]
    H --> I
    I --> J[Filter similar embeddings]
    J --> K[(PostgreSQL visual index)]
    L[Text query] --> M[CLIP text embedding]
    M --> N[Similarity search and result filtering]
    K --> N
    N --> O[Timestamped matches]
    O --> P[FFmpeg exports or reuses cached clip]
    B --> P
    P --> Q[Browser playback]
```

### Index once, search repeatedly

1. **Upload:** validate type, size, duration, and account limits; save the original; create a queued video record. Defaults are 2 GiB and 10 minutes per video.
2. **Detect and track:** YOLOv8n detects objects in sampled frames. ByteTrack connects observations across time. Track IDs describe continuity within a video, not real-world identity.
3. **Reduce repeated work:** a per-track minimum interval and inexpensive appearance/color checks skip redundant crops before CLIP. Whole-frame images provide broader scene context.
4. **Embed:** CLIP ViT-B/32 produces normalized 512-dimensional vectors in batches. A second, post-inference similarity gate selects entries to store.
5. **Persist:** store the video ID, track ID, class, confidence, timestamp, frame number, bounding box, and embedding. Original videos remain in file/object storage.
6. **Retrieve:** encode the query with CLIP and rank stored vectors. Apply account/video/class filters, absolute and relative score thresholds, and temporal grouping.
7. **Play:** generate a browser-compatible WebM segment around the match with FFmpeg. Cache generated clips locally for reuse.

### Engineering choices

| Choice | Reason and tradeoff |
| --- | --- |
| Approximately 5 FPS sampling | Reduces detector calls; brief appearances between samples can be missed. |
| Separate pre- and post-CLIP filters | The first saves inference work; the second reduces stored repetition. |
| Object crops plus scene embeddings | Captures object detail and broader context; adds embedding work. |
| Batched CLIP inference | Amortizes overhead; larger batches require more device memory and benchmarking. |
| One local indexing job at a time | Limits resource contention and shared-model concurrency; queued videos wait. |
| pgvector/HNSW with a `REAL[]` fallback | Supports vector retrieval while allowing local use without the extension. |
| On-demand clip encoding | Avoids precomputing every segment; first playback includes encoding latency. |
| Strict relevance filtering | Rejects weak matches, potentially excluding some relevant results. |

CUDA is selected automatically when available. Detection outputs move to CPU/NumPy for ByteTrack. `IVS_CLIP_BATCH_SIZE` controls CLIP batching; YOLO currently processes one sampled frame per call.

## Local setup

### Prerequisites

- Python 3.11+; CI uses Python 3.12.
- Node.js 22.12+ and npm.
- PostgreSQL with a database your configured user can initialize.
- Internet access for the first model download.
- Optional: an NVIDIA GPU and compatible CUDA-enabled PyTorch installation.

Redis and pgvector are optional locally. FFmpeg uses the system installation or the `imageio-ffmpeg` bundled binary.

### 1. Install the backend

```sh
git clone https://github.com/muaz-nadeem/clipseek.git
cd clipseek/backend
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```sh
# macOS / Linux
source .venv/bin/activate
```

```sh
python -m pip install -r requirements-dev.txt
```

Copy `backend/.env.example` to `backend/.env`. Configure your own PostgreSQL connection and generate a signing secret:

```sh
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Example settings (replace the placeholders):

```dotenv
IVS_ENV=development
IVS_DATABASE_URL=postgresql://YOUR_USER:YOUR_PASSWORD@localhost:5432/intelligent_video_search
IVS_JWT_SECRET=YOUR_GENERATED_SECRET
IVS_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

Create the database using your PostgreSQL administrator account, for example:

```sh
createdb -U postgres intelligent_video_search
```

The API initializes tables on startup. If pgvector is unavailable, it uses the array schema unless `IVS_REQUIRE_PGVECTOR=1` is set.

### 2. Download models

Run from `backend/` with the environment active:

```sh
python -c "from pathlib import Path; from ultralytics import YOLO; Path('models').mkdir(exist_ok=True); YOLO('yolov8n.pt').save('models/yolov8n.pt')"
python -c "from transformers import CLIPModel, CLIPProcessor; name='openai/clip-vit-base-patch32'; CLIPModel.from_pretrained(name); CLIPProcessor.from_pretrained(name)"
```

YOLO reads `backend/models/yolov8n.pt`; CLIP uses the Hugging Face model cache. Downloading weights does not require a paid inference API.

### 3. Start the API

```sh
python -m uvicorn app.main:app --reload --port 8001
```

Development docs: [localhost:8001/docs](http://127.0.0.1:8001/docs). Health: [localhost:8001/health](http://127.0.0.1:8001/health).

Without Redis, indexing uses a local background thread. If Redis is reachable, start the RQ worker too; otherwise jobs wait in its queue. The standard RQ worker is intended for Linux/WSL:

```sh
python -m app.workers.worker
```

### 4. Start the frontend

In another terminal, from the repository root:

```sh
cd frontend
npm ci
```

Copy `frontend/.env.example` to `frontend/.env`, then:

```sh
npm run dev
```

Open [localhost:5173](http://127.0.0.1:5173), create an account, upload a video, wait for indexing, and enter a visual description. Authentication is enabled by default.

## Key configuration

Defaults live in [`backend/app/config.py`](backend/app/config.py). Restart the API/worker after changing settings.

| Variable | Default | Purpose |
| --- | --- | --- |
| `IVS_INDEX_TARGET_FPS` | `5` | Approximate detection sampling rate |
| `IVS_INDEX_STRIDE` | Unset | Explicit frame interval; overrides target FPS |
| `IVS_CLIP_BATCH_SIZE` | `8` | Images per CLIP call |
| `IVS_TORCH_THREADS` | Up to `4` | CPU inference thread budget |
| `IVS_EMBED_MIN_GAP_SEC` | `0.5` | Minimum video-time gap between embeddings per track |
| `IVS_EMBED_HEARTBEAT_SEC` | `2` | Periodically re-embed unchanged appearances |
| `IVS_SCENE_INTERVAL_SEC` | `2` | Whole-frame interval; `0` disables it |
| `IVS_CHANGE_THRESHOLD` | `0.90` | Store when similarity to the last stored embedding drops below this |
| `IVS_MAX_GAP_SEC` | `15` | Store a periodic observation even if similar |
| `IVS_SEARCH_MIN_SCORE` | `0.23` | Absolute retrieval-score floor |
| `IVS_SEARCH_SCORE_MARGIN` | `0.04` | Maximum score drop below the best candidate |
| `IVS_CLIP_PADDING_SEC` | `5` | Playback context on either side of a match |

Batch sizes primarily change throughput and memory use. Sampling and embedding gaps affect what the index captures. Reindex existing videos after changing capture policies. Changing the embedding model also requires compatible query embeddings and rebuilding the stored index.

## Validation and benchmarking

From `backend/`:

```sh
python -m pytest tests -q
```

From `frontend/`:

```sh
npm test
npm run build
npm run lint
```

Tests cover auth helpers, upload limits, sampling, appearance gates, relevance filtering, indexing failures, worker initialization/recovery, storage paths, and clip export. GitHub Actions runs a lightweight backend subset: ML-dependent tests skip when their dependencies are absent. Install the full development requirements to exercise additional tests.

For a real upload → indexing → search → clip-decoding check, put your own test video at `backend/samples/traffic-video.mp4` and run from `backend/`:

```sh
python -m scripts.smoke_test
```

Requires cached models and PostgreSQL permissions to create a temporary schema. The smoke test checks authentication and cross-account access, uses isolated media/schema, and cleans up. It covers local-thread and array-storage paths, not Redis, S3, or browser playback.

For inference benchmarking without database writes:

```sh
python -m scripts.benchmark_indexing samples/traffic-video.mp4 --output benchmark.json
```

Run the same video/settings three times per environment and compare medians. Record hardware, package versions, video properties, embedded/stored counts, and retrieval quality. Test CLIP batches 8, 16, and 32 independently of FPS changes. Check CUDA with:

```sh
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

## Deployment boundaries

The included [`backend/Dockerfile`](backend/Dockerfile) is a **CPU backend image**, not the GPU benchmark environment:

```sh
docker build -t clipseek-api ./backend
```

Provide `IVS_ENV=production`, a strong `IVS_JWT_SECRET`, `IVS_DATABASE_URL`, explicit `IVS_CORS_ORIGINS`, and `IVS_PUBLIC_APP_URL` at runtime. Make model weights/cache available, set `IVS_YOLO_MODEL` if needed, and persist `/data/storage` or configure S3-compatible storage. The image serves port 8000.

A separate remote GPU worker needs a shared queue, database, accessible video storage, and a CUDA-compatible runtime. A laptop-local video path is inaccessible to a remote worker. Hugging Face hosting and a dedicated remote indexing API have not been deployed or validated in this repository.

The frontend builds to `frontend/dist`; configure the host for SPA route fallback. Set `VITE_API_URL` before building. Configure SMTP for production password-reset email delivery.

## Repository map

```text
backend/
  app/api/          Auth, upload, library, search, clips, health
  app/ml/           Detector, tracker, encoders, appearance gates
  app/services/     Indexing, retrieval, clip export, storage
  app/database/     PostgreSQL schemas and queries
  app/workers/      Queue, RQ worker, interrupted-job recovery
  scripts/          Benchmark, smoke test, migration, experiments
  tests/            Backend regression tests
frontend/
  src/app/          Routing and app composition
  src/features/     Auth, library, search, marketing, legal
  src/shared/       API client and shared components
.github/workflows/  Automated checks
```

## Limitations and next steps

- Visual similarity scores are not probabilities. Detection, tracking, sampling, and filtering can miss relevant moments.
- No speech transcription, dedicated OCR, persistent person identification, or explicit temporal-action reasoning is implemented.
- Models are pretrained; uploaded footage is processed with inference rather than training.
- Playback windows surround observations, not inferred event boundaries.
- Generated clip caches may remain after video deletion; account deletion is not exposed in the UI.
- These benchmarks do not establish production throughput, end-to-end latency, or retrieval accuracy on a labeled evaluation set.

Next experiments: capture per-stage GPU timings, tune CLIP batches, evaluate batched detection, build a labeled retrieval evaluation set, and compare complete upload-to-searchable latency with a remote worker.

## Credits

Built by [Muaz Nadeem](https://github.com/muaz-nadeem). Uses Ultralytics YOLO/ByteTrack, OpenAI CLIP via Transformers, and FFmpeg. Third-party code, models, and media retain their respective licenses. The landing-page preview is illustrative; photo attribution is in [`frontend/public/image-credits.txt`](frontend/public/image-credits.txt).
