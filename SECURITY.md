# yourFittingRoom private desktop beta: security boundary

This is a restricted beta, not a claim that the system is completely secure or certified for public production use.

## Hosted website

The existing Next.js UI is exported into a small Sites worker. The worker runs **only behind the Sites trusted dispatcher**. Visitor identity comes from that dispatcher; do not deploy this worker to an unprotected arbitrary worker URL or trust forwarded identity headers on a separate server. Local Next.js routes never accept identity headers as authentication.

Managed sign-in and sign-out use the hosting platform. No passwords, custom password reset system, paid identity API or account database are created. Sign-in can open in a popup, preserving the temporary photo draft in its original tab. Private beta audience access may require sign-in at entry; this is separate from the application’s generation authorization.

Every hosted generation requires a short-lived Ed25519-signed permission from an authenticated site identity, bound to the paired engine’s random challenge. The signing private key is a Sites secret. Only the public verification key is in source or the companion archive. Permission requests contain the challenge, never selected photos. The worker rejects photo-processing endpoints before reading their bodies. URL imports are disabled on the hosted beta, with the actual clothing-image upload fallback retained; local development retains its protected importer.

The production UI has a restrictive CSP with hashes for Next.js inline bootstrap scripts, no unsafe-eval, a fixed loopback connection allowlist, no framing, no referrer, nosniff, HSTS, and disabled camera/microphone/geolocation/payment/USB permissions. Styles permit inline attributes required by the UI. No advertising scripts, analytics or third-party client SDKs are loaded. Such additions require a fresh privacy/security review.

## Local companion

- Listener and client restricted to loopback; strict Host and exact Origin allowlists defend against DNS rebinding and unrelated websites.
- Explicit local-processing consent and a random 192-bit startup pairing code. Credentials are never saved to cookies/localStorage or sent to the hosted server.
- Pairing yields separate random browser-session credentials, expires in four hours, and is rate limited. Reloads require pairing again. Restarting the companion revokes all sessions.
- Job reads and deletion are bound to their creating session. A second paired tab cannot read or delete another session’s jobs.
- Hosted generation additionally verifies the pinned site signature, issuer, challenge, lifetime and subject. Local-development generation is explicitly device-paired access, not a fabricated cloud account.
- Request bodies are bounded before parsing, read deadlines are enforced, image formats/byte size/pixel dimensions are checked, concurrent requests and generation frequency are limited, and the job queue is bounded.
- Only local image data is accepted by inference. There is no arbitrary URL fetch or file-path input in photo APIs. Validation responses do not echo personal images; model errors are redacted.
- Photos/results live in process memory. Collected server results are deleted, uncollected results expire after 30 minutes, and active cancellation is acknowledged at the next model step. Engine shutdown clears its process memory. Memory clearing is not a claim of forensic secure erasure, and OS swap/crash reporting remain outside app control.
- Native model downloads use pinned revisions and SHA-256 checksums for the main model, pose and parser weights; integrity is checked on engine startup. CLIP loads a pinned safetensors conversion. Setup downloads trusted upstream code and dependencies; it is not a signed installer yet.

## Verification and remaining release gates

Automated checks cover URL/file validation, no default-image substitution, hosted photo rejection without reading the body, missing/forged local identity, origin checks, signature verification, expiry/challenge/tamper checks, pairing, large bodies, content type, actual garment recognition, scope restrictions, cross-session isolation, cancellation/purge, and non-person-photo rejection.

JavaScript dependency audit reported zero known vulnerabilities on 12 October 2026. This is a point-in-time check, not proof of safety. The Python audit also reports no known vulnerabilities in registry packages after updating cryptography to 50.0.0 and pip to 26.2.1. The source-installed FASHN package is not on PyPI and could not be scanned. A tested macOS/Python 3.12 transitive dependency lock is included; audits and lock updates must be maintained.

Before opening public access: validate a clean companion installation on a second computer, verify browser local-network permissions without disabling browser security, verify managed sign-in/sign-out with invited testers, review model/software license obligations, complete a dependency/security review, document vulnerability reporting and incident response, and set an update/key-rotation process. Apple M5/16 GB is tested; other GPUs are not certified. Mobile generation and browser-only model execution are not implemented.

No security-sensitive user database exists. If server AI, persistent photos, real accounts or ads are introduced later, require a new threat model covering consent, retention, access control, abuse controls, billing limits, deletion and third-party data flows.

## Account usage and mutual isolation requirement — 13 October 2026

Try-on must not consume the owner's ChatGPT allowance or OpenAI API credits. The current app uses identity-only managed ChatGPT sign-in and local FASHN inference; it has no OpenAI inference API integration or shared owner AI credential. Authentication/session/pairing tokens are access credentials, not paid AI-generation credits. Any future paid API integration needs separate explicit approval and a spending cap.

Visitors authenticate with their own accounts. Owner deployment/service credentials and the site signing private key must stay out of browser bundles and companion downloads. The hosted site must not forward photo jobs to the owner's computer. A visitor's 127.0.0.1 refers to that visitor's computer, not the developer's.

The companion API may process only explicitly selected images and manage the originating session's jobs. It must not expose file browsing, arbitrary paths/URLs, shell execution, remote desktop, LAN access or a remote-administration tunnel. Current hosted photo routes are disabled; pairing credentials remain in tab memory, and there is no owner-facing user-photo viewer.

This is application-level isolation, not an operating-system sandbox. The installed Python companion runs with the user's OS permissions, and website code necessarily sees the selected images in that user's browser. Before public release, provide a reviewed, signed, sandboxed companion with least-privilege filesystem/network access and a secure update process. Do not promise that installing native code gives it zero device access or that an owner-controlled website can never be modified to collect data.

Official distinction: identity scopes and ChatGPT plan usage are separate permissions: https://developers.openai.com/siwc/quickstart
