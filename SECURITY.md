# yourFittingRoom security boundary

Updated 14 October 2026. This is a local development build, not a certified or publicly released application. See [SECURITY_RELEASE_PLAN.md](SECURITY_RELEASE_PLAN.md) for remaining gates and evidence.

## Local photo workspace

The fixed React workspace is served from the installed companion at `http://127.0.0.1:8765`. Only manifest-listed assets with matching byte counts and SHA-256 digests are served. Its CSP blocks remote scripts, remote connections, frames and browser workers. There are no ad scripts, analytics or cloud photo endpoints. File selection, crop, previews and saved looks remain in temporary browser memory. Refresh clears that memory and requests engine-session revocation; a crash can prevent delivery, so engine expiry is the fallback.

The expanded project category catalog is shared by client and broker. The user confirms a garment’s intended Women/Men/Unisex range and explicitly chooses the wearer profile; no gender/identity classifier is run on person images. Missing declarations and mismatched non-unisex ranges are rejected before inference in both client and API. This validates declarations, not the actual gender of the person pictured. Garment visual details use isolated clothing pixels where available; exact fibre composition is never asserted from an image. New category routing does not imply validated output quality. Existing download archives remain unchanged until rebuilt.

The workspace accepts clothing-image uploads. Remote product import is disabled there; an optional original product link may be attached to a garment. The separate local Next.js development UI at port 3000 retains the protected importer. That developer page is an additional trusted origin and should be removed from the final installer profile.

Asset hashes detect accidental or partial changes; the local manifest is not yet signed. A future release must sign the bundled UI and executable components. Native isolation does not make remotely served photo-selection JavaScript trustworthy. No owner-controlled hosted page receives selected person photos or results automatically.

## Authorization and lifecycle

- The listener binds to loopback. Client address, exact Host and allowed local Origin are checked. Same-origin browser GETs that omit Origin must carry `Sec-Fetch-Site: same-origin`; other requests still require an allowed Origin. DNS-rebinding Hosts and unrelated/former hosted origins are rejected.
- A random startup pairing code creates separate in-memory browser-session credentials after consent. Credentials last up to four hours and are not stored in cookies, localStorage or a hosted service. Pairing attempts, active sessions, concurrent requests and generation frequency are bounded.
- Jobs, results and cancellation are owned by the creating session. Another paired tab cannot read or delete them.
- `POST /session/revoke` invalidates authorization before cleanup, stops that owner's worker and purges its results. It is idempotent. Failed cleanup leaves a retryable revocation record; the client keeps credentials only to retry cleanup and blocks all new image processing. Late image responses after withdrawal are discarded.
- Expiry sweeps retry incomplete cleanup without preventing other sessions from expiring. Uncollected finished results expire after 30 minutes. Collecting a result requests server deletion. Browser copies remain until cleared.
- Cancellation terminates the single supervised worker rather than waiting for the next diffusion step. A worker watchdog exits if its broker dies. Graceful engine shutdown stops the worker and clears session/job records.

## Mac inference isolation

The lightweight HTTP broker never decodes person/garment images or loads Torch. Selected image bytes pass through bounded, length-prefixed JSON pipes to a supervised macOS App Sandbox worker. No arbitrary URL, file path, executable command, pickle or shell API is accepted by inference.

The internal worker is ad-hoc signed with App Sandbox entitlements. Narrow temporary absolute-path exceptions allow read-only trusted runtime/code/model folders and writes to one disposable cache. No Internet networking entitlement is granted. Actual tests prove unrelated file reads/writes, Internet connection attempts and shell spawning are denied while cache access and Metal inference work. This is evidence for this machine's development profile, not portable release certification.

One operation runs at a time. Analysis has a 300-second deadline and generation a 600-second deadline. The supervisor samples worker resident memory and terminates it above 12 GB. These are failure limits, not promised completion times or a hard limit on total GPU/OS memory. Frame/queue sizes, input bytes/pixels, open files and per-file writes are bounded; child-process creation and core dumps are disabled. Image decoding checks the actual format and rejects unsupported/multi-frame inputs. Errors do not echo images or raw model exceptions.

The broker still runs with the current user's OS permissions. Final native broker/file-selection isolation, portable entitlements, aggregate cache quotas, clean-machine tests and an independent review remain unfinished. Memory cleanup is not guaranteed forensic erasure; OS swap and system diagnostics remain outside app control.

The updated Windows source now includes an experimental AppContainer/Job Object worker. It has not been executed on actual Windows. Startup is opt-in; every worker launch must pass real token, file/network/child-process denial and compute checks. The process is created suspended, assigned to a one-process, kill-on-close Job with 12 GB committed-memory limits, then resumed. It inherits only three anonymous-pipe handles. `Test Windows.cmd` adds cancellation, crash, small memory-cap and broker-death recovery checks. The broker must stop the worker and remove its private ACL grants/profile/cache on normal cleanup; a broker crash can leave narrow ACL/profile/cache remnants until recovery. Dedicated GPU VRAM and aggregate disk usage are not bounded by that Job limit. See [Windows testing](WINDOWS_TESTING.md). This is not a supported Windows release, and the existing download is unchanged. Missing worker/GPU support never triggers unrestricted inference or a cloud fallback.

## Build and supply chain

Windows now has explicit NVIDIA CUDA, AMD ROCm, Intel XPU and CPU development profiles. GPU failures do not silently downgrade processing or relax AppContainer restrictions. Per-backend environments prevent Torch replacements across profiles; models remain shared. Selected-device numerical/operator probes run inside isolation on every worker launch. Intel/AMD use bounded-query attention and avoid an FP64 rotary requirement; no universal performance/compatibility claim is made. Adapter diagnostics retain only names/vendor/driver information. AMD's small source-only bootstrap is size/SHA-256 verified before bounded extraction and an explicit local build without automatic build isolation/dependency fetching. Other compute dependencies remain binary wheels. The full Windows dependency hash lock, installed-runtime verification and native-platform testing remain release gates. Details: [WINDOWS_TESTING.md](WINDOWS_TESTING.md).

AMD development toolchain exception: the official pinned Torch 2.12.0+rocm7.14.0 Windows wheel requires `setuptools<82`. Its private AMD environment therefore hash-pins setuptools 80.9.0; other Windows profiles and the Mac retain 84.0.0. PyPI reports [GHSA-h35f-9h28-mq5c / CVE-2026-59890](https://github.com/pypa/setuptools/security/advisories/GHSA-h35f-9h28-mq5c) against the older version: Unicode-normalisation mismatches can bypass exclusions when constructing source distributions. This implementation does not create/publish source distributions; its local wheel builds use only bounded, verified source trees in app-owned folders, with no photos/credentials mixed into build inputs. That limits the reported disclosure path, but is not a claim that the package has no advisories. Do not reuse this old toolchain for general packaging. Public release still needs a reviewed supported toolchain or a maintained upstream fix. Setup respects the Torch constraint and runs `pip check`, permitting only the existing explicit FASHN CPU-ONNX metadata substitution and rejecting all other dependency conflicts. The separate small AMD `rocm-bootstrap` wheel is pinned by URL/version/SHA-256.

FASHN source archives are checksum-verified before bounded extraction. Traversal, links, special files, modified source and extra imported modules are rejected. Main and prepared recognition models are checked before startup. Recognition hashes are a local build baseline, not an independent publisher attestation. Model-download work is separate from offline inference.

Mac registry dependencies and pip bootstrap use hash-locked binary wheels. Development source setup still installs/builds dependencies. The internal fixed-code Mac bundle embeds Python, dependencies, verified source and the fixed UI; it needs no end-user pip, Node or source build. Its model-data link points to this machine's verified development installation, so it is not a portable installer.

Latest local advisory evidence: npm reports zero known vulnerabilities; official PyPI metadata reports none for 67 checked packages, with source-only FASHN outside that coverage. These checks do not establish malware absence. CPU ONNX is an intentional upstream dependency-metadata deviation that needs a reviewed release build. Final licences/SBOM, artifact scanning, independent review and provenance are pending.

## Signing and release

No Developer ID Application/Installer identity is available on this machine. Ad-hoc worker signing enables internal sandbox tests; it does not establish publisher identity, notarization or remove Gatekeeper download warnings. Windows signing is also unfinished. No quarantine removal, OS-warning approval automation, protection disabling, administrator rights, startup persistence, remote administration or public scanner submission is performed.

Remaining gates include portable installers/model storage, repair/uninstall, signed update/revocation rules, legitimate signing/notarization, Windows isolation, supported-hardware validation and independent review of the exact final artifacts. Signing credentials must stay owner-controlled and out of chat/source/packages. No universal malware-free guarantee is claimed.

## Hosting

Hosting permission remains withdrawn. The former preview `https://wearview-desktop-beta.kumar-ankush0796.chatgpt.site` was replaced with an offline-only HTTP 503 response and its signing secret removed. Historical platform records remain. No publication, domain purchase, source push, invitation or paid service is authorized. See [AGENTS.md](AGENTS.md).

Historical hosting adapters and the browser AI experiment remain in source for development. They are not the active photo-processing flow or a reason to publish this application.
