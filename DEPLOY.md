# Hosting on GitHub Pages

All files live in the `transplant-site` folder. They use **relative paths**, so they work from any repo/subfolder — no editing needed.

## One-time setup

1. Create a new repository on GitHub (e.g. `transplant-ref`). Public is simplest; private also works with Pages.
2. Upload the **contents** of the `transplant-site` folder to the repo root (drag the files into GitHub's "Add file → Upload files", or push via git). The repo root should contain `index.html`, not a nested folder.
3. In the repo: **Settings → Pages → Build and deployment → Source = "Deploy from a branch"**, Branch = `main`, folder = `/ (root)`. Save.
4. Wait ~1 minute. Your link appears at the top of the Pages settings:
   `https://<your-username>.github.io/transplant-ref/`

## Save to home screen

- **iPhone/iPad (Safari):** open the link → Share → **Add to Home Screen**. It launches full-screen (no browser bar) and works offline after the first load.
- **Android (Chrome):** open the link → menu → **Add to Home screen / Install app**.

## Files

| File | Purpose |
|---|---|
| `index.html` | Landing page / menu (set this as the home-screen link) |
| `guide.html` | Resident Guide |
| `protocols.html` | Inpatient Postop Protocols |
| `manifest.webmanifest` | App name, icon, standalone mode |
| `sw.js` | Service worker — offline caching |
| `icon-192.png`, `icon-512.png` | Home-screen icon |

## Updating content later

Re-upload the changed HTML file. Because the service worker caches, bump the version in `sw.js` (change `tx-ref-v1` to `tx-ref-v2`) whenever you update content, so devices fetch the new version.
