"""Mitigation knowledge base.

Curated levers with literature-grounded typical impact, feasibility, cost and
sources. The agent SELECTS and RANKS from this list - it never invents a
lever or an impact figure. Impacts are indicative ranges, not guarantees.
"""

LEVERS = [
    {
        "id": "contrail_avoidance",
        "name": "Contrail-avoidance altitude shifts",
        "category": "operational",
        "targets": ["contrails"],
        "impact": "~54-64% fewer contrails by re-flighting ~1.7% of flights (AA/Google/Breakthrough 2023 trial); small fuel penalty (~0.3% on adjusted flights)",
        "impact_score": 5,
        "feasibility": "high - flight-planning change only, no new hardware",
        "cost": "low",
        "timescale": "immediate",
        "source": "https://www.nature.com/articles/s44172-024-00329-7",
    },
    {
        "id": "saf",
        "name": "Sustainable Aviation Fuel (SAF) blending",
        "category": "fuel",
        "targets": ["co2", "soot", "contrails"],
        "impact": "up to ~80% lifecycle CO2 reduction at 100% SAF (proportional at blend %); lower soot also thins contrails",
        "impact_score": 5,
        "feasibility": "medium - certified to 50% blends; supply <1% of demand today",
        "cost": "high (2-5x fossil kerosene)",
        "timescale": "scaling through 2030s (ReFuelEU: 6% by 2030)",
        "source": "https://www.iata.org/en/programs/sustainability/sustainable-aviation-fuels/",
    },
    {
        "id": "cruise_optimization",
        "name": "Cruise speed & altitude optimization",
        "category": "operational",
        "targets": ["co2", "nox"],
        "impact": "1-3% fuel burn reduction per flight (cost-index tuning, optimal flight levels)",
        "impact_score": 3,
        "feasibility": "high - software + procedures (SkyBreathe-style analytics)",
        "cost": "low",
        "timescale": "immediate",
        "source": "https://www.openairlines.com/skybreathe-fuel-efficiency/",
    },
    {
        "id": "cdo",
        "name": "Continuous descent/climb operations (CDO/CCO)",
        "category": "operational",
        "targets": ["co2", "nox"],
        "impact": "50-150 kg fuel saved per approach; less NOx below 3,000 ft",
        "impact_score": 2,
        "feasibility": "medium - needs ATC cooperation",
        "cost": "low",
        "timescale": "immediate-2 years",
        "source": "https://www.eurocontrol.int/concept/continuous-climb-and-descent-operations",
    },
    {
        "id": "apm_maintenance",
        "name": "Performance-based maintenance (engine wash, rigging, drag audits)",
        "category": "maintenance",
        "targets": ["co2", "nox", "soot"],
        "impact": "0.5-1.5% fleet fuel burn recovered by fixing degraded airframes/engines flagged by fuel-per-km anomaly monitoring",
        "impact_score": 3,
        "feasibility": "high - GreenWings' predictive-maintenance module supplies the flags",
        "cost": "low-medium (engine wash pays back in weeks)",
        "timescale": "immediate",
        "source": "https://www.mdpi.com/2673-7590/4/2/25",
    },
    {
        "id": "load_factor",
        "name": "Load factor & weight reduction",
        "category": "operational",
        "targets": ["co2", "nox"],
        "impact": "~1% fuel per ~1.4t weight removed (long-haul); higher load factor cuts per-passenger footprint directly",
        "impact_score": 2,
        "feasibility": "high",
        "cost": "low",
        "timescale": "immediate",
        "source": "https://www.sciencedirect.com/science/article/pii/S1361920923001141",
    },
    {
        "id": "fleet_renewal",
        "name": "Fleet renewal (neo/MAX/787-class re-engining)",
        "category": "technology",
        "targets": ["co2", "nox", "soot"],
        "impact": "15-25% fuel burn per seat vs previous generation",
        "impact_score": 4,
        "feasibility": "medium - capital cycle",
        "cost": "very high",
        "timescale": "5-15 years",
        "source": "https://www.sciencedirect.com/science/article/pii/S0969699724000450",
    },
    {
        "id": "hydrogen_electric",
        "name": "Hydrogen / electric aircraft (short-haul)",
        "category": "technology",
        "targets": ["co2", "nox", "contrails"],
        "impact": "zero in-flight CO2; hydrogen shifts contrail chemistry (more H2O, no soot) - net effect under study",
        "impact_score": 3,
        "feasibility": "low today - demonstrators only",
        "cost": "very high",
        "timescale": "2035+",
        "source": "https://www.airbus.com/en/innovation/energy-transition/hydrogen/zeroe",
    },
    {
        "id": "modal_shift",
        "name": "Modal shift to rail (short-haul demand)",
        "category": "demand",
        "targets": ["co2", "nox", "contrails"],
        "impact": "~90%+ per-trip footprint reduction where high-speed rail exists (<700 km)",
        "impact_score": 3,
        "feasibility": "medium - policy + infrastructure dependent",
        "cost": "n/a (policy)",
        "timescale": "ongoing",
        "source": "https://www.eea.europa.eu/publications/transport-and-environment-report-2020",
    },
    {
        "id": "market_measures",
        "name": "CORSIA / EU ETS compliance & offsetting",
        "category": "economic",
        "targets": ["co2"],
        "impact": "caps net CO2 growth; EU MRV now requires non-CO2 monitoring from 2025 - GreenWings reporting aligns directly",
        "impact_score": 2,
        "feasibility": "high (mandatory)",
        "cost": "medium (allowance prices)",
        "timescale": "in force",
        "source": "https://www.icao.int/environmental-protection/CORSIA/",
    },
]

# NOx-specific note: reducing NOx cools via ozone but warms via methane response;
# honest advice weighs both (net RF +17.5 mW/m2, Lee et al. 2021).
TRADE_OFFS = {
    "contrail_avoidance": "small CO2 penalty on re-routed flights; net climate benefit strongly positive",
    "saf": "land-use / feedstock sustainability must be certified (no food-crop displacement)",
    "hydrogen_electric": "hydrogen contrails contain more water vapour; net non-CO2 effect still researched",
    "modal_shift": "regional connectivity equity - avoid penalising markets without rail alternatives",
}


def recommend(dominant_forcers: list[str] | None = None, max_levers: int = 5,
              categories: list[str] | None = None) -> list[dict]:
    """Rank levers for the given dominant forcers (defaults to all)."""
    forcers = [f.lower() for f in (dominant_forcers or ["co2", "contrails", "nox"])]
    scored = []
    for lever in LEVERS:
        if categories and lever["category"] not in categories:
            continue
        relevance = sum(1 for t in lever["targets"] if t in forcers)
        if relevance == 0:
            continue
        scored.append((lever["impact_score"] + relevance, lever))
    scored.sort(key=lambda x: -x[0])
    out = []
    for rank, (score, lever) in enumerate(scored[:max_levers], start=1):
        item = {"rank": rank, **lever}
        if lever["id"] in TRADE_OFFS:
            item["trade_off"] = TRADE_OFFS[lever["id"]]
        out.append(item)
    return out


# What-if simulator factors: fractional change applied to the relevant species.
SCENARIOS = {
    "saf_30": {"label": "30% SAF blend", "co2": -0.30 * 0.8, "soot": -0.2, "contrail_note": "thinner contrails from lower soot"},
    "saf_50": {"label": "50% SAF blend", "co2": -0.50 * 0.8, "soot": -0.35, "contrail_note": "thinner contrails from lower soot"},
    "contrail_reroute": {"label": "Contrail-avoidance altitude shift", "co2": +0.003, "contrail": -0.59},
    "cruise_opt": {"label": "Cruise speed/altitude optimization", "co2": -0.02, "nox": -0.02},
    "fleet_renewal": {"label": "Next-generation aircraft", "co2": -0.20, "nox": -0.20, "soot": -0.30},
    "maintenance_fix": {"label": "Restore flagged aircraft to peer baseline", "co2": -0.01, "nox": -0.01},
}


def simulate(baseline: dict, scenario_id: str) -> dict:
    """Apply a scenario to a baseline footprint dict (kg values)."""
    sc = SCENARIOS.get(scenario_id)
    if not sc:
        return {"error": f"unknown scenario '{scenario_id}'", "available": list(SCENARIOS)}
    out = {"scenario": sc["label"], "baseline_co2_kg": baseline.get("co2_kg"), "changes": {}}
    for key, delta in sc.items():
        if key in ("label", "contrail_note"):
            continue
        if key == "contrail":
            out["changes"]["contrail_formation"] = f"{delta:+.0%}"
            continue
        base = baseline.get(f"{key}_kg")
        if base is not None:
            out["changes"][f"{key}_kg"] = {"before": round(base, 1), "after": round(base * (1 + delta), 1), "delta_pct": round(delta * 100, 1)}
    if "contrail_note" in sc:
        out["note"] = sc["contrail_note"]
    return out
