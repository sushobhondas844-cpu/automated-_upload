---
name: cutout-motion-explainer
description: >-
  Versioned end-to-end production workflow for 2.5D hybrid cutout motion graphics
  explainers and long-form documentaries (9:16 Shorts and 16:9 widescreen). Supports
  Version 1.1 (locked Apollo-style aesthetic + 5 mandatory workflow, SFX, archival
  sync, background cap & per-topic story isolation rules) and Version 1.2 (next-gen
  active character performance, virtual 2.5D parallax camera choreography,
  deterministic Three.js 3D dioramas, and ducked CC0/Flow Music/Lyria background music).
  Distinct from stickman-explainer.
---

# Cutout Motion Explainer Production Workflow

> **Master Standard:** All productions must strictly comply with the centralised [CONTENT_CREATION_PROTOCOL.md](../../../CONTENT_CREATION_PROTOCOL.md) (mandatory topic research, emotional character pacing, multi-language metadata SEO research, aspect-ratio protection, and approval gates).

Produce studio-grade **2.5D cutout motion graphics** documentaries and Shorts built on **pre-planned & pre-downloaded SFX**, **emotional character-centric storytelling**, **authentic archival footage synced cleanly to audio**, **strictly varied backgrounds (`<= 2` clips per background; `>= 2–3` per scene)**, and **per-topic isolated assets under `stories/<slug>/` purified only upon user approval**.

*(Note: Separate skill from `stickman-explainer` — keep their workflows and style rules completely independent.)*

---

## Choosing Workflow Version (`v1.1` vs `v1.2`)

Always confirm or follow the user's requested version:
- **`Version 1.1` (Stable Current Look — Default when requesting `"v1.1"`, `"older version"`, or `"current Apollo style"`):**
  Follows [`references/cutout-motion-v1.1.md`](./references/cutout-motion-v1.1.md). Preserves the **exact Apollo Moon Landing visual style** (`CutoutPuppet` expression rigs, `BarComparison`, `dataCard`, `RadarSweepHUD`, `ElectricSplitPane`, `TopChapterCard`, `16:9` zero subtitles, unified single `<Audio>`) **upgraded with all 5 mandatory pipeline rules below**.
- **`Version 1.2` (Next-Gen Cinematic Evolution — When requesting `"v1.2"`, `"newer version"`, camera/Three.js/music upgrade):**
  Follows [`references/cutout-motion-v1.2-research.md`](./references/cutout-motion-v1.2-research.md). Inherits **100% of `v1.1` rules** AND replaces passive talking/gasping portraits + side text with **Active Action Poses + Visual Metaphors** (`ActionMotionLayer`), **Multi-Plane Camera Choreography** (`CameraRig25D` + `ParallaxPlane`), **Deterministic `Three.js` 3D Diorama Stages** (`ThreeDioramaStage`), and **Aesthetic Background Music** (downloaded `$0` CC0 scores, Google Flow Music `flowmusic.app`, or paid Gemini `Lyria 3.5` with `-20 dB` vocal-pocket sidechain ducking).

---

## Bundled Files
- **Locked `v1.1` Spec:** [`references/cutout-motion-v1.1.md`](./references/cutout-motion-v1.1.md)
- **Researched `v1.2` Spec (Camera, 3D, Active Motion, Music):** [`references/cutout-motion-v1.2-research.md`](./references/cutout-motion-v1.2-research.md)
- **Technical Asset, Prompting & Extraction Guide:** [`references/cutout-and-motion-guide.md`](./references/cutout-and-motion-guide.md)
- **Production Rule Validator (`--version 1.1 | 1.2`):** [`scripts/validate_production_plan.py`](./scripts/validate_production_plan.py)
- **TTS & Multi-Chapter RMS Aligner:** [`scripts/generate_gemini_story_tts.py`](./scripts/generate_gemini_story_tts.py)
- **Cutout, Action-Pose & Rig Extractor:** [`scripts/cutout_extractor.py`](./scripts/cutout_extractor.py)
- **Procedural SFX Pack:** [`scripts/generate_stickman_sfx.py`](./scripts/generate_stickman_sfx.py)
- **Flow Decoders & Fetchers:** [`scripts/decode_scenes.js`](./scripts/decode_scenes.js), [`scripts/download_flow_urls.py`](./scripts/download_flow_urls.py)
- **Visual Review Grid:** [`scripts/build_review_sheet.py`](./scripts/build_review_sheet.py)
- **Post-Approval Zero-Bloat Purge:** [`scripts/purge_story_assets.py`](./scripts/purge_story_assets.py)
- **Responsive Anti-Wobble Remotion Rig + Archival / 2.5D Cam / Three.js Components:** [`resources/CutoutMotionTemplate.tsx`](./resources/CutoutMotionTemplate.tsx)

---

## Core Production Pipeline

1. **Topic Sandbox (`stories/<slug>/`) & Emotional Script (`<slug>_script.json`)**
   - **Per-Project Isolation:** Create `stories/<slug>/` matching the project/topic name. Download and store **ALL project-specific media** inside `stories/<slug>/` (`images_raw/`, `images_clean/`, `cutouts/`, `archival/`, `music/`, `<slug>_voice.wav`, `_script.json`, `_sfx_plan.json`, `_storyboard.json`). Shared reusable sound effects remain in `video-template/public/sfx/`.
   - **Emotional, Character-Centric Storytelling:** Tell an emotional, human-centered story driven by stakes, struggle, tension, and triumph rather than dry factual recitation (whether AI-authored or refined around a user script).
   - **Analyze Script for Rich Scene Extraction:** Break complex paragraphs into granular visual scenes so pacing stays energetic (`<= 4.2s` max beat duration; `75–90+` beats for 5-min `16:9` documentaries).
   - *Format Subtitle Rule:* **`16:9` Long-Form Documentaries NEVER show burnt-in or printed subtitles.** Boxed captions belong strictly to `9:16` Shorts.
   - *Mode Visual Rule:* **`v1.1`** allows classic `CutoutPuppet` expression beats + `dataCard`/`BarComparison` overlays matching Apollo. **`v1.2`** restricts `dataCard` sideboxes to `<= 15%` and mandates active motion poses, visual metaphors, virtual camera movement, and 3D diorama showcases instead of static portraits + plain text.

2. **Mandatory Pre-Production SFX Blueprint, Audit & Missing-SFX Download (RUNS FIRST)**
   - Before generating Flow visuals or editing Remotion files, write **`stories/<slug>/<slug>_sfx_plan.json`**:
     - Identify **every type and count of SFX** usable across all acts (ambience beds, foley clicks/levers/footsteps, impacts/blasts, swooshes, telemetry pings, emotional stingers) — **more varied, literal SFX = better immersion**.
     - Map each SFX to its **exact beat ID, cue description, and timestamp**.
     - Check `video-template/public/sfx/` to flag `[HAVE]` vs `[MISSING]`.
     - **Find and download ALL `[MISSING]` SFX first** (`NASA Audio`, `Wikimedia Commons`, `Internet Archive`, `Freesound CC0` -> converted via `ffmpeg.exe` to 44.1kHz WAV in `video-template/public/sfx/`, synthesizing multi-layer foley only when real audio doesn't exist), guaranteeing every sound-producing visual (rocket boom, blasts, animal calls, transitions, switches, impacts) has its exact distinct file, until `validate_production_plan.py --check-files` passes. Use `--write-sfx-audit stories/<slug>/sfx_audit.json` to inspect HAVE vs MISSING cues cleanly.

3. **Background Variation Cap (`<= 2` Clips), `>= 2–3` Angles/Scene & Archival Clips**
   - **Hard Reuse Cap:** **Never reuse any single background image (`bgAsset`) for more than 2 clips (`count <= 2`) across an entire video.**
   - **Multi-Background Per Scene:** Generate **at least 2 to 3+ varied backgrounds & camera angles** for every recurring scene location (wide shot, close console/detail angle, over-the-shoulder/reverse perspective, night/alert lighting shift).
   - **Asset Budget Math:** `Distinct Backgrounds >= ceil((NonArchivalSceneBeats) / 2)` (typically `26–40+` varied backgrounds for 5-minute documentaries).
   - **Original Archival Video Integration + Audio Sync:** For documentaries covering real historical/real-world subjects, download authentic public-domain clips into `stories/<slug>/archival/`, trim/transcode with `ffmpeg.exe` (`1920x1080`, `30fps`, `yuv420p`), verify playback frames, and synchronize exact visual cut points with narration + SFX via `<ArchivalVideoStage>`.
   - *If running `v1.2`:* Also generate/acquire atmospheric score stems (`stories/<slug>/music/`) via `$0` CC0 downloads, **Google Flow Music (`flowmusic.app`)**, or paid **Gemini API `Lyria` (`lyria-3.5`)** organized by act mood (note: `flow.google.com` handles Images + Veo Video + Characters).

4. **Gemini TTS Voiceover & Flow Asset Generation (`stories/<slug>/`)**
   - Run `generate_gemini_story_tts.py` locking one consistent `voice` (e.g., `"Charon"`) across chapters into `stories/<slug>/<slug>_voice.wav`. Verified `generateContent` TTS models available on `GEMINI_API_KEY` (check live via `--list-tts-models`): `gemini-2.5-flash-preview-tts`, `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`, `gemini-3.1-flash-tts-preview`, and `gemini-2.5-pro-preview-tts` — the script automatically switches to the next available model on `429`/`503` quota errors.
   - Set Google Flow to `16:9` (or `9:16` Shorts), record baseline tile UUID, inject empty-background prompts + `#FFFFFF` cutout character/action-pose/prop prompts, decode to `stories/<slug>/images_raw/`, clean watermarks via `gwr remove` into `stories/<slug>/images_clean/`, visually inspect all assets via `read_file`, and extract with `cutout_extractor.py` (`splitMode: "neck"` for split dialogue rigs, `"whole"` for dynamic action poses, `interiorWhiteThresh: null` for white spacesuits/coats).

5. **Pre-Flight Rule Check, Remotion Assembly & Real Playback Verification**
   - Run validator:
     ```powershell
     python ".agents/skills/cutout-motion-explainer/scripts/validate_production_plan.py" `
       --version <1.1|1.2> `
       --storyboard "stories/<slug>/<slug>_storyboard.json" `
       --sfx-plan "stories/<slug>/<slug>_sfx_plan.json" `
       --check-files
     ```
   - **Unified Audio Pre-Mix (`>20` beats):** Mix voiceover + all beat-accurate SFX WAVs (+ ducked `-20 dB` vocal-pocket EQ-carved BGM stems if `v1.2`) offline in Python into ONE `<slug>_voice_mixed.wav` and mount a single `<Audio>` tag in Remotion.
   - Build `<Story>Video.tsx` using [`resources/CutoutMotionTemplate.tsx`](./resources/CutoutMotionTemplate.tsx):
     - **`v1.1`:** `CutoutPuppet`, `BarComparison`, `RadarSweepHUD`, `ElectricSplitPane`, `ArchivalVideoStage`, `TopChapterCard`.
     - **`v1.2`:** Also apply `<CameraRig25D>` + `<ParallaxPlane>`, `<ActionMotionLayer>`, and `<ThreeDioramaStage>` (`<= 1–2` persistent WebGL canvases max, `dpr={1}`, deterministic `useCurrentFrame()` camera transforms + `delayRender()` textures — zero `useFrame` jitter).
   - Verify TypeScript compilation (`npx.cmd tsc --noEmit`), inspect `4–5` `remotion still` PNGs across acts via `read_file`, render `.mp4` (`--concurrency=12`) to `output/`, and inspect real rendered `.mp4` video + audio segments via `read_file`.

6. **User Approval Gate -> Post-Approval Asset Cleanup**
   - **CRITICAL:** Keep `stories/<slug>/` intact after rendering so all scenes can be verified. **Only AFTER the video is completely rendered, inspected, AND the user explicitly says `"it's okay"` / approves**, execute:
     ```powershell
     python ".agents/skills/cutout-motion-explainer/scripts/purge_story_assets.py" --story <slug>
     ```
     removing every intermediate asset from `stories/<slug>/` and temporary staging under `video-template/public/<slug>/` while preserving the finished `.mp4` + metadata `.txt` in `output/` and reusable global SFX in `video-template/public/sfx/`.
