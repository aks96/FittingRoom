# Preparing the download website for Netlify

These instructions do not authorize deployment. All project build/check/preview commands below run locally. No script creates a Netlify project, pushes Git, publishes a site, opens a tunnel or starts the AI companion.

## What will be hosted

`netlify-dist/` contains the static landing/setup website, four supplied sample photography assets, Mac and Windows development source downloads, `checksums.txt`, `robots.txt` and generated security headers. It does not contain a server, functions, developer fitting room, photo APIs, personal photos/results, Python environments, AI model weights, browser AI runtime or the previous Sites hosting configuration. The companion downloads intentionally contain our implementation source and the fixed local photo UI.

Each user's separately started companion serves the photo workspace at **http://127.0.0.1:8765** on that user's computer. The website only links to it in a new tab; it does not fetch photos, pair, start/install software or accept pairing codes. HTTPS on the website does not make this loopback address a remote server. Keep the companion bound to loopback, with no port forwarding or tunnels.

## Build and verify locally

Use Node.js 22+ and `npm ci`. On this Mac, the existing project Node runtime can be used with `export PATH="$PWD/.runtime/bin:$PATH"`. Rebuilding archives currently also needs the project's existing Python 3.12 environment at `.runtime/ai-venv`; a fresh web build does not need that environment.

If companion source/UI has changed, first stop any running companion, then rebuild both downloads:

```sh
npm run build:companion-ui
npm run companion:package
```

This packages only explicitly allowlisted files and updates `security/companion-downloads.json`. It does not install or run the AI. Keep the changed archives and metadata together in Git. Old copies on testers' devices remain old until they explicitly download/extract a new version. Do not copy a developer `.runtime` folder to another device.

Build the website **after** packaging so its displayed sizes/checksums match:

```sh
npm test
npm run typecheck
npm run build:netlify
npm run check:netlify
```

For the companion regression/archive checks on this development Mac:

```sh
.runtime/ai-venv/bin/python -m unittest discover -s tests -p '*_test.py'
```

`build:netlify` uses a clean staging directory under `.runtime`, exports only the landing route, verifies the archives against their metadata, rejects unexpected output files, and generates CSP hashes for the exact exported inline scripts. A local inventory is retained at `.runtime/netlify-build-report.json`. The output is ignored by Git. Never use the old `build:site`/Sites-worker `dist` as the Netlify output.

Preview the built files and their generated headers:

```sh
npm run preview:netlify
```

Open **http://127.0.0.1:3002**. Switch Mac/Windows, read the setup guide, test the archive downloads and compare SHA-256 values. The local preview server refuses unavailable API/developer routes and POSTs. Ctrl+C stops it. Port 3002 is only a development preview; users will visit the main website after you deploy it yourself.

## Manual Netlify deployment — only when you choose

The simplest first beta is a manual upload of the **built `netlify-dist` folder** through Netlify's dashboard. Do not upload the project root, `public`, `.runtime`, `.next` or the old Sites `dist`. Manual uploads do not run the build for you. Do not enable HTML/script post-processing or add injected scripts without rebuilding/retesting the CSP.

If you later choose a Git-connected Netlify project, `netlify.toml` specifies:

- Build command: `npm run build:netlify`.
- Publish directory: `netlify-dist`.
- Node: 22; Next.js adapter skipped for this static export.
- No API keys, AI credentials, paid services, Netlify functions or user accounts are required for the landing website.

Connecting a Git repository can enable automatic deploys on pushes. Review/pause that configuration before further source pushes if you want manual deployment only. Adding this configuration file locally does not connect or deploy anything. Netlify build behaviour and credit limits must be checked in your own account.

After your manual deployment, verify HTTPS, both archive hashes, Windows/Mac switching, the generated response headers, and 404s for `/api/ai/tryon`, `/development/fitting-room` and `/.env`. Test that the local-open button opens only the tester's running companion. Actual Netlify header/adapter behaviour cannot be certified by local tests.

## Beta and public-release limits

Both downloads are unsigned development **source archives**, not portable signed installers. Python 3.12 is still a separate prerequisite. Mac generation was exercised on M5/16 GB; clean-device installation and other Macs remain unverified. The refreshed Windows ZIP includes `Set up.cmd`, `Test Windows.cmd`, `Start AI.cmd`, the AppContainer candidate and NVIDIA/AMD/Intel/explicit CPU profiles, but no real Windows execution has been performed here. Use [WINDOWS_TESTING.md](WINDOWS_TESTING.md) for the first hardware test. Never bypass OS protections or use administrator rights to force setup.

Do not advertise broad Windows compatibility, real-time generation, precise physical fit or a security certification. Signed/notarized installers, broker isolation, dependency/AMD-exception review, signed updates, uninstall controls, independent review, licences and clean-machine tests remain public-release gates in [SECURITY_RELEASE_PLAN.md](SECURITY_RELEASE_PLAN.md). `robots.txt`/`noindex` only discourage indexing; they do not provide access control for a friends-only site.

Official references: [Netlify manual deployments](https://docs.netlify.com/deploy/create-deploys/), [custom headers](https://docs.netlify.com/manage/routing/headers/), [Next.js static exports](https://nextjs.org/docs/app/guides/static-exports), [Netlify static export configuration](https://www.netlify.com/knowledge-base/how-to-deploy-nextjs-astro-nuxt-or-sveltekit-to-netlify/).
