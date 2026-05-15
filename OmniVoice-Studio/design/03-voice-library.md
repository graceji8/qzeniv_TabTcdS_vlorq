# 03 · Voice Library

All cloned and designed voices. A grid-first workspace for casting decisions. Every voice is three things at once: a reference audio clip, a style instruction, and a playback result.

## View

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ☰ ›  Voice Library                                        [+ Clone]  [✨ Design]    ●Ready      │
├───────┬─────────────────────────────────────────────────────────────────────────────────────────┤
│       │                                                                                         │
│  🎬   │   🔎 search…            Filter: [ All ▾ ]  [ Locked ▾ ]  [ Language ▾ ]    Sort ↓ recent │
│       │                                                                                         │
│  🧬◄  │   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │
│       │   │     Marcus     │  │   Dr. Chen     │  │   Narrator-F   │  │   Kid-Giggle   │        │
│  📚   │   │                │  │                │  │                │  │                │        │
│       │   │  ▓▓▓░▓▓▓▓▓░▓▓  │  │  ▓▓▓▓▓░▓▓▓░▓▓  │  │  ▓▓░▓▓▓▓▓▓▓░░  │  │  ▓░▓▓░▓▓▓░▓▓▓  │        │
│  🛠   │   │  ▶  3.2s       │  │  ▶  2.8s       │  │  ▶  4.1s       │  │  ▶  2.4s       │        │
│       │   │                │  │                │  │                │  │                │        │
│  📦   │   │ 🎭 warm, calm  │  │ 🎭 expert      │  │ 🎭 documentary │  │ 🎭 playful     │        │
│       │   │ 🌐 en-US       │  │ 🌐 en-GB       │  │ 🌐 multi       │  │ 🌐 en-US       │        │
│  ⚙   │   │ 🔒 locked      │  │ ○ free         │  │ ○ free         │  │ ○ free         │        │
│       │   │                │  │                │  │                │  │                │        │
│       │   │ [▶] [✎] [🔓]   │  │ [▶] [✎] [🗑]   │  │ [▶] [✎] [🗑]   │  │ [▶] [✎] [🗑]   │        │
│       │   └────────────────┘  └────────────────┘  └────────────────┘  └────────────────┘        │
│       │                                                                                         │
│       │   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │
│       │   │   SPK-03       │  │   Grandma-JP   │  │  Announcer-DE  │  │     + New      │        │
│       │   │  (auto-cast)   │  │                │  │                │  │                │        │
│       │   │  ▓▓░▓▓▓░▓▓▓▓░  │  │  ▓▓▓▓▓▓▓░▓░▓▓  │  │  ▓░▓▓▓▓▓▓▓▓▓▓  │  │    ┌──────┐    │        │
│       │   │  ▶  1.9s       │  │  ▶  3.5s       │  │  ▶  2.2s       │  │    │  +   │    │        │
│       │   │                │  │                │  │                │  │    └──────┘    │        │
│       │   │ 🎭 auto        │  │ 🎭 gentle      │  │ 🎭 commanding  │  │                │        │
│       │   │ 🌐 auto        │  │ 🌐 ja-JP       │  │ 🌐 de-DE       │  │                │        │
│       │   │ ○ ephemeral    │  │ ○ free         │  │ ○ free         │  │                │        │
│       │   │                │  │                │  │                │  │                │        │
│       │   │ [▶] [✎] [🗑]   │  │ [▶] [✎] [🗑]   │  │ [▶] [✎] [🗑]   │  │                │        │
│       │   └────────────────┘  └────────────────┘  └────────────────┘  └────────────────┘        │
│       │                                                                                         │
│       │   8 voices · 3 locked · 420 MB on disk                                [🔀 A/B Compare]   │
│       │                                                                                         │
└───────┴─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Clone panel (opens in a side sheet)

```
┌──────────────────────────────────────────────┐
│  Clone a voice                         ✕     │
├──────────────────────────────────────────────┤
│                                              │
│  Name           [ Dr. Chen            ]      │
│                                              │
│  Reference audio                             │
│  ┌──────────────────────────────────────┐    │
│  │                                      │    │
│  │   ▓▓▓░░▓▓▓▓▓▓░▓▓▓▓▓▓░░▓▓▓▓▓         │    │
│  │   ▶ 2.8 s                            │    │
│  │                                      │    │
│  │   [ 🎙 record ]   [ 📎 upload ]      │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  Transcript (optional, enables ultimate      │
│  cloning on VoxCPM2)                         │
│  [ The quick brown fox jumps over the…   ]   │
│                                              │
│  Language        [ en-GB ▾ ]                 │
│                                              │
│  Style prompt    [ expert, reassuring   ]    │
│                                              │
│  Seed            [ 42         ] [🎲 random]  │
│  Lock seed       ☑                          │
│                                              │
│  [Cancel]                         [ Clone ]  │
└──────────────────────────────────────────────┘
```

## Voice design panel (tag-driven, no reference audio)

```
┌──────────────────────────────────────────────┐
│  Design a new voice                    ✕     │
├──────────────────────────────────────────────┤
│                                              │
│  Describe the voice                          │
│  [ a young woman with a bright, playful  ]   │
│  [ tone, mid-Atlantic accent, excited     ]  │
│                                              │
│  Quick tags:                                 │
│  ☑ female  ☐ male  ☐ non-binary              │
│  ☐ young   ☑ adult ☐ elder                  │
│  ☐ deep    ☑ mid   ☐ bright                 │
│  ☑ excited ☐ calm  ☐ stern                  │
│                                              │
│  Language        [ en-US ▾ ]                 │
│                                              │
│  Preview text                                │
│  [ Hello, welcome to OmniVoice Studio! ]     │
│  [▶ Generate preview]         2s wav         │
│                                              │
│  [Cancel]                         [ Save  ]  │
└──────────────────────────────────────────────┘
```

## A/B Compare modal

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Compare voices — casting for  "Narrator, ep. 4"                            ✕  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Preview line:  [ In the beginning, there was only silence… ]   [↻ resynth]    │
│                                                                                 │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────┐   │
│  │  A · Marcus           │  │  B · Narrator-F       │  │  C · Designed-1   │   │
│  │                       │  │                       │  │                   │   │
│  │  ▓▓▓▓░▓▓▓▓▓▓▓▓░▓▓▓▓▓ │  │  ▓▓░▓▓▓▓▓░▓▓▓▓▓▓▓▓░  │  │  ▓▓▓▓▓░▓▓▓▓▓▓░░  │   │
│  │  ▶  4.1 s             │  │  ▶  4.3 s             │  │  ▶  3.9 s         │   │
│  │                       │  │                       │  │                   │   │
│  │  Lip-sync 0.97×       │  │  Lip-sync 1.04×       │  │  Lip-sync 0.94×   │   │
│  │  ●★★★☆ (you: ★★★★☆) │  │  ●★★★★☆             │  │  ●★★☆☆☆          │   │
│  │                       │  │                       │  │                   │   │
│  │ [ Pick A ]            │  │ [ Pick B ]            │  │ [ Pick C ]        │   │
│  └───────────────────────┘  └───────────────────────┘  └───────────────────┘   │
│                                                                                 │
│  Blind mode ☑   (randomise labels; reveal on pick)                             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Rules of the view

- **Ephemeral vs. saved**: auto-diarised `SPK-0n` voices are marked `ephemeral` and are auto-culled after the project they came from is deleted. Saved voices persist.
- **Locked** means seed + reference clip are frozen. Any playback of this voice from any project is bit-reproducible. Unlocking adds drift back in.
- **Disk usage footer** lives at the bottom of every voice-related view. Stops the cache from quietly ballooning.
- **No cloud upload option.** All clone audio stays on the user's disk. Full stop.

## What binds to what

| UI region | API | Store |
|---|---|---|
| Grid | `GET /profiles` | `voice.profiles` |
| Clone submit | `POST /profiles` (multipart) | `voice.profiles.append` |
| Design submit | `POST /profiles/design` | `voice.profiles.append` |
| A/B compare | `POST /generate` × N | `voice.compareResults` |
| Pick winner | `PUT /dub/{id}/cast` or writes to selected segment voice | `dub.segments[n].profile_id` |

## Roadmap phase

Grid + clone + design exist today. Transcript field appears in **Phase 3** once VoxCPM2 backend lands. Ratings + blind mode on A/B compare land in **Phase 4**.
