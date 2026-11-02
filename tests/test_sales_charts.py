import pandas as pd
import pytest

from modules import sales_charts


@pytest.fixture(autouse=True)
def reset_chart_legend():
    sales_charts.st.session_state.pop("sales_trends_chart_legend", None)
    yield
    sales_charts.st.session_state.pop("sales_trends_chart_legend", None)


def _sales_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp("2026-06-01").date(), pd.Timestamp("2026-06-02").date()],
            "units": [10, 20],
            "forecast_units": [11, 21],
            "sessions": [100, 200],
            "30-day avg": [9, 19],
            "available": [50, 60],
            "inventory_supply_at_fba": [55, 65],
            "stockout": [0, 0],
            "change_notes": ["Price change: test note", ""],
        }
    )


def _ads_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp("2026-06-01").date(), pd.Timestamp("2026-06-02").date()],
            "ad_spend": [1.25, 2.50],
            "total_sales": [10.0, 20.0],
            "total_units": [1, 2],
            "clicks": [5, 10],
            "impressions": [100, 200],
        }
    )


def test_change_note_markpoint_uses_date_category(monkeypatch):
    captured = {}

    def fake_st_echarts(options, **kwargs):
        captured["options"] = options
        captured["kwargs"] = kwargs

    monkeypatch.setattr(sales_charts, "st_echarts", fake_st_echarts)

    sales_charts.render_sales_chart(_sales_df(), _ads_df(), show_change_notes=True)

    units_series = captured["options"]["series"][0]
    mark_points = units_series["markPoint"]["data"]

    assert mark_points[0]["coord"] == ["2026-06-01", 10]
    assert mark_points[0]["coord"][0] in captured["options"]["xAxis"][0]["data"]
    assert mark_points[0]["coord"][0] != 0


@pytest.mark.parametrize("stockout", [[None, 0.2], [None, None]])
def test_unknown_stockout_and_undefined_acos_remain_gaps(monkeypatch, stockout):
    captured = {}
    monkeypatch.setattr(sales_charts, "st_echarts", lambda options, **_: captured.update(options))
    sales = _sales_df()
    sales["stockout"] = pd.Series(stockout, dtype="Float64")
    ads = _ads_df()
    ads["total_sales"] = [0., 20.]
    before_sales, before_ads = sales.copy(deep=True), ads.copy(deep=True)
    sales_charts.render_sales_chart(sales, ads)
    series = {item["name"]: item["data"] for item in captured["series"]}
    assert series["Stockout"][0] is None
    assert series["Stockout"][1] == (20.0 if stockout[1] is not None else None)
    assert series["ACoS"] == [None, 12.5]
    pd.testing.assert_frame_equal(sales, before_sales)
    pd.testing.assert_frame_equal(ads, before_ads)


def test_fractional_averages_and_stockout_scale(monkeypatch):
    captured = {}
    monkeypatch.setattr(sales_charts, "st_echarts", lambda options, **_: captured.update(options))
    sales = _sales_df()
    sales["30-day avg"] = [0.4, 1.4]
    sales_charts.render_sales_chart(sales, _ads_df())
    average = next(series for series in captured["series"] if series["name"] == "30-day avg")
    assert average["data"] == [0.4, 1.4]
    assert captured["yAxis"][3]["min"] == 0
    assert captured["yAxis"][3]["max"] == 100


@pytest.mark.parametrize("notes", [
    "LD: sale | Price change: cut, keep size",
    "Price change: cut, keep size | BD: sale",
    "ld: sale | Price change: cut, keep size | BD: sale",
])
def test_deal_toggle_preserves_other_notes(monkeypatch, notes):
    captured = {}
    monkeypatch.setattr(sales_charts, "st_echarts", lambda options, **_: captured.update(options))
    sales = _sales_df()
    sales["change_notes"] = [notes, ""]
    sales_charts.render_sales_chart(sales, _ads_df(), show_lds=False)
    pins = captured["series"][0]["markPoint"]["data"]
    assert pins[0]["tooltip"]["formatter"] == "2026-06-01<br/>Price change: cut, keep size"
    sales_charts.render_sales_chart(sales, _ads_df(), show_lds=True)
    assert "sale" in captured["series"][0]["markPoint"]["data"][0]["tooltip"]["formatter"]


def test_comparison_alignment_preserves_calendar_gaps_and_dates(monkeypatch):
    captured = {}
    monkeypatch.setattr(sales_charts, "st_echarts", lambda options, **_: captured.update(options))
    previous = pd.DataFrame({"date": ["2025-06-02", "2025-06-03"], "units": [7, 9]})
    before = previous.copy(deep=True)
    sales_charts.render_sales_chart(
        _sales_df(), _ads_df(), comparison_df=previous, comparison_start="2025-06-01",
    )
    comparison = next(series for series in captured["series"] if series["name"] == "Comparison units")
    assert comparison["data"] == [
        {"value": None, "comparison_date": "2025-06-01"},
        {"value": 7, "comparison_date": "2025-06-02"},
    ]
    assert comparison["connectNulls"] is False
    assert comparison["yAxisIndex"] == captured["series"][0]["yAxisIndex"]
    pd.testing.assert_frame_equal(previous, before)


def test_ad_metrics_are_optional_and_axes_have_distinct_offsets(monkeypatch):
    captured = {}
    monkeypatch.setattr(sales_charts, "st_echarts", lambda options, **_: captured.update(options))
    sales_charts.render_sales_chart(_sales_df(), _ads_df())
    selected = captured["legend"][1]["selected"]
    assert selected["Ad Spend"] and selected["ACoS"]
    for name in ("Ad Units", "Impressions", "Clicks"):
        assert selected[name] is False
        assert next(axis for axis in captured["yAxis"] if axis["name"] == name)["show"] is False
    sales_charts.st.session_state["sales_trends_chart_legend"] = {
        "Ad Units": True, "Impressions": True, "Clicks": True,
    }
    sales_charts.render_sales_chart(_sales_df(), _ads_df())
    offsets = [axis["offset"] for axis in captured["yAxis"][6:] if axis["show"]]
    assert len(offsets) == len(set(offsets)) == 3
    assert all(axis["position"] == "left" for axis in captured["yAxis"][6:])


def test_legend_event_persists_selection_without_a_rerun_loop(monkeypatch):
    monkeypatch.setattr(sales_charts, "st_echarts", lambda **_: {"Clicks": True})
    reruns = []
    monkeypatch.setattr(sales_charts.st, "rerun", lambda: reruns.append(True))
    sales_charts.render_sales_chart(_sales_df(), _ads_df())
    assert sales_charts.st.session_state["sales_trends_chart_legend"]["Clicks"] is True
    sales_charts.render_sales_chart(_sales_df(), _ads_df())
    assert reruns == [True]
