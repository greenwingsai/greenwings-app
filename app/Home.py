"""GreenWings AI - product app (tools only).

The marketing / business-case material lives on the static landing site
(http://localhost:8600). This app is just the working tools; the sidebar logo
links back to the landing. Chrome is hidden and the theme matches the landing
(Oswald headings, Open Sans body, green accent).
"""
from pathlib import Path

import streamlit as st

# DEPLOY: the public landing-site URL (GitHub Pages).
LANDING_URL = "https://greenwingsai.github.io"

st.set_page_config(page_title="GreenWings AI", page_icon="✈️", layout="wide")

# logo at top of the sidebar, links back to the landing site
_logo = Path(__file__).resolve().parent / "assets" / "logo.png"
if _logo.exists():
    try:
        st.logo(str(_logo), link=LANDING_URL, size="large")
    except Exception:
        pass

# ---------------- theme to match the landing site -----------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&family=Oswald:wght@400;500;600;700&display=swap');
:root{ --ink:#0B1220; --muted:#5b6676; --line:#E7E9EE; --accent:#0E9F6E; --accent-ink:#0B7A54; }
html, body, .stApp, [class*="css"]{ font-family:'Open Sans',-apple-system,Segoe UI,Roboto,sans-serif; }
.stApp{ background:#fff; color:var(--ink); }
.stApp h1,.stApp h2,.stApp h3,.stApp h4{ font-family:'Oswald','Open Sans',sans-serif; letter-spacing:-.005em; }
.stApp h1{ font-weight:700; } .stApp h2{ font-weight:600; }
.stApp p,.stApp li{ color:#334155; }
[data-testid="stMetricValue"]{ font-weight:700; color:var(--ink); }
[data-testid="stMetricLabel"]{ color:var(--muted); }
section[data-testid="stSidebar"]{ border-right:1px solid var(--line); background:#FCFCFC; }
[data-testid="stToolbar"]{ display:none; }
#MainMenu{ visibility:hidden; }
footer{ visibility:hidden; }
[data-testid="stDecoration"]{ display:none; }
.block-container{ padding-top:1.4rem; }
hr{ border-color:var(--line); }
/* Back-to-Home link, in normal flow at the top of every page (mobile-safe) */
a.gw-home{ display:inline-block; background:var(--accent); color:#fff !important;
  text-decoration:none; font-family:'Oswald',sans-serif; font-weight:600; font-size:.92rem;
  padding:.45rem 1rem; border-radius:999px; margin-bottom:.4rem; }
a.gw-home:hover{ background:var(--accent-ink); }
</style>
""", unsafe_allow_html=True)

# "Back to Home" button at the top of every page (rendered by the router before the page).
st.markdown(f'<a class="gw-home" href="{LANDING_URL}" target="_self">&larr; Home</a>',
            unsafe_allow_html=True)

# ---------------- tools only (clean URLs, back-link via logo) ------------
pages = [
    st.Page("pages/2_Footprint_Dashboard.py",   title="Footprint Dashboard",    icon="🌡️", default=True),
    st.Page("pages/3_AI_Advisor.py",             title="AI Advisor",             icon="🤖", url_path="advisor"),
    st.Page("pages/4_Predictive_Maintenance.py", title="Predictive Maintenance", icon="🔧", url_path="maintenance"),
    st.Page("pages/5_Compliance_Reports.py",     title="Compliance Reports",     icon="📋", url_path="compliance"),
    st.Page("pages/6_Emissions_Forecast.py",     title="Emissions Forecast",     icon="📈", url_path="forecast"),
    st.Page("pages/7_Fuel_Burn_Model.py",        title="Fuel-Burn Model",        icon="🧠", url_path="fuel"),
    st.Page("pages/1_Dataset_Explorer.py",       title="Dataset Explorer",       icon="📊", url_path="dataset"),
]

pg = st.navigation(pages)
pg.run()
