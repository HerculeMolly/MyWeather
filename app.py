import os
import streamlit as st
import requests
from datetime import datetime

# ==========================================
# PAGE CONFIGURATION & MOBILE OPTIMIZATION
# ==========================================
st.set_page_config(
    page_title="MyWeather",
    page_icon="⛅",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom mobile-first styling (Optimized for iPhone 13 mini & zero-bloat aesthetic)
st.markdown("""
<style>
    /* Hide Streamlit default chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { background-color: #fcfcfc; color: #111111; max-width: 420px; margin: 0 auto; }
    
    /* Clean card wrappers */
    .weather-card {
        background: #ffffff;
        border: 1px solid #eaeaea;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    
    /* Typography */
    h1, h2, h3 { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE & DEFAULTS
# ==========================================
if "location" not in st.session_state:
    st.session_state.location = "Peterborough, UK"
if "lat" not in st.session_state:
    st.session_state.lat = 52.5741
if "lon" not in st.session_state:
    st.session_state.lon = -0.2450
if "wind_unit" not in st.session_state:
    st.session_state.wind_unit = "mph"  # Also controls Visibility unit (mph -> miles)
if "show_overlay" not in st.session_state:
    st.session_state.show_overlay = False

# ==========================================
# WEATHER DATA FETCHING (Open-Meteo API)
# ==========================================
@st.cache_data(ttl=1800)
def fetch_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&"
        f"hourly=temperature_2m,relative_humidity_2m,precipitation_probability,"
        f"precipitation,weathercode,windspeed_10m,windgusts_10m,winddirection_10m,"
        f"visibility,uv_index,surface_pressure&"
        f"daily=sunrise,sunset&"
        f"timezone=auto"
    )
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

data = fetch_weather(st.session_state.lat, st.session_state.lon)

# ==========================================
# HEADER & APP BRANDING
# ==========================================
col_title, col_logo = st.columns([3, 1])
with col_title:
    st.markdown("### MyWeather")
    st.caption(f"📍 {st.session_state.location} &nbsp;|&nbsp; 🕒 {datetime.now().strftime('%H%M %d-%b-%y')}")
with col_logo:
    st.markdown("🐱", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# DATA PARSING & 24-HOUR ROLLING WINDOW
# ==========================================
if data and "hourly" in data:
    hourly = data["hourly"]
    times = hourly["time"]
    
    # Find current hour index using local naive time to match Open-Meteo timezone=auto format
    now_local = datetime.now()
    current_idx = 0
    for i, t_str in enumerate(times):
        dt = datetime.fromisoformat(t_str.replace("Z", ""))
        if dt >= now_local:
            current_idx = max(0, i - 1)
            break
            
    # Slice 24-hour rolling window (anchored at NOW)
    window_slice = slice(current_idx, current_idx + 24)
    t_labels = times[window_slice]
    
    # Helper to sanitize lists against unexpected API None values (prevents TypeErrors)
    def clean_list(lst, default=0.0):
        sliced = lst[window_slice] if lst else []
        return [x if x is not None else default for x in sliced]

    temps = clean_list(hourly.get("temperature_2m", []), 10.0)
    humidity = clean_list(hourly.get("relative_humidity_2m", []), 50.0)
    precip_amt = clean_list(hourly.get("precipitation", []), 0.0)
    wind_spd = clean_list(hourly.get("windspeed_10m", []), 0.0)
    wind_gst = clean_list(hourly.get("windgusts_10m", []), 0.0)
    visibility = clean_list(hourly.get("visibility", []), 10000.0)
    uv_raw = clean_list(hourly.get("uv_index", []), 0.0)
    
    # Unit conversions for UK preference safely
    if st.session_state.wind_unit == "mph":
        wind_spd = [s * 0.621371 for s in wind_spd]
        wind_gst = [g * 0.621371 for g in wind_gst]
        vis_vals = [v / 1609.34 for v in visibility]  # Meters to Miles
        vis_unit = "miles"
    else:
        vis_vals = [v / 1000.0 for v in visibility]    # Meters to KM
        vis_unit = "km"

    # SVG Builder Dimensions & Layout Constants
    W, H = 380, 88  # Taller graph strips for clarity
    pad_l, pad_r = 45, 45
    pad_t, pad_b = 10, 15
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    n_pts = len(t_labels)
    
    def get_x(i):
        return pad_l + (i / max(1, n_pts - 1)) * plot_w

    # ==========================================
    # CORE 4 CHARTS (ZERO-SCROLL VIEW)
    # ==========================================
    
    # 1. TEMPERATURE CHART (Snapped to 5-degree increments, 0°C freezing line)
    min_t = min(temps) if temps else 0
    max_t = max(temps) if temps else 10
    bound_min = 5 * (int(min_t // 5) - (1 if min_t < 0 else 0))
    bound_max = 5 * (int(max_t // 5) + 1)
    if bound_max - bound_min < 10:
        bound_max = bound_min + 10
        
    def scale_t(val):
        return pad_t + plot_h - ((val - bound_min) / max(1, bound_max - bound_min)) * plot_h

    temp_pts = " ".join([f"{get_x(i)},{scale_t(v):.1f}" for i, v in enumerate(temps)])
    zero_y = scale_t(0) if bound_min <= 0 <= bound_max else None

    temp_svg = f"""
    <svg width="100%" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
      <rect x="{pad_l}" y="{pad_t}" width="{plot_w}" height="{plot_h}" fill="#ffffff"/>
      {f'<line x1="{pad_l}" y1="{zero_y}" x2="{W-pad_r}" y2="{zero_y}" stroke="#4a90e2" stroke-width="1" stroke-dasharray="3,3" opacity="0.6"/>' if zero_y else ''}
      <polyline fill="none" stroke="#e056fd" stroke-width="2" points="{temp_pts}"/>
      <text x="{W - pad_r + 6}" y="{pad_t + 12}" font-size="10" fill="#666" font-family="sans-serif">🌡️ {bound_max}°</text>
      <text x="{W - pad_r + 6}" y="{pad_t + plot_h/2 + 3}" font-size="10" fill="#666" font-family="sans-serif">{(bound_max+bound_min)//2}°</text>
      <text x="{W - pad_r + 6}" y="{pad_t + plot_h}" font-size="10" fill="#666" font-family="sans-serif">{bound_min}°</text>
    </svg>
    """
    
    # 2. WIND CHART (Fixed zero-floor, shaded sustained fill, gust line above)
    max_w = max(max(wind_gst or [20]), 20)
    wind_max_scale = 20 * (int(max_w // 20) + 1)
    
    def scale_w(val):
        return pad_t + plot_h - (val / wind_max_scale) * plot_h

    sustained_pts = " ".join([f"{get_x(i)},{scale_w(v):.1f}" for i, v in enumerate(wind_spd)])
    gust_pts = " ".join([f"{get_x(i)},{scale_w(v):.1f}" for i, v in enumerate(wind_gst)])
    sustained_area = f"{pad_l},{pad_t + plot_h} " + sustained_pts + f" {W-pad_r},{pad_t + plot_h}"

    wind_svg = f"""
    <svg width="100%" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
      <polygon points="{sustained_area}" fill="rgba(100,100,100,0.12)" />
      <polyline fill="none" stroke="#999" stroke-width="1.5" stroke-dasharray="2,2" points="{gust_pts}"/>
      <polyline fill="none" stroke="#333" stroke-width="2" points="{sustained_pts}"/>
      <text x="4" y="{pad_t + 12}" font-size="10" fill="#666" font-family="sans-serif">💨 {wind_max_scale}</text>
      <text x="4" y="{pad_t + plot_h/2 + 3}" font-size="10" fill="#666" font-family="sans-serif">{wind_max_scale//2}</text>
      <text x="4" y="{pad_t + plot_h}" font-size="10" fill="#666" font-family="sans-serif">0</text>
    </svg>
    """

    # 3. PRECIPITATION CHART (Shaded fill, peak mm with knockout background gap)
    max_p = max(max(precip_amt or [1.0]), 1.0)
    p_scale = 5 if max_p <= 5 else 10 * (int(max_p // 10) + 1)
    
    def scale_p(val):
        return pad_t + plot_h - (val / p_scale) * plot_h

    precip_pts = " ".join([f"{get_x(i)},{scale_p(v):.1f}" for i, v in enumerate(precip_amt)])
    precip_area = f"{pad_l},{pad_t + plot_h} " + precip_pts + f" {W-pad_r},{pad_t + plot_h}"
    
    peak_p_val = max(precip_amt) if precip_amt else 0
    peak_p_idx = precip_amt.index(peak_p_val) if peak_p_val > 0.1 and peak_p_val in precip_amt else None
    peak_px = get_x(peak_p_idx) if peak_p_idx is not None else 0
    peak_py = scale_p(peak_p_val) if peak_p_idx is not None else 0

    precip_svg = f"""
    <svg width="100%" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
      <polygon points="{precip_area}" fill="rgba(68, 108, 179, 0.2)" />
      <polyline fill="none" stroke="#446cb3" stroke-width="2" points="{precip_pts}"/>
      {f'''
      <rect x="{peak_px - 16}" y="{peak_py - 16}" width="32" height="14" fill="#ffffff" rx="3" opacity="0.9"/>
      <text x="{peak_px}" y="{peak_py - 6}" font-size="9" font-weight="bold" fill="#2c3e50" text-anchor="middle" font-family="sans-serif">{peak_p_val:.1f}mm</text>
      ''' if peak_p_idx is not None and peak_p_val > 0.1 else ''}
      <text x="{W - pad_r + 6}" y="{pad_t + 12}" font-size="10" fill="#666" font-family="sans-serif">🌧️ {p_scale}</text>
      <text x="{W - pad_r + 6}" y="{pad_t + plot_h/2 + 3}" font-size="10" fill="#666" font-family="sans-serif">{p_scale/2:g}</text>
      <text x="{W - pad_r + 6}" y="{pad_t + plot_h}" font-size="10" fill="#666" font-family="sans-serif">0</text>
    </svg>
    """

    # 4. COMBINED HUMIDITY & UV STRIP (0-100% Normalized Scale)
    uv_scaled = [min(100, u * 8.3) for u in uv_raw]
    
    def scale_pct(val):
        return pad_t + plot_h - (val / 100.0) * plot_h

    hum_pts = " ".join([f"{get_x(i)},{scale_pct(v):.1f}" for i, v in enumerate(humidity)])
    uv_pts = " ".join([f"{get_x(i)},{scale_pct(v):.1f}" for i, v in enumerate(uv_scaled)])
    hum_area = f"{pad_l},{pad_t + plot_h} " + hum_pts + f" {W-pad_r},{pad_t + plot_h}"
    uv_area = f"{pad_l},{pad_t + plot_h} " + uv_pts + f" {W-pad_r},{pad_t + plot_h}"

    hum_uv_svg = f"""
    <svg width="100%" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
      <polygon points="{hum_area}" fill="rgba(52, 152, 219, 0.15)" />
      <polygon points="{uv_area}" fill="rgba(241, 196, 15, 0.25)" />
      <polyline fill="none" stroke="#2980b9" stroke-width="1.8" points="{hum_pts}"/>
      <polyline fill="none" stroke="#f39c12" stroke-width="1.8" points="{uv_pts}"/>
      <text x="4" y="{pad_t + 12}" font-size="10" fill="#666" font-family="sans-serif">💧/☀️ 100%</text>
      <text x="4" y="{pad_t + plot_h/2 + 3}" font-size="10" fill="#666" font-family="sans-serif">50%</text>
      <text x="4" y="{pad_t + plot_h}" font-size="10" fill="#666" font-family="sans-serif">0%</text>
    </svg>
    """

    # ==========================================
    # RENDER CORE 4 CHARTS ON MAIN SCREEN
    # ==========================================
    st.markdown('<div class="weather-card">', unsafe_allow_html=True)
    st.markdown("**Temperature (°C)**")
    st.markdown(temp_svg, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="weather-card">', unsafe_allow_html=True)
    st.markdown(f"**Wind & Gusts ({st.session_state.wind_unit})**")
    st.markdown(wind_svg, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="weather-card">', unsafe_allow_html=True)
    st.markdown("**Precipitation (Probability & Intensity)**")
    st.markdown(precip_svg, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="weather-card">', unsafe_allow_html=True)
    st.markdown("**Humidity & Solar UV (0–100% Scale)**")
    st.markdown(hum_uv_svg, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # 1-BUTTON TOGGLE OVERLAY FOR EXTRA CHARTS
    # ==========================================
    if st.button("🔍 More Metrics (Visibility & Pressure)", use_container_width=True):
        st.session_state.show_overlay = not st.session_state.show_overlay
        st.rerun()

    if st.session_state.show_overlay:
        st.markdown("---")
        st.info("📂 **Additional Metrics Overlay Active** (Dimmed view of extra data)")
        
        min_v = min(vis_vals) if vis_vals else 10.0
        min_v_idx = vis_vals.index(min_v) if min_v in vis_vals else 0
        v_max = max(max(vis_vals or [10]), 10)
        
        def scale_v(val):
            return pad_t + plot_h - (val / v_max) * plot_h

        vis_pts = " ".join([f"{get_x(i)},{scale_v(v):.1f}" for i, v in enumerate(vis_vals)])
        min_line_y = scale_v(min_v)
        min_x_pos = get_x(min_v_idx)

        vis_svg = f"""
        <svg width="100%" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
          <line x1="{pad_l}" y1="{min_line_y}" x2="{min_x_pos - 18}" y2="{min_line_y}" stroke="#e74c3c" stroke-width="1.5" stroke-dasharray="3,3"/>
          <line x1="{min_x_pos + 18}" y1="{min_line_y}" x2="{W-pad_r}" y2="{min_line_y}" stroke="#e74c3c" stroke-width="1.5" stroke-dasharray="3,3"/>
          <polyline fill="none" stroke="#16a085" stroke-width="2" points="{vis_pts}"/>
          <rect x="{min_x_pos - 16}" y="{min_line_y - 8}" width="32" height="16" fill="#ffffff" rx="3" opacity="0.9"/>
          <text x="{min_x_pos}" y="{min_line_y + 3}" font-size="9" font-weight="bold" fill="#c0392b" text-anchor="middle" font-family="sans-serif">{min_v:.1f}</text>
          <text x="{W - pad_r + 6}" y="{pad_t + 12}" font-size="10" fill="#666" font-family="sans-serif">👁️ {v_max:.0f}</text>
          <text x="{W - pad_r + 6}" y="{pad_t + plot_h}" font-size="10" fill="#666" font-family="sans-serif">0</text>
        </svg>
        """
        st.markdown(f'<div class="weather-card">**Visibility ({vis_unit})**', unsafe_allow_html=True)
        st.markdown(vis_svg, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # SETTINGS & GUIDE DRAWER
    # ==========================================
    with st.expander("⚙️ Weather Guide & Location Settings"):
        st.write("### Layout & Design Standards")
        st.markdown("""
        * **Core Four on Screen:** Main view locks in Temperature, Wind, Precipitation, and Humidity/Solar UV for instant zero-scroll mobile glanceability.
        * **Overlay Toggle:** Visibility and Pressure live behind a single tap overlay button to keep the screen uncluttered.
        * **Peak mm vs Total:** Precipitation numbers show the **maximum hourly intensity (peak mm/h)** expected during heavy bursts.
        * **Fixed Zero-Floors:** Wind and Precipitation always anchor cleanly at absolute 0.
        """)
        
        st.markdown("### Location & Units")
        new_loc = st.text_input("Location Name", value=st.session_state.location)
        unit_choice = st.selectbox("Wind & Visibility Units", ["mph", "km/h"], index=0 if st.session_state.wind_unit == "mph" else 1)
        
        if st.button("Apply Settings"):
            st.session_state.location = new_loc
            st.session_state.wind_unit = unit_choice
            st.rerun()

else:
    st.error("Unable to load weather data. Please check your network connection.")
