# Jyotish — Editing guide

## Review and edit
- Main site UI, content, styles, form markup and browser logic: `index.html`.
- Astrology calculations and API endpoints: `backend/main.py`.
- Dependencies: `backend/requirements.txt`.
- Render deployment blueprint: `render.yaml`.

## Deployment
1. Upload this project to a GitHub repository (keep it editable).
2. In Render, choose **New > Blueprint**, connect the repository and select `render.yaml`.
3. Render will build and launch the web service. The FastAPI service serves `index.html` at `/` and API endpoints under `/api/v1`.
4. Keep the repository as your source of truth. Edit `index.html` or `backend/main.py`, commit changes and Render redeploys.

## Accuracy status
This is an editable preview/development release. Panchang is currently a noon snapshot (not sunrise-based), matching is preliminary/simplified, divisional chart mappings require validation, and interpretation/AI features are not fully integrated. Review calculations with a qualified Jyotish practitioner before public use.

## Privacy/security before public launch
Do not add stored birth profiles or AI chat without privacy controls, consent, deletion and security review. The public Nominatim geocoder has usage limits and requires a production-compliant provider/cache for significant traffic. Review Swiss Ephemeris licensing for your deployment context.
