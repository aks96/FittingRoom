# Development companion setup

This source package is not a signed production installer or certified malware-free. Mac inference uses an ad-hoc App Sandbox prototype. The Windows ZIP includes an opt-in AppContainer/Job Object worker candidate and Test Windows.cmd, not yet executed on real Windows. Python 3.12 is required separately on both platforms.

## Windows internal testing

Target Windows x64 with Python 3.12: CUDA/CPU candidates allow Windows 10 version 2004+ or Windows 11; AMD ROCm and Intel XPU candidates require Windows 11 and supported GPUs/drivers. CPU mode works with Intel/AMD processors but can be impractically slow. None of these profiles has been tested on real Windows here. 16 GB system RAM alone does not establish GPU compatibility. In an updated source folder, open `Set up.cmd`, review detected adapters and choose a backend, run `Test Windows.cmd`, review `.runtime/windows-validation/report.json`, and only then choose experimental testing in `Start AI.cmd`. In this project these launchers are in `scripts/companion`; a source archive puts them at its root. Use the verified bundled UI at http://127.0.0.1:8765. The current project testing guide is `WINDOWS_TESTING.md`; copy the static `.runtime/local-workspace` export when testing project source directly, not the Mac environment or personal data.

Each compute profile has its own `.runtime/windows-venvs` environment; models are shared. AMD setup defaults to multiple architecture packages, so its download/storage can be much larger. A developer can specify a known `--amd-target` to reduce it. The AMD bootstrap is a small, pinned/checksummed source archive built locally without automatic build dependencies. The remaining runtime wheels are pinned but the full Windows hash lock is still unfinished. No driver installation, third-party GPU translation layer or paid API is added.

Every Windows worker creation checks the actual AppContainer token, filesystem/network/child-process denials, cache access and chosen compute device before AI starts. Any failure disables generation without unrestricted/cloud fallback. A passing probe is not a full-model performance or image-quality test. No Windows pass, supported-device claim, signed installer or paid API integration is implied. Temporary private-SID ACL entries permit approved Python/model reads and cache writes; cleanup removes them normally, while crashes can leave narrow profile/cache/ACL remnants until recovery. The broker/setup still run with ordinary user permissions; never disable OS protections or force setup using administrator rights.

## This project on the tested Mac

Open the project folder in Terminal and run `./scripts/ai.sh`. The installed models and Python environment are reused and integrity-checked. Keep the terminal open; after startup visit **http://127.0.0.1:8765**, consent and enter its private pairing code. This is the fixed local workspace; no separate website server is necessary.

The tested profile is an Apple M5 Mac with 16 GB memory. Other Macs require validation. Unsupported GPU/platform profiles disable generation; there is no unrestricted or cloud fallback. Phones cannot run the native companion.

## Source setup on another development Mac

1. Extract the Mac archive into a folder you own. It contains source scripts and a fixed local UI, not Python, model weights, credentials or personal photos.
2. Install Python 3.12 from the official Python vendor if needed, then open `Set up.command` inside that extracted folder. Setup needs Internet/disk space for several GB of runtime dependencies and verified model data. It uses official package/model sources and sends no photos.
3. Wait for Setup complete, then open `Start AI.command` for each session. Models are checked and reused, not redownloaded for each generation.
4. Open `http://127.0.0.1:8765`, consent and enter the private code from that command window. Refresh requires pairing again.

Clean installation on another Mac remains unverified. Ordinary users should receive a legitimate signed/notarized installer after the release gates are completed. Unsigned `.command` downloads may still be blocked by Gatekeeper. No quarantine removal, automatic warning approval, security disabling or admin access is implemented. An OS warning is not resolved by ad-hoc worker signing; if protection detects malware, stop.

### HTTPS certificate errors on Mac

If setup reports `CERTIFICATE_VERIFY_FAILED` or no trusted root certificates, the python.org installation may not have completed its certificate setup. In Finder, open **Applications > Python 3.12 > Install Certificates.command** (Python's own helper). Wait for **update complete**, then reopen the companion's **Set up.command**. Python versions have separate certificate configurations; configuring Python 3.15 does not configure Python 3.12. Existing verified model downloads are reused.

The source setup now checks Python's CA trust before downloading source or dependencies. This check does not change certificates or system settings, and does not prove that every download endpoint will verify. If verification still fails after the official helper succeeds, check the system clock and any organisation-managed HTTPS proxy with its administrator. Do not use `--trusted-host`, an unverified SSL context or disable TLS verification. An already-downloaded archive keeps its original setup script until a new archive is explicitly built.

## Session controls and limits

Uploaded clothing/person images are decoded locally. Review detected details before confirming. Generation is a still-photo AI style approximation, not size prediction or precise physical fit.

The current project supports experimental categories for tops/shirts/T-shirts/sweaters/hoodies/jackets, lower-body pants/jeans/shorts/skirts, and dresses/jumpsuits. One item is processed at a time. Lower-body and one-piece previews require a person photo showing hips and legs. Review automated category and clothing-range suggestions; unsupported items are blocked. Select the wearer profile yourself after uploading a photo. The app does not infer or verify gender from images; it blocks conflicting declared clothing range/profile pairs in both UI and API. Unisex clothing permits either profile.

Fabric appearance is an editable visual estimate, not fibre-composition detection or a physics simulation. Use label information for material composition. Balanced preview uses 30 model steps; Fast uses 20. Neither guarantees photorealistic texture. Expanded categories are experimental; a supported routing category is not proof of image quality for every garment.

Cancel terminates the single worker and purges its result. Disconnect invalidates this tab's token, terminates its processing and purges its engine results; selected browser photos stay until cleared/refresh. Delete all session data also clears browser image/preview copies. A failed termination/cleanup is reported and generation disabled, with cleanup retry available. Closing the companion clears its sessions; the worker watches for broker death. Expiry is the fallback when a tab closes abruptly without delivering revocation.

Uncollected finished results expire after 30 minutes; credentials expire after four hours. Safety deadlines are 300 seconds for analysis and 600 seconds for generation, with a sampled 12 GB resident-memory ceiling. These are failure limits, not expected generation times. Downloads, models, OS swap and developer test artifacts require separate retention/deletion handling.

Do not share pairing codes, expose/forward port 8765, create a tunnel or bind to 0.0.0.0. Only allowlisted local origins can pair. The Mac worker has OS sandbox restrictions, but the lightweight broker/setup still run with user permissions. No remote shell or arbitrary file-path API is provided.

## Internal fixed-code bundle

The project's `.runtime/fixed-mac-bundle/yourFittingRoom-local` embeds Python, dependencies, verified source and UI; it does not run pip, Node or source builds on first use. This development bundle reuses a model-data link to this machine and builds an ad-hoc worker identity. It is not portable, notarized or a public installer. Its file inventory and preliminary CycloneDX SBOM support further review; signing, portable model storage, licence review, Windows isolation, independent scanning/review and clean-machine install/uninstall/update tests remain release gates. See SECURITY_RELEASE_PLAN.md in the project.
