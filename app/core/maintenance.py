"""Predictive-maintenance signal from fuel-efficiency anomalies.

Real airlines run Aircraft Performance Monitoring (APM): an airframe that
burns significantly more fuel than its type baseline signals degradation
(engine wear, rigging, drag from damaged seals) and triggers inspection or
an engine wash. Flight IDs in this dataset are anonymised (no tail numbers),
so we apply the same logic at fleet level: each flight is compared to a peer
group of the SAME aircraft type on SIMILAR-distance missions, and outliers
in fuel-per-km are flagged as maintenance-check candidates.
"""
import numpy as np
import pandas as pd

MIN_PEERS = 8
DISTANCE_BINS_KM = [0, 500, 1000, 1500, 2500, 4000, 6000, 9000, 15000]
BIN_LABELS = ["<500", "500-1k", "1k-1.5k", "1.5k-2.5k", "2.5k-4k", "4k-6k", "6k-9k", ">9k"]


def peer_table(flights: pd.DataFrame) -> pd.DataFrame:
    """Add peer-group stats and anomaly flags to the flight features table."""
    df = flights.copy()
    df["dist_bin"] = pd.cut(df["distance_km"], bins=DISTANCE_BINS_KM, labels=BIN_LABELS)

    grp = df.groupby(["aircraft_type", "dist_bin"], observed=True)["fuel_per_km"]
    stats = grp.agg(peer_median="median", peer_std="std", peer_n="size")
    df = df.join(stats, on=["aircraft_type", "dist_bin"])

    valid = (df["peer_n"] >= MIN_PEERS) & (df["peer_std"] > 0)
    df["z_score"] = np.where(valid, (df["fuel_per_km"] - df["peer_median"]) / df["peer_std"], np.nan)
    df["excess_pct"] = np.where(valid, (df["fuel_per_km"] / df["peer_median"] - 1) * 100, np.nan)

    df["maintenance_flag"] = pd.cut(
        df["z_score"], bins=[-np.inf, 2, 3, np.inf],
        labels=["normal", "monitor - schedule performance check", "outlier - recommend inspection"],
    )
    return df


def summarize(df: pd.DataFrame) -> dict:
    """Fleet-level summary used by the agent tool and dashboard KPIs."""
    flagged = df[df["z_score"] > 2]
    urgent = df[df["z_score"] > 3]
    # Fuel that would be avoided if flagged flights matched their peer median.
    excess_fuel = float(((flagged["fuel_per_km"] - flagged["peer_median"])
                         * flagged["distance_km"] * flagged["coverage"]).sum())
    return {
        "flights_analyzed": int(df["z_score"].notna().sum()),
        "flagged_monitor": int(len(flagged) - len(urgent)),
        "flagged_inspection": int(len(urgent)),
        "excess_fuel_kg": round(excess_fuel, 0),
        "excess_co2_kg": round(excess_fuel * 3.16, 0),
        "method": "fuel-per-km z-score vs peer group (same type + distance band, "
                  f"min {MIN_PEERS} peers); >2σ monitor, >3σ inspect",
        "limitation": "flight IDs are anonymised (no tail numbers), so flags identify "
                      "anomalous flights, not specific airframes; with operator data the "
                      "same method tracks each aircraft over time",
    }


def check_flight(df: pd.DataFrame, flight_id: str) -> dict:
    """Maintenance verdict for a single flight (agent tool)."""
    row = df[df["flight_id"] == flight_id]
    if row.empty:
        return {"error": f"flight {flight_id} not found"}
    r = row.iloc[0]
    return {
        "flight_id": flight_id,
        "aircraft_type": r["aircraft_type"],
        "distance_km": round(float(r["distance_km"]), 0),
        "fuel_per_km": round(float(r["fuel_per_km"]), 2),
        "peer_median_fuel_per_km": round(float(r["peer_median"]), 2) if pd.notna(r["peer_median"]) else None,
        "peer_group_size": int(r["peer_n"]) if pd.notna(r["peer_n"]) else 0,
        "z_score": round(float(r["z_score"]), 2) if pd.notna(r["z_score"]) else None,
        "excess_vs_peers_pct": round(float(r["excess_pct"]), 1) if pd.notna(r["excess_pct"]) else None,
        "verdict": str(r["maintenance_flag"]) if pd.notna(r["maintenance_flag"]) else "insufficient peers",
    }
