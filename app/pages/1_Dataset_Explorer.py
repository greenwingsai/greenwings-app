import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import data, theme

st.title("📊 Dataset Explorer")
st.caption("EUROCONTROL PRC 2025 Data Challenge - ACARS fuel telemetry fused with ADS-B trajectories (CC BY 4.0)")

fl = data.flights()
iv = data.intervals()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Flights (training, usable)", f"{len(fl):,}")
k2.metric("Fuel intervals (labels)", "131,530")
k3.metric("Aircraft types", fl["aircraft_type"].nunique())
k4.metric("Total measured fuel", f"{fl['fuel_obs_kg'].sum()/1e6:,.1f} kt")
k5.metric("Period", "Apr–Aug 2025")

st.divider()

# ---------------- column dictionary ----------------------------------
st.header("1 · What every column means")
tab1, tab2, tab3, tab4 = st.tabs(["flightlist_*.parquet", "fuel_*.parquet", "flights_*.zip (trajectories)", "airports.parquet"])

with tab1:
    st.markdown("**Flight metadata** - one row per flight (11,037 train / 1,888 rank / 2,836 final)")
    st.table(pd.DataFrame([
        ["flight_id", "string", "Unique anonymised flight identifier (e.g. prc778174030). No airline or tail number - a privacy feature with analytical consequences (see maintenance page)."],
        ["flight_date", "string", "Date of flight (YYYY-MM-DD)"],
        ["aircraft_type", "string", "ICAO type designator (A320, B77W…). Drives which emission model applies."],
        ["takeoff / landed", "datetime", "Block times (UTC) → flight duration"],
        ["origin_icao / origin_name", "string", "Departure airport code + name"],
        ["destination_icao / destination_name", "string", "Arrival airport code + name"],
    ], columns=["Column", "Type", "Meaning & why it matters"]))

with tab2:
    st.markdown("**Fuel labels** - the ground truth: fuel actually consumed per time interval, from ACARS fuel-on-board reports")
    st.table(pd.DataFrame([
        ["idx", "int64", "Row index"],
        ["flight_id", "string", "Joins to the flight list"],
        ["start / end", "datetime", "Interval bounds (5–60 min). Fuel-on-board verified monotonically decreasing."],
        ["fuel_kg", "float64", "Fuel burned in the interval (kg) - the target variable of the original challenge, and the *measured input* to our emissions engine."],
    ], columns=["Column", "Type", "Meaning & why it matters"]))

with tab3:
    st.markdown("**Trajectories** - one parquet per flight; fused ADS-B (dense positions) + ACARS (sparse airspeeds)")
    st.table(pd.DataFrame([
        ["timestamp", "datetime", "Record time (UTC), sub-second for ADS-B"],
        ["latitude / longitude", "float64", "Position - route shape, region, great-circle deviation"],
        ["altitude", "float64", "Barometric altitude (m) - the key variable for contrail-formation risk (8.5–12 km band) and NOₓ altitude correction"],
        ["groundspeed", "float64", "m/s from ADS-B"],
        ["track", "float64", "Track angle (°)"],
        ["vertical_rate", "float64", "Climb/descent rate (m/s) - flight-phase detection"],
        ["mach / TAS / CAS", "float64", "From ACARS only (sparse) - true airspeed feeds the Boeing Fuel Flow Method 2 NOₓ correction"],
        ["source", "string", "'adsb' or 'acars'"],
    ], columns=["Column", "Type", "Meaning & why it matters"]))

with tab4:
    st.markdown("**Airports reference** - 8,787 airports")
    st.table(pd.DataFrame([
        ["icao", "string", "ICAO airport code (EHAM, KJFK…)"],
        ["latitude / longitude", "float64", "Coordinates → great-circle distance per flight"],
        ["elevation", "float64", "Elevation (m, some nulls)"],
    ], columns=["Column", "Type", "Meaning & why it matters"]))

st.divider()

# ---------------- features for the analysis --------------------------
st.header("2 · Features engineered for the GreenWings analysis")
st.markdown("From the raw columns we derive the features each capability needs:")
st.table(pd.DataFrame([
    ["distance_km", "haversine(origin, destination) from airports.parquet", "Footprint intensity (per-km), maintenance peer groups"],
    ["duration_hr", "landed − takeoff", "Fuel-flow normalisation"],
    ["fuel_obs_kg / obs_s", "sum of ACARS interval fuel ÷ observed seconds", "Measured fuel flow (kg/s) → all 7 emission species"],
    ["fuel_per_km", "observed fuel ÷ (distance × coverage)", "THE efficiency metric - powers predictive maintenance"],
    ["altitude_m (per interval)", "mean trajectory altitude within each fuel interval", "Contrail-risk band + NOₓ altitude correction"],
    ["tas_ms (per interval)", "ACARS TAS (fallback: groundspeed)", "Boeing Fuel Flow Method 2 inputs"],
    ["night (per interval)", "local solar hour from mid-interval longitude", "Night contrails warm more (no albedo offset)"],
    ["peer group", "same aircraft_type × distance band", "Maintenance anomaly baseline"],
], columns=["Feature", "How it is computed", "What it powers"]))

st.divider()

# ---------------- dataset shape charts --------------------------------
st.header("3 · The data at a glance")
c1, c2 = st.columns(2)

with c1:
    counts = fl["aircraft_type"].value_counts().head(12).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=counts.values, y=counts.index, orientation="h",
        marker=dict(color=theme.BLUE, cornerradius=4),
        text=[f"{v:,}" for v in counts.values], textposition="outside",
        textfont=dict(color=theme.INK_2),
        hovertemplate="%{y}: %{x:,} flights<extra></extra>",
    ))
    theme.layout(fig, "Flights by aircraft type (top 12)", height=420)
    fig.update_xaxes(title="flights")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("The A320 family dominates (~60% of flights) - typical of European short/medium-haul.")

with c2:
    fig = go.Figure(go.Histogram(
        x=fl["distance_km"], nbinsx=50,
        marker=dict(color=theme.BLUE, line=dict(color=theme.SURFACE, width=1)),
        hovertemplate="%{x} km: %{y:,} flights<extra></extra>",
    ))
    theme.layout(fig, "Route distance distribution", height=420)
    fig.update_xaxes(title="great-circle distance (km)")
    fig.update_yaxes(title="flights")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Mostly intra-European sectors under 3,000 km, with a long-haul tail to ~12,000 km.")

c3, c4 = st.columns(2)
with c3:
    fig = go.Figure(go.Histogram(
        x=iv["dur_s"] / 60, nbinsx=40,
        marker=dict(color=theme.AQUA, line=dict(color=theme.SURFACE, width=1)),
        hovertemplate="%{x} min: %{y:,} intervals<extra></extra>",
    ))
    theme.layout(fig, "Fuel-interval duration (enriched sample)", height=380)
    fig.update_xaxes(title="interval length (minutes)")
    fig.update_yaxes(title="intervals")
    st.plotly_chart(fig, use_container_width=True)

with c4:
    band = iv["altitude_m"].dropna()
    fig = go.Figure(go.Histogram(
        x=band / 1000, nbinsx=40,
        marker=dict(color=theme.AQUA, line=dict(color=theme.SURFACE, width=1)),
        hovertemplate="%{x} km: %{y:,} intervals<extra></extra>",
    ))
    fig.add_vrect(x0=8.5, x1=12, fillcolor=theme.RED, opacity=0.08, line_width=0)
    fig.add_annotation(x=10.25, y=1, yref="paper", text="contrail-formation band",
                       showarrow=False, font=dict(color=theme.RED, size=11))
    theme.layout(fig, "Interval altitudes vs the contrail band", height=380)
    fig.update_xaxes(title="mean altitude (km)")
    fig.update_yaxes(title="intervals")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"{(band.between(8500, 12000).mean()):.0%} of measured cruise intervals sit in the 8.5–12 km "
               "contrail-formation band - why non-CO₂ effects cannot be ignored.")

st.divider()

# ---------------- airports & routes world map --------------------------
st.header("4 · Airports & routes on the world map")

ctl1, ctl2, ctl3 = st.columns([2, 2, 3])
n_flights = ctl1.slider("Number of flights to display", 10, 2000, 300, step=10)
order = ctl2.radio("Pick flights by", ["Longest routes", "Most fuel burned", "Most recent"], horizontal=True)

sort_col = {"Longest routes": "distance_km", "Most fuel burned": "fuel_obs_kg", "Most recent": "flight_date"}[order]
sub = fl.sort_values(sort_col, ascending=False).head(n_flights)

tids = set(data.traj_sample()["flight_id"].unique())
flight_labels = {
    r.flight_id: f"{r.flight_id} · {r.aircraft_type} · {r.origin_icao}→{r.destination_icao} · {r.distance_km:,.0f} km"
                 + (" · 🛰 track" if r.flight_id in tids else "")
    for r in sub.itertuples()
}
sel = ctl3.selectbox("Highlight a flight (searchable)", ["(none)"] + list(flight_labels),
                     format_func=lambda x: flight_labels.get(x, x))

# airports appearing in the selected flights, sized by traffic
codes = pd.concat([sub["origin_icao"], sub["destination_icao"]]).value_counts()
ap = data.airports()
ap_sub = ap[ap["icao"].isin(codes.index)].copy()
ap_sub["n"] = ap_sub["icao"].map(codes)

# route lines (None-separated single trace for performance)
lons, lats = [], []
for r in sub.itertuples():
    lons += [r.origin_longitude, r.dest_longitude, None]
    lats += [r.origin_latitude, r.dest_latitude, None]

# OpenStreetMap data on CARTO's Positron tiles (no API key): raw OSM tiles
# label places in each local language/script, Positron uses Latin/English
# labels and a clean light style that matches the app theme.
fig = go.Figure()
fig.add_trace(go.Scattermap(lon=lons, lat=lats, mode="lines", name="routes",
                            line=dict(width=1, color=theme.BLUE), opacity=0.25, hoverinfo="skip"))
fig.add_trace(go.Scattermap(
    lon=ap_sub["longitude"], lat=ap_sub["latitude"], mode="markers", name="airports",
    marker=dict(color=theme.AQUA, size=(ap_sub["n"] ** 0.5 * 4).clip(6, 22), opacity=0.9),
    customdata=ap_sub[["icao", "n"]],
    hovertemplate="%{customdata[0]} · %{customdata[1]} flight(s)<extra></extra>"))

center = dict(lat=48.0, lon=10.0)
zoom = 2.6
if sel != "(none)":
    r = fl[fl["flight_id"] == sel].iloc[0]
    fig.add_trace(go.Scattermap(
        lon=[r["origin_longitude"], r["dest_longitude"]], lat=[r["origin_latitude"], r["dest_latitude"]],
        mode="lines+markers", name=f"{sel} (great-circle)",
        line=dict(width=3, color=theme.ORANGE), marker=dict(size=12, color=theme.ORANGE),
        hovertemplate=f"{r['origin_icao']} → {r['destination_icao']}<extra>{sel}</extra>"))
    tsel = data.traj_sample()
    tsel = tsel[tsel["flight_id"] == sel]
    if len(tsel):
        fig.add_trace(go.Scattermap(
            lon=tsel["longitude"], lat=tsel["latitude"], mode="lines",
            name=f"{sel} (actual ADS-B track)", line=dict(width=2.5, color=theme.VIOLET),
            hoverinfo="skip"))
    center = dict(lat=float((r["origin_latitude"] + r["dest_latitude"]) / 2),
                  lon=float((r["origin_longitude"] + r["dest_longitude"]) / 2))
    span = max(abs(r["origin_latitude"] - r["dest_latitude"]),
               abs(r["origin_longitude"] - r["dest_longitude"]), 1.0)
    zoom = max(1.2, min(6.0, 5.2 - span / 18))

theme.layout(fig, height=580)
fig.update_layout(
    map=dict(style="carto-positron", center=center, zoom=zoom),
    margin=dict(l=0, r=0, t=30, b=0))
st.plotly_chart(fig, use_container_width=True)

m1, m2, m3 = st.columns(3)
m1.metric("Flights shown", f"{len(sub):,}")
m2.metric("Airports involved", f"{ap_sub['icao'].nunique():,}")
m3.metric("Distance covered", f"{sub['distance_km'].sum()/1000:,.0f} thousand km")
st.caption("OpenStreetMap data (CARTO Positron tiles, English labels) - **scroll to zoom** from continent level down to individual airports. "
           "Aqua markers = airports, sized by traffic in the current selection. Blue lines = origin→destination "
           "routes. Highlight a flight to auto-center on it in orange - flights marked 🛰 also show their "
           "**actual flown ADS-B track in violet** (spot the difference between the planned straight line "
           "and real routing around weather and airspace).")

st.divider()
with st.expander("Show underlying flight-features table"):
    st.dataframe(fl.head(500), use_container_width=True)
