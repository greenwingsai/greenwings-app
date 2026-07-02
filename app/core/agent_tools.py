"""Agentic layer: Claude tool-calling over the grounded tools.

Anti-hallucination by design: the system prompt forbids free-generated
figures; every number the agent states must come from a tool result, and the
UI displays the tool-call trace so users can audit each figure's origin.
"""
import json
import os

import pandas as pd

from core import emissions, maintenance, mitigation_kb

# Valid Anthropic model id (the previous "claude-sonnet-5" was a placeholder and 404s).
# Override at deploy time with the ANTHROPIC_MODEL env var / Streamlit secret if desired.
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = """You are GreenWings AI, an aviation climate-impact advisor for airline
sustainability teams, regulators and researchers.

HARD RULES:
- Every quantitative figure (kg, %, CO2e, z-scores) MUST come from a tool result in this
  conversation. Never estimate numbers yourself. If a tool cannot provide it, say so.
- Always mention that non-CO2 effects (contrails, NOx) carry higher scientific uncertainty
  than CO2, and present CO2e as the low-central-high range the estimator returns.
- Recommendations are DRAFTS for human review - end recommendation lists by noting they
  require sign-off by the responsible analyst.
- Be concise and jury-friendly: explain in business/impact terms, cite the lever's source.
"""

TOOLS = [
    {
        "name": "estimate_footprint",
        "description": "Compute the full climate footprint (CO2, H2O, NOx, CO, HC, SOx, soot, "
                       "contrail risk, CO2e range) of a flight in the dataset from its observed "
                       "ACARS fuel burn, using OpenAP/ICAO emission models.",
        "input_schema": {
            "type": "object",
            "properties": {"flight_id": {"type": "string", "description": "dataset flight id, e.g. prc778174030"}},
            "required": ["flight_id"],
        },
    },
    {
        "name": "recommend_mitigations",
        "description": "Rank mitigation levers from the curated, literature-grounded knowledge base.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dominant_forcers": {"type": "array", "items": {"type": "string", "enum": ["co2", "contrails", "nox", "soot"]},
                                     "description": "which forcers dominate the footprint being mitigated"},
                "max_levers": {"type": "integer", "default": 5},
            },
        },
    },
    {
        "name": "simulate_scenario",
        "description": "What-if: apply a mitigation scenario to a flight's baseline footprint and "
                       "return before/after values. Scenarios: saf_30, saf_50, contrail_reroute, "
                       "cruise_opt, fleet_renewal, maintenance_fix.",
        "input_schema": {
            "type": "object",
            "properties": {"flight_id": {"type": "string"}, "scenario_id": {"type": "string"}},
            "required": ["flight_id", "scenario_id"],
        },
    },
    {
        "name": "forecast_emissions",
        "description": "Forecast the monitored fleet's CO2 emissions trend. Statistical (OLS on measured "
                       "mix-adjusted intensity) for short horizons; published scenario drivers (EUROCONTROL "
                       "traffic growth, ReFuelEU SAF, GreenWings levers) for multi-year horizons.",
        "input_schema": {
            "type": "object",
            "properties": {
                "horizon": {"type": "string",
                            "enum": ["Daily (next 14 days)", "Weekly (next 12 weeks)",
                                     "Monthly (next 12 months)", "Quarterly (next 8 quarters)",
                                     "6-month blocks (3 years)", "Yearly (5 years)"]},
                "km_per_day": {"type": "number", "description": "fleet activity in flown km/day (optional; "
                                                                "defaults to the monitored fleet's median)"},
            },
            "required": ["horizon"],
        },
    },
    {
        "name": "check_maintenance",
        "description": "Compare a flight's fuel-per-km to its peer group (same aircraft type, "
                       "similar distance) and return the predictive-maintenance verdict; or pass "
                       "no flight_id for the fleet-level summary.",
        "input_schema": {
            "type": "object",
            "properties": {"flight_id": {"type": "string", "description": "omit for fleet summary"}},
        },
    },
]


class ToolRunner:
    """Executes tool calls against the cached dataset."""

    def __init__(self, flights: pd.DataFrame, intervals: pd.DataFrame, peer_df: pd.DataFrame,
                 daily: pd.DataFrame | None = None):
        self.flights = flights
        self.intervals = intervals
        self.peer_df = peer_df
        self.daily = daily

    def _flight(self, flight_id: str) -> pd.Series | None:
        rows = self.flights[self.flights["flight_id"] == flight_id]
        return rows.iloc[0] if len(rows) else None

    def footprint(self, flight_id: str) -> dict:
        row = self._flight(flight_id)
        if row is None:
            return {"error": f"flight {flight_id} not in the training dataset"}
        ivs = self.intervals[self.intervals["flight_id"] == flight_id]
        result = emissions.flight_footprint(row, ivs if len(ivs) else None)
        result.update(
            flight_id=flight_id,
            route=f"{row['origin_icao']} -> {row['destination_icao']}",
            distance_km=round(float(row["distance_km"]), 0),
            data_source="ACARS observed fuel burn + OpenAP (ICAO Engine Emissions Databank)",
        )
        return result

    def run(self, name: str, args: dict) -> dict:
        if name == "estimate_footprint":
            return self.footprint(args["flight_id"])
        if name == "recommend_mitigations":
            return {"recommendations": mitigation_kb.recommend(
                args.get("dominant_forcers"), args.get("max_levers", 5)),
                "status": "DRAFT - requires human review"}
        if name == "simulate_scenario":
            base = self.footprint(args["flight_id"])
            if "error" in base:
                return base
            return mitigation_kb.simulate(base, args["scenario_id"])
        if name == "forecast_emissions":
            if self.daily is None:
                return {"error": "daily emissions series not loaded"}
            from core import forecast
            return forecast.summary_for_agent(self.daily, args["horizon"], args.get("km_per_day"))
        if name == "check_maintenance":
            fid = args.get("flight_id")
            if fid:
                return maintenance.check_flight(self.peer_df, fid)
            return maintenance.summarize(self.peer_df)
        return {"error": f"unknown tool {name}"}


def run_agent(user_messages: list[dict], runner: ToolRunner, api_key: str,
              max_turns: int = 8):
    """Full agentic loop. Yields ('tool', name, args, result) and ('text', str) events."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    messages = list(user_messages)
    for _ in range(max_turns):
        resp = client.messages.create(
            model=MODEL, max_tokens=1500, system=SYSTEM_PROMPT,
            tools=TOOLS, messages=messages,
        )
        tool_results = []
        for block in resp.content:
            if block.type == "text" and block.text.strip():
                yield ("text", block.text)
            elif block.type == "tool_use":
                result = runner.run(block.name, dict(block.input))
                yield ("tool", block.name, dict(block.input), result)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": json.dumps(result)})
        if resp.stop_reason != "tool_use":
            return
        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content": tool_results})


def scripted_demo(runner: ToolRunner, flight_id: str):
    """No-API-key fallback: a fixed conversation whose NUMBERS are computed live
    by the same tools the real agent would call."""
    fp = runner.run("estimate_footprint", {"flight_id": flight_id})
    yield ("user_says", f"What is the full climate footprint of flight {flight_id}, and how can we reduce it?")
    yield ("tool", "estimate_footprint", {"flight_id": flight_id}, fp)
    if "error" in fp:
        yield ("text", f"I could not find flight {flight_id} in the dataset, so I cannot give figures for it.")
        return
    contrail = fp.get("contrail_share", 0)
    contrail_txt = (f"About {contrail:.0%} of its measured intervals were flown in the contrail-formation "
                    "band (8.5-12 km), so contrail warming is a real factor on this flight. "
                    if contrail else "")
    yield ("text",
           f"Flight {flight_id} ({fp['route']}, {fp['aircraft_type']}, {fp['distance_km']:.0f} km) burned "
           f"**{fp['fuel_kg']:,.0f} kg of fuel** in its measured intervals. Grounded in OpenAP/ICAO models, that is "
           f"**{fp['co2_kg']:,.0f} kg CO₂**, {fp['nox_kg']:,.1f} kg NOₓ, {fp['h2o_kg']:,.0f} kg water vapour, "
           f"plus SOₓ and soot. {contrail_txt}"
           f"Including non-CO₂ effects, the total climate impact is **{fp['co2e_kg_low']:,.0f}–{fp['co2e_kg_high']:,.0f} kg CO₂e** "
           f"(central {fp['co2e_kg_central']:,.0f}) - the range reflects genuine scientific uncertainty on contrails and NOₓ "
           "(Lee et al. 2021). Let me pull ranked mitigation options.")
    forcers = ["co2", "nox"] + (["contrails"] if contrail else [])
    recs = runner.run("recommend_mitigations", {"dominant_forcers": forcers, "max_levers": 4})
    yield ("tool", "recommend_mitigations", {"dominant_forcers": forcers, "max_levers": 4}, recs)
    lines = [f"{r['rank']}. **{r['name']}** ({r['category']}) - {r['impact']}. Feasibility: {r['feasibility']}. "
             f"[source]({r['source']})" + (f" ⚠️ {r['trade_off']}" if r.get("trade_off") else "")
             for r in recs["recommendations"]]
    yield ("text", "Ranked mitigation options for this footprint:\n\n" + "\n".join(lines) +
           "\n\n*These are DRAFT recommendations and require review by the responsible analyst before adoption.*")
    sim = runner.run("simulate_scenario", {"flight_id": flight_id, "scenario_id": "saf_30"})
    yield ("tool", "simulate_scenario", {"flight_id": flight_id, "scenario_id": "saf_30"}, sim)
    ch = sim["changes"].get("co2_kg", {})
    yield ("text",
           f"What-if - **{sim['scenario']}**: CO₂ falls from {ch.get('before', 0):,.0f} kg to "
           f"{ch.get('after', 0):,.0f} kg ({ch.get('delta_pct', 0)}%), and lower soot also thins contrails. "
           "You can run other scenarios (contrail re-route, cruise optimization, fleet renewal) from the sidebar.")
    mt = runner.run("check_maintenance", {"flight_id": flight_id})
    yield ("tool", "check_maintenance", {"flight_id": flight_id}, mt)
    if mt.get("z_score") is not None:
        verdict = mt["verdict"]
        yield ("text",
               f"Maintenance check: this flight burned {mt['fuel_per_km']} kg/km vs a peer median of "
               f"{mt['peer_median_fuel_per_km']} kg/km ({mt['peer_group_size']} similar {mt['aircraft_type']} flights) - "
               f"z-score {mt['z_score']}. Verdict: **{verdict}**.")
