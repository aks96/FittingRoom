# WearView — design and prototype handoff

[Figma design file](https://www.figma.com/design/ssDEjgqWspzCQYi2mQPz4T)

The Figma file contains a compact design system, 16 desktop journey screens, 16 mobile journey screens, and 49 additional states at each size. The Figma Starter tool allowance was exhausted before prototype connections, tablet screens, layout cleanup, and final validation could be applied. These screens are currently unconnected; some tall frames overlap adjacent canvas rows. They must not be represented as a finished Figma prototype.

Open **WearView-prototype.html** in a browser for the separately completed responsive clickable prototype. It is a self-contained file with embedded sample photography and needs no installation or backend.

## Review journeys

1. Enter `https://studio-loom.example/products/linen-plum` → Find garment → Continue sample → select the garment and colour → confirm → add sample person → fitting room → Try it on → continue through queued, preparing and generating stages → preview → compare → save both → saved collection → original product details.
2. Enter a different valid domain → failed import → upload clothing image → use sample clothing image → Continue sample → confirm garment → continue with the same photo and preview journey.

The prototype state explorer in the footer is a review aid outside the intended shopper flow. It includes invalid URL, unsupported store, restricted page, missing garment image, unsupported image, poor photo quality, incorrect garment selection, unsupported category, generation failure, exhausted allowance, expired guest session, deletion confirmations and completion, failed download, camera fallback, and empty collection states.

## Design system

- Warm ivory `#F8F6F2`, charcoal `#29262A`, muted text `#666168`, plum `#68435C`, tint `#EEE4EB`, border `#DED8DC`.
- Figma typography: Playfair Display for editorial headings; Manrope for interface labels and body text. The portable prototype uses local Georgia and system sans-serif fallbacks so it remains self-contained.
- Figma: 26 scoped variables, seven text styles, five button variants and three reusable sample photo components. Buttons have 52px touch targets. Focus uses a visible plum outline.
- Cards use subtle borders and 12–16px radii. Spacing follows a 4px base scale.

## Responsive behavior

- Desktop above 1000px: input controls on the left; large preview on the right. Home uses a two-column editorial composition. Compare cards sit side by side.
- Tablet 601–1000px: primary page columns stack; fitting-room input cards can share a row; full preview sits below. Comparison retains two columns.
- Mobile up to 600px: preview appears before fitting-room controls; fixed bottom Try it on action remains visible. Compare cards snap horizontally with Previous / Next buttons, a position indicator, and a full vertical comparison alternative.
- Keep page content within the viewport; long product URLs wrap. No horizontal page overflow is intended. Comparison alone has intentional horizontal scrolling.

## Interaction and accessibility notes

- Product-link submission works with the button or Enter. URL validity and supported-domain handling have explicit fallback states. Variant and colour selection are user-controlled.
- Generation is a manual sample walkthrough, not live processing. Stages avoid fabricated percentages and completion times. Leaving the job screen preserves the sample job; cancellation has an explicit confirmation.
- Try it on is disabled until a photo is available and when allowance is exhausted. Missing inputs explain how to proceed.
- Upload controls open a native file picker and validate type / size; files are not uploaded. Valid files continue using clearly identified sample photography.
- Crop and rotate operate on the sample viewport. Buttons provide alternatives to gestures. Before / after uses separate accessible images and toggles rather than requiring a slider.
- Semantic controls, readable labels, visible keyboard focus, live status announcements, heading focus after navigation and reduced-motion styles are included. Production dialogs should trap focus, support Escape and restore focus to their trigger.
- Save/favourite/filter/delete actions operate on temporary in-memory sample state. Reloading clears the session. Sample sign-in creates no real account. Destructive actions require a second confirmation.
- Download exports a labelled sample image. Import, camera, AI generation, retailer handoff, sign-in and reporting are simulated. No official retailer partnership is implied.

## Privacy and production decisions

The UI does not claim photos remain on-device in production. Explain upload, processing provider and retention before consent. Set concrete production retention periods before release. Individual photo deletion does not imply deletion of generated looks; delete-all covers photos, generated looks and profile data. Confirm completion only after the real service reports success.

The initial category scope is tops and shirts. Previews explore style, do not determine clothing size, and contain no fit accuracy predictions. Price and availability remain unknown and are checked at the retailer.

## Photography

The included triptych was created with the built-in image generation tool. Prompt: one photographic triptych showing the same adult Indian woman in the same frontal pose and ivory studio, first in a cream T-shirt, then a plum linen shirt, then a sage linen shirt; charcoal trousers, soft daylight, realistic editorial photography, no text, logos or UI. These are illustrative sample assets, not results from a connected try-on service.

## Validation

Verified the main sample journey and the failed-import clothing-image fallback through the browser. Confirmed the Sage product details retain `/products/linen-sage`. Reviewed the desktop Figma home screenshot and the mobile and tablet web fitting room. Figma-wide font readback, canvas cleanup, tablet composition and connection verification remain pending because of the account tool limit.
