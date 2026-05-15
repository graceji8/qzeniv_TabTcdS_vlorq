# 07 · Tools

Standalone utilities exposed as first-class features, not buried inside the dub pipeline. Every tool here is something a user might reach for independently — e.g. "I just want to strip the vocals from this song" or "I already have subtitles, just align them."

## View

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ☰ ›  Tools                                                                           ●Ready    │
├───────┬─────────────────────────────────────────────────────────────────────────────────────────┤
│       │                                                                                         │
│       │   ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐                │
│  🎬   │   │                    │  │                    │  │                    │                │
│       │   │       🎧           │  │       📐           │  │       🔗           │                │
│  🧬   │   │  Vocal separation  │  │  Align subtitles   │  │  Merge SRT+video   │                │
│       │   │                    │  │                    │  │                    │                │
│  📚   │   │  Split speech from │  │  Force-align an    │  │  Mux external      │                │
│       │   │  music/background  │  │  existing SRT to   │  │  subtitle file     │                │
│  🛠◄  │   │  using demucs.     │  │  an audio file.    │  │  into an MP4.      │                │
│       │   │                    │  │                    │  │                    │                │
│  📦   │   │     [ open ]       │  │     [ open ]       │  │     [ open ]       │                │
│       │   └────────────────────┘  └────────────────────┘  └────────────────────┘                │
│  ⚙   │                                                                                         │
│       │   ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐                │
│       │   │                    │  │                    │  │                    │                │
│       │   │       📝           │  │       🔊           │  │       📥           │                │
│       │   │  Transcribe only   │  │  Convert format    │  │  YouTube ingest    │                │
│       │   │                    │  │                    │  │                    │                │
│       │   │  Audio or video →  │  │  WAV ↔ MP3 ↔ OGG  │  │  Pull audio/video  │                │
│       │   │  SRT/VTT/TXT       │  │  with loudness     │  │  from a URL        │                │
│       │   │  with diarisation. │  │  normalisation.    │  │  via yt-dlp.       │                │
│       │   │                    │  │                    │  │                    │                │
│       │   │     [ open ]       │  │     [ open ]       │  │     [ open ]       │                │
│       │   └────────────────────┘  └────────────────────┘  └────────────────────┘                │
│       │                                                                                         │
│       │   ┌────────────────────┐  ┌────────────────────┐                                        │
│       │   │                    │  │                    │                                        │
│       │   │       🧹           │  │       🔍           │                                        │
│       │   │  Clean audio       │  │  Diagnose file     │                                        │
│       │   │                    │  │                    │                                        │
│       │   │  De-noise,         │  │  Probe codecs,     │                                        │
│       │   │  de-reverb, fix    │  │  streams, bit      │                                        │
│       │   │  plosives.         │  │  depth, loudness.  │                                        │
│       │   │                    │  │                    │                                        │
│       │   │     [ open ]       │  │     [ open ]       │                                        │
│       │   └────────────────────┘  └────────────────────┘                                        │
│       │                                                                                         │
└───────┴─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Example tool surface — Align subtitles

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Align subtitles                                                           ✕     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   Audio / video                                                                 │
│   [ lecture-12.mp4                                                     [📂] ]   │
│                                                                                 │
│   Subtitle file (the timings may be off)                                        │
│   [ lecture-12.draft.srt                                               [📂] ]   │
│                                                                                 │
│   Language            [ en-US ▾ ]                                               │
│                                                                                 │
│   Method              ● force-align (wav2vec)   ○ anchor-match                  │
│   Max shift           [ ± 500 ms ]                                              │
│                                                                                 │
│   Output                                                                        │
│   [ lecture-12.aligned.srt                                             [📂] ]   │
│   ☑ Keep original as .bak                                                       │
│                                                                                 │
│   [Cancel]                                                        [ Align ▶ ]   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Example tool surface — Vocal separation

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ Vocal separation                                                          ✕     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   Input                                                                         │
│   [ song.mp3                                                           [📂] ]   │
│                                                                                 │
│   Model          ● htdemucs    ○ htdemucs_ft    ○ mdx                           │
│   Precision      ● float32     ○ float16 (faster, slightly lower quality)       │
│   Shifts         [ 1 ]    Overlap [ 0.25 ]                                      │
│                                                                                 │
│   Outputs to produce                                                            │
│     ☑ vocals.wav                                                                │
│     ☑ no_vocals.wav                                                             │
│     ☐ drums.wav                                                                 │
│     ☐ bass.wav                                                                  │
│     ☐ other.wav                                                                 │
│                                                                                 │
│   Output folder                                                                 │
│   [ ~/Documents/OmniVoice/stems/song/                                  [📂] ]   │
│                                                                                 │
│   [Cancel]                                                       [ Separate ▶ ] │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Rules of the view

- Every tool is **one form, one run, one output folder**. No wizards.
- Every tool **reuses the same job queue** as the dub pipeline. Closing the dialog doesn't cancel the run — the job moves to [Batch Queue](05-batch-queue.md).
- Every tool shows **estimated time before it starts** (from a dry-run probe or file-size heuristic).
- Every tool outputs to a user-chosen folder; defaults live under `~/Documents/OmniVoice/<tool>/<input-name>/`.
- No tool does anything irreversibly without the `Keep original as .bak` option enabled by default.

## What binds to what

| Tool | Backend | Under the hood |
|---|---|---|
| Vocal separation | `POST /tools/separate` | `services/rvc.py` already wraps demucs |
| Align subtitles | `POST /tools/align` | new: wav2vec forced alignment |
| Merge SRT+video | `POST /tools/mux-subs` | `services/ffmpeg_utils.py` |
| Transcribe only | `POST /tools/transcribe` | `services/segmentation.py` (current ASR path) |
| Convert format | `POST /tools/convert` | `services/ffmpeg_utils.py` |
| YouTube ingest | `POST /tools/ingest-url` | `yt-dlp` (already a dep) |
| Clean audio | `POST /tools/clean` | pedalboard + demucs (already deps) |
| Diagnose file | `GET /tools/probe?path=…` | `ffprobe` JSON passthrough |

## Why this page matters

Every tool above is already available as a piece of the dub pipeline. Exposing them standalone is **near-zero engineering cost** and dramatically broadens the product's appeal — many users will land here first, become comfortable with the app's reliability, and *then* try the dub flow.

## Roadmap phase

Tools page lands in **Phase 4** alongside step-level resumability (jobs posted from tools need the same durable queue). Probe + YouTube ingest ship earlier as lightweight slices.
