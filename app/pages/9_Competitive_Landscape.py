"""Competitive landscape - how GreenWings differs from existing tools."""
import streamlit as st

st.header("Competitive landscape")
st.markdown("Existing tools give airlines either *one CO₂ number* or *fuel-only ops advice*. None cover non-CO₂ "
            "compliance, none recommend ranked actions, and none are agentic with a human in the loop.")

st.markdown("""
| Capability | [ICAO ICEC](https://icec.icao.int/) | [IATA CO2 Connect](https://www.iata.org/en/services/data/environment-sustainability/co2-connect/) | [Google TIM](https://github.com/google/travel-impact-model) | [Climatiq](https://www.climatiq.io/flight-air-cargo-carbon-emissions-api) | [SkyBreathe](https://www.openairlines.com/skybreathe-fuel-efficiency/) | **GreenWings AI** |
|---|---|---|---|---|---|---|
| Non-CO₂ effects (NOₓ, contrails…) | ❌ | ❌ | ⚠️ partial | ❌ | ❌ | ✅ **7 species + contrail risk** |
| Uses *measured* fuel burn | ❌ | ⚠️ | ❌ | ❌ | ✅ | ✅ **ACARS telemetry** |
| EU ETS non-CO₂ MRV support | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Recommends ranked actions | ❌ | ❌ | ❌ | ❌ | ⚠️ fuel only | ✅ **sourced, with trade-offs** |
| What-if simulation | ❌ | ❌ | ❌ | ❌ | ⚠️ | ✅ |
| Predictive-maintenance signal | ❌ | ❌ | ❌ | ❌ | ⚠️ | ✅ |
| GenAI / agentic + human-in-the-loop | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
""")

st.info("GreenWings sits at the intersection none of the incumbents occupy: **full-impact accounting + "
        "actionable, sourced recommendations + agentic workflow with human approval.**")
