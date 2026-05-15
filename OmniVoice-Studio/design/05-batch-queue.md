# 05 · Batch Queue

The honest view of the machine. What's running, what's waiting, what went wrong, and where in the pipeline each job is parked. Named "Batch" because once the task queue is persistent, batches of videos become the natural unit of work.

## View

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ☰ ›  Batch Queue                                               [+ New batch]           ●Ready  │
├───────┬─────────────────────────────────────────────────────────────────────────────────────────┤
│       │                                                                                         │
│       │   Active                                                                   2 running    │
│  🎬   │   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│       │   │                                                                               │     │
│  🧬   │   │ ▣ Keynote 2026 (EN→DE)                                           started 14:02 │     │
│       │   │                                                                               │     │
│  📚   │   │   Ingest    ASR     Transcribe   Translate   Generate   Export     ↓          │     │
│       │   │   ●────────●─────────●───────────●──────────◐──────────○                       │     │
│  🛠   │   │                                            14/42                               │     │
│       │   │   ETA 3m 20s    GPU │▓▓▓▓▓▓░░│ 72%     VRAM 6.1 GB                  [⏸] [⏹]   │     │
│  📦   │   └───────────────────────────────────────────────────────────────────────────────┘     │
│       │                                                                                         │
│  ⚙   │   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│       │   │                                                                               │     │
│       │   │ ▣ Tutorial ep. 2 (EN→JA)                                       started 13:48 │     │
│       │   │                                                                               │     │
│       │   │   Ingest    ASR     Transcribe   Translate   Generate   Export     ↓          │     │
│       │   │   ●────────●─────────●───────────◆──────────○──────────○                       │     │
│       │   │                                  ⏸ awaiting review                           │     │
│       │   │   Paused by user · 3 flagged segments need approval            [Review] [⏹]   │     │
│       │   └───────────────────────────────────────────────────────────────────────────────┘     │
│       │                                                                                         │
│       │   Queued                                                                      3 pending │
│       │   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│       │   │  #3   Product demo v3     · EN→ES   · est. 9 min   · depends-on: none   [⇅]  │     │
│       │   │  #4   Product demo v3     · EN→FR   · est. 9 min   · depends-on: #3     [⇅]  │     │
│       │   │  #5   Cooking show pilot  · EN→IT   · est. 22 min  · depends-on: none   [⇅]  │     │
│       │   └───────────────────────────────────────────────────────────────────────────────┘     │
│       │                                                                                         │
│       │   Completed today                                                              4 done   │
│       │   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│       │   │  ✓ Interview — Huberman (EN→DE)     12m 04s · 42 seg · 1 warning   [open]    │     │
│       │   │  ✓ Product demo v3 (EN→DE)           9m 12s · 28 seg             [open]      │     │
│       │   │  ✓ Marketing cutdown v4              2m 31s ·  7 seg             [open]      │     │
│       │   │  ✗ Untitled-17 (EN→KO)              failed at step 6 · "OOM"  [retry] [logs] │     │
│       │   └───────────────────────────────────────────────────────────────────────────────┘     │
│       │                                                                                         │
│       │   Logs  (tail -f)                                                            [⋔ filter] │
│       │   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│       │   │  14:07:11  info   dub.generate  seg=14 dur=4.6s voice=marcus                 │     │
│       │   │  14:07:13  info   dub.generate  seg=14 lip_sync=0.98  ok                     │     │
│       │   │  14:07:13  info   dub.generate  seg=15 dur=4.9s voice=spk-02                 │     │
│       │   │  14:07:15  warn   rvc           skipped: model not loaded                    │     │
│       │   │  14:07:15  info   dub.generate  seg=15 lip_sync=1.04  ok                     │     │
│       │   └───────────────────────────────────────────────────────────────────────────────┘     │
│       │                                                                                         │
└───────┴─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Pipeline step glyphs

```
  ●   completed
  ◐   in progress
  ◆   paused at checkpoint (awaiting review)
  ○   queued
  ✗   failed
```

Each stage is explicitly **resumable**: a `●` means the artifact for that stage is persisted in the job store with a checksum. A crash before a `●` re-runs just that stage.

## Anatomy of a job row

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│ [icon] {project name}            {from → to}                 started {time}   │
│                                                                               │
│   {pipeline steps visualised}                                                 │
│                                                                               │
│   {current-step progress}                                                     │
│                                                                               │
│   {resource readout}     {wall-clock ETA}                  [action buttons]   │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

- Pipeline glyphs are **never** animated (no spinners inside the ASCII track). The current step pulses the text underneath.
- Action buttons are role-aware: `[⏸]` when running, `[Resume]` when paused, `[retry]` when failed.

## Rules of the view

- **Only one GPU job runs at a time.** Queued jobs with no dependency run in FIFO order. Users can reorder (`[⇅]`) at will.
- **Dependencies** are first-class. `depends-on: #3` means "start after #3 finishes, regardless of final state." Failures break the chain and surface a banner.
- **Paused jobs don't block the queue.** A job in `awaiting_review` releases the GPU; the next queued job starts. When the user resumes, it re-queues.
- **Completed today** is a 24-hour window. Older jobs live in each project's own history.
- **Logs pane** tails `/metrics/logs` SSE with filter chips. Defaults to active-job logs only.

## States the view must handle

- **Empty queue**: full-page empty state with `[+ New batch]` and a link to Launchpad.
- **Nothing active, things queued** (rare, usually means GPU is warming up): active region shows `⏳ GPU warming up…`.
- **Server restart during a run**: job re-appears in "Active" on reload with the step marker rewound to the last `●`; banner: *"Resumed from checkpoint at step 5 — no data lost."*

## What binds to what

| UI region | API | Store |
|---|---|---|
| Active jobs | `GET /jobs?state=active`, SSE `/jobs/stream` | `jobs.active` |
| Step glyph state | SSE payload `{job_id, step, state}` | `jobs.steps[job_id]` |
| Reorder | `PUT /jobs/{id}/priority` | `jobs.queued` |
| Cancel / retry | `POST /jobs/{id}/{cancel|retry}` | `jobs` |
| Logs pane | SSE `/metrics/logs?job={id}` | `logs.tail` |

## Roadmap phase

Fully realised in **Phase 4** (staged checkpoints + step-level resumability). Skeleton of this page appears at end of **Phase 1** (active/queued strips, no checkpoint gating yet). Logs pane requires Phase 1.6 (structured logging baseline).
