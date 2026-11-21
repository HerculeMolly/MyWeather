from datetime import datetime, timedelta
import math
import time
from zoneinfo import ZoneInfo
import requests
import streamlit as st
import streamlit.components.v1 as components

# 1. Page Configuration & Branding
st.set_page_config(
    page_title="MyWeather — 24h Rolling Forecast", page_icon="🌤️", layout="centered"
)

# Handle instant cache-clear refresh trigger from header button
if "refresh" in st.query_params:
    st.cache_data.clear()
    del st.query_params["refresh"]
    st.rerun()

# 2. Persistent State Defaults
if "unit_temp" not in st.session_state:
    st.session_state.unit_temp = "C"
if "unit_wind" not in st.session_state:
    st.session_state.unit_wind = "mph"
if "lang" not in st.session_state:
    st.session_state.lang = "en"
if "active_charts" not in st.session_state:
    st.session_state.active_charts = ["temp", "precip", "wind", "vis"]
if "loc2" not in st.session_state:
    st.session_state.loc2 = None  # Dict: {"name": str, "lat": float, "lon": float}

# Primary Geolocation & Persistent State
if "lat" in st.query_params and "lon" in st.query_params:
    try:
        st.session_state.lat = float(st.query_params["lat"])
        st.session_state.lon = float(st.query_params["lon"])
        st.session_state.city = st.query_params.get("city", "Custom Location")
    except Exception:
        pass

if "lat" not in st.session_state:
    try:
        res = requests.get("https://ipapi.co/json/", timeout=3)
        if res.status_code == 200:
            data = res.json()
            if "latitude" in data and "longitude" in data:
                st.session_state.lat = float(data["latitude"])
                st.session_state.lon = float(data["longitude"])
                st.session_state.city = data.get("city", data.get("region", "Current Location"))
                country_code = data.get("country_code", "GB")
                if country_code not in ["GB", "US"]:
                    st.session_state.unit_wind = "km/h"
                if country_code == "US":
                    st.session_state.unit_temp = "F"
    except Exception:
        pass

if "lat" not in st.session_state:
    st.session_state.lat = 52.5785
    st.session_state.lon = -0.1285
    st.session_state.city = "Peterborough"

lat = st.session_state.lat
lon = st.session_state.lon
city_name = st.session_state.city

# 3. Lightweight Multilingual Dictionary (Settings & Guide Drawer Only)
TRANSLATIONS = {
    "en": {
        "drawer_title": "🌤️ Weather Guide & Location Settings",
        "loc1_head": "📍 Primary Location",
        "loc2_head": "👨‍👩‍👧 2nd Location Overlay (Dotted Line)",
        "loc_placeholder": "UK Postcode, City, or Lat,Lon",
        "set_btn": "Set Location",
        "clear_btn": "Clear 2nd Location",
        "reset_btn": "Reset Default",
        "charts_head": "📊 Front Screen Charts & Order",
        "units_head": "⚙️ Units & Language",
        "guide_md": """
---
### Physics & Everyman Guide
* **Temperature & Feels Like:** Solid terracotta line shows actual air temperature; thinner amber line shows apparent temperature factoring in wind chill and humidity.
* **Precipitation (% & mm):** Shaded indigo curve shows rain probability; the number tucked under the peak shows maximum expected rainfall in millimeters.
* **Wind & Gusts:** Bottom line shows sustained wind speed; upper line shows peak gusts. Arrows at the top indicate wind direction.
* **Visibility:** Teal line tracks horizontal visibility in kilometers (helpful for fog or mist).
* **Shaded Vertical Band:** Marks nighttime hours from sunset to sunrise.
        """,
    },
    "fr": {
        "drawer_title": "🌤️ Guide Météo & Paramètres",
        "loc1_head": "📍 Lieu Principal",
        "loc2_head": "👨‍👩‍👧 2e Lieu Superposé (Ligne Pointillée)",
        "loc_placeholder": "Ville ou Lat,Lon (ex: Paris)",
        "set_btn": "Définir",
        "clear_btn": "Effacer 2e Lieu",
        "reset_btn": "Réinitialiser",
        "charts_head": "📊 Graphiques & Ordre d'Affichage",
        "units_head": "⚙️ Unités & Langue",
        "guide_md": """
---
### Guide Physique & Pratique
* **Température & Ressenti :** La ligne pleine indique la température réelle ; la ligne fine indique le ressenti avec le vent.
* **Précipitations (% & mm) :** La courbe bleue indique le risque de pluie ; le chiffre sous le pic indique les millimètres attendus.
* **Vent & Rafales :** Vitesse moyenne en bas, rafales en haut, flèches de direction au sommet.
* **Visibilité :** Ligne turquoise indiquant la visibilité horizontale en km.
* **Bande Grise :** Heures de nuit du coucher au lever du soleil.
        """,
    },
    "de": {
        "drawer_title": "🌤️ Wetter-Guide & Einstellungen",
        "loc1_head": "📍 Hauptstandort",
        "loc2_head": "👨‍👩‍👧 2. Standort-Overlay (Gepunktet)",
        "loc_placeholder": "Stadt oder Lat,Lon (z.B. Berlin)",
        "set_btn": "Speichern",
        "clear_btn": "2. Ort löschen",
        "reset_btn": "Zurücksetzen",
        "charts_head": "📊 Diagramme & Reihenfolge",
        "units_head": "⚙️ Einheiten & Sprache",
        "guide_md": """
---
### Physik & Kurz-Guide
* **Temperatur & Gefühlt:** Durchgezogene Linie zeigt Lufttemperatur; dünne Linie zeigt gefühlte Temperatur.
* **Niederschlag (% & mm):** Blaue Kurve zeigt Regenwahrscheinlichkeit; Wert unter der Spitze zeigt maximale Regenmenge in mm.
* **Wind & Böen:** Untere Linie zeigt Mittelwind, obere Linie Böen, Pfeile oben zeigen Windrichtung.
* **Sichtweite:** Türkise Linie zeigt horizontale Sichtweite in km.
* **Grauer Bereich:** Nachtstunden von Sonnenuntergang bis Sonnenaufgang.
        """,
    },
    "es": {
        "drawer_title": "🌤️ Guía del Tiempo y Ajustes",
        "loc1_head": "📍 Ubicación Principal",
        "loc2_head": "👨‍👩‍👧 2ª Ubicación (Línea Punteada)",
        "loc_placeholder": "Ciudad o Lat,Lon (ej. Madrid)",
        "set_btn": "Guardar",
        "clear_btn": "Quitar 2ª Ubicación",
        "reset_btn": "Restablecer",
        "charts_head": "📊 Gráficos y Orden en Pantalla",
        "units_head": "⚙️ Unidades e Idioma",
        "guide_md": """
---
### Guía Física y Práctica
* **Temperatura y Sensación:** Línea sólida muestra temperatura real; línea fina muestra sensación térmica.
* **Precipitación (% y mm):** Curva azul muestra probabilidad de lluvia; el número bajo el pico indica milímetros máximos.
* **Viento y Rachas:** Línea inferior muestra viento sostenido; superior muestra rachas; flechas indican dirección.
* **Visibilidad:** Línea verde azulado muestra visibilidad horizontal en km.
* **Franja Gris:** Horas nocturnas desde el atardecer hasta el amanecer.
        """,
    },
}

T = TRANSLATIONS.get(st.session_state.lang, TRANSLATIONS["en"])

# 4. Shared WashDry CSS Architecture (Compact iPhone 13 Mini First)
st.markdown(
    """
    <style>
    header {display: none !important;}
    .stAppHeader {display: none !important;}
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden;}
    
    .block-container {
        padding-top: 0.2rem;
        padding-bottom: 0.1rem;
        max-width: 600px;
        margin: 0 auto;
    }
    
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        justify-content: space-between !important;
        width: 100% !important;
    }
    [data-testid="stColumn"]:nth-of-type(1) {
        flex: 1 1 auto !important;
        width: auto !important;
        min-width: 0 !important;
    }
    [data-testid="stColumn"]:nth-of-type(2) {
        flex: 0 0 50px !important;
        width: 50px !important;
        min-width: 50px !important;
        display: flex !important;
        justify-content: flex-end !important;
        align-items: center !important;
        padding-right: 0px !important;
    }
    [data-testid="stColumn"] img {
        max-width: 44px !important;
        width: 44px !important;
        height: auto !important;
        margin-left: auto !important;
        margin-right: 0px !important;
    }

    .stExpander {
        margin-top: 2px !important;
        margin-bottom: 2px !important;
    }

    .stale-badge {
        background-color: rgba(217, 119, 6, 0.2);
        color: #b45309;
        border: 1px solid rgba(217, 119, 6, 0.5);
        padding: 0px 5px;
        border-radius: 4px;
    }

    .charts-wrapper {
        border: 1px solid rgba(128, 128, 128, 0.35);
        border-radius: 6px;
        overflow: hidden;
        margin-top: 3px;
        margin-bottom: 4px;
        background-color: rgba(128, 128, 128, 0.03);
    }

    .charts-desaturated {
        filter: saturate(35%) opacity(0.75);
    }

    .footer-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 3px;
        border-top: 1px solid rgba(128, 128, 128, 0.2);
        margin-top: 2px;
        margin-bottom: 2px;
    }
    .brand-text {
        display: flex;
        flex-direction: column;
        line-height: 1.15;
        text-align: right;
    }
    .brand-name {
        text-decoration: none;
        color: inherit;
        font-weight: 700;
        font-size: 0.88rem;
    }
    .brand-sub {
        font-size: 0.7rem;
        opacity: 0.8;
        font-weight: 600;
    }
    .instant-loader {
        text-align: center;
        padding: 1.5rem 0;
        font-size: 0.85rem;
        font-weight: 600;
        opacity: 0.6;
    }

    @media (min-width: 768px) {
        .block-container { max-width: 768px !important; padding-top: 1rem; }
        .footer-container { padding-top: 4px; margin-top: 2px; }
        .brand-name { font-size: 0.98rem !important; }
        .brand-sub { font-size: 0.78rem !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# 5. Multi-Tier Weather Fetchers (Open-Meteo Primary -> Met Norway Fallback)
@st.cache_data(ttl=1800)
def fetch_open_meteo(latitude, longitude):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
        "&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation_probability,"
        "precipitation,wind_speed_10m,wind_gusts_10m,wind_direction_10m,visibility,surface_pressure,uv_index"
        "&daily=sunrise,sunset&timezone=auto&forecast_days=2"
    )
    headers = {"User-Agent": "MyWeatherApp/1.0"}
    response = requests.get(url, headers=headers, timeout=6)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=1800)
def fetch_met_norway(latitude, longitude):
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={latitude}&lon={longitude}"
    headers = {"User-Agent": "MyWeatherApp/1.0 contact@herculemolly.co.uk"}
    response = requests.get(url, headers=headers, timeout=6)
    response.raise_for_status()
    j = response.json()
    timeseries = j["properties"]["timeseries"]

    times, temps, app_temps, hums, p_probs, precips = [], [], [], [], [], []
    winds, gusts, w_dirs, vis_list, press_list, uv_list = [], [], [], [], [], []

    for entry in timeseries:
        t_str = entry["time"].replace("Z", "")[:16]
        details = entry["data"]["instant"]["details"]
        next_1h = entry["data"].get("next_1_hours", {}).get("details", {})
        precip_amt = next_1h.get("precipitation_amount", 0.0)

        t_c = details.get("air_temperature", 15.0)
        rh = details.get("relative_humidity", 70.0)
        w_ms = details.get("wind_speed", 3.0)
        w_kmh = w_ms * 3.6
        e_hpa = (rh / 100.0) * 6.105 * math.exp((17.27 * t_c) / (237.7 + t_c))
        app_c = t_c + 0.33 * e_hpa - 0.70 * w_ms - 4.00

        times.append(t_str)
        temps.append(t_c)
        app_temps.append(round(app_c, 1))
        hums.append(rh)
        p_probs.append(100 if precip_amt > 0.1 else 10)
        precips.append(precip_amt)
        winds.append(w_kmh)
        gusts.append(details.get("wind_speed_of_gust", w_ms * 1.4) * 3.6)
        w_dirs.append(details.get("wind_from_direction", 180))
        vis_list.append(10000.0)
        press_list.append(details.get("air_pressure_at_sea_level", 1013.0))
        uv_list.append(0.0)

    return {
        "timezone": "UTC",
        "hourly": {
            "time": times,
            "temperature_2m": temps,
            "apparent_temperature": app_temps,
            "relative_humidity_2m": hums,
            "precipitation_probability": p_probs,
            "precipitation": precips,
            "wind_speed_10m": winds,
            "wind_gusts_10m": gusts,
            "wind_direction_10m": w_dirs,
            "visibility": vis_list,
            "surface_pressure": press_list,
            "uv_index": uv_list,
        },
        "daily": {"sunrise": [], "sunset": []},
    }


def get_weather_with_fallback(latitude, longitude):
    for attempt in range(1, 3):
        try:
            return fetch_open_meteo(latitude, longitude), False
        except Exception:
            time.sleep(0.5)
    try:
        return fetch_met_norway(latitude, longitude), False
    except Exception:
        return None, True


data, is_stale = get_weather_with_fallback(lat, lon)

# Extract timezone & 24-hour rolling slice anchored to NOW (using local naive time to avoid TypeErrors)
tz_name = data.get("timezone", "Europe/London") if data else "Europe/London"
try:
    tz = ZoneInfo(tz_name)
except Exception:
    tz = ZoneInfo("Europe/London")

now = datetime.now(tz)
timestamp_str = now.strftime("%H%M %d-%b-%y").lower()

if is_stale or not data or "hourly" not in data:
    is_stale = True
    base_time = now.replace(minute=0, second=0, microsecond=0)
    slice_times = [(base_time + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(25)]
    slice_data = {
        "times": slice_times,
        "temp": [14.0] * 25,
        "feels": [12.5] * 25,
        "precip_prob": [10] * 25,
        "precip_mm": [0.0] * 25,
        "wind": [12.0] * 25,
        "gust": [18.0] * 25,
        "wind_dir": [220] * 25,
        "vis": [15.0] * 25,
        "hum": [72] * 25,
        "press": [1014] * 25,
        "uv": [1.0] * 25,
    }
    sunrise_hours = [7]
    sunset_hours = [17]
else:
    h_data = data["hourly"]
    all_times = h_data["time"]
    
    # Robust current hour match using local naive comparison
    now_local = datetime.now()
    start_idx = 0
    for idx, t_str in enumerate(all_times):
        try:
            dt = datetime.fromisoformat(t_str.replace("Z", ""))
            if dt >= now_local:
                start_idx = max(0, idx - 1)
                break
        except Exception:
            pass
    end_idx = min(start_idx + 25, len(all_times))

    def get_slice(key, default_val=0.0):
        arr = h_data.get(key, [default_val] * len(all_times))
        sliced = [arr[i] if arr[i] is not None else default_val for i in range(start_idx, end_idx)]
        while len(sliced) < 25:
            sliced.append(sliced[-1] if sliced else default_val)
        return sliced

    slice_data = {
        "times": get_slice("time", now.strftime("%Y-%m-%dT%H:00")),
        "temp": get_slice("temperature_2m", 15.0),
        "feels": get_slice("apparent_temperature", 14.0),
        "precip_prob": get_slice("precipitation_probability", 0),
        "precip_mm": get_slice("precipitation", 0.0),
        "wind": get_slice("wind_speed_10m", 10.0),
        "gust": get_slice("wind_gusts_10m", 15.0),
        "wind_dir": get_slice("wind_direction_10m", 180),
        "vis": [round(v / 1000.0, 1) for v in get_slice("visibility", 10000.0)],
        "hum": get_slice("relative_humidity_2m", 70),
        "press": [round(p) for p in get_slice("surface_pressure", 1013)],
        "uv": get_slice("uv_index", 0.0),
    }

    sunrise_hours, sunset_hours = [], []
    daily = data.get("daily", {})
    for sr in daily.get("sunrise", []):
        if "T" in sr:
            sunrise_hours.append(int(sr.split("T")[1][:2]))
    for ss in daily.get("sunset", []):
        if "T" in ss:
            sunset_hours.append(int(ss.split("T")[1][:2]))
    if not sunrise_hours:
        sunrise_hours = [7]
    if not sunset_hours:
        sunset_hours = [17]

# Optional 2nd Location Overlay Data
slice_data_2 = None
if st.session_state.loc2:
    d2, stale2 = get_weather_with_fallback(st.session_state.loc2["lat"], st.session_state.loc2["lon"])
    if d2 and "hourly" in d2 and not stale2:
        h2 = d2["hourly"]
        t2 = h2["time"]
        s_idx2 = min(start_idx if not is_stale else 0, max(0, len(t2) - 25))
        e_idx2 = min(s_idx2 + 25, len(t2))

        def get_slice2(key, default_val=0.0):
            arr = h2.get(key, [default_val] * len(t2))
            sliced = [arr[i] if arr[i] is not None else default_val for i in range(s_idx2, e_idx2)]
            while len(sliced) < 25:
                sliced.append(sliced[-1] if sliced else default_val)
            return sliced

        slice_data_2 = {
            "temp": get_slice2("temperature_2m", 15.0),
            "precip_prob": get_slice2("precipitation_probability", 0),
            "wind": get_slice2("wind_speed_10m", 10.0),
            "vis": [round(v / 1000.0, 1) for v in get_slice2("visibility", 10000.0)],
            "hum": get_slice2("relative_humidity_2m", 70),
            "uv": get_slice2("uv_index", 0.0),
        }

# Unit Conversions
if st.session_state.unit_temp == "F":
    slice_data["temp"] = [round(c * 9 / 5 + 32, 1) for c in slice_data["temp"]]
    slice_data["feels"] = [round(c * 9 / 5 + 32, 1) for c in slice_data["feels"]]
    if slice_data_2:
        slice_data_2["temp"] = [round(c * 9 / 5 + 32, 1) for c in slice_data_2["temp"]]

if st.session_state.unit_wind == "mph":
    slice_data["wind"] = [round(k * 0.621371, 1) for k in slice_data["wind"]]
    slice_data["gust"] = [round(k * 0.621371, 1) for k in slice_data["gust"]]
    if slice_data_2:
        slice_data_2["wind"] = [round(k * 0.621371, 1) for k in slice_data_2["wind"]]

# 6. Header Row (Timestamp on same line + NOW anchor arrow + Refresh icon only)
col_head, col_logo = st.columns([5, 1])

badge_cls = "stale-badge" if is_stale else ""
loc2_pill = (
    f'<span style="font-size:0.68rem; opacity:0.75; margin-left:6px;">⋯ {st.session_state.loc2["name"]}</span>'
    if st.session_state.loc2
    else ""
)

with col_head:
    st.markdown(
        f"""
        <div style="display: flex; align-items: baseline; gap: 6px; flex-wrap: nowrap;">
            <h1 style="margin: 0; font-size: 1.3rem; font-weight: 800; line-height: 1.1;">MyWeather</h1>
            <span class="{badge_cls}" style="font-size: 0.74rem; opacity: 0.8; font-weight: 700; letter-spacing: -0.2px;">↙ {timestamp_str}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 2px;">
            <div style="font-size: 0.78rem; font-weight: 600; opacity: 0.85;">📍 {city_name}{loc2_pill}</div>
            <a href="?refresh=1" target="_self" title="Refresh" style="font-size: 0.82rem; text-decoration: none; background: rgba(128,128,128,0.12); padding: 1px 7px; border-radius: 4px; color: inherit; opacity: 0.85;">🔄</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_logo:
    try:
        st.image("logo.png", width=44)
    except Exception:
        st.markdown(
            '<div style="border: 2px dashed rgba(128,128,128,0.4); border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-size: 0.6rem; opacity: 0.6; margin-left: auto;">Logo</div>',
            unsafe_allow_html=True,
        )


# 7. Synchronized SVG Chart Builder (Filled Areas Restored)
def render_svg_dashboard():
    W = 360  
    PAD_L = 6
    PAD_R = 6
    PLOT_W = W - PAD_L - PAD_R
    HEADER_H = 18
    STRIP_H = 74

    active = st.session_state.active_charts
    if not active:
        active = ["temp", "precip", "wind", "vis"]

    TOTAL_H = HEADER_H + len(active) * STRIP_H

    def x_pos(i):
        return PAD_L + (i / 24.0) * PLOT_W

    # Nighttime Shading Rectangles
    sr_h = sunrise_hours[0]
    ss_h = sunset_hours[0]
    night_rects = []
    in_night = False
    n_start = 0
    for i in range(25):
        h_val = int(slice_data["times"][i].split("T")[1][:2])
        is_night = (h_val >= ss_h) or (h_val < sr_h)
        if is_night and not in_night:
            in_night = True
            n_start = i
        elif not is_night and in_night:
            in_night = False
            night_rects.append((x_pos(n_start), x_pos(i)))
    if in_night:
        night_rects.append((x_pos(n_start), x_pos(24)))

    midnight_x = x_pos(12)
    for i in range(25):
        if slice_data["times"][i].endswith("T00:00"):
            midnight_x = x_pos(i)
            break
    icon_x = max(PAD_L + 16, min(W - PAD_R - 42, midnight_x - 10))

    svg_parts = [
        f'<svg viewBox="0 0 {W} {TOTAL_H}" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg" style="display:block; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">'
    ]

    # Top Time Axis Row
    svg_parts.append(
        f'<rect x="0" y="0" width="{W}" height="{HEADER_H}" fill="rgba(128,128,128,0.08)"/>'
    )
    svg_parts.append(
        f'<line x1="0" y1="{HEADER_H}" x2="{W}" y2="{HEADER_H}" stroke="rgba(128,128,128,0.35)" stroke-width="1"/>'
    )
    for i in range(0, 25, 4):
        lbl = slice_data["times"][i].split("T")[1].replace(":", "")
        xp = x_pos(i)
        anchor = "start" if i == 0 else ("end" if i == 24 else "middle")
        weight = "800" if i == 0 else "600"
        svg_parts.append(
            f'<text x="{xp}" y="13" font-size="9.5" font-weight="{weight}" fill="currentColor" opacity="0.85" text-anchor="{anchor}">{lbl}</text>'
        )

    def make_points(vals, min_v, max_v, top_y, bot_y):
        span = max(max_v - min_v, 0.1)
        pts = []
        for idx, v in enumerate(vals):
            xp = x_pos(idx)
            yp = bot_y - ((v - min_v) / span) * (bot_y - top_y)
            pts.append((xp, yp))
        return pts

    for row_idx, metric in enumerate(active):
        y0 = HEADER_H + row_idx * STRIP_H
        y1 = y0 + STRIP_H
        top_pad = y0 + 10
        bot_pad = y1 - 8

        for nx1, nx2 in night_rects:
            svg_parts.append(
                f'<rect x="{nx1:.1f}" y="{y0}" width="{max(1, nx2 - nx1):.1f}" height="{STRIP_H}" fill="rgba(128,128,128,0.14)"/>'
            )

        if row_idx > 0:
            svg_parts.append(
                f'<line x1="0" y1="{y0}" x2="{W}" y2="{y0}" stroke="rgba(128,128,128,0.35)" stroke-width="1"/>'
            )

        # --- METRIC 1: TEMPERATURE & FEELS LIKE ---
        if metric == "temp":
            all_t = slice_data["temp"] + slice_data["feels"]
            if slice_data_2:
                all_t += slice_data_2["temp"]
            min_t = math.floor(min(all_t) - 2)
            max_t = math.ceil(max(all_t) + 2)

            pts_t = make_points(slice_data["temp"], min_t, max_t, top_pad, bot_pad)
            pts_f = make_points(slice_data["feels"], min_t, max_t, top_pad, bot_pad)

            # Translucent terracotta fill under Temp curve
            area_str = (
                f"M {pts_t[0][0]:.1f},{bot_pad} "
                + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts_t)
                + f" L {pts_t[-1][0]:.1f},{bot_pad} Z"
            )
            svg_parts.append(f'<path d="{area_str}" fill="rgba(217, 72, 15, 0.14)"/>')

            f_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_f)
            svg_parts.append(
                f'<polyline points="{f_str}" fill="none" stroke="#d97706" stroke-width="1.3" opacity="0.85"/>'
            )

            t_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_t)
            svg_parts.append(
                f'<polyline points="{t_str}" fill="none" stroke="#c92a2a" stroke-width="2.1"/>'
            )

            if slice_data_2:
                pts_t2 = make_points(slice_data_2["temp"], min_t, max_t, top_pad, bot_pad)
                t2_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_t2)
                svg_parts.append(
                    f'<polyline points="{t2_str}" fill="none" stroke="#1e3a8a" stroke-width="1.4" stroke-dasharray="3,3"/>'
                )

            svg_parts.append(
                f'<rect x="{icon_x}" y="{y0+3}" width="18" height="18" rx="3" fill="#1f2937"/>'
            )
            svg_parts.append(
                f'<circle cx="{icon_x+9}" cy="{y0+12}" r="4" fill="none" stroke="#ffffff" stroke-width="1.4"/>'
            )
            mid_t = round((max_t + min_t) / 2)
            for val_lbl, yp_lbl in [(max_t, y0 + 11), (mid_t, y0 + 40), (min_t, y1 - 4)]:
                svg_parts.append(
                    f'<text x="{icon_x+22}" y="{yp_lbl}" font-size="8.5" font-weight="700" fill="currentColor" opacity="0.75">{val_lbl}°</text>'
                )

        # --- METRIC 2: PRECIPITATION (% CHANCE & PEAK MM) ---
        elif metric == "precip":
            probs = slice_data["precip_prob"]
            mms = slice_data["precip_mm"]
            pts_p = make_points(probs, 0, 100, top_pad, bot_pad)

            # Translucent blue fill under Precipitation probability
            area_str = (
                f"M {pts_p[0][0]:.1f},{bot_pad} "
                + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts_p)
                + f" L {pts_p[-1][0]:.1f},{bot_pad} Z"
            )
            svg_parts.append(f'<path d="{area_str}" fill="rgba(29, 78, 216, 0.16)"/>')

            p_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_p)
            svg_parts.append(
                f'<polyline points="{p_str}" fill="none" stroke="#1d4ed8" stroke-width="2"/>'
            )

            if slice_data_2:
                pts_p2 = make_points(slice_data_2["precip_prob"], 0, 100, top_pad, bot_pad)
                p2_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_p2)
                svg_parts.append(
                    f'<polyline points="{p2_str}" fill="none" stroke="#0f172a" stroke-width="1.4" stroke-dasharray="3,3"/>'
                )

            max_mm = max(mms)
            if max_mm > 0.0:
                peak_idx = mms.index(max_mm)
                px, py = pts_p[peak_idx]
                lbl_y = min(y1 - 4, max(y0 + 22, py + 13))
                svg_parts.append(
                    f'<text x="{px:.1f}" y="{lbl_y:.1f}" font-size="8.5" font-weight="800" fill="#1d4ed8" text-anchor="middle">{round(max_mm, 1)}</text>'
                )

            svg_parts.append(
                f'<rect x="{icon_x}" y="{y0+3}" width="18" height="18" rx="3" fill="#1f2937"/>'
            )
            svg_parts.append(
                f'<path d="M {icon_x+9},{y0+6} C {icon_x+9},{y0+6} {icon_x+14},{y0+12} {icon_x+14},{y0+14.5} A 5,5 0 1,1 {icon_x+4},{y0+14.5} C {icon_x+4},{y0+12} {icon_x+9},{y0+6} {icon_x+9},{y0+6} Z" fill="none" stroke="#ffffff" stroke-width="1.4"/>'
            )
            for val_lbl, yp_lbl in [("100", y0 + 11), ("50", y0 + 40), ("0", y1 - 4)]:
                svg_parts.append(
                    f'<text x="{icon_x+22}" y="{yp_lbl}" font-size="8.5" font-weight="700" fill="currentColor" opacity="0.75">{val_lbl}</text>'
                )

        # --- METRIC 3: WIND, GUSTS & DIRECTION ARROWS ---
        elif metric == "wind":
            all_w = slice_data["wind"] + slice_data["gust"]
            if slice_data_2:
                all_w += slice_data_2["wind"]
            max_w = max(25, math.ceil(max(all_w) / 10.0) * 10)

            pts_w = make_points(slice_data["wind"], 0, max_w, top_pad + 6, bot_pad)
            pts_g = make_points(slice_data["gust"], 0, max_w, top_pad + 6, bot_pad)

            g_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_g)
            svg_parts.append(
                f'<polyline points="{g_str}" fill="none" stroke="#64748b" stroke-width="1.3"/>'
            )

            w_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_w)
            svg_parts.append(
                f'<polyline points="{w_str}" fill="none" stroke="#0f172a" stroke-width="2"/>'
            )

            if slice_data_2:
                pts_w2 = make_points(slice_data_2["wind"], 0, max_w, top_pad + 6, bot_pad)
                w2_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_w2)
                svg_parts.append(
                    f'<polyline points="{w2_str}" fill="none" stroke="#b45309" stroke-width="1.4" stroke-dasharray="3,3"/>'
                )

            for i in range(1, 24, 3):
                ax = x_pos(i)
                ay = y0 + 8
                deg = slice_data["wind_dir"][i]
                svg_parts.append(
                    f'<g transform="translate({ax:.1f},{ay}) rotate({deg})">'
                    f'<line x1="0" y1="-4" x2="0" y2="4" stroke="#3b82f6" stroke-width="1.4"/>'
                    f'<polyline points="-2.5,1.5 0,4 2.5,1.5" fill="none" stroke="#3b82f6" stroke-width="1.4"/>'
                    f"</g>"
                )

            svg_parts.append(
                f'<rect x="{icon_x}" y="{y0+3}" width="18" height="18" rx="3" fill="#1f2937"/>'
            )
            svg_parts.append(
                f'<path d="M {icon_x+3},{y0+9} H {icon_x+13} M {icon_x+3},{y0+13} H {icon_x+15} M {icon_x+3},{y0+17} H {icon_x+10}" stroke="#ffffff" stroke-width="1.4" stroke-linecap="round"/>'
            )
            for val_lbl, yp_lbl in [(max_w, y0 + 11), (round(max_w / 2), y0 + 40), (0, y1 - 4)]:
                svg_parts.append(
                    f'<text x="{icon_x+22}" y="{yp_lbl}" font-size="8.5" font-weight="700" fill="currentColor" opacity="0.75">{val_lbl}</text>'
                )

        # --- METRIC 4: VISIBILITY ---
        elif metric == "vis":
            all_v = slice_data["vis"] + (slice_data_2["vis"] if slice_data_2 else [])
            max_v = max(20, math.ceil(max(all_v) / 5.0) * 5)
            pts_v = make_points(slice_data["vis"], 0, max_v, top_pad, bot_pad)

            v_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_v)
            svg_parts.append(
                f'<polyline points="{v_str}" fill="none" stroke="#0d9488" stroke-width="2"/>'
            )

            if slice_data_2:
                pts_v2 = make_points(slice_data_2["vis"], 0, max_v, top_pad, bot_pad)
                v2_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_v2)
                svg_parts.append(
                    f'<polyline points="{v2_str}" fill="none" stroke="#1e3a8a" stroke-width="1.4" stroke-dasharray="3,3"/>'
                )

            svg_parts.append(
                f'<rect x="{icon_x}" y="{y0+3}" width="18" height="18" rx="3" fill="#1f2937"/>'
            )
            svg_parts.append(
                f'<path d="M {icon_x+3},{y0+12} Q {icon_x+9},{y0+6} {icon_x+15},{y0+12} Q {icon_x+9},{y0+18} {icon_x+3},{y0+12} Z" fill="none" stroke="#ffffff" stroke-width="1.3"/>'
            )
            svg_parts.append(
                f'<circle cx="{icon_x+9}" cy="{y0+12}" r="2" fill="#ffffff"/>'
            )
            for val_lbl, yp_lbl in [(max_v, y0 + 11), (round(max_v / 2), y0 + 40), (0, y1 - 4)]:
                svg_parts.append(
                    f'<text x="{icon_x+22}" y="{yp_lbl}" font-size="8.5" font-weight="700" fill="currentColor" opacity="0.75">{val_lbl}</text>'
                )

        # --- METRIC 5: HUMIDITY & PRESSURE (DUAL AXIS) ---
        elif metric == "hum_press":
            pts_h = make_points(slice_data["hum"], 0, 100, top_pad, bot_pad)
            p_vals = slice_data["press"]
            min_pr, max_pr = min(p_vals) - 3, max(p_vals) + 3
            pts_pr = make_points(p_vals, min_pr, max_pr, top_pad, bot_pad)

            h_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_h)
            svg_parts.append(
                f'<polyline points="{h_str}" fill="none" stroke="#0284c7" stroke-width="1.8"/>'
            )
            pr_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_pr)
            svg_parts.append(
                f'<polyline points="{pr_str}" fill="none" stroke="#7c3aed" stroke-width="1.5" stroke-dasharray="4,2"/>'
            )
            svg_parts.append(
                f'<rect x="{icon_x}" y="{y0+3}" width="18" height="18" rx="3" fill="#1f2937"/>'
            )
            svg_parts.append(
                f'<text x="{icon_x+9}" y="{y0+15}" font-size="9" font-weight="800" fill="#ffffff" text-anchor="middle">%</text>'
            )
            for val_lbl, yp_lbl in [("100", y0 + 11), ("50", y0 + 40), ("0", y1 - 4)]:
                svg_parts.append(
                    f'<text x="{icon_x+22}" y="{yp_lbl}" font-size="8.5" font-weight="700" fill="currentColor" opacity="0.75">{val_lbl}</text>'
                )

        # --- METRIC 6: UV INDEX ---
        elif metric == "uv":
            max_u = max(8, math.ceil(max(slice_data["uv"])))
            pts_u = make_points(slice_data["uv"], 0, max_u, top_pad, bot_pad)
            area_u = (
                f"M {pts_u[0][0]:.1f},{bot_pad} "
                + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts_u)
                + f" L {pts_u[-1][0]:.1f},{bot_pad} Z"
            )
            svg_parts.append(f'<path d="{area_u}" fill="rgba(217, 119, 6, 0.18)"/>')
            u_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_u)
            svg_parts.append(
                f'<polyline points="{u_str}" fill="none" stroke="#b45309" stroke-width="2"/>'
            )
            svg_parts.append(
                f'<rect x="{icon_x}" y="{y0+3}" width="18" height="18" rx="3" fill="#1f2937"/>'
            )
            svg_parts.append(
                f'<text x="{icon_x+9}" y="{y0+15}" font-size="8" font-weight="800" fill="#ffffff" text-anchor="middle">UV</text>'
            )
            for val_lbl, yp_lbl in [(max_u, y0 + 11), (round(max_u / 2), y0 + 40), (0, y1 - 4)]:
                svg_parts.append(
                    f'<text x="{icon_x+22}" y="{yp_lbl}" font-size="8.5" font-weight="700" fill="currentColor" opacity="0.75">{val_lbl}</text>'
                )

    svg_parts.append("</svg>")
    wrapper_cls = "charts-wrapper charts-desaturated" if is_stale else "charts-wrapper"
    st.markdown(f'<div class="{wrapper_cls}">{"".join(svg_parts)}</div>', unsafe_allow_html=True)


render_svg_dashboard()


# Helper function to resolve UK Postcode, Global City, or Raw Coordinates
def resolve_location_string(query_str):
    q = query_str.strip()
    if "," in q:
        try:
            parts = q.split(",")
            return float(parts[0].strip()), float(parts[1].strip()), f"{parts[0].strip()}, {parts[1].strip()}"
        except ValueError:
            pass
    try:
        q_up = q.upper()
        res = requests.get(f"https://api.postcodes.io/postcodes/{q_up}", timeout=3)
        if res.status_code == 200 and res.json().get("result"):
            r = res.json()["result"]
            return r["latitude"], r["longitude"], f"{r.get('admin_district', q_up)} ({q_up})"
    except Exception:
        pass
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1&language=en&format=json"
        geo_res = requests.get(geo_url, timeout=3)
        if geo_res.status_code == 200:
            g_data = geo_res.json()
            if "results" in g_data and len(g_data["results"]) > 0:
                loc = g_data["results"][0]
                label = f"{loc.get('name', q)}, {loc.get('country', '')}".strip(", ")
                return loc["latitude"], loc["longitude"], label
    except Exception:
        pass
    return None


# 8. Integrated Guide, Multi-Location, Chart Order & Language Settings Drawer
with st.expander(T["drawer_title"]):
    st.markdown(f"#### {T['loc1_head']}")
    with st.form(key="loc1_form"):
        q1 = st.text_input("Primary Location", placeholder=T["loc_placeholder"], label_visibility="collapsed")
        if st.form_submit_button(T["set_btn"], use_container_width=True) and q1:
            res1 = resolve_location_string(q1)
            if res1:
                st.session_state.lat, st.session_state.lon, st.session_state.city = res1
                st.query_params["lat"] = str(res1[0])
                st.query_params["lon"] = str(res1[1])
                st.query_params["city"] = res1[2]
                st.rerun()
            else:
                st.error("Location not found.")

    if st.session_state.city != "Peterborough":
        if st.button(T["reset_btn"], use_container_width=True):
            st.session_state.lat = 52.5785
            st.session_state.lon = -0.1285
            st.session_state.city = "Peterborough"
            st.query_params.clear()
            st.rerun()

    st.markdown(f"#### {T['loc2_head']}")
    with st.form(key="loc2_form"):
        q2 = st.text_input("2nd Location", placeholder=T["loc_placeholder"], label_visibility="collapsed")
        if st.form_submit_button(T["set_btn"], use_container_width=True) and q2:
            res2 = resolve_location_string(q2)
            if res2:
                st.session_state.loc2 = {"lat": res2[0], "lon": res2[1], "name": res2[2]}
                st.rerun()
            else:
                st.error("2nd Location not found.")

    if st.session_state.loc2:
        if st.button(f"{T['clear_btn']} ({st.session_state.loc2['name']})", use_container_width=True):
            st.session_state.loc2 = None
            st.rerun()

    st.markdown(f"#### {T['charts_head']}")
    chart_labels = {
        "temp": "🌡️ Temp & Feels Like",
        "precip": "💧 Precipitation (% & mm)",
        "wind": "💨 Wind & Gusts",
        "vis": "👁️ Visibility",
        "hum_press": "🧭 Humidity & Pressure",
        "uv": "☀️ UV Index",
    }
    selected = st.multiselect(
        "Select & order charts (order picked = display order)",
        options=list(chart_labels.keys()),
        default=st.session_state.active_charts,
        format_func=lambda k: chart_labels[k],
        label_visibility="collapsed",
    )
    if selected and selected != st.session_state.active_charts:
        st.session_state.active_charts = selected
        st.rerun()

    st.markdown(f"#### {T['units_head']}")
    c_u1, c_u2, c_u3 = st.columns(3)
    with c_u1:
        t_choice = st.selectbox("Temp", ["C", "F"], index=0 if st.session_state.unit_temp == "C" else 1)
        if t_choice != st.session_state.unit_temp:
            st.session_state.unit_temp = t_choice
            st.rerun()
    with c_u2:
        w_choice = st.selectbox("Wind", ["mph", "km/h"], index=0 if st.session_state.unit_wind == "mph" else 1)
        if w_choice != st.session_state.unit_wind:
            st.session_state.unit_wind = w_choice
            st.rerun()
    with c_u3:
        lang_keys = ["en", "fr", "de", "es"]
        l_choice = st.selectbox(
            "Lang",
            lang_keys,
            index=lang_keys.index(st.session_state.lang),
            format_func=lambda x: x.upper(),
        )
        if l_choice != st.session_state.lang:
            st.session_state.lang = l_choice
            st.rerun()

    st.markdown(T["guide_md"])

# 9. Footer Branding
st.markdown(
    """
    <div class="footer-container">
        <div>
            <a href="https://buymeacoffee.com/herculemolly" target="_blank" style="text-decoration: none; background-color: #ffdd00; color: #000; padding: 3px 7px; border-radius: 6px; font-weight: 700; font-size: 0.72rem; white-space: nowrap;">☕ Buy me a coffee</a>
        </div>
        <div class="brand-text">
            <a href="https://herculemolly.co.uk" target="_blank" class="brand-name">Hercule Molly</a>
            <span class="brand-sub">Quality Woodcraft Gifts</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
