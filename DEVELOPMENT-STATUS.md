# Development status — 18 Nov 2026

Chosen standard: Traditional Vedic, sidereal zodiac, Lahiri (Chitrapaksha) ayanamsha.
Default house convention in engine: whole-sign houses.
Node convention: mean Rahu, Ketu exactly opposite.

Delivered in this iteration:
- FastAPI backend foundation.
- Swiss Ephemeris sidereal calculation endpoint.
- Planet longitudes, signs, nakshatras, padas, retrograde flags and whole-sign houses.
- Initial divisional-chart sign mappings.
- Initial Vimshottari birth balance calculation.
- API documentation via FastAPI `/docs`.

Still required before production:
- Birthplace geocoding + timezone lookup UI and backend integration.
- Validate calculation conventions and divisional chart mappings with a Jyotish expert and reference test charts.
- Calculate full dated Mahadasha/Antardasha/Pratyantardasha periods and transit/Sade Saati timelines.
- Connect frontend form to backend endpoint.
- AI service with secure server-side API key and grounded chart context.
- User accounts, secure storage/consent/deletion, abuse protection, monitoring and deployment.
