# 01 · Launchpad

The home screen. First thing a user sees on launch. Answers the three questions:
1. What have I been working on?
2. What's the state of my machine / the engines right now?
3. How do I start something new?

## View

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ☰   OmniVoice Studio                                                    ⚙  ⛶  ●Ready  [ + New ] │
├────────┬────────────────────────────────────────────────────────────────────────────────────────┤
│        │                                                                                        │
│  🎬    │   Welcome back, debpalash                                                              │
│  Dub   │                                                                                        │
│        │   ┌──────────────────────────────────────────────────────────────────────────────┐     │
│  🧬    │   │  Quick start                                                                 │     │
│ Voice  │   │                                                                              │     │
│        │   │   [ 📼 Dub a video      ]   [ 🎙 Clone a voice    ]   [ 📝 Open project … ]  │     │
│  📚    │   │                                                                              │     │
│ Trans- │   └──────────────────────────────────────────────────────────────────────────────┘     │
│ late   │                                                                                        │
│        │   Recent projects                                              ↑ updated · size · name │
│  🛠    │   ┌──────────────────────────────────────────────────────────────────────────────┐     │
│ Tools  │   │  ▸  Interview — Huberman (EN → DE)          4 segments pending     2h ago    │     │
│        │   │  ▸  Product demo v3                         done · exported        yesterday │     │
│  📦    │   │  ▸  Tutorial series ep. 2 (EN → JA)         ◐ translating 14/42    3 days    │     │
│ Export │   │  ▸  Cooking show pilot                      ● error on step 7      1 week    │     │
│        │   │  ▸  Keynote 2026                            draft                  2 weeks   │     │
│  ⚙    │   └──────────────────────────────────────────────────────────────────────────────┘     │
│Settings│                                                                                        │
│        │   ┌───────────────────────────────┐  ┌─────────────────────────────────────────────┐   │
│        │   │  Engines                      │  │  Hardware                                   │   │
│        │   │                               │  │                                             │   │
│        │   │  TTS   OmniVoice       ● rdy  │  │  GPU    Apple M3 Max 40-core                │   │
│        │   │  ASR   WhisperX lg-v3  ● rdy  │  │  VRAM   │▓▓▓▓░░░░░░│  6.1 / 48 GB           │   │
│        │   │  LLM   Ollama llama3.3 ● rdy  │  │  CPU    │▓▓░░░░░░░░│  14 %                  │   │
│        │   │                        [swap] │  │  Disk   192 GB free                         │   │
│        │   └───────────────────────────────┘  └─────────────────────────────────────────────┘   │
│        │                                                                                        │
│        │   Queue                                                                                │
│        │   ┌──────────────────────────────────────────────────────────────────────────────┐     │
│        │   │  ◐  Keynote 2026 — TTS 14/42 · ETA 3m 20s                       [view] [⏸]  │     │
│        │   │  ⏸  Tutorial series ep. 2 — paused at translation review        [resume]    │     │
│        │   └──────────────────────────────────────────────────────────────────────────────┘     │
│        │                                                                                        │
└────────┴────────────────────────────────────────────────────────────────────────────────────────┘
```

## Why these choices

- **Status pill in the header (●Ready)** — model state is a permanent ambient signal, not a thing the user has to hunt for. Matches today's behavior, just lifted global.
- **Quick start row** — three canonical entry points. No clever text, no onboarding card that ages badly.
- **Recent projects** as the dominant region — power users live here. Status badges (`pending`, `translating`, `error`) are colour-only; the text reads the same to colour-blind users.
- **Engines card** — shows the active backend for each role and lets the user swap without diving into Settings. This is the UX surface for Phase 3.
- **Hardware card** — replaces today's scattered telemetry. One glance answers "can I run another dub right now?"
- **Queue** sits low but *always* visible when non-empty. Click-through to [Batch Queue](05-batch-queue.md).

## What binds to what

| UI region | API | Store |
|---|---|---|
| Status pill | `GET /model/status` (poll every 5s) | `ui.modelStatus` |
| Quick start → Dub | navigates to Dub Studio with empty state | `project.create()` |
| Recent projects | `GET /projects` | `project.list` |
| Engines card | `GET /engines`, `POST /engines/swap` | `engines.active` |
| Hardware card | `GET /system/stats` (SSE) | `ui.systemStats` |
| Queue strip | `GET /jobs?status=active` (SSE) | `jobs.active` |

## States the view must handle

- **Empty** (no projects yet): the entire recent-projects region becomes a single "Create your first project" CTA. No fake tutorial card.
- **Model loading**: status pill `● Loading…`, engines card shows per-engine spinners, quick-start buttons are enabled anyway (they queue work).
- **Engine failed to load**: status pill red, engines card surfaces the specific engine with `[retry]`.
- **Offline / backend dead**: full-page banner, auto-reconnects with exponential backoff. Recent projects fall back to local cache.

## Roadmap phase

Ships end of **Phase 1** (once Zustand stores and persistent job queue exist). Engines card expands in **Phase 3**. Queue strip reaches full fidelity in **Phase 4**.
