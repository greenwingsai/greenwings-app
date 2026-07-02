import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import data, maintenance, theme

st.title("🔧 Predictive Maintenance from Fuel-Efficiency Anomalies")
st.markdown("""
**The idea:** an aircraft that burns significantly more fuel than its peers on comparable missions is
telling you something - engine wear, rigging issues, drag from damaged seals. Airlines call this
*Aircraft Performance Monitoring*. GreenWings applies it to this dataset: every flight's **fuel-per-km**
is compared to a **peer group of the same aircraft type in the same distance band**; statistical
outliers become maintenance-check candidates. Fixing them saves fuel, money **and** emissions -
maintenance is a climate lever.
""")


@st.cache_data(show_spinner=False)
def peer_df():
    return maintenance.peer_table(data.flights())


df = peer_df()
summary = maintenance.summarize(df)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Flights analysed", f"{summary['flights_analyzed']:,}")
k2.metric("⚠️ Monitor (z > 2)", f"{summary['flagged_monitor']:,}")
k3.metric("🔴 Inspect (z > 3)", f"{summary['flagged_inspection']:,}")
k4.metric("Recoverable excess fuel", f"{summary['excess_fuel_kg']/1000:,.0f} t",
          help=f"≈ {summary['excess_co2_kg']/1000:,.0f} t CO₂ if flagged flights matched their peer median")

st.divider()

# ---------------- pick a peer group ------------------------------------
st.sidebar.header("Peer group")
types = sorted(df.loc[df["peer_n"] >= maintenance.MIN_PEERS, "aircraft_type"].unique())
actype = st.sidebar.selectbox("Aircraft type", types, index=types.index("A320") if "A320" in types else 0)
sub_t = df[(df["aircraft_type"] == actype) & (df["peer_n"] >= maintenance.MIN_PEERS)]
bins = [b for b in maintenance.BIN_LABELS if b in set(sub_t["dist_bin"].astype(str))]
dist_bin = st.sidebar.selectbox("Distance band (km)", bins)
sub = sub_t[sub_t["dist_bin"].astype(str) == dist_bin]

c1, c2 = st.columns(2)
FLAG_STYLE = {
    "normal": (theme.BLUE, "●"),
    "monitor - schedule performance check": (theme.STATUS["warning"], "▲"),
    "outlier - recommend inspection": (theme.STATUS["critical"], "■"),
}

with c1:
    st.subheader(f"{actype}, {dist_bin} km - fuel-per-km distribution")
    fig = go.Figure(go.Histogram(
        x=sub["fuel_per_km"], nbinsx=35,
        marker=dict(color=theme.BLUE, line=dict(color=theme.SURFACE, width=1)),
        hovertemplate="%{x:.2f} kg/km: %{y} flights<extra></extra>",
    ))
    med, sd = sub["peer_median"].iloc[0], sub["peer_std"].iloc[0]
    fig.add_vline(x=med, line=dict(color=theme.INK_2, width=2), annotation_text="peer median",
                  annotation_font_color=theme.INK_2)
    fig.add_vrect(x0=med + 2 * sd, x1=sub["fuel_per_km"].max() * 1.02,
                  fillcolor=theme.STATUS["warning"], opacity=0.10, line_width=0)
    fig.add_vline(x=med + 3 * sd, line=dict(color=theme.STATUS["critical"], width=1.5, dash="dot"),
                  annotation_text="z = 3 (inspect)", annotation_font_color=theme.STATUS["critical"])
    theme.layout(fig, height=380)
    fig.update_xaxes(title="fuel per km (kg, coverage-normalised)")
    fig.update_yaxes(title="flights")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Every flight vs its peers")
    fig = go.Figure()
    for flag, (color, symbol) in FLAG_STYLE.items():
        s = sub[sub["maintenance_flag"].astype(str) == flag]
        if not len(s):
            continue
        label = {"normal": "normal", "monitor - schedule performance check": "⚠ monitor",
                 "outlier - recommend inspection": "🔴 inspect"}[flag]
        fig.add_trace(go.Scatter(
            x=s["distance_km"], y=s["fuel_per_km"], mode="markers", name=label,
            marker=dict(color=color, size=9 if flag != "normal" else 6,
                        symbol={"●": "circle", "▲": "triangle-up", "■": "square"}[symbol],
                        line=dict(color=theme.SURFACE, width=1)),
            customdata=s[["flight_id", "z_score"]],
            hovertemplate="%{customdata[0]}<br>%{x:,.0f} km · %{y:.2f} kg/km · z=%{customdata[1]:.1f}<extra></extra>",
        ))
    theme.layout(fig, height=380)
    fig.update_xaxes(title="distance (km)")
    fig.update_yaxes(title="fuel per km (kg)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Status colors + distinct marker shapes flag anomalies (never color alone).")

st.divider()
st.subheader("Maintenance-check candidates in this peer group")
flagged = sub[sub["z_score"] > 2].sort_values("z_score", ascending=False)
if len(flagged):
    show = flagged[["flight_id", "flight_date", "origin_icao", "destination_icao", "distance_km",
                    "fuel_per_km", "peer_median", "z_score", "excess_pct", "maintenance_flag"]].copy()
    show.columns = ["flight", "date", "from", "to", "km", "kg/km", "peer median kg/km",
                    "z-score", "excess %", "verdict"]
    st.dataframe(show.round(2), use_container_width=True, hide_index=True)
    worst = flagged.iloc[0]
    st.markdown(f"""
**Reading the top flag:** flight `{worst['flight_id']}` burned **{worst['fuel_per_km']:.2f} kg/km**
against a peer median of **{worst['peer_median']:.2f} kg/km** - **{worst['excess_pct']:.0f}% excess**
(z = {worst['z_score']:.1f}, {int(worst['peer_n'])} peers). In an operator's fleet this pattern triggers
a performance review: engine compressor wash, control-surface rigging check, drag audit. Typical
recovery of 0.5–1.5% fleet fuel burn - an emissions lever that *pays for itself*.
""")
else:
    st.success("No anomalies above z = 2 in this peer group.")

st.divider()
st.subheader("Method & honest limitations")
st.markdown(f"""
- **Method:** {summary['method']}. Fuel-per-km is normalised by interval coverage so partial
  ACARS windows don't bias the metric.
- **Confounders we accept at demo scale:** wind/weather, payload, ATC routing all move fuel-per-km.
  With more data these become model covariates (regression baseline instead of a peer median).
- **Key limitation:** {summary['limitation']}.
- **Why it belongs in a climate tool:** every kg of excess fuel is ~3.16 kg of CO₂ **plus** the
  non-CO₂ effects - the flagged flights above represent ≈ **{summary['excess_co2_kg']/1000:,.0f} t of avoidable CO₂**.
""")
