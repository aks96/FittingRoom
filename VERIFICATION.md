# Offline AI verification — 12 October 2026

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

## Remaining limits

Still-photo inference is not live-video or instant try-on. Exact physical fit, clothing-size prediction and guaranteed preservation of colour/print/identity are unsupported. Product import cannot bypass retailer restrictions. User-side downloads persist until separately removed. Automatic 30-minute server-result expiry is implemented but was not wall-clock tested for 30 minutes; immediate cancellation/purge and missing-job handling were tested. Authentication and persistent storage are intentionally absent. No deployment was performed.

## Secured private beta — 12 October 2026

- TypeScript check and production UI export passed.
- Eight existing service tests, five hosted worker security tests and two companion security tests passed.
- Secured live companion smoke checks passed: real black T-shirt recognition, invalid image and origin rejection, Men scope, separate-session read/delete denial, missing hosted generation permit rejection, cancellation/purge and blank-person rejection.
- All installed main/pose/parser model checksums match pinned official artifacts.
- npm audit reports zero vulnerabilities. Python audit reports no known vulnerabilities after upgrading cryptography and pip; the source-installed FASHN package is not scanned by that tool.
- Updated home/setup layout checked at 390, 820 and 1440 px: no horizontal overflow. Mobile generation remains unsupported.
- Clean companion installation on another computer and invited-user browser authentication/local-network permission remain release gates.
