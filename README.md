# Jyotish — Vedic Astrology

Responsive English/Hindi frontend and FastAPI calculation backend.

## User-entered location
Visitors enter City, State/Region and Country. The backend resolves latitude, longitude and IANA timezone automatically through `/api/v1/geocode`; users do not need to know coordinates.

The starter uses OpenStreetMap Nominatim through geopy and timezonefinder. Nominatim is rate-limited and subject to its usage policy. For a public production launch, use a provider/service whose terms fit expected traffic, cache results and display the resolved address for confirmation.

## Frontend
Open `index.html` in a browser. For live calculations, run the backend and set:
```js
localStorage.setItem('jyotish_api_url', 'http://127.0.0.1:8000')
```
Reload the page. Prefer a local static server (`python -m http.server 5500`) and open http://localhost:5500.

## Backend
See `backend/README.md`; install `backend/requirements.txt` and run:
`uvicorn main:app --reload`

## Important calculation caveats
- Lahiri sidereal calculations use Swiss Ephemeris. Licensing must be reviewed before public deployment.
- Panchang currently returns a local-noon snapshot of Vara, Tithi, Nakshatra, Yoga and Karana. It does not yet calculate sunrise/sunset or exact limb transition times; it must not be used as a Muhurta authority.
- Horoscope matching is a preliminary 36-point Ashtakoota estimate. Some traditional scoring matrices and exceptions are simplified; Manglik analysis, seventh-house/Navamsa synthesis and expert validation are outstanding.
- Divisional chart mapping and dasha calculations require specialist validation against trusted reference datasets before production.
- AI astrologer, secure accounts, database, complete privacy workflows, monitoring and public hosting are not connected yet.


## Single-origin deployment
This version serves the frontend from FastAPI at `/`, so browser requests use the same origin. Deploy via the included `render.yaml` Blueprint. See `EDITING-GUIDE.md`.


### Hosting architecture (single service)
The FastAPI backend serves the frontend at `/`, and calculation endpoints under `/api/v1/`, so deploy the repository as one Render web service. The frontend automatically uses the same-origin API when hosted.
