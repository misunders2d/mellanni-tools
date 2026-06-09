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


def test_normalize_sp_inventory_report_maps_myi_fields():
    raw = pd.DataFrame(
        [
            {
                "sku": "S1",
                "asin": "A1",
                "afn-fulfillable-quantity": "7",
                "afn-total-quantity": "12",
                "afn-inbound-shipped-quantity": "3",
            }
        ]
    )

    out = rd.normalize_sp_inventory_report(raw, snapshot_date="2026-06-09")

    row = out.iloc[0]
    assert row["date"] == date(2026, 6, 9)
    assert row["available"] == 7
    assert row["fba_inventory"] == 12
    assert row["total_inventory"] == 12
    assert row["inbound_shipped"] == 3


def test_apply_current_inventory_snapshot_replaces_bq_current_date():
    history = pd.DataFrame(
        [
            {"date": date(2026, 6, 8), "asin": "A1", "available": 1, "fba_inventory": 2, "inbound_shipped": 0, "total_inventory": 2},
            {"date": date(2026, 6, 9), "asin": "A1", "available": 3, "fba_inventory": 4, "inbound_shipped": 0, "total_inventory": 4},
        ]
    )
    sp_current = pd.DataFrame(
        [{"date": date(2026, 6, 9), "asin": "A1", "available": 10, "fba_inventory": 20, "inbound_shipped": 0, "total_inventory": 20}]
    )

    out = rd.apply_current_inventory_snapshot(history, sp_current)

    assert len(out) == 2
    assert out[out["date"] == date(2026, 6, 9)].iloc[0]["fba_inventory"] == 20


def test_event_calendar_expands_inclusive_dates_and_ignores_extra_columns():
    calendar = pd.DataFrame(
        [
            {"event_code": "pd", "event_name": "Prime", "start_date": "2026-07-10", "end_date": "2026-07-12", "notes": "ignore"},
            {"event_code": "", "start_date": "bad", "end_date": "2026-07-12"},
        ]
    )

    normalized = rd.normalize_event_calendar(calendar)
    dates = rd.expand_event_dates(normalized)

    assert normalized.columns.tolist() == ["event_code", "start_date", "end_date"]
    assert normalized.iloc[0]["event_code"] == "PD"
    assert dates == [date(2026, 7, 10), date(2026, 7, 11), date(2026, 7, 12)]


def test_velocity_excludes_event_dates_when_toggle_off():
    sales = pd.DataFrame(
        [
            {"date": "2026-06-07", "asin": "A1", "unit_sales": 10, "dollar_sales": 100},
            {"date": "2026-06-08", "asin": "A1", "unit_sales": 90, "dollar_sales": 900},
            {"date": "2026-06-09", "asin": "A1", "unit_sales": 0, "dollar_sales": 0},
        ]
    )
    isr = pd.DataFrame([{"asin": "A1", "ISR": 1.0, "ISR_short": 1.0}])

    excluded = rd.calculate_smart_asin_sales(
        sales,
        isr,
        include_events=False,
        long_term_days=2,
        short_term_days=1,
        events=[date(2026, 6, 8)],
    )
    included = rd.calculate_smart_asin_sales(
        sales,
        isr,
        include_events=True,
        long_term_days=2,
        short_term_days=1,
        events=[date(2026, 6, 8)],
    )

    assert excluded.iloc[0]["avg units"] == 8
    assert included.iloc[0]["avg units"] == 74


def test_build_restock_summary_includes_size_and_color_metadata():
    sales = pd.DataFrame(
        [
            {"date": "2026-06-07", "asin": "A1", "unit_sales": 2, "dollar_sales": 20},
            {"date": "2026-06-08", "asin": "A1", "unit_sales": 2, "dollar_sales": 20},
            {"date": "2026-06-09", "asin": "A1", "unit_sales": 0, "dollar_sales": 0},
        ]
    )
    inv = pd.DataFrame(
        [{"date": "2026-06-09", "asin": "A1", "available": 10, "fba_inventory": 20, "inbound_shipped": 0, "total_inventory": 20}]
    )
    dictionary = pd.DataFrame(
        [{"sku": "S1", "asin": "A1", "collection": "Iconic", "sub_collection": "Sheets", "size": "King", "color": "White"}]
    )

    summary = rd.build_restock_summary(
        sales,
        inv,
        dictionary,
        rd.RestockConfig(top_n=1, long_term_days=2, short_term_days=1, include_events=True),
    )

    row = summary.iloc[0]
    assert row["collection"] == "Iconic"
    assert row["size"] == "King"
    assert row["color"] == "White"


def test_build_restock_summary_empty_selected_asins_returns_empty():
    summary = rd.build_restock_summary(
        pd.DataFrame(columns=["date", "asin", "unit_sales", "dollar_sales"]),
        pd.DataFrame(columns=["date", "asin", "available", "fba_inventory", "inbound_shipped", "total_inventory"]),
        pd.DataFrame(columns=["sku", "asin"]),
        selected_asins=(),
    )

    assert summary.empty
    assert summary.columns.tolist() == rd.SUMMARY_COLUMNS


def test_build_restock_summary_prefilters_selected_asins():
    inv = pd.DataFrame(
        [
            {"date": "2026-06-09", "asin": "A1", "available": 100, "fba_inventory": 100, "inbound_shipped": 0, "total_inventory": 100},
            {"date": "2026-06-09", "asin": "A2", "available": 100, "fba_inventory": 100, "inbound_shipped": 0, "total_inventory": 100},
        ]
    )
    sales = pd.DataFrame(
        [
            {"date": "2026-06-07", "asin": "A1", "unit_sales": 1, "dollar_sales": 100},
            {"date": "2026-06-08", "asin": "A1", "unit_sales": 1, "dollar_sales": 100},
            {"date": "2026-06-09", "asin": "A1", "unit_sales": 0, "dollar_sales": 0},
            {"date": "2026-06-07", "asin": "A2", "unit_sales": 1, "dollar_sales": 200},
            {"date": "2026-06-08", "asin": "A2", "unit_sales": 1, "dollar_sales": 200},
            {"date": "2026-06-09", "asin": "A2", "unit_sales": 0, "dollar_sales": 0},
        ]
    )
    dictionary = pd.DataFrame([{"sku": "S1", "asin": "A1"}, {"sku": "S2", "asin": "A2"}])

    summary = rd.build_restock_summary(
        sales,
        inv,
        dictionary,
        rd.RestockConfig(top_n=10, long_term_days=2, short_term_days=1, include_events=True),
        selected_asins=("A1",),
    )

    assert summary["asin"].tolist() == ["A1"]


def test_apply_summary_filters_red_alerts_and_dictionary_asins():
    summary = pd.DataFrame(
        [
            {"asin": "A1", "alert": True, "short_title": "One", "collection": "C1", "skus": "S1", "fba_inventory": 10},
            {"asin": "A2", "alert": False, "short_title": "Two", "collection": "C2", "skus": "S2", "fba_inventory": 20},
            {"asin": "A3", "alert": True, "short_title": "Three", "collection": "C3", "skus": "S3", "fba_inventory": 30},
        ]
    )
    filtered_dict = pd.DataFrame([{"asin": "A1"}, {"asin": "A2"}])

    visible = rd.apply_summary_filters(summary, filtered_dictionary=filtered_dict, red_alerts_only=True)

    assert visible["asin"].tolist() == ["A1"]


def test_apply_summary_filters_secondary_search_intersects_dictionary_filter():
    summary = pd.DataFrame(
        [
            {"asin": "A1", "alert": True, "short_title": "Blue Sheet", "collection": "C1", "skus": "S1"},
            {"asin": "A2", "alert": False, "short_title": "Gray Sheet", "collection": "C2", "skus": "S2"},
        ]
    )
    filtered_dict = pd.DataFrame([{"asin": "A1"}, {"asin": "A2"}])

    visible = rd.apply_summary_filters(summary, filtered_dictionary=filtered_dict, search="gray")

    assert visible["asin"].tolist() == ["A2"]


def test_projection_replaces_baseline_with_event_forecast_day():
    calendar = rd.normalize_event_calendar(
        pd.DataFrame([{"event_code": "PD", "start_date": "2026-06-10", "end_date": "2026-06-11"}])
    )
    performance = pd.DataFrame(
        [{"ASIN": "A1", "Average PD sales, units (total)": 100, "Best PD performance": 40}]
    )

    rows, days_to_stockout, stockout_date, projected = rd.project_inventory(
        asin="A1",
        current_total=100,
        avg_units=5,
        start_date=date(2026, 6, 9),
        projection_days=2,
        event_calendar=calendar,
        event_performance=performance,
    )

    # high-volume formula: ((100 + 5*40) / 2) * 1.2 = 180 total, /2 event days = 90/day
    assert rows[1]["projected_inventory"] == 10
    assert rows[2]["projected_inventory"] == 0
    assert 1 < days_to_stockout < 2
    assert stockout_date == date(2026, 6, 10)
    assert projected == 0
