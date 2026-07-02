"""Architecture & Responsible AI - how it is built and governed."""
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parents[1] / "assets"

st.header("Under the hood - grounded agentic architecture")
a1, a2 = st.columns([3, 1])
with a1:
    arch = ASSETS / "architecture.png"
    if arch.exists():
        st.image(str(arch),
                 caption="A Claude agent orchestrates four grounded tools; every figure traces to data, "
                         "every recommendation to a human approval")
    else:
        st.info("Architecture diagram not found (assets/architecture.png).")
with a2:
    st.markdown("""
**Anti-hallucination by design**
- All numbers come from **tools**, never the LLM
- CO₂e shown as an honest **uncertainty range**
- Tool-call audit trace on screen
- Declines when data is missing

**Governance**
- Human sign-off before any plan is final
- EU AI Act: decision-support, human authority
- GDPR: aggregate ops data, no PII
""")

st.divider()

with st.expander("🔌 Verified APIs & models this platform builds on", expanded=True):
    st.markdown("""
| Resource | What it provides | How GreenWings uses it |
|---|---|---|
| [OpenAP emission models](https://openap.dev/api/emission.html) | CO₂/H₂O/SOₓ/soot from fuel flow; altitude-corrected NOₓ/CO/HC (BFFM2, ICAO EEDB) | **Core of the footprint estimator** |
| [Google Contrails API / pycontrails](https://developers.google.com/contrails/v1/forecast-description) | ML + physics (CoCiP) contrail forecasts with ECMWF weather | Production path for live contrail-avoidance routing |
| [AA × Google trial](https://www.nature.com/articles/s44172-024-00329-7) | 54–64% contrail cut on ~2% of flights | Grounds the contrail-avoidance lever |
| [ICAO ICEC API](https://www.icao.int/environmental-protection/environmental-tools/icec/api) | Standardised per-passenger CO₂ | CO₂ benchmark / cross-check |
| [EUROCONTROL PRC dataset](https://doi.org/10.59490/joas.2026.8750) | 15,761 flights of ACARS fuel + ADS-B (CC BY 4.0) | The demo's trusted data layer |
""")

with st.expander("🛡️ Responsible AI - the full statement", expanded=True):
    c1, c2, c3 = st.columns(3)
    c1.markdown("""**Reliability**
- Figures grounded via tools (anti-hallucination by architecture)
- CO₂e as a low–central–high range (Lee et al. 2021)
- Unit-validation of source data (we caught the dataset's feet-vs-metres discrepancy)
- Visible tool-call trace per answer""")
    c2.markdown("""**Governance**
- Human review before recommendations are final
- Audit trail: figure → tool → source
- EU AI Act: decision-support tier, human oversight
- GDPR: public/aggregate data, no PII""")
    c3.markdown("""**Ethics & sustainability**
- Non-CO₂ uncertainty stated, never hidden
- Equity: feasibility-scored levers, no penalty for developing markets
- Trade-offs disclosed (SAF land-use, NOₓ–methane, re-route fuel)
- SDG 13 · 9 · 12""")

st.caption("ICAM / BIP Toulouse 2026 · Team: Product Manager · AI Developer · Data Analyst · "
           "Demo data: EUROCONTROL PRC 2025 (CC BY 4.0)")
