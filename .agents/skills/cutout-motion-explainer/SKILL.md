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
- **`Version 1.1` (Locked Cartoon Vector + Integrated Scene, Rigging & Locomotion Presets Baseline — Default when requesting `"v1.1"`, `"older version"`, or `"current Apollo style"`):**
  Follows [`references/cutout-motion-v1.1.md`](./references/cutout-motion-v1.1.md). Preserves the **2D cartoon vector character rigging** (`CutoutPuppet` neck-split rigs + `IntegratedPuppetStage` scene lighting/ground shadow + interactive foreground `propAsset` sandwich), adds **Locomotion Walking/Pacing Presets** (`paceX`, `stepBob`, `bodyTilt`) and **Dedicated Action Props** (`prop_arm_pointing`, `prop_hand_stop`) alongside `ActionPropStage`, `BarComparison`, `DataCalloutCard`, `TimelineScrubCard`, `RadarSweepHUD`, `ElectricSplitPane`, `TopChapterCard`, and `16:9` zero subtitles — **strictly banning photorealistic humans/photography** so extractions never slice at the waist and characters blend cleanly into the 2D illustrated world. Canonically referenced in `stories/digital_arrest_scam/script_blueprint.md`.
- **`Version 1.2` (Next-Gen Cinematic Evolution — When requesting `"v1.2"`, `"newer version"`, camera/Three.js/music upgrade):**
  Follows [`references/cutout-motion-v1.2-research.md`](./references/cutout-motion-v1.2-research.md). Inherits **100% of `v1.1` rules** AND replaces passive talking/gasping portraits + side text with **Active Action Poses + Visual Metaphors** (`ActionMotionLayer`), **Multi-Plane Camera Choreography** (`CameraRig25D` + `ParallaxPlane`), **Deterministic `Three.js` 3D Diorama Stages** (`ThreeDioramaStage`), and **Aesthetic Background Music** (downloaded `$0` CC0 scores, Google Flow Music `flowmusic.app`, or paid Gemini `Lyria 3.5` with `-20 dB` vocal-pocket sidechain ducking).

---

## Bundled Files
- **Locked `v1.1` Spec:** [`references/cutout-motion-v1.1.md`](./references/cutout-motion-v1.1.md)
- **Researched `v1.2` Spec (Camera, 3D, Active Motion, Music):** [`references/cutout-motion-v1.2-research.md`](./references/cutout-motion-v1.2-research.md)
- **Technical Asset, Prompting & Extraction Guide:** [`references/cutout-and-motion-guide.md`](./references/cutout-and-motion-guide.md)
- **Production Rule Validator (`--version 1.1 | 1.2`):** [`scripts/validate_production_plan.py`](./scripts/validate_production_plan.py)
- **Interruption-Resilient Asset & Prompt Tracker:** [`scripts/asset_tracker.py`](./scripts/asset_tracker.py)
- **TTS & Multi-Chapter RMS Aligner:** [`scripts/generate_gemini_story_tts.py`](./scripts/generate_gemini_story_tts.py)
- **Cutout, Action-Pose & Rig Extractor:** [`scripts/cutout_extractor.py`](./scripts/cutout_extractor.py)
- **Procedural SFX Pack:** [`scripts/generate_stickman_sfx.py`](./scripts/generate_stickman_sfx.py)
- **Flow Decoders & Fetchers:** [`scripts/decode_scenes.js`](./scripts/decode_scenes.js), [`scripts/download_flow_urls.py`](./scripts/download_flow_urls.py)
- **Visual Review Grid:** [`scripts/build_review_sheet.py`](./scripts/build_review_sheet.py)
- **Automated Post-Render Frame Verification:** [`scripts/verify_rendered_frames.py`](./scripts/verify_rendered_frames.py)
- **Post-Approval Zero-Bloat Purge:** [`scripts/purge_story_assets.py`](./scripts/purge_story_assets.py)
- **Responsive Anti-Wobble Remotion Rig + Archival / 2.5D Cam / Three.js Components:** [`resources/CutoutMotionTemplate.tsx`](./resources/CutoutMotionTemplate.tsx)

---

## Core Production Pipeline

1. **Research & Topic Sandbox (`stories/<slug>/`), Compelling Script & Active Motion Audit**
   - **Research & Real-World Reference Sourcing First:** Execute active factual research (`stories/<slug>/research_brief.md`) before writing narration. Whenever the topic covers a **real-life person, place/landmark, or object**, download authentic reference photos/footage into `stories/<slug>/references/` (or `archival/`), inspect them via `read_file`, pass them as reference context into Google Flow, AND explicitly name the real landmark/person/object in every matching Flow prompt so visuals are faithful to reality.
   - **Per-Project Isolation:** Create `stories/<slug>/` matching the project/topic name. Download and store **ALL project-specific media** inside `stories/<slug>/` (`images_raw/`, `images_clean/`, `cutouts/`, `archival/`, `music/`, `<slug>_voice.wav`, `_script.json`, `_sfx_plan.json`, `_storyboard.json`, `asset_tracker.json`). Shared reusable sound effects remain in `video-template/public/sfx/`.
   - **Emotional, Character-Centric Storytelling & High Scene Density:** Tell a gripping, emotional story with high scene density (`1.5–2.6s` avg / `<= 3.8s` ceiling in `9:16` Shorts, e.g. `18–26` scenes per Short; `<= 4.2s` max beat duration and `75–90+` beats for 5-min `16:9` docs) and rich unique assets.
   - **Deterministic Active Motion Audit (`motionPlan`):** On every beat, audit which elements imply movement, physics, telemetry, lighting alert, or limb/prop action (`motion_graphics` vs `cutout_rig` vs `prop_action`), declare `motionPlan` in `<slug>_script.json`, and ensure animated elements are built dynamically in Remotion or as `#FFFFFF` cutouts — never baked static into background plates.
   - *Format Subtitle Rule:* **`16:9` Long-Form Documentaries NEVER show burnt-in or printed subtitles.** Boxed 3-word captions (`KineticSubtitles`) belong strictly to `9:16` Shorts.
   - *Mode Visual Rule:* **`v1.1`** mandates 2D flat editorial vector cartoon characters + matching `STYLE_DNA` backgrounds/props (ZERO photorealistic humans/photos!), integrates rigged `CutoutPuppet` inside `<IntegratedPuppetStage>` (ground shadow + scene lighting tint + foreground `propAsset` interaction), and rotates across 5 visual modes (`dialogueScene`, `actionPropScene`, `dataCompareScene`, `splitContrastScene`, `radarHudScene`/`archivalClip`). **`v1.2`** restricts `dataCard` sideboxes to `<= 15%` and mandates active motion poses, virtual camera movement, and 3D diorama showcases.

2. **Mandatory Pre-Production SFX Blueprint, Audit & Missing-SFX Download (RUNS FIRST)**
   - Before generating Flow visuals or editing Remotion files, write **`stories/<slug>/<slug>_sfx_plan.json`**:
     - Identify **every type and count of SFX** usable across all acts (ambience beds, foley clicks/levers/footsteps, impacts/blasts, swooshes, telemetry pings, emotional stingers) — **more varied, literal SFX = better immersion**.
     - Map each SFX to its **exact beat ID, cue description, and timestamp**.
     - Check `video-template/public/sfx/` to flag `[HAVE]` vs `[MISSING]`.
     - **Find and download ALL `[MISSING]` SFX first** (`NASA Audio`, `Wikimedia Commons`, `Internet Archive`, `Freesound CC0` -> converted via `ffmpeg.exe` to 44.1kHz WAV in `video-template/public/sfx/`, synthesizing multi-layer foley only when real audio doesn't exist), guaranteeing every sound-producing visual (rocket boom, blasts, animal calls, transitions, switches, impacts) has its exact distinct file, until `validate_production_plan.py --check-files` passes. Use `--write-sfx-audit stories/<slug>/sfx_audit.json` to inspect HAVE vs MISSING cues cleanly.

3. **Strict Zero-Looping Rule, Background Diversity & Consecutive-Reuse Ban**
   - **RED-LIST BAN #1 — Absolute Prohibition on Consecutive Replay:** **NEVER reuse the same background asset (`bgAsset`) in consecutive beats (`beat[i].bgAsset !== beat[i+1].bgAsset`).** Replaying or looping the same scene across consecutive cuts creates an amateur "restarting clip" glitch where momentum and zooms abruptly snap back to zero while the voiceover continues.
   - **Multi-Asset Multi-Angle Mandate for Long Sentences:** If a narration sentence or idea is long (> 2.0s–4.0s), you MUST generate multiple distinct assets and perspective angles so the sentence is visually carried across different shots rather than looping:
     - *Shot 1 (Action Wide):* Character or scene executing the action.
     - *Shot 2 (Macro Detail):* Extreme close-up on the critical prop, document, needle, or tool.
     - *Shot 3 (Top-Down / Reverse POV):* High-angle or reverse angle showing the aftermath or mechanics.
   - **Hard Reuse Cap:** A single background image may NEVER appear more than 2 times across the entire video, and those 2 appearances must be separated by at least 3 intervening scenes.
   - **RED-LIST BAN #2 — Mandatory Ducked BGM Lock:** Video without background music is an immediate production failure. Every video MUST include continuous ducked background music (-18 dB to -22 dB / Remotion `volume={0.15}`) from frame 0 to end.
   - **Original Archival Video Integration + Audio Sync:** For documentaries covering real historical/real-world subjects, download authentic public-domain clips into `stories/<slug>/archival/`, trim/transcode with `ffmpeg.exe` (`1920x1080`, `30fps`, `yuv420p`), verify playback frames, and synchronize exact visual cut points with narration + SFX via `<ArchivalVideoStage>`.
   - *If running `v1.2`:* Also generate/acquire atmospheric score stems (`stories/<slug>/music/`) via `$0` CC0 downloads, **Google Flow Music (`flowmusic.app`)**, or paid **Gemini API `Lyria` (`lyria-3.5`)** organized by act mood (note: `flow.google.com` handles Images + Veo Video + Characters).

4. **Gemini TTS Voiceover & Resumable Flow Asset Generation (`stories/<slug>/`)**
   - Initialize **`stories/<slug>/asset_tracker.json`** immediately after writing `flow_prompts.json` (`python ".agents/skills/cutout-motion-explainer/scripts/asset_tracker.py" init --tracker "stories/<slug>/asset_tracker.json" --prompts "stories/<slug>/flow_prompts.json" --slug "<slug>"`). Update each item as it progresses (`queued -> generated -> downloaded -> gwr_cleaned -> extracted`), and on any pause/timeout run `asset_tracker.py pending` to resume ONLY unfinished assets cleanly.
   - Run `generate_gemini_story_tts.py` locking one consistent **heavy, high-impact narrative `voice`** (`"Algenib"` default, or `"Charon"` / `"Alnilam"` / `"Orus"` / `"Fenrir"` — **light voices like `"Puck"`/`"Zephyr"` are banned**) with documentary Director's Notes across chapters into `stories/<slug>/<slug>_voice.wav`. Verified `generateContent` TTS models available on `GEMINI_API_KEY` (check live via `--list-tts-models`): `gemini-2.5-flash-preview-tts`, `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`, `gemini-3.1-flash-tts-preview`, and `gemini-2.5-pro-preview-tts` — the script automatically switches to the next available model on `429`/`503` quota errors. **CRITICAL PACING CAP & `> 60s` USER GATE:** Never speed up TTS narration beyond **`1.20×`** (`ffmpeg atempo <= 1.20`; target `1.00×–1.15×` relaxed cadence) — write Shorts tightly (~130–145 words) so raw TTS fits under `60s` naturally. **If generated `9:16` Short voiceover exceeds `60.0s`, STOP before rendering and ask the user whether to still render over 60s, rewrite the script shorter, or eliminate specific parts.**
   - **MANDATORY GOOGLE CHROME + `chrome-devtools` MCP CONNECTION RULE (NO BUILT-IN `browser` SUBAGENT FOR FLOW):** Always connect directly to the user's already-authenticated Google Chrome instance via the **`chrome-devtools` MCP server** (`list_pages` -> `new_page`/`navigate_page`/`take_snapshot`/`click`/`upload_file`/`evaluate_script`). **NEVER** delegate Google Flow asset creation or reference image uploads to the built-in `browser` subagent (which lacks the user's Google session cookies and hits `accounts.google.com` login walls). First check `list_pages` on `chrome-devtools` MCP to verify an active Chrome connection; if unavailable, pause and notify the user to ensure Chrome remote debugging is active.
   - Open Google Flow (`https://flow.google.com/`) inside Chrome via `chrome-devtools` MCP, open **Settings**, explicitly verify the `9:16` or `16:9` radio state (`x1`) is checked, record baseline tile UUID, attach any staged real-world reference photos (`stories/<slug>/references/...` via `upload_file`), inject empty-background + `#FFFFFF` cartoon character/prop prompts sharing the same project `styleDna`, download generated `flow-content.google` signed URLs to `stories/<slug>/images_raw/`, clean watermarks via `gwr remove` into `stories/<slug>/images_clean/`, run `cutout_extractor.py` (`splitMode: "neck"` for `v1.1` dialogue rigs, `"whole"` for `v1.2` action poses, `interiorWhiteThresh: null` for white coats/suits) + `build_review_sheet.py`, and visually inspect EVERY asset and `<name>_rig_preview.png` via `read_file`.

5. **Pre-Flight Rule Check, Remotion Assembly & Real Playback Verification**
   - Run validator:
     ```powershell
     python ".agents/skills/cutout-motion-explainer/scripts/validate_production_plan.py" `
       --version <1.1|1.2> `
       --storyboard "stories/<slug>/<slug>_storyboard.json" `
       --sfx-plan "stories/<slug>/<slug>_sfx_plan.json" `
       --public-dir "C:/Users/susho/Downloads/antigravity/video-template/public" `
       --check-files --check-pacing
     ```
   - **Unified Audio Pre-Mix (MANDATORY BGM + SFX + Voice):** Mix voiceover + all beat-accurate SFX WAVs + a fresh, topic-matched CC0/royalty-free BGM bed ducked cleanly at **`30%–35%`** relative bed volume (zero clipping, smooth fade-in/out; required for BOTH `v1.1` and `v1.2`) offline in Python into ONE `<slug>_voice_mixed.wav` and mount a single `<Audio>` tag in Remotion.
   - Build `<Story>Video.tsx` using [`resources/CutoutMotionTemplate.tsx`](./resources/CutoutMotionTemplate.tsx) (**NEVER hardcode ad-hoc head/torso offsets**):
     - **`v1.1`:** `IntegratedPuppetStage` (or `CutoutPuppet`), `ActionPropStage`, `BarComparison`, `DataCalloutCard`, `TimelineScrubCard`, `RadarSweepHUD`, `ElectricSplitPane`, `ArchivalVideoStage`, `TopChapterCard`, `KineticSubtitles`.
     - **`v1.2`:** Also apply `<CameraRig25D>` + `<ParallaxPlane>`, `<ActionMotionLayer>`, and `<ThreeDioramaStage>` (`<= 1–2` persistent WebGL canvases max, `dpr={1}`, deterministic `useCurrentFrame()` camera transforms + `delayRender()` textures — zero `useFrame` jitter).
   - Verify TypeScript compilation (`npx.cmd tsc --noEmit`), inspect `4–5` `remotion still` PNGs across acts via `read_file` (Checkpoint A), render `.mp4` (`--concurrency=12`) to `output/`, and run **Checkpoint B (Self-Healing Render Verification)**:
     ```powershell
     python ".agents/skills/cutout-motion-explainer/scripts/verify_rendered_frames.py" `
       --video "output/<Language>/<slug>_explainer.mp4" `
       --storyboard "stories/<slug>/<slug>_storyboard.json" `
       --out-grid "stories/<slug>/verify_render_grid.jpg"
     ```
     Inspect `verify_render_grid.jpg` + audio via `read_file`. If ANY visual defect appears (severed rig, photorealism leak, detached sticker look, watermark, static consecutive beats, bad crop, broken subtitles), **notify the user explicitly of the exact flaw found**, repair the broken asset/rig/TSX automatically, **re-render the `.mp4`**, and **re-verify** until 0 defects remain before final handoff.

6. **User Approval Gate -> Post-Approval Asset Cleanup**
   - **CRITICAL:** Keep `stories/<slug>/` intact after rendering so all scenes can be verified. **Only AFTER the video is completely rendered, inspected, AND the user explicitly says `"it's okay"` / approves**, execute:
     ```powershell
     python ".agents/skills/cutout-motion-explainer/scripts/purge_story_assets.py" --story <slug>
     ```
     removing every intermediate asset from `stories/<slug>/` and temporary staging under `video-template/public/<slug>/` while preserving the finished `.mp4` + metadata `.txt` in `output/` and reusable global SFX in `video-template/public/sfx/`.
