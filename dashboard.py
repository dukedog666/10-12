"""Business calculations shared by the app, notebook, and validation checks."""
from pathlib import Path

import pandas as pd


DATA_PATH = Path(__file__).parent / "data" / "coffee_sales.csv"


def load_data(path=DATA_PATH):
    data = pd.read_csv(path)
    required = {"datetime", "date", "cash_type", "money", "coffee_name", "source"}
    if not required.issubset(data.columns):
        raise ValueError(f"Missing required columns: {sorted(required - set(data.columns))}")
    data["datetime"] = pd.to_datetime(data["datetime"], format="mixed", errors="raise")
    data["date"] = pd.to_datetime(data["date"], errors="raise").dt.normalize()
    data["money"] = pd.to_numeric(data["money"], errors="raise")
    if data[list(required)].isna().any().any():
        raise ValueError("A required transaction field is missing.")
    if not data["date"].eq(data["datetime"].dt.normalize()).all():
        raise ValueError("The date field does not match the transaction timestamp.")
    if not data["money"].gt(0).all():
        raise ValueError("Non-positive transaction amounts require source review.")
    return data.sort_values("datetime").reset_index(drop=True)


def default_period(data):
    """Use the most recent fully elapsed calendar month in this snapshot."""
    first = data["date"].min()
    last = data["date"].max()
    end = last.replace(day=1) - pd.Timedelta(days=1)
    start = end.replace(day=1)
    if end < first:
        return first.date(), last.date()
    return max(start, first).date(), end.date()


def filter_period(data, start, end):
    return data.loc[data["date"].between(pd.Timestamp(start), pd.Timestamp(end))].copy()


def headline_metrics(data):
    count = len(data)
    revenue = float(data["money"].sum())
    return {"sales": revenue, "transactions": count, "average": revenue / count if count else None}


def daily_counts(data, start, end):
    days = pd.date_range(start, end, freq="D", name="date")
    daily = data.groupby("date").size().reindex(days).rename("transactions").reset_index()
    # A source with no records is unknown, not a proven zero-sales day.
    daily["segment"] = daily["transactions"].isna().cumsum().astype(str)
    return daily


def weekly_check(data, start, end, source_last_date, threshold=-0.20):
    """Only compare two fully observed seven-day windows within the filter."""
    cutoff = min(pd.Timestamp(end), pd.Timestamp(source_last_date) - pd.Timedelta(days=1))
    current_start = cutoff - pd.Timedelta(days=6)
    previous_start = cutoff - pd.Timedelta(days=13)
    previous_end = current_start - pd.Timedelta(days=1)
    result = {"cutoff": cutoff, "current_start": current_start, "previous_start": previous_start,
              "previous_end": previous_end}
    if previous_start < pd.Timestamp(start):
        return result | {"status": "unavailable", "reason": "Select at least 14 days before the check date."}
    window = filter_period(data, previous_start, cutoff)
    observed = pd.DatetimeIndex(window["date"].unique())
    missing = pd.date_range(previous_start, cutoff).difference(observed)
    if len(missing):
        return result | {"status": "unavailable", "reason": f"{len(missing)} day(s) in the comparison have no records; no decline signal is inferred."}
    current = int(window["date"].between(current_start, cutoff).sum())
    previous = int(window["date"].between(previous_start, previous_end).sum())
    if not previous:
        return result | {"status": "unavailable", "reason": "The preceding period has no confirmed transactions."}
    change = current / previous - 1
    return result | {"status": "review" if change <= threshold else "within_threshold",
                     "current": current, "previous": previous, "change": change}
