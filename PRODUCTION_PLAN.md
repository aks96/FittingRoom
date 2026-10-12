# yourFittingRoom: local-first launch with a $25/month ceiling

Planning date: 12 October 2026. Current launch scope: **desktop/laptop only, free local generation, a responsive web app, login at first generation, and a $25/month out-of-pocket ceiling**. Mobile inference and paid acceleration are deferred. This document proposes work; it does not enable cloud processing, purchase services, change the app or deploy anything.

## Desktop web release gates

Assume the preferred public experience is website-only, with an initial model download and no Python installation. Desktop scope alone does not provide that experience: our verified M5 generation still runs in an installed Python process. Browser conversion is the first release gate. If that gate fails, an explicitly installed desktop companion can support an earlier technical beta, but must not be presented as website-only generation.

| Priority | Required work | Current gap / acceptance evidence |
| --- | --- | --- |
| P0 | Complete browser-local inference | Current `lib/services.ts` posts photos to Next.js; `lib/server/local-ai.ts` forwards them to a Python process at the host's loopback address. Replace the browser-mode analysis/generation implementations with actual client inference. Prove selected person + selected garment → genuine generated image without a photo request to our server or a paid provider. Test converted model quality against the current reference pipeline. |
| P0 | Desktop/browser compatibility | Check runtime capabilities, allocation limits and a small benchmark; offer only validated quality profiles. Test Apple Silicon and Windows GPU configurations, including lower-memory failure recovery. Publish the specific supported browsers/devices; keep unsupported-device messaging clear. The M5 Python test is not a browser-generation test. |
| P0 | One-time model setup | Versioned model manifest, pinned source/model revisions, redistribution notices, download-size disclosure, byte-based real download progress, resumable/retryable loading, integrity checks, local model caching, cache eviction/re-download recovery and an explicit remove-model action. Inference stages still must not invent percentages or ETAs. |
| P0 | Login and privacy | Real authentication at first Generate, secure session handling and preserved in-memory drafts during login. Keep original photos and generation on the device. Server holds only necessary account metadata. No secrets in client code; protect any account APIs and retained development/companion routes. Verify network traffic during generation and deletion. |
| P1 | Local job lifecycle | Move heavy work off the UI thread, one running job per device, actual stages, cancellation, out-of-memory/GPU-loss recovery and clear tab-close/refresh behavior. Resume an interrupted model download where possible; do not promise resuming an interrupted diffusion job unless implemented. Navigating within the app must not accidentally destroy the job or its selected inputs. |
| P1 | Saved looks and deletion | Choose explicit persistence. Guest inputs remain temporary; optional Save on this device may use local storage suited to images, with clear expiry and deletion controls. Do not label a local-only look as synced to an account or another device. Model cache and personal-photo persistence are separate controls. Keep uploaded originals, result copies and device downloads clearly distinguished. |
| P1 | Security and product quality | Content Security Policy and script isolation, bounded retailer fetching/rate limits, actual image validation, dependency and model licence review, privacy/terms/support pages and misuse/report handling. Validate full journeys on a diverse garment/person evaluation set, visible focus and keyboard behavior, wrong-category recovery, actual product links and unsupported-device states. Keep size/physical-fit limitations visible. |
| P1 | Hosting and operations | Production builds, HTTPS, static model delivery/CDN with budget controls, compatible Next.js deployment, redacted errors/usage metrics, metadata backup/restore and rollback. Models are currently in ignored `.runtime/`; they are not production website assets. No private photos in telemetry, ad requests, backups or automatic cloud fallbacks. |
| P2 | Advertising | Implement the reserved desktop rail without squeezing the fitting room, initially as clearly labelled unconnected placeholders. Activate only after an approved, isolated integration; no local-mode pop-ups. Keep measured ad revenue separate from forecasts and keep total cash spend below $25. Ads are not a prerequisite for the first invite-only beta. |

Recommended execution order: browser inference proof → model download/cache and device checks → authentication/draft preservation → local jobs and explicit saving/deletion → privacy/security/quality checks → hosted staging and invite-only desktop beta → approved ads → wider launch. Prefer a focused browser/model proof before spending effort on advertising or a full production backend. No hosted GPU queue, paid API credit ledger or cloud photo bucket is needed for a purely browser-local first release.

## Recommended launch

The launch strategy is **free local generation first, paid acceleration later if traffic and funding justify it**. Users can generate as often as their supported device can handle, with one active job at a time and no hosted AI call. Start by proving device compatibility, then run a small local beta. The hosted allowances below are a future optional comparison, not a requirement to introduce a paid API at launch.

Local inference has no metered third-party AI fee. Users supply their own hardware and electricity. Our existing measurement was about 103 seconds for one 20-step image on an M5 MacBook Air with 16 GB memory. This is a tested still-photo workflow, not instant video fitting or a benchmark for other devices.

For this tested configuration, roughly 1.5–2 minutes is a useful initial expectation, not an established average across users. Cold model loading can take additional time. Measure several runs on each supported device and publish median and slower-case timings before release. If inference runs on the user's computer, yourFittingRoom has no metered AI charge. If it runs on the founder's computer for remote users, the founder still supplies electricity, hardware capacity, maintenance and uptime; this is an owner-operated server rather than on-device processing for those users.

The current implementation is a development app: Next.js proxies to a loopback Python service, jobs/photos are in memory, and there is no real authentication or persistent credit ledger. Uploading this project to a web host does not make that host's `127.0.0.1` refer to a visitor's computer. A local-first public web app needs a secure installed companion/bridge, or a new browser-native inference implementation. The current Python/PyTorch model does not run in a phone browser. This is a limitation of our current implementation, not a statement that on-device phone inference is impossible.

### Local desktop-browser feasibility milestone

Browser-side AI is possible using runtimes such as ONNX Runtime Web with WebGPU or CPU/WASM. However, GPU backends support only subsets of operators, and model size must fit device constraints. The current FASHN pipeline needs conversion/porting of generation, pose detection, garment parsing and preprocessing; adding a WebGPU package does not convert the whole pipeline automatically. Native phone deployment is another route requiring an optimized mobile build. [ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/).

Before promising a browser-only desktop release, prove a complete person-photo plus garment-photo generation on representative laptop/desktop configurations. Measure memory use, result fidelity, cold/warm latency, download size, cancellation and recovery. The current try-on weights alone are roughly 1.85 GB, with additional models/runtime on top. Smaller or quantized variants may improve feasibility but need quality testing. Android/iPhone inference is outside this first release.

Use available runtime capabilities, supported GPU features/limits and a conservative test allocation or small benchmark to select a tested quality profile. Browsers do not expose a dependable full hardware configuration, so do not promise exact RAM/GPU detection. Use reduced image dimensions or steps only where evaluated results remain acceptable. A CPU fallback may still exceed memory/time limits. Explain an unsupported local device clearly; never substitute a sample result or automatically upload photos to a paid provider.

Download and cache model files on supported devices with clear size/setup information. Keep person/garment images and inference local. Model delivery, website hosting, authentication and maintenance still consume owner resources, while the device owner supplies compute and power. The desktop companion can be the first supported release if browser/mobile conversion is not yet viable. Later add an explicitly selected Fast cloud mode without removing the free local option.

### Compatibility status and proposed test devices

These targets distinguish proven yourFittingRoom support from hardware worth testing. RAM/VRAM targets below are conservative test configurations, not established minimum requirements or performance guarantees.

| Device family/configuration | Current installed local engine | Browser-only generation |
| --- | --- | --- |
| Tested M5 MacBook Air, 16 GB memory | Verified on this particular machine; about 103 seconds in one measured test | Not implemented/tested |
| Apple Silicon M1/M2/M3/M4/M5 MacBook, iMac, Mac mini or Mac Studio, preferably 16 GB+ memory | Good candidates for the Metal adapter; each chip/OS configuration still needs validation | Candidates after browser conversion; no yourFittingRoom browser support claimed yet |
| Windows/Linux PC with NVIDIA RTX 30-series or newer; start tests with 16 GB+ system RAM and 12 GB+ GPU memory | CUDA candidate; installation, driver, memory and result quality need testing | Candidate after conversion on a suitable browser/GPU/runtime combination |
| Windows/Linux CPU-only machine or other GPU types | Experimental; no usable latency or memory compatibility established by our tests | No support established |
| 8 GB Macs, older Intel Macs, older GPUs and low-memory laptops | Not a supported launch promise; require separate dependency/memory/performance evaluation | No support established |
| Android phones/tablets, iPhone and iPad | Current desktop Python setup is not a mobile app | Experimental future targets; model conversion and end-to-end device tests required |

The upstream FASHN CUDA route uses bfloat16 on Ampere-or-newer NVIDIA GPUs, while our Metal adapter uses float16. Hardware acceleration support does not certify the complete yourFittingRoom application. [FASHN inference notes](https://github.com/fashn-AI/fashn-vton-1.5), [PyTorch Metal backend](https://docs.pytorch.org/docs/2.14/notes/mps.html).

Initial release test matrix: an older 16 GB Apple Silicon Mac, a newer 16 GB Apple Silicon Mac and a Windows NVIDIA desktop with adequate VRAM, plus deliberate tests of unsupported/low-memory cases. Phones are deferred. Do not publish support based only on chipset or WebGPU availability. Distinguish the responsive website working from AI inference working locally. Classify devices from an actual successful generation and measured memory/latency, rather than processor names alone.

## Processing options

| Option | Photo destination | Owner's AI costs | Release implications |
| --- | --- | --- | --- |
| Browser-local, preferred desktop release | User's own computer | No per-image API fee | Full model conversion, compatible runtime, download/cache and device validation are required; not implemented yet |
| Local companion, technical-beta alternative | User's own computer | No per-image API fee | Package/install model, authenticate the website-to-companion bridge, test supported hardware; installation and a large initial download |
| Hosted try-on API, optional | Named external processor, after consent | Published per-output fee | Simplest GPU operations for a tiny consumer beta; requires private uploads/results, retention controls, quotas and queue handling |
| Our model on a hosted GPU | A rented server, after consent | Compute, loading, idle time, storage and retries | Benchmark before selecting; not equivalent to on-device privacy; scales-to-zero workers can reduce idle spend |

Keep the local mode selected until the user explicitly changes it. If a device cannot run locally, explain that limitation and offer the optional hosted choice; never silently switch processing destinations. Restrict the first local release to hardware we actually validate. A signed/notarized installer, packaging and redistribution licence review are production work, with potential upfront costs outside ordinary hosting. Start a technical closed beta before promising a polished installer to all consumers.

## Hosted price correction

FASHN's published on-demand rate is **$0.075/credit**, with a **$7.50 minimum for 100 prepaid credits**. Try-on v1.6 costs one credit per output. The **$0.06** rate is the Tier II discounted rate associated with a **$249/month** commitment; it is not the startup pay-as-you-go rate. Failed predictions do not consume FASHN credits. Use the fixed-cost v1.6 endpoint and one output rather than assuming premium endpoints have the same cost. [API pricing](https://help.fashn.ai/plans-and-pricing/api-pricing), [v1.6 reference](https://docs.fashn.ai/api-reference/tryon-v1-6).

Disable automatic top-ups. Start with 100 credits; purchase another 100 only if needed within the monthly cash ceiling. Credit purchases are prepaid/non-refundable, and unused on-demand credits expire after 12 months. Subscription discounts are not a reason to exceed the budget. Prices here are published USD rates; payment fees, tax and domain registration must be checked before purchase.

## Ads: what a generation can earn

There is no fixed payment for an image generation. Google defines ad RPM as publisher earnings per 1,000 ad impressions. Use the publisher's observed revenue figure; do not subtract the network share again from an RPM that already represents publisher earnings. Geography, demand, format, consent, blockers, viewability and fill affect the actual result. [Ad RPM definition](https://support.google.com/adsense/answer/112032?hl=en-AO).

The following numbers are sensitivity scenarios, not forecasts for yourFittingRoom or India:

| Publisher ad RPM | Revenue from one monetized ad | Ads needed to cover $0.06 | Ads needed to cover $0.075 |
| --- | --- | --- | --- |
| $1 | $0.001 | 60 | 75 |
| $3 | $0.003 | 20 | 25 |
| $10 | $0.010 | 6 | 8 |
| $20 | $0.020 | 3 | 4 |

These cover AI only. They exclude hosting, failed-user-experience replacements, payment costs and support. Example: two monetized ad impressions at $3 ad RPM produce $0.006 per generation, covering only 8% of a $0.075 API charge. One ad must earn $0.075 on average—$75 net ad RPM—to cover that API cost by itself. Do not confuse page RPM with ad RPM: page RPM already aggregates ads on that page.

Budget initial ad income as **$0**. Ad approval, fill and payouts are not guaranteed. For a USD AdSense account the payment threshold is $100, so early recorded earnings may not provide immediate cash for prepaid inference. [Payment thresholds](https://support.google.com/adsense/answer/1709871?hl=en).

Place initial ads on public clothing guides/gallery pages with no personal photo data. Keep the private photo editor and results free of third-party advertising scripts until an isolated implementation has been reviewed. Never send photos, data URLs, filenames or body measurements to advertising/analytics systems.

### Updated advertising layout preference

Reserve a right-side desktop advertising rail with **up to three labelled slots**, starting around 300 px wide on sufficiently wide screens. Preserve the useful fitting-room preview width. Three 300 × 250 slots require 750 px before gaps and page chrome, so do not force all three into every laptop viewport: show fewer slots or let remaining slots continue below the fold. On tablet/mobile use fewer inline placements, without covering photo controls or the persistent Try it on action. Empty or blocked slots should collapse cleanly without distracting layout shifts.

Local mode has no pop-up ads. For optional hosted mode, evaluate an approved, explicitly chosen rewarded-ad experience; do not implement ordinary ads in custom pop-up/pop-under windows. Google AdSense prohibits ads in those windows, and requires appropriate balance between content and advertising. These reserved slots are a layout proposal, not approved inventory or a guarantee of ad-network acceptance. [Placement policies](https://support.google.com/adsense/answer/1346295?hl=en), [multiple ad units](https://support.google.com/adsense/answer/17958?hl=en).

Three slots do not imply three paid impressions per generation. Only actual monetized impressions count, and repeated generation in the same page does not itself establish new ad impressions. Example only: three monetized impressions at $3 publisher ad RPM earn $0.009, or $9 per 1,000 such generation visits. This could help cover local-mode hosting, but it covers only 12% of a $0.075 hosted AI charge before other expenses. Slot count does not justify increasing hosted credits until actual revenue is measured.

Use an actual rewarded format for optional ad rewards, rather than rewarding clicks or incentivized views of ordinary display ads. Google supports opt-in rewarded web formats, and requires clear disclosure and delivery of the promised platform-only reward. [Web rewarded ads](https://support.google.com/admanager/answer/9116812?hl=en), [reward policies](https://support.google.com/admanager/answer/7496282?hl=en).

Important implementation limit: Google's rewarded web format does not provide server-side reward verification. A browser callback is not trusted proof of payment. Do not grant unlimited expensive inference from it. Use narrow one-time server-issued eligibility records and hard caps, or evaluate an ad partner with trustworthy verification. Offer an ad-funded extra generation only after measured net revenue covers measured generation cost with a buffer, or from a clearly preallocated subsidy; do not promise a reward and then deny it for lack of budget.

## Proposed allowance and cash limits

| Mode | Starting allowance | Limit |
| --- | --- | --- |
| Local | Generous/unlimited on supported devices | One running job per device; no owner-funded API call |
| Hosted welcome | Two previews for comparison | One-time; drawn from the account's monthly allowance |
| Hosted ongoing free beta | Up to one additional preview per 7 days | Three total per rolling 30 days, including welcome previews |
| Hosted beta capacity | At most 50 eligible accounts | Five submitted jobs per UTC day and 150 per billing month across the service |
| Optional ad bonus | Disabled initially | Only introduce with measured economics and reserved capacity |

All hosted limits apply together; unused user credits do not override a daily/global spending limit. Show eligibility, quota reset dates and budget-unavailable states clearly. A rolling user quota and billing-month global quota need separate timestamps. An account is not proof of a unique human: authentication needs rate limits, bot checks and account-abuse controls as well.

Conservative hosted comparison budget:

| Item | Monthly allocation |
| --- | --- |
| Small commercial-capable frontend/API hosting | $5 target |
| Auth + small usage/job database | $0 within validated free-tier limits |
| Short-lived private image storage | $0 within validated free-tier limits |
| AI prepaid purchases | Maximum $15: two packs of 100 |
| Tax/fees/contingency | $5 reserved |
| Total cash ceiling | **$25** |

At the 150-image application cap, raw v1.6 inference is $11.25. Use $0.09 as a conservative planning allowance per submitted job (20% above the raw rate); this is a budgeting assumption, not a vendor quote. That makes 150 jobs a $13.50 planning allocation. Buying 200 credits costs $15 in cash even though only 150 may be used; unused credits carry within the provider's validity period. Do not treat them as refundable money.

Use the hosting platform's included subdomain for the closed beta so annual domain registration does not unexpectedly exceed the first month's cash limit. Quote a custom domain and any installer-signing charges separately before purchasing. Hard ceilings should account for committed/in-flight jobs as well as completed ones. Budget alerts alone do not prevent overspend.

If only local mode ships, there is no need to buy AI credits. Keep the unused allocation rather than spending it to exhaust a budget. Do not purchase an always-on cloud GPU before measuring demand and cost.

For comparison, 100 daily users receiving one hosted image every day for a 30-day month means 3,000 images: $180 at $0.06 or $225 at $0.075, before infrastructure. This does not fit a $25 ceiling.

## Login-at-generation flow

Desktop-local launch: browse → capability check → select garment → review visible details → choose/crop person photo → tap Generate → sign in if needed → download/cache local models on first use → initialize local engine → generate with actual stages → compare/save/download. Only necessary account metadata goes to the server. Local-mode colour/category analysis also needs a client implementation; do not leave it posting uploaded garments to the development proxy.

On a first visit without cached recognition models, show basic/manual garment review rather than fabricated AI detection. After the explicitly started model setup, run local recognition and request confirmation of its suggestions before actual generation. On later visits, cached recognition models can analyse new uploads before the user taps Generate. An alternative first-use setup prompt may occur before analysis, but model downloads must be disclosed and user initiated; login remains tied to generation.

Future hosted alternative: tap Generate → sign in if needed → explicit hosted-processing consent → check quota and reserve cost → enqueue → show real stages → return preview → release/commit credits according to confirmed outcome. Hosted allowances and billing are not part of the initial local-only release.

Preserve the current draft during login with a popup or inline authentication flow. A full-page OAuth redirect would destroy the current in-memory photo selection. Keep photos out of auth redirects, URLs and browser token storage. Login is not consent to cloud photo processing. Subsequent generation uses the authenticated session; do not require login each time.

Pre-login analysis must stay local/browser-side, or use an explicitly bounded inexpensive service. Moving the current Python analysis endpoint online without limits creates an anonymous compute cost even if Generate requires login. Product import also needs anonymous throttling and safe outbound fetch rules.

## Additional release work and future hosted mode

The desktop web release gates above are the execution order for the first release. The broader checklist below includes future hosted concerns; hosted photo storage, quotas and provider integration are deferred until explicitly selected.

1. **Define the beta:** local desktop devices to support, optionally 50 hosted seats, supported clothing categories, target countries, budget ledger and retention policy. Keep size/physical-fit claims unknown. Retain upload as the reliable path while retailer import is best effort.
2. **Authentication and ownership:** real Google/email authentication at first generation; secure sessions; every job, look, download and deletion authorized to its owner; admin access separated. Keep secrets server-side. Implement persistent, atomic quota/cost reservations with idempotency and one active job per account.
3. **Local release path:** reproducible pinned dependencies/models, licence notices, installer or documented beta setup, secure allowed-origin/token bridge, localhost browser permission/CORS compatibility, hardware/OS tests, startup/readiness checks and clear out-of-memory/offline recovery. No direct public exposure of the development Python service.
4. **Hosted release path, only if selected:** private upload/result objects and short-lived signed URLs, durable jobs surviving restarts, provider request IDs, duplicate-submission prevention, bounded retries, cancellation semantics and separate user-credit versus actual-provider-cost accounting. Do not hold a long serverless request open for GPU inference.
5. **Privacy and content controls:** strip EXIF; validate byte size, decoded dimensions and actual formats server-side; clear consent/processor disclosure; expiry and verified deletion of originals/results/queued jobs; no photo logging/training without explicit permission; adult consenting-photo beta; moderation and reporting; privacy/terms/contact pages and applicable market review.
6. **Quality and reliability:** evaluate 50–100 varied person/garment pairs across the supported categories; inspect identity, body shape, colour, pattern, logo, hands and dresses. Measure cost per acceptable result, failure rate and latency distributions, including cold starts. Test simultaneous jobs, refresh, auth-popup failure, provider timeout, budget exhaustion, retries, deletion and recovery. Keep AI labels and original comparison.
7. **Operations:** production builds/container images, HTTPS, dependency updates, secure configuration, metadata database backups/restore testing, redacted monitoring, admin daily/monthly spend view, worker concurrency caps and an emergency stop. Reconcile provider billing with the ledger; do not retain deleted photo data in backups.
8. **Roll out:** internal test → invite-only local beta → optional tightly capped hosted beta → assess actual usage/quality/revenue → gradually broaden access. Add ads after approval; increase allowances only when realized revenue or a sponsor funds the increase. Hosting availability is not the same as production readiness.

## Hosting and optimization choices

Cloudflare Workers Paid starts at $5/month and supports Next.js via OpenNext. The existing native Node HTTPS/DNS product importer needs compatibility testing/adaptation; Python/PyTorch inference remains a separate local companion or hosted service. [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/), [Next.js support](https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/).

Supabase Free can be a small beta auth/metadata database; it has no included automatic backups or uptime SLA and can pause after inactivity. Do not mistake it for an operationally managed production database. R2 has a standard-storage free allowance that may cover short-lived beta images, but use private access and account for operations/retention/limits. [Supabase pricing](https://supabase.com/pricing), [R2 pricing](https://developers.cloudflare.com/r2/pricing/). Vercel Hobby is restricted to personal non-commercial use, so do not assume it is suitable for an ad-funded launch. [Vercel Hobby](https://vercel.com/docs/plans/hobby).

Later, benchmark the existing open model on a scale-to-zero GPU against the hosted API on identical evaluation cases. Compare total billed time, cold starts, idle intervals, storage and engineering effort—not just inference seconds. Runpod bills startup, execution and idle time; flex workers can scale to zero. [Serverless billing](https://docs.runpod.io/serverless/pricing). Example only: at the listed 4090 rate of $1.10/hour, 30 billed seconds would cost about $0.0092 in compute, while 120 seconds would cost about $0.0367, before storage/other costs. [GPU rates](https://www.runpod.io/product/serverless). Neither duration is a measured yourFittingRoom GPU result. Do not extrapolate the Mac timing to a rented GPU or promise this lower cost without a benchmark.

Cache unchanged outfit results only within the same user's retention scope; re-viewing, downloading, favouriting and comparing an existing output should not regenerate it. Hash identity must include that user's input images, confirmed category, model version and generation settings. Never share personalized results across users. If cost recovery becomes necessary, a small retailer-funded pilot or disclosed affiliate arrangement can be evaluated; neither revenue source is guaranteed or currently connected.

## Security implementation — 12 October 2026

Prepared an owner-private desktop beta on the provided hosting subdomain, with no domain purchase, paid AI service, cloud photo storage, ads or custom password database. Managed hosting sign-in authorizes generation with short-lived signed permissions bound to each paired local engine. Personal images travel directly from the browser to its own loopback companion; hosted photo proxies are disabled. Pairing credentials stay in tab memory, and jobs enforce session ownership, rate/concurrency limits and expiry. The production build includes browser security headers and hashed script CSP. Companion weights are pinned and verified.

Current launch remains a controlled beta requiring companion installation. The hosted beta uses clothing-image upload; URL import is disabled there. A private audience gate can require sign-in before entry, even though app generation is the authentication trigger in the eventual publicly browsable experience. Keep the audience private until clean installation, managed authentication and browser local-network support are verified with friends. Do not claim completely secure systems or browser-only generation. See SECURITY.md for implemented protections and remaining public-release gates.

Owner-private deployment is live at https://wearview-desktop-beta.kumar-ankush0796.chatgpt.site. No external testers have been granted access. The published boundary checks passed; browser profile-sharing consent is pending. Invite friends only after the clean-install/browser compatibility gates.

## Account usage and mutual isolation requirement — 13 October 2026

Try-on must not consume the owner's ChatGPT allowance or OpenAI API credits. The current app uses identity-only managed ChatGPT sign-in and local FASHN inference; it has no OpenAI inference API integration or shared owner AI credential. Authentication/session/pairing tokens are access credentials, not paid AI-generation credits. Any future paid API integration needs separate explicit approval and a spending cap.

Visitors authenticate with their own accounts. Owner deployment/service credentials and the site signing private key must stay out of browser bundles and companion downloads. The hosted site must not forward photo jobs to the owner's computer. A visitor's 127.0.0.1 refers to that visitor's computer, not the developer's.

The companion API may process only explicitly selected images and manage the originating session's jobs. It must not expose file browsing, arbitrary paths/URLs, shell execution, remote desktop, LAN access or a remote-administration tunnel. Current hosted photo routes are disabled; pairing credentials remain in tab memory, and there is no owner-facing user-photo viewer.

This is application-level isolation, not an operating-system sandbox. The installed Python companion runs with the user's OS permissions, and website code necessarily sees the selected images in that user's browser. Before public release, provide a reviewed, signed, sandboxed companion with least-privilege filesystem/network access and a secure update process. Do not promise that installing native code gives it zero device access or that an owner-controlled website can never be modified to collect data.

Official distinction: identity scopes and ChatGPT plan usage are separate permissions: https://developers.openai.com/siwc/quickstart
