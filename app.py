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

# Custom mobile-first styling (Ultra-clean stacked strips, zero bulky cards)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { background-color: #ffffff; color: #111111; max-width: 420px; margin: 0 auto; padding: 10px; }
    
    /* Clean strip wrapper replacing heavy cards */
    .metric-strip {
        border-bottom: 1px solid #eaeaea;
        padding: 4px 0;
        margin-bottom: 4px;
    }
    h1, h2, h3 { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE & DEFAULTS
# ==========================================
if "location" not in st.session_state:
    st.session_state.location = "Peterborough"
if "lat" not in st.session_state:
    st.session_state.lat = 52.5741
if "lon" not in st.session_state:
    st.session_state.lon = -0.2450
if "wind_unit" not in st.session_state:
    st.session_state.wind_unit = "mph"
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
# HEADER (Timestamp next to MyWeather on same line)
# ==========================================
col_title, col_time, col_logo = st.col([2.2, 1.3, 0.5]) if hasattr(st, "col") else st.columns([2.2, 1.3, 0.5])
with col_title:
    st.markdown("### MyWeather")
with col_time:
    st.markdown(f"<div style='text-align: right; font-size: 12px; color: #666; padding-top: 10px;'>{datetime.now().strftime('%H%M %d-%b-%y')}</div>", unsafe_allow_html=True)
with col_logo:
    st.markdown("<div style='text-align: right; font-size: 20px; padding-top: 6px;'>🐱</div>", unsafe_allow_html=True)

st.markdown(f"<div style='font-size: 13px; color: #555; margin-bottom: 8px;'>📍 {st.session_state.location}</div>", unsafe_allow_html=True)
st.markdown("---")

# ==========================================
# DATA PARSING & 24-HOUR ROLLING WINDOW
# ==========================================
if data and "hourly" in data:
    hourly = data["hourly"]
    times = hourly["time"]
    
    now_local = datetime.now()
    current_idx = 0
    for i, t_str in enumerate(times):
        dt = datetime.fromisoformat(t_str.replace("Z", ""))
        if dt >= now_local:
            current_idx = max(0, i - 1)
            break
            
    window_slice = slice(current_idx, current_idx + 24)
    t_labels = times[window_slice]
    
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
    
    if st.session_state.wind_unit == "mph":
        wind_spd = [s * 0.621371 for s in wind_spd]
        wind_gst = [g * 0.621371 for g in wind_gst]
        vis_vals = [v / 1609.34 for v in visibility]
        vis_unit = "miles"
    else:
        vis_vals = [v / 1000.0 for v in visibility]
        vis_unit = "km"

    W, H = 380, 75
    pad_l, pad_r = 35, 45
    pad_t, pad_b = 8, 12
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    n_pts = len(t_labels)
    
    def get_x(i):
        return pad_l + (i / max(1, n_pts - 1)) * plot_w

    # ==========================================
    # TIMELINE HEADER ROW (1200, 1600, 2000...)
    # ==========================================
    timeline_svg = f'<svg width="100%" height="22" viewBox="0 0 {W} 22" xmlns="http://www.w3.org/2000/svg">'
    for i, t_str in enumerate(t_labels):
        # Show label every 4 hours for clean spacing
        if i % 4 == 0:
            dt_obj = datetime.fromisoformat(t_str.replace("Z", ""))
            lbl = dt_obj.strftime("%H%M")
            x_pos = get_x(i)
            timeline_svg += f'<text x="{x_pos}" y="14" font-size="9" fill="#888" text-anchor="middle" font-family="sans-serif">{lbl}</text>'
    timeline_svg += '</svg>'
    
    st.markdown(timeline_svg, unsafe_allow_html=True)

    # ==========================================
    # 1. TEMPERATURE STRIP
    # ==========================================
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
      {f'<line x1="{pad_l}" y1="{zero_y}" x2="{W-pad_r}" y2="{zero_y}" stroke="#4a90e2" stroke-width="0.8" stroke-dasharray="2,2" opacity="0.5"/>' if zero_y else ''}
      <polyline fill="none" stroke="#e056fd" stroke-width="1.8" points="{temp_pts}"/>
      <text x="335" y="{pad_t + 10}" font-size="9" fill="#666" font-family="sans-serif">{bound_max}°</text>
      <text x="335" y="{pad_t + plot_h}" font-size="9" fill="#666" font-family="sans-serif">{bound_min}°</text>
      <text x="6" y="{pad_t + 12}" font-size="12">🔆</text>
    </svg>
    """
    st.markdown(temp_svg, unsafe_allow_html=True)

    # ==========================================
    # 2. HUMIDITY & SOLAR UV STRIP
    # ==========================================
    uv_scaled = [min(100, u * 8.3) for u in uv_raw]
    
    def scale_pct(val):
        return pad_t + plot_h - (val / 100.0) * plot_h

    hum_pts = " ".join([f"{get_x(i)},{scale_pct(v):.1f}" for i, v in enumerate(humidity)])
    uv_pts = " ".join([f"{get_x(i)},{scale_pct(v):.1f}" for i, v in enumerate(uv_scaled)])

    hum_uv_svg = f"""
    <svg width="100%" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
      <polyline fill="none" stroke="#2980b9" stroke-width="1.5" points="{hum_pts}"/>
      <polyline fill="none" stroke="#f39c12" stroke-width="1.5" points="{uv_pts}"/>
      <text x="335" y="{pad_t + 10}" font-size="9" fill="#666" font-family="sans-serif">100%</text>
      <text x="335" y="{pad_t + plot_h}" font-size="9" fill="#666" font-family="sans-serif">0%</text>
      <text x="6" y="{pad_t + 12}" font-size="12">💧</text>
    </svg>
    """
    st.markdown(hum_uv_svg, unsafe_allow_html=True)

    # ==========================================
    # 3. WIND & GUSTS STRIP
    # ==========================================
    max_w = max(max(wind_gst or [20]), 20)
    wind_max_scale = 20 * (int(max_w // 20) + 1)
    
    def scale_w(val):
        return pad_t + plot_h - (val / wind_max_scale) * plot_h

    sustained_pts = " ".join([f"{get_x(i)},{scale_w(v):.1f}" for i, v in enumerate(wind_spd)])
    gust_pts = " ".join([f"{get_x(i)},{scale_w(v):.1f}" for i, v in enumerate(wind_gst)])

    wind_svg = f"""
    <svg width="100%" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
      <polyline fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="2,2" points="{gust_pts}"/>
      <polyline fill="none" stroke="#333" stroke-width="1.8" points="{sustained_pts}"/>
      <text x="335" y="{pad_t + 10}" font-size="9" fill="#666" font-family="sans-serif">{wind_max_scale}</text>
      <text x="335" y="{pad_t + plot_h}" font-size="9" fill="#666" font-family="sans-serif">0</text>
      <text x="6" y="{pad_t + 12}" font-size="12">💨</text>
    </svg>
    """
    st.markdown(wind_svg, unsafe_allow_html=True)

    # ==========================================
    # 4. PRECIPITATION STRIP
    # ==========================================
    max_p = max(max(precip_amt or [1.0]), 1.0)
    p_scale = 5 if max_p <= 5 else 10 * (int(max_p // 10) + 1)
    
    def scale_p(val):
        return pad_t + plot_h - (val / p_scale) * plot_h

    precip_pts = " ".join([f"{get_x(i)},{scale_p(v):.1f}" for i, v in enumerate(precip_amt)])
    peak_p_val = max(precip_amt) if precip_amt else 0
    peak_p_idx = precip_amt.index(peak_p_val) if peak_p_val > 0.1 and peak_p_val in precip_amt else None
    peak_px = get_x(peak_p_idx) if peak_p_idx is not None else 0
    peak_py = scale_p(peak_p_val) if peak_p_idx is not None else 0

    precip_svg = f"""
    <svg width="100%" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
      <polyline fill="none" stroke="#446cb3" stroke-width="1.8" points="{precip_pts}"/>
      {f'''
      <rect x="{peak_px - 14}" y="{peak_py - 14}" width="28" height="12" fill="#ffffff" rx="2" opacity="0.9"/>
      <text x="{peak_px}" y="{peak_py - 5}" font-size="8" font-weight="bold" fill="#2c3e50" text-anchor="middle" font-family="sans-serif">{peak_p_val:.1f}mm</text>
      ''' if peak_p_idx is not None and peak_p_val > 0.1 else ''}
      <text x="335" y="{pad_t + 10}" font-size="9" fill="#666" font-family="sans-serif">{p_scale}</text>
      <text x="335" y="{pad_t + plot_h}" font-size="9" fill="#666" font-family="sans-serif">0</text>
      <text x="6" y="{pad_t + 12}" font-size="12">👁️</text>
    </svg>
    """
    st.markdown(precip_svg, unsafe_allow_html=True)

    # ==========================================
    # 1-BUTTON TOGGLE OVERLAY FOR EXTRA CHARTS
    # ==========================================
    st.markdown("---")
    if st.button("🔍 More Metrics (Visibility & Pressure)", use_container_width=True):
        st.session_state.show_overlay = not st.session_state.show_overlay
        st.rerun()

    if st.session_state.show_overlay:
        st.info("📂 **Additional Metrics Overlay Active**")
        min_v = min(vis_vals) if vis_vals else 10.0
        v_max = max(max(vis_vals or [10]), 10)
        
        def scale_v(val):
            return pad_t + plot_h - (val / v_max) * plot_h

        vis_pts = " ".join([f"{get_x(i)},{scale_v(v):.1f}" for i, v in enumerate(vis_vals)])
        vis_svg = f"""
        <svg width="100%" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
          <polyline fill="none" stroke="#16a085" stroke-width="1.8" points="{vis_pts}"/>
          <text x="335" y="{pad_t + 10}" font-size="9" fill="#666" font-family="sans-serif">{v_max:.0f}</text>
          <text x="335" y="{pad_t + plot_h}" font-size="9" fill="#666" font-family="sans-serif">0</text>
          <text x="6" y="{pad_t + 12}" font-size="12">👁️</text>
        </svg>
        """
        st.markdown(vis_svg, unsafe_allow_html=True)

    # ==========================================
    # SETTINGS & GUIDE DRAWER
    # ==========================================
    with st.expander("⚙️ Weather Guide & Location Settings"):
        new_loc = st.text_input("Location Name", value=st.session_state.location)
        unit_choice = st.selectbox("Wind & Visibility Units", ["mph", "km/h"], index=0 if st.session_state.wind_unit == "mph" else 1)
        
        if st.button("Apply Settings"):
            st.session_state.location = new_loc
            st.session_state.wind_unit = unit_choice
            st.rerun()

else:
    st.error("Unable to load weather data. Please check your network connection.")
