# yourFittingRoom — offline AI fitting room

yourFittingRoom uses the actual uploaded person and garment images. It now runs real local virtual try-on with [FASHN VTON 1.5](https://github.com/fashn-AI/fashn-vton-1.5), rather than a sample result, mannequin or manual collage. Women's tops, shirts and dresses and men's T-shirts are the current product scope.

## Run on this computer

The model, Python environment and Node runtime are already installed in this project. Use two terminals from the project folder:

```sh
# Terminal 1: offline AI processor
./scripts/ai.sh
```

```sh
# Terminal 2: web app
./scripts/dev.sh
```

Open http://127.0.0.1:3000. If either server is already running, stop the old process with Ctrl+C before restarting. **Check local engine** in the fitting room updates availability. No API key or paid service is required. Refresh ends the guest session.

## Try it

1. Select **Upload your clothing image**. Choose a JPG, PNG or WebP, up to 10 MB. The selected file is decoded and displayed; it is never replaced with a sample garment.
2. Local recognition suggests colour, category, pattern, sleeve length and model-photo versus flat-lay input. Review/correct suggestions and confirm the actual garment. Size and physical fit remain unknown.
3. Upload a person photo. Use one front-facing person with a visible face and torso, even lighting and arms away from the body. Show the full body for dresses. Crop, rotate, replace and remove controls edit the actual image locally.
4. Select **Try it on**. Real local job stages are polled while the model aligns inputs and generates the clothing on that person. Leaving the job screen keeps it running; cancellation is checked at the next model step.
5. Toggle original/AI preview, zoom, favourite, save, generate another outfit and compare. Downloads include a visible AI-generated/physical-fit-not-verified label.

Product import extracts JSON-LD and Open Graph images from public HTTPS product pages or direct image links. Retailers can block requests or require JavaScript. Import errors offer clothing-image upload. Retailer images and metadata require review. Optional original links stay attached to each outfit. Plum and Sage are explicitly labelled fictional sample garments with separate links, available only through explicit sample actions. A person photo is always selected by the user. On macOS, if the native picker greys out a WebP, choose Show Options → Format → All Files, or drag the image onto the upload area; app decoding and file validation still apply.

## Install on another machine

Use Python 3.12 and Node.js 22+. Install the web dependencies with `npm ci`. Then:

```sh
./scripts/setup-ai.sh
# Or select a Python 3.12 executable:
YOURFITTINGROOM_PYTHON=/path/to/python3.12 ./scripts/setup-ai.sh
```

Setup downloads several GB into `.runtime/` and installs an isolated Python environment. It contacts official GitHub/Hugging Face sources and the Python package registry for inbound downloads; it sends no personal images. The script is syntax checked, but a clean installation on another computer has not been tested. The running installation was assembled and verified with the same packages/models. The source download follows upstream main; pin its revision before distributing a release.

The Mac adapter uses Metal float16 diffusion, float32 rotary embeddings, meta-device weight loading and CPU pose/parser inference. CUDA and CPU paths are available but untested on other hardware. On this Apple M5 MacBook Air with 16 GB memory, one 20-step test took approximately 103 seconds. Cold loading adds time; timings vary. This is a still-photo preview, not live camera/video or instant fitting.

## Accuracy and privacy

- Real recognition and generation are connected. Suggestions can be uncertain. Lighting can distort colour; segmentation can include background; generated faces, hands, logos, prints or proportions can change. Compare the original carefully.
- Photos do not establish garment dimensions, brand sizing, stretch or physical fit. Accurate size recommendations need verified garment measurements, size charts, body measurements and fit validation. The app does not claim these capabilities.
- Runtime enables `HF_HUB_OFFLINE` and `TRANSFORMERS_OFFLINE` and disables Hugging Face telemetry. Analysis and generation use downloaded weights. The Next.js proxy has a fixed destination of `127.0.0.1:8765`; both servers bind to loopback. There is no cloud AI fallback.
- Input/output photos remain in browser/local-process memory. The AI service writes no photo files. The OS may manage memory through swap. Explicit downloads and developer QA artifacts are device files and need separate deletion.
- After collecting a completed result, the browser asks the server to purge it. Uncollected results expire after 30 minutes (checked every minute). Cancellation takes effect at the next model step. Stopping the AI server clears its process memory. Refresh requests cancellation, but closing/crashing cannot guarantee delivery.
- Saved previews contain input copies. Removing the current person photo alone keeps previews and active-job copies. Delete previews and cancel jobs, or use delete-all. No localStorage, database, real account, paid connection or public deployment is used.

## Architecture and checks

`lib/services.ts` exposes replaceable product-import, in-memory storage, analysis and generation interfaces. `lib/server/product-import.ts` bounds responses and protects public requests against private addresses and unsafe redirects. `lib/server/local-ai.ts` provides a bounded same-origin proxy to the fixed offline service. `local_ai/server.py` owns classification, segmentation, generation and cancellable in-memory jobs. `.runtime/` is ignored; model weights stay outside application assets.

```sh
export PATH="$PWD/.runtime/bin:$PATH"
npm test
npm run typecheck
npm run build
```

See [VERIFICATION.md](VERIFICATION.md) for observed results and coverage limits. Original references remain in `references/`.

## Proposed next phase

Keep local processing as the default. Add pose/occlusion guidance, validate diverse people and garments, and profile Metal inference before optimizing latency. Add optional body measurements and verified brand size charts as a separate fit feature with explicit uncertainty. Improve public product import without bypassing retailer restrictions. Real accounts and opt-in encrypted storage need retention/deletion policies; cloud photo processing needs a new explicit choice. Before release, pin model/source revisions, review component licences and build repeatable quality/privacy evaluations.

## Private hosted beta

The deployable UI keeps Next.js as its source stack. `npm run build:site` exports the UI into a narrow Sites worker. Hosted photo endpoints are disabled: the browser talks directly to the visitor's local companion after pairing. Hosted generation uses managed Sites sign-in and a signed permission; local development uses explicit device pairing. See [SECURITY.md](SECURITY.md) for the trust boundary and release gates.

Run `./scripts/ai.sh`, keep its private pairing code, then `./scripts/dev.sh`. In the website open Desktop beta setup, consent to local processing, and pair with that code. Refreshing ends the temporary photo session and requires pairing again. `node scripts/package-companion.mjs` creates a source-only setup archive for testers; it contains no weights, photos, credentials or virtual environment.

Verification: `npm test`; `npm run typecheck`; `npm run build:site`; `node --test tests/hosting.test.mjs`; `.runtime/ai-venv/bin/python -m unittest tests/security_test.py`; and, with the companion running, `.runtime/ai-venv/bin/python tests/local_ai_smoke.py` (enter its pairing code when prompted).

The private deployment requires invited access. It is not an unrestricted public launch. Do not deploy hosting/worker.mjs outside the trusted Sites dispatcher.

Owner-private preview: https://wearview-desktop-beta.kumar-ankush0796.chatgpt.site
The hosting platform requires sign-in before entry for this restricted beta. No friends have been invited yet.
