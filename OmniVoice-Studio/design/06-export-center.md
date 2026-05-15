# 06 · Export Center

The last step. Where a dubbed project becomes files someone else can use. No hidden defaults — every choice is shown, pre-sized, and reversible.

## View

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ☰ ›  Keynote 2026  ›  Export                                                          ●Ready   │
├───────┬─────────────────────────────────────────────────────────────────────────────────────────┤
│       │                                                                                         │
│  🎬   │   ┌──────────────────────────────────┐   ┌────────────────────────────────────────┐     │
│       │   │  Preset                          │   │  Preview                               │     │
│  🧬   │   │                                  │   │                                        │     │
│       │   │  ● Full deliverable (MP4+subs)   │   │      ┌──────────────────────────┐      │     │
│  📚   │   │  ○ Audio-only (MP3/WAV)          │   │      │                          │      │     │
│       │   │  ○ Subtitles only (SRT/VTT)      │   │      │   [ video preview ]      │      │     │
│  🛠   │   │  ○ Stems (vocals + BG separate)  │   │      │                          │      │     │
│       │   │  ○ Per-segment WAV .zip          │   │      └──────────────────────────┘      │     │
│  📦◄  │   │  ○ Custom…                       │   │      ⏮  ▶  ⏭   01:26 / 23:41          │     │
│       │   └──────────────────────────────────┘   │      🔊 mix: [ EN + DE ▾ ]             │     │
│  ⚙   │                                           │      cap: [ DE ▾ ]  style: [ Netflix ▾] │     │
│       │   Audio tracks                           │                                        │     │
│       │   ┌──────────────────────────────────┐   └────────────────────────────────────────┘     │
│       │   │                                  │                                                  │
│       │   │  ☑ Original     (en-US)  48k/16  │   Subtitles                                      │
│       │   │  ☑ Dub · German (de-DE)  48k/16  │   ┌────────────────────────────────────────┐     │
│       │   │  ☐ Dub · Spanish(es-ES)  48k/16  │   │                                        │     │
│       │   │  ☐ BG-only      (music)  48k/16  │   │  Tracks to burn / mux                  │     │
│       │   │                                  │   │    ☑ de-DE (dual: EN+DE)               │     │
│       │   │  Default: [ de-DE ▾ ]            │   │    ☐ de-DE (single)                    │     │
│       │   │                                  │   │    ☐ en-US (single)                    │     │
│       │   │  Mixdown: [ side-by-side ▾ ]     │   │                                        │     │
│       │   │                                  │   │  File format:                          │     │
│       │   └──────────────────────────────────┘   │    ☑ .srt   ☑ .vtt   ☐ burn-in         │     │
│       │                                          │                                        │     │
│       │                                          │  Style preset: [ Netflix safe ▾ ]      │     │
│       │                                          │    • max 42 chars/line                 │     │
│       │                                          │    • max 2 lines                       │     │
│       │                                          │    • max 17 CPS                        │     │
│       │                                          └────────────────────────────────────────┘     │
│       │                                                                                         │
│       │   Container / codec                                                                     │
│       │   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│       │   │ Container     ● .mp4   ○ .mkv   ○ .mov                                        │     │
│       │   │ Video codec   ● h264   ○ h265   ○ av1        (copy if possible: ☑)           │     │
│       │   │ Audio codec   ● aac    ○ opus   ○ flac                                        │     │
│       │   │ Loudness      ● -16 LUFS (web)  ○ -23 LUFS (EBU R128)  ○ off                 │     │
│       │   └───────────────────────────────────────────────────────────────────────────────┘     │
│       │                                                                                         │
│       │   Output                                                                                │
│       │   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│       │   │  Path   [ ~/Movies/OmniVoice/Keynote2026/                              [📂] ] │     │
│       │   │  Name   [ Keynote_2026_DE_v3.mp4                                             ] │     │
│       │   │                                                                               │     │
│       │   │  Estimated size  ~ 412 MB · est. time  38 s                                   │     │
│       │   └───────────────────────────────────────────────────────────────────────────────┘     │
│       │                                                                                         │
│       │   [Cancel]     [ Save as preset… ]                    [ ▶ Export ]                     │
│       │                                                                                         │
└───────┴─────────────────────────────────────────────────────────────────────────────────────────┘
```

## In-flight export view

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│   Exporting  Keynote_2026_DE_v3.mp4                                              │
│                                                                                  │
│   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  58%   est. 16s     │
│                                                                                  │
│   muxing audio · remapping streams · burning subtitles …                         │
│                                                                                  │
│   [⏹ cancel]                                                     [run in bg]    │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## Rules of the view

- **One preset radio, many detail panels.** Picking a preset pre-fills the panels below; any manual change flips the preset to `Custom…`. No hidden state.
- **Live preview mirrors the export choices exactly.** If burn-in is on, the preview shows burn-in. If subtitles are off, preview has none.
- **Size estimate is not a guess.** It comes from a dry-run ffmpeg probe of the mux with the selected streams, minus actual encoding.
- **Loudness normalisation defaults to -16 LUFS** (YouTube / podcast norm). Changing to EBU R128 re-probes.
- **"Copy if possible" ☑** is on by default — if the user didn't alter the original video track, it's stream-copied (no re-encode). Gigantic time win.
- **Selective tracks** (already shipped) stay first-class. Uncheck Original → single-track dub export.

## What binds to what

| UI region | API | Store |
|---|---|---|
| Preset picker | n/a (local) | `exporter.preset` |
| Audio/sub tracks | computed from `project.tracks` | `exporter.tracks` |
| Style preset | template from `services/subtitle_segmenter` | `exporter.subStyle` |
| Size + time estimate | `POST /export/estimate` | `exporter.estimate` |
| Export | `POST /export/{project_id}` → returns task_id, SSE progress | `jobs.active` |
| Save as preset | writes to `export_presets` table | `exporter.savedPresets` |

## States the view must handle

- **No dub generated yet**: full-page empty state, CTA to return to Dub Studio.
- **Missing translation for a selected track**: track checkbox is disabled with a reason tooltip.
- **Output dir not writable**: inline error on path field, with a "[choose another]" button.
- **Previous export with same name**: warning banner, offers auto-rename (`_v4`) or overwrite.

## Roadmap phase

Most of this ships end of **Phase 1** as a cleanup of today's scattered export surface. Dual-subtitle mode and Netflix style preset land in **Phase 2** (alongside NLP-aware segmentation). Loudness normalisation is a small **Phase 4** addition once speech-rate engineering lands.
