# 08 · Settings

One view, four tabs. No buried switches, no hidden env vars that aren't also here.

## View — Engines tab

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ☰ ›  Settings                                                                        ●Ready   │
├───────┬─────────────────────────────────────────────────────────────────────────────────────────┤
│       │                                                                                         │
│       │   [ Engines ]   Hardware   Data   Keyboard   About                                      │
│  🎬   │                                                                                         │
│       │   TTS (text-to-speech)                                                                  │
│  🧬   │   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│       │   │                                                                               │     │
│  📚   │   │   ● OmniVoice                                                                 │     │
│       │   │      600 languages · zero-shot · Apple/NVIDIA/CPU                             │     │
│  🛠   │   │      checkpoint: k2-fsa/OmniVoice     status: ● ready (6.1 GB VRAM)           │     │
│       │   │      [ swap checkpoint… ]    [ unload ]                                        │     │
│  📦   │   │                                                                               │     │
│       │   │   ○ VoxCPM2                                                                   │     │
│  ⚙◄  │   │      30 languages · studio 48 kHz · NVIDIA CUDA 12+                           │     │
│       │   │      checkpoint: openbmb/VoxCPM2       status: ○ not loaded                  │     │
│       │   │      [ install ]     gates on: requires ~8 GB VRAM                            │     │
│       │   │                                                                               │     │
│       │   │   ○ Custom plug-in (via pip package)                                          │     │
│       │   │      [ browse registered backends… ]                                          │     │
│       │   └───────────────────────────────────────────────────────────────────────────────┘     │
│       │                                                                                         │
│       │   ASR (speech recognition)                                                              │
│       │   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│       │   │   ● WhisperX large-v3              ○ mlx-whisper (Apple Silicon only)          │     │
│       │   │   ○ faster-whisper                 ○ Custom plug-in                            │     │
│       │   │                                                                               │     │
│       │   │   Diarisation   ● pyannote 3.1  (requires HF_TOKEN — [set…])                  │     │
│       │   │                 ○ off                                                          │     │
│       │   └───────────────────────────────────────────────────────────────────────────────┘     │
│       │                                                                                         │
│       │   LLM (translation / reflection)                                                        │
│       │   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│       │   │   ● Ollama (local)      model: [ llama3.3:70b-instruct ▾ ]    ● ready         │     │
│       │   │   ○ OpenAI-compatible   base_url: [ …                       ]                 │     │
│       │   │                         api_key:  [ ••••••••••••    ]  [paste] [clear]         │     │
│       │   │   ○ Claude              api_key:  [ ••••••••••••    ]  [paste] [clear]         │     │
│       │   │   ○ Off (disables Reflect/Adapt; Translate falls back to local MT)            │     │
│       │   │                                                                               │     │
│       │   │   ⚠ Cloud LLMs leave your device. Off by default. Enabled per-feature only.  │     │
│       │   └───────────────────────────────────────────────────────────────────────────────┘     │
│       │                                                                                         │
│       │   [ Reset engine selection to defaults ]                                                │
│       │                                                                                         │
└───────┴─────────────────────────────────────────────────────────────────────────────────────────┘
```

## View — Hardware tab

```
│   [ Engines ]   [ Hardware ]   Data   Keyboard   About                                      │
│                                                                                              │
│   Device                                                                                     │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│   │   Auto-detect: ● Apple M3 Max 40-core          [ override… ]                      │       │
│   │                                                                                  │       │
│   │   Current binding   ● MPS   ○ CUDA   ○ CPU                                       │       │
│   │                                                                                  │       │
│   │   Live                                                                           │       │
│   │      GPU   │▓▓▓▓▓▓░░░░│  72 %        VRAM  │▓▓▓▓▓░░░░░│  6.1 / 48 GB            │       │
│   │      CPU   │▓▓░░░░░░░░│  14 %        RAM   │▓▓▓░░░░░░░│  8.3 / 64 GB            │       │
│   │      Disk  192 GB free                                                           │       │
│   └──────────────────────────────────────────────────────────────────────────────────┘       │
│                                                                                              │
│   Model management                                                                           │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│   │   Idle-unload timeout    [ 5 min ▾ ]      (frees VRAM when no work is running)   │       │
│   │   CPU worker pool size   [ auto (8) ▾ ]                                          │       │
│   │   Preload on startup     ☐                                                       │       │
│   └──────────────────────────────────────────────────────────────────────────────────┘       │
│                                                                                              │
│   Acceleration                                                                               │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│   │   torch.compile   ☑ (CUDA only; silently skipped otherwise)                      │       │
│   │   Nano-vLLM       ☐ (VoxCPM2 only; requires separate install)                    │       │
│   │   ffmpeg hwaccel  [ auto ▾ ]      (videotoolbox on Mac, nvenc on NVIDIA, …)      │       │
│   └──────────────────────────────────────────────────────────────────────────────────┘       │
```

## View — Data tab

```
│   Engines   Hardware   [ Data ]   Keyboard   About                                           │
│                                                                                              │
│   Paths                                                                                      │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│   │   Database      ~/Library/.../omnivoice.db                            [reveal]   │       │
│   │   Models cache  ~/.cache/huggingface/                  12.4 GB        [reveal]   │       │
│   │   Outputs       ~/Movies/OmniVoice/                    4.1 GB         [reveal]   │       │
│   │   Voice refs    ~/Library/.../voices/                  380 MB         [reveal]   │       │
│   └──────────────────────────────────────────────────────────────────────────────────┘       │
│                                                                                              │
│   Retention                                                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│   │   Clean intermediate .wav files after export   ☑                                 │       │
│   │   Auto-delete failed jobs older than           [ 7 days ▾ ]                      │       │
│   │   Max disk for intermediate artifacts          [ 10 GB ▾ ]                       │       │
│   └──────────────────────────────────────────────────────────────────────────────────┘       │
│                                                                                              │
│   Privacy                                                                                    │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│   │   Anonymous usage telemetry                    ○ on   ● off                      │       │
│   │   Crash reports                                ● local only                       │       │
│   │                                                                                  │       │
│   │   All data stays on this machine unless you explicitly opt into cloud LLM.       │       │
│   └──────────────────────────────────────────────────────────────────────────────────┘       │
│                                                                                              │
│   Danger zone                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│   │   [ Clear models cache ]   [ Clear outputs ]   [ Reset all settings ]            │       │
│   │   [ Export database (.sqlite) ]       [ Import database (.sqlite) ]              │       │
│   └──────────────────────────────────────────────────────────────────────────────────┘       │
```

## View — Keyboard tab

```
│   Engines   Hardware   Data   [ Keyboard ]   About                                           │
│                                                                                              │
│   Global                                                                                     │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│   │   Toggle sidebar              [ ⌘ \ ]             [edit]                          │       │
│   │   Show keyboard cheatsheet    [ ? ]               [edit]                          │       │
│   │   Save project                [ ⌘ S ]             [edit]                          │       │
│   │   Undo / Redo                 [ ⌘ Z / ⌘ ⇧ Z ]     [edit]                          │       │
│   │   Focus search                [ ⌘ K ]             [edit]                          │       │
│   └──────────────────────────────────────────────────────────────────────────────────┘       │
│                                                                                              │
│   Dub Studio                                                                                 │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│   │   Play / pause                [ Space ]            [edit]                         │       │
│   │   Back / forward (JKL)        [ J / K / L ]        [edit]                         │       │
│   │   Jump segment                [ ← / → ]            [edit]                         │       │
│   │   Regenerate current          [ ⌘ ↵ ]              [edit]                         │       │
│   │   Regenerate selected         [ ⌘ ⇧ ↵ ]            [edit]                         │       │
│   │   Trim segment start / end    [ [ / ] ]            [edit]                         │       │
│   └──────────────────────────────────────────────────────────────────────────────────┘       │
│                                                                                              │
│   Translation                                                                                │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│   │   Run pipeline                [ ⌘ ↵ ]                                             │       │
│   │   Edit final column           [ ⌘ E ]                                             │       │
│   │   Add glossary term           [ G ]                                               │       │
│   └──────────────────────────────────────────────────────────────────────────────────┘       │
│                                                                                              │
│   [ Reset all shortcuts to defaults ]                                                        │
```

## View — About tab

```
│   Engines   Hardware   Data   Keyboard   [ About ]                                           │
│                                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│   │                                                                                  │       │
│   │              OmniVoice Studio                                                    │       │
│   │              Version  1.3.0  (tauri 2.10)                                        │       │
│   │                                                                                  │       │
│   │              Built on the open-source OmniVoice 600-language diffusion model.    │       │
│   │              Apache-2.0 licensed. 100% local, no API keys required.              │       │
│   │                                                                                  │       │
│   │              [ Check for updates ]  [ Release notes ]  [ GitHub ]                │       │
│   │                                                                                  │       │
│   │              Built with: FastAPI, React 19, Tauri 2, PyTorch 2.8, WhisperX,      │       │
│   │              pyannote, demucs, pedalboard, yt-dlp, ffmpeg, Bun.                  │       │
│   │                                                                                  │       │
│   └──────────────────────────────────────────────────────────────────────────────────┘       │
│                                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────────────────┐       │
│   │   Diagnostics                                                                    │       │
│   │                                                                                  │       │
│   │   [ Run self-test ]   checks: ffmpeg, torch, engines, disk, db, ports            │       │
│   │   [ Open logs folder ]                                                           │       │
│   │   [ Copy support bundle ]   (zips logs + sysinfo; no audio, no project data)     │       │
│   └──────────────────────────────────────────────────────────────────────────────────┘       │
```

## Rules of the view

- **Four tabs, no more.** Any new setting must fit one of: *Engines, Hardware, Data, Keyboard*. About is not a settings tab, it's the footer.
- **Every destructive control is in Danger Zone**, with confirmation.
- **Privacy defaults**: cloud LLM off, telemetry off, crash reports local only.
- **No setting is hidden in env vars.** If it's in `.env`, it's also here — or it's removed.
- **Self-test** is the first step of any support ticket; the support bundle button does the right thing so users don't have to explain their system to anyone.

## What binds to what

| UI | API | Store |
|---|---|---|
| TTS / ASR / LLM radios | `POST /engines/select` | `engines.active` |
| Install backend | `POST /engines/install` | triggers restart prompt |
| Hardware live meters | SSE `/metrics/stream` | `ui.systemStats` |
| Paths / retention | `GET/PUT /settings/data` | `settings.data` |
| Privacy toggles | `PUT /settings/privacy` | `settings.privacy` |
| Keybinds | local file `~/.config/omnivoice/keybindings.json` | `settings.keybindings` |
| Self-test | `POST /diagnostics/self-test` | one-shot |

## Roadmap phase

Engines tab lands in **Phase 3**. Hardware tab is mostly built today, needs restructuring. Data + Keyboard tabs land end of **Phase 1** alongside the Zustand refactor. About / Diagnostics ship as a Phase 5 productisation item.
