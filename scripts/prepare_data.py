"""Audit the supplied files and preserve both streams with explicit provenance."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def audit(path):
    data = pd.read_csv(path)
    dates = pd.to_datetime(data["date"])
    return data, {
        "filename": path.name, "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(data), "columns": list(data.columns),
        "dtypes": {col: str(kind) for col, kind in data.dtypes.items()},
        "missing": {col: int(count) for col, count in data.isna().sum().items()},
        "duplicates_all_fields": int(data.duplicated().sum()),
        "date_min": dates.min().strftime("%Y-%m-%d"), "date_max": dates.max().strftime("%Y-%m-%d"),
        "observed_days": int(dates.nunique()),
        "dates_without_records": [day.strftime("%Y-%m-%d") for day in pd.date_range(dates.min(), dates.max()).difference(pd.DatetimeIndex(dates.unique()))],
        "drink_categories": int(data.coffee_name.nunique()),
        "payment_counts": {name: int(count) for name, count in data.cash_type.value_counts().items()},
        "sales_source_units": round(float(data.money.sum()), 2),
        "nonpositive_amounts": int(data.money.le(0).sum()),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--secondary", type=Path, required=True)
    args = parser.parse_args()
    primary, first_audit = audit(args.primary)
    secondary, second_audit = audit(args.secondary)
    needed = ["date", "datetime", "cash_type", "money", "coffee_name"]
    if primary[needed].isna().any().any() or primary.money.le(0).any():
        raise ValueError("Review invalid source records before publication.")
    first_norm, second_norm = primary[needed].copy(), secondary[needed].copy()
    for frame in (first_norm, second_norm):
        frame["datetime"] = pd.to_datetime(frame.datetime, format="mixed")
        frame["coffee_name"] = frame.coffee_name.str.strip().str.casefold()
    matches = len(first_norm.merge(second_norm.drop_duplicates(), on=needed, how="inner"))
    if secondary[needed].isna().any().any() or secondary.money.le(0).any():
        raise ValueError("Review invalid secondary records before publication.")
    published = pd.concat([primary[needed].assign(source="index_1"),
                           secondary[needed].assign(source="index_2")], ignore_index=True)
    published["coffee_name"] = published.coffee_name.str.strip()
    published = published.sort_values(["source", "datetime"], kind="stable").reset_index(drop=True)
    destination = ROOT / "data"
    destination.mkdir(exist_ok=True)
    published.to_csv(destination / "coffee_sales.csv", index=False)
    summary = {
        "dataset_url": "https://www.kaggle.com/datasets/ihelon/coffee-sales",
        "source_audits": [first_audit, second_audit],
        "normalized_cross_file_matches": matches,
        "selection": "Preserve both sources in one small CSV; the app selects one source at a time because their business relationship is unconfirmed.",
        "published_rows": len(published),
        "published_csv_bytes": (destination / "coffee_sales.csv").stat().st_size,
        "transformations": ["Add explicit source provenance", "Remove anonymous card identifiers", "Trim drink-name whitespace", "Sort timestamps; retain all 3636 primary and 262 secondary records, including two unresolved duplicate rows"],
        "currency": "Unverified; report in source units",
        "license_reported_by_kaggle": "CC0: Public Domain",
    }
    (destination / "source_audit.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"published_rows": len(published), "published_csv_bytes": summary["published_csv_bytes"], "normalized_cross_file_matches": matches}, indent=2))


if __name__ == "__main__":
    main()
