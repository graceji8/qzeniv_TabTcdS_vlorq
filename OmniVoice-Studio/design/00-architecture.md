# 00 · System Architecture

End-to-end picture of the mature product. Every box is either a module that already exists or a module the roadmap creates. No boxes are aspirational.

## Logical architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      CLIENT (Tauri shell)                                  │
│                                                                                            │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐     │
│  │                             React 19 + TypeScript                                 │     │
│  │                                                                                   │     │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │     │
│  │  │Launchpad │  │Dub Studio│  │  Voice   │  │Translate │  │  Export  │   …         │     │
│  │  │  page    │  │  page    │  │  Library │  │ Workbench│  │  Center  │             │     │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘             │     │
│  │       └─────────────┴─────────────┼─────────────┴─────────────┘                   │     │
│  │                     ┌─────────────▼──────────────┐                                │     │
│  │                     │   Zustand stores           │   project · dub · voice · ui   │     │
│  │                     └─────────────┬──────────────┘                                │     │
│  │                     ┌─────────────▼──────────────┐                                │     │
│  │                     │   API client (typed)       │   fetch + SSE + error mapper   │     │
│  │                     └─────────────┬──────────────┘                                │     │
│  └─────────────────────────────────── │ ──────────────────────────────────────────── │     │
└─────────────────────────────────────  │  ──────────────────────────────────────────────────┘
                                        │ HTTP + SSE (localhost:8000)
┌───────────────────────────────────── ─│ ──────────────────────────────────────────────────┐
│                                       │                                                   │
│                                       ▼      FastAPI (uvicorn, single process, async)     │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐     │
│  │  ROUTERS (thin; HTTP concerns only)                                              │     │
│  │  system · profiles · projects · dub_core · dub_translate · dub_generate          │     │
│  │  dub_export · glossary · tools · exports · generation                            │     │
│  └──────────────────────────────────────────┬───────────────────────────────────────┘     │
│                                             │                                             │
│  ┌──────────────────────────────────────────▼───────────────────────────────────────┐     │
│  │  SERVICES (business logic)                                                       │     │
│  │  dub_pipeline · subtitle_segmenter · translator · speech_rate · glossary         │     │
│  │  audio_dsp · ffmpeg_utils · rvc · preview                                        │     │
│  └─────────┬───────────────────┬──────────────────┬──────────────────┬──────────────┘     │
│            │                   │                  │                  │                    │
│  ┌─────────▼────────┐  ┌───────▼──────┐  ┌────────▼────────┐  ┌──────▼───────────┐        │
│  │  ENGINE ADAPTERS │  │  JOB STORE   │  │    DB LAYER     │  │  TELEMETRY       │        │
│  │  tts_backend     │  │  Persistent  │  │  SQLite + WAL   │  │  structured logs │        │
│  │  asr_backend     │  │  queue +     │  │  Alembic        │  │  Prometheus      │        │
│  │  llm_backend     │  │  checkpoints │  │  migrations     │  │  OpenTelemetry   │        │
│  └─────────┬────────┘  └──────┬───────┘  └─────────────────┘  └──────────────────┘        │
│            │                  │                                                           │
│  ┌─────────▼──────────────────▼──────────────────────────────────────────────────┐        │
│  │  WORKER POOL                                                                  │        │
│  │  GPU worker (serial, pinned to device)  ·  CPU workers (ffmpeg, demucs, I/O)  │        │
│  └─────────┬─────────────────────────────────────────────────────────────────────┘        │
└────────────│──────────────────────────────────────────────────────────────────────────────┘
             │
┌────────────│──────────────────────────────────────────────────────────────────────────────┐
│            ▼                ENGINES (pluggable, optional, gated by capability)            │
│                                                                                           │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐       │
│  │   TTS          │  │   ASR          │  │   LLM          │  │   AUDIO            │       │
│  │                │  │                │  │                │  │                    │       │
│  │ ● OmniVoice    │  │ ● WhisperX     │  │ ● Ollama (def) │  │ ● demucs           │       │
│  │ ○ VoxCPM2      │  │ ○ mlx-whisper  │  │ ○ OpenAI (opt) │  │ ● pedalboard       │       │
│  │ ○ user-plugin  │  │ ○ faster-whisp │  │ ○ Claude (opt) │  │ ● pyannote         │       │
│  └────────────────┘  └────────────────┘  └────────────────┘  └────────────────────┘       │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

## Request lifecycle — "generate dub for segment N"

```
USER clicks [Generate]
    │
    ▼
Zustand store     ─► marks segment N as "pending"
    │
    ▼
API client        ─► POST /dub/generate/{job_id}
    │                                                    (single HTTP call returns task_id)
    ▼
Router            ─► validates request, creates job step in job_store
    │
    ▼
dub_pipeline      ─► plans steps for segment N
    │                   1. look up voice profile
    │                   2. speech-rate fit (Phase 4)
    │                   3. call tts_backend.generate()
    │                   4. apply mastering + normalize
    │                   5. persist segment WAV + update checkpoint
    │
    ▼
GPU worker        ─► runs model inference serially (one at a time)
    │
    ▼
SSE stream        ─► emits {type: progress}, {type: segment_done}, {type: done}
    │
    ▼
Zustand store     ─► reconciles updates, UI re-renders
```

## Data model (simplified)

```
┌─────────────────────┐       ┌─────────────────────┐       ┌─────────────────────┐
│   studio_projects   │──1:n──│       jobs          │──1:n──│     job_steps       │
│─────────────────────│       │─────────────────────│       │─────────────────────│
│ id                  │       │ id                  │       │ id                  │
│ name                │       │ project_id (fk)     │       │ job_id (fk)         │
│ video_path          │       │ state               │       │ stage (asr/tx/tts…) │
│ state_json          │       │ created_at          │       │ segment_id          │
│ created_at          │       │ updated_at          │       │ status              │
│ updated_at          │       │ engine_used         │       │ artifact_path       │
└─────────────────────┘       └─────────────────────┘       │ checksum            │
                                                            │ error               │
┌─────────────────────┐       ┌─────────────────────┐       └─────────────────────┘
│   voice_profiles    │       │        terms        │
│─────────────────────│       │─────────────────────│
│ id                  │       │ id                  │
│ name                │       │ project_id (fk)     │
│ ref_audio_path      │       │ source              │
│ ref_text            │       │ target              │
│ instruct            │       │ note                │
│ language            │       └─────────────────────┘
│ is_locked           │
│ seed                │       ┌─────────────────────┐
└─────────────────────┘       │   export_history    │
                              └─────────────────────┘
```

## Failure semantics

```
┌─────────────────┐    crash    ┌─────────────────┐    restart    ┌─────────────────┐
│ job: running    │────────────>│ server: down    │──────────────>│ server: up      │
│ step 7/10 done  │             │                 │               │ resume from 8   │
└─────────────────┘             └─────────────────┘               └─────────────────┘
         │                                                                 │
         │  job_store is durable (SQLite WAL)                              │
         │  artifacts are on disk, hashed                                  │
         │  SSE listeners re-subscribe, receive replay of last 50 events ─┘
         │
```

**Key invariant:** a running dub is safe against `kill -9`. The only loss is the in-flight segment, which re-runs on resume.

## Deployment topologies

```
TOPOLOGY A — Desktop (default)
┌─────────────────────────────────┐
│  Tauri app (single binary)      │
│  ├── React frontend (bundled)   │
│  ├── FastAPI sidecar (embedded) │
│  └── Engines (local weights)    │
└─────────────────────────────────┘

TOPOLOGY B — Single-machine server
┌─────────────────────────────────┐
│  docker compose up              │
│  ├── api (FastAPI)              │
│  ├── frontend (static /dist)    │
│  └── volumes: models, outputs   │
└─────────────────────────────────┘

TOPOLOGY C — Team (Phase 5)
┌─────────────────────────────────┐      ┌─────────────────────────────────┐
│   api x N (stateless)           │◄────►│   Postgres + Redis              │
│   worker x M (GPU-affined)      │      │   (job queue, listeners, data)  │
│   frontend (CDN)                │      └─────────────────────────────────┘
└─────────────────────────────────┘
```
