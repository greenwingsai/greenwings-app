import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import data, emissions, theme

CACHE = Path(__file__).resolve().parents[1] / "data_cache"

st.title("🧠 Trained Fuel-Burn Model")
st.markdown("""
**Yes - GreenWings contains a trained machine-learning model.** This is the PRC Data Challenge's official
task: predict fuel burn from flight characteristics. We train a gradient-boosting model on the Apr–Aug
flights and evaluate it on the **2,036 Sep–Oct flights it has never seen** - the honest test that mimics
production use on next month's schedule. Its job in the product: **estimate fuel and emissions for
*planned* flights** (schedules, what-ifs, route bids) before they fly, complementing the measured-data
pipeline for flown flights.
""")


@st.cache_resource(show_spinner=False)
def model():
    import joblib
    return joblib.load(CACHE / "fuel_model.joblib")


@st.cache_data(show_spinner=False)
def meta():
    return json.loads((CACHE / "fuel_model_meta.json").read_text())


m = meta()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Test RMSE", f"{m['rmse_kg']:,.0f} kg", help="Root-mean-square error on unseen Sep–Oct flights - the challenge's official metric")
k2.metric("Median error", f"{m['median_ape_pct']}%")
k3.metric("R²", f"{m['r2']:.3f}")
k4.metric("vs factor-table baseline", f"−{m['rmse_improvement_vs_baseline_pct']}% RMSE",
          help=f"Baseline: per-type median fuel-per-km × distance (RMSE {m['baseline_rmse_kg']:,.0f} kg)")
k5.metric("Training flights", f"{m['train_rows']:,}")

st.divider()
c1, c2 = st.columns([3, 2])

with c1:
    st.subheader("Predicted vs actual - unseen Sep–Oct flights")
    sample = pd.DataFrame(m["test_pred_sample"])
    lim = max(sample["actual_kg"].max(), sample["predicted_kg"].max()) * 1.05 / 1000
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines", name="perfect prediction",
                             line=dict(color=theme.MUTED, width=1, dash="dash"), hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=sample["actual_kg"] / 1000, y=sample["predicted_kg"] / 1000, mode="markers",
        name="test flights", marker=dict(color=theme.BLUE, size=7, opacity=0.65,
                                         line=dict(color=theme.SURFACE, width=1)),
        customdata=sample[["aircraft_type", "distance_km"]],
        hovertemplate="%{customdata[0]} · %{customdata[1]:,.0f} km<br>actual %{x:.1f} t · predicted %{y:.1f} t<extra></extra>"))
    theme.layout(fig, height=430)
    fig.update_xaxes(title="actual fuel burn (t)")
    fig.update_yaxes(title="predicted fuel burn (t)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("200-flight sample of the held-out set. Points hug the dashed line across two orders of "
               "magnitude - short-haul A320s to 100-tonne long-haul burns.")

with c2:
    st.subheader("Model card")
    st.markdown(f"""
- **Algorithm:** {m['model']}
- **Target:** {m['target']}
- **Features:** aircraft type, origin & destination airports, great-circle distance, scheduled duration, month, weekday - *only things known before departure*
- **Split:** {m['split']}
- **Test:** {m['test_rows']:,} flights · RMSE {m['rmse_kg']:,.0f} kg · MAE {m['mae_kg']:,.0f} kg

**Honest reading:** aircraft type × distance explains most of fuel burn (that's physics), so the ML model
beats a well-built factor table by {m['rmse_improvement_vs_baseline_pct']}% RMSE - the gain comes from
airport, seasonality and duration effects. With operator data (payload, planned cruise level, winds) the
gap widens substantially; the architecture is ready for those features.
""")

st.divider()

# ---------------- planned-flight estimator ------------------------------
st.subheader("✈️ Try it - estimate a planned flight")
fl = data.flights()
types = sorted(fl["aircraft_type"].unique())
c1, c2, c3, c4 = st.columns(4)
actype = c1.selectbox("Aircraft type", types, index=types.index("A320") if "A320" in types else 0)
dist = c2.slider("Great-circle distance (km)", 200, 12000, 1200, step=100)
month = c3.selectbox("Month", list(range(1, 13)), index=6, format_func=lambda mm: f"{mm:02d}")
airports = c4.selectbox("Route (origin → destination)", [
    "EHAM → LFBO", "EGLL → KJFK", "LFPG → OMDB", "EDDF → LEMD", "LTFM → EGKK"])
o, d = airports.split(" → ")

# scheduled duration from distance at a typical block speed
dur_hr = dist / 780 + 0.6
X = pd.DataFrame([{"aircraft_type": actype, "origin_icao": o, "destination_icao": d,
                   "distance_km": dist, "duration_hr": dur_hr, "month": month, "dow": 2}])
fuel_pred = float(model().predict(X)[0])
fp = emissions.estimate(actype, fuel_pred, dur_hr * 3600)

r1, r2, r3, r4 = st.columns(4)
r1.metric("Predicted fuel burn", f"{fuel_pred:,.0f} kg")
r2.metric("CO₂", f"{fp.co2_kg/1000:,.1f} t")
r3.metric("NOₓ", f"{fp.nox_kg:,.1f} kg")
r4.metric("Full climate impact", f"{fp.co2e_kg_low/1000:,.1f}–{fp.co2e_kg_high/1000:,.1f} t CO₂e",
          help="Range reflects non-CO₂ uncertainty (Lee et al. 2021)")
st.caption("The trained model predicts fuel for the planned flight; the OpenAP emissions engine converts "
           "it to species - the same grounded chain the AI advisor uses. Duration is estimated from "
           "distance at a typical block speed; connect your schedule system for exact block times.")
