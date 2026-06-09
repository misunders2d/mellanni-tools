from datetime import date

import numpy as np
import pandas as pd

from modules import restock_dashboard as rd


def test_inventory_aggregates_all_skus_and_excludes_warehouse():
    raw = pd.DataFrame(
        [
            {"date": "2026-06-09", "asin": "A1", "sku": "S1", "available": 10, "fba_inventory": 12, "inbound_shipped": 3, "warehouse": 999},
            {"date": "2026-06-09", "asin": "A1", "sku": "S2", "available": 15, "fba_inventory": 20, "inbound_shipped": 5, "warehouse": 999},
        ]
    )

    out = rd.aggregate_inventory_history(raw)

    assert len(out) == 1
    row = out.iloc[0]
    assert row["available"] == 25
    assert row["fba_inventory"] == 32
    assert row["inbound_shipped"] == 8
    assert row["total_inventory"] == 32


def test_projection_and_alert_threshold():
    sales = pd.DataFrame(
        [
            {"date": "2026-06-07", "asin": "A1", "unit_sales": 10, "dollar_sales": 100},
            {"date": "2026-06-08", "asin": "A1", "unit_sales": 10, "dollar_sales": 100},
            {"date": "2026-06-09", "asin": "A1", "unit_sales": 0, "dollar_sales": 0},
        ]
    )
    inv = pd.DataFrame(
        [{"date": "2026-06-09", "asin": "A1", "available": 10, "fba_inventory": 20, "inbound_shipped": 99, "total_inventory": 119}]
    )
    dictionary = pd.DataFrame([{"sku": "S1", "asin": "A1", "collection": "C", "sub_collection": "SC", "short_title": "Title"}])
    config = rd.RestockConfig(top_n=1, long_term_days=2, short_term_days=1, alert_days=21, projection_days=30, include_events=True)

    summary = rd.build_restock_summary(sales, inv, dictionary, config)

    row = summary.iloc[0]
    assert row["avg_units"] == 10
    assert row["avg_dollars"] == 100
    assert row["days_to_stockout"] == 2
    assert row["alert"] is True or bool(row["alert"]) is True
    assert row["projected_inventory_30d"] == 0
    # Projection uses Total FBA / Inventory_Supply_at_FBA; inbound_shipped is not added again.
    assert row["days_to_stockout"] == row["fba_inventory"] / row["avg_units"]


def test_top_n_ranks_by_smart_average_dollars():
    inv = pd.DataFrame(
        [
            {"date": "2026-06-09", "asin": "A1", "available": 100, "fba_inventory": 100, "inbound_shipped": 0, "total_inventory": 100},
            {"date": "2026-06-09", "asin": "A2", "available": 100, "fba_inventory": 100, "inbound_shipped": 0, "total_inventory": 100},
            {"date": "2026-06-09", "asin": "A3", "available": 100, "fba_inventory": 100, "inbound_shipped": 0, "total_inventory": 100},
        ]
    )
    sales = pd.DataFrame(
        [
            {"date": "2026-06-07", "asin": "A1", "unit_sales": 1, "dollar_sales": 100},
            {"date": "2026-06-08", "asin": "A1", "unit_sales": 1, "dollar_sales": 100},
            {"date": "2026-06-09", "asin": "A1", "unit_sales": 0, "dollar_sales": 0},
            {"date": "2026-06-07", "asin": "A2", "unit_sales": 1, "dollar_sales": 50},
            {"date": "2026-06-08", "asin": "A2", "unit_sales": 1, "dollar_sales": 50},
            {"date": "2026-06-09", "asin": "A2", "unit_sales": 0, "dollar_sales": 0},
            {"date": "2026-06-07", "asin": "A3", "unit_sales": 1, "dollar_sales": 200},
            {"date": "2026-06-08", "asin": "A3", "unit_sales": 1, "dollar_sales": 200},
            {"date": "2026-06-09", "asin": "A3", "unit_sales": 0, "dollar_sales": 0},
        ]
    )
    dictionary = pd.DataFrame(
        [
            {"sku": "S1", "asin": "A1"},
            {"sku": "S2", "asin": "A2"},
            {"sku": "S3", "asin": "A3"},
        ]
    )

    summary = rd.build_restock_summary(
        sales,
        inv,
        dictionary,
        rd.RestockConfig(top_n=2, long_term_days=2, short_term_days=1, include_events=True),
    )

    assert summary["asin"].tolist() == ["A3", "A1"]


def test_zero_velocity_has_no_alert():
    inv = pd.DataFrame(
        [{"date": "2026-06-09", "asin": "A1", "available": 50, "fba_inventory": 50, "inbound_shipped": 0, "total_inventory": 50}]
    )
    sales = pd.DataFrame(columns=["date", "asin", "unit_sales", "dollar_sales"])
    dictionary = pd.DataFrame([{"sku": "S1", "asin": "A1"}])

    summary = rd.build_restock_summary(sales, inv, dictionary, rd.RestockConfig(top_n=1))

    assert summary.empty


def test_build_chart_series_next_30_days_projection():
    history = pd.DataFrame(
        [
            {"date": date(2026, 6, 8), "asin": "A1", "total_inventory": 12},
            {"date": date(2026, 6, 9), "asin": "A1", "total_inventory": 10},
        ]
    )
    row = pd.Series({"asin": "A1", "fba_inventory": 10, "total_inventory": 10, "avg_units": 2})

    series = rd.build_chart_series("A1", history, row, history_days=30, projection_days=30)

    projected_last = series.dropna(subset=["projected_inventory"]).iloc[-1]
    assert projected_last["projected_inventory"] == 0
    assert len(series.dropna(subset=["projected_inventory"])) == 31
