# Local browser-inference experiment

No hosting or source push is authorized. The withdrawn hosted preview stays disabled.

The end-user flow is consent → compatibility check → verified download/cache → real execution checks → uploaded-photo analysis/try-on. No end-user terminal commands or native companion are required for this mode. A developer still starts the local Next.js site during development.

This experiment uses the installed, pinned FASHN/CLIP/parser weights. It exports CLIP image classification with fixed clothing text embeddings, human parsing, and a smaller 432×288 FASHN denoiser. The browser pose pass uses the whole photo as a padded region rather than the Python detector's multi-person box selection, so front-facing single-person photos are required. This is not a quality-equivalent replacement for the full-resolution Python pipeline.

Developer preparation, with the existing AI environment installed:

```sh
.runtime/ai-venv/bin/python -m pip install -r scripts/browser/requirements.txt
.runtime/ai-venv/bin/python scripts/browser/export_models.py
.runtime/ai-venv/bin/python scripts/browser/export_models.py --generation
.runtime/ai-venv/bin/python scripts/browser/prepare-generation.py
npm run browser:runtime
npm run dev
```

Generated graphs and weights stay under `.runtime/browser-models`, outside source control. The local `/api/browser-models/[name]` route serves only fixed model names on localhost; it does not receive photos. The worker fetches same-origin artifacts, validates byte lengths and SHA-256, and stores only model bytes in the app's CacheStorage namespace. Runtime assets are served locally, without a CDN. Consent stays in tab memory; returning visits re-consent and verify cached models. Clear cache affects only this app's model namespace.

ONNX conversion adjusts rotary-position constants to float32, matching the Mac adapter, and lowers RMSNormalization to WebGPU-supported primitives without changing trained weights. Runtime float16 arrays are decoded correctly whether stored as numeric Float16Array or Uint16Array bits. Model phases are loaded/released separately to reduce browser memory pressure. Setup reports Ready only after actual analysis, pose and denoiser execution checks.

Cancellation terminates setup workers or marks image jobs for cancellation at the next model step. Model caching never includes user photos. Browser jobs/results are in worker memory, expire after 30 minutes, and are removed after collection. Stopping AI or closing/refreshing the tab ends its worker. Selected images and saved previews remain in the tab until cleared or refreshed. Downloaded previews are separate device files.

Remaining release work: resolution/quality evaluation, device benchmarks, stronger low-memory handling and cache eviction tests, browser compatibility coverage, model/software license review, and model distribution without hosting personal-photo APIs. This is a local experiment, not a public release or universal device-support claim.

## Quality investigation, 13 October 2026

The user confirmed generation completed, then manually reset the session. The reported result was very poor and generation took too long. Reset is not evidence of a browser crash. That discarded result is unavailable for inspection; no exact duration was recorded for that run.

Corrected pose-map joint and face intensities, added hand edges, excluded foot dots, and rendered at source resolution before nearest-neighbour resize/padding. Whole-image pose cropping still differs from the native person's detected bounding box, and canvas rasterisation is not pixel-identical to OpenCV. The reduced 432×288 resolution remains a major limitation.

Found and corrected a conditioning bug: tops/shirts/T-shirts were assigned 0 (unconditional) and dresses 2 (bottoms). The trained/native model's IDs are 1 for tops and 3 for one-pieces, with 0 reserved for unconditional. This mapping now has a regression test. It is a plausible major cause of the unusable result; no finished image has yet established the size of its quality impact.

Float16 packing now rounds to nearest with ties to even, reuses scratch storage, and packs static conditioning once per job. Noise/time are reused between conditional/unconditional passes. Raw bit views are maintained even when ORT exposes numeric Float16Array. Twenty steps still require 39 model executions; no end-to-end acceleration claim follows from a packing microbenchmark. Jobs expose actual completed steps, elapsed time and last-step time, without percentages or predicted completion times.

Run `.runtime/ai-venv/bin/python scripts/browser/check-denoiser.py` for a developer-only synthetic comparison of the original PyTorch denoiser and the converted ONNX graph. The checked single conditional step had finite outputs and 0.333% relative RMS error with the correct tops category using CPU execution. This checks conversion, not WebGPU accuracy, pose quality or a finished preview. Full-image browser quality and speed remain release blockers.

`scripts/browser/render-native-baseline.py` uses only the two bundled public FASHN example photos and installed weights. On this Mac M5, native MPS at 432×288 with correct tops conditioning completed model loading in 2.86 seconds and preprocessing plus 20-step generation in 22.83 seconds. The inspected result places the black graphic T-shirt on the selected person and is coherent at this resolution, with limited graphic detail. This is a single native reference run, not an average, native full-resolution test or a browser performance/quality pass. It indicates reduced resolution alone does not explain the unusable browser result. A post-fix browser image retest remains outstanding; native file-picker testing was interrupted while Chrome was in use.

## Latency diagnostics

`node scripts/browser/benchmark-server.mjs` serves an isolated developer benchmark on 127.0.0.1:3001. It exposes fixed GET assets only, has no image/file-path/shell API, and never touches the fitting-room tab. The benchmark checks synthetic denoiser outputs and actual pass times; no full-image completion time follows from those measurements. Stop the server after testing. `tests/browser_attention.py` checks attention layout/scale/dtype equivalence and rejection of unsupported variants.

`prepare-attention.py` retains the original graph and prepares a candidate without changing weights or installing it. Standard ONNX Attention has no GPU kernel in this runtime; matching supported primitives or Microsoft-domain attention removes that bottleneck. Candidate graphs must pass numerical and visual evaluation. `install-attention.py` refuses installation without two completed candidate passes, finite outputs, the selected numerical tolerance and a matching candidate digest. Model installation changes only the denoiser graph and manifest; re-enable browser AI to load the new graph without refreshing away selected photos.

Current candidate status: **not installed**. It reduced a denoiser pass from about 50 seconds to 1.3 seconds, but failed the selected numerical tolerance on synthetic and public-photo inputs. `render-native-baseline.py --export-browser-fixture` exports only the bundled public example inputs and initial noise. The `/preview` diagnostic runs a full browser denoiser preview on these native-preprocessed public fixtures; two measured runs took about 55 seconds total. It is not the main app's browser pose/preprocessing path. Inspect its output before any promotion, and keep the failed numerical checks visible. Public fixture data contain photographic tensors from those examples; they contain no private user photos. The diagnostic server serves them by fixed GET names and accepts no uploads.
