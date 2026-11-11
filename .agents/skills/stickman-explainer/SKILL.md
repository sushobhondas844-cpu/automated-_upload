---
name: stickman-explainer
description: >-
  End-to-end production workflow for viral stickman explainer videos (9:16 Shorts and
  16:9 long-form) featuring lightweight 2.5D multi-plane depth, gentle whole-body stickman
  model movement, subtle motion graphics accents, pre-planned & audited SFX cues, single-call
  Gemini TTS voiceover (with multi-model quota fallback), Google Flow image generation,
  watermark removal, mandatory visual defect inspection + user review gate, Remotion assembly,
  and post-review zero-bloat asset cleanup.
---

# Stickman Explainer Production Workflow

Produce bright 2D / lightweight 2.5D stickman explainer videos cleanly with consistent voice, snappy beat cuts (every `1.5–2.8s`), pre-counted & audited contextual SFX, gentle whole-model movement (`2.5D` depth + subtle vector accents), zero watermarks, zero anatomical glitches, and zero leftover asset bloat.

## Bundled Files
- **TTS, Multi-Model Auto-Fallback & RMS Aligner:** [`scripts/generate_gemini_story_tts.py`](./scripts/generate_gemini_story_tts.py)
- **Pre-Production SFX Counter, Validator & Pacing Gate:** [`scripts/validate_sfx_and_plan.py`](./scripts/validate_sfx_and_plan.py)
- **Procedural Cartoon SFX Pack:** [`scripts/generate_stickman_sfx.py`](./scripts/generate_stickman_sfx.py)
- **Whole-Body Stickman & Prop Cutout Extractor:** [`scripts/cutout_extractor.py`](./scripts/cutout_extractor.py)
- **Flow Decoders & Fetchers:** [`scripts/decode_scenes.js`](./scripts/decode_scenes.js), [`scripts/download_flow_urls.py`](./scripts/download_flow_urls.py)
- **Visual Review Grid:** [`scripts/build_review_sheet.py`](./scripts/build_review_sheet.py)
- **Zero-Bloat Purge:** [`scripts/purge_story_assets.py`](./scripts/purge_story_assets.py)
- **Remotion Hybrid 2D / 2.5D Scene Template:** [`resources/StickmanExplainerTemplate.tsx`](./resources/StickmanExplainerTemplate.tsx)
- **Prompts, `#FFFFFF` Cutout Layering, Flow DOM & Long-Form Guide:** [`references/flow-and-pacing-guide.md`](./references/flow-and-pacing-guide.md)

## Production Steps

1. **Draft Timed Script JSON (`stories/<slug>/<slug>_script.json`)**
   - **Rule 1: Multi-Cut Rapid Hook (0.0s – 5.0s):**
     - The opening hook MUST have **at least 3 to 4 rapid visual cuts (1.0s – 1.5s per beat)**.
     - Split the opening thought into punchy visual beats (action -> hazard -> reaction -> cliffhanger).
   - **Rule 2: Dynamic Audio-Driven Beat Count Formula:**
     - `Required Scenes = ceil(Total Audio Duration Sec / 2.5s)` (`12–14` scenes for `30s`, `18–20` for `45s`, `24–26` for `60s`).
   - **Rule 3: Hard Per-Scene Ceiling (Zero Stretches):**
     - No single image or visual setup stays static for 4+ seconds; cut within **1.5 to 2.5 seconds** (absolute max `2.8s`).
   - **Choose Hybrid `panel` vs. Lightweight `2.5d` Beats:**
     - **`"panel"` (default):** Single full-bleed comic panel `scene_XX.jpg` with camera motion (`zoomIn`, `zoomOut`, `panRight`, `panLeft`, `scrubPulse`, `impactShake`) — fast and crisp for rapid `1.0–1.5s` hook cuts.
     - **`"2.5d"` (gentle model moving + depth):** Pairs a reusable empty comic background (`bgAsset`) moving slower at `0.36x` with a transparent whole-body stickman cutout (`modelAsset` at `1.0x`) performing light whole-body motion (`modelMotion`: `idleBob`, `strideRight`, `strideLeft`, `leanForward`, `popIn`, `floatZeroG`, `shakeHit`) plus optional floating `propAsset` (`0.70x`) and subtle vector accents (`fxAccent`: `none`, `dust`, `popRing`, `eurekaSparks`, `speedLines`).
     - Reuse `2–3` varied empty backgrounds cleanly per recurring scene (`<= 3` beats per `bgAsset`) so asset count stays lean while the stickman moves smoothly over depth.

2. **Pre-Production SFX Blueprint, Cue Counting, Audit & Download Gate (RUNS BEFORE IMAGES)**
   - Write **`stories/<slug>/<slug>_sfx_plan.json`** mapping **every sound-producing visual and beat shift** (`{ "cues": [{ "beatId": 1, "atSec": 0.0, "file": "sfx_water_splash.wav", "action": "..." }] }`) and assign `sfx` + `sfxVol` directly on beats in `<slug>_script.json`.
   - Run the counter & inventory check against shared `video-template/public/sfx/`:
     ```powershell
     python ".agents/skills/stickman-explainer/scripts/validate_sfx_and_plan.py" `
       --storyboard "stories/<slug>/<slug>_script.json" `
       --sfx-plan "stories/<slug>/<slug>_sfx_plan.json" `
       --write-sfx-audit "stories/<slug>/sfx_audit.json"
     ```
   - Inspect the exact tally (**Total SFX triggers**, **Distinct SFX files**, `[HAVE]` vs `[MISSING]`).
   - **Download or Generate ALL `[MISSING]` SFX first:** Fetch fitting public-domain / CC0 recordings (`Wikimedia Commons`, `Internet Archive`, `Freesound CC0` -> convert via `ffmpeg.exe` to `44.1kHz` WAV inside `C:\Users\susho\Downloads\antigravity\video-template\public\sfx\`), and run [`generate_stickman_sfx.py`](./scripts/generate_stickman_sfx.py) only for synthesized cartoon pops/whooshes/dings not covered by real audio.
   - Re-run validation with `--check-files` until **0 SFX are missing**:
     ```powershell
     python ".agents/skills/stickman-explainer/scripts/validate_sfx_and_plan.py" `
       --storyboard "stories/<slug>/<slug>_script.json" `
       --sfx-plan "stories/<slug>/<slug>_sfx_plan.json" `
       --check-files
     ```

3. **Generate Gemini Voiceover & Tight RMS Beat Timings**
   - Run **ONE** `generate_gemini_story_tts.py` call (`voice` defaults to `"Puck"`; tracks all 5 live API-key TTS models `gemini-2.5-flash-preview-tts`, `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`, `gemini-3.1-flash-tts-preview`, `gemini-2.5-pro-preview-tts` via `--list-tts-models` and auto-rotates on `429`/`503`):
     ```powershell
     python ".agents/skills/stickman-explainer/scripts/generate_gemini_story_tts.py" `
       --script "stories/<slug>/<slug>_script.json" `
       --out-wav "stories/<slug>/<slug>_voice.wav" `
       --out-storyboard "stories/<slug>/<slug>_storyboard.json"
     ```
   - Audition the `.wav` via `read_file`, then run pacing + SFX validation on the timed storyboard:
     ```powershell
     python ".agents/skills/stickman-explainer/scripts/validate_sfx_and_plan.py" `
       --storyboard "stories/<slug>/<slug>_storyboard.json" `
       --sfx-plan "stories/<slug>/<slug>_sfx_plan.json" `
       --check-files --check-pacing
     ```
   - Re-tighten locally with `--realign-wav` if pauses need refinement (0 extra API calls).

4. **Generate Flow Artwork (`panel` Scenes + Optional `2.5d` Empty BGs & `#FFFFFF` Models)**
   - Open Google Flow (`9:16` Shorts / `16:9` long-form, `x1`), capture baseline tile UUID, insert prompts into `[role="textbox"][aria-label="What do you want to create?"]` via `evaluate_script` + `execCommand('insertText')`, and submit via `press_key` (`Enter`). **Never call `take_screenshot` or `take_snapshot`.**
   - Wait until all tiles finish, verify monotonic `Expires` timestamps, download to `stories/<slug>/images_raw/`, and remove watermarks via `@pilio/gemini-watermark-remover` (`gwr remove ... --out-dir "stories/<slug>/images_clean" --overwrite`).
   - For `"2.5d"` beats, run [`cutout_extractor.py`](./scripts/cutout_extractor.py) (whole-body cutout with `interiorWhiteThresh: null` so solid white stickman head & torso pills remain opaque!):
     ```powershell
     python ".agents/skills/stickman-explainer/scripts/cutout_extractor.py" `
       --manifest "stories/<slug>/cutout_manifest.json" `
       --in-dir "stories/<slug>/images_clean" `
       --out-dir "stories/<slug>/cutouts"
     ```

5. **Mandatory Visual Audit + User Review Gate (Before Render)**
   - Inspect **every single cleaned image and extracted cutout** via `read_file` in batches (confirming two dot eyes, mouth, single stickman body, opaque white torso/head on cutouts, zero AI gibberish text, clean borders).
   - Build a numbered contact sheet with [`build_review_sheet.py`](./scripts/build_review_sheet.py), copy it to the conversation artifact folder, and wait for user approval before rendering.

6. **Remotion Assembly & Verification**
   - Stage images/cutouts -> `video-template/public/<slug>/`, voiceover -> `video-template/public/<slug>_voice.wav` (or `<slug>_voice_mixed.wav` when pre-mixing `>20` dense cues offline with `useMixedAudio: true`), storyboard JSON -> `video-template/src/<slug>_data.json`.
   - Build `<Story>Video.tsx` from [`resources/StickmanExplainerTemplate.tsx`](./resources/StickmanExplainerTemplate.tsx):
     - No top loading bar; crisp 2-line Top Chapter Card; fixed `impactShake`; exact `beat.sfx` / `beat.sfxCue` SFX playback; smooth `2.5d` multi-plane parallax + whole-body `modelMotion` + light `fxAccent` accents where configured; 3-word yellow-highlighted subtitles strictly for `9:16` Shorts (`isLandscape` hides them automatically in `16:9`).
   - Run `npx tsc --noEmit`, inspect preview `remotion still` frames across `"panel"` and `"2.5d"` beats via `read_file`, render to `output/<Language>/<slug>_explainer.mp4`, inspect real extracted `.mp4` frames & muxed audio via `read_file`, and write `output/<Language>/<slug>_metadata.txt`.
   - **Language-Specific Metadata & Pre-Publish SEO Research (Mandatory for all future videos):**
     - **Pre-Metadata SEO & Viral Keyword Research (Run Before Writing Metadata):**
       - Perform a search/research step for the specific topic and niche to identify the most viral, gripping titles, high-velocity search queries, and trending hashtags for both English and Indian audiences.
     - **English Videos (`output/English/<slug>_metadata.txt`):** 
       - **Title:** High-CTR, curiosity-driven English title researched specifically for the topic (e.g. `Why Does Chopping Onions Make Us Cry? 🧅😭 (It's NOT What You Think!)`).
       - **Description:** 2–3 hook-driven lines in English explaining the mystery + proven topic hashtags (`#Shorts #Facts #Science #Curiosity`).
       - **Tags:** Researched English tags and search queries targeting US/Global audiences.
     - **Hindi Videos (`output/Hindi/<slug>_metadata.txt`):**
       - **Title:** **Written in Hinglish (English letters with Hindi words)** — natural conversational phrasing that Indian viewers actually search and click on (e.g. `Pyaj Kaatne Par Aankhon Se Aansu Kyu Aate Hain? 🧅😭`).
       - **Description:** **Written in Hinglish (English letters with Hindi words)** — 2–3 punchy sentences explaining the core curiosity in conversational Roman-script Hindi, followed by trending viral hashtags:
         *(e.g. "Kya aapne kabhi socha hai, pyaj kaat te hi aankhon se aansu kyu nikalne lagte hain? Jaise hi knife chalta hai, pyaj ke chemical violent reaction se acid banate hain! Jaaniye iska real science... #Shorts #FactsInHindi #DailyFunFacts #HindiFacts #ScienceFacts")*.
       - **Tags:** Researched **Hinglish search queries and keywords** that people type into YouTube search bars (e.g. `pyaj katne se aansu kyu aate hai`, `pyaj ka science facts`, `hindi facts shorts`, `daily fun facts hindi`, `why onion make us cry in hindi`). Never use pure Devanagari script for Hindi metadata when Hinglish is specified.

7. **Approval-Gated Zero-Bloat Asset Purge**
   - Only after the rendered MP4 passes final verification (and user approves post-render if review is requested), run [`purge_story_assets.py`](./scripts/purge_story_assets.py):
     ```powershell
     python ".agents/skills/stickman-explainer/scripts/purge_story_assets.py" --story <slug>
     ```
   - Cleans `stories/<slug>/`, staged `video-template/public/<slug>/`, staged `public/*<slug>*.wav`, and `src/*<slug>*.json` while preserving final `.mp4` + metadata `.txt` in `output/` and all reusable SFX in `video-template/public/sfx/`.
