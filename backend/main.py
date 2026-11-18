from __future__ import annotations
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional
import os
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import swisseph as swe

APP_NAME = "Jyotish Vedic Astrology API"
# Lahiri / Chitrapaksha sidereal zodiac
swe.set_sid_mode(swe.SIDM_LAHIRI)

app = FastAPI(title=APP_NAME, version="0.2.0")
allowed = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware, allow_origins=allowed, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)
SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIGNS_HI = ["मेष","वृषभ","मिथुन","कर्क","सिंह","कन्या","तुला","वृश्चिक","धनु","मकर","कुंभ","मीन"]
NAKSHATRAS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
NAK_LORDS = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"] * 3
DASHA_YEARS = {"Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,"Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17}
DASHA_ORDER = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
PLANETS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE
}
DIVISION_NAMES = {1:"D1 Rashi",2:"D2 Hora",3:"D3 Drekkana",4:"D4 Chaturthamsha",7:"D7 Saptamsha",9:"D9 Navamsha",10:"D10 Dashamsha",12:"D12 Dwadashamsha",16:"D16 Shodashamsha",20:"D20 Vimshamsha",24:"D24 Chaturvimshamsha",27:"D27 Bhamsa",30:"D30 Trimshamsha",40:"D40 Khavedamsha",45:"D45 Akshavedamsha",60:"D60 Shashtiamsha"}

class LocationRequest(BaseModel):
    city: str = Field(min_length=1, max_length=120)
    state: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=1, max_length=120)

_geocoder = Nominatim(user_agent="jyotish-vedic-insights/1.0 (location lookup)")
_tzf = TimezoneFinder()
_last_geocode = 0.0

@app.post("/api/v1/geocode")
def geocode(req: LocationRequest):
    """Resolve a user-entered city/state/country into coordinates and IANA timezone."""
    global _last_geocode
    query = f"{req.city}, {req.state}, {req.country}"
    try:
        # Respect public Nominatim's one-request-per-second usage policy.
        wait = 1.05 - (time.monotonic() - _last_geocode)
        if wait > 0:
            time.sleep(wait)
        result = _geocoder.geocode(query, exactly_one=True, addressdetails=True, timeout=12)
        _last_geocode = time.monotonic()
        if result is None:
            raise HTTPException(404, "Location not found. Please check the city, state and country.")
        tz = _tzf.timezone_at(lat=result.latitude, lng=result.longitude)
        if not tz:
            raise HTTPException(422, "Could not determine the timezone for this location.")
        address = result.raw.get("display_name", query)
        return {"query":query,"resolved_address":address,"latitude":result.latitude,
                "longitude":result.longitude,"timezone":tz,
                "provider":"OpenStreetMap Nominatim",
                "note":"Coordinates and timezone were resolved from the selected place. Check the resolved address before calculating."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Location lookup failed: {str(e)}")

class BirthRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    birth_date: str = Field(description="YYYY-MM-DD")
    birth_time: str = Field(description="HH:MM, local civil time")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = Field(description="IANA timezone, e.g. Asia/Kolkata")
    ayanamsha: str = "Lahiri"

    @field_validator("ayanamsha")
    @classmethod
    def only_lahiri(cls, v):
        if v.lower() not in ("lahiri", "chitrapaksha"):
            raise ValueError("This engine currently supports Lahiri (Chitrapaksha) only.")
        return "Lahiri"

def parse_birth(req: BirthRequest):
    try:
        local = datetime.fromisoformat(f"{req.birth_date}T{req.birth_time}").replace(tzinfo=ZoneInfo(req.timezone))
    except Exception as e:
        raise HTTPException(422, f"Invalid date, time or IANA timezone: {e}")
    return local.astimezone(timezone.utc)

def norm(x): return x % 360.0

def sign_data(lon):
    idx = int(norm(lon)//30)
    deg = norm(lon)%30
    return {"sign_index":idx, "sign":SIGNS[idx], "sign_hi":SIGNS_HI[idx],
            "degree_in_sign":round(deg,6)}

def nak_data(lon):
    span=360/27
    idx=int(norm(lon)//span)
    within=norm(lon)-idx*span
    pada=int(within/(span/4))+1
    return {"nakshatra":NAKSHATRAS[idx],"nakshatra_index":idx,"pada":min(pada,4),
            "nakshatra_lord":NAK_LORDS[idx],"longitude_in_nakshatra":round(within,6)}

def divisional_sign(lon, n):
    # Parashara-style sign mapping for common vargas; D30 uses unequal sign-specific segments.
    s=int(norm(lon)//30); d=norm(lon)%30
    if n==1: return s
    if n==2: return (3 if s%2==0 else 4) + (0 if d<15 else 1) # Cancer/Leo for odd signs, Leo/Cancer for even signs
    if n==3: return (s + int(d//10)*4) % 12
    if n==4: return (s + int(d//7.5)*3) % 12
    if n==7: return (s + (int(d/(30/7)) if s%2==0 else 6+int(d/(30/7)))) % 12
    if n==9: return (s*9 + int(d/(30/9))) % 12
    if n==10: return (s*10 + int(d/3)) % 12
    if n==12: return (s*12 + int(d/2.5)) % 12
    if n==16: return ((0 if s%3==0 else 4 if s%3==1 else 8) + int(d/(30/16))) % 12
    if n==20: return ((0 if s%3==0 else 8 if s%3==1 else 4) + int(d/1.5)) % 12
    if n==24: return ((4 if s%2==0 else 3) + int(d/1.25)) % 12
    if n==27: return ((0 if s%4==0 else 3 if s%4==1 else 6 if s%4==2 else 9) + int(d/(30/27))) % 12
    if n==30:
        # Classical unequal Trimshamsha divisions, mapped to signs by gender of natal sign.
        odd = (s%2==0)
        segments = [(0,5,0),(5,10,10),(10,18,8),(18,25,2),(25,30,6)] if odd else [(0,5,1),(5,12,5),(12,20,11),(20,25,9),(25,30,7)]
        for lo,hi,sg in segments:
            if lo <= d < hi: return sg
    if n==40: return ((0 if s%2==0 else 6) + int(d/.75))%12
    if n==45: return ((0 if s%3==0 else 4 if s%3==1 else 8) + int(d/(30/45)))%12
    if n==60: return (s*60 + int(d/.5))%12
    return None

def calc(req: BirthRequest):
    utc = parse_birth(req)
    jd = swe.julday(utc.year, utc.month, utc.day,
                    utc.hour + utc.minute/60 + utc.second/3600)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    houses, ascmc = swe.houses_ex(jd, req.latitude, req.longitude, b'P', swe.FLG_SIDEREAL)
    asc = norm(ascmc[0])
    planets={}
    raw_lons={}
    for name,pid in PLANETS.items():
        xx, ret = swe.calc_ut(jd, pid, flags)
        lon=norm(xx[0])
        raw_lons[name]=lon
        planets[name]={"longitude":round(lon,6), **sign_data(lon), **nak_data(lon),
                       "retrograde": bool(xx[3] < 0)}
    # Ketu is opposite the selected mean Rahu node.
    ketu=norm(raw_lons["Rahu"]+180)
    raw_lons["Ketu"]=ketu
    planets["Ketu"]={"longitude":round(ketu,6), **sign_data(ketu), **nak_data(ketu), "retrograde":True}
    # Whole-sign houses from Lagna sign.
    for p in planets.values():
        p["house"]=(p["sign_index"]-int(asc//30))%12+1
    chart={"lagna":{"longitude":round(asc,6),**sign_data(asc),**nak_data(asc)},
           "planets":planets,
           "house_system":"Whole-sign houses from sidereal Lagna",
           "ayanamsha":"Lahiri (Chitrapaksha)"}
    divisions={}
    for n,label in DIVISION_NAMES.items():
        divisions[str(n)]={"name":label,"lagna_sign":SIGNS[divisional_sign(asc,n)],
                           "planet_signs":{k:SIGNS[divisional_sign(v,n)] for k,v in raw_lons.items()}}
    dasha=vimshottari(raw_lons["Moon"])
    return {"profile":{"name":req.name,"birth_date":req.birth_date,"birth_time":req.birth_time,
                       "timezone":req.timezone,"latitude":req.latitude,"longitude":req.longitude},
            "calculation":{"zodiac":"Sidereal","ayanamsha":"Lahiri (Chitrapaksha)",
                           "ephemeris":"Swiss Ephemeris","node":"Mean Rahu; Ketu opposite",
                           "house_system":"Whole-sign houses"},
            "rashi_chart":chart,"divisional_charts":divisions,"vimshottari_dasha":dasha}

def vimshottari(moon_lon):
    nd=nak_data(moon_lon)
    idx=nd["nakshatra_index"]
    lord=NAK_LORDS[idx]
    span=360/27
    elapsed=(norm(moon_lon)%span)/span
    balance=DASHA_YEARS[lord]*(1-elapsed)
    start_idx=DASHA_ORDER.index(lord)
    sequence=[DASHA_ORDER[(start_idx+i)%9] for i in range(9)]
    return {"birth_nakshatra":nd["nakshatra"],"birth_nakshatra_pada":nd["pada"],
            "starting_mahadasha":lord,"balance_at_birth_years":round(balance,4),
            "sequence_years":[{"lord":p,"years":DASHA_YEARS[p]} for p in sequence],
            "note":"Balance is an approximate tropical-year fraction of the birth nakshatra remaining; calendar period dates are not yet emitted."}

@app.get("/", include_in_schema=False)
def website():
    # Serve the editable frontend and API from one origin in production.
    frontend = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")
    if os.path.isfile(frontend):
        return FileResponse(frontend)
    return {"service":APP_NAME,"status":"running","calculation_standard":"Sidereal Lahiri","docs":"/docs"}

@app.get("/manifest.webmanifest", include_in_schema=False)
def web_manifest():
    return FileResponse(os.path.join(os.path.dirname(os.path.dirname(__file__)), "manifest.webmanifest"), media_type="application/manifest+json")

@app.get("/service-worker.js", include_in_schema=False)
def service_worker():
    return FileResponse(os.path.join(os.path.dirname(os.path.dirname(__file__)), "service-worker.js"), media_type="application/javascript", headers={"Cache-Control":"no-cache"})

@app.get("/icon.svg", include_in_schema=False)
def app_icon():
    return FileResponse(os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.svg"), media_type="image/svg+xml")

@app.get("/api", include_in_schema=False)
def api_root():
    return {"service":APP_NAME,"status":"running","docs":"/docs"}

@app.get("/health")
def health(): return {"ok":True}

@app.post("/api/v1/kundli")
def kundli(req: BirthRequest):
    try: return calc(req)
    except HTTPException: raise
    except Exception as e: raise HTTPException(500, f"Chart calculation failed: {str(e)}")


class PanchangRequest(BaseModel):
    date: str = Field(description="YYYY-MM-DD local date")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "Asia/Kolkata"

class MatchPerson(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    birth_date: str
    birth_time: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str

class MatchRequest(BaseModel):
    person_a: MatchPerson
    person_b: MatchPerson

TITHI_NAMES = ["Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami","Shashthi","Saptami","Ashtami","Navami","Dashami","Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima"]
TITHI_HI = ["प्रतिपदा","द्वितीया","तृतीया","चतुर्थी","पंचमी","षष्ठी","सप्तमी","अष्टमी","नवमी","दशमी","एकादशी","द्वादशी","त्रयोदशी","चतुर्दशी","पूर्णिमा"]
YOGA_NAMES = ["Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda","Sukarma","Dhriti","Shula","Ganda","Vriddhi","Dhruva","Vyaghata","Harshana","Vajra","Siddhi","Vyatipata","Variyana","Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla","Brahma","Indra","Vaidhriti"]
KARANA_NAMES = ["Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti","Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti","Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti","Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti","Shakuni","Chatushpada","Naga"]
WEEKDAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
NAK_YONI = ["Horse","Elephant","Sheep","Serpent","Serpent","Dog","Cat","Sheep","Cat","Rat","Rat","Cow","Buffalo","Tiger","Buffalo","Tiger","Deer","Deer","Dog","Monkey","Mongoose","Monkey","Lion","Horse","Lion","Cow","Elephant"]
NAK_GANA = ["Deva","Manushya","Rakshasa","Manushya","Deva","Manushya","Deva","Deva","Rakshasa","Rakshasa","Manushya","Manushya","Deva","Rakshasa","Deva","Rakshasa","Deva","Rakshasa","Rakshasa","Manushya","Manushya","Deva","Rakshasa","Rakshasa","Manushya","Manushya","Deva"]
NAK_NADI = ["Adi","Madhya","Antya"] * 9
SIGN_LORDS = ["Mars","Venus","Mercury","Moon","Sun","Mercury","Venus","Mars","Jupiter","Saturn","Saturn","Jupiter"]
VARNA_BY_SIGN = [3,1,2,0,3,1,2,0,3,1,2,0] # traditional four-class mapping used for scoring only

def local_noon_jd(date_str, tzname):
    try:
        local = datetime.fromisoformat(date_str+"T12:00").replace(tzinfo=ZoneInfo(tzname))
    except Exception as e:
        raise HTTPException(422, f"Invalid date or timezone: {e}")
    utc=local.astimezone(timezone.utc)
    return swe.julday(utc.year,utc.month,utc.day,utc.hour+utc.minute/60)

@app.post("/api/v1/panchang")
def panchang(req: PanchangRequest):
    jd=local_noon_jd(req.date,req.timezone)
    flags=swe.FLG_SWIEPH|swe.FLG_SIDEREAL
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    sun=swe.calc_ut(jd,swe.SUN,flags)[0][0]%360
    moon=swe.calc_ut(jd,swe.MOON,flags)[0][0]%360
    elong=(moon-sun)%360
    tithi_index=int(elong/12)
    paksha="Shukla" if tithi_index<15 else "Krishna"
    half_idx=tithi_index if tithi_index<15 else tithi_index-15
    tithi=TITHI_NAMES[half_idx] if half_idx<14 else "Purnima" if paksha=="Shukla" else "Amavasya"
    nak=nak_data(moon)
    yoga_idx=int(((sun+moon)%360)/(360/27))
    karana_index=int(elong/6)
    karana=KARANA_NAMES[min(karana_index, len(KARANA_NAMES)-1)]
    weekday=datetime.fromisoformat(req.date).weekday()
    return {
        "date":req.date,"timezone":req.timezone,"location":{"latitude":req.latitude,"longitude":req.longitude},
        "ayanamsha":"Lahiri (Chitrapaksha)","sun_longitude":round(sun,6),"moon_longitude":round(moon,6),
        "vara":WEEKDAYS[weekday],"tithi":{"name":tithi,"paksha":paksha,"index":tithi_index+1,"name_hi":TITHI_HI[half_idx] if half_idx<15 else "अमावस्या"},
        "nakshatra":nak,"yoga":YOGA_NAMES[yoga_idx],"karana":karana,
        "sunrise_sunset":{"status":"Not calculated in this starter endpoint; integrate and validate a location-aware horizon calculation before displaying times."},
        "note":"Panchang limbs are evaluated at local noon as a daily snapshot. Tithi, Nakshatra, Yoga and Karana start/end times are not yet calculated. Do not use this snapshot as a Muhurta or ritual timing authority."
    }

def tara_score(n1,n2):
    # Nav Tara cycle; 1,3,5,7,9 are traditionally favourable.
    count=((n2-n1)%27)+1
    tara=(count-1)%9+1
    return 3.0 if tara in (2,4,6,8) else 1.5

def ashtakoota(person_a, person_b):
    def moon_data(p):
        req=BirthRequest(name=p.name,birth_date=p.birth_date,birth_time=p.birth_time,
                         latitude=p.latitude,longitude=p.longitude,timezone=p.timezone,ayanamsha="Lahiri")
        result=calc(req)
        moon=result["rashi_chart"]["planets"]["Moon"]
        return moon["nakshatra_index"],moon["sign_index"],moon
    na,sa,ma=moon_data(person_a); nb,sb,mb=moon_data(person_b)
    # Classical maximum weights; rules below are a transparent first-pass scoring model.
    varna = 1.0 if VARNA_BY_SIGN[sa] >= VARNA_BY_SIGN[sb] else 0.0
    vashya = 1.0 if sa==sb or (sa%6)==(sb%6) else 0.5
    tara = tara_score(na,nb)
    yoni = 4.0 if NAK_YONI[na]==NAK_YONI[nb] else 2.0 if NAK_YONI[na] in ("Horse","Elephant","Cow","Buffalo","Deer","Sheep") and NAK_YONI[nb] in ("Horse","Elephant","Cow","Buffalo","Deer","Sheep") else 1.0
    gana = 6.0 if NAK_GANA[na]==NAK_GANA[nb] else 3.0 if "Manushya" in (NAK_GANA[na],NAK_GANA[nb]) else 0.0
    lord_a, lord_b = SIGN_LORDS[sa], SIGN_LORDS[sb]
    friends={"Sun":["Moon","Mars","Jupiter"],"Moon":["Sun","Mercury"],"Mars":["Sun","Moon","Jupiter"],"Mercury":["Sun","Venus"],"Jupiter":["Sun","Moon","Mars"],"Venus":["Mercury","Saturn"],"Saturn":["Mercury","Venus"]}
    if lord_a==lord_b: maitri=5.0
    elif lord_b in friends.get(lord_a,[]) and lord_a in friends.get(lord_b,[]): maitri=5.0
    elif lord_b in friends.get(lord_a,[]) or lord_a in friends.get(lord_b,[]): maitri=4.0
    else: maitri=1.0
    distance=(sb-sa)%12
    bhakoot=7.0 if distance not in (2,5,6,8,9,11) else 0.0
    nadi=8.0 if NAK_NADI[na]!=NAK_NADI[nb] else 0.0
    items=[
      {"name":"Varna","max":1,"score":varna,"basis":"Moon-sign traditional Varna category"},
      {"name":"Vashya","max":2,"score":round(vashya*2,1),"basis":"Simplified sign relationship; full Vashya group matrix pending"},
      {"name":"Tara","max":3,"score":tara,"basis":"Nav Tara cycle, directional check simplified"},
      {"name":"Yoni","max":4,"score":yoni,"basis":"Nakshatra animal category; enemy-pair matrix pending"},
      {"name":"Graha Maitri","max":5,"score":maitri,"basis":"Moon-sign lords and simplified natural friendship"},
      {"name":"Gana","max":6,"score":gana,"basis":"Nakshatra Gana"},
      {"name":"Bhakoot","max":7,"score":bhakoot,"basis":"Moon-sign distance rule"},
      {"name":"Nadi","max":8,"score":nadi,"basis":"Nakshatra Nadi"},
    ]
    total=round(sum(x["score"] for x in items),1)
    return {"total":total,"maximum":36,"kootas":items,
            "person_a":{"name":person_a.name,"moon_sign":ma["sign"],"nakshatra":ma["nakshatra"],"pada":ma["pada"]},
            "person_b":{"name":person_b.name,"moon_sign":mb["sign"],"nakshatra":mb["nakshatra"],"pada":mb["pada"]},
            "interpretation":"Preliminary educational estimate only. A production-grade match must apply the complete tradition-specific Vashya, Yoni enmity, Tara directionality, Nadi exceptions, Manglik analysis, seventh-house and Navamsa review.",
            "warning":"Do not treat this preliminary score as a marriage decision or compatibility guarantee. It is not yet validated for production use."}

@app.post("/api/v1/match")
def match(req: MatchRequest):
    try: return ashtakoota(req.person_a,req.person_b)
    except HTTPException: raise
    except Exception as e: raise HTTPException(500, f"Matching calculation failed: {str(e)}")
