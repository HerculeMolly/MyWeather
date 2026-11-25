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
if "loc2" not in st.session_state:
    st.session_state.loc2 = None  # Dict: {"name": str, "lat": float, "lon": float}
if "show_overlay" not in st.session_state:
    st.session_state.show_overlay = False

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

# 3. Lightweight Multilingual Dictionary (Concise & Clean)
TRANSLATIONS = {
    "en": {
        "exp_loc": "📍 Locations",
        "exp_units": "⚙️ Units",
        "exp_guide": "📖 Guide",
        "loc1_head": "Primary Location",
        "loc2_head": "2nd Location Overlay (Dotted Line)",
        "loc_placeholder": "UK Postcode, City, or Lat,Lon",
        "set_btn": "Set Location",
        "clear_btn": "Clear 2nd Location",
        "reset_btn": "Reset Default",
        "units_head": "Units & Language Settings",
        "guide_md": """
* **Temp / Feels-Like:** Red line is air temp; orange line & delta pill show feels-like variance.
* **Precipitation:** Blue curve shows rain probability & peak mm/24h.
* **Wind:** Slate grey lines track speed and gusts with direction arrows.
* **Visibility:** Teal gradient highlights tracking haze and hazard thresholds.
        """,
    },
    "fr": {
        "exp_loc": "📍 Lieux",
        "exp_units": "⚙️ Unités",
        "exp_guide": "📖 Guide",
        "loc1_head": "Lieu Principal",
        "loc2_head": "2e Lieu Superposé",
        "loc_placeholder": "Ville ou Lat,Lon",
        "set_btn": "Définir",
        "clear_btn": "Effacer 2e Lieu",
        "reset_btn": "Réinitialiser",
        "units_head": "Unités & Langue",
        "guide_md": """
* **Température & Ressenti :** Ligne rouge (réel) & orange (ressenti).
* **Précipitations :** Risque de pluie et cumul mm.
* **Vent :** Vitesse, rafales et orientation.
* **Visibilité :** Suivi des seuils de brume et de brouillard.
        """,
    },
    "de": {
        "exp_loc": "📍 Standorte",
        "exp_units": "⚙️ Einheiten",
        "exp_guide": "📖 Guide",
        "loc1_head": "Hauptstandort",
        "loc2_head": "2. Standort-Overlay",
        "loc_placeholder": "Stadt oder Lat,Lon",
        "set_btn": "Speichern",
        "clear_btn": "Löschen",
        "reset_btn": "Zurücksetzen",
        "units_head": "Einheiten & Sprache",
        "guide_md": """
* **Temperatur:** Rot = Lufttemperatur, Orange = Gefühlt.
* **Niederschlag:** Regenwahrscheinlichkeit & mm.
* **Wind:** Geschwindigkeit, Böen & Windrichtung.
* **Sichtweite:** Horizontale Sicht und Warnschwellen.
        """,
    },
    "es": {
        "exp_loc": "📍 Ubicaciones",
        "exp_units": "⚙️ Unidades",
        "exp_guide": "📖 Guía",
        "loc1_head": "Ubicación Principal",
        "loc2_head": "2ª Ubicación",
        "loc_placeholder": "Ciudad o Lat,Lon",
        "set_btn": "Guardar",
        "clear_btn": "Quitar",
        "reset_btn": "Restablecer",
        "units_head": "Unidades e Idioma",
        "guide_md": """
* **Temperatura:** Roja = real; naranja = sensación térmica.
* **Precipitación:** Probabilidad de lluvia y mm.
* **Viento:** Velocidad, ráfagas y dirección.
* **Visibilidad:** Seguimiento de calima y niebla.
        """,
    },
}

T = TRANSLATIONS.get(st.session_state.lang, TRANSLATIONS["en"])

# 4. Shared WashDry CSS Architecture (Forced Non-Black Expander Backgrounds)
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
    
    /* Header layout */
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

    /* Force 3 Equal Columns for Expanders in a single row */
    div[data-testid="stHorizontalBlock"]:has(div.stExpander) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 6px !important;
        width: 100% !important;
        align-items: flex-start !important;
        position: relative !important;
    }
    div[data-testid="stHorizontalBlock"]:has(div.stExpander) > div[data-testid="stColumn"] {
        flex: 1 1 0px !important;
        width: 33.333% !important;
        min-width: 0 !important;
        max-width: 33.333% !important;
        position: static !important;
    }
    div[data-testid="stHorizontalBlock"]:has(div.stExpander) .stExpander summary {
        padding-left: 4px !important;
        padding-right: 2px !important;
        font-size: 0.78rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* Make expanded drop-down content span full screen width with solid readable surface */
    div[data-testid="stHorizontalBlock"]:has(div.stExpander) .stExpander[data-baseweb="accordion"] {
        position: static !important;
    }
    .stExpander details[open] {
        position: absolute !important;
        left: 0 !important;
        right: 0 !important;
        width: 100% !important;
        z-index: 999 !important;
        background-color: #1e1e1e !important;
        color: #ffffff !important;
        border: 1px solid rgba(128, 128, 128, 0.5);
        border-radius: 6px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        padding: 10px 14px;
        margin-top: 2px;
    }
    .stExpander details[open] * {
        color: #ffffff !important;
    }
    .stExpander details[open] input {
        background-color: #2d2d2d !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }
    .stExpander details[open] button {
        background-color: #333333 !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
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
        border: 1px solid rgba(128, 128, 128, 0.75);
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
        border-top: 1px solid rgba(128, 128, 128, 0.3);
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


# 5. Multi-Tier Weather Fetchers
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
    current_hour_prefix = now.strftime("%Y-%m-%dT%H")
    start_idx = 0
    for idx, t in enumerate(all_times):
        if t.startswith(current_hour_prefix):
            start_idx = idx
            break
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
        "vis": [round(v / 1000.0, 2) for v in get_slice("visibility", 10000.0)],
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
            "vis": [round(v / 1000.0, 2) for v in get_slice2("visibility", 10000.0)],
            "hum": get_slice2("relative_humidity_2m", 70),
            "uv": get_slice2("uv_index", 0.0),
        }

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
    slice_data["vis"] = [round(v * 0.621371, 2) for v in slice_data["vis"]]
    if slice_data_2:
        slice_data_2["vis"] = [round(v * 0.621371, 2) for v in slice_data_2["vis"]]

# 6. Header Row
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
            <span class="{badge_cls}" style="font-size: 0.74rem; opacity: 0.8; font-weight: 700; letter-spacing: -0.2px;">{timestamp_str}</span>
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


# 7. Synchronized SVG Chart Builder
def build_svg_block(charts_to_render):
    W = 360  
    PAD_L = 6
    PAD_R = 6
    PLOT_W = W - PAD_L - PAD_R
    HEADER_H = 18
    STRIP_H = 96

    TOTAL_H = HEADER_H + len(charts_to_render) * STRIP_H

    def x_pos(i):
        return PAD_L + (i / 24.0) * PLOT_W

    sr_h = sunrise_hours[0]
    ss_h = sunset_hours[0]
    night_rects = []
    day_rects = []
    
    in_night = False
    n_start = 0
    in_day = False
    d_start = 0

    for i in range(25):
        h_val = int(slice_data["times"][i].split("T")[1][:2])
        is_night = (h_val >= ss_h) or (h_val < sr_h)
        
        if is_night and not in_night:
            in_night = True
            n_start = i
        elif not is_night and in_night:
            in_night = False
            night_rects.append((x_pos(n_start), x_pos(i)))
            
        if not is_night and not in_day:
            in_day = True
            d_start = i
        elif is_night and in_day:
            in_day = False
            day_rects.append((x_pos(d_start), x_pos(i)))

    if in_night:
        night_rects.append((x_pos(n_start), x_pos(24)))
    if in_day:
        day_rects.append((x_pos(d_start), x_pos(24)))

    midnight_x = x_pos(12)
    for i in range(25):
        if slice_data["times"][i].endswith("T00:00"):
            midnight_x = x_pos(i)
            break
    icon_x = max(PAD_L + 16, min(W - PAD_R - 70, midnight_x - 14))

    svg_parts = [
        f'<svg viewBox="0 0 {W} {TOTAL_H}" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg" style="display:block; font-family: -apple-system, BlinkMacSystemFont, sans-serif; color: inherit;">'
    ]

    svg_parts.append(f'<rect x="0" y="0" width="{W}" height="{HEADER_H}" fill="rgba(128,128,128,0.08)"/>')
    svg_parts.append(f'<line x1="0" y1="{HEADER_H}" x2="{W}" y2="{HEADER_H}" stroke="rgba(128,128,128,0.55)" stroke-width="1"/>')
    for i in range(0, 25, 4):
        lbl = slice_data["times"][i].split("T")[1].replace(":", "")
        xp = x_pos(i)
        anchor = "start" if i == 0 else ("end" if i == 24 else "middle")
        weight = "800" if i == 0 else "600"
        svg_parts.append(f'<text x="{xp}" y="13" font-size="9.5" font-weight="{weight}" fill="currentColor" opacity="0.85" text-anchor="{anchor}">{lbl}</text>')

    def make_points(vals, min_v, max_v, top_y, bot_y):
        span = max(max_v - min_v, 0.1)
        pts = []
        for idx, v in enumerate(vals):
            xp = x_pos(idx)
            yp = bot_y - ((v - min_v) / span) * (bot_y - top_y)
            pts.append((xp, yp))
        return pts

    for row_idx, metric in enumerate(charts_to_render):
        y0 = HEADER_H + row_idx * STRIP_H
        y1 = y0 + STRIP_H
        top_pad = y0 + 12
        bot_pad = y1 - 10

        for dx1, dx2 in day_rects:
            svg_parts.append(f'<rect x="{dx1:.1f}" y="{y0}" width="{max(1, dx2 - dx1):.1f}" height="{STRIP_H}" fill="rgba(128, 128, 128, 0.04)"/>')
        for nx1, nx2 in night_rects:
            svg_parts.append(f'<rect x="{nx1:.1f}" y="{y0}" width="{max(1, nx2 - nx1):.1f}" height="{STRIP_H}" fill="rgba(128, 128, 128, 0.16)"/>')

        if row_idx > 0:
            svg_parts.append(f'<line x1="0" y1="{y0}" x2="{W}" y2="{y0}" stroke="rgba(128,128,128,0.55)" stroke-width="1"/>')

        # GRAPH 1 (TEMP — RED & ORANGE)
        if metric == "temp":
            all_t = slice_data["temp"] + slice_data["feels"]
            if slice_data_2:
                all_t += slice_data_2["temp"]
            min_t = math.floor(min(all_t) - 2)
            max_t = math.ceil(max(all_t) + 2)

            pts_t = make_points(slice_data["temp"], min_t, max_t, top_pad, bot_pad)
            pts_f = make_points(slice_data["feels"], min_t, max_t, top_pad, bot_pad)

            area_str = f"M {pts_t[0][0]:.1f},{bot_pad} " + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts_t) + f" L {pts_t[-1][0]:.1f},{bot_pad} Z"
            svg_parts.append(f'<path d="{area_str}" fill="rgba(239, 68, 68, 0.12)"/>')

            f_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_f)
            svg_parts.append(f'<polyline points="{f_str}" fill="none" stroke="#d97706" stroke-width="1.3" opacity="0.9"/>')

            t_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_t)
            svg_parts.append(f'<polyline points="{t_str}" fill="none" stroke="#ef4444" stroke-width="2.2"/>')

            if slice_data_2:
                pts_t2 = make_points(slice_data_2["temp"], min_t, max_t, top_pad, bot_pad)
                t2_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_t2)
                svg_parts.append(f'<polyline points="{t2_str}" fill="none" stroke="#3b82f6" stroke-width="1.3" stroke-dasharray="3,3"/>')

            temps_raw = slice_data["temp"]
            max_val = int(round(max(temps_raw)))
            min_val = int(round(min(temps_raw)))
            max_idx = temps_raw.index(max(temps_raw))
            min_idx = temps_raw.index(min(temps_raw))

            hx, hy = pts_t[max_idx]
            lx, ly = pts_t[min_idx]
            hx = max(PAD_L + 22, min(W - PAD_R - 22, hx))
            lx = max(PAD_L + 22, min(W - PAD_R - 22, lx))

            svg_parts.append(f'<rect x="{hx-19}" y="{hy-7.5}" width="38" height="15" fill="#1f1f1f" stroke="#ef4444" stroke-width="0.75" rx="3"/>')
            svg_parts.append(f'<text x="{hx}" y="{hy+3.5}" font-size="11" font-weight="600" fill="#ffffff" text-anchor="middle">{max_val}°</text>')

            svg_parts.append(f'<rect x="{lx-19}" y="{ly-7.5}" width="38" height="15" fill="#1f1f1f" stroke="#ef4444" stroke-width="0.75" rx="3"/>')
            svg_parts.append(f'<text x="{lx}" y="{ly+3.5}" font-size="11" font-weight="600" fill="#ffffff" text-anchor="middle">{min_val}°</text>')

            diffs = [f_v - t_v for f_v, t_v in zip(slice_data["feels"], slice_data["temp"])]
            max_diff = max(diffs, key=abs)
            diff_idx = diffs.index(max_diff)
            dx, dy = pts_f[diff_idx]
            dx = max(PAD_L + 22, min(W - PAD_R - 22, dx))

            if (max_idx == diff_idx and abs(dx - hx) < 42) or (min_idx == diff_idx and abs(dx - lx) < 42):
                dx = min(W - PAD_R - 22, dx + 44) if dx + 44 <= W - PAD_R - 22 else max(PAD_L + 22, dx - 44)

            arrow_char = "↑" if max_diff >= 0 else "↓"
            delta_label = f"{arrow_char} {abs(int(round(max_diff)))}°"

            svg_parts.append(f'<rect x="{dx-19}" y="{dy-6.5}" width="38" height="13" fill="#d1d5db" stroke="#94a3b8" stroke-width="0.85" rx="2.5"/>')
            svg_parts.append(f'<text x="{dx}" y="{dy+3.5}" font-size="9.5" font-weight="700" fill="#1f1f1f" text-anchor="middle">{delta_label}</text>')

            svg_parts.append(f'<rect x="{icon_x}" y="{y0+3}" width="18" height="18" rx="3" fill="rgba(128,128,128,0.15)" stroke="currentColor" stroke-width="0.75" opacity="0.85"/>')
            svg_parts.append(f'<g transform="translate({icon_x+9}, {y0+12})">')
            svg_parts.append('<path d="M0 -5 v5.5 a2.5 2.5 0 1 1 -2 0 v-5.5 a2 2 0 1 1 4 0 z" fill="none" stroke="currentColor" stroke-width="1.1"/>')
            svg_parts.append('<circle cx="0" cy="3.5" r="1.1" fill="currentColor"/>')
            svg_parts.append('</g>')
            svg_parts.append(f'<text x="{icon_x + 22}" y="{y0 + 15}" font-size="11" font-weight="600" fill="currentColor">°{st.session_state.unit_temp}</text>')

        # GRAPH 2 (PRECIPITATION — BLUE)
        elif metric == "precip":
            probs = slice_data["precipitation_probability"] if "precipitation_probability" in slice_data else slice_data["precip_prob"]
            mms = slice_data["precipitation"] if "precipitation" in slice_data else slice_data["precip_mm"]
            pts_p = make_points(probs, 0, 100, top_pad, bot_pad)

            area_str = f"M {pts_p[0][0]:.1f},{bot_pad} " + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts_p) + f" L {pts_p[-1][0]:.1f},{bot_pad} Z"
            svg_parts.append(f'<path d="{area_str}" fill="rgba(52, 152, 219, 0.22)"/>')

            p_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_p)
            svg_parts.append(f'<polyline points="{p_str}" fill="none" stroke="#2980b9" stroke-width="2"/>')

            if slice_data_2:
                pts_p2 = make_points(slice_data_2["precip_prob"], 0, 100, top_pad, bot_pad)
                p2_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_p2)
                svg_parts.append(f'<polyline points="{p2_str}" fill="none" stroke="#3b82f6" stroke-width="1.3" stroke-dasharray="3,3"/>')

            max_prob = int(round(max(probs)))
            max_prob_idx = probs.index(max(probs))
            px_prob, py_prob = pts_p[max_prob_idx]
            px_prob = max(PAD_L + 22, min(W - PAD_R - 22, px_prob))

            svg_parts.append(f'<rect x="{px_prob-19}" y="{py_prob-7.5}" width="38" height="15" fill="#1f1f1f" stroke="#2980b9" stroke-width="0.75" rx="3"/>')
            svg_parts.append(f'<text x="{px_prob}" y="{py_prob+3.5}" font-size="11" font-weight="600" fill="#ffffff" text-anchor="middle">{max_prob}%</text>')

            max_mm = max(mms)
            if max_mm > 0.0:
                peak_idx = mms.index(max_mm)
                px_mm, py_mm = pts_p[peak_idx]
                px_mm = max(PAD_L + 22, min(W - PAD_R - 22, px_mm))
                svg_parts.append(f'<rect x="{px_mm-22}" y="{py_mm+4}" width="44" height="15" fill="#1f1f1f" stroke="#2980b9" stroke-width="0.75" rx="3"/>')
                svg_parts.append(f'<text x="{px_mm}" y="{py_mm+15}" font-size="11" font-weight="600" fill="#ffffff" text-anchor="middle">{max_mm:.1f}mm</text>')

            svg_parts.append(f'<rect x="{icon_x}" y="{y0+3}" width="18" height="18" rx="3" fill="rgba(128,128,128,0.15)" stroke="currentColor" stroke-width="0.75" opacity="0.85"/>')
            svg_parts.append(f'<g transform="translate({icon_x+9}, {y0+12})">')
            svg_parts.append('<path d="M0 -5 C-3 -2, -4 0, -4 2 A 4 4 0 0 0 4 2 C 4 0, 3 -2, 0 -5 Z" fill="none" stroke="currentColor" stroke-width="1.1"/>')
            svg_parts.append('</g>')
            svg_parts.append(f'<text x="{icon_x + 22}" y="{y0 + 15}" font-size="11" font-weight="600" fill="currentColor">%</text>')

            total_24h = sum(mms[:24])
            svg_parts.append(f'<rect x="{icon_x - 3}" y="{y0+23}" width="42" height="13" fill="#1f1f1f" stroke="currentColor" stroke-width="0.5" rx="2"/>')
            svg_parts.append(f'<text x="{icon_x + 18}" y="{y0+32}" font-size="8.5" font-weight="600" fill="#ffffff" text-anchor="middle">{total_24h:.1f}mm/24</text>')

        # GRAPH 3 (WIND)
        elif metric == "wind":
            winds_raw = slice_data["wind"]
            gusts_raw = slice_data["gust"]
            all_w = winds_raw + gusts_raw
            if slice_data_2:
                all_w += slice_data_2["wind"]
            max_w = max(25, math.ceil(max(all_w) / 10.0) * 10)

            pts_w = make_points(winds_raw, 0, max_w, top_pad, bot_pad)
            pts_g = make_points(gusts_raw, 0, max_w, top_pad, bot_pad)

            area_str = f"M {pts_w[0][0]:.1f},{bot_pad} " + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts_w) + f" L {pts_w[-1][0]:.1f},{bot_pad} Z"
            svg_parts.append(f'<path d="{area_str}" fill="rgba(100, 116, 139, 0.12)"/>')

            g_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_g)
            svg_parts.append(f'<polyline points="{g_str}" fill="none" stroke="#94a3b8" stroke-width="1.2"/>')

            w_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_w)
            svg_parts.append(f'<polyline points="{w_str}" fill="none" stroke="#64748b" stroke-width="2.2"/>')

            if slice_data_2:
                pts_w2 = make_points(slice_data_2["wind"], 0, max_w, top_pad, bot_pad)
                w2_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_w2)
                svg_parts.append(f'<polyline points="{w2_str}" fill="none" stroke="#64748b" stroke-width="1.3" stroke-dasharray="3,3"/>')

            max_wind_val = max(winds_raw)
            min_wind_val = min(winds_raw)
            max_gust_val = max(gusts_raw)
            max_wind = int(round(max_wind_val))
            min_wind = int(round(min_wind_val))
            max_gust = int(round(max_gust_val))
            max_w_idx = winds_raw.index(max_wind_val)
            min_w_idx = winds_raw.index(min_wind_val)
            max_g_idx = gusts_raw.index(max_gust_val)

            hwx, hwy = pts_w[max_w_idx]
            lwx, lwy = pts_w[min_w_idx]
            hwx = max(PAD_L + 22, min(W - PAD_R - 22, hwx))
            lwx = max(PAD_L + 22, min(W - PAD_R - 22, lwx))

            svg_parts.append(f'<rect x="{hwx-21}" y="{hwy-7.5}" width="42" height="15" fill="#1f1f1f" stroke="#64748b" stroke-width="0.75" rx="3"/>')
            svg_parts.append(f'<text x="{hwx}" y="{hwy+3.5}" font-size="11" font-weight="600" fill="#ffffff" text-anchor="middle">{max_wind}</text>')

            svg_parts.append(f'<rect x="{lwx-21}" y="{lwy-7.5}" width="42" height="15" fill="#1f1f1f" stroke="#64748b" stroke-width="0.75" rx="3"/>')
            svg_parts.append(f'<text x="{lwx}" y="{lwy+3.5}" font-size="11" font-weight="600" fill="#ffffff" text-anchor="middle">{min_wind}</text>')

            sust_thresh = 35.0 if st.session_state.unit_wind == "mph" else 56.0
            gust_thresh = 50.0 if st.session_state.unit_wind == "mph" else 80.0
            is_wind_warning = (max_wind_val >= sust_thresh) or (max_gust_val >= gust_thresh)

            if is_wind_warning:
                warn_txt = f"⚠ G{max_gust}" if max_gust_val >= gust_thresh else f"⚠ {max_wind}"
                svg_parts.append(f'<rect x="{icon_x - 4}" y="{y0+23}" width="44" height="14" fill="#f59e0b" stroke="#1f1f1f" stroke-width="0.9" rx="2.5"/>')
                svg_parts.append(f'<text x="{icon_x + 18}" y="{y0+33}" font-size="9" font-weight="800" fill="#1f1f1f" text-anchor="middle">{warn_txt}</text>')
            else:
                gx, gy = pts_g[max_g_idx]
                gx = max(PAD_L + 20, min(W - PAD_R - 20, gx))

                if abs(gx - hwx) < 44 and abs(gy - hwy) < 18:
                    gx = hwx + 46 if (hwx + 46 <= W - PAD_R - 20) else hwx - 46
                elif abs(gx - lwx) < 44 and abs(gy - lwy) < 18:
                    gx = lwx + 46 if (lwx + 46 <= W - PAD_R - 20) else lwx - 46

                svg_parts.append(f'<rect x="{gx-19}" y="{gy-6.5}" width="38" height="13" fill="#d1d5db" stroke="#94a3b8" stroke-width="0.85" rx="2.5"/>')
                svg_parts.append(f'<text x="{gx}" y="{gy+3.5}" font-size="9.5" font-weight="700" fill="#1f1f1f" text-anchor="middle">{max_gust}</text>')

            for i in range(1, 24, 3):
                ax = x_pos(i)
                ay = y0 + 8
                if abs(ax - (icon_x + 9)) < 35 or abs(ax - hwx) < 28 or abs(ax - lwx) < 28:
                    continue
                deg = slice_data["wind_dir"][i]
                svg_parts.append(
                    f'<g transform="translate({ax:.1f},{ay}) rotate({deg})">'
                    f'<line x1="0" y1="-4" x2="0" y2="4" stroke="#64748b" stroke-width="1.2"/>'
                    f'<polyline points="-2,1.5 0,3.5 2,1.5" fill="none" stroke="#64748b" stroke-width="1.2"/>'
                    f"</g>"
                )

            svg_parts.append(f'<rect x="{icon_x}" y="{y0+3}" width="18" height="18" rx="3" fill="rgba(128,128,128,0.15)" stroke="currentColor" stroke-width="0.75" opacity="0.85"/>')
            svg_parts.append(f'<g transform="translate({icon_x+3}, {y0+6})" stroke="currentColor" stroke-width="1.1" fill="none" stroke-linecap="round">')
            svg_parts.append('<path d="M1 2 h8 c1.5 0 2.5 1 2.5 2.5 s-1 2.5 -2.5 2.5 h-1"/>')
            svg_parts.append('<path d="M3 7 h10 c1.5 0 2.5 1 2.5 2.5 s-1 2.5 -2.5 2.5 h-3"/>')
            svg_parts.append('<path d="M2 12 h6 c1.2 0 2 0.8 2 2 s-0.8 2 -2 2 h-0.5"/>')
            svg_parts.append('</g>')
            svg_parts.append(f'<text x="{icon_x + 22}" y="{y0 + 15}" font-size="11" font-weight="600" fill="currentColor">{st.session_state.unit_wind}</text>')

        # GRAPH 4 (VISIBILITY)
        elif metric == "vis":
            vis_raw = slice_data["vis"]
            all_v = vis_raw + (slice_data_2["vis"] if slice_data_2 else [])
            max_v = max(20, math.ceil(max(all_v) / 5.0) * 5)

            pts_v = make_points(vis_raw, 0, max_v, top_pad, bot_pad)

            is_miles = st.session_state.unit_wind == "mph"
            thresh_caution = 3.1 if is_miles else 5.0
            thresh_danger = 0.6 if is_miles else 1.0
            unit_label = "mi" if is_miles else "km"

            y_caution = bot_pad - (thresh_caution / max_v) * (bot_pad - top_pad)
            y_danger = bot_pad - (thresh_danger / max_v) * (bot_pad - top_pad)

            grad_id = f"visGrad_{row_idx}"
            stop_c = max(0.0, min(1.0, (y_caution - top_pad) / max(bot_pad - top_pad, 1.0)))
            stop_d = max(stop_c, min(1.0, (y_danger - top_pad) / max(bot_pad - top_pad, 1.0)))

            svg_parts.append(
                f'<defs>'
                f'<linearGradient id="{grad_id}" gradientUnits="userSpaceOnUse" x1="0" y1="{top_pad}" x2="0" y2="{bot_pad}">'
                f'<stop offset="0%" stop-color="#16a085" stop-opacity="0.14"/>'
                f'<stop offset="{stop_c*100:.1f}%" stop-color="#16a085" stop-opacity="0.14"/>'
                f'<stop offset="{stop_c*100:.1f}%" stop-color="#d97706" stop-opacity="0.22"/>'
                f'<stop offset="{stop_d*100:.1f}%" stop-color="#d97706" stop-opacity="0.22"/>'
                f'<stop offset="{stop_d*100:.1f}%" stop-color="#ef4444" stop-opacity="0.28"/>'
                f'<stop offset="100%" stop-color="#ef4444" stop-opacity="0.28"/>'
                f'</linearGradient>'
                f'</defs>'
            )

            area_str = f"M {pts_v[0][0]:.1f},{bot_pad} " + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts_v) + f" L {pts_v[-1][0]:.1f},{bot_pad} Z"
            svg_parts.append(f'<path d="{area_str}" fill="url(#{grad_id})"/>')

            v_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_v)
            svg_parts.append(f'<polyline points="{v_str}" fill="none" stroke="#16a085" stroke-width="2.2"/>')

            if slice_data_2:
                pts_v2 = make_points(slice_data_2["vis"], 0, max_v, top_pad, bot_pad)
                v2_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts_v2)
                svg_parts.append(f'<polyline points="{v2_str}" fill="none" stroke="#3b82f6" stroke-width="1.3" stroke-dasharray="3,3"/>')

            max_vis_val = max(vis_raw)
            min_vis_val = min(vis_raw)
            max_vis_int = int(round(max_vis_val))
            min_vis_int = int(round(min_vis_val))
            max_vis_idx = vis_raw.index(max_vis_val)
            min_vis_idx = vis_raw.index(min_vis_val)

            hvx, hvy = pts_v[max_vis_idx]
            lvx, lwy = pts_v[min_vis_idx]
            hvx = max(PAD_L + 22, min(W - PAD_R - 22, hvx))
            lvx = max(PAD_L + 22, min(W - PAD_R - 22, lvx))

            svg_parts.append(f'<rect x="{hvx-19}" y="{hvy-7.5}" width="38" height="15" fill="#1f1f1f" stroke="#16a085" stroke-width="0.75" rx="3"/>')
            svg_parts.append(f'<text x="{hvx}" y="{hvy+3.5}" font-size="11" font-weight="600" fill="#ffffff" text-anchor="middle">{max_vis_int}</text>')

            svg_parts.append(f'<rect x="{lvx-19}" y="{lwy-7.5}" width="38" height="15" fill="#1f1f1f" stroke="#16a085" stroke-width="0.75" rx="3"/>')
            svg_parts.append(f'<text x="{lvx}" y="{lwy+3.5}" font-size="11" font-weight="600" fill="#ffffff" text-anchor="middle">{min_vis_int}</text>')

            if min_vis_val < thresh_caution:
                svg_parts.append(f'<line x1="{PAD_L}" y1="{y_caution:.1f}" x2="{W-PAD_R}" y2="{y_caution:.1f}" stroke="#d97706" stroke-width="1" stroke-dasharray="3,3" opacity="0.85"/>')
                svg_parts.append(f'<line x1="{PAD_L}" y1="{y_danger:.1f}" x2="{W-PAD_R}" y2="{y_danger:.1f}" stroke="#ef4444" stroke-width="1" stroke-dasharray="3,3" opacity="0.9"/>')

                left_clearance = abs(vis_raw[0] - thresh_caution) + abs(vis_raw[1] - thresh_caution)
                right_clearance = abs(vis_raw[-1] - thresh_caution) + abs(vis_raw[-2] - thresh_caution)
                badge_x = (PAD_L + 12) if left_clearance >= right_clearance else (W - PAD_R - 12)

                c_label = "3" if is_miles else "5"
                d_label = "1"

                svg_parts.append(f'<rect x="{badge_x-9}" y="{y_caution-11:.1f}" width="18" height="11" fill="#d1d5db" stroke="#d97706" stroke-width="0.9" rx="2"/>')
                svg_parts.append(f'<text x="{badge_x}" y="{y_caution-3:.1f}" font-size="8.5" font-weight="600" fill="#1f1f1f" text-anchor="middle">{c_label}</text>')

                svg_parts.append(f'<rect x="{badge_x-9}" y="{y_danger-11:.1f}" width="18" height="11" fill="#d1d5db" stroke="#ef4444" stroke-width="0.9" rx="2"/>')
                svg_parts.append(f'<text x="{badge_x}" y="{y_danger-3:.1f}" font-size="8.5" font-weight="600" fill="#1f1f1f" text-anchor="middle">{d_label}</text>')

            svg_parts.append(f'<rect x="{icon_x}" y="{y0+3}" width="18" height="18" rx="3" fill="rgba(128,128,128,0.15)" stroke="currentColor" stroke-width="0.75" opacity="0.85"/>')
            svg_parts.append(f'<g transform="translate({icon_x+9}, {y0+12})">')
            svg_parts.append('<path d="M-5 0 C-2 -3.5, 2 -3.5, 5 0 C 2 3.5, -2 3.5, -5 0 Z" fill="none" stroke="currentColor" stroke-width="1.1"/>')
            svg_parts.append('<circle cx="0" cy="0" r="1.5" fill="currentColor"/>')
            svg_parts.append('</g>')
            svg_parts.append(f'<text x="{icon_x + 22}" y="{y0 + 15}" font-size="11" font-weight="600" fill="currentColor">{unit_label}</text>')

    svg_parts.append("</svg>")
    wrapper_cls = "charts-wrapper charts-desaturated" if is_stale else "charts-wrapper"
    st.markdown(f'<div class="{wrapper_cls}">{"".join(svg_parts)}</div>', unsafe_allow_html=True)


# ==========================================
# UNIFIED TOGGLE BUTTON (LOCKED POSITION AT THE TOP)
# ==========================================
toggle_label = "Hide Extra Metrics (DropBox)" if st.session_state.show_overlay else "🔍 More Metrics (DropBox)"
if st.button(toggle_label, use_container_width=True):
    st.session_state.show_overlay = not st.session_state.show_overlay
    st.rerun()


# ==========================================
# IN-PLACE SLOT SWAP: GRAPHS 1-4 OR OVERLAY GRAPHS
# ==========================================
if not st.session_state.show_overlay:
    build_svg_block(["temp", "precip", "wind", "vis"])
else:
    build_svg_block(["uv", "hum_press"])


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


# 8. Mutually Exclusive Expanders in a Persistent 3-Button Row
if "active_expander" not in st.session_state:
    st.session_state.active_expander = None

col_e1, col_e2, col_e3 = st.columns(3)

with col_e1:
    open_1 = (st.session_state.active_expander == "loc")
    # Using an interactive button to control open state cleanly so other expanders close
    if st.button(T["exp_loc"], use_container_width=True):
        st.session_state.active_expander = None if open_1 else "loc"
        st.rerun()

with col_e2:
    open_2 = (st.session_state.active_expander == "units")
    if st.button(T["exp_units"], use_container_width=True):
        st.session_state.active_expander = None if open_2 else "units"
        st.rerun()

with col_e3:
    open_3 = (st.session_state.active_expander == "guide")
    if st.button(T["exp_guide"], use_container_width=True):
        st.session_state.active_expander = None if open_3 else "guide"
        st.rerun()

# Render only the active drawer contents full width below the button row
if st.session_state.active_expander == "loc":
    with st.container():
        st.markdown(
            """
            <div style="background-color: #1e1e1e; color: #ffffff; border: 1px solid rgba(128,128,128,0.5); border-radius: 6px; padding: 12px; margin-top: 4px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
            """,
            unsafe_allow_html=True,
        )
        st.markdown(f"**{T['loc1_head']}**")
        with st.form(key="loc1_form"):
            q1 = st.text_input("Primary Location", placeholder=T["loc_placeholder"], label_visibility="collapsed")
            if st.form_submit_button(T["set_btn"], use_container_width=True) and q1:
                res1 = resolve_location_string(q1)
                if res1:
                    st.session_state.lat, st.session_state.lon, st.session_state.city = res1
                    st.query_params["lat"] = str(res1[0])
                    st.query_params["lon"] = str(res1[1])
                    st.query_params["city"] = res1[2]
                    st.session_state.active_expander = None
                    st.rerun()
                else:
                    st.error("Location not found.")

        if st.session_state.city != "Peterborough":
            if st.button(T["reset_btn"], use_container_width=True):
                st.session_state.lat = 52.5785
                st.session_state.lon = -0.1285
                st.session_state.city = "Peterborough.xlsx" if False else "Peterborough"
                st.query_params.clear()
                st.session_state.active_expander = None
                st.rerun()

        st.markdown(f"**{T['loc2_head']}**")
        with st.form(key="loc2_form"):
            q2 = st.text_input("2nd Location", placeholder=T["loc_placeholder"], label_visibility="collapsed")
            if st.form_submit_button(T["set_btn"], use_container_width=True) and q2:
                res2 = resolve_location_string(q2)
                if res2:
                    st.session_state.loc2 = {"lat": res2[0], "lon": res2[1], "name": res2[2]}
                    st.session_state.active_expander = None
                    st.rerun()
                else:
                    st.error("2nd Location not found.")

        if st.session_state.loc2:
            if st.button(f"{T['clear_btn']} ({st.session_state.loc2['name']})", use_container_width=True):
                st.session_state.loc2 = None
                st.session_state.active_expander = None
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.active_expander == "units":
    with st.container():
        st.markdown(
            """
            <div style="background-color: #1e1e1e; color: #ffffff; border: 1px solid rgba(128,128,128,0.5); border-radius: 6px; padding: 12px; margin-top: 4px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
            """,
            unsafe_allow_html=True,
        )
        st.markdown(f"**{T['units_head']}**")
        t_choice = st.selectbox("°C / °F", ["C", "F"], index=0 if st.session_state.unit_temp == "C" else 1, key="sel_temp")
        if t_choice != st.session_state.unit_temp:
            st.session_state.unit_temp = t_choice
            st.rerun()
            
        w_choice = st.selectbox("Speed", ["mph", "km/h"], index=0 if st.session_state.unit_wind == "mph" else 1, key="sel_wind")
        if w_choice != st.session_state.unit_wind:
            st.session_state.unit_wind = w_choice
            st.rerun()
            
        lang_keys = ["en", "fr", "de", "es"]
        l_choice = st.selectbox(
            "Language",
            lang_keys,
            index=lang_keys.index(st.session_state.lang),
            format_func=lambda x: x.upper(),
            key="sel_lang"
        )
        if l_choice != st.session_state.lang:
            st.session_state.lang = l_choice
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.active_expander == "guide":
    with st.container():
        st.markdown(
            """
            <div style="background-color: #1e1e1e; color: #ffffff; border: 1px solid rgba(128,128,128,0.5); border-radius: 6px; padding: 12px; margin-top: 4px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
            """,
            unsafe_allow_html=True,
        )
        st.markdown(T["guide_md"])
        st.markdown("</div>", unsafe_allow_html=True)


# 9. Footer Branding (Always Fixed at Screen Bottom)
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
