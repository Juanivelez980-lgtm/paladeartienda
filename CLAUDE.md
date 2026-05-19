# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Local development

No build step. Serve locally with:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/paladeartienda/
```

The Service Worker requires HTTPS or localhost to register; `python3 -m http.server` is sufficient.

## Deployment

Push to `main` — GitHub Pages publishes automatically. The live URL is `https://paladear.github.io/paladeartienda/`.

## Architecture

This is a **single-file PWA** — all HTML, CSS, and JavaScript live in `index.html` (≈675 KB). There is no framework, no bundler, and no `package.json`.

### Product data pipeline

Product data comes from a private Google Sheets spreadsheet, exported as four CSV files committed to the repo:

| File | Contents |
|---|---|
| `precios-min.csv` | Retail prices |
| `info-min.csv` | Retail product info, images, descriptions |
| `precios-may.csv` | Wholesale prices |
| `info-may.csv` | Wholesale product info |

The GitHub Actions workflow (`.github/workflows/update-products.yml`) downloads fresh CSVs directly from the Google Sheets publish URL and commits them Mon–Sat every 2 hours during Argentine business hours. To update data manually: trigger the workflow from GitHub → Actions → "Actualizar snapshot de productos" → Run workflow.

### Two-mode store

The app has two distinct modes toggled via `?seccion=minorista` or `?seccion=mayorista` in the URL (also via PWA shortcuts). Each mode has its own cart, pricing display, and checkout flow.

### Service Worker (`sw.js`)

Uses a **network-first** strategy for all GET requests. Caches opaque responses (type `'opaque'`, status `0`) because product images loaded via Google Drive cross-origin scripts produce opaque responses. Cache version is hardcoded as `paladear-v3` — bump this string when you need to force cache invalidation for all users.

### Checkout

Cart is assembled client-side and checkout generates a pre-filled **WhatsApp message** sent to the store's phone numbers (retail: `+5492616512823`, wholesale: `+5492615983065`). There is no backend.

### CSS design tokens

All colors are CSS custom properties on `:root`:

```css
--azul: #547692      /* primary brand blue */
--azul-dark: #3d5a72
--azul-light: #cfdce8
--destructive: #e8633a
--whatsapp: #25d366
```
