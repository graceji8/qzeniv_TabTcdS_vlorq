# OmniVoice Studio — Mature Design

ASCII mockups of the target UX and architecture once [`ROADMAP.md`](../ROADMAP.md) is complete. This folder is the **source of truth for product intent**. When the shipped product diverges, either the code or this folder is wrong — decide which.

Every view page includes:
1. The screen as ASCII art.
2. What's on the screen and why.
3. Which roadmap phase delivers it.
4. The API endpoints and store slices it binds to.

## Views

| # | View | Purpose | Phase |
|---|---|---|---|
| [00](00-architecture.md) | System architecture | How the pieces fit together end-to-end | All |
| [01](01-launchpad.md) | Launchpad | Home. Projects grid + quick actions | 1 |
| [02](02-dub-studio.md) | Dub Studio | The main workspace. Timeline + segments + preview | 1–4 |
| [03](03-voice-library.md) | Voice Library | Profile management, cloning, A/B compare | 1, 3 |
| [04](04-translation-workbench.md) | Translation Workbench | 3-step reflect/adapt with glossary | 2 |
| [05](05-batch-queue.md) | Batch Queue | Staged pipeline visualisation + checkpoints | 4 |
| [06](06-export-center.md) | Export Center | Track picker + format matrix + preview | 1–2 |
| [07](07-tools.md) | Tools | Standalone utilities (isolate, align, merge) | 4 |
| [08](08-settings.md) | Settings | Engines, hardware, keys, data, about | 3 |

## Navigation map

```
┌──────────────────────────────────────────────────────────────────────┐
│                         OmniVoice Studio                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   [Launchpad] ──┬──> [Dub Studio] ──> [Translation] ──> [Export]     │
│                 │                                                    │
│                 ├──> [Voice Library] ──> [Clone/Design/Compare]      │
│                 │                                                    │
│                 ├──> [Batch Queue]  (always accessible in sidebar)   │
│                 │                                                    │
│                 ├──> [Tools]                                         │
│                 │                                                    │
│                 └──> [Settings]                                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Conventions used in the mockups

| Glyph | Meaning |
|---|---|
| `┌─┐ │ └─┘` | Region / panel |
| `[ ... ]` | Interactive control (button, dropdown, input) |
| `▶  ⏸  ⏹` | Media controls |
| `●` / `○` | Selected / unselected radio |
| `☑` / `☐` | Checked / unchecked |
| `│▓▓▓░░░│` | Progress / level meter |
| `↑ ↓` | Sortable |
| `…` | Truncated / more |
| `⟳` | Refresh / retry |
