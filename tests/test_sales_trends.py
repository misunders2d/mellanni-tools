"""Exercise the sales snapshot without Streamlit auth or live BigQuery."""

import ast
import os
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
import pyarrow as pa
import pyarrow.parquet as pq
import streamlit as st
from modules.sales_trends import SalesTrendsData, metric_delta, metric_value, safe_ratio

PAGE = Path(__file__).resolve().parents[1] / "pages" / "15_Sales_trends.py"


def write_cache(path, frame, version=b"2", generation=b"test"):
    table = pa.Table.from_pandas(frame, preserve_index=False)
    if version is not None:
        metadata = {
            **(table.schema.metadata or {}), b"sales_trends_version": version,
            b"sales_trends_generation": generation,
        }
        table = table.replace_schema_metadata(metadata)
    pq.write_table(table, path)


def page_cache_functions(paths, fresh_data, wipe_forecast=False):
    tree = ast.parse(PAGE.read_text())
    functions = [
        node for node in tree.body if isinstance(node, ast.FunctionDef)
        and node.name in ("load_sales_snapshot", "clear_data")
    ]
    namespace = {
        "os": os, "pa": pa, "pq": pq, "st": st, "SalesTrendsData": SalesTrendsData,
        "events": {}, "event_dates_list": [], "get_sales_data": fresh_data,
        "wipe_forecast": wipe_forecast, **paths,
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(PAGE), "exec"), namespace)
    return namespace


def load_function(previous=("2026-01-01", "2026-01-02"), events=None):
    event_ranges = events or {}
    event_dates = [
        day.date()
        for bounds in event_ranges.values()
        for day in pd.date_range(*bounds)
    ]

    def calculate(sales, sessions, ads, forecast, targets, available, include, dates, periods):
        snapshot = SalesTrendsData((sales, sessions, ads, forecast), event_ranges, event_dates)
        return snapshot.query(
            targets, available, include, dates, periods,
            tuple(date.fromisoformat(value) for value in previous),
        )

    return calculate


def frames(sales, sessions=(), ads=(), forecast=()):
    sales_rows = []
    for row in sales:
        sales_rows.append(
            {
                "asin": "A",
                "units": 10.0,
                "net_sales": 100.0,
                "available": 100.0,
                "inventory_supply_at_fba": 200.0,
                "collection": "C",
                "size": "S",
                "color": "white",
                "has_sales_row": True,
                "has_inventory_row": True,
                "change_notes": "",
                **row,
            }
        )
    sales_df = pd.DataFrame(sales_rows)
    sessions_df = pd.DataFrame(sessions, columns=["date", "asin", "sessions"])
    ads_df = pd.DataFrame(
        ads,
        columns=[
            "date",
            "asin",
            "ad_spend",
            "impressions",
            "clicks",
            "total_units",
            "total_sales",
        ],
    )
    forecast_df = pd.DataFrame(
        forecast, columns=["date", "asin", "forecast_units", "forecast_dollar"]
    )
    return sales_df, sessions_df, ads_df, forecast_df


def run(
    data,
    selected=("2026-02-01", "2026-02-02"),
    previous=("2026-01-01", "2026-01-02"),
    events=None,
    include_events=True,
    periods="custom",
    target_asins=None,
    available_inv=True,
):
    return load_function(previous, events)(
        *data,
        target_asins,
        available_inv,
        include_events,
        tuple(date.fromisoformat(value) for value in selected),
        periods,
    )


def test_asin_sessions_only_cover_selected_dates_and_asins():
    data = frames(
        [
            {"date": "2026-01-01"},
            {"date": "2026-02-01"},
            {"date": "2026-02-01", "asin": "B"},
        ],
        [
            ("2026-01-01", "A", 1000),
            ("2026-02-01", "A", 20),
            ("2026-02-02", "A", 30),
            ("2026-02-01", "B", 999),
        ],
    )
    visible, previous, asins, *_ = run(data, target_asins=["A"])
    assert asins["sessions"].tolist() == [50]
    assert visible["sessions"].sum() == 50
    assert previous["sessions"].sum() == 1000


def test_traffic_only_day_keeps_sessions_and_zero_sales():
    data = frames(
        [{"date": "2026-02-01"}],
        [("2026-02-02", "A", 25)],
    )
    visible, *_ = run(data, target_asins=["A"])
    row = visible.set_index("date").loc["2026-02-02"]
    assert row["sessions"] == 25
    assert row["units"] == 0
    assert pd.isna(row["average selling price"])


def test_zero_sales_with_inventory_still_contributes_stockout():
    data = frames(
        [
            *[
                {"date": day.date()}
                for day in pd.date_range("2026-01-03", "2026-01-31")
            ],
            {
                "date": "2026-02-01",
                "units": 0,
                "net_sales": 0,
                "available": 0,
                "inventory_supply_at_fba": 200,
                "has_sales_row": False,
            },
            {"date": "2026-02-01", "asin": "B", "available": 100},
        ]
    )
    available = run(
        data, selected=("2026-02-01", "2026-02-01"), target_asins=["A"]
    )[0]
    total_fba = run(
        data,
        selected=("2026-02-01", "2026-02-01"),
        target_asins=["A"],
        available_inv=False,
    )[0]
    assert available["stockout"].iloc[0] == pytest.approx(1)
    assert total_fba["stockout"].iloc[0] == 0


def test_calendar_average_counts_missing_days_and_is_input_order_independent():
    data = frames(
        [
            {"date": "2026-02-01", "units": 30, "net_sales": 300},
            {"date": "2026-01-02", "units": 3000, "net_sales": 30000},
        ]
    )
    visible, *_ = run(data, selected=("2026-02-01", "2026-02-01"))
    # Jan 2 is outside Jan 3-Feb 1. The other 29 days have zero sales.
    assert visible["30-day avg"].iloc[0] == 1
    assert visible["30-day sales avg"].iloc[0] == 10


def test_notes_and_forecast_do_not_change_historical_rolling_sales():
    data = frames(
        [
            {"date": "2026-01-03", "units": 30},
            {"date": "2026-02-01", "units": 30, "available": 1},
        ]
    )
    original = run(data)[0]
    added = frames(
        [
            *data[0].to_dict("records"),
            {
                "date": "2026-01-20",
                "units": 0,
                "net_sales": 0,
                "has_sales_row": False,
                "change_notes": "Price change",
            },
        ],
        forecast=[("2026-01-10", "A", 99, 999)],
    )
    result = run(added)[0]
    pd.testing.assert_series_equal(original["30-day avg"], result["30-day avg"])
    pd.testing.assert_series_equal(original["stockout"], result["stockout"])


def test_later_comparison_keeps_both_windows_and_ads():
    data = frames(
        [{"date": "2026-01-01"}, {"date": "2026-06-01", "units": 20}],
        [("2026-01-01", "A", 10), ("2026-06-01", "A", 20)],
        [
            ("2026-01-01", "A", 1, 10, 2, 1, 10),
            ("2026-06-01", "A", 2, 20, 4, 2, 20),
        ],
        [("2026-01-01", "A", 11, 110), ("2026-06-01", "A", 22, 220)],
    )
    visible, previous, _, ads_visible, ads_previous = run(
        data,
        selected=("2026-01-01", "2026-01-01"),
        previous=("2026-06-01", "2026-06-01"),
    )
    assert visible["units"].sum() == 10
    assert previous["units"].sum() == 20
    assert visible["forecast_units"].sum() == 11
    assert previous["forecast_units"].sum() == 22
    assert ads_visible["ad_spend"].sum() == 1
    assert ads_previous["ad_spend"].sum() == 2


def test_excluded_events_leave_gaps_but_selected_event_comparison_survives():
    events = {
        "sale": ("2026-01-01", "2026-01-02"),
        "current": ("2026-02-01", "2026-02-01"),
    }
    data = frames(
        [
            {"date": "2026-01-01"},
            {"date": "2026-02-01", "units": 999},
            {"date": "2026-02-02", "units": 29},
        ],
        [
            ("2026-01-01", "A", 100),
            ("2026-02-01", "A", 999),
            ("2026-02-02", "A", 29),
        ],
        [
            ("2026-01-01", "A", 1, 10, 2, 1, 10),
            ("2026-02-01", "A", 999, 10, 2, 1, 10),
        ],
    )
    visible, previous, asins, ads_visible, ads_previous = run(
        data, events=events, include_events=False, periods="sale"
    )
    assert visible["units"].sum() == 29
    assert pd.isna(visible["30-day avg"].iloc[0])
    assert visible["30-day avg"].iloc[1] == 1  # 29 units / 29 non-event days
    assert asins["sessions"].sum() == 29
    assert previous["units"].sum() == 10
    assert previous["sessions"].sum() == 100
    assert ads_previous["ad_spend"].sum() == 1
    assert pd.isna(ads_visible["ad_spend"].iloc[0])
    ordinary_previous = run(data, events=events, include_events=False)[1]
    assert ordinary_previous.empty


def test_inputs_unchanged_and_empty_selection_supported():
    data = frames(
        [{"date": "2026-02-01"}], forecast=[("2026-02-01", "A", 20, 200)]
    )
    before = [frame.copy(deep=True) for frame in data]
    result = run(data, target_asins=[])
    for original, frame in zip(before, data):
        pd.testing.assert_frame_equal(original, frame)
    assert result[2].empty
    assert result[0]["units"].sum() == 0


def test_inventory_query_preserves_inventory_only_rows():
    tree = ast.parse(PAGE.read_text())
    loader = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "get_sales_data"
    )
    assignment = next(
        node
        for node in loader.body
        if isinstance(node, ast.Assign) and node.targets[0].id == "sales_query"
    )
    query = eval(
        compile(ast.Expression(assignment.value), str(PAGE), "eval"),
        {"interval": "3 YEAR"},
    )
    inventory_join = query.split("sales_with_inventory AS (", 1)[1].split(
        "),", 1
    )[0]
    with sqlite3.connect(":memory:") as connection:
        connection.executescript("""
            CREATE TABLE sales_with_changelog(date TEXT, asin TEXT, units REAL, net_sales REAL, has_sales_row BOOLEAN, change_notes TEXT);
            CREATE TABLE inventory_by_date_asin(date TEXT, asin TEXT, inventory_supply_at_fba REAL, available REAL);
            INSERT INTO sales_with_changelog VALUES ('2026-02-01', 'A', 10, 100, TRUE, 'Note');
            INSERT INTO inventory_by_date_asin VALUES ('2026-02-01', 'A', 20, 10), ('2026-02-02', 'A', 0, 0);
        """)
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute(inventory_join)]
    assert len(rows) == 2
    no_sales = next(row for row in rows if row["date"] == "2026-02-02")
    assert no_sales["units"] == 0
    assert no_sales["has_sales_row"] == 0
    assert no_sales["has_inventory_row"] == 1
    assert no_sales["available"] == 0


def test_nullable_bigquery_columns_keep_chart_output_numeric():
    data = frames(
        [{"date": "2026-02-01", "available": None}],
        [("2026-02-01", "A", 20)],
        forecast=[("2026-02-02", "A", 20, 200)],
    )
    for column in ("units", "available", "inventory_supply_at_fba"):
        data[0][column] = data[0][column].astype("Int64")
    for column in ("has_sales_row", "has_inventory_row"):
        data[0][column] = data[0][column].astype("boolean")
    data[1]["sessions"] = data[1]["sessions"].astype("Int64")
    visible, *_ = run(data)
    assert visible["units"].dtype == "float64"
    assert visible["sessions"].dtype == "float64"
    assert pd.isna(visible["stockout"].iloc[0])  # Missing inventory is unknown.
    assert pd.isna(visible["units"].iloc[1])  # Forecast is not an actual sale.
    assert visible["forecast_units"].iloc[1] == 20


def test_legacy_sales_without_presence_flags_remain_supported():
    data = list(frames([{"date": "2026-02-01"}]))
    data[0] = data[0].drop(columns=["has_sales_row", "has_inventory_row"])
    visible, *_ = run(data)
    assert visible["units"].sum() == 10


def test_date_changes_reuse_snapshot_after_source_files_are_removed(tmp_path):
    data = frames([
        {"date": "2026-02-01", "units": 10},
        {"date": "2026-02-02", "units": 20},
    ])
    for name, frame in zip(("sales", "sessions", "ads", "forecast"), data):
        frame.to_parquet(tmp_path / f"{name}.parquet", index=False)
    snapshot = SalesTrendsData(tmp_path, {}, [])
    for path in tmp_path.glob("*.parquet"):
        path.unlink()
    for day, units in ((date(2026, 2, 1), 10), (date(2026, 2, 2), 20)):
        result = snapshot.query(None, True, True, (day, day))
        assert result[0]["units"].sum() == units


def test_cached_results_are_isolated_and_cache_is_bounded(monkeypatch):
    snapshot = SalesTrendsData(frames([{"date": "2026-02-01"}]), {}, [])
    selected = (date(2026, 2, 1), date(2026, 2, 1))
    first = snapshot.query(None, True, True, selected)
    expected = [frame.copy(deep=True) for frame in first]
    first[0].loc[0, "units"] = -1
    with monkeypatch.context() as patch:
        def unexpected_calculation(*args):
            pytest.fail("Identical parameters must reuse cached results")
        patch.setattr(snapshot, "_query", unexpected_calculation)
        again = snapshot.query(None, True, True, selected)
    for left, right in zip(expected, again):
        pd.testing.assert_frame_equal(left, right)
    for offset in range(1, 20):
        day = selected[0] + pd.Timedelta(days=offset)
        snapshot.query(None, True, True, (day, day))
    assert len(snapshot.cache) == 16


@pytest.mark.parametrize("wipe_forecast", [False, True])
def test_page_shares_snapshot_until_explicit_refresh(tmp_path, monkeypatch, wipe_forecast):
    monkeypatch.chdir(tmp_path)
    cache = tmp_path / "temp"
    cache.mkdir()
    data = frames([{"date": "2026-02-01"}])
    paths = {}
    for name, frame in zip(("sales", "sessions", "ads", "forecast"), data):
        paths[f"{name}_tempfile"] = str(cache / f"{name}.parquet")
        write_cache(paths[f"{name}_tempfile"], frame)
    refreshes = []

    def fresh_data():
        refreshes.append(True)
        return frames([{"date": "2026-02-01", "units": 20}])

    # Exercise the actual cached page loader and refresh callback without auth/BQ.
    namespace = page_cache_functions(paths, fresh_data, wipe_forecast)
    load = namespace["load_sales_snapshot"]
    load.clear()
    try:
        original = load()
        assert load() is original
        assert not refreshes
        namespace["clear_data"]()
        assert Path(paths["forecast_tempfile"]).exists() is not wipe_forecast
        refreshed = load()
        assert refreshed is not original
        assert load() is refreshed
        assert refreshed.frames[0]["units"].sum() == 20
        assert refreshes == [True]
    finally:
        load.clear()


@pytest.mark.parametrize("cache_state", ["legacy", "wrong_version", "corrupt", "mixed_snapshot"])
def test_page_rebuilds_incompatible_or_corrupt_cache(tmp_path, monkeypatch, cache_state):
    monkeypatch.chdir(tmp_path)
    cache = tmp_path / "temp"
    cache.mkdir()
    data = frames([{"date": "2026-02-01"}])
    paths = {}
    for name, frame in zip(("sales", "sessions", "ads", "forecast"), data):
        paths[f"{name}_tempfile"] = str(cache / f"{name}.parquet")
        write_cache(paths[f"{name}_tempfile"], frame)
    if cache_state == "corrupt":
        Path(paths["ads_tempfile"]).write_bytes(b"incomplete parquet")
    elif cache_state == "mixed_snapshot":
        write_cache(paths["ads_tempfile"], data[2], generation=b"interrupted refresh")
    else:
        write_cache(paths["ads_tempfile"], data[2], None if cache_state == "legacy" else b"1")
    refreshes = []

    def fresh_data():
        refreshes.append(True)
        return frames([{"date": "2026-02-01", "units": 20}])

    load = page_cache_functions(paths, fresh_data)["load_sales_snapshot"]
    load.clear()
    try:
        snapshot = load()
        assert snapshot.frames[0]["units"].sum() == 20
        assert snapshot.cached_at is not None
        assert load() is snapshot
        assert refreshes == [True]
        assert not list(cache.glob("*.tmp"))
        for path in paths.values():
            assert pq.read_schema(path).metadata[b"sales_trends_version"] == b"2"
    finally:
        load.clear()


def page_metrics(result):
    """Run the actual KPI calculations and card calls without auth or BigQuery."""
    tree = ast.parse(PAGE.read_text())
    page_guard = next(node for node in tree.body if isinstance(node, ast.If)
                      and any(isinstance(child, ast.Name) and child.id == "snapshot"
                              for child in ast.walk(node.test)))
    chart_guard = next(node for node in page_guard.body if isinstance(node, ast.If)
                       and ast.unparse(node.test) == "not combined.empty")
    start = next(index for index, node in enumerate(chart_guard.body)
                 if isinstance(node, ast.Assign) and node.targets[0].id == "total_units_this_year")
    end = next(index for index, node in enumerate(chart_guard.body)
               if isinstance(node, ast.Assign) and node.targets[0].id == "num_top_sellers")
    calculations = chart_guard.body[start:end]
    recorded = {}

    class Card:
        def metric(self, **kwargs):
            recorded[kwargs["label"]] = kwargs

    current, previous, _, ads, ads_previous = result
    namespace = {
        "pd": pd, "metric_delta": metric_delta, "metric_value": metric_value,
        "safe_ratio": safe_ratio, "combined": current, "combined_previous": previous,
        "ads_visible": ads, "ads_previous": ads_previous, "periods": "custom",
        "min_period": date(2026, 1, 1), "max_period": date(2026, 1, 2),
    }
    for node in calculations:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            namespace[node.value.func.value.id] = Card()
    exec(compile(ast.Module(body=calculations, type_ignores=[]), str(PAGE), "exec"), namespace)
    return recorded


@pytest.mark.parametrize("previous_units", [None, 0])
def test_page_handles_missing_and_zero_comparison_baselines(previous_units):
    rows = [{"date": "2026-02-01", "units": 0, "net_sales": 0}]
    if previous_units is not None:
        rows.append({"date": "2026-01-01", "units": previous_units, "net_sales": 0})
    data = frames(rows)
    data[0]["units"] = data[0]["units"].astype("Int64")
    result = run(data)
    cards = page_metrics(result)
    assert len(cards) == 16
    assert cards["Total units sold"]["value"] == "0"
    assert cards["Average price"]["value"] == "N/A"
    assert cards["Conversion %"]["value"] == "N/A"
    for card in cards.values():
        assert card["delta"] is None
        for field in ("value", "help"):
            assert "nan" not in card[field].lower()
            assert "inf" not in card[field].lower()


def test_page_daily_averages_ignore_future_dates_but_include_observed_zero_days():
    result = run(
        frames([
            {"date": "2026-02-01", "units": 10, "net_sales": 100},
            {"date": "2026-02-02", "units": 0, "net_sales": 0},
        ], forecast=[("2026-02-03", "A", 20, 200)]),
        selected=("2026-02-01", "2026-02-03"),
    )
    cards = page_metrics(result)
    assert cards["Avg units/day"]["value"] == "5.0"
    assert cards["Avg sales/day"]["value"] == "$50"
    assert cards["Total units sold"]["value"] == "10"


def test_page_keeps_valid_ratios_and_growth_percentages():
    cards = page_metrics(run(frames(
        [
            {"date": "2026-01-01", "units": 10, "net_sales": 100},
            {"date": "2026-02-01", "units": 20, "net_sales": 200},
        ],
        [("2026-01-01", "A", 100), ("2026-02-01", "A", 100)],
        [
            ("2026-01-01", "A", 1, 10, 2, 1, 10),
            ("2026-02-01", "A", 2, 20, 4, 2, 20),
        ],
    )))
    assert cards["Total units sold"]["value"] == "20"
    assert cards["Total units sold"]["delta"] == "100.0% vs period"
    assert cards["Average price"]["value"] == "$10.00"
    assert cards["Conversion %"]["value"] == "20.0%"
    assert cards["Avg CPC"]["value"] == "$0.50"
    assert cards["Avg ACoS"]["value"] == "10.0%"


def test_ads_query_keeps_halo_revenue_with_advertised_asin():
    tree = ast.parse(PAGE.read_text())
    loader = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                  and node.name == "get_sales_data")
    query_node = next(node for node in loader.body if isinstance(node, ast.Assign)
                      and node.targets[0].id == "ads_query")
    query = eval(compile(ast.Expression(query_node.value), str(PAGE), "eval"), {"interval": "3 YEAR"})
    query = query.replace("mellanni-project-da.reports.AdvertisedProduct", "advertised")
    query = query.replace('DATE_SUB(CURRENT_DATE("America/Los_Angeles"), INTERVAL 3 YEAR)', "'2023-02-01'")
    with sqlite3.connect(":memory:") as connection:
        connection.row_factory = sqlite3.Row
        connection.executescript("""
            CREATE TABLE advertised(date TEXT, advertisedAsin TEXT, country_code TEXT,
                spend REAL, impressions INTEGER, clicks INTEGER, unitsSoldClicks14d INTEGER,
                sales14d REAL, unitsSoldSameSku14d INTEGER, attributedSalesSameSku14d REAL);
            INSERT INTO advertised VALUES ('2026-02-01', 'A', 'us', 10, 100, 10, 1, 100, 0, 0);
            INSERT INTO advertised VALUES ('2026-02-01', 'B', 'us', 0, 0, 0, 0, 0, 0, 0);
            INSERT INTO advertised VALUES ('2026-02-01', 'A', 'ca', 99, 999, 99, 99, 999, 99, 999);
        """)
        rows = {row["asin"]: dict(row) for row in connection.execute(query)}
    assert rows["A"]["total_sales"] == 100
    assert rows["A"]["total_units"] == 1
    assert rows["A"]["ad_spend"] == 10
    assert rows["B"]["total_sales"] == 0


def test_seller_ranks_follow_display_order():
    tree = ast.parse(PAGE.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "_top_n_sellers")
    namespace = {"pd": pd}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(PAGE), "exec"), namespace)
    ranked = pd.DataFrame({"asin": ["A", "B", "C"], "net_sales": [10., 30., 20.]})
    table = namespace["_top_n_sellers"](ranked.sort_values("net_sales", ascending=False), 2)
    assert table["asin"].iloc[:2].tolist() == ["B", "C"]
    assert table["#"].iloc[:2].tolist() == [1, 2]
    assert table["net_sales"].iloc[-1] == 50
