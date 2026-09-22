"""Exercise the page's pure calculation without Streamlit auth or live BigQuery."""

import ast
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from dateutil.relativedelta import relativedelta

PAGE = Path(__file__).resolve().parents[1] / "pages" / "15_Sales_trends.py"


def load_function(previous=("2026-01-01", "2026-01-02"), events=None):
    tree = ast.parse(PAGE.read_text())
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "filtered_sales"
    )
    event_ranges = events or {}
    namespace = {
        "pd": pd,
        "relativedelta": relativedelta,
        "min_period": date.fromisoformat(previous[0]),
        "max_period": date.fromisoformat(previous[1]),
        "events": event_ranges,
        "event_dates_list": [
            day.date()
            for bounds in event_ranges.values()
            for day in pd.date_range(*bounds)
        ],
    }
    exec(  # noqa: S102 - Execute only the trusted local function, without page startup.
        compile(ast.Module(body=[function], type_ignores=[]), str(PAGE), "exec"),
        namespace,
    )
    return namespace["filtered_sales"]


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
