# 02 · Dub Studio

The main workspace. Where 80% of user time is spent. Every pixel is earning its place.

## View

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ☰ › Keynote 2026  (EN → DE)          [Save ⌘S]  [Export]  [⎋ Back]         ⚙  ●Ready   ⎯ ◻ ✕   │
├───────┬─────────────────────────────────────────────────────────────────────────┬───────────────┤
│       │                                                                         │               │
│       │   ┌─────────────────────────────────────────────────────────────────┐   │  Inspector   │
│  🎬   │   │                                                                 │   │               │
│       │   │                                                                 │   │  Segment #14  │
│  🧬   │   │                       [ video preview ]                         │   │               │
│       │   │                                                                 │   │  Start 01:24.3│
│  📚   │   │                                                                 │   │  End   01:28.9│
│       │   │                                                                 │   │  Dur   4.6 s  │
│  🛠   │   └─────────────────────────────────────────────────────────────────┘   │               │
│       │   ⏮   ⏪   ▶   ⏩   ⏭     01:26.2 / 23:41.7    🔊│▓▓▓▓▓▓░░│  ⎇ Dub ▾   │  Voice        │
│  📦   │                                                                         │  ● Marcus  ▾ │
│       │   ┌─────────────────────────────────────────────────────────────────┐   │  [🎙 retake] │
│  ⚙   │   │ Timeline                                              1× ▼  ⟳   │   │               │
│       │   │                                                                 │   │  Speed 1.00  │
│       │   │  00:00     00:30     01:00     01:30     02:00     02:30       │   │  ────●────── │
│       │   │  │         │         │         │         │         │           │   │               │
│       │   │  ▓▓▓▓▓░▓▓▓▓▓▓▓▓░▓▓▓▓▓▓▓░░▓▓▓▓▓▓▓▓▓░▓▓▓▓▓▓▓▓▓▓▓▓▓░▓▓▓▓▓▓     │   │  Gain  100%  │
│       │   │   orig   ═══════════════════════▉════════════════════════      │   │  ────●────── │
│       │   │   de-DE  ──────────────────────▉═══════════════════▓▓▓         │   │               │
│       │   │                                 ↑ playhead                     │   │  Lip sync    │
│       │   │  ▼ selection: 01:24.3 – 01:28.9  (seg #14)                    │   │  ● ok 0.98×  │
│       │   └─────────────────────────────────────────────────────────────────┘   │               │
│       │                                                                         │  Instruct    │
│       │   ┌─────────────────────────────────────────────────────────────────┐   │  excited,    │
│       │   │ Segments                         🔎 find…      [⇄ Translate]    │   │  emphatic    │
│       │   │─────────────────────────────────────────────────────────────────│   │               │
│       │   │  # │ time      │ speaker │ source            │ target · status │   │               │
│       │   │────┼───────────┼─────────┼───────────────────┼─────────────────│   │ Actions       │
│       │   │ 12 │ 01:18–22  │ SPK-01  │ And so we asked…  │ Und so fragten… │   │ [Regenerate] │
│       │   │ 13 │ 01:22–24  │ SPK-01  │ What if we could… │ Was wäre wenn…  │   │ [Listen A/B] │
│       │   │►14 │ 01:24–28  │ SPK-01  │ Actually change t │ Tatsächlich ä…  │   │ [Split here] │
│       │   │ 15 │ 01:28–33  │ SPK-02  │ I think that's…   │ Ich denke, das…  │   │ [Mark silent]│
│       │   │ 16 │ 01:33–36  │ SPK-02  │ …the real breakt  │ …der eigentli…   │   │ [Delete]     │
│       │   │ 17 │ 01:36–41  │ SPK-01  │ Let me show you   │ Lass mich dir…   │   │               │
│       │   └─────────────────────────────────────────────────────────────────┘   │               │
│       │                                                                         │               │
│       │   ● Translated 42/42   ● Generated 38/42   ● Exported 0           ⏸  ⏹  │               │
│       │                                                                         │               │
└───────┴─────────────────────────────────────────────────────────────────────────┴───────────────┘
```

## Regions

### 1. Video preview (top)
- Scrubbable, frame-accurate. Spacebar = play/pause.
- Audio selector `🔊 Dub ▾`: original / dub / mixed / off.
- Matches the timeline playhead at all times.

### 2. Transport (below preview)
- Jump-to-prev-seg / back 5s / play / forward 5s / jump-to-next-seg.
- Total time display uses `tabular-nums`.
- Volume meter is a level, not a slider — the slider lives in the audio menu.

### 3. Timeline (middle)
- Waveform at the top is the source audio.
- Below: one track per language (`orig`, `de-DE`, `es-ES`, …). Filled = present, shaded = missing.
- Vertical red line = playhead. Shaded range = current selection.
- Zoom control top-right. Keyboard: `+` / `-` / `0` (fit).

### 4. Segment table (bottom-mid)
- Virtualised (`react-window`). Handles 10k rows without lag.
- Current segment is highlighted and auto-scrolls into view during playback.
- Status dot per row: grey (draft), amber (generating), green (ready), red (error).
- Click source or target to edit inline. Tab cycles fields.
- `⇄ Translate` opens [Translation Workbench](04-translation-workbench.md) scoped to selected rows.

### 5. Inspector (right panel)
- Collapsible. Contents switch based on selection: single segment, multi-select, nothing.
- Voice picker includes A/B retake.
- Lip-sync badge is a **feedback signal** in Phase 4: clicking it runs speech-rate re-fit.

### 6. Pipeline strip (footer)
- Live counters for the three pipeline stages.
- Play/pause/stop controls the running job, not the video.

## Keyboard shortcuts

| Key | Action |
|---|---|
| Space | Play/pause preview |
| `J K L` | Back / pause / forward (editor-standard) |
| `←` / `→` | Jump ±1 segment |
| `⌘ ↵` | Regenerate current segment |
| `⌘ ⇧ ↵` | Regenerate all selected |
| `⌘ S` | Save project |
| `⌘ Z` / `⌘ ⇧ Z` | Undo / redo |
| `⌘ F` | Focus segment search |
| `?` | Show cheatsheet |
| `[` / `]` | Trim segment start / end by 100ms |

## States the view must handle

- **No video yet** (landed from Launchpad's empty state): the whole main area becomes a drop-zone with a YouTube/URL field.
- **Transcribing**: segments table shows a skeleton; progress bar at the pipeline strip. Preview is already scrubbable.
- **Mid-dub**: only completed segment rows show the green dot; in-flight row pulses; failed rows show inline `[retry]`.
- **Awaiting review gate** (Phase 4): the pipeline strip turns amber, shows which stage needs a `[Continue]`.

## What binds to what

| UI region | API | Store |
|---|---|---|
| Segments table | `GET /dub/{id}/segments`, SSE `/tasks/{id}/stream` | `dub.segments` |
| Inspector · regenerate | `POST /dub/generate/{id}` (scoped to seg) | `dub.pendingJobs` |
| Translate button | `POST /dub/translate/{id}` | `dub.translationJob` |
| Timeline waveform | `/audio/{id}/waveform.json` | `dub.waveform` |
| Save | `PUT /projects/{id}` | `project.dirty → false` |

## Roadmap phase

Skeleton exists today. Phase 1 (Zustand + pipeline split) cleans the data flow. Phase 4 adds the awaiting-review states and speech-rate re-fit. The Inspector's voice picker gets "A/B Compare" in Phase 3.
