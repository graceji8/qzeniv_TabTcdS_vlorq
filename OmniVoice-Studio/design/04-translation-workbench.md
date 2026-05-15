# 04 · Translation Workbench

Where dubbed output actually becomes watchable. The centre of mass for the Phase 2 quality leap. Three-step translate → reflect → adapt happens here, with glossary pinned to the side.

## View

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ☰ ›  Keynote 2026  ›  Translation          EN → DE  ▾    Quality: ● Cinematic ○ Fast    ●Ready │
├───────┬─────────────────────────────────────────────────────────────────────────────────────────┤
│       │                                                                                         │
│       │   ┌──────────────────┬──────────────────────────┬──────────────────────────────┐        │
│  🎬   │   │  1 · Literal     │  2 · Reflection          │  3 · Final (cinematic)       │        │
│       │   │                  │                          │                              │        │
│  🧬   │   │  The quick brown │  This literal version    │  Der flinke braune Fuchs     │        │
│       │   │  fox jumps over  │  loses the English       │  setzt mit einem Sprung      │        │
│  📚◄  │   │  the lazy dog.   │  idiomatic feel. Sounds  │  über den trägen Hund        │        │
│       │   │                  │  stiff in German;        │  hinweg.                     │        │
│  🛠   │   │                  │  "springt über den       │                              │        │
│       │   │                  │  faulen Hund" is a       │  [ use this ]  [ edit ]      │        │
│  📦   │   │                  │  better idiomatic fit.   │                              │        │
│       │   │                  │                          │                              │        │
│  ⚙   │   │  [ retranslate ] │  [ refine reflection ]   │  [ regenerate ]              │        │
│       │   └──────────────────┴──────────────────────────┴──────────────────────────────┘        │
│       │                                                                                         │
│       │   Segments                                          🔎 …                 42 rows        │
│       │   ┌───────────────────────────────────────────────────────────────────────────────┐     │
│       │   │  # │ src snippet          │ target (final)                    │ state  │  Δ   │     │
│       │   │────┼──────────────────────┼───────────────────────────────────┼────────┼──────│     │
│       │   │ 12 │ And so we asked…     │ Und so fragten wir uns…           │  ✓     │  —   │     │
│       │   │ 13 │ What if we could…    │ Was wäre, wenn wir…               │  ✓     │  ⚠   │     │
│       │   │►14 │ Actually change t…   │ Das Spiel wirklich zu verändern.  │  ◐     │  +3% │     │
│       │   │ 15 │ I think that's…      │ Ich glaube, das ist…              │  ✓     │  —   │     │
│       │   │ 16 │ …the real breakth…   │ …der eigentliche Durchbruch.      │  ✓     │  —   │     │
│       │   │ 17 │ Let me show you…     │ Lass mich dir etwas zeigen…       │  ✓     │  +8% │     │
│       │   └───────────────────────────────────────────────────────────────────────────────┘     │
│       │                                                                                         │
│       │   42 / 42 translated    · 3 flagged for length (> 17 CPS)    · 2 glossary conflicts     │
│       │                                                                                         │
│       │   [Translate all]  [Reflect selected]  [Re-adapt selected]       [ Next: Generate ▸ ]   │
│       │                                                                                         │
├───────┴─────────────────────────────────────────────────────────────────────────────────────────┤
│  Glossary                                                                                  ⎯ 📌 │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│  Source                   Target                 Note                         Auto? │ Actions   │
│─────────────────────────────────────────────────────────────────────────────────────┼───────────│
│  OmniVoice                OmniVoice              keep as-is (brand)           ●     │ [✎] [🗑]  │
│  breakthrough             Durchbruch             prefer over "Durchbruchs"    ○     │ [✎] [🗑]  │
│  game-changing            bahnbrechend           confirm ok                   ●     │ [✎] [🗑]  │
│  Marcus                   Marcus                 character name                ●     │ [✎] [🗑]  │
│  product                  Produkt                                             ●     │ [✎] [🗑]  │
│  [ + add term ]                                                                     │           │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## The 3-step flow, shown inline

The workbench isn't a linear wizard — it's **a live pipeline the user can intervene at any step**:

```
segment text (source)
        │
        ▼
┌───────────────┐      ┌─────────────────┐      ┌─────────────────────┐
│ 1. TRANSLATE  │─────▶│  2. REFLECT     │─────▶│  3. ADAPT           │
│ literal pass  │      │  critique tone, │      │  cinematic rewrite  │
│               │      │  length, idiom  │      │  using critique     │
└───────────────┘      └─────────────────┘      └─────────────────────┘
        ▲                      ▲                          ▲
        │                      │                          │
        └─────── user can edit any stage directly ────────┘
                  (editing invalidates downstream; they auto-re-run)
```

## Rules of the view

- **Quality: Cinematic** runs all three steps. **Quality: Fast** runs step 1 only and copies it to the final column — useful for prototyping.
- **Δ column** shows the ratio of target character count to source. Over ±15% triggers the warning ⚠ — likely to break lip-sync. Color-coded but not colour-only.
- **State column**: `✓` done, `◐` in-flight, `⚠` needs review, `✗` errored.
- Glossary is **pinned** by default (📌). Unpinning hides it; resurfaces on glossary-related warnings.
- Glossary conflicts (same source, different targets in different segments) surface at the pipeline footer with `[auto-fix]`.
- `[ Next: Generate ▸ ]` is the **only way forward** to TTS — or, in Phase 4 when staged checkpoints exist, the explicit "continue" gate.

## States the view must handle

- **Nothing translated yet**: all three columns are empty; big `[ Translate all ]` button is centred.
- **Step 1 only (Fast mode)**: reflection column greyed out with "not run in Fast mode".
- **Mid-reflection**: column 2 streams tokens; column 3 shows a placeholder `…`.
- **LLM provider offline**: inline banner in the header; quality auto-degrades to Fast; user is notified, not blocked.

## Keyboard shortcuts

| Key | Action |
|---|---|
| `⌘ ↵` | Run pipeline on current segment |
| `⌘ ⇧ ↵` | Run on all selected |
| `⌘ E` | Edit the final column |
| `G` | Jump to glossary add |
| `⇧ ↓` / `⇧ ↑` | Extend selection |

## What binds to what

| UI region | API | Store |
|---|---|---|
| 3-column panel | `POST /dub/translate/{id}/segment/{n}` (streaming SSE) | `translation.stages` |
| Segments table | same job feed | `translation.rows` |
| Glossary CRUD | `GET/POST/PUT/DELETE /glossary/{project_id}` | `glossary.terms` |
| Re-adapt | `POST /dub/translate/{id}/adapt` | queues on job store |
| Next: Generate | transitions pipeline state | `jobs.advance()` |

## Roadmap phase

Entire view is delivered in **Phase 2**. Glossary persistence uses the `terms` table introduced in phase 2.3. The 3-column UI is a first-class React component; the underlying LLM calls sit behind the Phase 3 `llm_backend` adapter once it lands.
