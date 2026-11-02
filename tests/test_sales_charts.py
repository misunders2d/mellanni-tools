import pandas as pd
import pytest

from modules import sales_charts


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
