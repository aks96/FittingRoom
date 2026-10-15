# yourFittingRoom — local AI fitting room

Real uploaded person and garment images are used by local FASHN VTON 1.5 inference. The project and refreshed downloads route tops, shirts, T-shirts, sweaters, hoodies and jackets to `tops`; pants, jeans, shorts and skirts to `bottoms`; dresses and jumpsuits to `one-pieces`. New categories are experimental and need real-image quality validation. One garment at a time; shoes, accessories and layered multi-item outfits are unsupported. There is no cloud AI API, default-image substitution or physical-size prediction. This is a local development build; public release is not ready or authorized.

Garment detection provides editable category, colour, pattern, sleeve, clothing-range and fabric-appearance suggestions. Ambiguous range/material cues remain uncertain. Exact fibre composition must come from a label/retailer; fabric notes do not condition the image model. The wearer profile is explicitly selected, never inferred from a person photo. Confirmed women’s/men’s clothing must match that profile; unisex clothing permits either. Both client and broker block missing declarations and mismatches before generation. This checks declarations, not the person’s actual gender or identity.

Native preview settings offer Balanced (30 model steps, default) and Fast (20 steps). More steps take longer and do not guarantee photorealistic texture. Crops preserve up to 1600 pixels on the longest edge rather than always exporting at 600 pixels wide. The model still uses its native 576 × 864 canvas; no texture-restoring filter or new model was added. `tests/local_quality_smoke.py` tests a real preview and cleanup on public upstream fixtures only, with a pairing code read hidden from stdin.

Both development source downloads are refreshed with the current local UI and worker source. The Windows ZIP now includes the opt-in AppContainer/Job Object candidate with NVIDIA CUDA, AMD ROCm, Intel XPU and explicit CPU profiles, separate backend environments, adapter diagnostics and `Test Windows.cmd`. Real Windows execution is still unverified; GPU-specific hardware/driver and OS limits apply. See [Windows testing](WINDOWS_TESTING.md). Neither download is a signed installer or includes Python/model weights. Older downloaded copies do not update themselves.

## Run on this computer

The runtime/models are already installed here. From this project folder:

```sh
./scripts/ai.sh
```

Keep that terminal open, then visit **http://127.0.0.1:8765**. This serves the fixed local photo workspace directly from the companion; a separate web server is unnecessary. Enter the private pairing code printed by the companion and give selected-image processing consent. Refresh clears temporary photos/looks and requires pairing again. Models are reused.

The development website at http://127.0.0.1:3000 shows the download-first landing page, separate Mac/Windows choices, exact archive names/sizes/contents/checksums and setup steps. First-time download, extraction, setup, start, pairing/consent and photo-generation instructions are on this main page, alongside returning-user steps and launcher/opening help. Windows instructions require validation checks and explicit experimental startup. Open your local fitting room opens the installed companion on the same computer in a new tab; the website cannot install/start it or approve OS prompts. It does not select personal photos. Use `./scripts/dev.sh` for development. The full developer photo/import flow remains at `/development/fitting-room`, restricted to the local Host and excluded from the Netlify static export. The fixed workspace at port 8765 uses clothing-image uploads and optional original product links.

## Try it

1. Pair with consent, select a JPG/PNG/WebP garment image and review actual detected colour, category, pattern, sleeves and photograph type.
2. Confirm/correct the details, then upload one clear front-facing person photo. Crop, rotate, replace and remove edit the actual selected image locally.
3. Generate a local AI preview. Stages are real worker states; cancellation terminates its process. No percentages or completion guarantees are shown.
4. Toggle original/preview, zoom, favourite, save, compare and open the garment's attached original product details. Exports visibly label the result as an AI preview with physical fit unverified.
5. Disconnect withdraws engine consent and stops/purges that session. Clear temporary session data also removes browser images and saved previews. Downloaded files/models remain separate.

AI can change faces, hands, logos, patterns and proportions. A single photo cannot establish clothing size, measurements or precise physical fit. No official retailer partnership is claimed. This is a still-photo preview, not real-time camera/video.

## Current security work

Inference now runs in a supervised Mac App Sandbox worker. Actual tests deny unrelated file reads/writes, Internet connections and shell spawning. The local workspace blocks remote scripts/connections. Server revocation, ownership, cleanup retries, image limits, cancellation, runtime and resident-memory limits are implemented. Unsupported platforms/worker/GPU profiles fail closed. The Windows worker in the refreshed ZIP requires explicit experimental startup and successful per-launch isolation/compute probes; it remains unvalidated on actual Windows hardware.

The broker remains outside the OS sandbox and the worker uses development-only absolute-path exceptions. It is ad-hoc signed, not Developer ID signed/notarized. An internal embedded-runtime bundle exists at `.runtime/fixed-mac-bundle/yourFittingRoom-local`; its model link is specific to this machine. It is not a portable installer or a download for ordinary users.

See [SECURITY.md](SECURITY.md), [SECURITY_RELEASE_PLAN.md](SECURITY_RELEASE_PLAN.md) and [VERIFICATION.md](VERIFICATION.md). Legitimate signing, portable installers/model storage, Windows isolation, clean-machine tests, independent review and signed updates remain release gates. Nothing was publicly deployed in this iteration.

## Developer builds and checks

```sh
export PATH="$PWD/.runtime/bin:$PATH"
npm test
npm run typecheck
npm run build
node scripts/build-local-workspace.mjs
.runtime/ai-venv/bin/python scripts/build-fixed-mac-bundle.py
```

`build-local-workspace.mjs` exports the fixed React UI separately without touching hosting output. Restart the companion after rebuilding its local UI. `package-companion.mjs` packages explicitly allowlisted development source and verified UI assets; these archives still require source setup and are not final signed installers.

Python fault/authorization tests run without AI:

```sh
.runtime/ai-venv/bin/python -m unittest discover -s tests -p '*_test.py'
```

Real sandbox tests: `.runtime/ai-venv/bin/python scripts/test-worker-isolation.py`. The running-engine smoke test uses only public fixtures and asks for the local pairing code: `.runtime/ai-venv/bin/python tests/local_ai_smoke.py`.

`lib/services.ts` provides replaceable import/storage/analysis/generation interfaces. `local_ai/server.py` is the loopback broker; `supervisor.py` manages isolated workers; `worker.py`/`inference.py` execute offline models; `sessions.py` owns revocation/expiry. Dependencies, weights and private sessions are excluded from source downloads. Original references remain in `references/`; the slow browser AI experiment remains in `scripts/browser/README.md` for development only.

## Netlify website preparation (local only)

See [NETLIFY_DEPLOYMENT.md](NETLIFY_DEPLOYMENT.md) for the complete manual handoff. The user authorized local preparation, not deployment or another Git push.

```sh
# Only when companion source/UI changed: rebuild before building the website.
npm run build:companion-ui
npm run companion:package
npm test
npm run typecheck
npm run build:netlify
npm run check:netlify
npm run preview:netlify
```

The preview runs at **http://127.0.0.1:3002**. The static output is **netlify-dist/**; it contains only the download/setup site, supplied photography and companion source archives. The build generates CSP script hashes and download/security headers and rejects unexpected assets. It does not include developer/photo API routes, models, private runtime data or Sites identity. The old `build:site` target is not the Netlify build. Netlify needs no AI keys or photo storage for this website.

No build/check/preview command deploys anything. Hosting permission remains withdrawn; the former preview is offline. Do not deploy, connect Git to automatic hosting, buy a domain or invite testers without new explicit authorization. A private Git repository and noindex do not make a hosted website private.

For a Windows developer testing only the website, use Node.js 22+, `npm ci`, `npm run build:netlify`, `npm run check:netlify` and `npm run preview:netlify`. These static-website commands do not install or test Windows AI. For generation, extract the refreshed ZIP and follow [WINDOWS_TESTING.md](WINDOWS_TESTING.md).
