# Netlify preparation and refreshed downloads — 15 October 2026 (local only)

- Built the fixed local React workspace and regenerated both explicitly allowlisted source archives. The Mac archive contains 58 files (10,248,688 bytes); Windows contains 70 files (10,233,791 bytes), including the current worker, backend profiles, three launchers and Windows test guide. Archive checks compare packaged source with the project and verify all bundled UI bytes against its manifest. No personal photos, model weights, environments or private keys are packaged. These remain unsigned source downloads with a separate Python 3.12 prerequisite.
- Added `build:netlify`, `check:netlify`, `preview:netlify`, `netlify.toml` and [NETLIFY_DEPLOYMENT.md](NETLIFY_DEPLOYMENT.md). The generated `netlify-dist` has 26 allowlisted files, approximately 24 MB on disk. Only the landing route is compiled; developer/photo API routes, browser AI assets, models, runtime data and Sites identity are excluded. The build verifies archive metadata and writes exact inline-script CSP hashes, attachment headers, no-referrer/nosniff/device restrictions, noindex and public archive checksums. Noindex is not access control.
- Both Next.js static builds and TypeScript validation passed. 21 JS regression tests, 77 Python tests and all 4 static-export/HTTP checks passed. HTTP tests verify actual download bytes/attachment headers, reject mismatched checksum metadata, and confirm 404s for unavailable API/developer/private paths plus 405 for POST. Loopback HTTP testing required sandbox permission; no public server or AI worker was started.
- Chrome review at 1440, 820 and 390 px showed no horizontal overflow. Mac/Windows switching, Windows experimental setup/checks/start instructions, checksum disclosure and both download action/status messages passed. The browser download API reported a Mac file path, but it was absent when checked locally; the saved-file browser check is inconclusive. Browser policy prevented inspection of its internal download manager, and no workaround or security bypass was attempted. Actual HTTP responses for both downloads have verified matching bytes/attachment headers; manually confirm saved browser files before sharing. Keyboard traversal exposed a 3 px visible focus outline. No console warnings/errors were captured. Screenshot: `screenshots/netlify-download-desktop.jpg`.
- No deployment, account connection, Git push, private-photo processing or fresh AI generation was performed. The preview is loopback-only. Actual Netlify response headers/adapter behaviour and Windows setup/isolation/GPU/model generation require testing on those environments. Installer signing, broker isolation, dependency review (including the AMD exception), clean-machine lifecycle/quality tests and other public-release gates remain pending. Earlier deployment notes below are historical; the former hosted preview remains offline.

# AMD/Intel Windows compute profiles — 15 October 2026

- Added native AMD ROCm and Intel XPU paths alongside NVIDIA and explicit CPU testing. Backends install into separate environments and share model files. Adapter diagnostics show vendor/name/driver; configuration selects only fixed app-owned runtimes and official pinned package indexes. AMD's small bootstrap archive is size/hash verified before a development-only source build.
- All 76 Python tests and 21 JavaScript tests pass. New tests cover vendor/API separation, wrong-build rejection, no automatic CPU fallback, OS/adapter restrictions, environment sanitisation, per-profile runtime paths, AMD target validation, bootstrap tampering/oversize rejection, dependency-conflict rejection, and numeric equivalence of query-sliced attention with complete key/value sequences.
- Actual CPU operator checks pass on this Mac. Actual MPS checks inside the Mac App Sandbox pass for matmul, attention, normalisation, rotary calculations, embeddings, convolution and random tensors; worker warmup/shutdown also pass. The first probe's nearly constant input made FP16 normalisation comparison unstable; representative varied inputs fixed that test fixture. No tolerance was loosened. This does not validate AMD/Intel GPU execution.
- Official package listings were checked for Windows CPython 3.12 Torch/torchvision XPU and AMD wheels. Bounded ZIP-directory/metadata reads from AMD's Torch wheel confirmed its exact ROCm and setuptools constraints; no large runtime was downloaded. AMD bootstrap source/runtime wheels were read and hashed without installation/execution. AMD's older build-tool advisory and scoped development exception are documented in SECURITY.md. No Windows dependency installation, AppContainer GPU run, full Windows generation, image-quality inspection or timing measurement has been performed. The Windows runner continues to refuse execution on this Mac, and no Windows pass report was fabricated. The full dependency lock and clean-machine hardware testing remain pending.
- Python compilation and packaging-script syntax pass. Existing website download archives/metadata are unchanged. No package, hosting artifact or deployment was created. Follow [WINDOWS_TESTING.md](WINDOWS_TESTING.md) using updated source; the old ZIP does not include these changes.

---

# Windows worker candidate — 15 October 2026

- Added AppContainer token checks, private-SID directory ACL grants, anonymous-pipe handle allowlisting, child-process restrictions and suspended creation with Job assignment before execution. Job limits cover one process, committed memory and kill-on-close. Added opt-in Windows startup and a Windows-only validation runner/report. These are source implementation and test contracts, **not Windows execution evidence**.
- All 55 Python tests and 21 JavaScript tests pass on this Mac. Eleven new cross-platform tests exercise launch ordering/failure cleanup, required OS-denial results, retryable ACL cleanup, platform rejection and worker-entry/compute restrictions. Win32 calls in those contract tests are fakes, not a real Windows sandbox.
- The Windows validation command correctly refuses execution on this Mac. No Windows report was created or marked passed. Windows 11/NVIDIA CUDA loading, full inference, cancellation/crash/memory tests on that OS and image-quality/performance measurements remain pending.
- Rebuilt the internal Mac sandbox prototype from updated source and verified actual MPS worker warmup and shutdown, without photos or a listener. The coding-tool sandbox initially prevented worker startup; the same check passed with the existing App Sandbox worker run outside that outer tool restriction. This is not a Windows compatibility test.
- Packaging-script syntax and Python compilation pass. Existing Mac/Windows archives and download metadata are unchanged; no package or hosting artifact was built or deployed. Instructions: [WINDOWS_TESTING.md](WINDOWS_TESTING.md).

---

# Website/download interface verification — 14 October 2026

This iteration implements the website preview and links the existing archives. No companion package was created/regenerated and no hosting build, deployment or invitation was performed.

- Next.js production build and TypeScript checks passed. All 20 JavaScript tests passed, including integrity checks against the exact existing Mac/Windows download files.
- Mac and Windows download URLs return HTTP 200 with the correct MIME type, exact byte counts and matching displayed SHA-256 checksums. The browser-saved Mac archive also matches its checksum.
- Windows selection and keyboard activation request the correct ZIP and show truthful Download requested feedback. The browser reported a target path, but Windows ZIP save completion was not confirmed on disk. Chrome's downloads-page inspection was blocked by browser security policy; no alternate browser surface or security setting was used to bypass that block. Direct served-file checks passed. This does not establish Windows installation or generation compatibility.
- OS buttons work with keyboard Enter/Tab, show aria-pressed selection and a visible 3 px focus outline. Checks at widths 1440/820/390 show no horizontal overflow. The main website has zero file-upload inputs; personal photo selection remains in the local workspace.
- The full developer fitting room remains at `/development/fitting-room`: local Host succeeds and unrelated Host returns 404. Website exports omit this route. The native export compiled successfully without deployment; its next version is retained separately. The existing live companion's verified static UI was restored without restarting its AI worker, and port 8765 continues returning HTTP 200.
- Recent Windows x64 devices with 16 GB RAM are the interface/download test target. No actual Windows hardware test or AI-isolation implementation was performed. Local Windows generation remains disabled.

Screenshots: `screenshots/download-website-windows-desktop.png`, `screenshots/download-website-tablet.png`, `screenshots/download-website-mobile.png`. These contain provided sample photography and public download metadata only.

---

# Current security implementation verification — 14 October 2026

Tests used public FASHN person/garment fixtures and disposable files only. No private user photos were uploaded, saved into reports, submitted to scanners or included in packages. No hosting operation or OS protection change was performed.

## Passed in this iteration

- Next.js production build, fixed local-workspace export and TypeScript checking.
- 19 JavaScript tests: upload/source contracts, scope, pairing/expiry, withdrawal blocking, retry credentials and late-response rejection, alongside retained browser experiment contracts.
- 29 Python tests: source/model/dependency tampering, HTTP Host/Origin/authorization, same-origin browser GET protection, revocation/retry/expiry, job ownership, queueing, termination, deadlines, RSS failure, crashed/malformed worker output, cancelled-before-start race, denied-termination tracking, expired-health cleanup/retry and fixed-asset traversal/tampering/CSP. Fault tests use disposable processes and mocked RSS; they do not claim exhaustive GPU memory profiling.
- Real Mac App Sandbox probes: unrelated file read/write denied, Internet socket denied, shell spawning denied, own temporary cache writable. No personal files were probed.
- Real orphan-worker check: the worker exited after its disposable supervisor terminated; no photos were sent.
- Running native API smoke: actual black graphic T-shirt recognition, invalid images/origins/tokens, men's unsupported category rejection, cross-session read/delete rejection, former hosted origin rejection, cancellation/purge and blank-person rejection. Revocation while the GPU was actually generating returned cancelled=1/purged=1; old-token requests failed, revocation retry was idempotent and another session remained authorized.
- The active-GPU test initially exposed a denied process-group signal. Cancellation now targets the one supervised worker and retains its process reference until confirmed dead. A termination failure disables processing and keeps cleanup retryable. The corrected active-GPU test passes.
- Browser journey at port 8765: consent/pairing, actual native garment/person file selection, local recognition, confirmation, real 20-step 576×864 preview and explicit Disconnect with acknowledged cleanup. The garment appeared on the chosen public test person; small logo/text details can still distort. No sample image was substituted.
- Result layout reviewed at 1440, 820 and 390 pixels. Page width matched each viewport with no horizontal overflow. Temporary viewport overrides were reset. Mobile layout does not imply mobile inference support.
- Internal fixed-code Mac bundle: embedded Python imports, verified source/models and embedded App Sandbox worker startup with MPS support pass. It needs no end-user package install for this development profile. Its model-data link is machine-specific; no portable/clean-install claim is made.
- Development archives were rebuilt from explicit source/UI allowlists. They include the new worker/lifecycle modules and verified UI assets and exclude runtime environments, weights, credentials and photos. Windows remains disabled for generation.

Public-fixture screenshots: `screenshots/sandbox-preview-desktop.png`, `screenshots/sandbox-preview-tablet.png`, `screenshots/sandbox-preview-mobile.png`. They are local ignored QA artifacts.

## Remaining coverage and release gates

No Developer ID/notarization, Windows signing/AppContainer test, sandboxed broker, portable installer/model-store/uninstall test, signed updater, independent security review or final malware scan has been completed. Worker entitlements use narrow development-only absolute-path exceptions. Resident-memory monitoring does not guarantee total GPU/OS memory bounds or forensic memory erasure. Package/model licences and the preliminary SBOM need review; CPU ONNX dependency metadata remains an intentional deviation. A full real preview proves this tested journey, not accuracy across bodies/garments or universal device safety.

The former hosted preview remains withdrawn; nothing was published in this iteration.

---

# Historical checks before this isolation iteration

The following earlier observations are retained as history. Current security/lifecycle behaviour is described above and in SECURITY.md.

# Offline AI verification — 12 October 2026

## Installer integrity hardening — 13 October 2026

Ten Python security/setup/integrity tests and seventeen JavaScript tests pass. Hardened native startup and the public-fixture smoke journey also passed: garment recognition, invalid image/origin rejection, session ownership, former hosted-origin denial, cancellation/purge and blank-person failure. Tampered wheel hashes are rejected by a real pip dry-run without installation. Source tests reject checksum changes, traversal, links, altered source and injected Python modules; recognition tests reject changed/missing artifacts. Mac's complete 62-package profile and pip bootstrap now use official PyPI wheel hashes with --require-hashes and --only-binary. Pip runs in isolated configuration mode; the source-only FASHN build is separately checksum-verified and still needs fixed-content production packaging. Windows's pinned dependency profile remains experimental and is not fully hashed or clean-install validated.

The installed source matches the pinned archive and startup verifies it before AI imports. All installed main weights and recognition baselines pass hash checks. Model downloads now stop at their expected byte lengths; parser config also has an integrity baseline. Recognition setup reused local models with offline environment flags and passed. The Mac hash lock passed an offline dependency dry-run against the installed environment. This does not verify installed wheel contents against publisher hashes or replace a clean installation.

Fresh npm audit: zero known vulnerabilities. Official PyPI release metadata check: 67 installed packages checked, zero reported advisory-bearing packages, one uncovered source package (FASHN). This is not malware scanning. Pip check still reports the intentional upstream onnxruntime-gpu declaration versus the CPU ONNX adapter; reviewed package metadata remains a production requirement. No independent review, platform sandbox, legitimate signing, notarization, malware-scanner execution, Windows hardware test or publication was completed. See SECURITY_RELEASE_PLAN.md.


## Mac warning help and experimental Windows package — 13 October 2026

The app offers separate Mac TAR / Windows ZIP downloads and platform-specific instructions, with Windows explicitly labelled experimental. Added unsigned-launcher warning explanations and Apple's per-app approval link; no OS warning was bypassed, quarantine removed, protection disabled, elevation requested or execution policy changed. This does not certify the package as malware-free or provide a signed installer.

Seventeen JavaScript tests, six Python setup/security tests, TypeScript and the production build passed. Offline recognition-model setup reused installed models without downloading. Live Mac loopback smoke checks passed for recognition, invalid inputs/origins, men's scope, session ownership, cancellation/purge and blank-person rejection after the CPU pose adapter change. Both download routes served archives whose hashes matched the packaged files. Package tests cover allowlists, CRLF Windows launchers, paths with spaces, x86-64/Python 3.12 bounds, fixed CPU/CUDA installation plans and hostile archive traversal rejection. They do not execute cmd.exe, install Windows dependencies or verify NVIDIA performance.

The Windows setup selects CPU or CUDA explicitly, probes CUDA before model download and persists only a device preference. Runtime fails if the configured GPU is unavailable. Mac retains its installed/tested Torch; Windows pins Torch 2.13.0 / torchvision 0.28.0 from documented official CPU/CUDA 12.6 indexes. Remaining dependency pins derive from the Mac environment; their resolution and wheel compatibility still need a clean Windows install. Pose/parser run on CPU, diffusion on the selected device, with bfloat16 used only when supported.

The platform selector, correct download links and launcher copy were verified in Chrome; Windows setup layout was reviewed at 390, 820 and 1440 pixels without horizontal overflow. Proof: screenshots/companion-windows-setup.png. Windows hardware/driver/VRAM checks, SmartScreen behaviour, real Windows inference and fresh Mac installation remain unverified. The original user's Gatekeeper-blocked download was not approved or executed through UI automation. No publication or cloud service was used.


## Companion-default implementation — 13 October 2026

The normal app now selects only the native companion setup; the browser experiment and its model artifacts remain preserved. Seventeen service, browser-contract and engine tests pass, including image preservation, default pairing gates, engine restart/expiry detection, wrong-code/network errors and route bounds. Two Python security tests pass. TypeScript and the Next.js production build pass.

The rebuilt download uses an explicit file allowlist; archive inspection found no personal photos, environments, weights, private credentials or AppleDouble metadata. Both root launchers and shell scripts have executable modes. An extracted archive in a path with spaces, launched from another working directory, produced actionable missing-Python and missing-model errors. This is not a clean-install verification. Shell syntax checks passed.

Live native smoke checks passed against loopback: black graphic T-shirt recognition, invalid image/origin/session rejection, men's category scope, cross-session job read/delete denial, hosted permit rejection, cancellation/purge and blank-person failure. Browser consent gating and native pairing succeeded. Public FASHN garment/person fixtures were selected with the actual native picker, recognised and confirmed. The 20-step full-resolution native preview completed and was visible when checked 121 seconds after the Generate click (an upper-bound observation, not an exact job time). Original/preview toggling and saving to the temporary collection succeeded. The result was visually inspected: the black shirt transferred to the selected person, while small printed lettering remained distorted. The local app served the rebuilt download with matching SHA-256. Setup screens were reviewed at 390, 820 and 1440 pixels with no horizontal overflow. Mobile layout support does not mean mobile inference support.

Clean installation on another Mac, downloaded-script quarantine behaviour, other GPU/OS configurations and signed/sandboxed distribution remain unverified. No cloud processing, paid API, source push or deployment was performed.


This update follows the user's explicit choice of strictly local model/server processing. The mannequin/manual collage path has been removed. No personal photo was sent to a cloud model or paid service.

## Real inference and recognition

- Installed and ran FASHN VTON 1.5 on Apple M5 / 16 GB, with Metal diffusion and CPU pose/human parsing. Runtime is offline; model/package downloads were inbound setup only.
- Actual men's test: the bundled seated person in a white T-shirt received the selected black graphic T-shirt. Generated output inspected at `screenshots/local-tryon-example.png`. One 20-step test took about 103 seconds; timing is an observation, not a completion promise.
- Actual women's shirt test: supplied original person photography received the Sage shirt. Output inspected at `screenshots/local-women-tryon-example.png`.
- Actual women's dress test: supplied original person photography received the selected black dress, using the one-pieces model category. Output inspected at `screenshots/local-dress-tryon-example.png`; server job purged after retrieval.
- Full browser upload journey: maroon floral garment screenshot → automatic Maroon/Top/Floral/Short sleeves detection → confirmation → native selection of supplied person PNG → real local job → maroon garment on the selected person. A second uploaded black T-shirt detected Black/T-shirt/Graphic/Short sleeves and produced a second preview for comparison.
- Visible size and physical-fit claims remain unknown. Quality evaluation is a small smoke test, not validation across all bodies, lighting, garment shapes or fabrics. Minor generated geometry/identity/print differences remain possible.

## UI and state transitions

Verified actual file selection through Chrome's native picker; no injected browser state or default output image was used. Chrome extension automation of `setFiles` is permission limited. PNG native selection works. Native macOS customised-file filtering can grey out WebP; Show Options → All Files allowed the actual WebP, and final app decoding/recognition succeeded. Drag/drop is another available fallback.

Checked clothing rotation, original ratio reset and applied crop, scope correction, keyboard confirmation and men's unsupported-shirt error. Checked original/AI toggle, zoom dialog and Escape, saving, favourites, filters, correct uploaded garment details, comparison, mobile Previous/Next and vertical comparison. The download completed in Chrome; the PNG was visually inspected with its visible AI-generated/fit-not-verified footer. The automation download event timed out despite successful native download history/file verification.

Removing the current person photo disabled try-on while retaining two generated/saved previews, as disclosed. Refresh cleared the session and collection. The final app was reopened after the successful build, and import-failure upload fallback was rechecked. Sample-link failure was tested in the final UI; an actual Myntra timeout/upload recovery and actual Quince product import were verified earlier. Retailer import remains best effort.

Reviewed mobile 390 × 844, tablet 820 × 1180 and desktop 1440 × 1000 layouts. Document width matched the viewport at all three sizes. Mobile preview precedes controls and the Try it on action stays fixed at the bottom. Comparison intentionally scrolls within its container. Proof screenshots are in `screenshots/local-ai-*.png`. No browser errors or warnings were captured in the exercised journey. Reduced-motion CSS disables animations and transitions; buttons, form labels, status announcements, heading focus and native modal focus handling are present.

## Automated checks

- Optimized Next.js production build passed; all nine generated routes completed.
- TypeScript passed.
- Eight service tests passed: distinct sample links, file type/size/empty validation, safe public URL handling, real JSON-LD and Open Graph extraction, missing-image failure, exact uploaded-file byte preservation in memory storage and category scope restrictions.
- `tests/local_ai_smoke.py` passed against the running final app: actual Black/T-shirt recognition, invalid image rejection, cross-origin rejection, men's scope enforcement, actual cancellation with job deletion returning 404, and non-person input failing with a clear photo-quality error rather than a substituted preview.
- Setup/run scripts passed shell syntax checks. Clean installation on a second machine and CUDA/CPU inference have not been tested. The installed Mac runtime works.

## Browser quality investigation — 13 October 2026

The user confirmed a browser-generated image completed, then manually reset. They reported very poor image quality and excessive latency. That reset was not a crash. The image was discarded by reset and has not been inspected; its exact duration is unknown. This run does not pass the realistic-try-on release gate.

Corrected category conditioning to match native trained IDs: tops/shirts/T-shirts 1, dresses 3; the prior 0/2 mapping meant unconditional/bottoms. Corrected pose-map joint/face intensities, hand connections, foot exclusion and source-resolution drawing followed by nearest-neighbour resize. Corrected float16 rounding, reused packing buffers, and packed static conditioning once per job. Added actual step counts, elapsed time and last-step timing to browser jobs and retained backend/resolution/time on results. Execution-check copy now explicitly separates runtime success from image quality.

Fifteen service/contract tests passed, including native category conditioning IDs, all finite half-bit round trips, ties-to-even/subnormal handling and reusable buffer behavior. TypeScript and the Next.js production build passed. A synthetic conditional denoiser step using identical inputs in original PyTorch and ONNX CPU had finite output, mean absolute error 0.002756, maximum error 0.01953 and relative RMS error 0.333% with category 1. This is a conversion test, not WebGPU or visual quality proof. A Node CPU feed-packing microbenchmark took 282.8 ms before and 9.4 ms after; it is not an end-to-end speed measurement. Twenty denoising steps still require 39 model calls.

Updated browser cache/GPU setup checks passed, as did actual upload/detection/confirmation of the public black graphic T-shirt. Setup was inspected at 390, 820 and 1440 pixels with no horizontal overflow; this does not assert mobile inference support. The full browser image retest is unfinished: native person-file selection could not continue while Chrome was being used. Do not count native reference images as browser outputs.

The developer-only native baseline on public FASHN samples at 432×288, 20 steps, category 1 on M5 MPS loaded models in 2.86 seconds and completed preprocessing/generation in 22.83 seconds. Its image was inspected: black T-shirt transferred coherently to the source person, while graphic text remains imperfect. This is one native measurement, not an average or full-resolution/browser performance verification. Files: ignored `.runtime/browser-native-baseline.png` and `.json`.

Browser setup/cache/GPU execution and visual output need separate coverage. Reduced 432×288 resolution, whole-image pose crop, browser rasterisation differences and long WebGPU inference remain known limitations. No quantisation, cloud/photo upload, paid integration, source push or deployment was performed for these fixes.

## Remaining limits

### Browser latency investigation, after the next cancelled user run

The user cancelled another browser job because it was too slow. The native 25.7-second measurement is not a browser estimate. The user's selected images/session were not refreshed, reset, replaced or sent to another backend during this investigation.

An isolated loopback benchmark measured original browser denoiser calls at approximately 49–51 seconds each; basic graph optimisation did not help. The export contains 28 standard-domain Attention operations unsupported by this runtime's WebGPU provider. Supported attention rewrites reduced single passes to approximately 1.3 seconds, without changing weights, resolution, steps or guidance.

The latest expanded candidate preserves split scaling and FP16 intermediate rounding, with float32 accumulation. Three attention conversion tests passed (layout/scaling, half-precision equivalence and fail-closed unsupported cases), plus all 15 service/contract tests. Both synthetic and public-photo numerical checks nevertheless failed the selected 1% full-denoiser tolerance. Latest drift: 1.354% synthetic relative RMS; 1.645% with native-preprocessed public photos, maximum absolute difference 0.15625. Do not relabel these checks as passes. No candidate was installed into the main app.

Two complete browser **model-core** previews using native-preprocessed bundled public FASHN photos completed at 20 steps and 288×432 pixels: generation 50.28/50.61 seconds, total local read + load + generation 55.04/54.97 seconds. The displayed second image was inspected against the native reference: person, pose and black graphic T-shirt are coherent, while background contrast and small details differ. This is not the main app's own browser pose/preprocessing journey, a precision/identity guarantee, an average across devices or release approval. Diagnostic-page CSP was corrected to display local data-URL previews; no private photo was involved.

Reports and public fixtures stay under ignored `.runtime/`; screenshot proof is `screenshots/browser-public-speed-test.png`. The original reference graph and main model/manifest remain intact. The diagnostic server exposes fixed GET assets on loopback only and is stopped after the checks. No app restart, source push, deployment, cloud AI or paid integration occurred.

Still-photo inference is not live-video or instant try-on. Exact physical fit, clothing-size prediction and guaranteed preservation of colour/print/identity are unsupported. Product import cannot bypass retailer restrictions. User-side downloads persist until separately removed. Automatic 30-minute server-result expiry is implemented but was not wall-clock tested for 30 minutes; immediate cancellation/purge and missing-job handling were tested. Authentication and persistent storage are intentionally absent. No deployment was performed.

## Secured private beta — 12 October 2026

- TypeScript check and production UI export passed.
- Eight existing service tests, five hosted worker security tests and two companion security tests passed.
- Secured live companion smoke checks passed: real black T-shirt recognition, invalid image and origin rejection, Men scope, separate-session read/delete denial, missing hosted generation permit rejection, cancellation/purge and blank-person rejection.
- All installed main/pose/parser model checksums match pinned official artifacts.
- npm audit reports zero vulnerabilities. Python audit reports no known vulnerabilities after upgrading cryptography and pip; the source-installed FASHN package is not scanned by that tool.
- Updated home/setup layout checked at 390, 820 and 1440 px: no horizontal overflow. Mobile generation remains unsupported.
- Clean companion installation on another computer and invited-user browser authentication/local-network permission remain release gates.

The private deployment succeeded and was opened in Chrome. Live checks returned: static home 200 with hashed-script CSP; visitor session 200 with authenticated=false when service access attempted forged identity headers; generation permission 401 without visitor identity; photo proxy 410. This verifies the hosting dispatcher strips forged identity headers and that service access cannot stand in for visitor authentication. Browser login reached the profile-sharing consent screen and is left for the owner to complete. Actual signed-in browser generation and browser-to-loopback network permission remain unverified on the hosted site.

## Expanded category and garment-detail verification — 15 October 2026

- Shared TS/Python catalog routes 12 supported categories to the native tops/bottoms/one-pieces model groups; unknown/unsupported categories are rejected. Image recognition now classifies against that catalog. New categories remain experimental; per-category real-image generation quality is unverified.
- Both UI and API require declared garment range/wearer profile compatibility. Women→Men and Men→Women mismatches, missing/unknown declarations and unsupported categories are blocked before inference; unisex permits either profile. Person-image gender is not inferred or verified. Tests include no photo request on a client mismatch and no worker invocation on an API mismatch.
- Garment-only crops exclude the retailer model’s face/skin for detail cues. Low-margin or unavailable garment isolation returns uncertain clothing range/fabric appearance. Exact composition is never asserted. Flat-lay foreground and skirt/pants segmentation labels have offline tests.
- 21 JS tests and 44 Python tests passed. Full Next.js build and the fixed native UI export passed, including TypeScript validation. Desktop checks at 1280/1440 px found no horizontal overflow. Unsupported category UI error and profile-mismatch error/disabled action were observed; selecting a matching profile cleared that error. Public person photo was selected via the native picker; Chrome’s extension upload helper required an unavailable file-URL permission, and no extension settings were changed.
- Actual sandboxed local analysis on the public upstream black graphic T-shirt returned T-shirt/Black/Graphic/Short sleeves, visual fabric suggestion Smooth woven, intended range Uncertain, and no composition claim. The API rejected its deliberate declared-range mismatch. A valid unisex/profile request completed a 30-step preview in 165.98 seconds at 576 × 864. Result cleanup confirmed the worker no longer loaded, then the QA engine was stopped. Files: ignored `.runtime/quality-review/native-balanced.png` and `report.json`. Output inspected: coherent shirt transfer; texture realism and logo fidelity are not guaranteed or claimed fixed.
- Screenshot: `screenshots/clothing-profile-mismatch.png`. Both public download archives are unchanged (download-integrity tests passed). Packaging code was updated to include the new catalog/modules and refresh metadata when explicitly invoked later; no packaging or deployment occurred. Windows generation remains disabled.

## Main website setup guide — 14 October 2026 (local only)

- Expanded the main download page with five Mac setup/use steps, returning-session instructions and opening/launcher troubleshooting. Windows instructions continue to state that AI generation is unavailable.
- Next.js production build passed, including TypeScript checks. Desktop browser review at 1280 and 1440 px found no horizontal overflow. Platform switching and keyboard-operated help disclosures passed; Mac Open action targets the same-computer companion in a new tab. No pairing codes or photos are requested on the website.
- Screenshot: `screenshots/main-website-setup-guide.png`. No companion archive was regenerated, no personal-photo session was opened and nothing was deployed. This checks the local guide, not future hosted-to-local browser permissions or a clean companion installation.
