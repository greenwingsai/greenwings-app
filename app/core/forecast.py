"""Emissions trend forecasting.

WHAT IS MODELLED - and why not raw totals: the monitored sample's daily volume
and fleet mix follow crowdsourced ACARS coverage (145 fl/day in April vs 59 in
August), so raw totals trend with data collection, not aviation. We therefore
model the **mix-adjusted CO2 intensity per flown km** (fuel per flight per
aircraft type, fixed whole-period fleet-mix weights - a Laspeyres index) and
scale by an activity level the user chooses (their flights/day).

Two regimes, honestly separated:

1. STATISTICAL (daily -> quarterly): OLS on the observed daily intensity -
   linear trend + day-of-week seasonality - with prediction intervals from
   residual variance. Supported by the ~6.5 months of monitored data.

2. SCENARIO (6 months -> 5 years): the fitted baseline extended with published
   industry drivers, because 6.5 months cannot identify annual seasonality or
   multi-year trend:
     - traffic growth ~+2%/yr (EUROCONTROL STATFOR European base scenario)
     - ReFuelEU SAF mandate: 2% (2025) -> 6% (2030), ~-80% lifecycle CO2/kg SAF
     - GreenWings operational levers: 1.5-4.5% fuel recovery (mitigation KB)
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

TRAFFIC_GROWTH = 0.02
SAF_SHARE = {2025: 0.02, 2026: 0.028, 2027: 0.036, 2028: 0.044, 2029: 0.052, 2030: 0.06}
SAF_LIFECYCLE_CUT = 0.80
GW_LEVER_RAMP = [0.015, 0.03, 0.045, 0.045, 0.045]   # GreenWings ops levers, years 1..5

HORIZONS = {
    "Daily (next 14 days)":        dict(days=14, freq="D"),
    "Weekly (next 12 weeks)":      dict(days=84, freq="W"),
    "Monthly (next 12 months)":    dict(days=365, freq="ME"),
    "Quarterly (next 8 quarters)": dict(days=730, freq="QE"),
    "6-month blocks (3 years)":    dict(days=1095, freq="2QE"),
    "Yearly (5 years)":            dict(days=1825, freq="YE"),
}
SCENARIO_HORIZONS = {"6-month blocks (3 years)", "Yearly (5 years)"}


@dataclass
class Fit:
    daily: pd.DataFrame
    coef: np.ndarray             # [intercept, slope, dow1..dow6] on kg CO2/km
    sigma: float                 # residual std, kg CO2/km
    t0: pd.Timestamp


def _design(dates: pd.Series, t0: pd.Timestamp) -> np.ndarray:
    t = (dates - t0).dt.days.to_numpy(dtype=float)
    dow = pd.get_dummies(dates.dt.dayofweek, drop_first=True).reindex(columns=range(1, 7), fill_value=0)
    return np.column_stack([np.ones(len(t)), t, dow.to_numpy(dtype=float)])


def fit(daily: pd.DataFrame) -> Fit:
    d = daily.dropna(subset=["co2_per_km_adj"]).copy()
    t0 = d["date"].min()
    X = _design(d["date"], t0)
    y = d["co2_per_km_adj"].to_numpy(dtype=float)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    return Fit(daily=d, coef=coef, sigma=float(resid.std(ddof=X.shape[1])), t0=t0)


def predict_daily(f: Fit, n_days: int, km_per_day: float) -> pd.DataFrame:
    """Daily total CO2 forecast (kg) = intensity forecast x chosen activity."""
    start = f.daily["date"].max() + pd.Timedelta(days=1)
    dates = pd.date_range(start, periods=n_days, freq="D")
    X = _design(pd.Series(dates), f.t0)
    # Long extrapolation of a short-sample slope is not defensible: hold the
    # trend after one observed-length horizon and let scenarios take over.
    t = X[:, 1].copy()
    t_max = (f.daily["date"].max() - f.t0).days + len(f.daily)
    X[:, 1] = np.minimum(t, t_max)
    mean = (X @ f.coef).clip(min=0) * km_per_day
    # intensity residuals average out over a day of flying; scale like a daily mean
    sig = f.sigma * km_per_day / np.sqrt(30)
    out = pd.DataFrame({"date": dates, "co2_kg": mean})
    out["lo"] = (mean - 1.96 * sig).clip(min=0)
    out["hi"] = mean + 1.96 * sig
    return out


def aggregate(pred: pd.DataFrame, freq: str) -> pd.DataFrame:
    g = pred.set_index("date").groupby(pd.Grouper(freq=freq))
    out = g.agg(co2_kg=("co2_kg", "sum"), n=("co2_kg", "size")).reset_index()
    sigma_day = (pred["hi"] - pred["co2_kg"]).mean() / 1.96
    out["lo"] = (out["co2_kg"] - 1.96 * sigma_day * np.sqrt(out["n"])).clip(lower=0)
    out["hi"] = out["co2_kg"] + 1.96 * sigma_day * np.sqrt(out["n"])
    return out[out["n"] >= out["n"].max() * 0.5]

def yearly_scenarios(f: Fit, km_per_day: float, years: int = 5,
                     periods_per_year: int = 1) -> pd.DataFrame:
    """BAU vs ReFuelEU SAF vs SAF + GreenWings levers (kg CO2 per period)."""
    base_year = predict_daily(f, 365, km_per_day)["co2_kg"].sum()
    start_year = int(f.daily["date"].max().year) + 1
    rows = []
    for i in range(years * periods_per_year):
        yr_frac = (i + 1) / periods_per_year
        year = start_year + i // periods_per_year
        growth = (1 + TRAFFIC_GROWTH) ** yr_frac
        saf = SAF_SHARE.get(min(year, 2030), 0.06)
        gw = GW_LEVER_RAMP[min(int(yr_frac) if yr_frac >= 1 else 0, len(GW_LEVER_RAMP) - 1)]
        bau = base_year / periods_per_year * growth
        with_saf = bau * (1 - SAF_LIFECYCLE_CUT * saf)
        rows.append((year, i, bau, with_saf, with_saf * (1 - gw)))
    df = pd.DataFrame(rows, columns=["year", "period", "bau_kg", "saf_kg", "gw_kg"])
    df["gw_saving_kg"] = df["saf_kg"] - df["gw_kg"]
    return df


def summary_for_agent(daily: pd.DataFrame, horizon_label: str,
                      km_per_day: float | None = None) -> dict:
    f = fit(daily)
    fpd = km_per_day or float(f.daily["km_flown"].median())
    spec = HORIZONS.get(horizon_label)
    if spec is None:
        return {"error": f"unknown horizon '{horizon_label}'", "available": list(HORIZONS)}
    slope_pct_month = f.coef[1] * 30 / f.daily["co2_per_km_adj"].mean() * 100
    result = {
        "horizon": horizon_label,
        "observed_period": f"{f.daily['date'].min().date()} to {f.daily['date'].max().date()}",
        "mix_adjusted_intensity_kg_co2_per_km": round(f.daily["co2_per_km_adj"].mean(), 2),
        "fitted_intensity_trend_pct_per_month": round(slope_pct_month, 2),
        "activity_assumption_km_flown_per_day": round(fpd, 0),
        "method": "OLS trend + weekday seasonality on mix-adjusted CO2 intensity per flown km "
                  "(fixed fleet-mix weights), scaled by the activity assumption",
        "caveat": "~6.5 months of monitored data; horizons beyond ~6 months use published scenario "
                  "drivers (EUROCONTROL +2%/yr traffic, ReFuelEU SAF ramp, GreenWings lever impacts)",
    }
    if horizon_label not in SCENARIO_HORIZONS:
        agg = aggregate(predict_daily(f, spec["days"], fpd), spec["freq"])
        result["forecast"] = [
            {"period": str(r.date.date()), "co2_t": round(r.co2_kg / 1000, 1),
             "range_t": [round(r.lo / 1000, 1), round(r.hi / 1000, 1)]}
            for r in agg.itertuples()]
    else:
        sc = yearly_scenarios(f, fpd)
        result["scenarios_t_co2_per_year"] = [
            {"year": int(r.year), "business_as_usual": round(r.bau_kg / 1000, 0),
             "with_refueleu_saf": round(r.saf_kg / 1000, 0),
             "with_saf_plus_greenwings": round(r.gw_kg / 1000, 0)}
            for r in sc.itertuples()]
        result["greenwings_5yr_cumulative_saving_t"] = round(sc["gw_saving_kg"].sum() / 1000, 0)
    return result
