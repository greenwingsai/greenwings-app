import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import data, forecast, theme

st.title("📈 Emissions Trend Forecast")
st.markdown("""
**Plan the budget, the allowances and the board narrative before the year happens.** GreenWings fits the
trend in your **measured** emissions intensity and projects it over every planning horizon you use -
daily ops, weekly review, monthly reporting, quarterly board pack, and the 1–5 year strategy view where
regulation (ReFuelEU SAF) and GreenWings levers bend the curve.
""")


@st.cache_data(show_spinner=False)
def daily():
    return pd.read_parquet(Path(__file__).resolve().parents[1] / "data_cache" / "daily_emissions.parquet")


d = daily()
f = forecast.fit(d)
mean_int = d["co2_per_km_adj"].mean()
trend_m = f.coef[1] * 30 / mean_int * 100

# ---------------- activity assumption -----------------------------------
st.sidebar.header("Your fleet's activity")
fl = data.flights()
med_sector = float(fl["distance_km"].median())
fpd = st.sidebar.slider("Flights per day", 20, 500, 80, step=10)
sector = st.sidebar.slider("Average sector length (km)", 300, 6000, int(round(med_sector, -2)), step=100)
km_day = fpd * sector
st.sidebar.caption(f"= {km_day/1000:,.0f} thousand km flown per day. The model forecasts **intensity** "
                   "(kg CO₂ per km, mix-adjusted) from the measured data and scales it by this activity.")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Observed period", f"{d['date'].min():%d %b} – {d['date'].max():%d %b %Y}",
          help="EUROCONTROL PRC monitored fleet, 181 days of measured fuel")
k2.metric("Fleet CO₂ intensity (mix-adjusted)", f"{mean_int:,.1f} kg/km")
k3.metric("Fitted intensity trend", f"{trend_m:+.2f} %/month",
          help="OLS trend on the mix-adjusted intensity; weekday seasonality removed")
k4.metric("Your projected CO₂ (next 12 months)",
          f"{forecast.predict_daily(f, 365, km_day)['co2_kg'].sum()/1e6:,.2f} kt")

st.divider()

# ---------------- observed intensity + fit ------------------------------
st.subheader("What the model learns from - measured intensity, not raw totals")
import numpy as np
Xh = forecast._design(d["date"], f.t0)
fitted = Xh @ f.coef
fig = go.Figure()
fig.add_trace(go.Scatter(x=d["date"], y=d["co2_per_km_adj"], mode="markers", name="daily observed",
                         marker=dict(color=theme.SEQ[1], size=5),
                         hovertemplate="%{x|%d %b}: %{y:.1f} kg/km<extra></extra>"))
fig.add_trace(go.Scatter(x=d["date"], y=fitted, mode="lines", name="fitted trend + weekday pattern",
                         line=dict(color=theme.BLUE, width=2),
                         hovertemplate="%{x|%d %b}: %{y:.1f} kg/km<extra></extra>"))
theme.layout(fig, height=330)
fig.update_yaxes(title="kg CO₂ per flown km (mix-adjusted)")
st.plotly_chart(fig, use_container_width=True)
st.caption("Why intensity? The monitored sample's daily volume and fleet mix follow crowdsourced data "
           "coverage (145 flights/day in April vs 59 in August), so raw totals would forecast the data "
           "collection, not the flying. Intensity per km at fixed fleet-mix weights removes both effects - "
           "we caught and removed a coverage artifact that faked a −3%/month 'improvement'.")

st.divider()

# ---------------- horizon forecasts -------------------------------------
st.subheader("Forecast by planning horizon")
horizon = st.radio("Horizon", list(forecast.HORIZONS.keys()), horizontal=True, label_visibility="collapsed")

if horizon not in forecast.SCENARIO_HORIZONS:
    spec = forecast.HORIZONS[horizon]
    pred = forecast.predict_daily(f, spec["days"], km_day)
    agg = forecast.aggregate(pred, spec["freq"])
    unit = 1000.0
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.concat([agg["date"], agg["date"][::-1]]),
        y=pd.concat([agg["hi"] / unit, agg["lo"][::-1] / unit]),
        fill="toself", fillcolor="rgba(42,120,214,0.12)", line=dict(width=0),
        name="95% interval", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=agg["date"], y=agg["co2_kg"] / unit, mode="lines+markers",
                             name="forecast", line=dict(color=theme.BLUE, width=2),
                             marker=dict(size=8),
                             hovertemplate="%{x|%d %b %Y}: %{y:,.1f} t CO₂<extra></extra>"))
    theme.layout(fig, f"{horizon} - tonnes CO₂ for your activity level", height=380)
    fig.update_yaxes(title="tonnes CO₂ per period")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Statistical regime: OLS trend + weekday seasonality on measured intensity, 95% prediction "
               "interval from residual variance. The fitted trend is held constant beyond one observed-sample "
               "length - a short sample must not dictate a long extrapolation.")
    with st.expander("Table view"):
        show = agg.assign(period=agg["date"].dt.date, co2_t=(agg["co2_kg"]/1000).round(1),
                          low_t=(agg["lo"]/1000).round(1), high_t=(agg["hi"]/1000).round(1))
        st.dataframe(show[["period", "co2_t", "low_t", "high_t"]], hide_index=True, use_container_width=True)
else:
    periods = 2 if horizon.startswith("6-month") else 1
    years = 3 if horizon.startswith("6-month") else 5
    sc = forecast.yearly_scenarios(f, km_day, years=years, periods_per_year=periods)
    if periods == 2:
        sc["label"] = [f"H{int(p % 2) + 1} {int(y)}" for y, p in zip(sc["year"], sc["period"])]
    else:
        sc["label"] = sc["year"].astype(int).astype(str)
    unit = 1000.0
    fig = go.Figure()
    for col, name, color in [("bau_kg", "Business as usual (+2%/yr traffic)", theme.YELLOW),
                             ("saf_kg", "+ ReFuelEU SAF mandate", theme.AQUA),
                             ("gw_kg", "+ GreenWings levers", theme.GREEN)]:
        fig.add_trace(go.Scatter(x=sc["label"], y=sc[col] / unit, mode="lines+markers", name=name,
                                 line=dict(color=color, width=2), marker=dict(size=8),
                                 hovertemplate="%{x}: %{y:,.0f} t CO₂<extra>" + name + "</extra>"))
    theme.layout(fig, f"{horizon} - scenario projections (tonnes CO₂)", height=420)
    fig.update_yaxes(title="tonnes CO₂ per period")
    st.plotly_chart(fig, use_container_width=True)

    total_saving = sc["gw_saving_kg"].sum() / 1000
    ets_value = total_saving * 75
    c1, c2, c3 = st.columns(3)
    c1.metric("GreenWings levers vs SAF-only", f"−{total_saving:,.0f} t CO₂",
              help="Cumulative over the horizon: cruise optimization + performance-based maintenance, ramping 1.5% → 4.5%")
    c2.metric("Allowance value @ €75/t", f"€{ets_value/1e6:,.1f} M")
    c3.metric("Fuel cost avoided @ $0.85/kg", f"${total_saving/3.16*0.85/1e3*1000/1e6:,.1f} M")
    st.caption("Scenario regime - 6.5 months of data cannot identify multi-year trends, so long horizons "
               "combine the fitted baseline with **published** drivers: EUROCONTROL STATFOR base traffic "
               "growth (+2%/yr), the ReFuelEU SAF blending mandate (2% 2025 → 6% 2030, ~80% lifecycle CO₂ "
               "cut per SAF-kg), and the GreenWings mitigation levers from the knowledge base. "
               "The gap between the aqua and green lines is the platform's pitch, in tonnes.")
    with st.expander("Table view"):
        show = sc.assign(BAU_t=(sc["bau_kg"]/1000).round(0), SAF_t=(sc["saf_kg"]/1000).round(0),
                         GreenWings_t=(sc["gw_kg"]/1000).round(0), saving_t=(sc["gw_saving_kg"]/1000).round(0))
        st.dataframe(show[["label", "BAU_t", "SAF_t", "GreenWings_t", "saving_t"]],
                     hide_index=True, use_container_width=True)

st.divider()
st.markdown("""
**Method & honest limits** - The statistical model is deliberately simple (OLS trend + weekday
seasonality): with 181 days of history, a heavier model would overfit and impress no verifier. Prediction
intervals assume independent residuals. Annual seasonality (winter ops, summer peaks) **cannot** be learned
from one partial year - that is exactly why horizons beyond ~6 months switch to published scenario drivers
instead of pretending the regression knows the future. In production, rolling data continuously re-fits the
model and tightens the intervals.
""")
