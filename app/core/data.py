"""Cached data loaders for the GreenWings AI app."""
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "app" / "data_cache"
DATASET = ROOT / "Dataset"


@st.cache_data(show_spinner=False)
def flights() -> pd.DataFrame:
    """Per-flight engineered features (training phase)."""
    return pd.read_parquet(CACHE / "features_flights.parquet")


@st.cache_data(show_spinner=False)
def intervals() -> pd.DataFrame:
    """Fuel intervals enriched with altitude/TAS/night for the trajectory sample."""
    return pd.read_parquet(CACHE / "intervals_enriched.parquet")


@st.cache_data(show_spinner=False)
def traj_sample() -> pd.DataFrame:
    """Thinned trajectories for map/altitude plots."""
    return pd.read_parquet(CACHE / "traj_sample.parquet")


@st.cache_data(show_spinner=False)
def airports() -> pd.DataFrame:
    # Prefer the copy bundled in data_cache (ships in the deployed repo);
    # fall back to the local Dataset folder for development.
    cached = CACHE / "airports.parquet"
    return pd.read_parquet(cached if cached.exists() else DATASET / "airports.parquet")
