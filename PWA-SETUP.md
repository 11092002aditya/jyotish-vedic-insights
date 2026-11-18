# Jyotish V2 — PWA foundation

This iteration adds the installable Progressive Web App foundation:
- Web app manifest and Jyotish app icon
- Service worker with app-shell caching for repeat visits
- FastAPI routes for the manifest, service worker and icon
- Single-root Render deployment configuration

## Deploy
1. Push the entire project folder to a GitHub repository (keep `index.html`, `backend/`, `render.yaml`, `manifest.webmanifest`, `service-worker.js`, and `icon.svg` at repository root).
2. In Render choose **New > Blueprint**, connect the repository and deploy `render.yaml`.
3. Open the HTTPS Render URL in Chrome on Android. Use Chrome menu > **Install app** or **Add to Home screen**.

## Limitations
The service worker caches the app shell, not live calculation responses. Kundli, Panchang and matching still require the online backend. AI Jyotishi, accounts, saved charts, privacy workflows and validated production-grade calculations are not implemented in this PWA foundation. The existing calculations remain a development prototype and require specialist validation before public reliance.
