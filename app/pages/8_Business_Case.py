"""Business case & vision - the 'why build this' story, kept separate from the product."""
import streamlit as st

# ---------------- hero --------------------------------------------------
st.markdown("""
<div class="hero">
  <h1>✈️ GreenWings AI - the business case</h1>
  <p class="tag">Reduce <b>operational cost</b> and <b>regulatory exposure</b> in one platform: your flight data in,
  fuel savings, verifier-ready compliance packs and board-level climate actions out.</p>
  <div class="chips">
    <span>💶 Lower fuel OPEX</span>
    <span>📋 EU ETS / CORSIA evidence packs</span>
    <span>🔧 Fleet performance monitoring</span>
    <span>🌍 Full-impact accounting (CO₂ + non-CO₂)</span>
    <span>🤖 AI advisor, human-approved</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.header("The business case - what your P&L and your compliance officer get")
st.markdown("Fuel is the **largest controllable line in airline OPEX (25–30% of operating cost)**, and since "
            "**January 2025 the EU ETS requires monitoring of non-CO₂ effects** (contrails, NOₓ) on intra-European "
            "flights - a new compliance burden with **€100/t excess penalties**. GreenWings addresses both in one workflow:")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("""<div class="card accent-green"><h3>💶 Reduce fuel OPEX</h3>
    <span class="big">1–4.5%</span><br>of fuel burn recoverable: cruise optimization (1–3%) + restoring
    under-performing airframes our monitoring flags (0.5–1.5%). Every 1% on a $500M fuel line = <b>$5M/yr EBIT impact</b>,
    at zero capex.</div>""", unsafe_allow_html=True)
with c2:
    st.markdown("""<div class="card accent-blue"><h3>📋 De-risk compliance</h3>
    <span class="big">7 species</span><br>per flight - CO₂, NOₓ, H₂O, SOₓ, soot + contrail exposure - the evidence
    the <b>EU ETS non-CO₂ MRV (2025)</b> and CORSIA now demand. Downloadable, verifier-ready reports; no penalty
    surprises, no manual spreadsheet audit.</div>""", unsafe_allow_html=True)
with c3:
    st.markdown("""<div class="card accent-red"><h3>🔧 Protect asset availability</h3>
    <span class="big">334 flights</span><br>flagged in the demo fleet (of 8,329): aircraft burning 2–3σ above peers.
    Early performance checks convert unplanned AOG risk into <b>scheduled maintenance</b> - and recovered
    ≈1,040&nbsp;t of fuel.</div>""", unsafe_allow_html=True)
with c4:
    st.markdown("""<div class="card accent-violet"><h3>🌍 Win ESG-driven revenue</h3>
    <span class="big">−62%</span><br>contrail formation in the American Airlines × Google trial, at ~0.3% fuel cost
    on ~2% of flights. Corporate travel RFPs now score carriers on reported emissions - full-impact reporting is a
    <b>sales asset</b>, not a cost.</div>""", unsafe_allow_html=True)

st.write("")

# ---------------- ROI calculator ----------------------------------------
st.subheader("📈 What would it save *your* airline? - try it")
rc1, rc2 = st.columns([1, 2])
with rc1:
    spend = st.slider("Your annual fuel spend (US$ millions)", 50, 2000, 500, step=50)
    eu_share = st.slider("Share of flights under EU ETS (%)", 0, 100, 40, step=5)
with rc2:
    fuel_price = 0.85          # $/kg jet fuel (mid-2020s average)
    ets_price = 75             # €/t CO2 allowance, indicative
    fuel_kg = spend * 1e6 / fuel_price
    lo_kg, hi_kg = fuel_kg * 0.015, fuel_kg * 0.045
    lo_co2, hi_co2 = lo_kg * 3.16 / 1000, hi_kg * 3.16 / 1000
    ets_lo = lo_co2 * ets_price * eu_share / 100
    ets_hi = hi_co2 * ets_price * eu_share / 100
    m1, m2, m3 = st.columns(3)
    m1.metric("Fuel saved / year", f"{lo_kg/1e6:,.0f}–{hi_kg/1e6:,.0f} kt",
              help="1.5–4.5% of burn: cruise optimization + performance-based maintenance recovery")
    m2.metric("Direct fuel savings", f"${lo_kg*fuel_price/1e6:,.1f}–{hi_kg*fuel_price/1e6:,.1f} M/yr")
    m3.metric("CO₂ avoided + ETS allowances", f"{lo_co2/1000:,.0f}–{hi_co2/1000:,.0f} kt · €{ets_lo/1e6:,.1f}–{ets_hi/1e6:,.1f} M",
              help=f"CO₂ = 3.16 × fuel; allowances at €{ets_price}/t on the EU-ETS share you selected")
    st.caption("Indicative ranges from published lever impacts (sources in the mitigation knowledge base) "
               "at $0.85/kg jet fuel - the AI Advisor computes flight-specific numbers from your telemetry.")

st.divider()

# ---------------- how it works -----------------------------------------
st.header("How it works - four steps, human in command")
s1, s2, s3, s4 = st.columns(4)
s1.markdown("""<div class="step"><b>1 · Connect your ops data</b><br>
ACARS fuel telemetry + ADS-B trajectories you already collect - no new sensors, no fleet downtime.
Demo runs on 15,761 real EUROCONTROL flights.</div>""", unsafe_allow_html=True)
s2.markdown("""<div class="step"><b>2 · See cost & footprint together</b><br>
Dashboards break every flight, route and fleet into fuel-per-km and 7 emission species - the numbers
your CFO and your compliance officer both need.</div>""", unsafe_allow_html=True)
s3.markdown("""<div class="step"><b>3 · Ask the AI advisor</b><br>
“Where do we save the most this quarter?” The agent calls grounded tools, ranks levers by ROI and
feasibility, simulates what-ifs before you commit budget.</div>""", unsafe_allow_html=True)
s4.markdown("""<div class="step"><b>4 · Your team approves, then acts</b><br>
Every recommendation is a DRAFT until your analyst signs off - then export the plan and the
verifier-ready compliance pack, full audit trail included.</div>""", unsafe_allow_html=True)

st.write("")
v1, v2 = st.columns([3, 2])
with v1:
    st.subheader("🎬 Why contrails are the surprise lever")
    st.video("https://www.youtube.com/watch?v=xBkK7olwjx0")
    st.caption("Google Research's Project Contrails film - the science behind the −62% trial with American Airlines. "
               "Contrail cirrus warms more than all of aviation's CO₂ (RF 57.4 vs 34.3 mW/m², Lee et al. 2021).")
with v2:
    st.subheader("Why now")
    st.markdown("""
- 🟢 **Jan 2025** - EU ETS **non-CO₂ monitoring (MRV)** became mandatory for intra-EU flights: airlines must
  now track exactly what GreenWings computes.
- 🟢 **2025** - AA × Google trial proves contrail avoidance works **at airline scale** ([Nature Comms Eng](https://www.nature.com/articles/s44172-024-00329-7)).
- 🟢 **2030** - ReFuelEU mandates **6% SAF**; CORSIA offsetting phase 1 in force - every avoided tonne is avoided cost.
- 🟢 Corporate travel buyers increasingly **select carriers on reported emissions** - full-impact reporting is a sales asset.

**The gap:** today's tools give you *one CO₂ number* (ICAO, IATA, Climatiq) or *fuel-only ops advice*
(SkyBreathe). **None** cover non-CO₂ compliance, none recommend, none are agentic.
""")
