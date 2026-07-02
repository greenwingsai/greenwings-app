import json
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import agent_tools, data, maintenance

st.title("🤖 AI Advisor - the agentic core")
st.caption("A Claude agent that plans, calls grounded tools, and explains. It never free-generates a "
           "number: every figure below traces to a visible tool call. Recommendations stay DRAFT until you approve them.")

fl = data.flights()
iv = data.intervals()


@st.cache_data(show_spinner=False)
def _peer_df():
    return maintenance.peer_table(data.flights())


@st.cache_data(show_spinner=False)
def _daily():
    from pathlib import Path as _P
    import pandas as _pd
    return _pd.read_parquet(_P(__file__).resolve().parents[1] / "data_cache" / "daily_emissions.parquet")


runner = agent_tools.ToolRunner(fl, iv, _peer_df(), daily=_daily())

# ---------------- sidebar ----------------------------------------------
st.sidebar.header("Agent settings")
api_key = st.sidebar.text_input("Anthropic API key (optional)", type="password",
                                value=os.environ.get("ANTHROPIC_API_KEY", ""))
mode = "live" if api_key else "demo"
if mode == "demo":
    st.sidebar.info("No API key → **scripted demo mode**: a fixed conversation whose numbers are computed "
                    "live by the same tools the real agent calls. Paste a key to go fully conversational.")
else:
    st.sidebar.success("Live agent mode (Claude tool-calling).")

enriched_ids = sorted(iv["flight_id"].unique())
labels = {
    fid: f"{fid} · {r['aircraft_type']} · {r['origin_icao']}→{r['destination_icao']}"
    for fid, r in fl[fl["flight_id"].isin(enriched_ids)].set_index("flight_id").iterrows()
}
sel = st.sidebar.selectbox("Flight for the demo conversation", enriched_ids,
                           format_func=lambda x: labels.get(x, x))


def run_demo(flight_id):
    with st.spinner("🤖 Agent is planning, calling tools and drafting recommendations…"):
        try:
            st.session_state["events"] = list(agent_tools.scripted_demo(runner, flight_id))
            st.session_state["approvals"] = {}
        except Exception as e:
            st.session_state["events"] = [("text", f"⚠️ Demo failed: {type(e).__name__}: {e}")]


# ---------------- start controls (main page, always visible) ------------
if not st.session_state.get("events"):
    st.info("**How this demo works** - the agent walks the full loop on a real flight: measured footprint → "
            "diagnosis → ranked mitigations (you approve/reject) → what-if simulation → maintenance check. "
            "Every number is computed live by the grounded tools; the tool calls are shown so you can audit them.")
    c1, c2 = st.columns([1, 2])
    if c1.button(f"▶ Run the agent on {sel}", type="primary", use_container_width=True):
        run_demo(sel)
        st.rerun()
    c2.caption("…or type anything in the chat box below - in demo mode it triggers the same walkthrough "
               "for the selected flight; with an API key it becomes a free conversation.")

if st.sidebar.button("▶ Run demo conversation", type="primary"):
    run_demo(sel)
    st.rerun()

# ---------------- chat input (both modes) -------------------------------
q = st.chat_input("Ask about a flight's footprint, mitigations, forecast or maintenance…"
                  if mode == "live" else
                  f"Type anything to run the demo conversation for {sel}…")
if q:
    if mode == "live":
        st.session_state["events"] = [("user_says", q)]
        st.session_state["approvals"] = {}
        with st.spinner("🤖 Agent is planning and calling tools…"):
            try:
                for ev in agent_tools.run_agent([{"role": "user", "content": q}], runner, api_key):
                    st.session_state["events"].append(ev)
            except Exception as e:
                st.session_state["events"].append(("text", f"⚠️ Agent error: {e}"))
        st.rerun()
    else:
        run_demo(sel)
        st.rerun()

events = st.session_state.get("events", [])

# ---------------- render conversation ----------------------------------
rec_counter = 0
for i, ev in enumerate(events):
    kind = ev[0]
    if kind == "user_says":
        with st.chat_message("user"):
            st.markdown(ev[1])
    elif kind == "text":
        with st.chat_message("assistant"):
            st.markdown(ev[1])
    elif kind == "tool":
        _, name, args, result = ev
        with st.chat_message("assistant"):
            with st.expander(f"🛠 tool call → `{name}({json.dumps(args)})`  - click to audit the raw result"):
                st.json(result)
            # HITL: recommendations require explicit approval
            if name == "recommend_mitigations" and "recommendations" in result:
                st.markdown("**Human-in-the-loop review** - each draft lever needs your sign-off:")
                for r in result["recommendations"]:
                    rec_counter += 1
                    key = f"rec_{i}_{r['id']}"
                    cols = st.columns([6, 1, 1])
                    cols[0].markdown(f"**{r['rank']}. {r['name']}** - {r['impact']}")
                    approved = st.session_state.get("approvals", {}).get(key)
                    if cols[1].button("✅ Approve", key=key + "_a"):
                        st.session_state.setdefault("approvals", {})[key] = ("approved", r)
                        st.rerun()
                    if cols[2].button("❌ Reject", key=key + "_r"):
                        st.session_state.setdefault("approvals", {})[key] = ("rejected", r)
                        st.rerun()
                    if approved:
                        state = approved[0]
                        (st.success if state == "approved" else st.error)(
                            f"{state.upper()} by reviewer", icon="✅" if state == "approved" else "❌")

# ---------------- approved report --------------------------------------
approvals = st.session_state.get("approvals", {})
approved = [r for (s, r) in approvals.values() if s == "approved"]
if approved:
    st.divider()
    st.subheader("📄 Reviewed & approved mitigation plan")
    lines = ["# GreenWings AI - approved mitigation plan", ""]
    for r in approved:
        lines += [f"## {r['name']} ({r['category']})",
                  f"- Expected impact: {r['impact']}",
                  f"- Feasibility: {r['feasibility']} · Cost: {r['cost']} · Timescale: {r['timescale']}",
                  f"- Source: {r['source']}"]
        if r.get("trade_off"):
            lines.append(f"- Trade-off: {r['trade_off']}")
        lines.append("")
    lines.append("*Approved via human review in GreenWings AI. Figures grounded in tool outputs; "
                 "non-CO₂ estimates carry higher scientific uncertainty.*")
    report = "\n".join(lines)
    st.markdown(report)
    st.download_button("⬇ Download approved plan (Markdown)", report,
                       file_name="greenwings_mitigation_plan.md")
