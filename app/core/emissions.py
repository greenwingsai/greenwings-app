"""Grounded emissions engine.

All quantities derive from observed fuel burn (ACARS telemetry) via OpenAP
emission models (ICAO Engine Emissions Databank + Boeing Fuel Flow Method 2).
The LLM never generates these numbers - it calls this module as a tool.

Species covered: CO2, H2O, NOx, CO, HC, SOx, soot  (+ contrail-risk flag).
CO2-equivalent is reported as a RANGE, reflecting the genuine scientific
uncertainty on non-CO2 effects (Lee et al. 2021).
"""
from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd

# Fallback emission indices (kg pollutant per kg fuel) used when OpenAP has no
# model for an aircraft type. CO2/H2O/SOx/soot are fuel-chemistry constants;
# NOx/CO/HC are fleet-typical cruise values (ICAO EEDB order of magnitude).
FALLBACK_EI = {"co2": 3.16, "h2o": 1.23, "nox": 0.0153, "co": 0.002, "hc": 0.0002, "sox": 0.0012, "soot": 0.00003}


# Lee et al. 2021: aviation total ERF is ~3x CO2-only when contrail cirrus is
# included; ~1.3x excluding it. We surface this as a low/central/high range.
CO2E_MULTIPLIER = {"low": 1.3, "central": 1.7, "high": 3.0}

# Contrail-formation window (Schmidt-Appleman regime, simplified): most
# persistent contrails form at cruise between ~8.5 and 12 km; night-time
# contrails warm more (no albedo offset).
CONTRAIL_ALT_M = (8500.0, 12000.0)

_openap_cache: dict = {}


def _openap_model(actype: str):
    """Return an OpenAP Emission model or None (cached). use_synonym maps types
    without their own model (e.g. B77L) to the closest supported relative."""
    if actype in _openap_cache:
        return _openap_cache[actype]
    try:
        from openap import Emission
        model = Emission(ac=actype, use_synonym=True)
    except Exception:
        model = None
    _openap_cache[actype] = model
    return model


@dataclass
class FootprintResult:
    aircraft_type: str
    fuel_kg: float
    duration_s: float
    co2_kg: float
    h2o_kg: float
    nox_kg: float
    co_kg: float
    hc_kg: float
    sox_kg: float
    soot_kg: float
    contrail_risk: str            # "none" | "possible" | "likely (night)"
    co2e_kg_low: float
    co2e_kg_central: float
    co2e_kg_high: float
    method: str = "openap"        # "openap" or "fallback-EI"
    notes: list = field(default_factory=list)

    def as_dict(self):
        return asdict(self)


def estimate(aircraft_type: str, fuel_kg: float, duration_s: float,
             altitude_m: float | None = None, tas_ms: float | None = None,
             night: bool = False) -> FootprintResult:
    """Emissions for one interval/flight segment from observed fuel burn."""
    notes = []
    ff = fuel_kg / duration_s if duration_s > 0 else 0.0
    alt_ft = (altitude_m if altitude_m and not np.isnan(altitude_m) else 10500.0) * 3.28084
    tas_kt = (tas_ms if tas_ms and not np.isnan(tas_ms) else 230.0) * 1.94384
    if altitude_m is None or (isinstance(altitude_m, float) and np.isnan(altitude_m)):
        notes.append("altitude unavailable; assumed typical cruise FL345")

    model = _openap_model(aircraft_type)
    if model is not None:
        # OpenAP returns grams per second at the given fuel flow.
        co2 = model.co2(ff) / 1000 * duration_s
        h2o = model.h2o(ff) / 1000 * duration_s
        nox = model.nox(ff, tas=tas_kt, alt=alt_ft) / 1000 * duration_s
        co = model.co(ff, tas=tas_kt, alt=alt_ft) / 1000 * duration_s
        hc = model.hc(ff, tas=tas_kt, alt=alt_ft) / 1000 * duration_s
        sox = model.sox(ff) / 1000 * duration_s
        soot = model.soot(ff) / 1000 * duration_s
        method = "openap"
    else:
        co2, h2o, nox, co, hc, sox, soot = (FALLBACK_EI[k] * fuel_kg for k in
                                            ("co2", "h2o", "nox", "co", "hc", "sox", "soot"))
        method = "fallback-EI"
        notes.append("aircraft type not in OpenAP; fleet-typical emission indices used")

    alt_m = altitude_m if altitude_m and not np.isnan(altitude_m) else 10500.0
    if CONTRAIL_ALT_M[0] <= alt_m <= CONTRAIL_ALT_M[1]:
        risk = "likely (night)" if night else "possible"
    else:
        risk = "none"

    return FootprintResult(
        aircraft_type=aircraft_type, fuel_kg=round(fuel_kg, 1), duration_s=duration_s,
        co2_kg=round(co2, 1), h2o_kg=round(h2o, 1), nox_kg=round(nox, 3),
        co_kg=round(co, 3), hc_kg=round(hc, 4), sox_kg=round(sox, 3), soot_kg=round(soot, 5),
        contrail_risk=risk,
        co2e_kg_low=round(co2 * CO2E_MULTIPLIER["low"], 1),
        co2e_kg_central=round(co2 * CO2E_MULTIPLIER["central"], 1),
        co2e_kg_high=round(co2 * CO2E_MULTIPLIER["high"], 1),
        method=method, notes=notes,
    )


def flight_footprint(flight_row: pd.Series, flight_intervals: pd.DataFrame | None = None) -> dict:
    """Whole-flight footprint from the features table (+ enriched intervals when available)."""
    if flight_intervals is not None and len(flight_intervals):
        parts = [
            estimate(flight_row["aircraft_type"], r.fuel_kg, r.dur_s,
                     altitude_m=r.altitude_m, tas_ms=r.tas_ms, night=bool(r.night))
            for r in flight_intervals.itertuples()
        ]
        total = {k: round(sum(getattr(p, k) for p in parts), 2)
                 for k in ("fuel_kg", "co2_kg", "h2o_kg", "nox_kg", "co_kg", "hc_kg",
                           "sox_kg", "soot_kg", "co2e_kg_low", "co2e_kg_central", "co2e_kg_high")}
        contrail_int = sum(1 for p in parts if p.contrail_risk != "none")
        total.update(
            aircraft_type=flight_row["aircraft_type"], n_intervals=len(parts),
            contrail_intervals=contrail_int,
            contrail_share=round(contrail_int / len(parts), 2),
            method=parts[0].method, granularity="per-interval (real altitude/TAS)",
        )
        return total
    # flight-level fallback: observed totals, assumed cruise conditions
    res = estimate(flight_row["aircraft_type"], flight_row["fuel_obs_kg"], flight_row["obs_s"])
    out = res.as_dict()
    out["granularity"] = "flight-level (assumed cruise altitude)"
    return out
