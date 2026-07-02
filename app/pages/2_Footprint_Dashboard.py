import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import data, emissions, theme

st.title("🌡️ Full Climate-Footprint Dashboard")
st.caption("Not just CO₂: seven emission species + contrail risk, computed from *measured* ACARS fuel burn "
           "via OpenAP / ICAO Engine Emissions Databank. CO₂e is shown as a range (Lee et al. 2021).")

fl = data.flights()
iv = data.intervals()

enriched_ids = sorted(iv["flight_id"].unique())
labels = {
    fid: f"{fid} · {r['aircraft_type']} · {r['origin_icao']}→{r['destination_icao']} · {r['distance_km']:,.0f} km"
    for fid, r in fl[fl["flight_id"].isin(enriched_ids)].set_index("flight_id").iterrows()
}

st.sidebar.header("Choose a flight")
sel = st.sidebar.selectbox("Flight (trajectory-enriched sample)", enriched_ids,
                           format_func=lambda f: labels.get(f, f))
row = fl[fl["flight_id"] == sel].iloc[0]
ivs = iv[iv["flight_id"] == sel]

fp = emissions.flight_footprint(row, ivs)

# ---------------- KPI row ---------------------------------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Measured fuel burn", f"{fp['fuel_kg']:,.0f} kg")
k2.metric("CO₂", f"{fp['co2_kg']/1000:,.1f} t")
k3.metric("NOₓ", f"{fp['nox_kg']:,.1f} kg")
k4.metric("Total climate impact (central)", f"{fp['co2e_kg_central']/1000:,.1f} t CO₂e",
          help="Range reflects scientific uncertainty on non-CO₂ effects (contrails, NOₓ) - Lee et al. 2021")
k5.metric("Contrail-band flying", f"{fp.get('contrail_share', 0):.0%}",
          help="Share of measured intervals flown in the 8.5–12 km contrail-formation band")
st.caption(f"CO₂e range: **{fp['co2e_kg_low']/1000:,.1f} – {fp['co2e_kg_high']/1000:,.1f} t** "
           f"(low = CO₂-dominated view, high = contrail cirrus fully included) · "
           f"method: {fp['method']} · granularity: {fp['granularity']}")

st.divider()
c1, c2 = st.columns([3, 2])

# ---------------- CO2 vs CO2e range ------------------------------------
with c1:
    st.subheader("The two-thirds most tools ignore")
    bars = [
        ("CO₂ only (what typical calculators report)", fp["co2_kg"], theme.SEQ[2]),
        ("CO₂e - low (non-CO₂ minimal)", fp["co2e_kg_low"], theme.SEQ[3]),
        ("CO₂e - central", fp["co2e_kg_central"], theme.SEQ[4]),
        ("CO₂e - high (contrail cirrus included)", fp["co2e_kg_high"], theme.SEQ[5]),
    ]
    fig = go.Figure(go.Bar(
        y=[b[0] for b in bars][::-1], x=[b[1] / 1000 for b in bars][::-1],
        orientation="h", marker=dict(color=[b[2] for b in bars][::-1], cornerradius=4),
        text=[f"{b[1]/1000:,.1f} t" for b in bars][::-1], textposition="outside",
        textfont=dict(color=theme.INK_2),
        hovertemplate="%{y}: %{x:,.1f} t<extra></extra>",
    ))
    theme.layout(fig, height=330)
    fig.update_xaxes(title="tonnes CO₂-equivalent", range=[0, fp["co2e_kg_high"] / 1000 * 1.25])
    st.plotly_chart(fig, use_container_width=True)
    st.caption("A single hue, light→dark = one magnitude scale. The full-impact figure can be "
               "up to 3× the CO₂-only number - decisions based on CO₂ alone see a third of the problem.")

# ---------------- species table ----------------------------------------
with c2:
    st.subheader("All species (this flight)")
    species = pd.DataFrame([
        ["CO₂", f"{fp['co2_kg']:,.0f} kg", "long-lived warming"],
        ["H₂O (water vapour)", f"{fp['h2o_kg']:,.0f} kg", "warming at altitude; feeds contrails"],
        ["NOₓ", f"{fp['nox_kg']:,.1f} kg", "ozone warming, partial methane offset"],
        ["CO", f"{fp['co_kg']:,.2f} kg", "air quality"],
        ["HC", f"{fp['hc_kg']:,.3f} kg", "air quality"],
        ["SOₓ", f"{fp['sox_kg']:,.2f} kg", "small cooling (aerosol)"],
        ["Soot", f"{fp['soot_kg']*1000:,.1f} g", "warming; contrail ice nuclei"],
        ["Contrail risk", fp.get("contrail_share", 0) and f"{fp['contrail_share']:.0%} of intervals" or "-",
         "largest single warming term when formed"],
    ], columns=["Species", "Amount", "Climate role"])
    st.table(species)
    st.caption("Source: OpenAP emission models (ICAO EEDB, Boeing Fuel Flow Method 2) applied to measured fuel burn.")

st.divider()

# ---------------- flight profile ---------------------------------------
st.subheader("Flight profile - where the contrail risk sits")
traj = data.traj_sample()
tsel = traj[traj["flight_id"] == sel]
if len(tsel):
    fig = go.Figure()
    fig.add_hrect(y0=8.5, y1=12, fillcolor=theme.RED, opacity=0.07, line_width=0)
    fig.add_trace(go.Scatter(
        x=tsel["timestamp"], y=tsel["altitude"] / 1000, mode="lines",
        line=dict(color=theme.BLUE, width=2), name="altitude",
        hovertemplate="%{x|%H:%M} · %{y:.1f} km<extra></extra>",
    ))
    night_iv = ivs[ivs["night"]]
    for r in night_iv.itertuples():
        fig.add_vrect(x0=r.start, x1=r.end, fillcolor=theme.VIOLET, opacity=0.06, line_width=0)
    fig.add_annotation(x=1, y=12, xref="paper", yanchor="bottom", text="contrail-formation band (8.5–12 km)",
                       showarrow=False, font=dict(color=theme.RED, size=11), xanchor="right")
    theme.layout(fig, height=340)
    fig.update_yaxes(title="altitude (km)")
    fig.update_xaxes(title="time (UTC)")
    st.plotly_chart(fig, use_container_width=True)
    if len(night_iv):
        st.caption("Violet shading = night-time intervals (local solar time): contrails formed at night "
                   "warm more because there is no daytime albedo offset.")
else:
    st.info("Trajectory plot available for the 40-flight plotting sample; this flight's intervals are still fully computed above.")

st.divider()

# ---------------- fleet view -------------------------------------------
st.subheader("Fleet view - footprint intensity by aircraft type")
NARROW = {"A20N", "A21N", "A318", "A319", "A320", "A321", "B38M", "B39M", "B737", "B738", "B739", "B752"}
agg = fl.groupby("aircraft_type").agg(
    flights=("flight_id", "size"), med_fpk=("fuel_per_km", "median")).reset_index()
agg = agg[agg["flights"] >= 30].sort_values("med_fpk")
agg["body"] = agg["aircraft_type"].map(lambda t: "Narrow-body" if t in NARROW else "Wide-body / freighter")
agg["co2_per_km"] = agg["med_fpk"] * 3.16

fig = go.Figure()
for body, color in [("Narrow-body", theme.BLUE), ("Wide-body / freighter", theme.AQUA)]:
    sub = agg[agg["body"] == body]
    fig.add_trace(go.Bar(
        x=sub["aircraft_type"], y=sub["co2_per_km"], name=body,
        marker=dict(color=color, cornerradius=4),
        hovertemplate="%{x}: %{y:.1f} kg CO₂/km (median, n=%{customdata:,})<extra></extra>",
        customdata=sub["flights"],
    ))
theme.layout(fig, height=380)
fig.update_yaxes(title="median kg CO₂ per km (whole aircraft)")
fig.update_xaxes(title=None)
st.plotly_chart(fig, use_container_width=True)
st.caption("Whole-aircraft intensity from measured fuel (≥30 flights per type). Wide-bodies burn more per km "
           "but carry far more payload - per-seat comparisons need load-factor data (disclosed limitation).")
